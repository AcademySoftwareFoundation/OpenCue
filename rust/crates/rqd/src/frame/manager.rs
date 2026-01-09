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

use chrono::{DateTime, Local};
use itertools::Either;
use miette::{miette, Diagnostic, Result};
use opencue_proto::{
    host::HardwareState,
    rqd::{run_frame, RunFrame},
};
use std::{fs, sync::Arc, time::SystemTime};
use thiserror::Error;
use tokio::{sync::OnceCell, time};
use tracing::{error, info, warn};
use uuid::Uuid;

#[cfg(feature = "containerized_frames")]
use super::docker_running_frame;

use super::running_frame::RunningFrame;
use crate::{config::CONFIG, servant::rqd_servant::MachineImpl, system::machine};

pub struct FrameManager {
    pub machine: Arc<MachineImpl>,
}

static FRAME_MANAGER: OnceCell<Arc<FrameManager>> = OnceCell::const_new();

/// Returns the singleton instance of the FrameManager.
///
/// This function lazily initializes the FrameManager on first call and returns a reference
/// to the singleton instance on subsequent calls.
///
/// # Returns
///
/// * `Ok(Arc<FrameManager>)` - A cloned Arc reference to the FrameManager singleton
/// * `Err(miette::Error)` - If initialization fails (typically due to machine instance failure)
pub async fn instance() -> Result<Arc<FrameManager>> {
    FRAME_MANAGER
        .get_or_try_init(|| async {
            let frame_manager = FrameManager {
                machine: machine::instance().await?,
            };
            Ok(Arc::new(frame_manager))
        })
        .await
        .map(Arc::clone)
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

        let resource_id = run_frame.resource_id();

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
            None => CONFIG.runner.default_uid,
        };

        // Although num_gpus is not required on a frame, the field is not optional on the proto
        // layer. =0 means None, !=0 means Some
        let gpu_list = match run_frame.num_gpus {
            0 => None,
            _ => {
                // TODO: Release GPUs in case of error when GPU support gets implemented
                let reserved_res = self.machine.reserve_gpus(run_frame.num_gpus as u32).await;
                Some(reserved_res.map_err(|err| {
                    FrameManagerError::Aborted(format!(
                        "Not launching, insufficient resources {:?}",
                        err
                    ))
                })?)
            }
        };

        // Cuebot unfortunatelly uses a hardcoded frame environment variable to signal if
        // a frame is hyperthreaded. Rqd should only reserve cores if a frame is hyperthreaded.
        let hyperthreaded = run_frame
            .environment
            .get("CUE_THREADABLE")
            .is_some_and(|v| v == "1");

        let slot_based_booking = self.machine.is_slot_configured().await;
        // Keep track of reserved slots, if any
        let mut reserved_slots = 0;

        let running_frame = match slot_based_booking {
            // Core based booking
            false => {
                // **Attention**: If an error happens between here and spawning a frame, the resources
                // reserved need to be released.
                let num_cores =
                    (run_frame.num_cores as u32).div_ceil(CONFIG.machine.core_multiplier);

                // Reserving cores will always yield a list of reserved thread_ids. If hyperthreading is off,
                // the list should be ignored
                let thread_ids = self
                    .machine
                    .reserve_cores(Either::Left(num_cores as usize), run_frame.resource_id())
                    .await
                    .map_err(|err| {
                        FrameManagerError::Aborted(format!(
                            "Not launching, failed to reserve cpu resources {:?}",
                            err
                        ))
                    })?;
                // Ignore the list of allocated threads if hyperthreading is off
                let thread_ids = hyperthreaded.then_some(thread_ids);

                Arc::new(RunningFrame::init(
                    run_frame,
                    uid,
                    CONFIG.runner.clone(),
                    thread_ids,
                    gpu_list,
                    self.machine.get_host_name(),
                ))
            }
            // Slot based booking
            true => {
                reserved_slots = if run_frame.slots_required > 0 {
                    run_frame.slots_required as u32
                } else {
                    Err(FrameManagerError::InvalidArgument(
                        "Core based frame cannot be launched on a slot configured host".to_string(),
                    ))?
                };
                self.machine
                    .reserve_slots(reserved_slots)
                    .await
                    .map_err(|err| {
                        FrameManagerError::Aborted(format!(
                            "Not launching, failed to reserve {:} slots {:?}",
                            run_frame.slots_required, err
                        ))
                    })?;

                Arc::new(RunningFrame::init(
                    run_frame,
                    uid,
                    CONFIG.runner.clone(),
                    // Disable taskset to avoid binding this frame to specific threads
                    None,
                    gpu_list,
                    self.machine.get_host_name(),
                ))
            }
        };

        if cfg!(feature = "containerized_frames") && CONFIG.runner.run_on_docker {
            #[cfg(feature = "containerized_frames")]
            self.spawn_docker_frame(running_frame, false);
        } else if self.spawn_running_frame(running_frame, false).is_err() {
            let release_res = if slot_based_booking {
                // Release slots reserved if spawning the frame failed
                self.machine.release_slots(reserved_slots).await
            } else {
                // Release cores reserved if spawning the frame failed
                self.machine.release_cores(&resource_id).await
            };

            // Log failure to release
            if let Err(err) = release_res {
                warn!(
                    "Failed to release resources reserved for {} during spawn failure. {}",
                    &resource_id, err
                );
            }
        }

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
        let snapshots_path = &CONFIG.runner.snapshots_path;
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
        let slot_based_booking = self.machine.is_slot_configured().await;

        for path in snapshot_dir {
            let running_frame = RunningFrame::from_snapshot(&path, CONFIG.runner.clone())
                .await
                .map(Arc::new);
            match running_frame {
                Ok(running_frame) => {
                    let resource_id = running_frame.request.resource_id();
                    let mut reserved_slots = 0;

                    // Update reservations based on booking mode
                    if let Err(err) = match slot_based_booking {
                        // Core-based booking: If a thread_ids list exists, the frame was booked using affinity
                        false => {
                            match &running_frame.thread_ids {
                                Some(thread_ids) => {
                                    self.machine
                                        .reserve_cores(
                                            Either::Right(thread_ids.clone()),
                                            running_frame.request.resource_id(),
                                        )
                                        .await
                                }
                                None => {
                                    let num_cores = (running_frame.request.num_cores as u32)
                                        .div_ceil(CONFIG.machine.core_multiplier);
                                    self.machine
                                        .reserve_cores(
                                            Either::Left(num_cores as usize),
                                            running_frame.request.resource_id(),
                                        )
                                        .await
                                }
                            }
                            // Ignore reserved threads as they are no longer necessary
                            .map(|_| ())
                        }
                        // Slot-based booking
                        true => {
                            reserved_slots = if running_frame.request.slots_required > 0 {
                                running_frame.request.slots_required as u32
                            } else {
                                errors.push(format!(
                                    "Core based frame {} cannot be recovered on a slot configured host",
                                    resource_id
                                ));
                                continue;
                            };
                            self.machine.reserve_slots(reserved_slots).await
                        }
                    } {
                        errors.push(err.to_string());
                    }

                    if CONFIG.runner.run_on_docker {
                        todo!("Recovering frames when running on docker is not yet supported")
                    } else if self.spawn_running_frame(running_frame, true).is_err() {
                        let release_res = if slot_based_booking {
                            // Release slots reserved if spawning the frame failed
                            self.machine.release_slots(reserved_slots).await
                        } else {
                            self.machine.release_cores(&resource_id).await
                        };

                        // Failed to release
                        if let Err(err) = release_res {
                            warn!(
                                "Failed to release resources reserved for {} during recover spawn error. {}",
                                &resource_id, err
                            );
                        }
                    }
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

    fn spawn_running_frame(
        &self,
        running_frame: Arc<RunningFrame>,
        recover_mode: bool,
    ) -> Result<()> {
        self.machine.add_running_frame(Arc::clone(&running_frame));
        let running_frame_ref: Arc<RunningFrame> = Arc::clone(&running_frame);
        let thread_handle = tokio::spawn(async move { running_frame.run(recover_mode).await });
        running_frame_ref
            .update_launch_thread_handle(thread_handle)
            .map_err(|err| {
                warn!(
                    "Failed to update thread handle for frame {}. {}",
                    running_frame_ref, err
                );
                err
            })?;
        Ok(())
    }

    #[cfg(feature = "containerized_frames")]
    fn spawn_docker_frame(&self, running_frame: Arc<RunningFrame>, recovery_mode: bool) {
        self.machine.add_running_frame(Arc::clone(&running_frame));
        let _thread_handle =
            tokio::spawn(async move { running_frame.run_docker(recovery_mode).await });
    }

    fn validate_grpc_frame(&self, run_frame: &RunFrame) -> Result<(), FrameManagerError> {
        // Frame is already running
        if self.machine.is_frame_running(&run_frame.frame_id()) {
            Err(FrameManagerError::AlreadyExist(format!(
                "Not lauching, frame is already running on this host {}",
                run_frame.frame_id()
            )))?
        }
        // Trying to run as root
        if run_frame
            .uid_optional
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
        self.machine.get_running_frame(frame_id)
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
                let pid = running_frame.get_pid_to_kill(&reason);
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

    /// Kills all running frames on this host.
    ///
    /// This function iterates through all running frames and attempts to terminate each one.
    /// For each frame that is successfully killed, a monitor task is spawned to ensure the
    /// process fully terminates.
    ///
    /// # Arguments
    ///
    /// * `reason` - A string describing why the frames are being killed
    ///
    /// # Returns
    ///
    /// * `Ok(count)` - The number of frames that were successfully killed
    /// * `Err(miette::Error)` - If any frame exists but has no pid assigned (invalid state)
    pub async fn kill_all_running_frames(&self, reason: &str) -> Result<usize> {
        let mut count = 0;
        for frame_id in self.machine.all_running_frame_ids() {
            if let Some(running_frame) = self.get_running_frame(&frame_id) {
                let pid = running_frame.get_pid_to_kill(reason);
                if let Ok(frame_pid) = pid {
                    info!(
                        "Killing frame {running_frame}({frame_pid}) as a kill_all request.\n\
                        Reason: {reason}"
                    );
                    self.machine.kill_session(frame_pid, false).await?;
                    self.monitor_killed_frame(frame_pid, &running_frame);
                    count += 1;
                } else {
                    Err(miette!(
                        "Kill frame with invalid State. Frame {running_frame} exists but has \
                        no pid assigned to it"
                    ))?
                }
            }
        }
        Ok(count)
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
        let interval_seconds = CONFIG.runner.kill_monitor_interval.as_secs();
        let mut monitor_limit_seconds = CONFIG.runner.kill_monitor_timeout.as_secs();
        let force_kill = CONFIG.runner.force_kill_after_timeout;
        let mut tried_to_force_kill_session = false;
        let mut interval = time::interval(CONFIG.runner.kill_monitor_interval);

        // Now into localized timestamp
        let time_str: DateTime<Local> = SystemTime::now().into();
        let kill_request_time = time_str.format("%Y-%m-%d %H:%M:%S").to_string();

        let job_str = format!("{}", running_frame);
        let machine = Arc::clone(&self.machine);

        tokio::spawn(async move {
            loop {
                interval.tick().await;

                let active_lineage = machine.get_active_proc_lineage(frame_pid).await;
                if let Some(mut lineage) = active_lineage {
                    lineage.push(frame_pid);
                    // Check limit before decrementing as tick() returns immediately on the first call
                    if monitor_limit_seconds == 0 || tried_to_force_kill_session {
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
                            tried_to_force_kill_session = true;
                            // First try to force kill the session
                            match machine.kill_session(frame_pid, true).await {
                                Ok(()) => {
                                    info!(
                                        "Kill timeout for {}. Used session force_kill on \
                                        session_id {} to kill {:?}",
                                        job_str, frame_pid, lineage
                                    )
                                }
                                Err(err) => {
                                    warn!(
                                        "Failed to force_kill {} lineage = {:?}. {}",
                                        job_str, lineage, err
                                    )
                                }
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
                    monitor_limit_seconds = monitor_limit_seconds.saturating_sub(interval_seconds);
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
