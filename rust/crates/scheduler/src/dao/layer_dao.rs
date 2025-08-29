use std::sync::Arc;

use futures::Stream;
use miette::Result;
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres};
use uuid::Uuid;

use crate::{
    config::DatabaseConfig,
    models::{CoreSize, DispatchLayer},
    pgpool::connection_pool,
};

/// Data Access Object for layer operations in the job dispatch system.
///
/// Handles database queries related to layers within jobs, specifically
/// finding layers that have waiting frames and are ready for dispatch.
pub struct LayerDao {
    connection_pool: Arc<Pool<Postgres>>,
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

impl From<DispatchLayerModel> for DispatchLayer {
    fn from(val: DispatchLayerModel) -> Self {
        DispatchLayer {
            id: Uuid::parse_str(&val.pk_layer).unwrap_or_default(),
            job_id: Uuid::parse_str(&val.pk_job).unwrap_or_default(),
            facility_id: Uuid::parse_str(&val.pk_facility).unwrap_or_default(),
            show_id: Uuid::parse_str(&val.pk_show).unwrap_or_default(),
            job_name: val.str_job_name,
            layer_name: val.str_name,
            str_os: val.str_os,
            cores_min: CoreSize::from_multiplied(
                val.int_cores_min
                    .try_into()
                    .expect("int_cores_min should fit on a i32"),
            ),
            mem_min: val.int_mem_min,
            threadable: val.b_threadable,
            gpus_min: val
                .int_gpus_min
                .try_into()
                .expect("gpus_min should fit on a i32"),
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
    pub async fn from_config(config: &DatabaseConfig) -> Result<Self> {
        let pool = connection_pool(config).await?;
        Ok(LayerDao {
            connection_pool: pool,
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
    pub fn query_layers(
        &self,
        pk_job: Uuid,
    ) -> impl Stream<Item = Result<DispatchLayerModel, sqlx::Error>> + '_ {
        sqlx::query_as::<_, DispatchLayerModel>(QUERY_LAYER)
            .bind(format!("{:x}", pk_job))
            .fetch(&*self.connection_pool)
    }
}
