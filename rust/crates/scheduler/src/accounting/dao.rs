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

use std::sync::Arc;

use miette::{Context, IntoDiagnostic, Result};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::dao::helpers::parse_uuid;
use crate::pgpool::connection_pool;

/// Single PG-side DAO for the Redis-backed accounting module. Owns:
/// - the managed-shows lookup that drives the in-process cache,
/// - the unified SUM(proc) snapshot used by the booked-counter recompute,
/// - per-table limit-field reads used by the limit reseed (subscription burst/size,
///   folder/job caps, point min/max).
pub struct AccountingDao {
    connection_pool: Arc<Pool<Postgres>>,
}

/// One row from the unified SUM(proc) snapshot used by the recompute loop.
#[derive(Debug, Clone)]
pub struct BookedSnapshotRow {
    pub show_id: Uuid,
    pub alloc_id: Uuid,
    pub folder_id: Uuid,
    pub job_id: Uuid,
    pub layer_id: Uuid,
    pub dept_id: Uuid,
    pub cores: i64,
    pub gpus: i64,
}

/// The full universe of enumerable accounting keys for scheduler-managed shows,
/// used by the booked-counter recompute to seed zero baselines. A key present here
/// but absent from the `SUM(proc)` snapshot has no procs, so its booked counter must
/// be reset to 0 - otherwise a counter that drifted stale-high and then drained to
/// zero procs would never converge (the snapshot only returns keys that still have
/// procs). Layer keys are intentionally absent: layers have no limit table to
/// enumerate from, and the booking Lua never reads the layer counter (it is
/// `HINCRBY`-only), so residual layer drift is cosmetic. See `recompute.rs`.
#[derive(Debug, Clone, Default)]
pub struct BaselineKeys {
    pub subs: Vec<(Uuid, Uuid)>,
    pub folders: Vec<Uuid>,
    pub jobs: Vec<Uuid>,
    pub points: Vec<(Uuid, Uuid)>,
}

#[derive(Debug, Clone)]
pub struct SubscriptionLimitsRow {
    pub show_id: Uuid,
    pub alloc_id: Uuid,
    pub size: i64,
    pub burst: i64,
}

#[derive(Debug, Clone)]
pub struct FolderLimitsRow {
    pub folder_id: Uuid,
    pub min_cores: i64,
    pub max_cores: i64,
    pub min_gpus: i64,
    pub max_gpus: i64,
}

#[derive(Debug, Clone)]
pub struct JobLimitsRow {
    pub job_id: Uuid,
    pub max_cores: i64,
    pub max_gpus: i64,
    pub priority: i64,
}

#[derive(Debug, Clone)]
pub struct PointLimitsRow {
    pub dept_id: Uuid,
    pub show_id: Uuid,
    pub min_cores: i64,
    pub min_gpus: i64,
}

static QUERY_MANAGED_SHOW_IDS: &str = r#"
    SELECT pk_show FROM show WHERE b_scheduler_managed = true
"#;

/// One snapshot row per (show, alloc, folder, job, layer, dept) tuple of bookings.
/// Filtered to scheduler-managed shows; excludes local procs. Joins through host to
/// derive `pk_alloc` per the same path Cuebot uses.
///
/// Why `b_local=false`: the Redis hot path is naturally non-local-only - the Rust
/// scheduler never books local procs, and Cuebot's `procDestroyed` skips Redis
/// publishing on the local branch. Recompute must match that to avoid creating
/// drift the hot path can't repair. Consequence: for a scheduler-managed show with
/// locals, `acct:layer:{layer}.int_cores` under-counts vs `layer_resource.int_cores`
/// in PG (Cuegui's view still includes locals via the existing PG recompute that
/// doesn't filter). A layer "full" with locals could still accept non-local
/// bookings via the Lua cap check - acceptable per design §4.4 because local
/// dispatch is rare and intentionally accounted for via `job_resource.int_local_cores`
/// rather than the show-wide caps.
static QUERY_BOOKED_BY_5DIM: &str = r#"
    SELECT j.pk_show, h.pk_alloc, j.pk_folder, p.pk_job, p.pk_layer, j.pk_dept,
           COALESCE(SUM(p.int_cores_reserved), 0)::bigint as cores,
           COALESCE(SUM(p.int_gpus_reserved),  0)::bigint as gpus
    FROM proc p
    JOIN host h ON h.pk_host = p.pk_host
    JOIN job  j ON j.pk_job  = p.pk_job AND j.str_state <> 'FINISHED'
    JOIN show s ON s.pk_show = j.pk_show AND s.b_scheduler_managed = true
    WHERE p.b_local = false
    GROUP BY j.pk_show, h.pk_alloc, j.pk_folder, p.pk_job, p.pk_layer, j.pk_dept
