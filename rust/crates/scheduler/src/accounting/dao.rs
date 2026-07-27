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

/// Single PG-side DAO for the in-memory accounting module. Owns:
/// - the managed-shows lookup that drives the in-process cache,
/// - the `SUM(proc)` snapshot used by the booked-counter recompute,
/// - per-table reads of the enforced caps used by the limit reseed (subscription burst,
///   folder/job max cores+gpus).
pub struct AccountingDao {
    connection_pool: Arc<Pool<Postgres>>,
}

/// One row from the `SUM(proc)` snapshot used by the recompute loop, grouped by the three
/// enforced vertices (subscription via show+alloc, folder, job).
#[derive(Debug, Clone)]
pub struct BookedSnapshotRow {
    pub show_id: Uuid,
    pub alloc_id: Uuid,
    pub folder_id: Uuid,
    pub job_id: Uuid,
    pub cores: i64,
    pub gpus: i64,
    pub slots: i64,
}

/// The full universe of enumerable accounting keys for scheduler-managed shows, used by
/// the recompute to seed zero baselines. A key present here but absent from the
/// `SUM(proc)` snapshot has no procs, so its booked counter must reset to 0 - otherwise a
/// counter that drifted stale-high and then drained to zero procs would never converge
/// (the snapshot only returns keys that still have procs).
#[derive(Debug, Clone, Default)]
pub struct BaselineKeys {
    pub subs: Vec<(Uuid, Uuid)>,
    pub folders: Vec<Uuid>,
    pub jobs: Vec<Uuid>,
}

#[derive(Debug, Clone)]
pub struct SubscriptionLimitsRow {
    pub show_id: Uuid,
    pub alloc_id: Uuid,
    pub burst: i64,
    pub max_slots: i64,
}

#[derive(Debug, Clone)]
pub struct FolderLimitsRow {
    pub folder_id: Uuid,
    pub max_cores: i64,
    pub max_gpus: i64,
    pub max_slots: i64,
}

#[derive(Debug, Clone)]
pub struct JobLimitsRow {
    pub job_id: Uuid,
    pub max_cores: i64,
    pub max_gpus: i64,
    pub max_slots: i64,
}

static QUERY_MANAGED_SHOW_IDS: &str = r#"
    SELECT pk_show FROM show WHERE b_scheduler_managed = true
"#;

/// One snapshot row per (show, alloc, folder, job) tuple of bookings. Filtered to
/// scheduler-managed shows; excludes local procs. Joins through host to derive `pk_alloc`
/// per the same path Cuebot uses.
///
/// Why `b_local=false`: the scheduler never books local procs, and Cuebot's `procDestroyed`
/// skips the release NOTIFY on the local branch, so recompute must match to avoid creating
/// drift the hot path can't repair. Local dispatch is accounted for separately via
/// `job_resource.int_local_cores`, not the show-wide caps the scheduler enforces.
static QUERY_BOOKED: &str = r#"
    SELECT j.pk_show, h.pk_alloc, j.pk_folder, p.pk_job,
           COALESCE(SUM(p.int_cores_reserved), 0)::bigint as cores,
           COALESCE(SUM(p.int_gpus_reserved),  0)::bigint as gpus,
           COALESCE(SUM(p.int_slots_reserved), 0)::bigint as slots
    FROM proc p
    JOIN host h ON h.pk_host = p.pk_host
    JOIN job  j ON j.pk_job  = p.pk_job AND j.str_state <> 'FINISHED'
    JOIN show s ON s.pk_show = j.pk_show AND s.b_scheduler_managed = true
    WHERE p.b_local = false
    GROUP BY j.pk_show, h.pk_alloc, j.pk_folder, p.pk_job
"#;

/// Same shape as `QUERY_BOOKED` but scoped to one show, for the managed-flip booked-counter
/// seed. Not gated on `b_scheduler_managed` (the caller already knows the show is flipping).
static QUERY_BOOKED_FOR_SHOW: &str = r#"
    SELECT h.pk_alloc, j.pk_folder, p.pk_job,
           COALESCE(SUM(p.int_cores_reserved), 0)::bigint as cores,
           COALESCE(SUM(p.int_gpus_reserved),  0)::bigint as gpus,
           COALESCE(SUM(p.int_slots_reserved), 0)::bigint as slots
    FROM proc p
    JOIN host h ON h.pk_host = p.pk_host
    JOIN job  j ON j.pk_job  = p.pk_job AND j.str_state <> 'FINISHED'
    WHERE p.b_local = false AND j.pk_show = $1
    GROUP BY h.pk_alloc, j.pk_folder, p.pk_job
