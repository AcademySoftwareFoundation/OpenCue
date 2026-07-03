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

//! Limit-field reseed loop - the cap-change backstop. Every
//! `CONFIG.accounting.limit_reseed_interval`, reads the enforced caps from PG
//! (subscription burst, folder/job `int_max_cores`/`int_max_gpus`) and writes them into
//! the in-memory store. The live `acct_limit_change` NOTIFY propagates cueadmin changes
//! immediately; this loop heals any missed notification within one interval.
//!
//! Only the caps the booking check reads are seeded (subscription burst, folder/job max
//! cores+gpus). Size, min-cores, priority and point caps are not enforced by the
//! scheduler, so they live only in PG (CueGUI reads them there, unchanged).

use std::panic::AssertUnwindSafe;
use std::sync::Arc;

use futures::FutureExt;
use miette::Result;
use tokio::time;
use tracing::{error, info, warn};
use uuid::Uuid;

use crate::accounting::dao::{
    AccountingDao, FolderLimitsRow, JobLimitsRow, SubscriptionLimitsRow,
};
use crate::accounting::store::{centicores_to_cores, centicores_to_cores_cap, Store};
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

/// One reseed pass: snapshot the limit tables and write the enforced caps into the store.
/// Shared by the periodic loop, the bootstrap, and the synchronous seed performed when a
/// show first becomes scheduler-managed (`ManagedShowsCache`).
pub async fn reseed_limits(store: &Store, dao: &AccountingDao) -> Result<()> {
    let (subs, folders, jobs) = tokio::try_join!(
        dao.query_subscription_limits(),
        dao.query_folder_limits(),
        dao.query_job_limits(),
    )?;

    store.set_caps(
        subs.iter().map(sub_cap),
        folders.iter().map(folder_cap),
        jobs.iter().map(job_cap),
    );

    info!(
        "Limit reseed applied: subs={} folders={} jobs={}",
        subs.len(),
        folders.len(),
        jobs.len(),
    );
    Ok(())
}

/// Thin wrapper over [`reseed_limits`] taking the full service. Used by the periodic loop
/// and the bootstrap.
pub async fn reseed_once(service: &AccountingService) -> Result<()> {
    reseed_limits(service.store(), service.dao()).await
}

/// `(show, alloc, burst_cores, max_slots)`. Burst is PG centicores → cores; never the `-1`
/// sentinel. Slots are whole counts (no centicore conversion); `-1` unlimited passes through.
fn sub_cap(r: &SubscriptionLimitsRow) -> (Uuid, Uuid, i64, i64) {
    (
        r.show_id,
        r.alloc_id,
        centicores_to_cores(r.burst),
        r.max_slots,
    )
}

/// `(folder, max_cores, max_gpus, max_slots)`. Cores preserve the `-1` unlimited sentinel;
/// GPUs and slots pass through unconverted (whole counts; their `-1` sentinel survives).
fn folder_cap(r: &FolderLimitsRow) -> (Uuid, i64, i64, i64) {
    (
        r.folder_id,
        centicores_to_cores_cap(r.max_cores),
        r.max_gpus,
        r.max_slots,
    )
}

/// `(job, max_cores, max_gpus, max_slots)`. Same conventions as [`folder_cap`].
fn job_cap(r: &JobLimitsRow) -> (Uuid, i64, i64, i64) {
    (
        r.job_id,
        centicores_to_cores_cap(r.max_cores),
        r.max_gpus,
        r.max_slots,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sub_burst_converts_centicores_to_cores() {
        let r = SubscriptionLimitsRow {
            show_id: Uuid::nil(),
            alloc_id: Uuid::nil(),
            burst: 1000,
            max_slots: -1,
        };
        assert_eq!(sub_cap(&r), (Uuid::nil(), Uuid::nil(), 10, -1));
    }

    #[test]
    fn folder_preserves_unlimited_and_passes_gpus() {
        let r = FolderLimitsRow {
            folder_id: Uuid::nil(),
            max_cores: -1,
            max_gpus: -1,
            max_slots: 5,
        };
        assert_eq!(folder_cap(&r), (Uuid::nil(), -1, -1, 5));
    }

    #[test]
    fn job_converts_positive_cap_to_cores() {
        let r = JobLimitsRow {
            job_id: Uuid::nil(),
            max_cores: 2000,
            max_gpus: 4,
            max_slots: 0,
        };
        assert_eq!(job_cap(&r), (Uuid::nil(), 20, 4, 0));
    }
}
