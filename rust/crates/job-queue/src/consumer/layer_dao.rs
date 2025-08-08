use std::sync::Arc;

use futures::Stream;
use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::{config::DatabaseConfig, models::DispatchLayer, pgpool::connection_pool};

pub struct LayerDao {
    connection_pool: Arc<Pool<Postgres>>,
    core_multiplier: u32,
}

#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct DispatchLayerModel {
    pub pk_layer: String,
    pub pk_job: String,
    pub pk_facility: String,
    pub pk_show: String,
    pub str_os: String,
    pub int_cores_min: i32,
    pub int_mem_min: i32,
    pub b_threadable: bool,
    pub int_gpus_min: i32,
    pub int_gpu_mem_min: i32,
    pub str_tags: String,
    pub core_multiplier: i32,
}

impl From<DispatchLayerModel> for DispatchLayer {
    fn from(val: DispatchLayerModel) -> Self {
        DispatchLayer {
            id: Uuid::parse_str(&val.pk_layer).unwrap_or_default(),
            job_id: Uuid::parse_str(&val.pk_job).unwrap_or_default(),
            facility_id: Uuid::parse_str(&val.pk_facility).unwrap_or_default(),
            show_id: Uuid::parse_str(&val.pk_show).unwrap_or_default(),
            str_os: val.str_os,
            cores_min: (val.int_cores_min / val.core_multiplier),
            mem_min: val.int_mem_min,
            threadable: val.b_threadable,
            gpus_min: val.int_gpus_min,
            gpu_mem_min: val.int_gpu_mem_min,
            tags: val.str_tags,
        }
    }
}

static QUERY_LAYER: &str = r#"
SELECT
    l.pk_layer,
    j.pk_job,
    j.pk_facility,
    j.pk_show,
    j.str_os,
    l.int_cores_min,
    l.int_mem_min,
    l.b_threadable,
    l.int_gpus_min,
    l.int_gpu_mem_min,
    l.str_tags
    ? as core_multiplier
FROM job j
    INNER JOIN layer l ON j.pk_job = l.pk_job
    INNER JOIN layer_stat ls on l.pk_layer = ls.pk_layer
WHERE j.pk_job = ?
    AND ls.int_waiting_count > 0
ORDER BY
    l.int_dispatch_order
"#;
// TODO: Take table limit_record into consideration

impl LayerDao {
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(LayerDao {
            connection_pool: pool,
            core_multiplier: config.core_multiplier,
        })
    }

    pub fn query_layers(
        &self,
        pk_job: Uuid,
    ) -> impl Stream<Item = Result<DispatchLayerModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, DispatchLayerModel>(QUERY_LAYER)
            .bind(self.core_multiplier as i32)
            .bind(pk_job.to_string())
            .fetch(&*self.connection_pool)
    }
}
