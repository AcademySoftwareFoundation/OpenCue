use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};

use crate::{
    allocation::{AllocationService, allocation_service},
    cluster::Cluster,
    cluster_key::Tag,
    config::CONFIG,
    dao::LayerDao,
    host_cache::{HostCacheService, host_cache_service, messages::*},
    models::{CoreSize, DispatchJob, DispatchLayer, Host},
    pipeline::dispatcher::{
        RqdDispatcherService,
        error::DispatchError,
        messages::{DispatchLayerMessage, DispatchResult},
        rqd_dispatcher_service,
    },
};
use actix::Addr;
use miette::{Context, Result};
use tokio::sync::Semaphore;
use tracing::{debug, error, info, warn};

pub static HOST_CYCLES: AtomicUsize = AtomicUsize::new(0);

/// Event handler for booking jobs to available hosts.
///
/// This handler orchestrates the job dispatch process by:
/// - Processing incoming dispatch jobs
/// - Finding eligible layers within each job
/// - Matching layers to available host candidates
/// - Dispatching frames to selected hosts via the RQD dispatcher
pub struct MatchingService {
    host_service: Addr<HostCacheService>,
    layer_dao: LayerDao,
    dispatcher_service: Addr<RqdDispatcherService>,
    concurrency_semaphore: Arc<Semaphore>,
    allocation_service: Arc<AllocationService>,
}

