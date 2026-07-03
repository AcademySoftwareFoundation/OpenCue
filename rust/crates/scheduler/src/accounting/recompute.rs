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

//! Booked-counter recompute loop - the correctness backstop. Every
//! `CONFIG.accounting.recompute_interval`:
//!
//! 1. PG side (durable, unconditional): the existing `RECOMPUTE_*_FROM_PROC` UPDATEs keep
//!    the PG accounting tables (CueGUI's view) within one interval of `proc` for
//!    scheduler-managed shows.
//! 2. Store side: a single `SUM(proc)` snapshot keyed by (show, alloc, folder, job) is
//!    overlaid on a zero-baseline and written absolutely into the in-memory store, with
//!    each key's in-flight `pending` delta carried forward. The carry-forward is what
//!    keeps the overwrite from erasing a booking whose `proc` row is not yet visible to
//!    the snapshot - the only way an absolute overwrite could under-count and over-book a
//!    hard cap. No retry / CAS: the live store is the primary record, this only reconciles.

use std::collections::HashMap;
use std::panic::AssertUnwindSafe;
use std::sync::Arc;

use futures::FutureExt;
use miette::Result;
use tokio::time;
use tracing::{debug, error, info, warn};
use uuid::Uuid;

use crate::accounting::dao::{BaselineKeys, BookedSnapshotRow};
use crate::accounting::store::{centicores_to_cores, CounterSnapshot};
use crate::accounting::AccountingService;
use crate::config::CONFIG;
use crate::dao::ResourceAccountingDao;
use crate::metrics;

pub fn spawn_loop(service: Arc<AccountingService>) {
    tokio::spawn(async move {
        let pg_dao = match ResourceAccountingDao::new().await {
            Ok(d) => Arc::new(d),
            Err(err) => {
                error!("Recompute loop aborting: PG dao init failed: {err}");
                return;
            }
        };
        let interval_dur = CONFIG.accounting.recompute_interval;
        let mut interval = time::interval(interval_dur);
        // Skip the immediate first tick - bootstrap reseed already ran at startup.
        interval.tick().await;
        // Dispatch heartbeat baseline: snapshot the session counters so the first
        // logged delta only covers events after this point.
        let mut last_dispatched = metrics::frames_dispatched_session();
        let mut last_limit_exceeded = metrics::resource_limit_exceeded_session();
        loop {
            interval.tick().await;

            // Dispatch heartbeat: the aggregate INFO that replaces the demoted
            // per-frame dispatch logs. Decoupled from the accounting reseed below.
            let current_dispatched = metrics::frames_dispatched_session();
            let dispatched_delta = current_dispatched.saturating_sub(last_dispatched);
            last_dispatched = current_dispatched;

            let current_limit_exceeded = metrics::resource_limit_exceeded_session();
            let limit_exceeded_delta = current_limit_exceeded.saturating_sub(last_limit_exceeded);
            last_limit_exceeded = current_limit_exceeded;

            info!(
                "Dispatched {} frames in the last {}ms ({} resource-limit-exceeded)",
                dispatched_delta,
                interval_dur.as_millis(),
                limit_exceeded_delta
            );

            let result = AssertUnwindSafe(async {
                if let Err(err) = run_once(&service, &pg_dao).await {
                    warn!("Recompute cycle failed: {err}");
                }
            })
            .catch_unwind()
            .await;
            if let Err(e) = result {
                error!("Recompute iteration panicked: {:?}", e);
            }
        }
    });
}

/// One pass: PG recompute (unconditional, for CueGUI) + store reseed.
async fn run_once(service: &AccountingService, pg_dao: &Arc<ResourceAccountingDao>) -> Result<()> {
    debug!("Recompute cycle: starting");

    // PG side: durable, scoped to scheduler-managed shows. Empty list is a no-op inside
    // the DAO so we never widen to all shows and clobber Cuebot's accounting.
    let managed_ids: Vec<Uuid> = service.managed_shows().snapshot().into_iter().collect();
    if managed_ids.is_empty() {
        debug!("PG recompute skipped: no scheduler-managed shows");
    } else {
        if let Err(err) = pg_dao.recompute_all_from_proc(&managed_ids).await {
            warn!("PG recompute (layer/job/folder/point) failed (store reseed still runs): {err}");
        }
        if let Err(err) = pg_dao.recompute_subscription_table(&managed_ids).await {
            warn!("PG subscription recompute failed (store reseed still runs): {err}");
        }
    }

    reseed_store_once(service).await
}

/// Overwrite the store's booked counters from a fresh `SUM(proc)` snapshot, carrying each
/// key's pending in-flight delta forward (handled inside `Store::overwrite_counters`).
///
/// The snapshot is overlaid on a zero-baseline of every enumerable sub/folder/job key, so
/// a key whose counter drifted stale-high and then drained to zero procs is reset to 0
/// (the `SUM(proc)` snapshot alone only returns keys that still have procs). Used by both
/// the recompute loop and the bootstrap.
pub async fn reseed_store_once(service: &AccountingService) -> Result<()> {
    // Bump the epoch BEFORE reading the snapshot so a `confirm` that races this read lands
    // in a settled bucket the overwrite will not clear (closes the straddle hole).
    let epoch = service.store().begin_recompute();
    let (rows, baseline) = tokio::try_join!(
        service.dao().query_booked_snapshot(),
        service.dao().query_booked_baseline_keys(),
    )?;
    let snapshot = snapshot_to_counters(&rows, &baseline);
    let n = snapshot.sub.len() + snapshot.folder.len() + snapshot.job.len();
    service.store().overwrite_counters(&snapshot, epoch);
    info!("Recompute reseed applied: {} keys from {} proc rows", n, rows.len());
    Ok(())
}

