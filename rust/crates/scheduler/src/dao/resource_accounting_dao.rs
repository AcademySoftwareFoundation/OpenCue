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

//! PG-side recompute queries that keep the accounting tables (layer_resource,
//! job_resource, folder_resource, point, subscription) within ~2 minutes of `proc`
//! for scheduler-managed shows. Driven by `accounting::recompute`.
//!
//! For Cuebot-managed shows, Cuebot's transactional `unbookProc` path updates these
//! same tables synchronously and `recalculate_subs()` runs every 2 hours - see PR-A
//! for the show-aware gating that prevents double-writes.

use std::sync::Arc;

use miette::{Context, IntoDiagnostic, Result};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::pgpool::connection_pool;

//== Recompute Layer Resource
//
// $1 is a non-empty list of scheduler-managed show IDs (Rust callers must early-return
// on empty). The filter is mandatory: never widen to all shows, or this loop will
// clobber accounting for Cuebot-managed shows.
static RECOMPUTE_LAYER_RESOURCE_FROM_PROC: &str = r#"
UPDATE layer_resource lr
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT lr2.pk_layer,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM layer_resource lr2
    LEFT JOIN proc p ON p.pk_layer = lr2.pk_layer
        AND p.pk_show = ANY($1)
    JOIN job j ON j.pk_job = lr2.pk_job AND j.str_state <> 'FINISHED'
        AND j.pk_show = ANY($1)
    GROUP BY lr2.pk_layer
) booked
WHERE lr.pk_layer = booked.pk_layer
  AND (lr.int_cores IS DISTINCT FROM COALESCE(booked.total_cores, 0)
    OR lr.int_gpus IS DISTINCT FROM COALESCE(booked.total_gpus, 0))
"#;

//== Recompute Job Resource

/// SQL to save original max-cores/max-gpus values before the trigger-bypass update.
/// $1 is a non-empty list of scheduler-managed show IDs.
static SELECT_JOB_RESOURCE_MAX: &str = r#"
    SELECT jr.pk_job_resource, jr.int_max_cores, jr.int_max_gpus
    FROM job_resource jr
    JOIN job j ON j.pk_job = jr.pk_job AND j.str_state <> 'FINISHED'
    WHERE j.pk_show = ANY($1)
"#;

/// Bulk-update job_resource booked cores/gpus with trigger bypass.
///
/// Sets `int_max_cores = total_cores` and `int_max_gpus = total_gpus` to prevent the
/// `verify_job_resources` trigger from raising an exception when
/// `int_cores > int_max_cores`. The trigger fires when
/// `NEW.int_max_cores = OLD.int_max_cores AND NEW.int_cores > OLD.int_cores`.
/// By changing `int_max_cores` in the same UPDATE, the trigger condition is not met.
static RECOMPUTE_JOB_RESOURCE_FROM_PROC: &str = r#"
UPDATE job_resource jr
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0),
    int_max_cores = COALESCE(booked.total_cores, 0),
    int_max_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT jr2.pk_job,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM job_resource jr2
    LEFT JOIN proc p ON p.pk_job = jr2.pk_job
        AND p.pk_show = ANY($1)
    JOIN job j ON j.pk_job = jr2.pk_job AND j.str_state <> 'FINISHED'
        AND j.pk_show = ANY($1)
    GROUP BY jr2.pk_job
) booked
WHERE jr.pk_job = booked.pk_job
  AND (jr.int_cores IS DISTINCT FROM COALESCE(booked.total_cores, 0)
    OR jr.int_gpus IS DISTINCT FROM COALESCE(booked.total_gpus, 0))
"#;

/// Restore original max-cores/max-gpus values after the trigger-bypass update.
static RESTORE_JOB_RESOURCE_MAX: &str = r#"
    UPDATE job_resource jr
    SET int_max_cores = restore.max_cores,
        int_max_gpus = restore.max_gpus
    FROM (SELECT unnest($1::text[]) AS id,
                 unnest($2::int[]) AS max_cores,
                 unnest($3::int[]) AS max_gpus) restore
    WHERE jr.pk_job_resource = restore.id
"#;

//=== Recompute Folder Resources
//
// LEFT JOIN job + LEFT JOIN proc so a folder with no managed-show jobs (or none with
// any booked procs) still appears in the subquery with SUM=NULL -> 0 - i.e., the row
// gets zeroed instead of left stale. Folders that host both managed and Cuebot shows
// end up reflecting only the managed-show portion; that's an inherent collision in
// the schema (folder_resource is per-folder, ownership is per-show) and Cuebot's
// recalculate_subs handles the Cuebot half separately.
static RECOMPUTE_FOLDER_RESOURCE_FROM_PROC: &str = r#"
UPDATE folder_resource fr
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT fr2.pk_folder,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM folder_resource fr2
    LEFT JOIN job j ON j.pk_folder = fr2.pk_folder AND j.str_state <> 'FINISHED'
        AND j.pk_show = ANY($1)
    LEFT JOIN proc p ON p.pk_job = j.pk_job
        AND p.pk_show = ANY($1)
    GROUP BY fr2.pk_folder
) booked
WHERE fr.pk_folder = booked.pk_folder
  AND (fr.int_cores IS DISTINCT FROM COALESCE(booked.total_cores, 0)
    OR fr.int_gpus IS DISTINCT FROM COALESCE(booked.total_gpus, 0))
