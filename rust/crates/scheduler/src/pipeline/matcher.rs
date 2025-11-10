use std::{
    sync::{
        atomic::{AtomicUsize, Ordering},
        Arc,
    },
    time::Duration,
};

use crate::{
    allocation::{allocation_service, AllocationService},
    cluster::Cluster,
    cluster_key::Tag,
    config::CONFIG,
    dao::LayerDao,
    host_cache::{host_cache_service, messages::*, HostCacheService},
    metrics,
    models::{CoreSize, DispatchJob, DispatchLayer, Host},
    pipeline::{
        dispatcher::{
            error::DispatchError,
            messages::{DispatchLayerMessage, DispatchResult},
            rqd_dispatcher_service, RqdDispatcherService,
        },
        layer_permit::{layer_permit_service, LayerPermitService, Release, Request},
    },
};
use actix::Addr;
use miette::{Context, Result};
use tokio::sync::Semaphore;
use tracing::{debug, error, info, trace};

pub static HOSTS_ATTEMPTED: AtomicUsize = AtomicUsize::new(0);
pub static WASTED_ATTEMPTS: AtomicUsize = AtomicUsize::new(0);

/// Event handler for booking jobs to available hosts.
///
/// This handler orchestrates the job dispatch process by:
/// - Processing incoming dispatch jobs
/// - Finding eligible layers within each job
/// - Matching layers to available host candidates
/// - Dispatching frames to selected hosts via the RQD dispatcher
pub struct MatchingService {
    host_service: Addr<HostCacheService>,
    layer_permit_service: Addr<LayerPermitService>,
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
        let layer_permit_service = layer_permit_service().await?;

        // Limiting the concurrency here is necessary to avoid consuming the entire
        // database connection pool
        let max_concurrent_transactions = (CONFIG.database.pool_size as usize).saturating_sub(1);

        let dispatcher_service = rqd_dispatcher_service().await?;
        let allocation_service = allocation_service()
            .await
            .wrap_err("Failed to initialize AllocationService for MatchingService")?;

