use std::sync::Arc;

use futures::Stream;
use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::{
    config::DatabaseConfig,
    models::{CoreSize, DispatchFrame, DispatchLayer},
    pgpool::connection_pool,
};

/// Data Access Object for frame operations in the job dispatch system.
///
/// Handles database queries related to frames, particularly for finding
/// dispatchable frames within layers that meet resource constraints.
pub struct FrameDao {
    connection_pool: Arc<Pool<Postgres>>,
}

/// Database model representing a frame ready for dispatch.
///
/// Contains all the necessary information to dispatch a frame to a host,
/// including resource requirements, job metadata, and execution parameters.
/// This model maps directly to the database query results and is converted
/// to `DispatchFrame` for business logic processing.
#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct DispatchFrameModel {
    // Entity fields
    pub pk_frame: String,
    pub str_frame_name: String,

    // LayerEntity fields
    pub pk_show: String,
    pub pk_facility: String,
    pub pk_job: String,

    // FrameEntity fields
    pub pk_layer: String,

    // DispatchFrame specific fields
    pub str_cmd: String,
    pub str_range: String,
    pub int_chunk_size: i64,
    pub str_show: String,
    pub str_shot: String,
    pub str_user: String,
    pub int_uid: Option<i64>,
    pub str_log_dir: String,
    pub str_layer_name: String,
    pub str_job_name: String,
    pub int_min_cores: i32,
    pub int_mem_min: i64,
    pub b_threadable: bool,
    pub int_gpus_min: i64,
    pub int_gpu_mem_min: i64,
    // On Cuebot these fields come from constants, maybe replicate these constants here
    // pub int_soft_memory_limit: i64,
    // pub int_hard_memory_limit: i64,
    pub str_services: Option<String>,
    pub str_os: Option<String>,
    pub int_layer_cores_max: i32,
}

impl From<DispatchFrameModel> for DispatchFrame {
    fn from(val: DispatchFrameModel) -> Self {
        DispatchFrame {
            // id: Uuid::parse_str(&val.pk_host).unwrap_or_default(),
            id: Uuid::parse_str(&val.pk_frame).unwrap_or_default(),
            frame_name: val.str_frame_name,
            show_id: Uuid::parse_str(&val.pk_show).unwrap_or_default(),
            facility_id: Uuid::parse_str(&val.pk_facility).unwrap_or_default(),
            job_id: Uuid::parse_str(&val.pk_job).unwrap_or_default(),
            layer_id: Uuid::parse_str(&val.pk_layer).unwrap_or_default(),
            command: val.str_cmd,
            range: val.str_range,
            chunk_size: val
                .int_chunk_size
                .try_into()
                .expect("int_chunk_size fit on a i32"),
            show_name: val.str_show,
            shot: val.str_shot,
            user: val.str_user,
            uid: val
                .int_uid
                .map(|uid| uid.try_into().expect("int_uid should fit on a i32")),
            log_dir: val.str_log_dir,
            layer_name: val.str_layer_name,
            job_name: val.str_job_name,
            min_cores: CoreSize::from_multiplied(val.int_min_cores),
            threadable: val.b_threadable,
            min_gpus: val
                .int_gpus_min
                .try_into()
                .expect("int_gpus_min should fit on a i32"),
            min_gpu_memory: val.int_gpu_mem_min as u64,
            min_memory: val.int_mem_min as u64,
            services: val.str_services,
            os: val.str_os,
            // TODO: fill up from config, or update database schema
            loki_url: None,
            layer_cores_limit: (val.int_layer_cores_max > 0)
                .then(|| CoreSize::from_multiplied(val.int_layer_cores_max)),
            // TODO: Implement a better solution for handling selfish services
            has_selfish_service: false,
        }
    }
}

static QUERY_FRAME: &str = r#"
WITH dispatch_frames AS (
    SELECT
        f.pk_frame,
        f.str_name as str_frame_name,
        j.pk_show,
        j.pk_facility,
        j.pk_job,
        l.pk_layer,
        l.str_cmd,
        l.str_range,
        l.int_chunk_size,
        j.str_show,
        j.str_shot,
        j.str_user,
        j.int_uid,
        j.str_log_dir,
        l.str_name as str_layer_name,
        j.str_name as str_job_name,
        j.int_min_cores,
        l.int_mem_min,
        l.b_threadable,
        l.int_gpus_min,
        l.int_gpu_mem_min,
        l.str_services,
        j.str_os,
        l.int_cores_max as int_layer_cores_max,
        f.int_dispatch_order,
        f.int_layer_order,
        -- Accumulate the number of cores that would be consumed
        SUM(l.int_cores_min) OVER (
            ORDER BY f.int_dispatch_order, f.int_layer_order
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS aggr_job_cores,
        jr.int_max_cores as job_resource_core_limit,
        jr.int_cores as job_resource_consumed_cores
    FROM job j
        INNER JOIN layer l ON j.pk_job = l.pk_job
        INNER JOIN frame f ON l.pk_layer = f.pk_layer
        INNER JOIN job_resource jr ON l.pk_job = jr.pk_job
    WHERE l.pk_layer = $1
        -- Avoid booking DEPEND frames. This status is maintained by a database trigger
        AND f.str_state = 'WAITING'
) SELECT * from dispatch_frames
    -- Limit the query to a number of frames that would not overflow the job_resource limit
    -- limit <= 0 means there's no limit
    WHERE job_resource_core_limit <= 0 OR (aggr_job_cores + job_resource_consumed_cores <= job_resource_core_limit)
ORDER BY
    int_dispatch_order,
    int_layer_order
LIMIT $2
"#;
// TODO: Take table limit_record into consideration

impl FrameDao {
    /// Creates a new FrameDao from database configuration.
    ///
    /// Establishes a connection pool to the PostgreSQL database using the
    /// provided configuration settings.
    ///
    /// # Arguments
    /// * `config` - Database configuration containing connection parameters
    ///
    /// # Returns
    /// * `Ok(FrameDao)` - Configured DAO ready for database operations
    /// * `Err(miette::Error)` - If database connection fails
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(FrameDao {
            connection_pool: pool,
        })
    }

    /// Queries frames ready for dispatch within a specific layer.
    ///
    /// Returns a stream of frames that are:
    /// - In WAITING state (not DEPEND or already running)
    /// - Respecting job resource core limits
    /// - Ordered by dispatch and layer priority
    ///
    /// The query includes a complex resource limit check that ensures the
    /// cumulative core usage doesn't exceed job resource limits.
    ///
    /// # Arguments
    /// * `layer` - The layer to find dispatchable frames for
    /// * `limit` - Maximum number of frames to return
    ///
    /// # Returns
    /// A stream of `DispatchFrameModel` results from the database query
    pub fn query_dispatch_frames(
        &self,
        layer: &DispatchLayer,
        limit: i32,
    ) -> impl Stream<Item = Result<DispatchFrameModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, DispatchFrameModel>(QUERY_FRAME)
            .bind(format!("{:x}", layer.id))
            .bind(limit)
            .fetch(&*self.connection_pool)
    }
}
