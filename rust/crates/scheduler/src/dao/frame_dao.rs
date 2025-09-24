use std::sync::Arc;

use bytesize::{ByteSize, KB};
use futures::Stream;
use miette::{Context, IntoDiagnostic, Result};
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};

use crate::{
    config::DatabaseConfig,
    models::{CoreSize, DispatchFrame, DispatchLayer, VirtualProc},
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
    pub int_version: i32,
}

impl From<DispatchFrameModel> for DispatchFrame {
    fn from(val: DispatchFrameModel) -> Self {
        DispatchFrame {
            // id: Uuid::parse_str(&val.pk_host).unwrap_or_default(),
            id: val.pk_frame,
            frame_name: val.str_frame_name,
            show_id: val.pk_show,
            facility_id: val.pk_facility,
            job_id: val.pk_job,
            layer_id: val.pk_layer,
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
            min_gpu_memory: ByteSize::kb(val.int_gpu_mem_min as u64),
            min_memory: ByteSize::kb(val.int_mem_min as u64),
            services: val.str_services,
            os: val.str_os,
            // TODO: fill up from config, or update database schema
            loki_url: None,
            layer_cores_limit: (val.int_layer_cores_max > 0)
                .then(|| CoreSize::from_multiplied(val.int_layer_cores_max)),
            // TODO: Implement a better solution for handling selfish services
            has_selfish_service: false,
            version: val.int_version as u32,
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
        f.int_version,
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
    pub async fn query_dispatch_frames(
        &self,
        layer_id: &str,
        limit: i32,
    ) -> Result<Vec<DispatchFrameModel>, sqlx::Error> {
        sqlx::query_as::<_, DispatchFrameModel>(QUERY_FRAME)
            .bind(layer_id)
            .bind(limit)
            .fetch_all(&*self.connection_pool)
            .await
    }

    pub async fn update_frame_started(&self, virtual_proc: &VirtualProc) -> Result<()> {
        sqlx::query(
            r#"
            UPDATE frame SET
                str_state = 'RUNNING',
                str_host = $1,
                int_cores = $2,
                int_mem_reserved = $3,
                int_gpus = $4,
                int_gpu_mem_reserved = $5,
                ts_updated = current_timestamp,
                ts_started = current_timestamp,
                ts_stopped = null,
                int_version = int_version + 1
            WHERE pk_frame = $6
                AND str_state = 'WAITING'
                AND int_version = $7
                AND frame.pk_layer IN (
                    SELECT layer.pk_layer
                    FROM layer
                    LEFT JOIN layer_limit ON layer_limit.pk_layer = layer.pk_layer
                    LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record
                    LEFT JOIN (
                        SELECT limit_record.pk_limit_record,
                               SUM(layer_stat.int_running_count) AS int_sum_running
                        FROM layer_limit
                        LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record
                        LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer
                        GROUP BY limit_record.pk_limit_record
                    ) AS sum_running ON limit_record.pk_limit_record = sum_running.pk_limit_record
                    WHERE sum_running.int_sum_running < limit_record.int_max_value
                       OR sum_running.int_sum_running IS NULL
                );
            "#,
        )
        .bind(virtual_proc.host_name.clone())
        .bind(virtual_proc.cores_reserved.value())
        .bind((virtual_proc.memory_reserved.as_u64() / KB) as i32)
        .bind(virtual_proc.gpus_reserved as i32)
        .bind((virtual_proc.gpu_memory_reserved.as_u64() / KB) as i32)
        .bind(virtual_proc.frame.id.clone())
        .bind(virtual_proc.frame.version as i32)
        .execute(&*self.connection_pool)
        .await
        .into_diagnostic()
        .wrap_err("Failed to start frame on database")?;

        Ok(())
    }
}
