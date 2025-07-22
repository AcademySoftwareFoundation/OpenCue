use std::sync::Arc;

use futures::Stream;
use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::{config::DatabaseConfig, models::DispatchJob, pgpool::connection_pool};

pub struct JobDao {
    connection_pool: Arc<Pool<Postgres>>,
}

#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct JobModel {
    pub pk_job: String,
    pub int_priority: i32,
    pub age_days: i32,
}

impl From<JobModel> for DispatchJob {
    fn from(val: JobModel) -> Self {
        DispatchJob {
            id: Uuid::parse_str(&val.pk_job).unwrap_or_default(),
            int_priority: val.int_priority,
            age_days: val.age_days,
        }
    }
}

static QUERY_PENDING_JOBS: &str = r#"
WITH bookable_shows AS (
    SELECT
        w.pk_show,
        s.float_tier,
        s.int_burst
    FROM subscription s
    INNER JOIN vs_waiting w ON s.pk_show = w.pk_show
    WHERE s.int_burst > 0
        AND s.int_burst - s.int_cores >= 100
        AND s.int_cores < s.int_burst
),
filtered_jobs AS (
    SELECT
        j.pk_job,
        jr.int_priority,
        CAST(EXTRACT(EPOCH FROM (NOW() - j.ts_updated)) / 86400 AS INTEGER) AS age_days
    FROM job j
    INNER JOIN bookable_shows on j.pk_show = bookable_shows.pk_show
    INNER JOIN job_resource jr ON j.pk_job = jr.pk_job
    INNER JOIN folder f ON j.pk_folder = f.pk_folder
    INNER JOIN folder_resource fr ON f.pk_folder = fr.pk_folder
    INNER JOIN point p ON f.pk_dept = p.pk_dept AND f.pk_show = p.pk_show
    WHERE j.str_state = 'PENDING'
        AND j.b_paused = false
        AND (fr.int_max_cores = -1 OR fr.int_cores < fr.int_max_cores)
        AND (fr.int_max_gpus = -1 OR fr.int_gpus < fr.int_max_gpus)
)
SELECT DISTINCT
    fj.pk_job,
    fj.int_priority,
    fj.age_days
FROM filtered_jobs fj
INNER JOIN layer_stat ls ON fj.pk_job = ls.pk_jobWITH bookable_shows AS (
    SELECT
        w.pk_show,
        s.float_tier,
        s.int_burst
    FROM subscription s,
    INNER JOIN vs_waiting w ON s.pk_show = w.pk_show
    WHERE s.int_burst > 0
        AND s.int_burst - s.int_cores >= 100
        AND s.int_cores < s.int_burst
),
WITH filtered_jobs AS (
    SELECT
        j.pk_job,
        jr.int_priority,
        CAST(EXTRACT(EPOCH FROM (NOW() - j.ts_updated)) / 86400 AS INTEGER) AS age_days
    FROM job j
    INNER JOIN j.pk_show = bookable_shows.pk_show
    INNER JOIN job_resource jr ON j.pk_job = jr.pk_job
    INNER JOIN folder f ON j.pk_folder = f.pk_folder
    INNER JOIN folder_resource fr ON f.pk_folder = fr.pk_folder
    INNER JOIN point p ON f.pk_dept = p.pk_dept AND f.pk_show = p.pk_show
    WHERE j.str_state = 'PENDING'
        AND j.b_paused = false
        AND (fr.int_max_cores = -1 OR fr.int_cores < fr.int_max_cores)
        AND (fr.int_max_gpus = -1 OR fr.int_gpus < fr.int_max_gpus)
)
SELECT DISTICT
    fj.pk_job,
    fj.int_priority,
    fj.age_days
FROM filtered_jobs fj
INNER JOIN layer_stat ls ON fj.pk_job = ls.pk_job
WHERE ls.int_waiting_count > 0
"#;

impl JobDao {
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;

        Ok(JobDao {
            connection_pool: pool,
        })
    }

    pub fn query_active_jobs(&self) -> impl Stream<Item = Result<JobModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, JobModel>(QUERY_PENDING_JOBS).fetch(&*self.connection_pool)
    }
}