impl MatchingService {
    /// Creates a new MatchingService with configured DAOs and dispatcher.
    ///
    /// Initializes the service with:
    /// - Host cache service for finding available hosts
    /// - Layer DAO for querying job layers
    /// - RQD dispatcher service for frame execution
    /// - Concurrency semaphore to limit database transaction pressure
    ///
    /// # Returns
    ///
    /// * `Ok(MatchingService)` - Configured matching service
    /// * `Err(miette::Error)` - Failed to initialize dependencies
    pub async fn new() -> Result<Self> {
        let layer_dao = LayerDao::new().await?;
        let host_service = host_cache_service().await?;
        // let max_concurrent_transactions = 2;
        let max_concurrent_transactions = CONFIG.database.pool_size as usize * 3 / 5;
        let dispatcher_service = rqd_dispatcher_service().await?;
        let allocation_service = allocation_service()
            .await
            .wrap_err("Failed to initialize AllocationService for MatchingService")?;

        Ok(MatchingService {
            host_service,
            layer_dao,
            dispatcher_service,
            concurrency_semaphore: Arc::new(Semaphore::new(max_concurrent_transactions)),
            allocation_service,
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
    ///
    /// * `job` - The dispatch job containing layers to process
    pub async fn process(&self, job: DispatchJob) {
        let job_disp = format!("{}", job);
        let cluster = Arc::new(job.source_cluster);

        let layers = self
            .layer_dao
            .query_layers(
                job.id,
                cluster.tags().map(|tag| &tag.name).cloned().collect(),
            )
            .await;

        match layers {
            Ok(layers) => {
                let processed_layers = AtomicUsize::new(0);

                // Stream elegible layers from this job and dispatch one by one
                for layer in layers {
                    let layer_disp = format!("{}", layer);
                    // TODO: Properly handle errors and remove unwrap
                    let _permit = self.concurrency_semaphore.acquire().await.unwrap();

                    let cluster = cluster.clone();
                    self.process_layer(layer, cluster).await;
                    debug!("{}: Processed layer", layer_disp);
                    processed_layers.fetch_add(1, Ordering::Relaxed);
                }
                // TODO: Evaluate if handling transaction during panic is necesssary here

                if processed_layers.load(Ordering::Relaxed) == 0 {
                    warn!("Job {} didn't process any layer", job_disp);
                }
            }
            Err(err) => {
                error!("Failed to query layers. {}", err);
            }
        }
    }

    /// Validates whether a host is suitable for a specific layer.
    ///
    /// Currently a placeholder that always returns true. Will be implemented to check
    /// subscription limits and other host-layer compatibility rules.
    ///
    /// # Arguments
    ///
    /// * `_host` - The host to validate
    /// * `_layer_id` - The layer ID to validate against
    ///
    /// # Returns
    ///
    /// * `bool` - True if the match is valid
    fn validate_match(
        host: &Host,
        _layer_id: String,
        show_id: String,
        cores_requested: CoreSize,
        allocation_service: Arc<AllocationService>,
    ) -> bool {
        // Check subscription limits for this host allocation

        if let Some(subscription) =
            allocation_service.get_subscription(&host.allocation_name, &show_id)
        {
            if !subscription.bookable(&cores_requested) {
                return false;
            }
        } else {
            return false;
        };

        true
    }

    /// Filters cluster tags to include only those that are also present in the dispatch layer tags.
    ///
    /// # Arguments
    ///
    /// * `cluster` - The cluster containing available tags
    /// * `dispatch_layer` - The layer with tag requirements
    ///
    /// # Returns
    ///
    /// * `Vec<Tag>` - Tags that exist in both the cluster and the dispatch layer
    fn filter_matching_tags(cluster: &Cluster, dispatch_layer: &DispatchLayer) -> Vec<Tag> {
        // Extract tags from cluster and filter by layer tags
        match cluster {
            Cluster::ComposedKey(cluster_key) => {
                if dispatch_layer.tags.contains(cluster_key.tag.name.as_str()) {
                    vec![cluster_key.tag.clone()]
                } else {
                    vec![]
                }
            }
            Cluster::TagsKey(cluster_tags) => cluster_tags
                .iter()
                .filter(|tag| dispatch_layer.tags.contains(tag.name.as_str()))
                .cloned()
                .collect(),
        }
    }

    /// Processes a single layer by finding host candidates and attempting dispatch.
    ///
    /// The process:
    /// 1. Checks out host candidates from the host cache
    /// 2. Attempts dispatch on each candidate until successful or attempts exhausted
    /// 3. Handles various dispatch errors (resource exhaustion, allocation limits, etc.)
    /// 4. Returns hosts back to the cache after use
    ///
    /// # Arguments
    ///
    /// * `dispatch_layer` - The layer to dispatch to a host
    /// * `cluster` - The cluster context for this dispatch operation
    async fn process_layer(&self, dispatch_layer: DispatchLayer, cluster: Arc<Cluster>) {
        let mut try_again = true;
        let mut attempts = CONFIG.queue.host_candidate_attemps_per_layer;

        // Use Option to handle ownership transfer cleanly
        let mut current_layer_version = Some(dispatch_layer);

        while try_again && attempts > 0 {
            HOST_CYCLES.fetch_add(1, Ordering::Relaxed);

            // Take ownership of the layer for this iteration
            let layer = current_layer_version
                .take()
                .expect("Layer should be available");

            // Filter layer tags to match the scope of the cluster in context
            let tags = Self::filter_matching_tags(&cluster, &layer);
            assert!(
                !tags.is_empty(),
                "Layer shouldn't be here if it doesn't contain at least one matching tag"
            );
            debug!(
                "{}: Getting a host candidate for {}, {}",
                layer, layer.facility_id, layer.show_id
            );

            let layer_id = layer.id.clone();
            let show_id = layer.show_id.clone();
            let cores_requested = layer.cores_min;
            let allocation_service = self.allocation_service.clone();
            let host_candidate = self
                .host_service
                .send(CheckOut {
                    facility_id: layer.facility_id.clone(),
                    show_id: layer.show_id.clone(),
                    tags,
                    cores: layer.cores_min,
                    memory: layer.mem_min,
                    validation: move |host| {
                        Self::validate_match(
                            host,
                            layer_id.clone(),
                            show_id.clone(),
                            cores_requested,
                            allocation_service.clone(),
                        )
                    },
                })
                .await
                .expect("Host Cache actor is unresponsive");

            match host_candidate {
                Ok(CheckedOutHost(cluster_key, host)) => {
                    let host_before_dispatch = host.clone();
                    // Store layer info for error logging before moving ownership
                    let layer_display = format!("{}", layer);
                    let layer_job_id = layer.job_id.clone();

                    match self
                        .dispatcher_service
                        .send(DispatchLayerMessage {
                            layer, // Move ownership here
                            host,
                        })
                        .await
                        .expect("Dispatcher actor is unresponsive")
                    {
                        Ok(DispatchResult {
                            updated_host,
                            updated_layer,
                            dispatched_frames: _,
                        }) => {
                            // Stop on the first successful attempt
                            self.host_service
                                .send(CheckIn(cluster_key, updated_host))
                                .await
                                .expect("Host Cache actor is unresponsive");

                            if updated_layer.frames.is_empty() {
                                debug!("Layer {} fully consumed.", updated_layer,);
                                try_again = false;
                            } else {
                                debug!(
                                    "Layer {} not fully consumed. {} frames left",
                                    updated_layer,
                                    updated_layer.frames.len()
                                );
                                // Put the updated layer back for the next iteration
                                current_layer_version = Some(updated_layer);
                            }
                        }
                        Err(err) => {
                            // On error, we lost the layer since it was moved to DispatchLayerMessage
                            // This means we can't continue with this layer
                            Self::log_dispatch_error_with_info(
                                err,
                                &layer_display,
                                &layer_job_id,
                                &host_before_dispatch,
                            );
                            self.host_service
                                .send(CheckIn(cluster_key, host_before_dispatch))
                                .await
                                .expect("Host Cache actor is unresponsive");
                            try_again = false; // Can't continue without the layer
                        }
                    };
                }
                Err(err) => {
                    // Put the layer back since we didn't use it
                    current_layer_version = Some(layer);

                    match err {
                        crate::host_cache::HostCacheError::NoCandidateAvailable => {
                            warn!(
                                "No host candidate available for layer {}",
                                current_layer_version.as_ref().unwrap()
                            );
                            try_again = false;
                        }
                        crate::host_cache::HostCacheError::FailedToQueryHostCache(err) => {
                            panic!("Cache is no longer able to access the database. {}", err)
                        }
                    }
                }
            }
            attempts -= 1;
        }
    }

    /// Handles various dispatch errors with appropriate logging and actions.
    ///
    /// Uses pre-computed layer info since the layer ownership may have been moved.
    /// Different error types result in different log levels and recovery strategies.
    ///
    /// # Arguments
    ///
    /// * `error` - The dispatch error that occurred
    /// * `layer_display` - Pre-computed display string for the layer
    /// * `layer_job_id` - The job ID from the layer
    /// * `host` - The host that the dispatch was attempted on
    fn log_dispatch_error_with_info(
        error: DispatchError,
        layer_display: &str,
        layer_job_id: &str,
        host: &Host,
    ) {
        match error {
            DispatchError::HostLock(host_name) => {
                info!("Failed to acquire lock for host {}", host_name)
            }
            DispatchError::Failure(report) => {
                error!(
                    "Failed to dispatch {} on {}. {}",
                    layer_display,
                    host,
                    report.to_string()
                );
            }
            DispatchError::AllocationOverBurst(allocation_name) => {
                let msg = format!(
                    "Skiping host in this selection for {}. Allocation {} is over burst.",
                    layer_job_id, allocation_name
                );
                info!(msg);
            }
            DispatchError::FailureAfterDispatch(report) => {
                // TODO: Implement a recovery logic for when a frame got dispatched
                // but its status hasn't been updated on the database
                let msg = format!(
                    "Failed after dispatch {} on {}. {}",
                    layer_display, host, report
                );
                error!(msg);
            }
            DispatchError::FailedToStartOnDb(report) => {
                error!(
                    "Failed to Start frame on Database when dispatching {} on {}. {}",
                    layer_display,
                    host,
                    report.to_string()
                );
            }
            DispatchError::DbFailure(error) => {
                error!(
                    "Failed to Start due to database error when dispatching {} on {}. {}",
                    layer_display,
                    host,
                    error.to_string()
                );
            }
            DispatchError::FailureGrpcConnection(_, report) => {
                error!(
                    "{} failed to create a GRPC connection to {}. {}",
                    layer_display, host, report
                );
            }
            DispatchError::GrpcFailure(status) => {
                error!(
                    "{} failed to create execute grpc command on {}. {}",
                    layer_display, host, status
                );
            }
        }
    }
}
