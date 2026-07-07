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

use miette::{IntoDiagnostic, Result};
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use tracing::trace;
use uuid::Uuid;

use crate::{
    cluster::Cluster, config::CONFIG, dao::helpers::parse_uuid,
    metrics::observe_job_query_duration, models::DispatchJob, pgpool::connection_pool,
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
    pub show_name: String,
}

/// One active (facility, show, tag) tuple from [`JobDao::scan_active_tags`].
///
/// A tag is "active" for a (facility, show) when at least one PENDING job in
/// that facility/show has a waiting layer carrying the tag, and the show still
/// has subscription headroom. Used to gate the cluster feed's awake set: a
/// cluster is eligible iff one of its tags appears here under its
/// (facility, show) key. See `cluster::ClusterFeed` and the superset argument
/// on [`QUERY_ACTIVE_TAGS`].
#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct ActiveTagModel {
    pub pk_show: String,
    pub pk_facility: String,
    pub tag: String,
}

impl DispatchJob {
    /// Creates a new DispatchJob from a database model and cluster assignment.
    ///
    /// # Arguments
    ///
    /// * `model` - Database model containing job ID and priority
    /// * `cluster` - The cluster this job is assigned to for dispatch
    ///
    /// # Returns
    ///
    /// * `DispatchJob` - New dispatch job instance
    pub fn new(model: JobModel, cluster: Cluster) -> Self {
        DispatchJob {
            id: parse_uuid(&model.pk_job),
            int_priority: model.int_priority,
            source_cluster: cluster,
        }
    }
}

static QUERY_PENDING_BY_SHOW_FACILITY_TAG: &str = r#"
-- LIVE booked-core CTEs. The job/folder/subscription caps must be gated on CURRENT
-- usage, but the PG columns job_resource.int_cores / folder_resource.int_cores /
-- subscription.int_cores are only materialized by the ~120s recompute loop, so they
-- lag reality. `proc` is the transactionally-accurate source (the scheduler inserts on
-- booking, Cuebot deletes on frame completion, compensation deletes on a failed launch),
-- so we sum it directly. Each CTE is scoped to this show ($1) via i_proc_pkshow and
-- mirrors the recompute aggregation (so the value equals a fresher copy of the PG
-- column), and joins on indexed pk_host / pk_job. Gating on stale PG would otherwise
-- (a) over-fetch jobs for caps that are full in Redis -> wasted rejections, and worse
-- (b) FALSE-EXCLUDE: a frame completes and frees burst live, but the lagged PG column
-- stays high for up to a cycle, dropping the show/folder/job from the fetch and starving
-- its (esp. low-priority) jobs until the next recompute.
WITH job_live AS (
    -- per-job booked cores (mirrors RECOMPUTE_JOB_RESOURCE_FROM_PROC)
    SELECT p.pk_job, COALESCE(SUM(p.int_cores_reserved), 0)::int AS cores
    FROM proc p
    WHERE p.pk_show = $1
    GROUP BY p.pk_job
),
folder_live AS (
    -- per-folder booked cores/gpus (mirrors RECOMPUTE_FOLDER_RESOURCE_FROM_PROC)
    SELECT j2.pk_folder,
           COALESCE(SUM(p.int_cores_reserved), 0)::int AS cores,
           COALESCE(SUM(p.int_gpus_reserved), 0)::int  AS gpus
    FROM proc p
    JOIN job j2 ON j2.pk_job = p.pk_job AND j2.str_state <> 'FINISHED'
    WHERE p.pk_show = $1
    GROUP BY j2.pk_folder
),
sub_live AS (
    -- per-alloc booked cores for this show (mirrors RECOMPUTE_SUBSCRIPTION_FROM_PROC:
    -- proc -> host -> alloc, excluding local/desktop bookings)
    SELECT h.pk_alloc, COALESCE(SUM(p.int_cores_reserved), 0)::int AS cores
    FROM proc p
    JOIN host h ON h.pk_host = p.pk_host
    WHERE p.pk_show = $1 AND p.b_local = false
    GROUP BY h.pk_alloc
),
-- bookable_shows: shows that still have room in at least one subscription (LIVE).
bookable_shows AS (
    SELECT DISTINCT w.pk_show, sh.str_name AS show_name
    FROM subscription s
    -- LEFT JOIN: an alloc with no booked procs has full headroom.
    LEFT JOIN sub_live sl ON sl.pk_alloc = s.pk_alloc
    INNER JOIN vs_waiting w ON s.pk_show = w.pk_show
    INNER JOIN show sh ON sh.pk_show = w.pk_show
    WHERE s.pk_show = $1
        -- Burst == 0 is used to freeze a subscription.
        AND s.int_burst > 0
        -- At least one core unit available, measured against LIVE usage.
        AND s.int_burst - COALESCE(sl.cores, 0) >= $2
        AND COALESCE(sl.cores, 0) < s.int_burst
)
SELECT
    j.pk_job,
    jr.int_priority,
    bs.show_name