        Ok(MatchingService {
            host_service,
            layer_permit_service,
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
                    // Limiting the concurrency here is necessary to avoid consuming the entire
                    // database connection pool
                    let _permit = self
                        .concurrency_semaphore
                        .acquire()
                        .await
                        .expect("Semaphore shouldn't be closed");

                    let cluster = cluster.clone();

                    // Holding a permit for a layer is intended to eliminate a race condition
                    // between concurrent cluster_rounds attempting to process the same layer.
                    // The race condition is mitigated, but not complitely avoided, as the permit
                    // is acquired after the layers and frames have been queried. Acquiring the
                    // permit before querying would require breaking 'query_layers' into separate
                    // queries, one per layer, which greatly impacts performance. The rare cases
                    // that race each other are controlled by the frame.int_version lock on
                    // frame_dao.lock_for_update
                    let layer_permit = self
                        .layer_permit_service
                        .send(Request {
                            id: layer.id.clone(),
                            duration: Duration::from_secs(2 * layer.frames.len() as u64),
                        })
                        .await
                        .expect("Layer permit service is not available");

                    if layer_permit {
                        let layer_id = layer.id.clone();
                        self.process_layer(layer, cluster).await;
                        debug!("{}: Processed layer", layer_disp);

                        self.layer_permit_service
                            .send(Release { id: layer_id })
                            .await
                            .expect("Layer permit service is not available");

                        processed_layers.fetch_add(1, Ordering::Relaxed);
                    } else {
                        debug!(
                            "Layer skipped. {} already being processed by another task.",
                            layer
                        );
                    }
                }

                if processed_layers.load(Ordering::Relaxed) == 0 {
                    WASTED_ATTEMPTS.fetch_add(1, Ordering::Relaxed);
                    debug!("Job {} didn't process any layer", job_disp);
                }
            }
            Err(err) => {
                error!("Failed to query layers. {:?}", err);
            }
        }
    }

    /// Validates whether a host is suitable for a specific layer.
    ///
    /// Subscriptions: Check whether this hosts' subscription can book at least one frame
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
        _layer_id: &str,
        show_id: &str,
        cores_requested: CoreSize,
        allocation_service: &AllocationService,
        os: Option<&str>,
    ) -> bool {
        // Check OS compatibility
        if host.str_os.as_deref() != os {
            return false;
        }

        if let Some(subscription) =
            allocation_service.get_subscription(&host.allocation_name, &show_id.to_string())
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
        let initial_attempts = attempts;

        // Use Option to handle ownership transfer cleanly
        let mut current_layer_version = Some(dispatch_layer);

        while try_again && attempts > 0 {
            attempts -= 1;
            HOSTS_ATTEMPTED.fetch_add(1, Ordering::Relaxed);

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
            trace!(
                "{}: Getting a host candidate for {}, {}",
                layer,
                layer.facility_id,
                layer.show_id
            );

            // Clone only the minimal data needed for the validation closure
            // These are needed because the closure must have 'static lifetime for actor messaging
            let layer_id = layer.id.clone();
            let show_id = layer.show_id.clone();
            let cores_requested = layer.cores_min;
            let allocation_service = self.allocation_service.clone();
            let os = layer.str_os.clone();

            let host_candidate = self
                .host_service
                .send(CheckOut {
                    facility_id: layer.facility_id.clone(),
                    show_id: layer.show_id.clone(),
                    tags,
                    cores: cores_requested,
                    memory: layer.mem_min,
                    validation: move |host| {
                        Self::validate_match(
                            host,
                            &layer_id,
                            &show_id,
                            cores_requested,
                            &allocation_service,
                            os.as_deref(),
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
                        }) => {
                            self.host_service
                                .send(CheckIn(cluster_key, updated_host))
                                .await
                                .expect("Host Cache actor is unresponsive");

                            if updated_layer.frames.is_empty() {
                                // Stop on the first successful attempt
                                debug!("Layer {} fully consumed.", updated_layer,);
                                // Track how many candidates were needed to fully consume this layer
                                let candidates_used = initial_attempts - attempts + 1;
                                metrics::observe_candidates_per_layer(candidates_used);
                                try_again = false;
                            } else {
                                debug!(
                                    "Layer {} not fully consumed. {} frames left",
                                    updated_layer,
                                    updated_layer.frames.len()
                                );
                                try_again = true;
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
                            debug!(
                                "No host candidate available for layer {}",
                                current_layer_version.as_ref().unwrap()
                            );
                            metrics::increment_no_candidate_iterations();
                            try_again = false;
                        }
                        crate::host_cache::HostCacheError::FailedToQueryHostCache(err) => {
                            panic!("Cache is no longer able to access the database. {}", err)
                        }
                    }
                }
            }
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
                    "{:?}",
                    report.wrap_err(format!("Failed to dispatch {} on {}.", layer_display, host))
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
                error!(
                    "{:?}",
                    report.wrap_err(format!("Failed to dispatch {} on {}.", layer_display, host))
                );
            }
            DispatchError::FailedToStartOnDb(sqlx_error) => {
                error!(
                    "Failed to Start frame on Database when dispatching {} on {}. {:?}",
                    layer_display, host, sqlx_error
                );
            }
            DispatchError::DbFailure(error) => {
                error!(
                    "Failed to Start due to database error when dispatching {} on {}. {:?}",
                    layer_display, host, error
                );
            }
            DispatchError::FailureGrpcConnection(_, report) => {
                error!(
                    "{:?}",
                    report.wrap_err(format!(
                        "{} failed to create a GRPC connection to {}.",
                        layer_display, host
                    ))
                );
            }
            DispatchError::GrpcFailure(status) => {
                error!(
                    "{} failed to create execute grpc command on {}. {:?}",
                    layer_display, host, status
                );
            }
        }
    }
}
