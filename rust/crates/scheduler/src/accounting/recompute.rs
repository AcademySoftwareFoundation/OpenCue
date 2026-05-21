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

//! Booked-counter recompute loop. Every `CONFIG.accounting.recompute_interval`:
//!
//! 1. PG side (durable, unconditional): the four existing `RECOMPUTE_*_FROM_PROC`
//!    UPDATEs in `ResourceAccountingDao::recompute_all_from_proc` are run
//!    concurrently and committed transactionally. These keep the PG accounting
//!    tables (Cuegui's view) within ~2 min of `proc` for scheduler-managed shows.
//! 2. Redis side (CAS-guarded): a single unified `SUM(proc)` snapshot
//!    keyed by (show, alloc, folder, job, layer, dept) is converted to `HSET` ops
//!    on `int_cores`/`int_gpus` fields of the five `acct:*` hashes. Sent in one
//!    `RESEED_CAS` Lua call; on CAS miss the snapshot is recomputed and retried
//!    up to `CONFIG.accounting.cas_max_retries` times. On budget exhaustion the
//!    cycle is skipped (hot-path writes are keeping Redis fresh, per §2.4).
//!
//! PG writes are independent of Redis writes - even if Redis CAS keeps missing,
//! PG converges. They are decoupled stores by design §2.1.

use std::panic::AssertUnwindSafe;
use std::sync::Arc;

use futures::FutureExt;
use miette::{IntoDiagnostic, Result, WrapErr};
use tokio::time;
use tracing::{debug, error, info, warn};

use crate::accounting::dao::BookedSnapshotRow;
use crate::accounting::redis_client::ReseedOp;
use crate::accounting::AccountingService;
use crate::config::CONFIG;
use crate::dao::ResourceAccountingDao;

