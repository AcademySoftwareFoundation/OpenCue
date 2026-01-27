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

use std::{collections::HashMap, time::SystemTime};

use bytesize::{ByteSize, KB};
use chrono::{DateTime, Utc};
use miette::{Diagnostic, Result};
use opencue_proto::job::FrameExitStatus;
use prost::Message;
use sqlx::{Postgres, Transaction};
use thiserror::Error;

use crate::{
    config::CONFIG,
    dao::helpers::parse_uuid,
    models::{CoreSize, DispatchFrame, VirtualProc},
};

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
#[derive(sqlx::FromRow)]
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
    pub int_min_cores: i64,
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
    pub str_loki_url: Option<String>,
    pub ts_updated: Option<DateTime<Utc>>,

    // Env fields
    pub job_env: HashMap<String, String>,
    pub layer_env: HashMap<String, String>,
}

impl From<DispatchFrameModel> for DispatchFrame {
    fn from(val: DispatchFrameModel) -> Self {
        // Little closure to match a frames' list of services to the hardcode list of
        // selfish services.
        //
        // TODO: The definitive solution for selfish services will require changes to the db,
        // which at this moment would greatly impact the ability to deploy this scheduler on
        // an active render farm. For now, read the list of servives from the config file,
        // similar to Cuebot's approach
        let has_selfish_service = |services: Vec<String>| {
            CONFIG
                .queue
                .selfish_services
                .iter()
                .any(|item| services.contains(item))
        };
        // Convert to SystemTime
        let updated_at = match val.ts_updated {
            Some(t) => SystemTime::from(t),
            None => SystemTime::now(),
        };

        // Combine job and layer envs as Frame has no interest on where envs came from
        let mut env = val.job_env;
        env.extend(val.layer_env);

        DispatchFrame {
            id: parse_uuid(&val.pk_frame),
            frame_name: val.str_frame_name,
            show_id: parse_uuid(&val.pk_show),
            facility_id: parse_uuid(&val.pk_facility),
            job_id: parse_uuid(&val.pk_job),
            layer_id: parse_uuid(&val.pk_layer),
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
            min_cores: CoreSize::from_multiplied(
                val.int_min_cores
                    .try_into()
                    .expect("layer.int_cores_min should fix i32"),
            ),
            threadable: val.b_threadable,
            min_gpus: val
                .int_gpus_min
                .try_into()
                .expect("int_gpus_min should fit on a i32"),
            min_gpu_memory: ByteSize::kb(val.int_gpu_mem_min as u64),
            min_memory: ByteSize::kb(val.int_mem_min as u64),
            services: val.str_services.clone(),
            os: val.str_os,
            loki_url: val.str_loki_url,
            layer_cores_limit: (val.int_layer_cores_max > 0)
                .then(|| CoreSize::from_multiplied(val.int_layer_cores_max)),
            has_selfish_service: has_selfish_service(
                val.str_services
                    .map(|services| services.split(",").map(|v| v.to_string()).collect())
                    .unwrap_or_default(),
            ),
            version: val.int_version as u32,
            updated_at,
            env,
        }
    }
}

static UPDATE_FRAME_STARTED: &str = r#"
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
"#;

static UPDATE_RETRY_COUNT: &str = r#"
UPDATE frame SET
    int_retries = int_retries + 1
WHERE pk_frame = $1
    AND int_exit_status != ALL($2)
"#;

impl FrameDao {
    /// Creates a new FrameDao instance.
    ///
    /// # Returns
    ///
    /// * `Ok(FrameDao)` - New DAO instance
    /// * `Err(miette::Error)` - Initialization failed
    pub async fn new() -> Result<Self> {
        // This is only here to keep a similar interface with other DAO modules
        Ok(FrameDao {})
    }

    /// Updates a frame's state to RUNNING and assigns it to a host.
    ///
    /// Atomically transitions a frame from WAITING to RUNNING state, recording
    /// the host assignment and reserved resources. Uses optimistic locking via
    /// version field to prevent race conditions. Also respects layer limits.
    ///
    /// # Arguments
    ///
    /// * `transaction` - Database transaction for atomic update
    /// * `virtual_proc` - Virtual proc containing frame and host assignment details
    ///
    /// # Returns
    ///
    /// * `Ok(())` - Frame successfully started
    /// * `Err(miette::Error)` - Database update failed or frame no longer available
    pub async fn update_frame_started(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        virtual_proc: &VirtualProc,
    ) -> Result<(), FrameDaoError> {
        let result = sqlx::query(UPDATE_FRAME_STARTED)
            .bind(virtual_proc.host_name.clone())
            .bind(virtual_proc.cores_reserved.value())
            .bind((virtual_proc.memory_reserved.as_u64() / KB) as i32)
            .bind(virtual_proc.gpus_reserved as i32)
            .bind((virtual_proc.gpu_memory_reserved.as_u64() / KB) as i32)
            .bind(virtual_proc.frame.id.to_string())
            .bind(virtual_proc.frame.version as i32)
            .execute(&mut **transaction)
            .await
            .map_err(FrameDaoError::DbFailure)?;

        // Check if the update actually modified a row
        if result.rows_affected() == 0 {
            return Err(FrameDaoError::FrameCouldNotBeUpdated);
        }

        // Update retry count for frames that have been previously executed
        let non_retriable_codes = &[
            FrameExitStatus::SkipRetry as i32,
            FrameExitStatus::FailedLaunch as i32,
            // Values predefined at Cuebot on Dispatcher.java
            299, // EXIT_STATUS_FRAME_CLEARED
            301, // EXIT_STATUS_FRAME_ORPHAN
            302, // EXIT_STATUS_FAILED_KILL
            399, // EXIT_STATUS_DOWN_HOST
            -1,  // Not set (This will skip frames that have never ran)
        ];
        let _ = sqlx::query(UPDATE_RETRY_COUNT)
            .bind(virtual_proc.frame.id.to_string())
            .bind(non_retriable_codes)
            .execute(&mut **transaction)
            .await
            .map_err(FrameDaoError::DbFailure)?;

        Ok(())
    }
}

#[derive(Debug, Error, Diagnostic)]
pub enum FrameDaoError {
    #[error("Failed to lock frame for update. Frame possibly changed before being dispatched")]
    FrameCouldNotBeUpdated,

    #[error("Failed to execute query")]
    DbFailure(sqlx::Error),
}
