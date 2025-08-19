use std::sync::Arc;

use crate::{
    config::CONFIG,
    dao::{FrameDao, HostDao, LayerDao},
    job_dispatcher::{DispatchError, dispatcher::RqdDispatcher},
    models::{DispatchJob, DispatchLayer, Host},
};
use futures::StreamExt;
use miette::Result;
use tracing::{debug, error, info};

/// Event handler for booking jobs to available hosts.
///
/// This handler orchestrates the job dispatch process by:
/// - Processing incoming dispatch jobs
/// - Finding eligible layers within each job
/// - Matching layers to available host candidates
/// - Dispatching frames to selected hosts via the RQD dispatcher
pub struct BookJobEventHandler {
    host_dao: Arc<HostDao>,
    job_dao: LayerDao,
    dispatcher: RqdDispatcher,
}

impl BookJobEventHandler {
    /// Creates a new BookJobEventHandler with configured DAOs and dispatcher.
    ///
    /// Initializes the handler with:
    /// - Host DAO for finding available hosts
    /// - Layer DAO for querying job layers
    /// - RQD dispatcher for frame execution
    pub async fn new() -> Result<Self> {
        let host_dao = Arc::new(HostDao::from_config(&CONFIG.database).await?);
        let layer_dao = LayerDao::from_config(&CONFIG.database).await?;
        let frame_dao = FrameDao::from_config(&CONFIG.database).await?;

        let dispatcher = RqdDispatcher::new(
            frame_dao,
            host_dao.clone(),
            CONFIG.rqd.grpc_port,
            CONFIG.queue.dispatch_frames_per_layer_limit,
            CONFIG.queue.memory_stranded_threshold.as_u64(),
            CONFIG.rqd.dry_run_mode,
        );
        Ok(BookJobEventHandler {
            host_dao,
            job_dao: layer_dao,
            dispatcher,
        })
    }

    /// Processes a dispatch job by finding and dispatching its eligible layers.
    ///
    /// For each layer in the job:
    /// - Queries eligible layers from the database
    /// - Attempts to find suitable host candidates
    /// - Dispatches frames to available hosts, layer by layer
    ///
    /// # Arguments
    /// * `job` - The dispatch job containing layers to process
    pub async fn process(&self, job: DispatchJob) {
        let mut stream = self.job_dao.query_layers(job.id);
        let mut pending_layers = 0;
        // Stream elegible layers from this job and dispatch one by one
        while let Some(layer_model) = stream.next().await {
            let layer: Result<DispatchLayer, _> = layer_model.map(|l| l.into());
            match layer {
                Ok(dispatch_layer) => {
                    pending_layers += 1;
                    // Give up on this
                    self.process_layer(dispatch_layer).await
                }
                Err(err) => {
                    error!("Failed to query layers. {}", err);
                }
            }
        }

        if pending_layers == 0 {
            info!("Found no pending layers for {}", job);
        }
    }

    /// Processes a single layer by finding host candidates and attempting dispatch.
    ///
    /// The process:
    /// 1. Queries host candidates suitable for the layer
    /// 2. Attempts dispatch on each candidate until successful
    /// 3. Handles various dispatch errors (resource exhaustion, allocation limits, etc.)
    ///
    /// # Arguments
    /// * `dispatch_layer` - The layer to dispatch to a host
    async fn process_layer(&self, dispatch_layer: DispatchLayer) {
        let limit = 10;
        let mut host_candidates_stream = self.host_dao.find_host_for_layer(&dispatch_layer, limit);
        let mut candidates_count = 0;
        let mut choosen_host = None;

        // Attempt to dispatch host candidates and exist on the first successful attempt
        while let Some(host_candidate) = host_candidates_stream.next().await {
            match host_candidate {
                Ok(host_model) => {
                    candidates_count += 1;

                    let host: Host = host_model.into();
                    debug!(
                        "Attempting host candidate {} for job {}",
                        host, dispatch_layer
                    );
                    match self.dispatcher.dispatch(&dispatch_layer, &host).await {
                        // Stop on the first successful attempt
                        // Attempt next candidate in any failure case
                        Ok(_) => {
                            choosen_host.replace(host);
                            break;
                        }
                        Err(DispatchError::HostLock(host_name)) => {
                            info!("Failed to acquire lock for host {}", host_name)
                        }
                        Err(DispatchError::Failure(report)) => {
                            error!(
                                "Failed to dispatch {} on {}. {}",
                                dispatch_layer,
                                host,
                                report.to_string()
                            );
                        }
                        Err(DispatchError::AllocationOverBurst(allocation_name)) => {
                            let msg = format!(
                                "Skiping host in this selection for {}. Allocation {} is over burst.",
                                dispatch_layer.job_id, allocation_name
                            );
                            info!(msg);
                        }
                        Err(DispatchError::FailureAfterDispatch(report)) => {
                            // TODO: Implement a recovery logic for when a frame got dispatched
                            // but its status hasn't been updated on the database
                            let msg = format!(
                                "Failed after dispatch {} on {}. {}",
                                dispatch_layer, host, report
                            );
                            error!(msg);
                        }
                        Err(DispatchError::HostResourcesExtinguished) => {
                            debug!(
                                "Host resources for {} extinguished, skiping to the next candidate",
                                host
                            );
                        }
                    };
                }
                Err(err) => {
                    error!("Failed to query host to dispatch. {}", err);
                }
            }
        }
        if candidates_count == 0 {
            info!("Found no candidate for dispatching {}", dispatch_layer);
        } else if choosen_host.is_none() {
            info!(
                "Attempted {} candidates and found no match for {}",
                limit, dispatch_layer
            );
        }
    }
}
