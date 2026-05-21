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
//! and writes them to Redis under the `acct:seq` CAS guard. `HSET` overwrites only the
//! specified fields, leaving booked counters (`int_cores`/`int_gpus`) untouched.

use std::panic::AssertUnwindSafe;
use std::sync::Arc;

use futures::FutureExt;
use miette::{IntoDiagnostic, Result, WrapErr};
use tokio::time;
use tracing::{debug, error, info, warn};

use crate::accounting::dao::{
    FolderLimitsRow, JobLimitsRow, PointLimitsRow, SubscriptionLimitsRow,
};
use crate::accounting::redis_client::ReseedOp;
use crate::accounting::AccountingService;
use crate::config::CONFIG;

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

/// One CAS-guarded reseed pass: snapshot all four limit tables, flatten to ops, send
/// in one `RESEED_CAS`. On CAS miss, recompute the snapshot and retry. Used by both
/// the loop and the bootstrap.
pub async fn reseed_once(service: &AccountingService) -> Result<()> {
    let max_retries = CONFIG.accounting.cas_max_retries;
    for attempt in 0..=max_retries {
        let seq_before = service.redis().get_seq().await.into_diagnostic()?;

        let (subs, folders, jobs, points) = tokio::try_join!(
            service.dao().query_subscription_limits(),
            service.dao().query_folder_limits(),
            service.dao().query_job_limits(),
            service.dao().query_point_limits(),
        )?;

        let ops: Vec<ReseedOp> = subscription_ops(&subs)
            .chain(folder_ops(&folders))
            .chain(job_ops(&jobs))
            .chain(point_ops(&points))
            .collect();

        debug!(
            "Limit reseed attempt {}/{}: subs={} folders={} jobs={} points={} -> {} ops at seq={}",
            attempt + 1,
            max_retries + 1,
            subs.len(),
            folders.len(),
            jobs.len(),
            points.len(),
            ops.len(),
            seq_before
        );

        let applied = service
            .redis()
            .reseed_cas(seq_before, &ops)
            .await
            .into_diagnostic()
            .wrap_err("RESEED_CAS for limits failed")?;
        if applied {
            info!(
                "Limit reseed applied: {} ops, seq={}",
                ops.len(),
                seq_before
            );
            return Ok(());
        }
        warn!(
            "Limit reseed CAS miss (attempt {}/{}); resnapshot and retry",
            attempt + 1,
            max_retries + 1
        );
    }
    warn!(
        "Limit reseed exhausted {} CAS retries; cycle skipped",
        max_retries + 1
    );
    Ok(())
}

/// Flatten subscription limit rows into per-field `ReseedOp`s (`size`, `burst`).
fn subscription_ops(rows: &[SubscriptionLimitsRow]) -> impl Iterator<Item = ReseedOp> + '_ {
    rows.iter().flat_map(|r| {
        let key = format!("acct:sub:{}:{}", r.show_id, r.alloc_id);
        [
            ReseedOp {
                key: key.clone(),
                field: "size",
                value: r.size,
            },
            ReseedOp {
                key,
                field: "burst",
                value: r.burst,
            },
        ]
    })
}

/// Flatten folder limit rows into the four cap fields per row.
fn folder_ops(rows: &[FolderLimitsRow]) -> impl Iterator<Item = ReseedOp> + '_ {
    rows.iter().flat_map(|r| {
        let key = format!("acct:folder:{}", r.folder_id);
        [
            ReseedOp {
                key: key.clone(),
                field: "int_min_cores",
                value: r.min_cores,
            },
            ReseedOp {
                key: key.clone(),
                field: "int_max_cores",
                value: r.max_cores,
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

/// Flatten job limit rows into the three cap fields per row.
fn job_ops(rows: &[JobLimitsRow]) -> impl Iterator<Item = ReseedOp> + '_ {
    rows.iter().flat_map(|r| {
        let key = format!("acct:job:{}", r.job_id);
        [
            ReseedOp {
                key: key.clone(),
                field: "int_max_cores",
                value: r.max_cores,
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
/// `int_max_*` columns in the schema; only minimums are surfaced.)
fn point_ops(rows: &[PointLimitsRow]) -> impl Iterator<Item = ReseedOp> + '_ {
    rows.iter().flat_map(|r| {
        let key = format!("acct:point:{}:{}", r.dept_id, r.show_id);
        [
            ReseedOp {
                key: key.clone(),
                field: "int_min_cores",
                value: r.min_cores,
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
    fn subscription_emits_two_fields_per_row() {
        let out: Vec<ReseedOp> = subscription_ops(&[SubscriptionLimitsRow {
            show_id: Uuid::nil(),
            alloc_id: Uuid::nil(),
            size: 100,
            burst: 200,
        }])
        .collect();
        assert_eq!(out.len(), 2);
        assert!(out.iter().any(|o| o.field == "size" && o.value == 100));
        assert!(out.iter().any(|o| o.field == "burst" && o.value == 200));
    }

    #[test]
    fn folder_emits_four_cap_fields_per_row() {
        let out: Vec<ReseedOp> = folder_ops(&[FolderLimitsRow {
            folder_id: Uuid::nil(),
            min_cores: 0,
            max_cores: -1,
            min_gpus: 0,
            max_gpus: -1,
        }])
        .collect();
        assert_eq!(out.len(), 4);
        let fields: std::collections::HashSet<_> = out.iter().map(|o| o.field).collect();
        assert!(fields.contains("int_min_cores"));
        assert!(fields.contains("int_max_cores"));
        assert!(fields.contains("int_min_gpus"));
        assert!(fields.contains("int_max_gpus"));
    }
}
