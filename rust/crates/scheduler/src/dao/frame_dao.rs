use bytesize::{ByteSize, KB};
use miette::{Context, IntoDiagnostic, Result};
use serde::{Deserialize, Serialize};
use sqlx::{Postgres, Transaction};

use crate::models::{CoreSize, DispatchFrame, VirtualProc};

/// Data Access Object for frame operations in the job dispatch system.
///
/// Handles database queries related to frames, particularly for finding
/// dispatchable frames within layers that meet resource constraints.
pub struct FrameDao {}

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

impl FrameDao {
    pub async fn new() -> Result<Self> {
        // This is only here to keep a similar interface with other DAO modules
        Ok(FrameDao {})
    }

    pub async fn update_frame_started(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        virtual_proc: &VirtualProc,
    ) -> Result<()> {
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
        .execute(&mut **transaction)
        .await
        .into_diagnostic()
        .wrap_err("Failed to start frame on database")?;

        Ok(())
    }
}
