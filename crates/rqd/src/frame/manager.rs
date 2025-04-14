use chrono::DateTime;
use miette::{Diagnostic, Result, miette};
use opencue_proto::{
    host::HardwareState,
    rqd::{RunFrame, run_frame},
};
use std::{
    fs,
    sync::Arc,
    time::{SystemTime, UNIX_EPOCH},
};
use thiserror::Error;
use tokio::time;
use tracing::{error, info, warn};
use uuid::Uuid;

use crate::{config::config::Config, servant::rqd_servant::MachineImpl};

use super::{cache::RunningFrameCache, running_frame::RunningFrame};

pub struct FrameManager {
    pub config: Config,
    pub frame_cache: Arc<RunningFrameCache>,
    pub machine: Arc<MachineImpl>,
}

impl FrameManager {
    /// Spawns a new frame to be executed on this host.
    ///
    /// This function handles the entire process of validating, preparing, and launching a frame:
    /// - Validates the frame and machine state
    /// - Reserves CPU resources if the frame is hyperthreaded
    /// - Reserves GPU resources if requested
    /// - Creates the user if necessary
    /// - Initializes and launches the frame in a separate thread
    ///
    /// # Arguments
    ///
    /// * `run_frame` - The grpc frame configuration containing all information needed to run the
    ///   job
    ///
    /// # Returns
    ///
    /// * `Ok(())` if the frame was successfully spawned
    /// * `Err(FrameManagerError)` if the frame could not be spawned for any reason
    pub async fn spawn(&self, run_frame: RunFrame) -> Result<(), FrameManagerError> {
        // Validate machine state
        self.validate_grpc_frame(&run_frame)?;
        self.validate_machine_state(run_frame.ignore_nimby).await?;

        // Create user if required. uid and gid ranges have already been verified
        let uid = match run_frame.uid_optional.as_ref().map(|o| match o {
            run_frame::UidOptional::Uid(v) => *v as u32,
        }) {
            Some(uid) => self
                .machine
                .create_user_if_unexisting(&run_frame.user_name, uid, run_frame.gid as u32)
                .await
                .map_err(|err| {
                    FrameManagerError::Aborted(format!(
                        "Not launching, user {}({}:{}) could not be created. {:?}",
                        run_frame.user_name, uid, run_frame.gid, err
                    ))
                })?,
            None => self.config.runner.default_uid,
        };

        // **Attention**: If an error happens between here and spawning a frame, the resources
        // reserved need to be released.
        //
        // Cuebot unfortunatelly uses a hardcoded frame environment variable to signal if
        // a frame is hyperthreaded. Rqd should only reserve cores if a frame is hyperthreaded.
        let hyperthreaded = run_frame
            .environment
            .get("CUE_THREADABLE")
            .map_or(false, |v| v == "1");
        let cpu_request = run_frame.num_cores as u32 / self.config.machine.core_multiplier;
        let cpu_list = self
            .machine
            .reserve_cores(cpu_request, run_frame.resource_id(), hyperthreaded)
            .await
            .map_err(|err| {
                FrameManagerError::Aborted(format!(
                    "Not launching, failed to reserve cpu resources {:?}",
                    err
                ))
            })?;
        // Although num_gpus is not required on a frame, the field is not optional on the proto
        // layer. =0 means None, !=0 means Some
        let gpu_list = match run_frame.num_gpus {
            0 => None,
            _ => {
                let reserved_res = self.machine.reserve_gpus(run_frame.num_gpus as u32).await;
                if let Err(_) = reserved_res {
                    // Release cores reserved on the last step
                    if let Some(procs) = &cpu_list {
                        self.machine.release_cpus(procs).await;
                    } else {
                        self.machine.release_cores(cpu_request).await;
                    }
                }
                Some(reserved_res.map_err(|err| {
                    FrameManagerError::Aborted(format!(
                        "Not launching, insufficient resources {:?}",
                        err
                    ))
                })?)
            }
        };

        let running_frame = Arc::new(RunningFrame::init(
            run_frame,
            uid,
            self.config.runner.clone(),
            cpu_list,
            gpu_list,
            self.machine.get_host_name().await,
        ));

        self.spawn_running_frame(running_frame, false);
        Ok(())
    }

