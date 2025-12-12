use std::collections::HashMap;
use std::sync::Arc;

use bytesize::ByteSize;
use chrono::{DateTime, Utc};
use miette::{IntoDiagnostic, Result};
use serde::{Deserialize, Serialize};
use sqlx::{Pool, Postgres, Transaction};
use tracing::debug;
use uuid::Uuid;

use crate::{
    config::CONFIG,
    dao::frame_dao::DispatchFrameModel,
    dao::helpers::parse_uuid,
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

/// Combined model for batched layer and frame queries.
///
/// This model contains both layer and frame data in a single row,
/// allowing us to fetch layers with their frames in one database call
/// instead of making nested queries.
#[derive(sqlx::FromRow)]
pub struct LayerWithFramesModel {
    // Layer fields
    pub pk_layer: String,
    pub pk_job: String,
    pub pk_facility: String,
    pub pk_show: String,
    pub layer_name: String,
    pub job_name: String,
    pub str_os: Option<String>,
    pub int_cores_min: i64,
    pub int_mem_min: i64,
    pub b_threadable: bool,
    pub int_gpus_min: i64,
    pub int_gpu_mem_min: i64,
    pub str_tags: String,

    // Frame fields (Optional - NULL when no frames match)
    pub pk_frame: Option<String>,
    pub str_frame_name: Option<String>,
    pub str_cmd: Option<String>,
    pub str_range: Option<String>,
    pub int_chunk_size: Option<i64>,
    pub str_show: Option<String>,
    pub str_shot: Option<String>,
    pub str_user: Option<String>,
    pub int_uid: Option<i64>,
    pub str_log_dir: Option<String>,
    pub str_layer_name: Option<String>,
    pub int_min_cores: Option<i32>,
    pub int_mem_min_frame: Option<i64>,
    pub int_gpus_min_frame: Option<i64>,
    pub int_gpu_mem_min_frame: Option<i64>,
    pub str_services: Option<String>,
    pub int_layer_cores_max: Option<i32>,
    pub int_version: Option<i32>,
    pub str_loki_url: Option<String>,
    pub ts_updated: Option<DateTime<Utc>>,
}

impl DispatchLayer {
    /// Creates a new DispatchLayer from database models.
    ///
    /// # Arguments
    ///
    /// * `layer` - Layer database model
    /// * `frames` - Vector of frame database models belonging to this layer
    ///
    /// # Returns
    ///
    /// * `DispatchLayer` - New layer instance with converted frames
    pub fn new(layer: DispatchLayerModel, frames: Vec<DispatchFrameModel>) -> Self {
        DispatchLayer {
            id: parse_uuid(&layer.pk_layer),
            job_id: parse_uuid(&layer.pk_job),
            facility_id: parse_uuid(&layer.pk_facility),
            show_id: parse_uuid(&layer.pk_show),
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

/// Batched query that fetches layers with their frames in a single database call.
/// This eliminates the nested database calls that could cause connection pool exhaustion.
static QUERY_LAYERS_WITH_FRAMES: &str = r#"
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
        j.str_loki_url,
        l.str_name as str_layer_name,
        j.str_name as str_job_name,
        j.int_min_cores,
        l.int_mem_min as int_mem_min_frame,
        l.b_threadable,
        l.int_gpus_min as int_gpus_min_frame,
        l.int_gpu_mem_min as int_gpu_mem_min_frame,
        l.str_services,
        l.int_cores_max as int_layer_cores_max,
        f.int_dispatch_order,
        f.int_layer_order,
        f.int_version,
        f.ts_updated,
        -- Accumulate the number of cores that would be consumed
        SUM(l.int_cores_min) OVER (
            PARTITION BY l.pk_layer
            ORDER BY f.int_dispatch_order, f.int_layer_order
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS aggr_job_cores,
        jr.int_max_cores as job_resource_core_limit,
        jr.int_cores as job_resource_consumed_cores,
        -- Add row number to limit frames per layer
        ROW_NUMBER() OVER (
            PARTITION BY l.pk_layer
            ORDER BY f.int_dispatch_order, f.int_layer_order
        ) as frame_rank
    FROM job j
        INNER JOIN layer l ON j.pk_job = l.pk_job
        INNER JOIN frame f ON l.pk_layer = f.pk_layer
        INNER JOIN job_resource jr ON l.pk_job = jr.pk_job
        INNER JOIN layer_stat ls on l.pk_layer = ls.pk_layer
    WHERE j.pk_job = $1
        AND ls.int_waiting_count > 0
        AND string_to_array($2, ' | ') && string_to_array(l.str_tags, ' | ')
        AND f.str_state = 'WAITING'
),
limited_frames AS (
    SELECT * FROM dispatch_frames
    WHERE frame_rank <= $3  -- limit frames per layer
        AND (job_resource_core_limit <= 0 OR (aggr_job_cores + job_resource_consumed_cores <= job_resource_core_limit))
)
SELECT DISTINCT
    -- Layer fields
    l.pk_layer,
    j.pk_job,
    j.pk_facility,
    j.pk_show,
    l.str_name as layer_name,
    j.str_name as job_name,
    j.str_os,
    l.int_cores_min,
    l.int_mem_min,
    l.b_threadable,
    l.int_gpus_min,
    l.int_gpu_mem_min,
    l.str_tags,
    l.int_dispatch_order,

    -- Frame fields (can be NULL if no frames)
    lf.pk_frame,
    lf.str_frame_name,
    lf.str_cmd,
    lf.str_range,
    lf.int_chunk_size,
    lf.str_show,
    lf.str_shot,
    lf.str_user,
    lf.int_uid,
    lf.str_log_dir,
    lf.str_layer_name,
    lf.int_min_cores,
    lf.int_mem_min_frame,
    lf.int_gpus_min_frame,
    lf.int_gpu_mem_min_frame,
    lf.str_services,
    lf.int_layer_cores_max,
    lf.int_version,
    lf.int_dispatch_order,
    lf.int_layer_order,
    lf.str_loki_url,
    lf.ts_updated
FROM job j
    INNER JOIN layer l ON j.pk_job = l.pk_job
    INNER JOIN layer_stat ls on l.pk_layer = ls.pk_layer
    LEFT JOIN limited_frames lf ON l.pk_layer = lf.pk_layer
WHERE j.pk_job = $1
    AND ls.int_waiting_count > 0
    AND string_to_array($2, ' | ') && string_to_array(l.str_tags, ' | ')
ORDER BY
    l.int_dispatch_order,
    lf.int_dispatch_order,
    lf.int_layer_order
"#;

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
    pub async fn new() -> Result<Self> {
        let pool = connection_pool().await.into_diagnostic()?;
        Ok(LayerDao {
            connection_pool: pool,
        })
    }

    /// Fetches layers with their frames in a single batched database query.
    ///
    /// Uses a single SQL query with joins to fetch both layers and their frames,
    /// eliminating nested queries that could exhaust the connection pool. Respects
    /// the configured frame limit per layer.
    ///
    /// # Arguments
    ///
    /// * `pk_job` - UUID of the job to query layers for
    /// * `tags` - Vector of tags to match against layer tags
    ///
    /// # Returns
    ///
    /// * `Ok(Vec<DispatchLayer>)` - Layers with their frames, ordered by dispatch priority
    /// * `Err(sqlx::Error)` - Database query failed
    pub async fn query_layers(
        &self,
        pk_job: Uuid,
        tags: Vec<String>,
    ) -> Result<Vec<DispatchLayer>, sqlx::Error> {
        let combined_models = sqlx::query_as::<_, LayerWithFramesModel>(QUERY_LAYERS_WITH_FRAMES)
            .bind(pk_job.to_string())
            .bind(tags.join(" | ").to_string())
            .bind(CONFIG.queue.dispatch_frames_per_layer_limit as i32)
            .fetch_all(&*self.connection_pool)
            .await?;
        debug!("Got {} frames", combined_models.len());

        Ok(self.group_layers_and_frames(combined_models))
    }

    /// Groups flat query results into layers with their associated frames.
    ///
    /// Transforms the denormalized query results into a structured hierarchy
    /// of layers containing their respective frames.
    ///
    /// # Arguments
    ///
    /// * `models` - Flat list of combined layer+frame records from database
    ///
    /// # Returns
    ///
    /// * `Vec<DispatchLayer>` - Structured layers with grouped frames
    fn group_layers_and_frames(&self, models: Vec<LayerWithFramesModel>) -> Vec<DispatchLayer> {
        let mut layers_map: HashMap<String, (DispatchLayerModel, Vec<DispatchFrameModel>)> =
            HashMap::new();

        for model in models {
            // Extract layer data
            let layer_model = DispatchLayerModel {
                pk_layer: model.pk_layer.clone(),
                pk_job: model.pk_job.clone(),
                pk_facility: model.pk_facility.clone(),
                pk_show: model.pk_show.clone(),
                str_name: model.layer_name.clone(),
                str_job_name: model.job_name.clone(),
                str_os: model.str_os.clone(),
                int_cores_min: model.int_cores_min,
                int_mem_min: model.int_mem_min,
                b_threadable: model.b_threadable,
                int_gpus_min: model.int_gpus_min,
                int_gpu_mem_min: model.int_gpu_mem_min,
                str_tags: model.str_tags.clone(),
            };

            // Extract frame data (if present)
            let frame_model = if let Some(pk_frame) = model.pk_frame {
                Some(DispatchFrameModel {
                    pk_frame,
                    str_frame_name: model.str_frame_name.unwrap_or_default(),
                    pk_show: model.pk_show.clone(),
                    pk_facility: model.pk_facility.clone(),
                    pk_job: model.pk_job.clone(),
                    pk_layer: model.pk_layer.clone(),
                    str_cmd: model.str_cmd.unwrap_or_default(),
                    str_range: model.str_range.unwrap_or_default(),
                    int_chunk_size: model.int_chunk_size.unwrap_or(1),
                    str_show: model.str_show.unwrap_or_default(),
                    str_shot: model.str_shot.unwrap_or_default(),
                    str_user: model.str_user.unwrap_or_default(),
                    int_uid: model.int_uid,
                    str_log_dir: model.str_log_dir.unwrap_or_default(),
                    str_layer_name: model.str_layer_name.unwrap_or_default(),
                    str_job_name: model.job_name.clone(),
                    int_min_cores: model.int_min_cores.unwrap_or(100), // default core multiplier
                    int_mem_min: model.int_mem_min_frame.unwrap_or(0),
                    b_threadable: model.b_threadable,
                    int_gpus_min: model.int_gpus_min_frame.unwrap_or(0),
                    int_gpu_mem_min: model.int_gpu_mem_min_frame.unwrap_or(0),
                    str_services: model.str_services,
                    str_os: model.str_os.clone(),
                    int_layer_cores_max: model.int_layer_cores_max.unwrap_or(0),
                    int_version: model.int_version.unwrap_or(1),
                    str_loki_url: model.str_loki_url,
                    ts_updated: model.ts_updated,
                })
            } else {
                None
            };

            // Group by layer_id
            let layer_entry = layers_map
                .entry(model.pk_layer.clone())
                .or_insert((layer_model, vec![]));

            if let Some(frame) = frame_model {
                layer_entry.1.push(frame);
            }
        }

        // Convert to DispatchLayer objects
        layers_map
            .into_values()
            .map(|(layer_model, frame_models)| DispatchLayer::new(layer_model, frame_models))
            .collect()
    }

    /// Checks if a layer has available capacity under its configured limits.
    ///
    /// Verifies that the sum of running frames across all layers sharing the same
    /// limit record is below the maximum allowed value. Returns false if the layer
    /// is at its limit, preventing further frame dispatch.
    ///
    /// # Arguments
    ///
    /// * `transaction` - Active database transaction
    /// * `layer` - Layer to check limits for
    ///
    /// # Returns
    ///
    /// * `Ok(true)` - Layer has capacity available or no limits configured
    /// * `Ok(false)` - Layer has reached its limit
    /// * `Err(sqlx::Error)` - Database query failed
    pub async fn check_limits(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        layer: &DispatchLayer,
    ) -> Result<bool, sqlx::Error> {
        let res = sqlx::query(
            r#"
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
                WHERE layer.pk_layer = $1
                    AND sum_running.int_sum_running < limit_record.int_max_value
                    OR sum_running.int_sum_running IS NULL
        "#,
        )
        .bind(layer.id.to_string())
        .fetch_one(&mut **transaction)
        .await;
        // Only return false if the query returns no row, which means the layer queried is at limit
        match res {
            Ok(_) => Ok(true),
            Err(err) => match err {
                sqlx::Error::RowNotFound => Ok(false),
                _ => Err(err),
            },
        }
    }
}