"#;

static QUERY_SUBSCRIPTION_LIMITS: &str = r#"
    SELECT s.pk_show, s.pk_alloc, s.int_size, s.int_burst
    FROM subscription s
    JOIN show sh ON sh.pk_show = s.pk_show AND sh.b_scheduler_managed = true
"#;

static QUERY_FOLDER_LIMITS: &str = r#"
    SELECT fr.pk_folder,
           fr.int_min_cores, fr.int_max_cores,
           fr.int_min_gpus,  fr.int_max_gpus
    FROM folder_resource fr
    JOIN folder f ON f.pk_folder = fr.pk_folder
    JOIN show   s ON s.pk_show   = f.pk_show AND s.b_scheduler_managed = true
"#;

static QUERY_JOB_LIMITS: &str = r#"
    SELECT jr.pk_job, jr.int_max_cores, jr.int_max_gpus, jr.int_priority
    FROM job_resource jr
    JOIN job  j ON j.pk_job  = jr.pk_job AND j.str_state <> 'FINISHED'
    JOIN show s ON s.pk_show = j.pk_show AND s.b_scheduler_managed = true
"#;

// `point` has `int_min_cores`/`int_min_gpus` but no `int_max_*` columns - points enforce a
// floor, not a ceiling. The design doc §2.3 lists `int_max_cores` in the `acct:point`
// HASH for symmetry, but the schema doesn't back it; we don't populate or read it.
static QUERY_POINT_LIMITS: &str = r#"
    SELECT pt.pk_dept, pt.pk_show, pt.int_min_cores, pt.int_min_gpus
    FROM point pt
    JOIN show s ON s.pk_show = pt.pk_show AND s.b_scheduler_managed = true
"#;

