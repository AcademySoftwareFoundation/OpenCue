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

use miette::{IntoDiagnostic, Result, WrapErr};
use tokio::sync::watch;
use tokio::task::JoinHandle;
use tracing::{error, info, warn};
use uuid::Uuid;

use crate::cluster::get_facility_id;
use crate::config::CONFIG;
use crate::metrics::JOBS_QUERIED_TOTAL;

use super::dao::OrchestratorDao;

/// Manages this scheduler instance's lifecycle in the orchestrator registry.
///
/// Handles registration, periodic heartbeat updates, and graceful deregistration.
pub struct InstanceManager {
    pub instance_id: Uuid,
    instance_name: String,
    /// Resolved facility UUID (as string), or None if unscoped.
    facility_id: Option<String>,
    capacity: i32,
    dao: Arc<OrchestratorDao>,
}

impl InstanceManager {
    /// Creates a new instance manager and establishes a database connection.
    ///
    /// Generates a unique instance ID, builds an instance name from hostname and PID,
    /// and initializes the orchestrator DAO for database operations.
    /// If a facility name is provided, it is resolved to its UUID immediately.
    ///
    /// # Arguments
    ///
    /// * `facility_name` - Optional facility name to scope this instance to a specific facility
    ///
    /// # Returns
    ///
    /// * `Ok(InstanceManager)` - Successfully created instance manager
    /// * `Err(miette::Error)` - Failed to establish database connection or resolve facility name
    pub async fn new(facility_name: Option<String>) -> Result<Self> {
        let instance_id = Uuid::new_v4();
        let hostname = gethostname::gethostname().to_string_lossy().to_string();
        let pid = std::process::id();
        let instance_name = format!("{}:{}", hostname, pid);
        let capacity = CONFIG.orchestrator.capacity as i32;
        let dao = Arc::new(OrchestratorDao::new().await?);

        let facility_id = match &facility_name {
            Some(name) => Some(
                get_facility_id(name)
                    .await
                    .wrap_err_with(|| format!("facility '{}' not found", name))?
                    .to_string(),
            ),
            None => None,
        };

        Ok(InstanceManager {
            instance_id,
            instance_name,
            facility_id,
            capacity,
            dao,
        })
    }

    /// Creates an instance manager with an externally provided DAO.
    /// Useful for testing with an embedded database.
    pub fn with_dao(dao: Arc<OrchestratorDao>, facility_id: Option<String>, capacity: i32) -> Self {
        let instance_id = Uuid::new_v4();
        let hostname = gethostname::gethostname().to_string_lossy().to_string();
        let pid = std::process::id();
        let instance_name = format!("{}:{}", hostname, pid);
        InstanceManager {
            instance_id,
            instance_name,
            facility_id,
            capacity,
            dao,
        }
    }

    /// Registers this instance in the scheduler_instance table.
    ///
    /// Inserts a row with the instance's ID, name, facility, and capacity so that
    /// the leader can discover it during distribution cycles.
    ///
    /// # Returns
    ///
    /// * `Ok(())` - Instance registered successfully
    /// * `Err(miette::Error)` - Database insert failed
    pub async fn register(&self) -> Result<()> {
        self.dao
            .register_instance(
                self.instance_id,
                &self.instance_name,
                self.facility_id.as_deref(),
                self.capacity,
            )
            .await
            .into_diagnostic()?;
        info!(
            instance_id = %self.instance_id,
            name = %self.instance_name,
            facility_id = ?self.facility_id,
            capacity = self.capacity,
            "Registered scheduler instance"
        );
        Ok(())
    }

    /// Starts the heartbeat loop.
    ///
    /// Spawns a background task that periodically updates this instance's heartbeat
    /// timestamp and jobs_queried counter in the database. Runs until the shutdown
    /// signal is received.
    ///
    /// # Arguments
    ///
    /// * `shutdown` - Watch receiver that signals when the loop should stop
    ///
    /// # Returns
    ///
    /// A `JoinHandle` for the spawned heartbeat task.
    pub fn start_heartbeat(&self, mut shutdown: watch::Receiver<bool>) -> JoinHandle<()> {
        self.start_heartbeat_with_interval(CONFIG.orchestrator.heartbeat_interval, shutdown)
    }

    /// Starts the heartbeat loop with an explicit interval.
    /// Useful for testing with fast intervals without depending on CONFIG.
    pub fn start_heartbeat_with_interval(
        &self,
        interval: std::time::Duration,
        mut shutdown: watch::Receiver<bool>,
    ) -> JoinHandle<()> {
        let instance_id = self.instance_id;
        let dao = self.dao.clone();

        tokio::spawn(async move {
            let mut ticker = tokio::time::interval(interval);
            loop {
                tokio::select! {
                    _ = ticker.tick() => {
                        let jobs_queried = JOBS_QUERIED_TOTAL.get();
                        if let Err(e) = dao.update_heartbeat(instance_id, jobs_queried).await {
                            error!(instance_id = %instance_id, "Failed to update heartbeat: {}", e);
                        }
                    }
                    _ = shutdown.changed() => {
                        info!(instance_id = %instance_id, "Heartbeat loop shutting down");
                        break;
                    }
                }
            }
        })
    }

    /// Gracefully shuts down this instance: marks as draining, then deletes the row.
    pub async fn shutdown(&self) {
        info!(instance_id = %self.instance_id, "Initiating graceful shutdown");

        if let Err(e) = self.dao.set_draining(self.instance_id).await {
            warn!(instance_id = %self.instance_id, "Failed to set draining: {}", e);
        }

        if let Err(e) = self.dao.delete_instance(self.instance_id).await {
            warn!(instance_id = %self.instance_id, "Failed to delete instance: {}", e);
        }

        info!(instance_id = %self.instance_id, "Instance deregistered");
    }

    /// Returns a reference to the shared orchestrator DAO.
    pub fn dao(&self) -> &Arc<OrchestratorDao> {
        &self.dao
    }
}