"#;

//=== Recompute Points
//
// point rows are keyed by (pk_dept, pk_show), so the show filter on pt2.pk_show in
// the inner WHERE is what restricts the update to managed shows. The job join is left
// unfiltered by show because j.pk_dept + pt2.pk_show is the natural join key (jobs
// only roll up into a point row that matches their show), and adding j.pk_show =
// ANY($1) would be redundant.
static RECOMPUTE_POINT_FROM_PROC: &str = r#"
UPDATE point pt
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT pt2.pk_dept, pt2.pk_show,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM point pt2
    LEFT JOIN job j ON j.pk_dept = pt2.pk_dept AND j.str_state <> 'FINISHED'
    LEFT JOIN proc p ON p.pk_job = j.pk_job AND p.pk_show = pt2.pk_show
        AND p.pk_show = ANY($1)
    WHERE pt2.pk_show = ANY($1)
    GROUP BY pt2.pk_dept, pt2.pk_show
) booked
WHERE pt.pk_dept = booked.pk_dept
  AND pt.pk_show = booked.pk_show
  AND (pt.int_cores IS DISTINCT FROM COALESCE(booked.total_cores, 0)
    OR pt.int_gpus IS DISTINCT FROM COALESCE(booked.total_gpus, 0))
"#;

/// SQL to read all subscription IDs and their current burst values.
/// $1 is a non-empty list of scheduler-managed show IDs.
static SELECT_SUBSCRIPTION_BURSTS: &str = r#"
    SELECT pk_subscription, int_burst FROM subscription
    WHERE pk_show = ANY($1)
"#;

/// Bulk-update subscription booked cores/gpus with burst bypass.
///
/// Sets `int_burst = total_cores` to prevent the `verify_subscription` trigger from
/// raising an exception when `int_cores > int_burst`. The trigger fires when
/// `NEW.int_burst = OLD.int_burst AND NEW.int_cores > OLD.int_cores`.
/// By changing `int_burst` in the same UPDATE, the trigger condition is not met.
static RECOMPUTE_SUBSCRIPTION_FROM_PROC: &str = r#"
    UPDATE subscription s
    SET int_cores = booked.total_cores,
        int_gpus = booked.total_gpus,
        int_burst = booked.total_cores
    FROM (
        SELECT s2.pk_subscription,
               COALESCE(SUM(p.int_cores_reserved), 0)::int AS total_cores,
               COALESCE(SUM(p.int_gpus_reserved), 0)::int AS total_gpus
        FROM subscription s2
        LEFT JOIN host h ON h.pk_alloc = s2.pk_alloc
        LEFT JOIN proc p ON p.pk_host = h.pk_host
                        AND p.pk_show = s2.pk_show
                        AND p.b_local = false
                        AND p.pk_show = ANY($1)
        WHERE s2.pk_show = ANY($1)
        GROUP BY s2.pk_subscription
    ) booked
    WHERE s.pk_subscription = booked.pk_subscription
      AND (s.int_cores IS DISTINCT FROM booked.total_cores
        OR s.int_gpus IS DISTINCT FROM booked.total_gpus
        OR s.int_burst IS DISTINCT FROM booked.total_cores)
"#;

/// Restore original burst values after the burst-bypass update.
static RESTORE_SUBSCRIPTION_BURSTS: &str = r#"
    UPDATE subscription s
    SET int_burst = restore.burst
    FROM (SELECT unnest($1::text[]) AS id, unnest($2::bigint[]) AS burst) restore
    WHERE s.pk_subscription = restore.id
"#;

pub struct ResourceAccountingDao {
    connection_pool: Arc<Pool<Postgres>>,
}

