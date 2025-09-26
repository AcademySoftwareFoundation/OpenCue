use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};

use crate::{
    cluster::Cluster,
    cluster_key::Tag,
    config::CONFIG,
    dao::{FrameDao, HostDao, LayerDao},
    host_cache::{HostCacheService, host_cache_service},
    models::{DispatchJob, DispatchLayer, Host},
    pgpool::begin_transaction,
    pipeline::dispatcher::{RqdDispatcher, error::DispatchError},
};
use miette::Result;
use sqlx::{Postgres, Transaction};
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
    host_service: Arc<HostCacheService>,
    layer_dao: LayerDao,
    dispatcher: RqdDispatcher,
    concurrency_semaphore: Arc<Semaphore>,
}

impl MatchingService {
    /// Creates a new BookJobEventHandler with configured DAOs and dispatcher.
    ///
    /// Initializes the handler with:
    /// - Host DAO for finding available hosts
    /// - Layer DAO for querying job layers
    /// - RQD dispatcher for frame execution
    pub async fn new() -> Result<Self> {
        let host_dao = Arc::new(HostDao::from_config(&CONFIG.database).await?);
        let frame_dao = Arc::new(FrameDao::from_config(&CONFIG.database).await?);
        let layer_dao = LayerDao::new(&CONFIG.database, frame_dao.clone()).await?;
        let host_service = host_cache_service().await?;
        // let max_concurrent_transactions = 2;
        let max_concurrent_transactions = CONFIG.database.pool_size as usize * 3 / 5;

        let dispatcher = RqdDispatcher::new(
            frame_dao,
            host_dao.clone(),
            CONFIG.rqd.grpc_port,
            CONFIG.queue.memory_stranded_threshold,
            CONFIG.rqd.dry_run_mode,
        );
        Ok(MatchingService {
            host_service,
            layer_dao,
            dispatcher,
            concurrency_semaphore: Arc::new(Semaphore::new(max_concurrent_transactions)),
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
        let job_disp = format!("{}", job);
        let cluster = Arc::new(job.source_cluster);

        // Acquire a transaction for this branch
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
                    debug!("{}: Trying to get a permit to work on", layer);
                    // TODO: Properly handle errors and remove unwrap
                    let _permit = self.concurrency_semaphore.acquire().await.unwrap();
                    debug!("{}: Got a permit to work on", layer);

                    let mut trans = begin_transaction(&CONFIG.database).await.unwrap();
                    debug!("{}: Started a transaction", layer);
                    let cluster = cluster.clone();
                    self.process_layer(layer, cluster, &mut trans).await;
                    debug!("{}: Processed layer", layer_disp);
                    processed_layers.fetch_add(1, Ordering::Relaxed);

                    if let Err(err) = trans.commit().await {
                        error!("Failed to commit job {} transaction. {}", job_disp, err);
                    }
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

    fn validate_match(_host: &Host, _layer: &DispatchLayer) -> bool {
        // todo!("define layer validation rule (copy from host_dao old query)")
        // Check subscription limits for this host allocation
        true
    }

    /// Filters cluster tags to include only those that are also present in the dispatch layer tags.
    ///
    /// # Arguments
    /// * `cluster` - The cluster containing available tags
    /// * `dispatch_layer` - The layer with comma-separated tag requirements
    ///
    /// # Returns
    /// A vector of tags that exist in both the cluster and the dispatch layer
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
    /// 1. Queries host candidates suitable for the layer
    /// 2. Attempts dispatch on each candidate until successful
    /// 3. Handles various dispatch errors (resource exhaustion, allocation limits, etc.)
    ///
    /// # Arguments
    /// * `dispatch_layer` - The layer to dispatch to a host
    async fn process_layer(
        &self,
        dispatch_layer: DispatchLayer,
        cluster: Arc<Cluster>,
        transaction: &mut Transaction<'_, Postgres>,
    ) {
        let mut try_again = true;
        let mut attempts = CONFIG.queue.host_candidate_attemps_per_layer;
        let mut current_layer_version = dispatch_layer;

        while try_again && attempts > 0 {
            HOST_CYCLES.fetch_add(1, Ordering::Relaxed);
            // Filter layer tags to match the scope of the cluster in context
            let tags = Self::filter_matching_tags(&cluster, &current_layer_version);
            assert!(
                !tags.is_empty(),
                "Layer shouldn't be here if it doesn't contain at least one matching tag"
            );
            debug!(
                "{}: Getting a host candidate for {}, {}",
                current_layer_version,
                current_layer_version.facility_id,
                current_layer_version.show_id
            );
            let host_candidate = self
                .host_service
                .check_out(
                    current_layer_version.facility_id.clone(),
                    current_layer_version.show_id.clone(),
                    tags,
                    current_layer_version.cores_min,
                    current_layer_version.mem_min,
                    |host| Self::validate_match(host, &current_layer_version),
                )
                .await;
            debug!("{}: Got a host candidate", current_layer_version);

            match host_candidate {
                Ok((cluster_key, host)) => {
                    debug!(
                        "Attempting host candidate {} for job {}",
                        host, &current_layer_version
                    );

                    let host_before_dispatch = host.clone();
                    match self
                        .dispatcher
                        .dispatch(&current_layer_version, host, transaction)
                        .await
                    {
                        Ok((updated_host, updated_dispatch_layer)) => {
                            // Stop on the first successful attempt
                            self.host_service.check_in(cluster_key, updated_host);
                            if updated_dispatch_layer.frames.is_empty() {
                                debug!("Layer {} fully consumed.", updated_dispatch_layer,);
                                try_again = false;
                            } else {
                                debug!(
                                    "Layer {} not fully consumed. {} frames left",
                                    updated_dispatch_layer,
                                    updated_dispatch_layer.frames.len()
                                )
                            }
                            current_layer_version = updated_dispatch_layer;
                        }
                        Err(err) => {
                            // Attempt next candidate in any failure case
                            Self::log_dispatch_error(
                                err,
                                &current_layer_version,
                                &host_before_dispatch,
                            );
                            self.host_service
                                .check_in(cluster_key, host_before_dispatch);
                        }
                    };
                }
                Err(err) => match err {
                    crate::host_cache::HostCacheError::NoCandidateAvailable => {
                        warn!(
                            "No host candidate available for layer {}",
                            current_layer_version
                        );
                        try_again = false;
                    }
                    crate::host_cache::HostCacheError::FailedToQueryHostCache(err) => {
                        panic!("Cache is no longer able to access the database. {}", err)
                    }
                },
            }
            attempts -= 1;
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
            DispatchError::FailedToStartOnDb(report) => {
                error!(
                    "Failed to Start frame on Database when dispatching {} on {}. {}",
                    dispatch_layer,
                    host,
                    report.to_string()
                );
            }
            DispatchError::DbFailure(error) => {
                error!(
                    "Failed to Start due to database error when dispatching {} on {}. {}",
                    dispatch_layer,
                    host,
                    error.to_string()
                );
            }
        }
    }
}
