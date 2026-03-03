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

use tokio::sync::watch;
use tokio::task::JoinHandle;
use tracing::{debug, error, info};
use uuid::Uuid;

use crate::cluster::{Cluster, ClusterFeed};
use crate::config::CONFIG;

use super::dao::OrchestratorDao;

/// Worker-side cluster synchronization.
///
/// Periodically polls `scheduler_cluster_assignment` for this instance's assigned clusters
/// and updates the local `ClusterFeed` accordingly.
pub struct ClusterSync;

impl ClusterSync {
    /// Starts the cluster sync polling loop.
    ///
    /// Polls the database for assigned clusters and updates the ClusterFeed's internal
    /// cluster list. The pipeline's round-robin stream automatically picks up the changes.
    ///
    /// # Arguments
    ///
    /// * `instance_id` - UUID of this scheduler instance to query assignments for
    /// * `dao` - Shared orchestrator DAO for database queries
    /// * `cluster_feed` - Shared cluster feed to update with assigned clusters
    /// * `shutdown` - Watch receiver that signals when the loop should stop
    ///
    /// # Returns
    ///
    /// A `JoinHandle` for the spawned sync polling task.
    pub fn start(
        instance_id: Uuid,
        dao: Arc<OrchestratorDao>,
        cluster_feed: Arc<ClusterFeed>,
        mut shutdown: watch::Receiver<bool>,
    ) -> JoinHandle<()> {
        let poll_interval = CONFIG.orchestrator.poll_interval;

        tokio::spawn(async move {
            let mut ticker = tokio::time::interval(poll_interval);

            loop {
                tokio::select! {
                    _ = ticker.tick() => {
                        match dao.get_assignments_for_instance(instance_id).await {
                            Ok(assignments) => {
                                let clusters: Vec<Cluster> = assignments
                                    .into_iter()
                                    .filter_map(|row| {
                                        match serde_json::from_str::<Cluster>(&row.str_cluster) {
                                            Ok(cluster) => Some(cluster),
                                            Err(e) => {
                                                error!(
                                                    "Failed to deserialize cluster assignment: {}. JSON: {}",
                                                    e, row.str_cluster
                                                );
                                                None
                                            }
                                        }
                                    })
                                    .collect();

                                let count = clusters.len();
                                cluster_feed.update_clusters(clusters);
                                crate::metrics::set_orchestrator_assigned_clusters(count);

                                debug!(
                                    instance_id = %instance_id,
                                    "Synced {} cluster assignment(s)",
                                    count
                                );
                            }
                            Err(e) => {
                                error!(
                                    instance_id = %instance_id,
                                    "Failed to poll cluster assignments: {}",
                                    e
                                );
                            }
                        }
                    }
                    _ = shutdown.changed() => {
                        info!(instance_id = %instance_id, "Cluster sync loop shutting down");
                        break;
                    }
                }
            }
        })
    }
}
