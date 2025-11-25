use actix::{Actor, ActorFutureExt, Handler, ResponseActFuture, WrapFuture};
use bytesize::{ByteSize, MIB};
use chrono::Utc;
use futures::FutureExt;
use miette::{miette, Context, IntoDiagnostic, Result};
use moka::future::Cache;
use sqlx::{Postgres, Transaction};
use std::{collections::HashMap, sync::Arc, time::Duration};
use tonic::transport::Channel;
use tracing::{debug, error, info, trace, warn};
use uuid::Uuid;

use crate::{
    allocation::allocation_service,
    config::CONFIG,
    dao::{FrameDao, FrameDaoError, HostDao, LayerDao, ProcDao, UpdatedHostResources},
    metrics,
    models::{CoreSize, DispatchFrame, DispatchLayer, Host, VirtualProc},
    pgpool::begin_transaction,
    pipeline::dispatcher::{
        error::{DispatchError, DispatchVirtualProcError, VirtualProcError},
        frame_set::FrameSet,
        messages::{DispatchLayerMessage, DispatchResult},
    },
};
use opencue_proto::{
    host::ThreadMode,
    rqd::{rqd_interface_client::RqdInterfaceClient, RqdStaticLaunchFrameRequest, RunFrame},
};

/// Actor wrapper for RqdDispatcher that provides message-based dispatch operations.
///
/// This actor handles:
/// - Message-driven frame dispatching with proper error isolation
/// - gRPC connection management and pooling
/// - Database transaction coordination
/// - Supervision and retry logic for external service failures
#[derive(Clone)]
pub struct RqdDispatcherService {
    frame_dao: Arc<FrameDao>,
    layer_dao: Arc<LayerDao>,
    host_dao: Arc<HostDao>,
    proc_dao: Arc<ProcDao>,
    rqd_connection_cache: Cache<String, RqdInterfaceClient<Channel>>,
    dry_run_mode: bool,
}

impl Actor for RqdDispatcherService {
    type Context = actix::Context<Self>;

    fn started(&mut self, _ctx: &mut Self::Context) {
        info!("RqdDispatcherService actor started");
    }

    fn stopped(&mut self, _ctx: &mut Self::Context) {
        info!("RqdDispatcherService actor stopped");
    }
}

impl Handler<DispatchLayerMessage> for RqdDispatcherService {
    type Result = ResponseActFuture<Self, Result<DispatchResult, DispatchError>>;

    fn handle(&mut self, msg: DispatchLayerMessage, _ctx: &mut Self::Context) -> Self::Result {
        let DispatchLayerMessage { layer, host } = msg;

        let dispatcher = self.clone();
        debug!(
            "Received dispatch message for layer {} on host {}",
            layer.layer_name, host.name
        );

        Box::pin(
            async move {
                // Note: In a real implementation, we would need to coordinate with a transaction manager
                // or pass the transaction through the message. For now, we'll create a new transaction
                // within the dispatcher's database operations.

                // Create a database transaction scope
                let mut transaction = begin_transaction()
                    .await
                    .map_err(DispatchError::DbFailure)?;

                match dispatcher.dispatch(&layer, host, &mut transaction).await {
                    Ok((updated_host, updated_layer)) => {
                        // Commit the transaction
                        transaction
                            .commit()
                            .await
                            .map_err(DispatchError::DbFailure)?;

                        Ok(DispatchResult {
                            updated_host,
                            updated_layer,
                        })
                    }
                    Err(e) => {
                        // Rollback the transaction on error
                        if let Err(rollback_err) = transaction.rollback().await {
                            error!("Failed to rollback transaction: {}", rollback_err);
                        }
                        Err(e)
                    }
                }
            }
            .into_actor(self)
            .map(|result, _actor, _ctx| result),
        )
    }
}

impl RqdDispatcherService {
    /// Creates a new RqdDispatcherService with the specified configuration.
    ///
    /// # Arguments
    /// * `frame_dao` - Database access for frame operations
    /// * `layer_dao` - Database access for layer operations
    /// * `host_dao` - Database access for host operations and locking
    /// * `dry_run_mode` - If true, logs dispatch actions without executing them
    pub async fn new(
        frame_dao: Arc<FrameDao>,
        layer_dao: Arc<LayerDao>,
        host_dao: Arc<HostDao>,
        proc_dao: Arc<ProcDao>,
        dry_run_mode: bool,
    ) -> Result<Self> {
        let rqd_connection_cache = Cache::builder()
            .max_capacity(100)
            // 5 min. (from_hours is still an experimental feature)
            .time_to_idle(Duration::from_secs(5 * 60))
            // 2 hours. (from_hours is still an experimental feature)
            .time_to_live(Duration::from_secs(2 * 60 * 60))
            .build();

        Ok(RqdDispatcherService {
            frame_dao,
            layer_dao,
            host_dao,
            proc_dao,
            dry_run_mode,
            rqd_connection_cache,
        })
    }

    /// Dispatches a layer to a specific host with proper locking and error handling.
    ///
    /// The dispatch process:
    /// 1. Acquires an exclusive lock on the target host
    /// 2. Performs the actual dispatch operation
    /// 3. Ensures the host lock is always released, even on panic or failure
    ///
    /// # Arguments
    /// * `layer` - The layer containing frames to dispatch
    /// * `host` - The target host for frame execution
    ///
    /// # Returns
    /// * `Ok(())` on successful dispatch
    /// * `Err(DispatchError)` on various failure conditions
    async fn dispatch(
        &self,
        layer: &DispatchLayer,
        host: Host,
        transaction: &mut Transaction<'_, Postgres>,
    ) -> Result<(Host, DispatchLayer), DispatchError> {
        let host_id = host.id;
        let host_disp = format!("{}", &host);
        let layer_disp = format!("{}", &layer);

        // Acquire lock first
        if !self
            .host_dao
            .lock(transaction, &host.id)
            .await
            .map_err(DispatchError::Failure)?
        {
            return Err(DispatchError::HostLock(host.name.clone()));
        }

        // Ensure unlock is always called, regardless of panics or fails
        let result = std::panic::AssertUnwindSafe(self.dispatch_inner(layer, host))
            .catch_unwind()
            .await;

        // Always attempt to unlock, regardless of outcome. Failing to unlock here can be ignored as
        // endint the transaction will automatically unlock.
        if let Err(unlock_err) = self.host_dao.unlock(transaction, &host_id).await {
            trace!("Failed to unlock host {}: {}", host_disp, unlock_err);
        }

        // Handle the result from dispatch_inner
        match result {
            Ok(result) => {
                if result.is_ok() {
                    info!(
                        "Successfully dispatched layer {} on {}.",
                        layer_disp, host_disp
                    );
                }
                result
            }
            Err(_panic) => Err(DispatchError::Failure(miette!(
                "Dispatch operation panicked for layer {} on host {}",
                layer_disp,
                host_id
            ))),
        }
    }