FROM job j
INNER JOIN bookable_shows bs ON j.pk_show = bs.pk_show
INNER JOIN job_resource jr ON j.pk_job = jr.pk_job
INNER JOIN folder f ON j.pk_folder = f.pk_folder
INNER JOIN folder_resource fr ON f.pk_folder = fr.pk_folder
-- LEFT JOIN the live CTEs: no row => 0 booked => full headroom.
LEFT JOIN job_live jl ON jl.pk_job = j.pk_job
LEFT JOIN folder_live fl ON fl.pk_folder = f.pk_folder
WHERE j.str_state = 'PENDING'
    AND j.b_paused = false
    AND j.pk_facility = $4
    -- Folder must have any room at all (LIVE); per-layer fit is checked below.
    AND (fr.int_max_cores <= 0 OR COALESCE(fl.cores, 0) < fr.int_max_cores)
    AND (fr.int_max_gpus <= 0 OR COALESCE(fl.gpus, 0) < fr.int_max_gpus)
    -- The job must have at least one layer that matches the tag set, has waiting
    -- frames, and fits within the folder AND job caps (both LIVE). EXISTS short-circuits
    -- per job and avoids the cardinality blowup of joining layer + layer_stat at the
    -- outer level.
    AND EXISTS (
        SELECT 1
        FROM layer l
        INNER JOIN layer_stat ls ON ls.pk_layer = l.pk_layer
        WHERE l.pk_job = j.pk_job
          AND ls.int_waiting_count > 0
          AND string_to_array(REPLACE($3, ' ', ''), '|')
              && string_to_array(REPLACE(l.str_tags, ' ', ''), '|')
          AND (fr.int_max_cores <= 0 OR COALESCE(fl.cores, 0) + l.int_cores_min <= fr.int_max_cores)
          AND (fr.int_max_gpus <= 0 OR COALESCE(fl.gpus, 0) + l.int_gpus_min <= fr.int_max_gpus)
          AND (jr.int_max_cores <= 0 OR COALESCE(jl.cores, 0) + l.int_cores_min <= jr.int_max_cores)
    )
ORDER BY jr.int_priority DESC
LIMIT $5
"#;

// Awake-gate scan. Returns the set of (facility, show, tag) tuples that *could*
// yield a dispatchable job, so the cluster feed can keep clusters with no work
// asleep instead of re-querying them every backoff window.
//
// SUPERSET INVARIANT (must never produce a false negative): every (job, layer)
// the per-cluster query QUERY_PENDING_BY_SHOW_FACILITY_TAG would return must be
// captured here, otherwise the owning cluster is gated to permanent sleep and
// its jobs starve. Two rules keep this true:
//
// `unnest` splits each layer's pipe-joined str_tags into individual tags; the
// feed re-applies tag-set overlap on the cluster side, matching the per-cluster
// `&&` array-overlap semantics.
static QUERY_ACTIVE_TAGS: &str = r#"
SELECT DISTINCT
    j.pk_show,
    j.pk_facility,
    unnest(string_to_array(REPLACE(l.str_tags, ' ', ''), '|')) AS tag
FROM job j
INNER JOIN show sh ON sh.pk_show = j.pk_show
INNER JOIN layer l ON l.pk_job = j.pk_job
INNER JOIN layer_stat ls ON ls.pk_layer = l.pk_layer
WHERE j.str_state = 'PENDING'
    AND j.b_paused = false
    AND sh.b_active = true
    AND sh.b_scheduler_managed = true
    AND ls.int_waiting_count > 0
    AND EXISTS (
        SELECT 1 FROM subscription s
        WHERE s.pk_show = j.pk_show AND s.int_burst > 0
    )
    AND ($1::text IS NULL OR j.pk_facility = $1)
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
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;

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
    pub async fn query_pending_jobs_by_show_facility_and_tags(
        &self,
        show_id: Uuid,
        facility_id: &str,
        tags: impl Iterator<Item = String>,
    ) -> Result<Vec<JobModel>, sqlx::Error> {
        trace!(
            "QUERY_PENDING_BY_SHOW_FACILITY_TAG= {}",
            QUERY_PENDING_BY_SHOW_FACILITY_TAG
        );
        let tags_collected: Vec<String> = tags.collect();
        trace!(
            "QUERY_PENDING_BY_SHOW_FACILITY_TAG query args: show_id={}, core_multi={}, tag={}, facility_id={}",
            show_id, CONFIG.queue.core_multiplier, tags_collected.join(","), facility_id);

        let start = std::time::Instant::now();
        let result = sqlx::query_as::<_, JobModel>(QUERY_PENDING_BY_SHOW_FACILITY_TAG)
            .bind(show_id.to_string())
            .bind(CONFIG.queue.core_multiplier as i32)
            .bind(tags_collected.join(" | ").to_string())
            .bind(facility_id)
            .bind(CONFIG.queue.max_jobs_per_cluster_pass)
            .fetch_all(&*self.connection_pool)
            .await;
        observe_job_query_duration(start.elapsed());
        result
    }

    /// Scans for the set of (facility, show, tag) tuples that currently have
    /// plausibly-dispatchable work, used to gate the cluster feed's awake set.
    ///
    /// This is a strict superset of what `query_pending_jobs_by_show_facility_and_tags`
    /// would return (see [`QUERY_ACTIVE_TAGS`]): a cluster whose tag is absent
    /// here is guaranteed to have no dispatchable job and can stay asleep. The
    /// reverse does not hold — a returned tag may still yield a no_jobs or
    /// saturated pass once the folder/job caps and live subscription headroom are
    /// evaluated per-cluster, which is intentionally cheap to absorb.
    ///
    /// # Arguments
    /// * `facility_id` - Optional facility filter; `None` scans every facility.
    ///
    /// # Returns
    /// All active tuples (unordered). One database round-trip regardless of the
    /// number of clusters.
    pub async fn scan_active_tags(
        &self,
        facility_id: Option<&str>,
    ) -> Result<Vec<ActiveTagModel>, sqlx::Error> {
        let start = std::time::Instant::now();
        let result = sqlx::query_as::<_, ActiveTagModel>(QUERY_ACTIVE_TAGS)
            .bind(facility_id)
            .fetch_all(&*self.connection_pool)
            .await;
        crate::metrics::observe_active_scan_duration(start.elapsed());
        result
    }
}
