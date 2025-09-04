use std::{collections::HashSet, sync::Arc};

use crate::{
    cluster::Cluster,
    cluster_key::Tag,
    config::CONFIG,
    dao::{FrameDao, HostDao, LayerDao},
    host_cache::{HostCacheService, host_cache_service},
    job_dispatcher::{DispatchError, dispatcher::RqdDispatcher},
    models::{DispatchJob, DispatchLayer, Host},
};
use futures::StreamExt;
use miette::Result;
use tracing::{debug, error, info, warn};

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
        let cluster = Arc::new(job.source_cluster);

        // Stream elegible layers from this job and dispatch one by one
        stream
            .for_each_concurrent(CONFIG.queue.stream.layer_buffer_size, |layer_model| {
                let cluster = cluster.clone();
                async {
                    let layer: Result<DispatchLayer, _> = layer_model.map(|l| l.into());
                    match layer {
                        Ok(dispatch_layer) => self.process_layer(dispatch_layer, cluster).await,
                        Err(err) => {
                            error!("Failed to query layers. {}", err);
                        }
                    }
                }
            })
            .await;
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
        // Parse dispatch layer tags from comma-separated string
        let layer_tag_names: HashSet<&str> = dispatch_layer
            .tags
            .split(',')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .collect();

        // Extract tags from cluster and filter by layer tags
        match cluster {
            Cluster::ComposedKey(cluster_key) => {
                if layer_tag_names.contains(cluster_key.tag.name.as_str()) {
                    vec![cluster_key.tag.clone()]
                } else {
                    vec![]
                }
            }
            Cluster::TagsKey(cluster_tags) => cluster_tags
                .iter()
                .filter(|tag| layer_tag_names.contains(tag.name.as_str()))
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
    async fn process_layer(&self, dispatch_layer: DispatchLayer, cluster: Arc<Cluster>) {
        let mut try_again = false;
        let mut attempts = CONFIG.queue.host_candidate_attemps_per_layer;
        while try_again && attempts > 0 {
            // Filter layer tags to match the scope of the cluster in context
            let tags = Self::filter_matching_tags(&cluster, &dispatch_layer);
            let host_candidate = self
                .host_service
                .checkout(
                    dispatch_layer.facility_id,
                    dispatch_layer.show_id,
                    tags,
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
                        Ok(_) => {
                            // Stop on the first successful attempt
                            try_again = false;
                        }
                        Err(err) => {
                            // Attempt next candidate in any failure case
                            attempts -= 1;
                            Self::log_dispatch_error(err, &dispatch_layer, &host);
                        }
                    };
                    self.host_service.checkin(cluster_key, host);
                }
                Err(err) => match err {
                    crate::host_cache::HostCacheError::KeyNotFoundError(cluster_key) => {
                        warn!(
                            "ClusterKey={} not found when attempting to dispatch layer {}",
                            cluster_key, dispatch_layer
                        );
                        try_again = false;
                    }
                    crate::host_cache::HostCacheError::NoCandidateAvailable => {
                        warn!("No host candidate available for layer {}", dispatch_layer);
                        try_again = false;
                    }
                },
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