impl AccountingDao {
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(AccountingDao {
            connection_pool: pool,
        })
    }

    pub async fn query_managed_show_ids(&self) -> Result<Vec<Uuid>> {
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_show: String,
        }
        let rows: Vec<Row> = sqlx::query_as(QUERY_MANAGED_SHOW_IDS)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to query managed show ids")?;
        Ok(rows.iter().map(|r| parse_uuid(&r.pk_show)).collect())
    }

    pub async fn query_booked_snapshot(&self) -> Result<Vec<BookedSnapshotRow>> {
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_show: String,
            pk_alloc: String,
            pk_folder: String,
            pk_job: String,
            pk_layer: String,
            pk_dept: String,
            cores: i64,
            gpus: i64,
        }
        let rows: Vec<Row> = sqlx::query_as(QUERY_BOOKED_BY_5DIM)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to query booked snapshot from proc")?;

        Ok(rows
            .into_iter()
            .map(|r| BookedSnapshotRow {
                show_id: parse_uuid(&r.pk_show),
                alloc_id: parse_uuid(&r.pk_alloc),
                folder_id: parse_uuid(&r.pk_folder),
                job_id: parse_uuid(&r.pk_job),
                layer_id: parse_uuid(&r.pk_layer),
                dept_id: parse_uuid(&r.pk_dept),
                cores: r.cores,
                gpus: r.gpus,
            })
            .collect())
    }

    /// Enumerate the full set of sub/folder/job/point keys for scheduler-managed
    /// shows, by projecting the key tuples out of the four limit queries. Reusing the
    /// limit queries (rather than dedicated key-only SELECTs) guarantees this key
    /// universe is grain-consistent with both the limit reseed and the booked snapshot
    /// (same `b_scheduler_managed` / `str_state <> 'FINISHED'` filters). Layer keys are
    /// not enumerable from a limit table, so they are absent here by design.
    pub async fn query_booked_baseline_keys(&self) -> Result<BaselineKeys> {
        let (subs, folders, jobs, points) = tokio::try_join!(
            self.query_subscription_limits(),
            self.query_folder_limits(),
            self.query_job_limits(),
            self.query_point_limits(),
        )?;
        Ok(BaselineKeys {
            subs: subs.iter().map(|r| (r.show_id, r.alloc_id)).collect(),
            folders: folders.iter().map(|r| r.folder_id).collect(),
            jobs: jobs.iter().map(|r| r.job_id).collect(),
            points: points.iter().map(|r| (r.dept_id, r.show_id)).collect(),
        })
    }

    pub async fn query_subscription_limits(&self) -> Result<Vec<SubscriptionLimitsRow>> {
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_show: String,
            pk_alloc: String,
            int_size: i64,
            int_burst: i64,
        }
        let rows: Vec<Row> = sqlx::query_as(QUERY_SUBSCRIPTION_LIMITS)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to query subscription limits")?;
        Ok(rows
            .into_iter()
            .map(|r| SubscriptionLimitsRow {
                show_id: parse_uuid(&r.pk_show),
                alloc_id: parse_uuid(&r.pk_alloc),
                size: r.int_size,
                burst: r.int_burst,
            })
            .collect())
    }

    pub async fn query_folder_limits(&self) -> Result<Vec<FolderLimitsRow>> {
        // folder_resource columns are INT (i32); widen to i64 for Redis storage.
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_folder: String,
            int_min_cores: i32,
            int_max_cores: i32,
            int_min_gpus: i32,
            int_max_gpus: i32,
        }
        let rows: Vec<Row> = sqlx::query_as(QUERY_FOLDER_LIMITS)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to query folder limits")?;
        Ok(rows
            .into_iter()
            .map(|r| FolderLimitsRow {
                folder_id: parse_uuid(&r.pk_folder),
                min_cores: i64::from(r.int_min_cores),
                max_cores: i64::from(r.int_max_cores),
                min_gpus: i64::from(r.int_min_gpus),
                max_gpus: i64::from(r.int_max_gpus),
            })
            .collect())
    }

    pub async fn query_job_limits(&self) -> Result<Vec<JobLimitsRow>> {
        // job_resource columns are INT (i32); widen to i64 for Redis storage.
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_job: String,
            int_max_cores: i32,
            int_max_gpus: i32,
            int_priority: i32,
        }
        let rows: Vec<Row> = sqlx::query_as(QUERY_JOB_LIMITS)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to query job limits")?;
        Ok(rows
            .into_iter()
            .map(|r| JobLimitsRow {
                job_id: parse_uuid(&r.pk_job),
                max_cores: i64::from(r.int_max_cores),
                max_gpus: i64::from(r.int_max_gpus),
                priority: i64::from(r.int_priority),
            })
            .collect())
    }

    pub async fn query_point_limits(&self) -> Result<Vec<PointLimitsRow>> {
        // point columns are INT (i32); widen to i64 for Redis storage.
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_dept: String,
            pk_show: String,
            int_min_cores: i32,
            int_min_gpus: i32,
        }
        let rows: Vec<Row> = sqlx::query_as(QUERY_POINT_LIMITS)
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to query point limits")?;
        Ok(rows
            .into_iter()
            .map(|r| PointLimitsRow {
                dept_id: parse_uuid(&r.pk_dept),
                show_id: parse_uuid(&r.pk_show),
                min_cores: i64::from(r.int_min_cores),
                min_gpus: i64::from(r.int_min_gpus),
            })
            .collect())
    }
}