    /// Recovers frames from saved snapshots on disk.
    ///
    /// This function:
    /// - Reads saved frame snapshots from the configured snapshots directory
    /// - Deserializes each valid snapshot file into a RunningFrame
    /// - Spawns recovered frames to continue execution
    /// - Cleans up invalid or corrupted snapshot files
    ///
    /// # Returns
    ///
    /// * `Ok(())` if snapshot recovery was attempted (even if some snapshots failed)
    /// * `Err(miette::Error)` if the snapshots directory could not be read
    pub async fn recover_snapshots(&self) -> Result<()> {
        let snapshots_path = &self.config.runner.snapshots_path;
        let read_dirs = std::fs::read_dir(snapshots_path).map_err(|err| {
            let msg = format!("Failed to read snapshot dir. {}", err);
            warn!(msg);
            miette!(msg)
        })?;
        // Filter paths that are files ending with .bin
        let snapshot_dir: Vec<String> = read_dirs
            .filter_map(|entry| {
                let entry = entry.ok()?;
                let file_type = entry.file_type().ok()?;
                if file_type.is_file() && entry.file_name().to_str().unwrap_or("").ends_with(".bin")
                {
                    entry.path().to_str().map(String::from)
                } else {
                    None
                }
            })
            .collect();
        let mut errors = Vec::new();
        for path in snapshot_dir {
            let running_frame = RunningFrame::from_snapshot(&path, self.config.runner.clone())
                .map(|rf| Arc::new(rf));
            match running_frame {
                Ok(running_frame) => {
                    // Update reservations. If a cpu_list exists, the frame was booked using affinity
                    if let Err(err) = match &running_frame.cpu_list {
                        Some(cpu_list) => self
                            .machine
                            .reserve_cores_by_id(cpu_list, running_frame.request.resource_id())
                            .await
                            .map(|v| Some(v)),
                        None => {
                            self.machine
                                .reserve_cores(
                                    running_frame.request.num_cores as u32,
                                    running_frame.request.resource_id(),
                                    false,
                                )
                                .await
                        }
                    } {
                        errors.push(err.to_string());
                    }
                    self.spawn_running_frame(running_frame, true)
                }
                Err(err) => {
                    error!("Snapshot recover failed: {}", err);
                    if let Err(err) = fs::remove_file(&path) {
                        warn!("Snapshot {} failed to be cleared. {}", path, err);
                    };
                }
            }
        }

        if !errors.is_empty() {
            Err(miette!("{}", errors.join("\n")))
        } else {
            Ok(())
        }
    }

    fn spawn_running_frame(&self, running_frame: Arc<RunningFrame>, recover_mode: bool) {
        self.frame_cache
            .insert_running_frame(Arc::clone(&running_frame));
        let running_frame_ref: Arc<RunningFrame> = Arc::clone(&running_frame);
        // Fire and forget
        let thread_handle = std::thread::spawn(move || {
            let result = std::panic::catch_unwind(|| running_frame.run(recover_mode));
            if let Err(panic_info) = result {
                _ = running_frame.finish(1, None);
                error!(
                    "Run thread panicked for {}: {:?}",
                    running_frame, panic_info
                );
            }
        });
        if let Err(err) = running_frame_ref.update_launch_thread_handle(thread_handle) {
            warn!(
                "Failed to update thread handle for frame {}. {}",
                running_frame_ref, err
            );
        }
    }

    fn validate_grpc_frame(&self, run_frame: &RunFrame) -> Result<(), FrameManagerError> {
        // Frame is already running
        if self.frame_cache.contains(&run_frame.frame_id()) {
            Err(FrameManagerError::AlreadyExist(format!(
                "Not lauching, frame is already running on this host {}",
                run_frame.frame_id()
            )))?
        }
        // Trying to run as root
        if run_frame
            .uid_optional
            .clone()
            .map(|o| match o {
                run_frame::UidOptional::Uid(v) => v,
            })
            .unwrap_or(1)
            <= 0
        {
            Err(FrameManagerError::InvalidArgument(format!(
                "Not launching, will not run frame as uid = {:?}",
                run_frame.uid_optional
            )))?
        }
        // Invalid number of cores
        if run_frame.num_cores <= 0 {
            Err(FrameManagerError::InvalidArgument(
                "Not launching, num_cores must be positive".to_string(),
            ))?
        }
        // Fractional cpu cores are not allowed
        if run_frame.num_cores % 100 != 0 {
            Err(FrameManagerError::InvalidArgument(
                "Not launching, num_cores must be multiple of 100 (Fractional Cores are not allowed)".to_string(),
            ))?
        }

        Ok(())
    }

    async fn validate_machine_state(&self, ignore_nimby: bool) -> Result<(), FrameManagerError> {
        // Hardware state is not UP
        if self
            .machine
            .hardware_state()
            .await
            .unwrap_or(HardwareState::Down)
            != HardwareState::Up
        {
            Err(FrameManagerError::InvalidHardwareState(
                "Not launching, host HardwareState is not Up".to_string(),
            ))?
        }

        // Nimby locked
        if self.machine.nimby_locked().await && !ignore_nimby {
            Err(FrameManagerError::NimbyLocked)?
        }
        Ok(())
    }

    pub fn get_running_frame(&self, frame_id: &Uuid) -> Option<Arc<RunningFrame>> {
        self.frame_cache
            .get(frame_id)
            .as_ref()
            .map(|f| Arc::clone(f))
    }

