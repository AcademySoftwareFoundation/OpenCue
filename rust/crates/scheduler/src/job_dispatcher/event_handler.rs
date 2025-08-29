use std::sync::Arc;

use crate::{
    cluster_key::ClusterKey,
    config::CONFIG,
    dao::{FrameDao, HostDao, LayerDao},
    host_cache::{HostCacheService, host_cache_service},
    job_dispatcher::{DispatchError, dispatcher::RqdDispatcher},
    models::{DispatchJob, DispatchLayer, Host},
};
use bytesize::ByteSize;
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
    host_service: Arc<HostCacheService>,
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
        let host_service = host_cache_service().await?;

        let dispatcher = RqdDispatcher::new(
            frame_dao,
            host_dao.clone(),
            CONFIG.rqd.grpc_port,
            CONFIG.queue.dispatch_frames_per_layer_limit,
            CONFIG.queue.memory_stranded_threshold,
            CONFIG.rqd.dry_run_mode,
        );
        Ok(BookJobEventHandler {
            host_service,
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
        let stream = self.job_dao.query_layers(job.id);

        // Stream elegible layers from this job and dispatch one by one
        stream
            .for_each_concurrent(CONFIG.queue.stream.layer_buffer_size, |layer_model| async {
                let layer: Result<DispatchLayer, _> = layer_model.map(|l| l.into());
                match layer {
                    Ok(dispatch_layer) => self.process_layer(dispatch_layer).await,
                    Err(err) => {
                        error!("Failed to query layers. {}", err);
                    }
                }
            })
            .await;
    }

    fn validate_match(host: &Host, layer: &DispatchLayer) -> bool {
        todo!("define layer validation rule (copy from host_dao old query)")
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
        // TODO: Backoff on each attempt
        for _ in 0..10 {
            let host_candidate = self
                .host_service
                .checkout(
                    dispatch_layer.facility_id,
                    dispatch_layer.show_id,
                    dispatch_layer
                        .tags
                        .split(",")
                        .map(|t| t.trim().to_string())
                        .collect(),
                    dispatch_layer.cores_min,
                    dispatch_layer.mem_min,
                    |host| Self::validate_match(host, &dispatch_layer),
                )
                .await;

            match host_candidate {
                Ok((cluster_key, host)) => {
                    debug!(
                        "Attempting host candidate {} for job {}",
                        host, dispatch_layer
                    );
                    match self.dispatcher.dispatch(&dispatch_layer, &host).await {
                        // Stop on the first successful attempt
                        // Attempt next candidate in any failure case
                        Ok(_) => {
                            break;
                        }
                        Err(err) => {
                            Self::log_dispatch_error(err, &dispatch_layer, &host);
                        }
                    };
                    self.host_service.checkin(cluster_key, host);
                }
                Err(_) => todo!(),
            }
        }
    }

    /// Handles various dispatch errors with appropriate logging and actions.
    ///
    /// # Arguments
    /// * `error` - The dispatch error that occurred
    /// * `dispatch_layer` - The layer that failed to dispatch
    /// * `host` - The host that the dispatch was attempted on
    fn log_dispatch_error(error: DispatchError, dispatch_layer: &DispatchLayer, host: &Host) {
        match error {
            DispatchError::HostLock(host_name) => {
                info!("Failed to acquire lock for host {}", host_name)
            }
            DispatchError::Failure(report) => {
                error!(
                    "Failed to dispatch {} on {}. {}",
                    dispatch_layer,
                    host,
                    report.to_string()
                );
            }
            DispatchError::AllocationOverBurst(allocation_name) => {
                let msg = format!(
                    "Skiping host in this selection for {}. Allocation {} is over burst.",
                    dispatch_layer.job_id, allocation_name
                );
                info!(msg);
            }
            DispatchError::FailureAfterDispatch(report) => {
                // TODO: Implement a recovery logic for when a frame got dispatched
                // but its status hasn't been updated on the database
                let msg = format!(
                    "Failed after dispatch {} on {}. {}",
                    dispatch_layer, host, report
                );
                error!(msg);
            }
            DispatchError::HostResourcesExtinguished => {
                debug!(
                    "Host resources for {} extinguished, skiping to the next candidate",
                    host
                );
            }
        }
    }
}
