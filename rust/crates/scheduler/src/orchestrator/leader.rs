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

use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use tokio::sync::watch;
use tokio::task::JoinHandle;
use tracing::{error, info, warn};

use crate::config::CONFIG;

use super::dao::OrchestratorDao;
use super::distributor::Distributor;

/// Well-known advisory lock ID for the orchestrator leader.
/// "OpenCue" encoded as hex digits: 0x4F70656E437565
const ORCHESTRATOR_LOCK_ID: i64 = 0x4F70656E437565;

/// Manages leader election via PostgreSQL advisory locks and runs the distribution
/// loop when this instance is the leader.
pub struct LeaderElection {
    dao: Arc<OrchestratorDao>,
    is_leader: Arc<AtomicBool>,
}

impl LeaderElection {
    /// Creates a new leader election manager.
    ///
    /// # Arguments
    ///
    /// * `dao` - Shared orchestrator DAO for advisory lock operations
    pub fn new(dao: Arc<OrchestratorDao>) -> Self {
        LeaderElection {
            dao,
            is_leader: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Returns whether this instance is currently the leader.
    #[allow(dead_code)]
    pub fn is_leader(&self) -> bool {
        self.is_leader.load(Ordering::Relaxed)
    }

    /// Returns a cloned `Arc<AtomicBool>` that reflects the current leader status.
    ///
    /// Useful for sharing the leader flag with other tasks that need to check
    /// leadership without holding a reference to the `LeaderElection` struct.
    #[allow(dead_code)]
    pub fn is_leader_flag(&self) -> Arc<AtomicBool> {
        self.is_leader.clone()
    }

    /// Starts the leader election and distribution loop.
    ///
    /// Continuously tries to acquire the advisory lock. Once acquired, runs the
    /// distributor loop. If the lock is lost (e.g., PG connection drops), demotes
    /// self and re-enters election.
    ///
    /// # Arguments
    ///
    /// * `ignore_tags` - Allocation tags to exclude from cluster loading during distribution
    /// * `shutdown` - Watch receiver that signals when the loop should stop
    ///
    /// # Returns
    ///
    /// A `JoinHandle` for the spawned election/distribution task.
    pub fn start(
        &self,
        ignore_tags: Vec<String>,
        mut shutdown: watch::Receiver<bool>,
    ) -> JoinHandle<()> {
        let dao = self.dao.clone();
        let is_leader = self.is_leader.clone();
        let election_interval = CONFIG.orchestrator.election_interval;
        let distribution_interval = CONFIG.orchestrator.distribution_interval;
        let failure_threshold = CONFIG.orchestrator.failure_threshold;

        tokio::spawn(async move {
            let mut distributor = Distributor::new();

            loop {
                // Check for shutdown
                if *shutdown.borrow() {
                    info!("Leader election loop shutting down");
                    break;
                }

                if is_leader.load(Ordering::Relaxed) {
                    // We are the leader — run one distribution cycle
                    match distributor
                        .distribute(&dao, &ignore_tags, failure_threshold)
                        .await
                    {
                        Ok(()) => {}
                        Err(e) => {
                            error!("Distribution cycle failed: {}", e);
                            // If distribution fails, it might be a DB issue.
                            // Demote and re-enter election after interval.
                            is_leader.store(false, Ordering::Relaxed);
                            warn!("Demoted from leader due to distribution failure");
                            crate::metrics::set_orchestrator_is_leader(false);
                        }
                    }

                    // Wait for next distribution cycle or shutdown
                    tokio::select! {
                        _ = tokio::time::sleep(distribution_interval) => {}
                        _ = shutdown.changed() => {
                            info!("Leader loop received shutdown signal");
                            break;
                        }
                    }
                } else {
                    // Not leader — try to acquire the lock
                    match dao.try_acquire_leader_lock(ORCHESTRATOR_LOCK_ID).await {
                        Ok(true) => {
                            info!("Acquired leader lock — this instance is now the leader");
                            is_leader.store(true, Ordering::Relaxed);
                            crate::metrics::set_orchestrator_is_leader(true);
                            // Reset distributor state for fresh snapshots
                            distributor = Distributor::new();
                            // Seed assignment ages from existing DB assignments so they
                            // get a full TTL grace period before redistribution
                            match dao.get_all_assignments().await {
                                Ok(assignments) => distributor.seed_ages(&assignments),
                                Err(e) => warn!("Failed to seed assignment ages: {}", e),
                            }
                        }
                        Ok(false) => {
                            // Another instance holds the lock
                        }
                        Err(e) => {
                            warn!("Failed to attempt leader lock acquisition: {}", e);
                        }
                    }

                    // Wait before retrying election or shutdown
                    tokio::select! {
                        _ = tokio::time::sleep(election_interval) => {}
                        _ = shutdown.changed() => {
                            info!("Election loop received shutdown signal");
                            break;
                        }
                    }
                }
            }

            // On shutdown, demote
            is_leader.store(false, Ordering::Relaxed);
            crate::metrics::set_orchestrator_is_leader(false);
        })
    }
}
