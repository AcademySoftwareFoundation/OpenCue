// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

//! Limit-field reseed loop. Every `CONFIG.accounting.limit_reseed_interval`,
//! reads limit fields from PG (subscription burst/size, folder/job caps, point min/max)
//! and writes them to Redis with unconditional `HSET`s. `HSET` overwrites only the
//! specified fields, leaving booked counters (`int_cores`/`int_gpus`) untouched, so this
//! needs no `acct:seq` CAS guard (limit fields are written only here, never by the
//! booking hot path) - which also stops force-rollback churn from starving the reseed and
//! leaving a freshly-managed show's subscription `burst` unseeded (== 0 == "reject all").

use std::panic::AssertUnwindSafe;
use std::sync::Arc;

use futures::FutureExt;
use miette::{IntoDiagnostic, Result, WrapErr};
use tokio::time;
use tracing::{error, info, warn};

use crate::accounting::dao::{
    AccountingDao, FolderLimitsRow, JobLimitsRow, PointLimitsRow, SubscriptionLimitsRow,
};
use crate::accounting::redis_client::{RedisAccounting, ReseedOp};
use crate::accounting::AccountingService;
use crate::config::CONFIG;
use crate::models::CoreSize;

pub fn spawn_loop(service: Arc<AccountingService>) {
    tokio::spawn(async move {
        let mut interval = time::interval(CONFIG.accounting.limit_reseed_interval);
        // Skip the immediate first tick - bootstrap reseed already ran at startup.
        interval.tick().await;
        loop {
            interval.tick().await;
            let result = AssertUnwindSafe(async {
                if let Err(err) = reseed_once(&service).await {
                    warn!("Limit reseed cycle failed: {err}");
                }
            })
            .catch_unwind()
            .await;
            if let Err(e) = result {
                error!("Limit reseed iteration panicked: {:?}", e);
            }
        }
    });
}

/// One reseed pass: snapshot all four limit tables, flatten to ops, write them with
/// unconditional `HSET`s (no `acct:seq` CAS). Shared by the periodic loop, the bootstrap,
/// and the synchronous seed performed when a show first becomes scheduler-managed
/// (`ManagedShowsCache`).
///
/// No CAS guard because limit fields are written only here and are disjoint from the
/// booked counters the hot path mutates - so this can never clobber a booking, and a
/// concurrent booking can never clobber it. The previous CAS-guarded variant could be
/// starved into skipping by force-rollback churn bumping `acct:seq`; an unconditional
/// write always lands. See `RedisAccounting::reseed_unconditional`.
pub async fn reseed_limits(redis: &RedisAccounting, dao: &AccountingDao) -> Result<()> {
    let (subs, folders, jobs, points) = tokio::try_join!(
        dao.query_subscription_limits(),
        dao.query_folder_limits(),
        dao.query_job_limits(),
        dao.query_point_limits(),
    )?;

    let ops: Vec<ReseedOp> = subscription_ops(&subs)
        .chain(folder_ops(&folders))
        .chain(job_ops(&jobs))
        .chain(point_ops(&points))
        .collect();

    redis
        .reseed_unconditional(&ops)
        .await
        .into_diagnostic()
        .wrap_err("HSET reseed for limit fields failed")?;

    info!(
        "Limit reseed applied: {} ops (subs={} folders={} jobs={} points={})",
        ops.len(),
        subs.len(),
        folders.len(),
        jobs.len(),
        points.len(),
    );
    Ok(())
}

/// Thin wrapper over [`reseed_limits`] taking the full service. Used by the periodic loop
/// and the bootstrap.
pub async fn reseed_once(service: &AccountingService) -> Result<()> {
    reseed_limits(service.redis(), service.dao()).await
}

/// Flatten subscription limit rows into per-field `ReseedOp`s (`size`, `burst`).
/// PG centicores → Redis cores via `CoreSize::from_multiplied`; the type carries
/// the unit through the conversion. Subscription caps never use the `-1` sentinel.
fn subscription_ops(rows: &[SubscriptionLimitsRow]) -> impl Iterator<Item = ReseedOp> + '_ {
    rows.iter().flat_map(|r| {
        let key = format!("acct:sub:{}:{}", r.show_id, r.alloc_id);
        [
            ReseedOp {
                key: key.clone(),
                field: "size",
                value: i64::from(CoreSize::from_multiplied(r.size).value()),
            },
            ReseedOp {
                key,
                field: "burst",
                value: i64::from(CoreSize::from_multiplied(r.burst).value()),
            },
        ]
    })
}