    async fn dispatch_inner(
        &self,
        layer: &DispatchLayer,
        host: Host,
    ) -> Result<(Host, DispatchLayer), DispatchError> {
        // A host should not book frames if its allocation is at or above its limit,
        // but checking the limit before each frame is too costly. The tradeoff is
        // to check the allocation state before entering the frame booking loop,
        // with these there's a risk the allocation will go above burst, but not by
        // a great margin as each loop only runs for a limited number of frames
        // (see config queue.dispatch_frames_per_layer_limit)
        let mut allocation_capacity = host.alloc_available_cores;
        let allocation_name = host.alloc_name.clone();
        let mut last_host_version = host;

        let allocation_service = allocation_service().await.map_err(|err| {
            DispatchError::Failure(err.wrap_err("Allocation Service is not available"))
        })?;
        // Use a closure for this validation to reduce the number of arguments that would be passed
        // to dispatch_virtual_proc.
        let is_subscription_bookable = |cores_requested| {
            matches!(allocation_service.get_subscription(&allocation_name, &layer.show_id),
                Some(subscription) if subscription.bookable(&cores_requested)
            )
        };

        // Deliberately cloning the layer to avoid requiring a mutable reference
        let mut layer = layer.clone();
        let mut last_error = None;
        let mut non_retrieable_frames = Vec::new();

        // Use an unique id for all logs on this dispatch
        let dispatch_id = Uuid::new_v4();

        for frame in &layer.frames {
            let frame_str = format!("{}", frame);

            let (virtual_proc, updated_host) = match Self::consume_host_virtual_resources(
                frame,
                &last_host_version,
                CONFIG.queue.memory_stranded_threshold,
            )
            .await
            {
                Ok(result) => result,
                Err(VirtualProcError::HostResourcesExtinguished(msg)) => {
                    debug!(
                        "({dispatch_id}) Host resourse extinguished for {}. {}",
                        last_host_version, msg
                    );
                    break;
                }
            };

            debug!(
                "({dispatch_id}) Host {} will have {} cores available after update",
                updated_host.id, updated_host.idle_cores
            );

            // Each proc should run on its own transaction
            let mut proc_transaction = begin_transaction()
                .await
                .map_err(DispatchError::DbFailure)?;

            // Before dispatching, confirm the layer still has limits
            if !self
                .layer_dao
                .check_limits(&mut proc_transaction, &layer)
                .await
                .map_err(DispatchError::DbFailure)?
            {
                proc_transaction
                    .rollback()
                    .await
                    .map_err(DispatchError::DbFailure)?;
                info!("({dispatch_id}) Skiping layer {}, reached limits", layer);

                // Skip the entire layer
                break;
            }

            match self
                .dispatch_virtual_proc(
                    dispatch_id,
                    virtual_proc,
                    updated_host,
                    &mut proc_transaction,
                    &is_subscription_bookable,
                    allocation_capacity,
                )
                .await
            {
                Ok((new_host, new_allocation_capacity)) => {
                    proc_transaction
                        .commit()
                        .await
                        .map_err(DispatchError::DbFailure)?;

                    // Track successful frame dispatch
                    metrics::increment_frames_dispatched();

                    // Track time from frame updated_at to dispatch
                    if let Ok(elapsed) = frame.updated_at.elapsed() {
                        metrics::observe_time_to_book(elapsed);
                    }

                    non_retrieable_frames.push(frame.id);
                    allocation_capacity = new_allocation_capacity;
                    last_host_version = new_host;
                }
                Err(err) => {
                    proc_transaction
                        .rollback()
                        .await
                        .map_err(DispatchError::DbFailure)?;

                    match err {
                        DispatchVirtualProcError::AllocationOverBurst(err) => {
                            info!("({dispatch_id}) {frame_str} {err}");

                            last_error = Some(err);
                            break;
                        }
                        DispatchVirtualProcError::FailedToStartOnDb(err) => {
                            // Something is not right with this frame on the database. log error and give
                            // the next frame a chance. If there was already an error like this on previous
                            // frames, give up.
                            if last_error.is_some() {
                                break;
                            }
                            warn!(
                                "({dispatch_id}) Failed to start frame {} on Db. {}",
                                frame_str, err
                            );
                            last_error = Some(err);
                            // IMPORTANT: Do NOT update last_host_version here since the transaction
                            // rolled back and we didn't actually consume any resources from the database.
                            // The next iteration should use the same host state as before.
                            continue;
                        }
                        DispatchVirtualProcError::FrameCouldNotBeUpdated => {
                            // The entire transaction is probably compromised, stop working on this layer
                            info!(
                                "({dispatch_id}) Frame {} couldn't be updated on the database. Version has changed.",
                                frame_str
                            );
                            non_retrieable_frames.push(frame.id);
                            break;
                        }
                        DispatchVirtualProcError::RqdConnectionFailed { host, error } => {
                            // An error here means connection with this host is probably broken,
                            // there's no reason to attempt the next frame
                            warn!(
                                "({dispatch_id}) Failed to connect to rqd on {} to launch frame. {:?}",
                                host, error
                            );

                            break;
                        }
                    }
                }
            }
        }

        if non_retrieable_frames.is_empty() {
            info!(
                "Found no frames on {} to dispatch to {}",
                layer, last_host_version
            );
        } else {
            debug!(
                "Dispatched {} frames on {}: ",
                non_retrieable_frames.len(),
                layer
            );
            for proc in &non_retrieable_frames {
                trace!("{}", proc);
            }
        }

        // Only drain successful frames. Failed frames will get retried on the next host candidate
        if !non_retrieable_frames.is_empty() {
            layer.drain_frames(non_retrieable_frames);
        }

        if let Some(error) = last_error {
            warn!("Wasn't able to dispatch all frames: {:?}", error)
        }
        Ok((last_host_version, layer))
    }

