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

pub mod dao;
pub mod distributor;
pub mod instance;
pub mod leader;
pub mod sync;

use miette::Result;
use tokio::sync::watch;
use tracing::info;

use std::sync::atomic::Ordering;

use crate::cluster::ClusterFeed;
use crate::config::CONFIG;
use crate::metrics::ORCHESTRATOR_ENABLED;

use instance::InstanceManager;
use leader::LeaderElection;
use sync::ClusterSync;

/// Main entry point for orchestrated mode.
///
/// Sets up instance registration, heartbeat, leader election, cluster sync,
/// and then runs the scheduling pipeline. On shutdown (SIGTERM/SIGINT),
/// gracefully drains and deregisters.
///
/// # Arguments
///
/// * `facility` - Optional facility name to scope this instance to a specific facility
/// * `ignore_tags` - Allocation tags to exclude from cluster loading
///
/// # Returns
///
/// * `Ok(())` - Scheduler completed successfully
/// * `Err(miette::Error)` - Fatal error during setup or pipeline execution
pub async fn run(facility: Option<String>, ignore_tags: Vec<String>) -> Result<()> {
    ORCHESTRATOR_ENABLED.store(true, Ordering::Relaxed);

    // Shutdown signal: send `true` to stop all loops
    let (shutdown_tx, shutdown_rx) = watch::channel(false);

    // 1. Register this instance
    let instance_mgr = InstanceManager::new(facility).await?;
    instance_mgr.register().await?;

    info!(
        instance_id = %instance_mgr.instance_id,
        "Starting orchestrated mode"
    );

    // 2. Create an empty ClusterFeed — clusters will be populated by the sync loop
    let cluster_feed = ClusterFeed::empty();

    // 3. Start heartbeat loop
    let heartbeat_handle = instance_mgr.start_heartbeat(shutdown_rx.clone());

    // 4. Start leader election + distribution loop
    let leader_election = LeaderElection::new(instance_mgr.dao().clone());
    let leader_handle = leader_election.start(ignore_tags, shutdown_rx.clone());

    // 5. Start cluster sync loop (worker side)
    let sync_handle = ClusterSync::start(
        instance_mgr.instance_id,
        instance_mgr.dao().clone(),
        cluster_feed.clone(),
        shutdown_rx.clone(),
    );

    // 6. Set up SIGTERM/SIGINT handler for graceful shutdown
    let shutdown_tx_clone = shutdown_tx.clone();
    let shutdown_handle = tokio::spawn(async move {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to listen for ctrl-c");
        info!("Received shutdown signal");
        let _ = shutdown_tx_clone.send(true);
    });

    // 7. Run the pipeline — this blocks until the feed is stopped
    let pipeline_result = crate::pipeline::run(cluster_feed).await;

    // 8. Graceful shutdown sequence
    info!("Pipeline stopped, initiating shutdown...");
    let _ = shutdown_tx.send(true);

    // Wait for background tasks with a timeout
    let timeout = CONFIG.orchestrator.shutdown_timeout;
    let _ = tokio::time::timeout(timeout, async {
        let _ = heartbeat_handle.await;
        let _ = leader_handle.await;
        let _ = sync_handle.await;
    })
    .await;

    // Deregister this instance
    instance_mgr.shutdown().await;

    shutdown_handle.abort();

    pipeline_result
}