pub fn spawn_loop(service: Arc<AccountingService>) {
    tokio::spawn(async move {
        let pg_dao = match ResourceAccountingDao::new().await {
            Ok(d) => Arc::new(d),
            Err(err) => {
                error!("Recompute loop aborting: PG dao init failed: {err}");
                return;
            }
        };
        let mut interval = time::interval(CONFIG.accounting.recompute_interval);
        // Skip the immediate first tick - bootstrap reseed already ran at startup.
        interval.tick().await;
        loop {
            interval.tick().await;
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

/// One pass: PG recompute (unconditional) + Redis reseed (CAS-guarded).
async fn run_once(service: &AccountingService, pg_dao: &Arc<ResourceAccountingDao>) -> Result<()> {
    debug!("Recompute cycle: starting");

    // PG side: durable, scoped to scheduler-managed shows. Empty list is a no-op
    // inside the DAO so we never widen to all shows and clobber Cuebot's accounting.
    let managed_ids: Vec<uuid::Uuid> = service.managed_shows().snapshot().into_iter().collect();
    if managed_ids.is_empty() {
        debug!("PG recompute skipped: no scheduler-managed shows");
    } else {
        if let Err(err) = pg_dao.recompute_all_from_proc(&managed_ids).await {
            warn!(
                "PG recompute (layer/job/folder/point) failed (Redis reseed will still run): {err}"
            );
        }
        if let Err(err) = pg_dao.recompute_subscription_table(&managed_ids).await {
            warn!("PG subscription recompute failed (Redis reseed will still run): {err}");
        }
    }

    // Redis side: CAS-guarded.
    reseed_redis_once(service).await
}

/// CAS-guarded reseed of the booked-counter fields (`int_cores`/`int_gpus`) on the
/// five `acct:*` hashes from a fresh `SUM(proc)` snapshot. Used by both the recompute
/// loop and the bootstrap. On CAS-budget exhaustion: warn and return Ok (per §2.4).
pub async fn reseed_redis_once(service: &AccountingService) -> Result<()> {
    let max_retries = CONFIG.accounting.cas_max_retries;
    for attempt in 0..=max_retries {
        let seq_before = service.redis().get_seq().await.into_diagnostic()?;
        let rows = service.dao().query_booked_snapshot().await?;
        let ops = booked_ops_from_snapshot(&rows);
        debug!(
            "Recompute reseed attempt {}/{}: {} rows -> {} ops at seq={}",
            attempt + 1,
            max_retries + 1,
            rows.len(),
            ops.len(),
            seq_before
        );
        let applied = service
            .redis()
            .reseed_cas(seq_before, &ops)
            .await
            .into_diagnostic()
            .wrap_err("RESEED_CAS for booked counters failed")?;
        if applied {
            info!(
                "Recompute reseed applied: {} ops, seq={}",
                ops.len(),
                seq_before
            );
            return Ok(());
        }
        warn!(
            "Recompute reseed CAS miss (attempt {}/{}); resnapshot and retry",
            attempt + 1,
            max_retries + 1
        );
    }
    warn!(
        "Recompute reseed exhausted {} CAS retries; cycle skipped (hot-path writes are \
         keeping Redis fresh, per design §2.4)",
        max_retries + 1
    );
    Ok(())
}

/// Aggregate one `SUM(proc)` snapshot into HSET ops, one set of ops per unique key.
///
/// The SQL groups by `(show, alloc, folder, job, layer, dept)` - a finer granularity
/// than any of the Redis keys. A folder with several jobs, or a job whose procs span
/// multiple allocations, produces several snapshot rows that all map to the same
/// `acct:folder:{folder}` (or `acct:job:{job}`, etc.) key. Because `RESEED_CAS` does
/// `HSET` (overwrite) rather than `HINCRBY`, emitting one op per row would let later
/// rows clobber earlier ones - the final value would be whichever row sorted last,
/// not the sum across rows. Aggregate first, emit once per unique key.
fn booked_ops_from_snapshot(rows: &[BookedSnapshotRow]) -> Vec<ReseedOp> {
    use std::collections::HashMap;

    let mut sub_totals: HashMap<(uuid::Uuid, uuid::Uuid), (i64, i64)> = HashMap::new();
    let mut folder_totals: HashMap<uuid::Uuid, (i64, i64)> = HashMap::new();
    let mut job_totals: HashMap<uuid::Uuid, (i64, i64)> = HashMap::new();
    let mut layer_totals: HashMap<uuid::Uuid, (i64, i64)> = HashMap::new();
    let mut point_totals: HashMap<(uuid::Uuid, uuid::Uuid), (i64, i64)> = HashMap::new();

    for r in rows {
        let s = sub_totals.entry((r.show_id, r.alloc_id)).or_default();
        s.0 += r.cores;
        s.1 += r.gpus;
        let f = folder_totals.entry(r.folder_id).or_default();
        f.0 += r.cores;
        f.1 += r.gpus;
        let j = job_totals.entry(r.job_id).or_default();
        j.0 += r.cores;
        j.1 += r.gpus;
        let l = layer_totals.entry(r.layer_id).or_default();
        l.0 += r.cores;
        l.1 += r.gpus;
        let p = point_totals.entry((r.dept_id, r.show_id)).or_default();
        p.0 += r.cores;
        p.1 += r.gpus;
    }

    let total_keys = sub_totals.len()
        + folder_totals.len()
        + job_totals.len()
        + layer_totals.len()
        + point_totals.len();
    let mut ops = Vec::with_capacity(total_keys * 2);

    fn push_pair(ops: &mut Vec<ReseedOp>, key: String, cores: i64, gpus: i64) {
        ops.push(ReseedOp {
            key: key.clone(),
            field: "int_cores",
            value: cores,
        });
        ops.push(ReseedOp {
            key,
            field: "int_gpus",
            value: gpus,
        });
    }

    for ((show_id, alloc_id), (cores, gpus)) in sub_totals {
        push_pair(
            &mut ops,
            format!("acct:sub:{}:{}", show_id, alloc_id),
            cores,
            gpus,
        );
    }
    for (folder_id, (cores, gpus)) in folder_totals {
        push_pair(&mut ops, format!("acct:folder:{}", folder_id), cores, gpus);
    }
    for (job_id, (cores, gpus)) in job_totals {
        push_pair(&mut ops, format!("acct:job:{}", job_id), cores, gpus);
    }
    for (layer_id, (cores, gpus)) in layer_totals {
        push_pair(&mut ops, format!("acct:layer:{}", layer_id), cores, gpus);
    }
    for ((dept_id, show_id), (cores, gpus)) in point_totals {
        push_pair(
            &mut ops,
            format!("acct:point:{}:{}", dept_id, show_id),
            cores,
            gpus,
        );
    }
    ops
}

#[cfg(test)]
mod tests {
    use super::*;
    use uuid::Uuid;

    fn fixture_row() -> BookedSnapshotRow {
        BookedSnapshotRow {
            show_id: Uuid::nil(),
            alloc_id: Uuid::nil(),
            folder_id: Uuid::nil(),
            job_id: Uuid::nil(),
            layer_id: Uuid::nil(),
            dept_id: Uuid::nil(),
            cores: 42,
            gpus: 3,
        }
    }

    fn find_op<'a>(ops: &'a [ReseedOp], key: &str, field: &str) -> &'a ReseedOp {
        ops.iter()
            .find(|o| o.key == key && o.field == field)
            .unwrap_or_else(|| panic!("no op for key={key} field={field}"))
    }

    fn count_ops_for_key(ops: &[ReseedOp], key: &str) -> usize {
        ops.iter().filter(|o| o.key == key).count()
    }

    #[test]
    fn snapshot_single_row_expands_to_ten_ops() {
        let ops = booked_ops_from_snapshot(&[fixture_row()]);
        // 5 unique keys × 2 fields (int_cores, int_gpus).
        assert_eq!(ops.len(), 10);
        let cores_ops: Vec<_> = ops.iter().filter(|o| o.field == "int_cores").collect();
        let gpus_ops: Vec<_> = ops.iter().filter(|o| o.field == "int_gpus").collect();
        assert_eq!(cores_ops.len(), 5);
        assert_eq!(gpus_ops.len(), 5);
        assert!(cores_ops.iter().all(|o| o.value == 42));
        assert!(gpus_ops.iter().all(|o| o.value == 3));
    }

    #[test]
    fn snapshot_keys_match_publisher_format() {
        let ops = booked_ops_from_snapshot(&[fixture_row()]);
        let keys: std::collections::HashSet<&str> = ops.iter().map(|o| o.key.as_str()).collect();
        assert!(keys.contains(
            "acct:sub:00000000-0000-0000-0000-000000000000:00000000-0000-0000-0000-000000000000"
        ));
        assert!(keys.contains("acct:folder:00000000-0000-0000-0000-000000000000"));
        assert!(keys.contains("acct:job:00000000-0000-0000-0000-000000000000"));
        assert!(keys.contains("acct:layer:00000000-0000-0000-0000-000000000000"));
        assert!(keys.contains(
            "acct:point:00000000-0000-0000-0000-000000000000:00000000-0000-0000-0000-000000000000"
        ));
    }

    /// Two jobs in the same folder, same sub, same point. The coarse counters must
    /// SUM across the per-job snapshot rows, not pick "last write wins."
    #[test]
    fn snapshot_sums_coarse_keys_across_per_job_rows() {
        let show = Uuid::new_v4();
        let alloc = Uuid::new_v4();
        let folder = Uuid::new_v4();
        let dept = Uuid::new_v4();
        let row_a = BookedSnapshotRow {
            show_id: show,
            alloc_id: alloc,
            folder_id: folder,
            job_id: Uuid::new_v4(),
            layer_id: Uuid::new_v4(),
            dept_id: dept,
            cores: 10,
            gpus: 1,
        };
        let row_b = BookedSnapshotRow {
            show_id: show,
            alloc_id: alloc,
            folder_id: folder,
            job_id: Uuid::new_v4(),
            layer_id: Uuid::new_v4(),
            dept_id: dept,
            cores: 25,
            gpus: 2,
        };

        let ops = booked_ops_from_snapshot(&[row_a, row_b]);

        let sub_key = format!("acct:sub:{}:{}", show, alloc);
        assert_eq!(find_op(&ops, &sub_key, "int_cores").value, 35);
        assert_eq!(find_op(&ops, &sub_key, "int_gpus").value, 3);
        assert_eq!(count_ops_for_key(&ops, &sub_key), 2);

        let folder_key = format!("acct:folder:{}", folder);
        assert_eq!(find_op(&ops, &folder_key, "int_cores").value, 35);
        assert_eq!(find_op(&ops, &folder_key, "int_gpus").value, 3);
        assert_eq!(count_ops_for_key(&ops, &folder_key), 2);

        let point_key = format!("acct:point:{}:{}", dept, show);
        assert_eq!(find_op(&ops, &point_key, "int_cores").value, 35);
        assert_eq!(find_op(&ops, &point_key, "int_gpus").value, 3);
        assert_eq!(count_ops_for_key(&ops, &point_key), 2);
    }

    /// One job whose procs span two allocations. The job and layer counters must sum
    /// across the two snapshot rows, while the two sub counters are independent.
    #[test]
    fn snapshot_sums_job_and_layer_across_allocations() {
        let show = Uuid::new_v4();
        let folder = Uuid::new_v4();
        let dept = Uuid::new_v4();
        let job = Uuid::new_v4();
        let layer = Uuid::new_v4();
        let alloc_a = Uuid::new_v4();
        let alloc_b = Uuid::new_v4();
        let rows = [
            BookedSnapshotRow {
                show_id: show,
                alloc_id: alloc_a,
                folder_id: folder,
                job_id: job,
                layer_id: layer,
                dept_id: dept,
                cores: 10,
                gpus: 0,
            },
            BookedSnapshotRow {
                show_id: show,
                alloc_id: alloc_b,
                folder_id: folder,
                job_id: job,
                layer_id: layer,
                dept_id: dept,
                cores: 7,
                gpus: 0,
            },
        ];

        let ops = booked_ops_from_snapshot(&rows);

        let job_key = format!("acct:job:{}", job);
        assert_eq!(find_op(&ops, &job_key, "int_cores").value, 17);
        assert_eq!(count_ops_for_key(&ops, &job_key), 2);

        let layer_key = format!("acct:layer:{}", layer);
        assert_eq!(find_op(&ops, &layer_key, "int_cores").value, 17);
        assert_eq!(count_ops_for_key(&ops, &layer_key), 2);

        // Sub counters stay per-allocation.
        let sub_a = format!("acct:sub:{}:{}", show, alloc_a);
        let sub_b = format!("acct:sub:{}:{}", show, alloc_b);
        assert_eq!(find_op(&ops, &sub_a, "int_cores").value, 10);
        assert_eq!(find_op(&ops, &sub_b, "int_cores").value, 7);
    }
}