    /// Dispatches a virtual proc to a host, handling allocation checks, database updates, and RQD communication.
    ///
    /// This function encapsulates the complete dispatch process for a single virtual proc:
    /// 1. Validates allocation capacity against subscription limits
    /// 2. Updates frame status in the database
    /// 3. Launches the frame on RQD (or logs in dry-run mode)
    /// 4. Updates host resources and proc records in the database
    ///
    /// # Arguments
    /// * `virtual_proc` - The virtual proc to dispatch
    /// * `updated_host` - The host with updated resource allocations
    /// * `transaction` - Database transaction for atomic updates
    /// * `is_subscription_bookable` - Closure to check if subscription can accept more cores
    /// * `allocation_capacity` - Current available allocation capacity
    ///
    /// # Returns
    /// On success, returns a tuple of (updated host, new allocation capacity).
    /// On failure, returns a `DispatchVirtualProcError` indicating the specific failure mode.
    async fn dispatch_virtual_proc(
        &self,
        dispatch_id: Uuid,
        virtual_proc: VirtualProc,
        host: Host,
        transaction: &mut Transaction<'_, Postgres>,
        is_subscription_bookable: &impl Fn(CoreSize) -> bool,
        allocation_capacity: CoreSize,
    ) -> Result<(Host, CoreSize), DispatchVirtualProcError> {
        trace!("({dispatch_id}) Built virtual proc {}", virtual_proc);
        let cores_reserved_without_multiplier: CoreSize = virtual_proc.cores_reserved.into();

        // Check allocation capacity in two ways
        //  - Check the cached subscription to account for external bookings
        //  - Check for cores consumed by this dispatcher iteration
        if !is_subscription_bookable(cores_reserved_without_multiplier)
            || cores_reserved_without_multiplier > allocation_capacity
        {
            return Err(DispatchVirtualProcError::AllocationOverBurst(
                DispatchError::AllocationOverBurst(host.alloc_name.clone()),
            ));
        }
        let new_allocation_capacity = allocation_capacity - virtual_proc.cores_reserved.into();

        // Update database
        let updated_resources = self
            .update_database_for_dispatch(transaction, &virtual_proc, host.id, dispatch_id)
            .await?;

        // When running on dry_run_mode, just log the outcome
        if self.dry_run_mode {
            debug!(
                "(DRY_RUN) ({dispatch_id}) Dispatching {} on {}",
                virtual_proc, &host
            );
        } else {
            self.launch_on_rqd(&virtual_proc, &host, true)
                .await
                .map_err(|err| DispatchVirtualProcError::RqdConnectionFailed {
                    host: host.to_string(),
                    error: miette!("{}", err),
                })?;
        }

        // Update the host struct with the actual database values after the update
        // to ensure cache and database stay in sync
        let mut updated_host = host;
        updated_host.idle_cores = CoreSize::from_multiplied(
            updated_resources
                .cores_idle
                .try_into()
                .expect("db_cores_idle should fit in i32"),
        );
        updated_host.idle_memory = ByteSize::kb(updated_resources.mem_idle as u64);
        updated_host.idle_gpus = updated_resources
            .gpus_idle
            .try_into()
            .expect("db_gpus_idle should fit in u32");
        updated_host.idle_gpu_memory = ByteSize::kb(updated_resources.gpu_mem_idle as u64);
        updated_host.last_updated = updated_resources.last_updated;

        Ok((updated_host, new_allocation_capacity))
    }

    /// Updates database records for frame dispatch.
    ///
    /// This function performs three database operations atomically:
    /// 1. Updates the frame status to "started"
    /// 2. Inserts the virtual proc record
    /// 3. Updates host resource allocations
    ///
    /// # Arguments
    /// * `transaction` - Database transaction for atomic updates
    /// * `virtual_proc` - The virtual proc being dispatched
    /// * `host_id` - ID of the host receiving the dispatch
    /// * `dispatch_id` - Unique identifier for this dispatch operation
    ///
    /// # Returns
    /// On success, returns the updated host resources from the database.
    /// On failure, returns a `DispatchVirtualProcError` indicating the specific failure mode.
    async fn update_database_for_dispatch(
        &self,
        transaction: &mut Transaction<'_, Postgres>,
        virtual_proc: &VirtualProc,
        host_id: Uuid,
        dispatch_id: Uuid,
    ) -> Result<UpdatedHostResources, DispatchVirtualProcError> {
        self.frame_dao
            .update_frame_started(transaction, virtual_proc)
            .await
            .map_err(|err| match err {
                FrameDaoError::FrameCouldNotBeUpdated => {
                    DispatchVirtualProcError::FrameCouldNotBeUpdated
                }
                FrameDaoError::DbFailure(err) => DispatchVirtualProcError::FailedToStartOnDb(
                    DispatchError::FailedToStartOnDb(err),
                ),
            })?;

        self.proc_dao
            .insert(transaction, virtual_proc)
            .await
            .map_err(|(error, frame_id, host_id)| {
                DispatchVirtualProcError::FailedToStartOnDb(DispatchError::FailedToCreateProc {
                    error,
                    frame_id,
                    host_id,
                })
            })?;

        let updated_resources = self
            .host_dao
            .update_resources(transaction, &host_id, virtual_proc, dispatch_id)
            .await
            .map_err(|err| {
                DispatchVirtualProcError::FailedToStartOnDb(DispatchError::FailedToUpdateResources(
                    err,
                ))
            })?;

        Ok(updated_resources)
    }

    async fn launch_on_rqd(
        &self,
        virtual_proc: &VirtualProc,
        host: &Host,
        can_retry: bool,
    ) -> Result<(), DispatchError> {
        debug!("Dispatching {} on {}", virtual_proc, host);

        let run_frame =
            Self::prepare_rqd_run_frame(virtual_proc).map_err(DispatchError::Failure)?;
        debug!("Prepared run_frame for {}", virtual_proc);

        let request = RqdStaticLaunchFrameRequest {
            run_frame: Some(run_frame),
        };

        let mut rqd_client = self
            .get_rqd_connection(&host.name, CONFIG.rqd.grpc_port)
            .await
            .map_err(|err| DispatchError::FailureGrpcConnection(host.name.clone(), err))?;

        // Launch frame on rqd
        match rqd_client.launch_frame(request).await {
            Ok(_) => Ok(()),
            Err(status) => {
                match status.code() {
                    tonic::Code::Unauthenticated
                    | tonic::Code::Unavailable
                    | tonic::Code::Aborted
                    | tonic::Code::PermissionDenied
                    | tonic::Code::DeadlineExceeded
                    | tonic::Code::Internal
                    | tonic::Code::Unknown => {
                        warn!("Failed to launch on rqd. {}", status.message());
                        // Invalidate entry to force a new connection on the next interaction
                        self.rqd_connection_cache.invalidate(&host.name).await;

                        if can_retry {
                            // Retry once in case the cached connection was interrupted
                            Box::pin(self.launch_on_rqd(virtual_proc, host, false)).await
                        } else {
                            Err(DispatchError::GrpcFailure(status))
                        }
                    }
                    _ => {
                        warn!("Unretrieable failure on rqd launch. {:?}", status.message());
                        // Invalidate entry to force a new connection
                        self.rqd_connection_cache.invalidate(&host.name).await;

                        Err(DispatchError::GrpcFailure(status))
                    }
                }
            }
        }
    }

    /// Calculates the actual number of cores requested based on frame requirements.
    ///
    /// Handles special core request semantics:
    /// - Negative values: Reserve all cores except the specified amount
    /// - Zero: Reserve all cores on the host
    /// - Positive values: Reserve the exact amount requested
    ///
    /// # Arguments
    /// * `cores_requested` - The raw core request from the frame
    /// * `total_cores` - Total cores available on the host
    ///
    /// # Returns
    /// The calculated number of cores to actually request
    fn calculate_cores_requested(cores_requested: CoreSize, total_cores: CoreSize) -> CoreSize {
        // Requesting NEGATIVE cores is actually reserving ALL but the number of cores requeted
        if cores_requested.value() < 0 {
            total_cores + cores_requested
        // Requesting ZERO cores is actually reserving ALL cores on the host
        } else if cores_requested.value() == 0 {
            total_cores
        // Requesting POSITIVE cores
        } else {
            cores_requested
        }
    }

