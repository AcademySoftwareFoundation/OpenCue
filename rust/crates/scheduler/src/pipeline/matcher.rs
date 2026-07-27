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

use std::{
    sync::{
        atomic::{AtomicUsize, Ordering},
        Arc,
    },
    time::Duration,
};

use uuid::Uuid;

use crate::{
    accounting::{accounting_service, AccountingService},
    cluster::{Cluster, FeedMessage},
    cluster_key::{Tag, TagType},
    config::CONFIG,
    dao::LayerDao,
    host_cache::{host_cache_service, messages::*, HostCacheService},
    metrics,
    models::{DispatchJob, DispatchLayer, Host},
    pipeline::{
        dispatcher::{
            error::DispatchError,
            messages::{DispatchLayerMessage, DispatchResult},
            rqd_dispatcher_service, RqdDispatcherService,
        },
        layer_permit::{layer_permit_service, LayerPermitService, Release, Request},
        placement::{self, LayerProfile},
    },
};
use actix::Addr;
use miette::Result;
use tokio::sync::{mpsc, Semaphore};
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
    accounting: Arc<AccountingService>,
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
        let accounting = accounting_service().await?;

        // Limiting the concurrency here is necessary to avoid consuming the entire
        // database connection pool
        let max_concurrent_transactions = (CONFIG.database.pool_size as usize).saturating_sub(1);

        let dispatcher_service = rqd_dispatcher_service().await?;

        Ok(MatchingService {
            host_service,
            layer_permit_service,
            layer_dao,
            dispatcher_service,
            concurrency_semaphore: Arc::new(Semaphore::new(max_concurrent_transactions)),
            accounting,
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
    /// * `feed_sender` - Control channel for the cluster feed; used by
    ///   `process_layer` to sleep the cluster when the (show, alloc)
    ///   subscription is over burst (Alloc clusters + managed shows only).
    ///
    /// # Returns
    ///
    /// Number of frames dispatched for this job. The caller uses this to back
    /// the cluster off when an entire pass dispatches nothing.
    pub async fn process(
        &self,
        job: DispatchJob,
        feed_sender: &mpsc::Sender<FeedMessage>,
    ) -> usize {
        let job_disp = format!("{}", job);
        let cluster = Arc::new(job.source_cluster);
        let mut frames_dispatched = 0;

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
                            id: layer.id,
                            duration: Duration::from_secs(2 * layer.frames.len() as u64),
                        })
                        .await
                        .expect("Layer permit service is not available");

                    if layer_permit {
                        let layer_id = layer.id;
                        frames_dispatched += self.process_layer(layer, cluster, feed_sender).await;
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
        frames_dispatched
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
    /// * `feed_sender` - Control channel for sleeping the cluster on
    ///   pre-checkout over-burst detection.
    ///
    /// # Returns
    ///
    /// Number of frames dispatched for this layer.
    async fn process_layer(
        &self,
        dispatch_layer: DispatchLayer,
        cluster: Arc<Cluster>,
        feed_sender: &mpsc::Sender<FeedMessage>,
    ) -> usize {
        let mut frames_dispatched: usize = 0;
        let mut try_again = true;
        let mut attempts = CONFIG.queue.host_candidate_attempts_per_layer;
        let initial_attempts = attempts;

        // E-PVM live-usage snapshot taken once at permit entry (design Branch 2a).
        // Locally incremented per dispatched frame within the while-loop. The store
        // returns booked cores directly (already in cores, not centicores), so do NOT
        // apply `from_multiplied` here. A non-managed/unseen job reads 0, leaving the cap
        // unbounded by live usage but still bounded by `job_max_cores`.
        let initial_job_cores_in_use =
            self.accounting.job_cores_in_use(dispatch_layer.job_id) as i32;
        let mut local_job_cores_booked: i32 = 0;

        // Job-level at-cap pre-check. The job's core cap is enforced
        // authoritatively by the accounting check in the dispatcher, but a
        // job sitting at its cap would otherwise be re-checked-out and re-rejected
        // up to host_candidate_attempts_per_layer times every pass (see the retry
        // loop below). Skip it cheaply here, reusing the live `initial_job_cores_in_use`
        // snapshot read above. Unlike the subscription skip below, we do NOT sleep
        // the cluster: the job cap is per-job and sibling jobs in this cluster may
        // still be dispatchable. Fail-open: a failed store read left
        // `initial_job_cores_in_use` at 0, so the guard simply won't fire and the
        // booking call stays authoritative.
        if placement::job_at_core_cap(
            initial_job_cores_in_use,
            dispatch_layer.cores_min.value(),
            dispatch_layer.job_max_cores,
        ) {
            metrics::increment_job_cap_precheck_skip();
            debug!(
                "Skipping layer {} pre-checkout: job over core cap \
                 (job={}, in_use={}, requested={}, cap={})",
                dispatch_layer,
                dispatch_layer.job_id,
                initial_job_cores_in_use,
                dispatch_layer.cores_min.value(),
                dispatch_layer.job_max_cores,
            );
            return frames_dispatched;
        }

        // (show, alloc) subscription burst snapshot — Alloc clusters + managed
        // shows only. `Cluster::single_tag` is built once per (facility, show,
        // alloc.str_tag) row and the SQL join `host_tag.str_tag = alloc.str_tag`
        // guarantees the chosen host is in that allocation, so the alloc_id on
        // the single Tag IS the alloc the dispatched host will be in. For
        // Manual/HostName/Hardware clusters and CLI-built alloc tags
        // (alloc_id = None), we fall back to the burst-unaware behavior
        // (show_burst = 0 → treated as "unlimited" by `compute_max_more`).
        let alloc_id_opt = if self
            .accounting
            .managed_shows()
            .contains(&dispatch_layer.show_id)
            && cluster.tags.len() == 1
        {
            cluster
                .tags
                .iter()
                .next()
                .filter(|tag| tag.ttype == TagType::Alloc)
                .and_then(|tag| tag.alloc_id)
        } else {
            None
        };
        let (initial_show_cores_in_use, show_burst): (i32, i32) = match alloc_id_opt {
            Some(alloc_id) => {
                // Both counters are already in cores (the conversion from PG centicores
                // happens at the store-seed boundary), so do NOT apply `from_multiplied`
                // here. The booking call remains authoritative on the actual decision.
                let (booked, burst) = self.accounting.sub_counters(dispatch_layer.show_id, alloc_id);
                (booked as i32, burst as i32)
            }
            None => (0, 0),
        };

        // Pre-checkout over-burst skip. When the snapshot says the requested
        // cores won't fit under burst, sleep the cluster for the same duration
        // as the empty-cluster back-off and return without scanning the host
        // cache or pinging the dispatcher. A stale "over burst" read costs at
        // most a single cluster_empty_sleep window of latency on this cluster
        // and self-corrects on the next wake; the booking call remains
        // authoritative on the actual booking.
        if show_burst > 0
            && initial_show_cores_in_use.saturating_add(dispatch_layer.cores_min.value())
                > show_burst
        {
            metrics::increment_accounting_limit_exceeded("subscription");
            debug!(
                "Skipping layer {} pre-checkout: subscription over burst \
                 (show={}, alloc={:?}, booked={}, requested={}, burst={}); \
                 sleeping cluster {}",
                dispatch_layer,
                dispatch_layer.show_id,
                alloc_id_opt,
                initial_show_cores_in_use,
                dispatch_layer.cores_min.value(),
                show_burst,
                cluster,
            );
            let _ = feed_sender
                .send(FeedMessage::Sleep(
                    (*cluster).clone(),
                    CONFIG.queue.cluster_empty_sleep,
                ))
                .await;
            return frames_dispatched;
        }
        let mut local_show_cores_booked: i32 = 0;

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

            // Subscription burst pre-check was removed in PR-C: the booking call inside
            // `dispatch_virtual_proc` is now the authoritative gate. An over-burst (show, alloc)
            // produces a single wasted dispatch attempt - design accepts that trade-off (see
            // §2.1 and the PR-C plan; restoring the optimization would require an async
            // validation hook on the host_cache actor or a per-process subscription mirror).
            //
            // TODO: if over-burst attempts become a measurable perf drag, add a precomputed
            // per-layer store snapshot of (show, alloc) → bookable and consult it here.
            let cores_requested = layer.cores_min;
            let (gate, weights) = match CONFIG.queue.host_booking_strategy {
                crate::config::HostBookingStrategy::Epvm { weights, .. } => (
                    placement::epvm_gate as crate::host_cache::cache::Gate,
                    weights,
                ),
                crate::config::HostBookingStrategy::Saturation { .. } => (
                    placement::saturation_gate as crate::host_cache::cache::Gate,
                    Default::default(),
                ),
            };
            // `show_burst` / `show_cores_in_use` come from the per-(show, alloc)
            // store snapshot taken above. They're populated for managed shows on
            // Alloc clusters (where the chosen host's allocation is deterministic
            // from the cluster's single Tag), and 0 otherwise — in which case
            // `compute_max_more`'s `> 0` guards treat the cap as "unlimited" and
            // E-PVM scoring loses the show-burst component of `maxMore`. The
            // authoritative cap remains the accounting check inside the
            // dispatcher; this snapshot is an optimistic input to scoring.
            let profile = LayerProfile {
                cores_min: layer.cores_min,
                mem_min: layer.mem_min,
                gpus_min: layer.gpus_min,
                gpu_mem_min: layer.gpu_mem_min,
                slots_required: layer.slots_required,
                os: layer.str_os.clone(),
                threadable: layer.threadable,
                job_max_cores: layer.job_max_cores,
                show_burst,
                job_cores_in_use: initial_job_cores_in_use + local_job_cores_booked,
                show_cores_in_use: initial_show_cores_in_use + local_show_cores_booked,
                weights,
            };

            let host_candidate = self
                .host_service
                .send(CheckOut {
                    facility_id: layer.facility_id.clone(),
                    show_id: layer.show_id,
                    tags,
                    cores: cores_requested,
                    memory: layer.mem_min,
                    profile,
                    gate,
                })
                .await
                .expect("Host Cache actor is unresponsive");

            match host_candidate {
                Ok(CheckedOutHost(cluster_key, host)) => {
                    let host_before_dispatch = host.clone();
                    // Store layer info for error logging before moving ownership
                    let layer_display = format!("{}", layer);
                    let layer_job_id = layer.job_id;
                    let frames_before_dispatch = layer.frames.len();

                    match self
                        .dispatcher_service
                        .send(DispatchLayerMessage {
                            layer, // Move ownership here
                            host,
                            // Live job usage so the dispatcher can clamp each
                            // frame's reservation to the job's remaining cap.
                            // Same value fed to the LayerProfile above.
                            job_cores_in_use: initial_job_cores_in_use + local_job_cores_booked,
                        })
                        .await
                        .expect("Dispatcher actor is unresponsive")
                    {
                        Ok(DispatchResult {
                            updated_host,
                            updated_layer,
                            cores_booked,
                        }) => {
                            metrics::increment_checkout_outcome("booked");
                            // Track cores actually consumed so the next iteration's
                            // LayerProfile sees the local picture of usage. The same
                            // delta applies to the (show, alloc) subscription burst
                            // since every dispatched frame counts against both caps.
                            // Use the dispatcher's real per-frame reservations
                            // (`cores_booked`) rather than `dispatched * cores_min`:
                            // a threadable frame can reserve far more than `cores_min`
                            // (up to a whole host), so the approximation undercounts
                            // and lets the matcher keep re-checking-out a job that is
                            // already at its cap.
                            let dispatched = frames_before_dispatch
                                .saturating_sub(updated_layer.frames.len())
                                as i32;
                            frames_dispatched += dispatched as usize;
                            local_job_cores_booked += cores_booked;
                            local_show_cores_booked += cores_booked;

                            // Record the outcome by what actually landed, not merely
                            // that the dispatch returned Ok. A dispatch can succeed yet
                            // book zero frames (the job hit its core cap before any frame
                            // fit, or the host went stale between checkout and dispatch);
                            // counting those as "booked" hid the real throughput.
                            metrics::increment_checkout_outcome(if dispatched > 0 {
                                "booked"
                            } else {
                                "no_progress"
                            });

                            self.host_service
                                .send(CheckIn(cluster_key, CheckInPayload::Host(updated_host)))
                                .await
                                .expect("Host Cache actor is unresponsive");

                            if updated_layer.frames.is_empty() {
                                // Layer fully consumed.
                                debug!("Layer {} fully consumed.", updated_layer,);
                                // Track how many candidates were needed to fully consume this layer
                                let candidates_used = initial_attempts - attempts + 1;
                                metrics::observe_candidates_per_layer(candidates_used);
                                try_again = false;
                            } else if dispatched == 0 {
                                // No-progress guard: this dispatch booked nothing (job at
                                // its core cap, or a stale host that fit nothing). Retrying
                                // the same layer on another host this pass would hit the
                                // same wall, so stop instead of burning the remaining
                                // host_candidate_attempts_per_layer on empty checkouts. The
                                // cluster re-queries this job on its next round, so the
                                // layer is deferred, not abandoned.
                                debug!(
                                    "Layer {} made no progress ({} frames left); stopping retries.",
                                    updated_layer,
                                    updated_layer.frames.len()
                                );
                                try_again = false;
                            } else {
                                debug!(
                                    "Layer {} partially consumed. {} frames left",
                                    updated_layer,
                                    updated_layer.frames.len()
                                );
                                try_again = true;
                                // Put the updated layer back for the next iteration
                                current_layer_version = Some(updated_layer);
                            }
                        }
                        Err(err) => {
                            metrics::increment_checkout_outcome("dispatch_error");
                            // On error, we lost the layer since it was moved to DispatchLayerMessage
                            // This means we can't continue with this layer
                            Self::log_dispatch_error_with_info(
                                err,
                                &layer_display,
                                &layer_job_id,
                                &host_before_dispatch,
                            );
                            self.host_service
                                .send(CheckIn(
                                    cluster_key,
                                    CheckInPayload::Invalidate(host_before_dispatch.id),
                                ))
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
                            metrics::increment_checkout_outcome("no_match");
                            debug!(
                                "No host candidate available for layer {}. {:?}",
                                current_layer_version.as_ref().unwrap(),
                                err
                            );
                            metrics::increment_no_candidate_iterations();
                            try_again = false;
                        }
                        crate::host_cache::HostCacheError::FailedToQueryHostCache(err) => {
                            // CRITICAL: Database connection failure in host cache query
                            //
                            // When the host cache cannot query the database, the matching service
                            // cannot reliably find hosts for job dispatch. This is a systemic
                            // failure that affects all job processing.
                            //
                            // We panic here rather than propagating an error because:
                            // 1. The entire service is compromised - no jobs can be matched
                            // 2. Graceful degradation is not possible without host candidates
                            // 3. The orchestration layer (e.g., Kubernetes) should restart the
                            //    service to re-establish database connectivity
                            // 4. Bubbling the error up would add unnecessary complexity for a
                            //    condition that always requires service restart
                            //
                            // This allows the orchestration layer to handle the failure through
                            // its standard restart policies rather than attempting partial recovery.
                            panic!(
                                "Host cache failed to query database - service is non-functional \
                                and requires restart. Error: {}",
                                err
                            )
                        }
                    }
                }
            }
        }
        frames_dispatched
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
