use crate::{
    consumer::{frame_dao::FrameDao, host_dao::HostDao},
    models::{DispatchFrame, DispatchLayer, Host, VirtualProc},
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
use tracing::{error, info};
use uuid::Uuid;

pub struct RqdDispatcher {
    frame_dao: FrameDao,
    host_dao: Arc<HostDao>,
    dispatch_frames_per_layer_limit: usize,
    grpc_port: u32,
    core_multiplier: u32,
    memory_stranded_threshold: u64,
}

pub enum VirtualProcError {
    HostResourcesExtinguished(String),
    FailedToReserveHost(String),
}

impl RqdDispatcher {
    pub fn new(
        frame_dao: FrameDao,
        host_dao: Arc<HostDao>,
        grpc_port: u32,
        dispatch_frames_per_layer_limit: usize,
        core_multiplier: u32,
        memory_stranded_threshold: u64,
    ) -> Self {
        Self {
            frame_dao,
            host_dao,
            grpc_port,
            dispatch_frames_per_layer_limit,
            core_multiplier,
            memory_stranded_threshold,
        }
    }

    pub async fn dispatch(&self, layer: &DispatchLayer, host: &Host) -> Result<()> {
        // Acquire lock first
        if !self.host_dao.lock(&host.id).await? {
            return Err(miette!("Failed to acquire lock for host {}", host.id));
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
            Err(_panic) => Err(miette!(
                "Dispatch operation panicked for layer {} on host {}",
                layer,
                host
            )),
        }
    }

    async fn dispatch_inner(&self, layer: &DispatchLayer, host: &Host) -> Result<()> {
        host.is_allocation_at_or_over_burst(&layer.show_id)?;

        let mut rqd_client = Self::connect_to_rqd(&host.name, self.grpc_port).await?;

        let mut stream = self
            .frame_dao
            .query_frames(layer, self.dispatch_frames_per_layer_limit as i32);
        let mut current_host = host.clone();

        while let Some(frame) = stream.next().await {
            match frame {
                Ok(frame_model) => {
                    let frame: DispatchFrame = frame_model.into();
                    let frame_str = frame.to_string();

                    match Self::consume_host_virtual_resources(
                        frame,
                        current_host.clone(),
                        self.core_multiplier,
                        self.memory_stranded_threshold,
                    )
                    .await
                    {
                        Ok((virtual_proc, updated_host)) => {
                            // Update host for the next iteration
                            current_host = updated_host;

                            let run_frame = self.prepare_rqd_run_frame(&virtual_proc)?;
                            let request = RqdStaticLaunchFrameRequest {
                                run_frame: Some(run_frame),
                            };

                            rqd_client.launch_frame(request).await.into_diagnostic()?;

                            self.host_dao.update_resources(&current_host).await?;
                        }
                        Err(err) => match err {
                            VirtualProcError::HostResourcesExtinguished(msg) => {
                                Err(miette!(
                                    "Failed to book {} on {}. Not enough resources. {}",
                                    frame_str,
                                    host,
                                    msg
                                ))?;
                            }
                            VirtualProcError::FailedToReserveHost(msg) => {
                                Err(miette!(
                                    "Failed to allocate VirtualProc for {} on {}. {}",
                                    frame_str,
                                    host,
                                    msg
                                ))?;
                            }
                        },
                    }
                }
                Err(err) => {
                    let msg = "Failed to consume a frame at dispatch stream";
                    error!("{}. {}", msg, err);
                    Err(err).into_diagnostic().wrap_err(msg)?
                }
            }
        }
        Ok(())
    }

    fn calculate_cores_requested(cores_requested: i32, total_cores: u32) -> u32 {
        // Requesting NEGATIVE cores is actually reserving ALL but the number of cores requeted
        if cores_requested < 0 {
            total_cores + cores_requested as u32
        // Requesting ZERO cores is actually reserving ALL cores on the host
        } else if cores_requested == 0 {
            total_cores
        // Requesting POSITIVE cores
        } else {
            cores_requested as u32
        }
    }

    fn calculate_core_reservation(
        host: &Host,
        frame: &DispatchFrame,
        core_multiplier: u32,
        memory_stranded_threshold: u64,
    ) -> Result<u32, VirtualProcError> {
        let cores_requested = Self::calculate_cores_requested(frame.min_cores, host.total_cores);

        // Number of idle cores not taking fractional cores into consideration
        let whole_cores_idle = ((host.idle_cores as f64 / core_multiplier as f64).floor()
            * core_multiplier as f64) as u32;

        let cores_reserved = match (host.thread_mode, frame.threadable) {
            (ThreadMode::All, _) => whole_cores_idle,
            (ThreadMode::Variable, true) if cores_requested <= 2 * core_multiplier => {
                2 * core_multiplier
            }
            (ThreadMode::Auto, true) | (ThreadMode::Variable, true) => {
                // Book whatever is left for hosts with selfish services or memory stranded
                if frame.has_selfish_service
                    || host.idle_memory - frame.min_memory <= memory_stranded_threshold
                {
                    whole_cores_idle
                // Limit Variable booking to at least 2 cores
                } else {
                    Self::calculate_memory_balanced_core_count(
                        host,
                        frame,
                        cores_requested,
                        core_multiplier,
                    )
                }
            }
            _ => cores_requested,
        };

        // Sanity check
        if cores_reserved > host.total_cores
            || cores_reserved > host.idle_cores
            // Don't book hosts with only a fraction of a core
            || host.idle_cores < core_multiplier
        {
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
        core_multiplier: u32,
        memory_stranded_threshold: u64,
    ) -> Result<(VirtualProc, Host), VirtualProcError> {
        let mut host = original_host;

        let cores_reserved = Self::calculate_core_reservation(
            &host,
            &frame,
            core_multiplier,
            memory_stranded_threshold,
        )?;

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
        host.idle_cores -= cores_reserved;
        host.idle_memory -= memory_reserved;
        host.idle_gpus -= gpus_reserved;
        host.idle_gpu_memory -= gpu_memory_reserved;

        Ok((
            VirtualProc {
                proc_id: Uuid::new_v4(),
                host_id: host.id,
                cores_reserved,
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

    fn calculate_memory_balanced_core_count(
        host: &Host,
        frame: &DispatchFrame,
        cores_requested: u32,
        core_multiplier: u32,
    ) -> u32 {
        let total_cores = (host.total_cores as f64 / 100.0).floor();
        let total_memory = host.total_memory as f64;
        let frame_min_memory = frame.min_memory as f64;

        // Memory per core if evently distributed
        let memory_per_core = total_cores / total_memory;

        // How many cores worth of memory the frame needs
        let cores_worth_of_memory = (frame_min_memory / memory_per_core).round() as u32;
        let mut cores_to_reserve = cores_worth_of_memory * core_multiplier;

        // If frame requested more than the memory-balanced core count, use frame's request
        if cores_to_reserve < cores_requested {
            cores_to_reserve = cores_requested;
        }
        // Don't book above max_core limit
        if frame.max_cores > 0 && cores_to_reserve > frame.max_cores {
            cores_to_reserve = frame.max_cores;
        }

        cores_to_reserve
    }

    fn prepare_rqd_run_frame(&self, proc: &VirtualProc) -> Result<RunFrame> {
        // Calculate threads from cores reserved (divided by 100, minimum 1)
        let threads = std::cmp::max(1, proc.cores_reserved / 100);
        let frame = &proc.frame;

        // Extract frame number from frame name (assumes format "frameNumber-...")
        let frame_number = frame
            .frame_name
            .split('-')
            .next()
            .and_then(|s| s.parse::<i32>().ok())
            .unwrap_or(1);
        let z_frame_number = format!("{:04}", frame_number);

        // TODO: Implement FrameSet logic for frameSpec calculation
        let frame_spec = frame.range.clone(); // Simplified for now
        let chunk_end_frame = frame_number + frame.chunk_size - 1;

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
            num_cores: proc.cores_reserved as i32,
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