    /// Calculates the number of cores to reserve for a frame on a specific host.
    ///
    /// Takes into account:
    /// - Host thread mode (All, Variable, Auto)
    /// - Frame threadability
    /// - Memory requirements and stranded thresholds
    /// - Selfish services and resource availability
    ///
    /// # Arguments
    /// * `host` - The target host with available resources
    /// * `frame` - The frame requiring resources
    /// * `memory_stranded_threshold` - Threshold for memory-stranded frame detection
    ///
    /// # Returns
    /// * `Ok(CoreSize)` - Number of cores to reserve
    /// * `Err(VirtualProcError)` - If insufficient resources available
    fn calculate_core_reservation(
        host: &Host,
        frame: &DispatchFrame,
        memory_stranded_threshold: ByteSize,
    ) -> CoreSize {
        let cores_requested = Self::calculate_cores_requested(frame.min_cores, host.total_cores);

        match (host.thread_mode, frame.threadable) {
            (ThreadMode::All, _) => host.idle_cores,
            // Limit Variable booking to at least 2 cores
            (ThreadMode::Variable, true) if cores_requested.value() <= 2 => CoreSize(2),
            (ThreadMode::Auto, true) | (ThreadMode::Variable, true) => {
                // Book whatever is left for hosts with selfish services or memory stranded
                if frame.has_selfish_service
                    || host
                        .idle_memory
                        .as_u64()
                        .saturating_sub(frame.min_memory.as_u64())
                        <= memory_stranded_threshold.as_u64()
                {
                    host.idle_cores
                } else {
                    Self::calculate_memory_balanced_core_count(host, frame, cores_requested)
                }
            }
            _ => cores_requested,
        }
    }

    /// Consumes a host(HostModel) and returns an updated version accounting for consumed resources
    /// eg.
    /// HostModel(2 cores, 20GB) + frame(1 core, 10GB)
    ///     -> VirtualProc(1core, 10GB) + HostModel(1 core, 10GB)
    async fn consume_host_virtual_resources(
        frame: &DispatchFrame,
        host: &Host,
        memory_stranded_threshold: ByteSize,
    ) -> Result<(VirtualProc, Host), VirtualProcError> {
        let mut host = host.clone();

        let cores_reserved =
            Self::calculate_core_reservation(&host, frame, memory_stranded_threshold);

        if cores_reserved > host.total_cores || cores_reserved > host.idle_cores {
            Err(VirtualProcError::HostResourcesExtinguished(format!(
                "Not enough cores: {} < {}",
                host.idle_cores, cores_reserved
            )))?
        }

        if host.idle_memory < frame.min_memory {
            Err(VirtualProcError::HostResourcesExtinguished(format!(
                "Not enough memory: {}mb < {}mb",
                host.idle_memory.as_u64() / MIB,
                frame.min_memory.as_u64() / MIB
            )))?
        }

        if host.idle_gpus < frame.min_gpus {
            Err(VirtualProcError::HostResourcesExtinguished(format!(
                "Not enough GPU cores: {} < {}",
                host.idle_gpus, frame.min_gpus
            )))?
        }

        if host.idle_gpu_memory < frame.min_gpu_memory {
            Err(VirtualProcError::HostResourcesExtinguished(format!(
                "Not enough GPU memory: {}mb < {}mb",
                host.idle_gpu_memory.as_u64() / MIB,
                frame.min_gpu_memory.as_u64() / MIB
            )))?
        }

        let memory_reserved = frame.min_memory;
        let gpus_reserved = frame.min_gpus;
        let gpu_memory_reserved = frame.min_gpu_memory;

        // Update host resources
        host.idle_cores = host.idle_cores - cores_reserved;
        host.idle_memory = ByteSize(host.idle_memory.as_u64() - memory_reserved.as_u64());
        host.idle_gpus -= gpus_reserved;
        host.idle_gpu_memory =
            ByteSize(host.idle_gpu_memory.as_u64() - gpu_memory_reserved.as_u64());
        // Field will be overwritten with database values as soon as the changes are committed
        host.last_updated = Utc::now();

        Ok((
            VirtualProc {
                proc_id: Uuid::new_v4(),
                host_id: host.id,
                show_id: frame.show_id,
                layer_id: frame.layer_id,
                job_id: frame.job_id,
                frame_id: frame.id,
                alloc_id: host.alloc_id,
                cores_reserved: cores_reserved.into(),
                memory_reserved,
                gpus_reserved,
                gpu_memory_reserved,
                os: host.str_os.clone().unwrap_or_default(),
                is_local_dispatch: false,
                frame: frame.clone(),
                host_name: host.name.clone(),
            },
            host,
        ))
    }

    /// Calculates a memory-balanced core count to prevent resource imbalance.
    ///
    /// Ensures that core allocation is proportional to memory requirements
    /// to avoid situations where memory or cores become stranded.
    ///
    /// # Arguments
    /// * `host` - The host with available resources
    /// * `frame` - The frame with memory and core requirements
    /// * `cores_requested` - The number of cores originally requested
    ///
    /// # Returns
    /// The balanced number of cores to allocate
    fn calculate_memory_balanced_core_count(
        host: &Host,
        frame: &DispatchFrame,
        cores_requested: CoreSize,
    ) -> CoreSize {
        let total_cores = host.total_cores.value() as f64;
        let total_memory = host.total_memory.as_u64() as f64;
        let frame_min_memory = frame.min_memory.as_u64() as f64;

        // Memory per core if evently distributed
        let memory_per_core = total_memory / total_cores;

        // How many cores worth of memory the frame needs
        let mut cores_worth_of_memory = (frame_min_memory / memory_per_core.round()) as i32;

        // If frame requested more than the memory-balanced core count, use frame's request
        if cores_worth_of_memory < cores_requested.value() {
            cores_worth_of_memory = cores_requested.value();
        }
        // Don't book above max_core limit
        if let Some(layer_cores_limit) = frame.layer_cores_limit {
            if layer_cores_limit.value() > 0 && cores_worth_of_memory > layer_cores_limit.value() {
                cores_worth_of_memory = layer_cores_limit.value();
            }
        }

        CoreSize(cores_worth_of_memory)
    }

