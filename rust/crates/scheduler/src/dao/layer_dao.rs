use std::sync::Arc;

use bytesize::ByteSize;
use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use tracing::warn;

use crate::{
    config::{CONFIG, DatabaseConfig},
    dao::{FrameDao, frame_dao::DispatchFrameModel},
    models::{CoreSize, DispatchLayer},
    pgpool::connection_pool,
};

/// Data Access Object for layer operations in the job dispatch system.
///
/// Handles database queries related to layers within jobs, specifically
/// finding layers that have waiting frames and are ready for dispatch.
pub struct LayerDao {
    connection_pool: Arc<Pool<Postgres>>,
    frame_dao: Arc<FrameDao>,
}

/// Database model representing a layer ready for dispatch.
///
/// Contains layer metadata, resource requirements, and job context needed
/// for host matching and frame dispatch. This model is converted to
/// `DispatchLayer` for business logic processing.
#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct DispatchLayerModel {
    pub pk_layer: String,
    pub pk_job: String,
    pub pk_facility: String,
    pub pk_show: String,
    pub str_name: String,
    pub str_job_name: String,
    pub str_os: Option<String>,
    pub int_cores_min: i64,
    pub int_mem_min: i64,
    pub b_threadable: bool,
    pub int_gpus_min: i64,
    pub int_gpu_mem_min: i64,
    pub str_tags: String,
}

impl DispatchLayer {
    pub fn new(layer: DispatchLayerModel, frames: Vec<DispatchFrameModel>) -> Self {
        DispatchLayer {
            id: layer.pk_layer,
            job_id: layer.pk_job,
            facility_id: layer.pk_facility,
            show_id: layer.pk_show,
            job_name: layer.str_job_name,
            layer_name: layer.str_name,
            str_os: layer.str_os,
            cores_min: CoreSize::from_multiplied(
                layer
                    .int_cores_min
                    .try_into()
                    .expect("int_cores_min should fit on a i32"),
            ),
            mem_min: ByteSize::kb(layer.int_mem_min as u64),
            threadable: layer.b_threadable,
            gpus_min: layer
                .int_gpus_min
                .try_into()
                .expect("gpus_min should fit on a i32"),
            gpu_mem_min: ByteSize::kb(layer.int_gpu_mem_min as u64),
            tags: layer.str_tags.split(" | ").map(|t| t.to_string()).collect(),
            frames: frames.into_iter().map(|f| f.into()).collect(),
        }
    }
}

static QUERY_LAYER: &str = r#"
SELECT
    l.pk_layer,
    j.pk_job,
    j.pk_facility,
    j.pk_show,
    j.str_name,
    l.str_name as str_job_name,
    j.str_os,
    l.int_cores_min,
    l.int_mem_min,
    l.b_threadable,
    l.int_gpus_min,
    l.int_gpu_mem_min,
    l.str_tags
FROM job j
    INNER JOIN layer l ON j.pk_job = l.pk_job
    INNER JOIN layer_stat ls on l.pk_layer = ls.pk_layer
WHERE j.pk_job = $1
    AND ls.int_waiting_count > 0
    AND string_to_array($2, ' | ') && string_to_array(l.str_tags, ' | ')
ORDER BY
    l.int_dispatch_order
"#;
// TODO: Take table limit_record into consideration

impl LayerDao {
    /// Creates a new LayerDao from database configuration.
    ///
    /// Establishes a connection pool to the PostgreSQL database for
    /// layer-related queries.
    ///
    /// # Arguments
    /// * `config` - Database configuration containing connection parameters
    ///
    /// # Returns
    /// * `Ok(LayerDao)` - Configured DAO ready for layer operations
    /// * `Err(miette::Error)` - If database connection fails
    pub async fn new(config: &DatabaseConfig, frame_dao: Arc<FrameDao>) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(LayerDao {
            connection_pool: pool,
            frame_dao,
        })
    }

    /// Queries layers within a specific job that have waiting frames.
    ///
    /// Returns layers that:
    /// - Belong to the specified job
    /// - Have at least one frame in waiting state
    /// - Are ordered by dispatch priority (int_dispatch_order)
    ///
    /// This query is used to find layers within a job that are ready
    /// for frame dispatch processing.
    ///
    /// # Arguments
    /// * `pk_job` - The UUID of the job to find layers for
    ///
    /// # Returns
    /// A stream of `DispatchLayerModel` results ordered by dispatch priority
    pub async fn query_layers(
        &self,
        pk_job: String,
        tags: Vec<String>,
    ) -> Result<Vec<DispatchLayer>, sqlx::Error> {
        let layer_models = sqlx::query_as::<_, DispatchLayerModel>(QUERY_LAYER)
            .bind(pk_job)
            .bind(tags.join(" | ").to_string())
            .fetch_all(&*self.connection_pool)
            .await?;

        let mut result = Vec::new();
        for layer_model in layer_models {
            let frame = self
                .frame_dao
                .query_dispatch_frames(
                    &layer_model.pk_layer,
                    CONFIG.queue.dispatch_frames_per_layer_limit as i32,
                )
                .await?;
            result.push(DispatchLayer::new(layer_model, frame));
        }
        Ok(result)
    }
}
