use crate::{
    dao::{FrameDao, HostDao},
    job_dispatcher::{DispatchError, VirtualProcError, frame_set::FrameSet},
    models::{CoreSize, DispatchFrame, DispatchLayer, Host, VirtualProc},
};
use bytesize::MIB;
use futures::{FutureExt, StreamExt};
use miette::{Context, IntoDiagnostic, Result, miette};
use opencue_proto::{
    host::ThreadMode,
    rqd::{RqdStaticLaunchFrameRequest, RunFrame, rqd_interface_client::RqdInterfaceClient},
};
use std::{collections::HashMap, sync::Arc};
use tonic::transport::Channel;
use tracing::{debug, error, info};
use uuid::Uuid;

/// RQD dispatcher responsible for dispatching frames to render hosts.
///
/// The dispatcher handles:
/// - Frame-to-host matching and resource allocation
/// - gRPC communication with RQD instances
/// - Resource consumption tracking and validation
/// - Frame command preparation and execution setup
pub struct RqdDispatcher {
    frame_dao: FrameDao,
    host_dao: Arc<HostDao>,
    dispatch_frames_per_layer_limit: usize,
    grpc_port: u32,
    memory_stranded_threshold: u64,
    dry_run_mode: bool,
}

impl RqdDispatcher {
    /// Creates a new RQD dispatcher with the specified configuration.
    ///
    /// # Arguments
    /// * `frame_dao` - Database access for frame operations
    /// * `host_dao` - Database access for host operations and locking
    /// * `grpc_port` - Port number for RQD gRPC connections
    /// * `dispatch_frames_per_layer_limit` - Maximum frames to dispatch per layer
    /// * `memory_stranded_threshold` - Memory threshold for stranded frame detection
    /// * `dry_run_mode` - If true, logs dispatch actions without executing them
    pub fn new(
        frame_dao: FrameDao,
        host_dao: Arc<HostDao>,
        grpc_port: u32,
        dispatch_frames_per_layer_limit: usize,
        memory_stranded_threshold: u64,
        dry_run_mode: bool,
    ) -> Self {
        Self {
            frame_dao,
            host_dao,
            grpc_port,
            dispatch_frames_per_layer_limit,
            memory_stranded_threshold,
            dry_run_mode,
        }
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
    pub async fn dispatch(&self, layer: &DispatchLayer, host: &Host) -> Result<(), DispatchError> {
        // Acquire lock first
        if !self
            .host_dao
            .lock(&host.id)
            .await
            .map_err(DispatchError::Failure)?
        {
            return Err(DispatchError::HostLock(host.name.clone()));
        }

        // Ensure unlock is always called, even if dispatch_inner panics or fails
        let result = std::panic::AssertUnwindSafe(self.dispatch_inner(layer, host))
            .catch_unwind()
            .await;

        // Always unlock, regardless of outcome
        if let Err(unlock_err) = self.host_dao.unlock(&host.id).await {
            error!("Failed to unlock host {}: {}", host.id, unlock_err);
        }

        // Handle the result from dispatch_inner
        match result {
            Ok(result) => {
                if result.is_ok() {
                    info!("Successfully dispatched layer {} on {}.", layer, host);
                }
                result
            }
            Err(_panic) => Err(DispatchError::Failure(miette!(
                "Dispatch operation panicked for layer {} on host {}",
                layer,
                host
            ))),
        }
    }

    async fn dispatch_inner(
        &self,
        layer: &DispatchLayer,
        host: &Host,
    ) -> Result<(), DispatchError> {
        let rqd_client = if self.dry_run_mode {
            None
        } else {
            Some(
                Self::connect_to_rqd(&host.name, self.grpc_port)
                    .await
                    .map_err(DispatchError::Failure)?,
            )
        };

        let mut stream = self
            .frame_dao
            .query_dispatch_frames(layer, self.dispatch_frames_per_layer_limit as i32);
        let mut current_host = host.clone();

        // A host should not book frames if its allocation is at or above its limit,
        // but checking the limit before each frame is too costly. The tradeoff is
        // to check the allocation state before entering the frame booking loop,
        // with these there's a risk the allocation will go above burst, but not by
        // a great margin as each loop only runs for a limited number of frames
        // (see config queue.dispatch_frames_per_layer_limit)
        let mut allocation_capacity = host.alloc_available_cores;

        let mut dispatched_procs: Vec<String> = Vec::new();

        while let Some(frame) = stream.next().await {
            match frame {
                Ok(frame_model) => {
                    let frame: DispatchFrame = frame_model.into();
                    debug!("found frame {}", frame);

                    match Self::consume_host_virtual_resources(
                        frame,
                        current_host.clone(),
                        self.memory_stranded_threshold,
                    )
                    .await
                    {
                        Ok((virtual_proc, updated_host)) => {
                            debug!("Built virtual proc {}", virtual_proc);
                            // Update host for the next iteration
                            current_host = updated_host;

                            // Check allocation capacity
                            let cores_reserved_without_multiplier: CoreSize =
                                virtual_proc.cores_reserved.into();
                            if cores_reserved_without_multiplier > allocation_capacity {
                                Err(DispatchError::AllocationOverBurst(
                                    host.allocation_name.clone(),
                                ))?;
                            };
                            allocation_capacity =
                                allocation_capacity - virtual_proc.cores_reserved.into();

                            let run_frame = self
                                .prepare_rqd_run_frame(&virtual_proc)
                                .map_err(DispatchError::Failure)?;
                            debug!("Prepared run_frame for {}", virtual_proc);
                            let request = RqdStaticLaunchFrameRequest {
                                run_frame: Some(run_frame),
                            };

                            // When running on dry_run_mode, just log the outcome
                            let msg = format!("Dispatching {} on {}", virtual_proc, &current_host);
                            if self.dry_run_mode {
                                info!("(DRY_RUN) {}", msg);
                            } else {
                                debug!(msg);
                                // Get a ref to the mutable grpc client
                                let mut rqd_client_ref = rqd_client
                                    .as_ref()
                                    .expect("Should be Some if dry_run is false")
                                    .clone();

                                // Launch frame on rqd
                                rqd_client_ref
                                    .launch_frame(request)
                                    .await
                                    .into_diagnostic()
                                    .map_err(DispatchError::Failure)?;

                                // Update database resources
                                self.host_dao
                                    .update_resources(&current_host)
                                    .await
                                    .map_err(DispatchError::FailureAfterDispatch)?;
                            }
                            dispatched_procs.push(virtual_proc.to_string());
                        }
                        Err(err) => match err {
                            VirtualProcError::HostResourcesExtinguished(msg) => {
                                debug!("Host resourses extinguished for {}. {}", host, msg);
                                Err(DispatchError::HostResourcesExtinguished)?;
                            }
                        },
                    }
                }
                Err(err) => {
                    Err(DispatchError::Failure(miette!(
                        "Failed to consume dispatch stream. {}",
                        err
                    )))?;
                }
            }
        }
        if dispatched_procs.is_empty() {
            info!("Found no frames on {} to dispatch to {}", layer, host);
        } else {
            debug!("Dispatched {} frames: ", dispatched_procs.len());
            for proc in dispatched_procs {
                debug!("{}", proc);
            }
        }
        Ok(())
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
        memory_stranded_threshold: u64,
    ) -> Result<CoreSize, VirtualProcError> {
        let cores_requested = Self::calculate_cores_requested(frame.min_cores, host.total_cores);

        let cores_reserved = match (host.thread_mode, frame.threadable) {
            (ThreadMode::All, _) => host.idle_cores,
            (ThreadMode::Variable, true) if cores_requested.value() <= 2 => CoreSize(2),
            (ThreadMode::Auto, true) | (ThreadMode::Variable, true) => {
                // Book whatever is left for hosts with selfish services or memory stranded
                if frame.has_selfish_service
                    || host.idle_memory - frame.min_memory <= memory_stranded_threshold
                {
                    host.idle_cores
                // Limit Variable booking to at least 2 cores
                } else {
                    Self::calculate_memory_balanced_core_count(host, frame, cores_requested)
                }
            }
            _ => cores_requested,
        };

        // Sanity check
        if cores_reserved > host.total_cores || cores_reserved > host.idle_cores {
            Err(VirtualProcError::HostResourcesExtinguished(format!(
                "Not enough cores: {} < {}",
                host.idle_cores, cores_reserved
            )))
        } else {
            Ok(cores_reserved)
        }
    }

    /// Consumes a host(HostModel) and returns an updated version accounting for consumed resources
    /// eg.
    /// HostModel(2 cores, 20GB) + frame(1 core, 10GB)
    ///     -> VirtualProc(1core, 10GB) + HostModel(1 core, 10GB)
    async fn consume_host_virtual_resources(
        frame: DispatchFrame,
        original_host: Host,
        memory_stranded_threshold: u64,
    ) -> Result<(VirtualProc, Host), VirtualProcError> {
        let mut host = original_host;

        let cores_reserved =
            Self::calculate_core_reservation(&host, &frame, memory_stranded_threshold)?;

        if host.idle_memory < frame.min_memory {
            Err(VirtualProcError::HostResourcesExtinguished(format!(
                "Not enough memory: {}mb < {}mb",
                host.idle_memory / MIB,
                frame.min_memory / MIB
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
                host.idle_gpu_memory / MIB,
                frame.min_gpu_memory / MIB
            )))?
        }

        let memory_reserved = frame.min_memory;
        let gpus_reserved = frame.min_gpus;
        let gpu_memory_reserved = frame.min_gpu_memory;

        // Update host resources
        host.idle_cores = host.idle_cores - cores_reserved;
        host.idle_memory -= memory_reserved;
        host.idle_gpus -= gpus_reserved;
        host.idle_gpu_memory -= gpu_memory_reserved;

        Ok((
            VirtualProc {
                proc_id: Uuid::new_v4(),
                host_id: host.id,
                cores_reserved: cores_reserved.into(),
                memory_reserved,
                gpus_reserved,
                gpu_memory_reserved,
                os: host.str_os.clone().unwrap_or_default(),
                is_local_dispatch: false,
                frame,
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
        let total_memory = host.total_memory as f64;
        let frame_min_memory = frame.min_memory as f64;

        // Memory per core if evently distributed
        let memory_per_core = total_cores / total_memory;

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
    /// # Arguments
    /// * `proc` - The virtual proc containing frame and resource information
    ///
    /// # Returns
    /// * `Ok(RunFrame)` - The prepared RQD RunFrame message
    /// * `Err(miette::Error)` - If frame preparation fails
    fn prepare_rqd_run_frame(&self, proc: &VirtualProc) -> Result<RunFrame> {
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
    async fn connect_to_rqd(hostname: &str, port: u32) -> Result<RqdInterfaceClient<Channel>> {
        let client = RqdInterfaceClient::connect(format!("http://{}:{}", hostname, port))
            .await
            .into_diagnostic()
            .wrap_err(format!(
                "Failed to connect to Rqd Server: {}:{}",
                hostname, port
            ))?;
        Ok(client)
    }
}