    /// Calculate a new frame spec from an original frame_range and a chunk definition
    ///
    /// # Arguments
    ///
    /// * `initial_frame_number` - The starting frame number to begin the chunk from
    /// * `frame_range` - A string representation of the frame range (e.g., "1-100")
    /// * `chunk_size` - The number of frames to include in the chunk
    ///
    /// # Returns
    ///
    /// Returns a `Result` containing a tuple of:
    /// * `String` - The frame specification string for the chunk
    /// * `i32` - The last frame number in the chunk
    ///
    /// # Errors
    ///
    /// This function will return an error if:
    /// * The frame range string is invalid
    /// * The initial frame number is not within the specified range
    /// * The chunk cannot be generated from the given parameters
    /// * The chunk frame set is empty or invalid
    fn prepare_frame_spec(
        initial_frame_number: i32,
        frame_range: &str,
        chunk_size: usize,
    ) -> Result<(String, i32)> {
        let frame_set = FrameSet::new(frame_range)?;
        let start_index = frame_set.index(initial_frame_number).ok_or(miette!(
            "Invalid frame number {}. Out of range {}",
            initial_frame_number,
            frame_range
        ))?;
        let frame_spec = frame_set
            .get_chunk(start_index, chunk_size)
            .wrap_err("Invalid Chunk")?;
        let chunk_frame_set = FrameSet::new(&frame_spec)?;
        let chunk_end_frame = chunk_frame_set.last().ok_or(miette!(
            "Could not find last frame of the chunk {}",
            frame_spec
        ))?;

        Ok((frame_spec, chunk_end_frame))
    }

    /// Prepares a RunFrame message for RQD execution.
    ///
    /// Converts a VirtualProc into the protobuf RunFrame format required by RQD,
    /// including:
    /// - Environment variable setup (CUE_*, frame metadata)
    /// - Command token replacement (#FRAME#, #LAYER#, etc.)
    /// - Resource allocation specifications
    /// - Frame timing and execution context
    ///
    /// A frame name shall follow the format [number]-[layer_name]
    ///
    /// # Arguments
    /// * `proc` - The virtual proc containing frame and resource information
    ///
    /// # Returns
    /// * `Ok(RunFrame)` - The prepared RQD RunFrame message
    /// * `Err(miette::Error)` - If frame preparation fails
    fn prepare_rqd_run_frame(proc: &VirtualProc) -> Result<RunFrame> {
        // Calculate threads from cores reserved
        let proc_cores_reserved: CoreSize = proc.cores_reserved.into();
        let threads = std::cmp::max(CoreSize(1), proc_cores_reserved);
        let frame = &proc.frame;

        // Extract frame number from frame name (assumes format "frameNumber-...")
        let frame_number = frame
            .frame_name
            .split('-')
            .next()
            .and_then(|s| s.parse::<i32>().ok())
            .ok_or(miette!("Invalid Frame Number"))?;

        let z_frame_number = format!("{:04}", frame_number);

        let (frame_spec, chunk_end_frame) =
            Self::prepare_frame_spec(frame_number, &frame.range, frame.chunk_size as usize)?;

        // Build environment variables
        let mut environment = HashMap::new();
        environment.insert("CUE3".to_string(), "1".to_string());
        environment.insert("CUE_THREADS".to_string(), threads.to_string());
        environment.insert("CUE_MEMORY".to_string(), proc.memory_reserved.to_string());
        environment.insert("CUE_GPUS".to_string(), proc.gpus_reserved.to_string());
        environment.insert(
            "CUE_GPU_MEMORY".to_string(),
            proc.gpu_memory_reserved.to_string(),
        );
        environment.insert("CUE_LOG_PATH".to_string(), frame.log_dir.clone());
        environment.insert("CUE_RANGE".to_string(), frame.range.clone());
        environment.insert("CUE_CHUNK".to_string(), frame.chunk_size.to_string());
        environment.insert("CUE_IFRAME".to_string(), frame_number.to_string());
        environment.insert("CUE_LAYER".to_string(), frame.layer_name.clone());
        environment.insert("CUE_JOB".to_string(), frame.job_name.clone());
        environment.insert("CUE_FRAME".to_string(), frame.frame_name.clone());
        environment.insert("CUE_SHOW".to_string(), frame.show_name.clone());
        environment.insert("CUE_SHOT".to_string(), frame.shot.clone());
        environment.insert("CUE_USER".to_string(), frame.user.clone());
        environment.insert("CUE_JOB_ID".to_string(), frame.job_id.to_string());
        environment.insert("CUE_LAYER_ID".to_string(), frame.layer_id.to_string());
        environment.insert("CUE_FRAME_ID".to_string(), frame.id.to_string());
        environment.insert(
            "CUE_THREADABLE".to_string(),
            if frame.threadable { "1" } else { "0" }.to_string(),
        );

        // Process command with token replacements
        let processed_command = frame
            .command
            .replace("#ZFRAME#", &z_frame_number)
            .replace("#IFRAME#", &frame_number.to_string())
            .replace("#FRAME_START#", &frame_number.to_string())
            .replace("#FRAME_END#", &chunk_end_frame.to_string())
            .replace("#FRAME_CHUNK#", &frame.chunk_size.to_string())
            .replace("#LAYER#", &frame.layer_name)
            .replace("#JOB#", &frame.job_name)
            .replace("#FRAMESPEC#", &frame_spec)
            .replace("#FRAME#", &frame.frame_name);

        // Build RunFrame
        let run_frame = RunFrame {
            shot: frame.shot.clone(),
            show: frame.show_name.clone(),
            user_name: frame.user.clone(),
            log_dir: frame.log_dir.clone(),
            job_id: frame.job_id.to_string(),
            job_name: frame.job_name.clone(),
            frame_id: frame.id.to_string(),
            frame_name: frame.frame_name.clone(),
            layer_id: frame.layer_id.to_string(),
            resource_id: proc.proc_id.to_string(),
            num_cores: proc.cores_reserved.value(),
            num_gpus: proc.gpus_reserved as i32,
            start_time: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as i64)
                .unwrap_or(0),
            ignore_nimby: proc.is_local_dispatch,
            os: proc.os.clone(),
            // TODO: Get soft/hard limits from config
            soft_memory_limit: -1,
            hard_memory_limit: -1,
            loki_url: frame.loki_url.as_ref().unwrap_or(&String::new()).clone(),
            environment,
            command: processed_command,
            uid_optional: frame
                .uid
                .map(opencue_proto::rqd::run_frame::UidOptional::Uid),
            frame_temp_dir: String::new(), // Will be set by RQD
            gid: 0,                        // Will be set by RQD based on user
            attributes: HashMap::new(),
            children: None,
            pid: 0, // Will be set by RQD

            // Deprecated fields
            #[allow(deprecated)]
            job_temp_dir: "deprecated".to_string(),
            #[allow(deprecated)]
            log_file: "deprecated".to_string(),
            #[allow(deprecated)]
            log_dir_file: "deprecated".to_string(),
        };

