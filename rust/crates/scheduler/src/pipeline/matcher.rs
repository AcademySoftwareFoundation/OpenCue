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

use std::sync::{
    atomic::{AtomicUsize, Ordering},
    Arc,
};

use uuid::Uuid;

use crate::{
    cluster::Cluster,
    cluster_key::Tag,
    config::CONFIG,
    dao::LayerDao,
    host_cache::{host_cache_service, messages::*, HostCacheService},
    metrics,
    models::{CoreSize, DispatchJob, DispatchLayer, Host},
    pipeline::dispatcher::{
        error::DispatchError,
        messages::{DispatchLayerMessage, DispatchResult},
        rqd_dispatcher_service, RqdDispatcherService,
    },
    resource_accounting::{resource_accounting_service, ResourceAccountingService},
};
use miette::{Context, Result};
use tokio::sync::Semaphore;
use tracing::{debug, error, info, trace, warn};

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
    host_service: HostCacheService,
    layer_dao: LayerDao,
    dispatcher_service: RqdDispatcherService,
    concurrency_semaphore: Arc<Semaphore>,
    resource_accounting_service: Arc<ResourceAccountingService>,
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

        // Each concurrent layer now holds two connections: one for the
        // SKIP LOCKED layer lock (held for the whole dispatch) and one for
        // its per-proc transaction. Halve the semaphore relative to the
        // pool so we don't risk exhausting it.
        let pool_size = CONFIG.database.pool_size as usize;
        let max_concurrent_transactions = (pool_size / 2).saturating_sub(1).max(1);

        let dispatcher_service = rqd_dispatcher_service().await?;
        let resource_accounting_service = resource_accounting_service()
            .await
            .wrap_err("Failed to initialize ResourceAccountingService for MatchingService")?;

        Ok(MatchingService {
            host_service,
            layer_dao,
            dispatcher_service,
            concurrency_semaphore: Arc::new(Semaphore::new(max_concurrent_transactions)),
            resource_accounting_service,
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
                cluster.tags.iter().map(|tag| &tag.name).cloned().collect(),
            )
            .await;

        match layers {
            Ok(layers) => {
                let processed_layers = AtomicUsize::new(0);

                // Stream elegible layers from this job and dispatch one by one
                for layer in layers {
                    let layer_disp = format!("{}", layer);
                    // Limit concurrent layer processing to stay within the DB
                    // connection budget — each layer holds a SKIP-LOCKED lock
                    // transaction plus its per-proc transactions.
                    let _permit = self
                        .concurrency_semaphore
                        .acquire()
                        .await
                        .expect("Semaphore shouldn't be closed");

                    let cluster = cluster.clone();

                    // Try to acquire a row-level SELECT … FOR UPDATE SKIP LOCKED
                    // on the layer. This both deduplicates dispatch across
                    // concurrent schedulers (single-process or multi-replica)
                    // and replaces the in-memory LayerPermitService.
                    let lock_guard = match self.layer_dao.try_lock_layer(layer.id).await {
                        Ok(Some(guard)) => guard,
                        Ok(None) => {
                            debug!(
                                "Layer skipped. {} already being processed by another scheduler.",
                                layer
                            );
                            continue;
                        }
                        Err(err) => {
                            error!("Failed to lock layer {}: {:?}", layer_disp, err);
                            continue;
                        }
                    };

                    self.process_layer(layer, cluster).await;
                    debug!("{}: Processed layer", layer_disp);

                    if let Err(err) = lock_guard.release().await {
                        // Releasing only fails if the connection is dead, in which
                        // case sqlx has already rolled back implicitly so the lock
                        // is gone — log and move on.
                        warn!("Failed to release layer lock for {}: {:?}", layer_disp, err);
                    }

                    processed_layers.fetch_add(1, Ordering::Relaxed);
                }

                if processed_layers.load(Ordering::Relaxed) == 0 {
                    WASTED_ATTEMPTS.fetch_add(1, Ordering::Relaxed);
                    metrics::increment_wasted_attempts();
                    debug!("Job {} didn't process any layer", job_disp);
                }
            }
            Err(err) => {
                error!("Failed to query layers. {:?}", err);
            }
        }
    }

    fn host_matches_layer_os(host: &Host, os: Option<&str>) -> bool {
        os.is_none() || host.str_os.as_deref() == os
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
        _layer_id: &Uuid,
        show_id: &Uuid,
        cores_requested: CoreSize,
        resource_accounting_service: &ResourceAccountingService,
        os: Option<&str>,
    ) -> bool {
        // Check OS compatibility
        if !Self::host_matches_layer_os(host, os) {
            return false;
        }

        if let Some(subscription) =
            resource_accounting_service.get_subscription(&host.alloc_name, show_id)
        {
            if !subscription.can_book(&cores_requested) {
                return false;
            }
        } else {
            return false;
        };

        true
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
        let mut attempts = CONFIG.queue.host_candidate_attempts_per_layer;
        let initial_attempts = attempts;

        // Use Option to handle ownership transfer cleanly
        let mut current_layer_version = Some(dispatch_layer);

        while try_again && attempts > 0 {
            attempts -= 1;
            HOSTS_ATTEMPTED.fetch_add(1, Ordering::Relaxed);
            metrics::increment_hosts_attempted();

            // Take ownership of the layer for this iteration
            let layer = current_layer_version
                .take()
                .expect("Layer should be available");

            // Filter layer tags to match the scope of the cluster in context
            let tags: Vec<Tag> = cluster
                .tags
                .iter()
                .filter(|tag| layer.tags.contains(&tag.name))
                .cloned()
                .collect();

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
            let layer_id = layer.id;
            let show_id = layer.show_id;
            let cores_requested = layer.cores_min;
            let resource_accounting_service = self.resource_accounting_service.clone();
            let os = layer.str_os.clone();

            let host_candidate = self
                .host_service
                .check_out(
                    layer.facility_id,
                    layer.show_id,
                    tags,
                    cores_requested,
                    layer.mem_min,
                    move |host| {
                        Self::validate_match(
                            host,
                            &layer_id,
                            &show_id,
                            cores_requested,
                            &resource_accounting_service,
                            os.as_deref(),
                        )
                    },
                )
                .await;

            match host_candidate {
                Ok(CheckedOutHost(cluster_key, host)) => {
                    let host_before_dispatch = host.clone();
                    // Store layer info for error logging before moving ownership
                    let layer_display = format!("{}", layer);
                    let layer_job_id = layer.job_id;

                    match self
                        .dispatcher_service
                        .dispatch_layer(DispatchLayerMessage {
                            layer, // Move ownership here
                            host,
                        })
                        .await
                    {
                        Ok(DispatchResult {
                            updated_host,
                            updated_layer,
                        }) => {
                            self.host_service.check_in_payload(
                                cluster_key,
                                CheckInPayload::Host(updated_host),
                            );

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
                            self.host_service.check_in_payload(
                                cluster_key,
                                CheckInPayload::Invalidate(host_before_dispatch.id),
                            );
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
                                "No host candidate available for layer {}. {:?}",
                                current_layer_version.as_ref().unwrap(),
                                err
                            );
                            metrics::increment_no_candidate_iterations();
                            try_again = false;
                        }
                        crate::host_cache::HostCacheError::FailedToQueryHostCache(err) => {
                            // Transient DB query failure. The host_cache circuit breaker
                            // applies exponential backoff and will short-circuit further
                            // queries until it recovers. After
                            // CONFIG.host_cache.db_circuit_breaker.failure_threshold
                            // consecutive failures the host cache exits the process cleanly
                            // so the orchestrator (k8s, systemd) restarts us. From the
                            // matcher's perspective we just skip this layer for now —
                            // other clusters keep running, and the next cycle may find
                            // candidates once the breaker closes again.
                            warn!(
                                "Host cache query failed for layer {} — skipping for now: {}",
                                current_layer_version.as_ref().unwrap(),
                                err
                            );
                            try_again = false;
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
        layer_job_id: &Uuid,
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
            DispatchError::FailedToCreateProc {
                error,
                frame_id,
                host_id,
            } => {
                error!(
                    "Failed to create proc for frame {} on host {}. {:?}",
                    frame_id, host_id, error
                );
            }
            DispatchError::FailedToUpdateResources(report) => {
                error!(
                    "{:?}",
                    report.wrap_err(format!(
                        "Failed to update resources for dispatching {} on {}.",
                        layer_display, host
                    ))
                );
            }
            DispatchError::HostResourcesExhausted(_) => {
                info!(
                    "Host resources exhausted before updating database when dispatching {} on {}.",
                    layer_display, host
                );
            }
            DispatchError::ResourceLimitExceeded(msg) => {
                info!(
                    "Resource limit exceeded when dispatching {} on {}: {}",
                    layer_display, host, msg
                );
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use bytesize::ByteSize;
    use opencue_proto::host::ThreadMode;
    use uuid::Uuid;

    use super::MatchingService;
    use crate::models::{CoreSize, Host};

    fn host_with_os(str_os: Option<&str>) -> Host {
        Host::new_for_test(
            Uuid::new_v4(),
            "test-host".to_string(),
            str_os.map(str::to_string),
            CoreSize::from_multiplied(100),
            ByteSize::gb(64),
            CoreSize::from_multiplied(100),
            ByteSize::gb(64),
            0,
            ByteSize::gb(0),
            ThreadMode::Variable,
            CoreSize::from_multiplied(100),
            Uuid::new_v4(),
            "test-alloc".to_string(),
        )
    }

    #[test]
    fn host_matches_when_layer_os_is_not_set() {
        let host = host_with_os(Some("Linux"));

        assert!(MatchingService::host_matches_layer_os(&host, None));
    }

    #[test]
    fn host_matches_when_layer_os_matches_host_os() {
        let host = host_with_os(Some("Linux"));

        assert!(MatchingService::host_matches_layer_os(&host, Some("Linux")));
    }

    #[test]
    fn host_does_not_match_when_layer_os_differs_from_host_os() {
        let host = host_with_os(Some("Linux"));

        assert!(!MatchingService::host_matches_layer_os(
            &host,
            Some("Windows")
        ));
    }
}
