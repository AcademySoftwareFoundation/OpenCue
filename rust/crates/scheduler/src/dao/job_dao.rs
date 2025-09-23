use std::sync::Arc;

use futures::Stream;
use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use tracing::debug;

use crate::{
    cluster::Cluster,
    config::{CONFIG, DatabaseConfig},
    models::DispatchJob,
    pgpool::connection_pool,
};

/// Data Access Object for job operations in the job dispatch system.
///
/// Handles database queries related to jobs, specifically finding jobs
/// that are ready for dispatch processing based on show subscriptions,
/// resource limits, and job states.
pub struct JobDao {
    connection_pool: Arc<Pool<Postgres>>,
}

/// Database model representing a job ready for dispatch.
///
/// Contains the essential job metadata needed for dispatch prioritization
/// and processing. This model is converted to `DispatchJob` for business
/// logic operations.
#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct JobModel {
    pub pk_job: String,
    pub int_priority: i32,
}

impl DispatchJob {
    pub fn new(model: JobModel, cluster: Cluster) -> Self {
        DispatchJob {
            id: model.pk_job,
            int_priority: model.int_priority,
            source_cluster: cluster,
        }
    }
}

// static QUERY_PENDING_BY_SHOW_FACILITY_TAG: &str = r#"
// SELECT j.pk_job, 1 as int_priority
//   FROM job j
//   INNER JOIN show s ON j.pk_show = s.pk_show
//   WHERE s.pk_show = $1
//     AND j.pk_facility = $2
// "#;
static QUERY_PENDING_BY_SHOW_FACILITY_TAG: &str = r#"
WITH bookable_shows AS (
    SELECT
        distinct w.pk_show
    FROM subscription s
    INNER JOIN vs_waiting w ON s.pk_show = w.pk_show
    WHERE s.pk_show = $1
        AND s.int_burst > 0
        AND s.int_burst - s.int_cores >= $2
        AND s.int_cores < s.int_burst
),
filtered_jobs AS (
    SELECT
        j.pk_job,
        jr.int_priority
    FROM job j
    INNER JOIN bookable_shows on j.pk_show = bookable_shows.pk_show
    INNER JOIN job_resource jr ON j.pk_job = jr.pk_job
    INNER JOIN folder f ON j.pk_folder = f.pk_folder
    INNER JOIN folder_resource fr ON f.pk_folder = fr.pk_folder
    INNER JOIN layer l ON l.pk_job = j.pk_job
    WHERE j.str_state = 'PENDING'
        AND j.b_paused = false
        AND (fr.int_max_cores = -1 OR fr.int_cores + l.int_cores_min < fr.int_max_cores)
        AND (fr.int_max_gpus = -1 OR fr.int_gpus + l.int_gpus_min < fr.int_max_gpus)
        AND string_to_array($3, ' | ') && string_to_array(l.str_tags, ' | ')
        --AND j.pk_facility = $4
)
SELECT DISTINCT
    fj.pk_job,
    fj.int_priority
FROM filtered_jobs fj
INNER JOIN layer_stat ls ON fj.pk_job = ls.pk_job
WHERE ls.int_waiting_count > 0
ORDER BY int_priority DESC
"#;

static QUERY_PENDING_BY_TAGS: &str = r#"
WITH filtered_jobs AS(
    SELECT
        j.pk_job,
        jr.int_priority
    FROM job j
    INNER JOIN job_resource jr ON j.pk_job = jr.pk_job
    INNER JOIN folder f ON j.pk_folder = f.pk_folder
    INNER JOIN folder_resource fr ON f.pk_folder = fr.pk_folder
    INNER JOIN layer l ON l.pk_job = j.pk_job
    WHERE j.str_state = 'PENDING'
        AND j.b_paused = false
        AND (fr.int_max_cores = -1 OR fr.int_cores + l.int_cores_min < fr.int_max_cores)
        AND (fr.int_max_gpus = -1 OR fr.int_gpus + l.int_gpus_min < fr.int_max_gpus)
        AND string_to_array($1, ' | ') && string_to_array(l.str_tags, ' | ')
        --TODO: Add facility to this query. ClusterType::Tags will have to contain facility
        --AND j.pk_facility = 'AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1'
)
SELECT DISTINCT
    fj.pk_job,
    fj.int_priority
FROM filtered_jobs fj
INNER JOIN layer_stat ls ON fj.pk_job = ls.pk_job
WHERE ls.int_waiting_count > 0
ORDER BY int_priority DESC
"#;

impl JobDao {
    /// Creates a new JobDao from database configuration.
    ///
    /// Establishes a connection pool to the PostgreSQL database for
    /// job-related queries.
    ///
    /// # Arguments
    /// * `config` - Database configuration containing connection parameters
    ///
    /// # Returns
    /// * `Ok(JobDao)` - Configured DAO ready for job operations
    /// * `Err(miette::Error)` - If database connection fails
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;

        Ok(JobDao {
            connection_pool: pool,
        })
    }

    /// Queries for pending jobs by show, facility, and tag criteria.
    ///
    /// Finds jobs that are ready for dispatch based on subscription availability,
    /// resource constraints, and tag matching. The query includes several filters:
    /// - Show must have active subscriptions with available burst capacity
    /// - Jobs must be in PENDING state and not paused
    /// - Folder resource limits must not be exceeded
    /// - Layer tags must match the specified tag
    /// - Jobs must have waiting layers
    ///
    /// # Arguments
    /// * `show_id` - The unique identifier of the show to query jobs for
    /// * `facility_id` - The facility identifier (currently unused in query but available for future use)
    /// * `tag` - The tag string to match against layer tags (pipe-separated format supported)
    ///
    /// # Returns
    /// A stream of `JobModel` results ordered by priority (descending).
    /// Each item in the stream is a `Result<JobModel, sqlx::Error>`.
    ///
    /// # Example
    /// ```rust,ignore
    /// let job_stream = job_dao.query_pending_jobs_by_show_facility_tag(
    ///     "show-123".to_string(),
    ///     "facility-456".to_string(),
    ///     "render | lighting".to_string(),
    /// );
    /// ```
    pub async fn query_pending_jobs_by_show_facility_tag(
        &self,
        show_id: String,
        facility_id: String,
        tag: String,
    ) -> Result<Vec<JobModel>, sqlx::Error> {
        debug!(
            "QUERY_PENDING_BY_SHOW_FACILITY_TAG= {}",
            QUERY_PENDING_BY_SHOW_FACILITY_TAG
        );
        debug!(
            "QUERY_PENDING_BY_SHOW_FACILITY_TAG query args: show_id={}, core_multi={}, tag={}, facility_id={}",
            show_id, CONFIG.queue.core_multiplier, tag, facility_id
        );

        sqlx::query_as::<_, JobModel>(QUERY_PENDING_BY_SHOW_FACILITY_TAG)
            .bind(show_id)
            .bind(CONFIG.queue.core_multiplier as i32)
            .bind(tag)
            .bind(facility_id)
            .fetch_all(&*self.connection_pool)
            .await
    }

    pub async fn query_pending_jobs_by_tags(
        &self,
        tags: Vec<String>,
    ) -> Result<Vec<JobModel>, sqlx::Error> {
        sqlx::query_as::<_, JobModel>(QUERY_PENDING_BY_TAGS)
            .bind(tags.join(" | ").to_string())
            .fetch_all(&*self.connection_pool)
            .await
    }
}
