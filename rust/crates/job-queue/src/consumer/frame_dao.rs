use std::sync::Arc;

use futures::Stream;
use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::{
    config::DatabaseConfig,
    models::{DispatchFrame, DispatchLayer},
    pgpool::connection_pool,
};

pub struct FrameDao {
    connection_pool: Arc<Pool<Postgres>>,
    core_multiplier: u32,
}

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
    pub int_chunk_size: i32,
    pub str_show: String,
    pub str_shot: String,
    pub str_user: String,
    pub int_uid: Option<i32>,
    pub str_log_dir: String,
    pub str_layer_name: String,
    pub str_job_name: String,
    pub int_min_cores: i32,
    pub int_min_memory: i64,
    pub b_threadable: bool,
    pub int_gpus_min: i32,
    pub int_gpu_mem_min: i64,
    // On Cuebot these fields come from constants, maybe replicate these constants here
    // pub int_soft_memory_limit: i64,
    // pub int_hard_memory_limit: i64,
    pub str_services: Option<String>,
    pub str_os: Option<String>,
    pub str_loki_url: Option<String>,
    pub int_layer_cores_max: i32,
    pub core_multiplier: i32,
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
            chunk_size: val.int_chunk_size,
            show_name: val.str_show,
            shot: val.str_shot,
            user: val.str_user,
            uid: val.int_uid,
            log_dir: val.str_log_dir,
            layer_name: val.str_layer_name,
            job_name: val.str_job_name,
            min_cores: val.int_min_cores / val.core_multiplier,
            threadable: val.b_threadable,
            min_gpus: val.int_gpus_min as u32,
            min_gpu_memory: val.int_gpu_mem_min as u64,
            min_memory: val.int_min_memory as u64,
            services: val.str_services,
            os: val.str_os,
            loki_url: val.str_loki_url,
            layer_cores_limit: (val.int_layer_cores_max > 0)
                .then(|| (val.int_layer_cores_max / val.core_multiplier) as u32),
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
        j.str_loki_url,
        l.int_cores_max,
        ? as core_multiplier,
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
    WHERE l.pk_layer = ?
        AND f.str_state = 'WAITING'
) SELECT * from dispatch_frames
    -- Limit the query to a number of frames that would not overflow the job_resource limit
    -- limit <= 0 means there's no limit
    WHERE job_resource_core_limit <= 0 OR (aggr_job_cores + job_resource_consumed_cores <= job_resource_core_limit)
ORDER BY
    int_dispatch_order,
    int_layer_order
LIMIT ?
"#;
// TODO: Take table limit_record into consideration

impl FrameDao {
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(FrameDao {
            connection_pool: pool,
            core_multiplier: config.core_multiplier,
        })
    }

    pub fn query_dispatch_frames(
        &self,
        layer: &DispatchLayer,
        limit: i32,
    ) -> impl Stream<Item = Result<DispatchFrameModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, DispatchFrameModel>(QUERY_FRAME)
            .bind(self.core_multiplier as i32)
            .bind(layer.id.to_string())
            .bind(limit)
            .fetch(&*self.connection_pool)
    }
}