        Ok(run_frame)
    }

    /// Establishes a gRPC connection to an RQD instance.
    ///
    /// # Arguments
    /// * `hostname` - The hostname or IP address of the RQD instance
    /// * `port` - The gRPC port number for the RQD service
    ///
    /// # Returns
    /// * `Ok(RqdInterfaceClient)` - Connected gRPC client
    /// * `Err(miette::Error)` - If connection fails
    async fn get_rqd_connection(
        &self,
        hostname: &str,
        port: u32,
    ) -> Result<RqdInterfaceClient<Channel>> {
        self.rqd_connection_cache
            .entry(hostname.to_string())
            .or_optionally_insert_with(async {
                // Build endpoint with timeout and keep-alive settings
                let endpoint = Channel::from_shared(format!("http://{}:{}", hostname, port))
                    .into_diagnostic()
                    .ok()?
                    // Connection timeout - how long to wait when establishing connection
                    .connect_timeout(Duration::from_secs(10))
                    // Request timeout - maximum time for a single request
                    .timeout(Duration::from_secs(30))
                    // Keep-alive configuration
                    .http2_keep_alive_interval(Duration::from_secs(30))
                    .keep_alive_timeout(Duration::from_secs(10))
                    // Send keep-alive ping even when no active streams
                    .keep_alive_while_idle(true);

                RqdInterfaceClient::connect(endpoint)
                    .await
                    .into_diagnostic()
                    .ok()
            })
            .await
            .map(|e| e.into_value())
            .ok_or(miette!("Failed to connect to {} grpc server", hostname))
    }
}

#[cfg(test)]
mod tests {
    use std::time::SystemTime;

    use super::*;
    use crate::models::{CoreSize, DispatchFrame, Host};
    use bytesize::ByteSize;
    use opencue_proto::host::ThreadMode;
    use uuid::Uuid;

    // Helper function to create a test host
    fn create_test_host() -> Host {
        Host::new_for_test(
            Uuid::new_v4(),
            "test-host".to_string(),
            Some("linux".to_string()),
            CoreSize(8),
            ByteSize::gib(16),
            CoreSize(4),
            ByteSize::gib(8),
            1,
            ByteSize::gib(4),
            ThreadMode::Variable,
            CoreSize(4),
            Uuid::new_v4(),
            "test-alloc".to_string(),
        )
    }

    // Helper function to create a test dispatch frame
    fn create_test_dispatch_frame() -> DispatchFrame {
        DispatchFrame {
            id: Uuid::new_v4(),
            frame_name: "0001-test_frame".to_string(),
            show_id: Uuid::new_v4(),
            facility_id: Uuid::new_v4(),
            job_id: Uuid::new_v4(),
            layer_id: Uuid::new_v4(),
            command: "echo 'test command'".to_string(),
            range: "1-10".to_string(),
            chunk_size: 1,
            show_name: "test_show".to_string(),
            shot: "test_shot".to_string(),
            user: "test_user".to_string(),
            uid: Some(1000),
            log_dir: "/tmp/logs".to_string(),
            layer_name: "test_layer".to_string(),
            job_name: "test_job".to_string(),
            min_cores: CoreSize(1),
            layer_cores_limit: None,
            threadable: true,
            has_selfish_service: false,
            min_gpus: 0,
            min_gpu_memory: ByteSize::gb(0),
            min_memory: ByteSize::gib(2),
            services: None,
            os: Some("linux".to_string()),
            loki_url: None,
            version: 1,
            updated_at: SystemTime::now(),
        }
    }

    #[test]
    fn test_calculate_cores_requested_positive() {
        let result = RqdDispatcherService::calculate_cores_requested(CoreSize(4), CoreSize(8));
        assert_eq!(result, CoreSize(4));
    }

    #[test]
    fn test_calculate_cores_requested_zero() {
        let result = RqdDispatcherService::calculate_cores_requested(CoreSize(0), CoreSize(8));
        assert_eq!(result, CoreSize(8));
    }

    #[test]
    fn test_calculate_cores_requested_negative() {
        let result = RqdDispatcherService::calculate_cores_requested(CoreSize(-2), CoreSize(8));
        assert_eq!(result, CoreSize(6));
    }

    #[tokio::test]
    async fn test_calculate_core_reservation_thread_mode_all() {
        let mut host = create_test_host();
        host.thread_mode = ThreadMode::All;
        host.idle_cores = CoreSize(6);

        let frame = create_test_dispatch_frame();
        let memory_threshold = ByteSize::mib(500);

        let result =
            RqdDispatcherService::calculate_core_reservation(&host, &frame, memory_threshold);
        assert_eq!(result, CoreSize(6)); // Should return idle_cores
    }

    #[tokio::test]
    async fn test_calculate_core_reservation_variable_threadable_small_request() {
        let mut host = create_test_host();
        host.thread_mode = ThreadMode::Variable;

        let mut frame = create_test_dispatch_frame();
        frame.threadable = true;
        frame.min_cores = CoreSize(1);

        let memory_threshold = ByteSize::mib(500);

        let result =
            RqdDispatcherService::calculate_core_reservation(&host, &frame, memory_threshold);
        assert_eq!(result, CoreSize(2)); // Should return 2 cores minimum
    }

    #[tokio::test]
    async fn test_calculate_core_reservation_not_threadable() {
        let host = create_test_host();
        let mut frame = create_test_dispatch_frame();
        frame.threadable = false;
        frame.min_cores = CoreSize(3);

        let memory_threshold = ByteSize::mib(500);

        let result =
            RqdDispatcherService::calculate_core_reservation(&host, &frame, memory_threshold);
        assert_eq!(result, CoreSize(3)); // Should return cores_requested
    }

    #[tokio::test]
    async fn test_calculate_core_reservation_insufficient_cores() {
        let mut host = create_test_host();
        host.idle_cores = CoreSize(2);

        let mut frame = create_test_dispatch_frame();
        frame.min_cores = CoreSize(10); // More than available

        let memory_threshold = ByteSize::mib(500);

        let result =
            RqdDispatcherService::calculate_core_reservation(&host, &frame, memory_threshold);
        assert_eq!(result, CoreSize(-8));
    }

    #[test]
    fn test_calculate_memory_balanced_core_count_exact_calculation() {
        // Create a host with precise values to test the calculation
        let host = Host::new_for_test(
            Uuid::new_v4(),
            "test-host".to_string(),
            Some("linux".to_string()),
            CoreSize(8),       // 8 cores
            ByteSize::gib(16), // 16 GB total memory
            CoreSize(4),
            ByteSize::gib(8),
            1,
            ByteSize::gib(4),
            ThreadMode::Variable,
            CoreSize(4),
            Uuid::new_v4(),
            "test-alloc".to_string(),
        );

        let mut frame = create_test_dispatch_frame();
        frame.min_memory = ByteSize::gib(4); // Frame needs 4GB

        let cores_requested = CoreSize(1);

        let result = RqdDispatcherService::calculate_memory_balanced_core_count(
            &host,
            &frame,
            cores_requested,
        );

        // With 8 cores and 16GB, each core gets 2GB on average
        // Frame needs 4GB, so it should get 2 cores worth of memory
        // Since cores_requested (1) < cores_worth_of_memory (2), should return 2
        assert_eq!(result.value(), 2);
    }