"#;

static QUERY_SUBSCRIPTION_LIMITS: &str = r#"
    SELECT s.pk_show, s.pk_alloc, s.int_burst, s.int_max_slots
    FROM subscription s
    JOIN show sh ON sh.pk_show = s.pk_show AND sh.b_scheduler_managed = true
"#;

static QUERY_FOLDER_LIMITS: &str = r#"
    SELECT fr.pk_folder, fr.int_max_cores, fr.int_max_gpus, fr.int_max_slots
    FROM folder_resource fr
    JOIN folder f ON f.pk_folder = fr.pk_folder
    JOIN show   s ON s.pk_show   = f.pk_show AND s.b_scheduler_managed = true
"#;

static QUERY_JOB_LIMITS: &str = r#"
    SELECT jr.pk_job, jr.int_max_cores, jr.int_max_gpus, jr.int_max_slots
    FROM job_resource jr
    JOIN job  j ON j.pk_job  = jr.pk_job AND j.str_state <> 'FINISHED'
    JOIN show s ON s.pk_show = j.pk_show AND s.b_scheduler_managed = true
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
            cores: i64,
            gpus: i64,
            slots: i64,
        }
        let rows: Vec<Row> = sqlx::query_as(QUERY_BOOKED)
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
                cores: r.cores,
                gpus: r.gpus,
                slots: r.slots,
            })
            .collect())
    }

    /// Booked snapshot for a single show (managed-flip seed). `show_id` fills the row's
    /// `show_id` since the query keys it by parameter rather than selecting `pk_show`.
    pub async fn query_booked_snapshot_for_show(
        &self,
        show_id: Uuid,
    ) -> Result<Vec<BookedSnapshotRow>> {
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_alloc: String,
            pk_folder: String,
            pk_job: String,
            cores: i64,
            gpus: i64,
            slots: i64,
        }
        let rows: Vec<Row> = sqlx::query_as(QUERY_BOOKED_FOR_SHOW)
            .bind(show_id.to_string())
            .fetch_all(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to query booked snapshot for show")?;
        Ok(rows
            .into_iter()
            .map(|r| BookedSnapshotRow {
                show_id,
                alloc_id: parse_uuid(&r.pk_alloc),
                folder_id: parse_uuid(&r.pk_folder),
                job_id: parse_uuid(&r.pk_job),
                cores: r.cores,
                gpus: r.gpus,
                slots: r.slots,
            })
            .collect())
    }

    /// Enumerate the full set of sub/folder/job keys for scheduler-managed shows, by
    /// projecting the key tuples out of the three limit queries. Reusing the limit queries
    /// (rather than dedicated key-only SELECTs) guarantees this key universe is
    /// grain-consistent with both the limit reseed and the booked snapshot (same
    /// `b_scheduler_managed` / `str_state <> 'FINISHED'` filters).
    pub async fn query_booked_baseline_keys(&self) -> Result<BaselineKeys> {
        let (subs, folders, jobs) = tokio::try_join!(
            self.query_subscription_limits(),
            self.query_folder_limits(),
            self.query_job_limits(),
        )?;
        Ok(BaselineKeys {
            subs: subs.iter().map(|r| (r.show_id, r.alloc_id)).collect(),
            folders: folders.iter().map(|r| r.folder_id).collect(),
            jobs: jobs.iter().map(|r| r.job_id).collect(),
        })
    }

    pub async fn query_subscription_limits(&self) -> Result<Vec<SubscriptionLimitsRow>> {
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_show: String,
            pk_alloc: String,
            int_burst: i64,
            int_max_slots: i32,
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
                burst: r.int_burst,
                max_slots: i64::from(r.int_max_slots),
            })
            .collect())
    }

    pub async fn query_folder_limits(&self) -> Result<Vec<FolderLimitsRow>> {
        // folder_resource columns are INT (i32); widen to i64 for store arithmetic.
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_folder: String,
            int_max_cores: i32,
            int_max_gpus: i32,
            int_max_slots: i32,
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
                max_cores: i64::from(r.int_max_cores),
                max_gpus: i64::from(r.int_max_gpus),
                max_slots: i64::from(r.int_max_slots),
            })
            .collect())
    }

    pub async fn query_job_limits(&self) -> Result<Vec<JobLimitsRow>> {
        // job_resource columns are INT (i32); widen to i64 for store arithmetic.
        #[derive(sqlx::FromRow)]
        struct Row {
            pk_job: String,
            int_max_cores: i32,
            int_max_gpus: i32,
            int_max_slots: i32,
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
                max_slots: i64::from(r.int_max_slots),
            })
            .collect())
    }
}