/// Aggregate one `SUM(proc)` snapshot into per-vertex core/gpu totals (in cores), overlaid
/// on the zero-baseline. The SQL groups finer than the vertices (by layer/dept too), so
/// several rows fold into the same sub/folder/job key - aggregate before converting.
///
/// Layer and point are intentionally absent: the booking check never reads them, so they
/// are not tracked in the store (the legacy Lua incremented them but never enforced them).
pub(crate) fn snapshot_to_counters(
    rows: &[BookedSnapshotRow],
    baseline: &BaselineKeys,
) -> CounterSnapshot {
    let mut sub: HashMap<(Uuid, Uuid), (i64, i64, i64)> = HashMap::new();
    let mut folder: HashMap<Uuid, (i64, i64, i64)> = HashMap::new();
    let mut job: HashMap<Uuid, (i64, i64, i64)> = HashMap::new();

    // Zero-baseline first: every enumerable key gets a (0, 0, 0) entry so drained keys still
    // reset. Centicore sums are folded on top below, then converted once at the end.
    for &k in &baseline.subs {
        sub.entry(k).or_default();
    }
    for &k in &baseline.folders {
        folder.entry(k).or_default();
    }
    for &k in &baseline.jobs {
        job.entry(k).or_default();
    }

    // Accumulate centicores (cores) / whole counts (gpus, slots); convert cores to whole
    // cores after summing so truncation happens once. Slots are already whole counts.
    for r in rows {
        let s = sub.entry((r.show_id, r.alloc_id)).or_default();
        s.0 += r.cores;
        s.1 += r.gpus;
        s.2 += r.slots;
        let f = folder.entry(r.folder_id).or_default();
        f.0 += r.cores;
        f.1 += r.gpus;
        f.2 += r.slots;
        let j = job.entry(r.job_id).or_default();
        j.0 += r.cores;
        j.1 += r.gpus;
        j.2 += r.slots;
    }

    CounterSnapshot {
        sub: to_cores(sub),
        folder: to_cores(folder),
        job: to_cores(job),
    }
}

/// Convert each key's accumulated centicore total to cores (GPUs and slots pass through as
/// whole counts).
fn to_cores<K: std::hash::Hash + Eq>(
    m: HashMap<K, (i64, i64, i64)>,
) -> HashMap<K, (i64, i64, i64)> {
    m.into_iter()
        .map(|(k, (cores, gpus, slots))| (k, (centicores_to_cores(cores), gpus, slots)))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture_row() -> BookedSnapshotRow {
        // PG-shaped: `cores` is centicores per SUM(proc.int_cores_reserved). 4200 = 42 cores.
        BookedSnapshotRow {
            show_id: Uuid::nil(),
            alloc_id: Uuid::nil(),
            folder_id: Uuid::nil(),
            job_id: Uuid::nil(),
            cores: 4200,
            gpus: 3,
            slots: 5,
        }
    }

    fn empty_baseline() -> BaselineKeys {
        BaselineKeys::default()
    }

    #[test]
    fn single_row_converts_centicores_to_cores() {
        let snap = snapshot_to_counters(&[fixture_row()], &empty_baseline());
        assert_eq!(snap.sub[&(Uuid::nil(), Uuid::nil())], (42, 3, 5));
        assert_eq!(snap.folder[&Uuid::nil()], (42, 3, 5));
        assert_eq!(snap.job[&Uuid::nil()], (42, 3, 5));
    }

    /// Two jobs in the same folder/sub: the coarse keys SUM across rows (not last-write).
    #[test]
    fn sums_coarse_keys_across_per_job_rows() {
        let show = Uuid::new_v4();
        let alloc = Uuid::new_v4();
        let folder = Uuid::new_v4();
        let row_a = BookedSnapshotRow {
            show_id: show,
            alloc_id: alloc,
            folder_id: folder,
            job_id: Uuid::new_v4(),
            cores: 1000, // 10 cores
            gpus: 1,
            slots: 2,
        };
        let row_b = BookedSnapshotRow {
            cores: 2500, // 25 cores
            gpus: 2,
            job_id: Uuid::new_v4(),
            ..row_a.clone()
        };
        let snap = snapshot_to_counters(&[row_a, row_b], &empty_baseline());
        // 3500 centicores summed then /100 -> 35 cores; gpus 3; slots 2+2=4.
        assert_eq!(snap.sub[&(show, alloc)], (35, 3, 4));
        assert_eq!(snap.folder[&folder], (35, 3, 4));
    }

    /// A baseline key with no proc row (drained to zero) must reset to 0.
    #[test]
    fn baseline_key_absent_from_snapshot_resets_to_zero() {
        let job = Uuid::new_v4();
        let baseline = BaselineKeys {
            jobs: vec![job],
            ..Default::default()
        };
        let snap = snapshot_to_counters(&[], &baseline);
        assert_eq!(snap.job[&job], (0, 0, 0));
    }
}