    #[test]
    fn test_calculate_memory_balanced_core_count_high_memory_frame() {
        // Create a host with precise values
        let host = Host::new_for_test(
            Uuid::new_v4(),
            "test-host".to_string(),
            Some("linux".to_string()),
            CoreSize(4),      // 4 cores
            ByteSize::gib(8), // 8 GB total memory
            CoreSize(4),
            ByteSize::gib(8),
            1,
            ByteSize::gib(4),
            ThreadMode::Variable,
            CoreSize(4),
            Uuid::new_v4(),
            "test-alloc".to_string(),
        );

        let mut frame = create_test_dispatch_frame();
        frame.min_memory = ByteSize::gib(6); // Frame needs 6GB - more than half

        let cores_requested = CoreSize(1);

        let result = RqdDispatcherService::calculate_memory_balanced_core_count(
            &host,
            &frame,
            cores_requested,
        );

        // With 4 cores and 8GB, each core gets 2GB on average
        // Frame needs 6GB, so it should get 3 cores worth of memory
        // Since cores_requested (1) < cores_worth_of_memory (3), should return 3
        assert_eq!(result.value(), 3);
    }

    #[test]
    fn test_calculate_memory_balanced_core_count_low_memory_frame() {
        // Create a host with precise values
        let host = Host::new_for_test(
            Uuid::new_v4(),
            "test-host".to_string(),
            Some("linux".to_string()),
            CoreSize(8),       // 8 cores
            ByteSize::gib(32), // 32 GB total memory
            CoreSize(8),
            ByteSize::gib(32),
            1,
            ByteSize::gib(16),
            ThreadMode::Variable,
            CoreSize(8),
            Uuid::new_v4(),
            "test-alloc".to_string(),
        );

        let mut frame = create_test_dispatch_frame();
        frame.min_memory = ByteSize::gib(2); // Frame needs only 2GB

        let cores_requested = CoreSize(4); // But requests 4 cores

        let result = RqdDispatcherService::calculate_memory_balanced_core_count(
            &host,
            &frame,
            cores_requested,
        );

        // With 8 cores and 32GB, each core gets 4GB on average
        // Frame needs 2GB, so memory-wise it only needs 0.5 cores worth (rounds to 1)
        // Since cores_requested (4) > cores_worth_of_memory (1), should return cores_requested (4)
        assert_eq!(result.value(), 4);
    }

    #[test]
    fn test_calculate_memory_balanced_core_count_with_layer_limit() {
        let host = Host::new_for_test(
            Uuid::new_v4(),
            "test-host".to_string(),
            Some("linux".to_string()),
            CoreSize(8),
            ByteSize::gib(16),
            CoreSize(8),
            ByteSize::gib(16),
            1,
            ByteSize::gib(8),
            ThreadMode::Variable,
            CoreSize(8),
            Uuid::new_v4(),
            "test-alloc".to_string(),
        );

        let mut frame = create_test_dispatch_frame();
        frame.layer_cores_limit = Some(CoreSize(2)); // Limit to 2 cores
        frame.min_memory = ByteSize::gib(8); // High memory requirement (would want 4 cores normally)

        let cores_requested = CoreSize(1);

        let result = RqdDispatcherService::calculate_memory_balanced_core_count(
            &host,
            &frame,
            cores_requested,
        );

        // With 8 cores and 16GB, each core gets 2GB
        // Frame needs 8GB, so memory-wise it needs 4 cores
        // But layer limit is 2, so should be capped at 2
        assert_eq!(result.value(), 2);
    }

    #[test]
    fn test_prepare_frame_spec_basic() {
        let result = RqdDispatcherService::prepare_frame_spec(5, "1-10", 1);
        assert!(result.is_ok());
        let (frame_spec, last_frame) = result.unwrap();
        assert_eq!(frame_spec, "5");
        assert_eq!(last_frame, 5);
    }

    #[test]
    fn test_prepare_frame_spec_chunk() {
        let result = RqdDispatcherService::prepare_frame_spec(5, "1-10", 3);
        assert!(result.is_ok());
        let (frame_spec, last_frame) = result.unwrap();
        assert_eq!(frame_spec, "5-7");
        assert_eq!(last_frame, 7);
    }

    #[test]
    fn test_prepare_frame_spec_invalid_frame() {
        let result = RqdDispatcherService::prepare_frame_spec(15, "1-10", 1);
        assert!(result.is_err());
    }

