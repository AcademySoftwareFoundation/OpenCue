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

use crate::pgpool::connection_pool;

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
    GROUP BY lr2.pk_layer
) booked
WHERE lr.pk_layer = booked.pk_layer
"#;

static RECOMPUTE_JOB_RESOURCE_FROM_PROC: &str = r#"
UPDATE job_resource jr
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT jr2.pk_job,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM job_resource jr2
    LEFT JOIN proc p ON p.pk_job = jr2.pk_job
    GROUP BY jr2.pk_job
) booked
WHERE jr.pk_job = booked.pk_job
"#;

static RECOMPUTE_FOLDER_RESOURCE_FROM_PROC: &str = r#"
UPDATE folder_resource fr
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT fr2.pk_folder,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM folder_resource fr2
    LEFT JOIN job j ON j.pk_folder = fr2.pk_folder
    LEFT JOIN proc p ON p.pk_job = j.pk_job
    GROUP BY fr2.pk_folder
) booked
WHERE fr.pk_folder = booked.pk_folder
"#;

static RECOMPUTE_POINT_FROM_PROC: &str = r#"
UPDATE point pt
SET int_cores = COALESCE(booked.total_cores, 0),
    int_gpus = COALESCE(booked.total_gpus, 0)
FROM (
    SELECT pt2.pk_dept, pt2.pk_show,
           SUM(p.int_cores_reserved)::int AS total_cores,
           SUM(p.int_gpus_reserved)::int AS total_gpus
    FROM point pt2
    LEFT JOIN job j ON j.pk_dept = pt2.pk_dept
    LEFT JOIN proc p ON p.pk_job = j.pk_job AND p.pk_show = pt2.pk_show
    GROUP BY pt2.pk_dept, pt2.pk_show
) booked
WHERE pt.pk_dept = booked.pk_dept
  AND pt.pk_show = booked.pk_show
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

    /// Recomputes layer_resource, job_resource, folder_resource, and point tables
    /// from the proc table as the single source of truth.
    ///
    /// **Staleness window:** subscriptions refresh every ~3s and resources every ~10s.
    /// This is acceptable because these tables are advisory — the scheduler's in-memory
    /// cache is the authoritative source for dispatch decisions.
    ///
    /// **No transaction by design:** the four queries intentionally run outside a
    /// transaction to avoid holding row-level locks across tables, which would contend
    /// with cuebot's incremental updates during the migration period. Any mid-cycle
    /// inconsistency is self-healing on the next cycle.
    pub async fn recompute_all_from_proc(&self) -> Result<()> {
        sqlx::query(RECOMPUTE_LAYER_RESOURCE_FROM_PROC)
            .execute(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to recompute layer_resource from proc")?;

        sqlx::query(RECOMPUTE_JOB_RESOURCE_FROM_PROC)
            .execute(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to recompute job_resource from proc")?;

        sqlx::query(RECOMPUTE_FOLDER_RESOURCE_FROM_PROC)
            .execute(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to recompute folder_resource from proc")?;

        sqlx::query(RECOMPUTE_POINT_FROM_PROC)
            .execute(self.connection_pool.as_ref())
            .await
            .into_diagnostic()
            .wrap_err("Failed to recompute point from proc")?;

        Ok(())
    }
}