/// Flatten folder limit rows into the four cap fields per row. `int_max_cores` uses
/// `from_multiplied_cap` to preserve the `-1` "unlimited" sentinel; GPU fields
/// pass through unconverted.
fn folder_ops(rows: &[FolderLimitsRow]) -> impl Iterator<Item = ReseedOp> + '_ {
    rows.iter().flat_map(|r| {
        let key = format!("acct:folder:{}", r.folder_id);
        [
            ReseedOp {
                key: key.clone(),
                field: "int_min_cores",
                value: i64::from(CoreSize::from_multiplied(r.min_cores).value()),
            },
            ReseedOp {
                key: key.clone(),
                field: "int_max_cores",
                value: i64::from(CoreSize::from_multiplied_cap(r.max_cores).value()),
            },
            ReseedOp {
                key: key.clone(),
                field: "int_min_gpus",
                value: r.min_gpus,
            },
            ReseedOp {
                key,
                field: "int_max_gpus",
                value: r.max_gpus,
            },
        ]
    })
}

/// Flatten job limit rows into the three cap fields per row. `int_max_cores`
/// uses `from_multiplied_cap` for the `-1` sentinel; `int_max_gpus` and
/// `int_priority` pass through unconverted.
fn job_ops(rows: &[JobLimitsRow]) -> impl Iterator<Item = ReseedOp> + '_ {
    rows.iter().flat_map(|r| {
        let key = format!("acct:job:{}", r.job_id);
        [
            ReseedOp {
                key: key.clone(),
                field: "int_max_cores",
                value: i64::from(CoreSize::from_multiplied_cap(r.max_cores).value()),
            },
            ReseedOp {
                key: key.clone(),
                field: "int_max_gpus",
                value: r.max_gpus,
            },
            ReseedOp {
                key,
                field: "int_priority",
                value: r.priority,
            },
        ]
    })
}

/// Flatten point limit rows into the two floor fields per row. (Point has no
/// `int_max_*` columns in the schema; only minimums are surfaced.) `int_min_cores`
/// is a floor, never negative, so `from_multiplied` is sufficient.
fn point_ops(rows: &[PointLimitsRow]) -> impl Iterator<Item = ReseedOp> + '_ {
    rows.iter().flat_map(|r| {
        let key = format!("acct:point:{}:{}", r.dept_id, r.show_id);
        [
            ReseedOp {
                key: key.clone(),
                field: "int_min_cores",
                value: i64::from(CoreSize::from_multiplied(r.min_cores).value()),
            },
            ReseedOp {
                key,
                field: "int_min_gpus",
                value: r.min_gpus,
            },
        ]
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use uuid::Uuid;

    #[test]
    fn subscription_emits_two_fields_in_cores() {
        // PG centicores 900/1000 -> Redis cores 9/10.
        let out: Vec<ReseedOp> = subscription_ops(&[SubscriptionLimitsRow {
            show_id: Uuid::nil(),
            alloc_id: Uuid::nil(),
            size: 900,
            burst: 1000,
        }])
        .collect();
        assert_eq!(out.len(), 2);
        assert!(out.iter().any(|o| o.field == "size" && o.value == 9));
        assert!(out.iter().any(|o| o.field == "burst" && o.value == 10));
    }

    #[test]
    fn folder_converts_cores_passes_gpus_and_preserves_unlimited() {
        // min_cores: 0 -> 0; max_cores: -1 (unlimited sentinel) -> -1; GPUs unchanged.
        let out: Vec<ReseedOp> = folder_ops(&[FolderLimitsRow {
            folder_id: Uuid::nil(),
            min_cores: 0,
            max_cores: -1,
            min_gpus: 0,
            max_gpus: -1,
        }])
        .collect();
        assert_eq!(out.len(), 4);
        let by_field: std::collections::HashMap<_, _> =
            out.iter().map(|o| (o.field, o.value)).collect();
        assert_eq!(by_field["int_min_cores"], 0);
        assert_eq!(by_field["int_max_cores"], -1);
        assert_eq!(by_field["int_min_gpus"], 0);
        assert_eq!(by_field["int_max_gpus"], -1);
    }

    #[test]
    fn folder_converts_positive_cap_to_cores() {
        let out: Vec<ReseedOp> = folder_ops(&[FolderLimitsRow {
            folder_id: Uuid::nil(),
            min_cores: 500,
            max_cores: 2000,
            min_gpus: 0,
            max_gpus: 4,
        }])
        .collect();
        let by_field: std::collections::HashMap<_, _> =
            out.iter().map(|o| (o.field, o.value)).collect();
        assert_eq!(by_field["int_min_cores"], 5);
        assert_eq!(by_field["int_max_cores"], 20);
        assert_eq!(by_field["int_max_gpus"], 4); // GPUs unconverted.
    }
}