    #[test]
    fn test_prepare_frame_spec_invalid_range() {
        let result = RqdDispatcherService::prepare_frame_spec(5, "invalid-range", 1);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_consume_host_virtual_resources_success() {
        let frame = create_test_dispatch_frame();
        let host = create_test_host();
        let memory_stranded_threshold = ByteSize::gib(1);

        let result = RqdDispatcherService::consume_host_virtual_resources(
            &frame,
            &host,
            memory_stranded_threshold,
        )
        .await;

        assert!(result.is_ok());
        let (virtual_proc, updated_host) = result.unwrap();

        // Check virtual proc creation
        assert_eq!(virtual_proc.host_id, host.id);
        assert_eq!(virtual_proc.memory_reserved, frame.min_memory);
        assert_eq!(virtual_proc.gpus_reserved, frame.min_gpus);
        assert_eq!(virtual_proc.gpu_memory_reserved, frame.min_gpu_memory);
        assert_eq!(virtual_proc.frame.id, frame.id);
        // proc_id should be a valid UUID (non-nil)
        assert_ne!(virtual_proc.proc_id, Uuid::nil());

        // Check host resource consumption
        assert!(updated_host.idle_cores < host.idle_cores);
        assert_eq!(
            updated_host.idle_memory.as_u64(),
            host.idle_memory.as_u64() - frame.min_memory.as_u64()
        );
        assert_eq!(updated_host.idle_gpus, host.idle_gpus - frame.min_gpus);
        assert_eq!(
            updated_host.idle_gpu_memory.as_u64(),
            host.idle_gpu_memory.as_u64() - frame.min_gpu_memory.as_u64()
        );
    }

    #[tokio::test]
    async fn test_consume_host_virtual_resources_insufficient_memory() {
        let mut frame = create_test_dispatch_frame();
        frame.min_memory = ByteSize::gib(64); // More than host has
        frame.min_cores = CoreSize(1);
        let host = create_test_host();
        let memory_stranded_threshold = ByteSize::gib(1);

        let result = RqdDispatcherService::consume_host_virtual_resources(
            &frame,
            &host,
            memory_stranded_threshold,
        )
        .await;

        assert!(result.is_err());
        match result {
            Err(VirtualProcError::HostResourcesExtinguished(msg)) => {
                assert!(msg.contains("Not enough memory"));
            }
            _ => panic!("Expected HostResourcesExtinguished error for memory"),
        }
    }

    #[tokio::test]
    async fn test_consume_host_virtual_resources_insufficient_gpus() {
        let mut frame = create_test_dispatch_frame();
        frame.min_gpus = 4; // More than host has
        let host = create_test_host();
        let memory_stranded_threshold = ByteSize::gib(1);

        let result = RqdDispatcherService::consume_host_virtual_resources(
            &frame,
            &host,
            memory_stranded_threshold,
        )
        .await;

        assert!(result.is_err());
        match result {
            Err(VirtualProcError::HostResourcesExtinguished(msg)) => {
                assert!(msg.contains("Not enough GPU cores"));
            }
            _ => panic!("Expected HostResourcesExtinguished error for GPUs"),
        }
    }

    #[tokio::test]
    async fn test_consume_host_virtual_resources_insufficient_gpu_memory() {
        let mut frame = create_test_dispatch_frame();
        frame.min_gpu_memory = ByteSize::gib(32); // More than host has
        let host = create_test_host();
        let memory_stranded_threshold = ByteSize::gib(1);

        let result = RqdDispatcherService::consume_host_virtual_resources(
            &frame,
            &host,
            memory_stranded_threshold,
        )
        .await;

        assert!(result.is_err());
        match result {
            Err(VirtualProcError::HostResourcesExtinguished(msg)) => {
                assert!(msg.contains("Not enough GPU memory"));
            }
            _ => panic!("Expected HostResourcesExtinguished error for GPU memory"),
        }
    }

    #[test]
    fn test_prepare_rqd_run_frame_basic() {
        let frame = create_test_dispatch_frame();
        let virtual_proc = VirtualProc {
            proc_id: Uuid::new_v4(),
            host_id: Uuid::new_v4(),
            show_id: Uuid::new_v4(),
            layer_id: Uuid::new_v4(),
            job_id: Uuid::new_v4(),
            frame_id: Uuid::new_v4(),
            alloc_id: Uuid::new_v4(),
            cores_reserved: CoreSize(2).with_multiplier(),
            memory_reserved: ByteSize::gib(4),
            gpus_reserved: 1,
            gpu_memory_reserved: ByteSize::gib(8),
            os: "linux".to_string(),
            is_local_dispatch: false,
            frame,
            host_name: "somehost".to_string(),
        };

        let result = RqdDispatcherService::prepare_rqd_run_frame(&virtual_proc);

        assert!(result.is_ok());
        let run_frame = result.unwrap();

        // Check basic fields
        assert_eq!(run_frame.frame_id, virtual_proc.frame.id.to_string());
        assert_eq!(run_frame.frame_name, virtual_proc.frame.frame_name);
        assert_eq!(run_frame.job_name, virtual_proc.frame.job_name);
        assert_eq!(run_frame.layer_id, virtual_proc.frame.layer_id.to_string());
        assert_eq!(run_frame.resource_id, virtual_proc.proc_id.to_string());
        assert_eq!(run_frame.num_cores, virtual_proc.cores_reserved.value());
        assert_eq!(run_frame.num_gpus, virtual_proc.gpus_reserved as i32);
        assert_eq!(run_frame.os, virtual_proc.os);
        assert_eq!(run_frame.ignore_nimby, virtual_proc.is_local_dispatch);

        // Check environment variables
        assert_eq!(run_frame.environment.get("CUE3").unwrap(), "1");
        assert_eq!(run_frame.environment.get("CUE_THREADS").unwrap(), "2");
        assert_eq!(
            run_frame.environment.get("CUE_MEMORY").unwrap(),
            &virtual_proc.memory_reserved.to_string()
        );
        assert_eq!(run_frame.environment.get("CUE_GPUS").unwrap(), "1");
        assert_eq!(
            run_frame.environment.get("CUE_FRAME").unwrap(),
            &virtual_proc.frame.frame_name
        );
        assert_eq!(
            run_frame.environment.get("CUE_JOB").unwrap(),
            &virtual_proc.frame.job_name
        );
        assert_eq!(
            run_frame.environment.get("CUE_LAYER").unwrap(),
            &virtual_proc.frame.layer_name
        );
        assert_eq!(
            run_frame.environment.get("CUE_SHOW").unwrap(),
            &virtual_proc.frame.show_name
        );
        assert_eq!(
            run_frame.environment.get("CUE_USER").unwrap(),
            &virtual_proc.frame.user
        );
        assert_eq!(
            run_frame.environment.get("CUE_RANGE").unwrap(),
            &virtual_proc.frame.range
        );
    }

    #[test]
    fn test_prepare_rqd_run_frame_token_replacement() {
        let mut frame = create_test_dispatch_frame();
        frame.command =
            "render #ZFRAME# #IFRAME# #FRAME_START# #FRAME_END# #LAYER# #JOB# #FRAME#".to_string();
        frame.frame_name = "0005-test_frame".to_string();
        frame.range = "1-10".to_string(); // Ensure frame 5 is in range

        let virtual_proc = VirtualProc {
            proc_id: Uuid::new_v4(),
            host_id: Uuid::new_v4(),
            show_id: Uuid::new_v4(),
            layer_id: Uuid::new_v4(),
            job_id: Uuid::new_v4(),
            frame_id: Uuid::new_v4(),
            alloc_id: Uuid::new_v4(),
            cores_reserved: CoreSize(1).with_multiplier(),
            memory_reserved: ByteSize::gib(2),
            gpus_reserved: 0,
            gpu_memory_reserved: ByteSize::gb(0),
            os: "linux".to_string(),
            is_local_dispatch: false,
            frame,
            host_name: "somehost".to_string(),
        };

        let result = RqdDispatcherService::prepare_rqd_run_frame(&virtual_proc);

        assert!(result.is_ok());
        let run_frame = result.unwrap();

        // Check token replacements in command
        let expected_command = "render 0005 5 5 5 test_layer test_job 0005-test_frame";
        assert_eq!(run_frame.command, expected_command);

        // Check frame number parsing and environment
        assert_eq!(run_frame.environment.get("CUE_IFRAME").unwrap(), "5");
    }

    #[test]
    fn test_prepare_rqd_run_frame_invalid_frame_name() {
        let mut frame = create_test_dispatch_frame();
        frame.frame_name = "invalid-frame-name".to_string();

        let virtual_proc = VirtualProc {
            proc_id: Uuid::new_v4(),
            host_id: Uuid::new_v4(),
            show_id: Uuid::new_v4(),
            layer_id: Uuid::new_v4(),
            job_id: Uuid::new_v4(),
            frame_id: Uuid::new_v4(),
            alloc_id: Uuid::new_v4(),
            cores_reserved: CoreSize(1).with_multiplier(),
            memory_reserved: ByteSize::gib(2),
            gpus_reserved: 0,
            gpu_memory_reserved: ByteSize::gb(0),
            os: "linux".to_string(),
            is_local_dispatch: false,
            frame,
            host_name: "somehost".to_string(),
        };

        let result = RqdDispatcherService::prepare_rqd_run_frame(&virtual_proc);
        assert!(result.is_err());
    }
}