    /// Kills a running frame on this host.
    ///
    /// This function attempts to find and terminate a running frame by its ID.
    ///
    /// # Arguments
    ///
    /// * `frame_id` - The UUID identifying the frame to kill
    /// * `reason` - A string describing why the frame is being killed
    ///
    /// # Returns
    ///
    /// * `Ok(Some(()))` if the frame was found and killed successfully
    /// * `Ok(None)` if no frame with the given ID was found
    /// * `Err(miette::Error)` if frame cannot be killed, possibly a precondition wasn't met
    ///     - Frame existed but wasn't running
    ///     - Frame has alredy been killed
    pub async fn kill_running_frame(&self, frame_id: &Uuid, reason: String) -> Result<Option<()>> {
        match self.get_running_frame(frame_id) {
            Some(running_frame) => {
                let pid = running_frame.get_pid_to_kill();
                if let Ok(frame_pid) = pid {
                    info!(
                        "Killing frame {running_frame}({frame_pid}) by request.\n\
                        Reason: {reason}"
                    );
                    self.machine.kill_session(frame_pid, false).await?;
                    self.monitor_killed_frame(frame_pid, &running_frame);

                    Ok(Some(()))
                } else {
                    Err(miette!(
                        "Kill frame with invalid State. Frame {running_frame} exists but has \
                        no pid assigned to it"
                    ))
                }
            }
            None => Ok(None),
        }
    }

    /// Monitors a killed frame to ensure it fully terminates.
    ///
    /// After a frame is killed, this function spawns a background task that periodically checks
    /// if the process and its children have fully terminated. It will log an error if processes
    /// are still running after the monitoring time limit.
    ///
    /// # Arguments
    ///
    /// * `frame_pid` - The process ID of the killed frame
    /// * `running_frame` - Reference to the RunningFrame object that was killed
    fn monitor_killed_frame(&self, frame_pid: u32, running_frame: &RunningFrame) {
        let interval_seconds = self.config.runner.kill_monitor_interval.as_secs();
        let mut monitor_limit_seconds = self.config.runner.kill_monitor_timeout.as_secs();
        let force_kill = self.config.runner.force_kill_after_timeout;
        let mut tried_to_force_kill_session = false;
        let mut interval = time::interval(self.config.runner.kill_monitor_interval);
        let kill_request_time = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| {
                let secs = d.as_secs();
                let dt = DateTime::from_timestamp(secs as i64, 0).unwrap_or_default();
                dt.format("%Y-%m-%d %H:%M:%S").to_string()
            })
            .unwrap_or_else(|_| "invalid time".to_string());
        let job_str = format!("{}", running_frame);
        let machine = Arc::clone(&self.machine);

        tokio::spawn(async move {
            loop {
                interval.tick().await;

                let active_lineage = machine.get_active_proc_lineage(frame_pid).await;
                if let Some(mut lineage) = active_lineage {
                    lineage.push(frame_pid);
                    // Check limit before decrementing as tick() returns immediately on the first call
                    if monitor_limit_seconds <= 0 || tried_to_force_kill_session {
                        // Notify only
                        if !force_kill {
                            error!(
                                "Gave up waiting on {} termination. \
                                Kill has been requested at {} but proc({}) lineage is still active: {:?}.",
                                job_str, kill_request_time, frame_pid, lineage
                            );
                            break;
                        }

                        // Force kill
                        if !tried_to_force_kill_session {
                            // First try to force kill the session
                            match machine.kill_session(frame_pid, true).await {
                                Ok(()) => {
                                    tried_to_force_kill_session = true;
                                    info!(
                                        "Kill timeout for {}. Used session force_kill on \
                                        session_id {} to kill {:?}",
                                        job_str, frame_pid, lineage
                                    )
                                }
                                Err(err) => warn!(
                                    "Failed to force_kill {} lineage = {:?}. {}",
                                    job_str, lineage, err
                                ),
                            }
                        } else {
                            match machine.force_kill(&lineage).await {
                                Ok(()) => info!(
                                    "Kill timeout for {}. Used force_kill on {:?}",
                                    job_str, lineage
                                ),
                                Err(err) => warn!(
                                    "Failed to force_kill {} lineage = {:?}. {}",
                                    job_str, lineage, err
                                ),
                            }
                            break;
                        }
                    } else {
                        info!(
                            "Frame {} still being killed. \
                            Kill has been requested at {} but proc({}) lineage is still active: {:?}.",
                            job_str, kill_request_time, frame_pid, lineage
                        );
                    }
                } else {
                    break;
                }

                if monitor_limit_seconds >= interval_seconds {
                    monitor_limit_seconds -= interval_seconds;
                }
            }
        });
    }
}

#[derive(Debug, Error, Diagnostic)]
pub enum FrameManagerError {
    #[error("Action aborted due to a host invalid state")]
    InvalidHardwareState(String),
    #[error("Invalid Request")]
    InvalidArgument(String),
    #[error("Frame is already running")]
    AlreadyExist(String),
    #[error("Aborted")]
    Aborted(String),
    #[error("Execution aborted, host is nimby locked")]
    NimbyLocked,
}

impl From<FrameManagerError> for tonic::Status {
    fn from(value: FrameManagerError) -> Self {
        match value {
            FrameManagerError::InvalidHardwareState(msg) => tonic::Status::failed_precondition(msg),
            FrameManagerError::InvalidArgument(msg) => tonic::Status::invalid_argument(msg),
            FrameManagerError::AlreadyExist(msg) => tonic::Status::invalid_argument(msg),
            FrameManagerError::Aborted(msg) => tonic::Status::aborted(msg),
            FrameManagerError::NimbyLocked => tonic::Status::aborted("Nimby Locked"),
        }
    }
}