impl ResourceAccountingDao {
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(ResourceAccountingDao {
            connection_pool: pool,
        })
    }

    /// Recomputes layer_resource, job_resource, folder_resource and point from `proc`
    /// for the given scheduler-managed shows. Runs the four UPDATEs concurrently.
    ///
    /// `managed_show_ids` must contain only shows where `b_scheduler_managed = true` -
    /// the SQL never widens to all shows. When the slice is empty (scheduler manages
    /// nothing), returns `Ok(())` without touching PG so we don't clobber Cuebot's
    /// transactional writes.
    pub async fn recompute_all_from_proc(&self, managed_show_ids: &[Uuid]) -> Result<()> {
        if managed_show_ids.is_empty() {
            return Ok(());
        }
        let show_id_strings: Vec<String> =
            managed_show_ids.iter().map(|id| id.to_string()).collect();
        let bind_value: &[String] = &show_id_strings;
        let pool = self.connection_pool.as_ref();

        tokio::try_join!(
            async {
                sqlx::query(RECOMPUTE_LAYER_RESOURCE_FROM_PROC)
                    .bind(bind_value)
                    .execute(pool)
                    .await
                    .into_diagnostic()
                    .wrap_err("Failed to recompute layer resource from proc")
            },
            self.recompute_job_resource_from_proc(bind_value),
            async {
                sqlx::query(RECOMPUTE_FOLDER_RESOURCE_FROM_PROC)
                    .bind(bind_value)
                    .execute(pool)
                    .await
                    .into_diagnostic()
                    .wrap_err("Failed to recompute folder resource from proc")
            },
            async {
                sqlx::query(RECOMPUTE_POINT_FROM_PROC)
                    .bind(bind_value)
                    .execute(pool)
                    .await
                    .into_diagnostic()
                    .wrap_err("Failed to recompute point from proc")
            },
        )?;

        Ok(())
    }

    /// Recomputes job_resource from `proc` using a transactional trigger bypass.
    ///
    /// 1. Read original max_cores/max_gpus values
    /// 2. Bulk update cores/gpus with trigger bypass (sets max = total to avoid
    ///    `verify_job_resources`)
    /// 3. Restore original max values
    async fn recompute_job_resource_from_proc(
        &self,
        bind_value: &[String],
    ) -> std::result::Result<(), miette::Report> {
        #[derive(sqlx::FromRow)]
        struct MaxRow {
            pk_job_resource: String,
            int_max_cores: i32,
            int_max_gpus: i32,
        }

        let mut tx = self
            .connection_pool
            .begin()
            .await
            .into_diagnostic()
            .wrap_err("Failed to begin transaction for job resource recompute")?;

        let max_rows: Vec<MaxRow> = sqlx::query_as(SELECT_JOB_RESOURCE_MAX)
            .bind(bind_value)
            .fetch_all(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to read job resource max values")?;

        let ids: Vec<String> = max_rows.iter().map(|r| r.pk_job_resource.clone()).collect();
        let max_cores: Vec<i32> = max_rows.iter().map(|r| r.int_max_cores).collect();
        let max_gpus: Vec<i32> = max_rows.iter().map(|r| r.int_max_gpus).collect();

        sqlx::query(RECOMPUTE_JOB_RESOURCE_FROM_PROC)
            .bind(bind_value)
            .execute(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to recompute job resource cores/gpus from proc")?;

        sqlx::query(RESTORE_JOB_RESOURCE_MAX)
            .bind(&ids)
            .bind(&max_cores)
            .bind(&max_gpus)
            .execute(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to restore job resource max values")?;

        tx.commit()
            .await
            .into_diagnostic()
            .wrap_err("Failed to commit job resource recompute transaction")?;

        Ok(())
    }

    /// Recomputes the subscription table from `proc` using a transactional burst bypass.
    ///
    /// Same pattern as `recompute_job_resource_from_proc` but for the
    /// `verify_subscription` trigger which gates on `int_cores > int_burst`.
    ///
    /// `managed_show_ids` must contain only scheduler-managed shows. Empty slice is a
    /// no-op (scheduler has nothing to recompute; Cuebot owns the rest).
    pub async fn recompute_subscription_table(&self, managed_show_ids: &[Uuid]) -> Result<()> {
        if managed_show_ids.is_empty() {
            return Ok(());
        }
        let show_id_strings: Vec<String> =
            managed_show_ids.iter().map(|id| id.to_string()).collect();
        let bind_value: &[String] = &show_id_strings;

        #[derive(sqlx::FromRow)]
        struct BurstRow {
            pk_subscription: String,
            int_burst: i64,
        }

        let mut tx = self
            .connection_pool
            .begin()
            .await
            .into_diagnostic()
            .wrap_err("Failed to begin transaction for subscription recompute")?;

        let burst_rows: Vec<BurstRow> = sqlx::query_as(SELECT_SUBSCRIPTION_BURSTS)
            .bind(bind_value)
            .fetch_all(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to read subscription burst values")?;

        let ids: Vec<String> = burst_rows
            .iter()
            .map(|r| r.pk_subscription.clone())
            .collect();
        let bursts: Vec<i64> = burst_rows.iter().map(|r| r.int_burst).collect();

        sqlx::query(RECOMPUTE_SUBSCRIPTION_FROM_PROC)
            .bind(bind_value)
            .execute(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to recompute subscription cores/gpus from proc")?;

        sqlx::query(RESTORE_SUBSCRIPTION_BURSTS)
            .bind(&ids)
            .bind(&bursts)
            .execute(&mut *tx)
            .await
            .into_diagnostic()
            .wrap_err("Failed to restore subscription burst values")?;

        tx.commit()
            .await
            .into_diagnostic()
            .wrap_err("Failed to commit subscription recompute transaction")?;

        Ok(())
    }
}
