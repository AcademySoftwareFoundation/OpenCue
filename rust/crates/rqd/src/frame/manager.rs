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
use itertools::{Either, Itertools};
use miette::{miette, Diagnostic, Result};
use opencue_proto::{
    host::HardwareState,
    rqd::{run_frame, RunFrame},
};
use std::{
    collections::HashMap,
    fs,
    path::Path,
    sync::Arc,
    time::{Duration, SystemTime},
};
use thiserror::Error;
use tokio::{sync::OnceCell, time};
use tracing::{error, info, warn};
use uuid::Uuid;

#[cfg(feature = "containerized_frames")]
use super::docker_running_frame;

use super::running_frame::RunningFrame;
use crate::{
    config::{RunnerConfig, CONFIG},
    servant::rqd_servant::MachineImpl,
    system::{machine, manager::Lineage},
};

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

        // **Attention**: If an error happens between here and spawning a frame, the resources
        // reserved need to be released.

        let num_cores = (run_frame.num_cores as u32).div_ceil(CONFIG.machine.core_multiplier);

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
        // Although num_gpus is not required on a frame, the field is not optional on the proto
        // layer. =0 means None, !=0 means Some
        let gpu_list = match run_frame.num_gpus {
            0 => None,
            _ => {
                let reserved_res = self.machine.reserve_gpus(run_frame.num_gpus as u32).await;
                if reserved_res.is_err() {
                    // Release cores reserved on the last step
                    if let Err(err) = self.machine.release_cores(&run_frame.resource_id()).await {
                        warn!(
                            "Failed to release cores reserved for {} during gpu reservation failure. {}",
                            &run_frame.resource_id(),
                            err
                        )
                    };
                }
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
        // Ignore the list of allocated threads if hyperthreading is off
        let thread_ids = hyperthreaded.then_some(thread_ids);

        let resource_id = run_frame.resource_id();
        let hyperthreading_multiplier = self.machine.get_hyperthreading_multiplier().await;
        let running_frame = Arc::new(RunningFrame::init(
            run_frame,
            uid,
            CONFIG.runner.clone(),
            thread_ids,
            gpu_list,
            self.machine.get_host_name().await,
            hyperthreading_multiplier,
        ));

        if cfg!(feature = "containerized_frames") && CONFIG.runner.run_on_docker {
            #[cfg(feature = "containerized_frames")]
            self.spawn_docker_frame(running_frame, false);
        } else if self.spawn_running_frame(running_frame, false).is_err() {
            // Release cores reserved if spawning the frame failed
            if let Err(err) = self.machine.release_cores(&resource_id).await {
                warn!(
                    "Failed to release cores reserved for {} during spawn failure. {}",
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
    /// - Keeps one snapshot per frame id, preferring one whose process is alive (see
    ///   [`prefer_live_snapshots`]); stale duplicates are removed
    /// - Spawns recovered frames to continue execution
    /// - Cleans up invalid or corrupted snapshot files
    ///
    /// # Returns
    ///
    /// * `Ok(Recovery)` once every snapshot was looked at, even if some frames failed to be
    ///   recovered (see [`Recovery::errors`])
    /// * `Err(miette::Error)` if the snapshots directory could not be listed in full, missing
    ///   directory included: it is created at startup, so a missing one means snapshots were
    ///   lost and rqd can't tell which frames are still running
    pub async fn recover_snapshots(&self) -> Result<Recovery> {
        let snapshots_path = &CONFIG.runner.snapshots_path;
        let snapshot_paths = list_snapshots(Path::new(snapshots_path))
            .map_err(|err| miette!("Failed to read snapshot dir {snapshots_path}. {err}"))?;

        let mut recovery = Recovery::default();
        let mut loaded = Vec::new();
        for path in snapshot_paths {
            match RunningFrame::from_snapshot(&path, CONFIG.runner.clone()).await {
                Ok(running_frame) => {
                    let launch = running_frame.launch();
                    if launch.contained {
                        recovery.claimed_launches.push(launch.id);
                    }
                    let alive = running_frame.is_process_alive();
                    loaded.push((path, Arc::new(running_frame), alive));
                }
                Err(err) => {
                    error!("Snapshot recover failed: {}", err);
                    if let Err(err) = fs::remove_file(&path) {
                        warn!("Snapshot {} failed to be cleared. {}", path, err);
                    };
                }
            }
        }

        let (recovered, duplicates) =
            prefer_live_snapshots(loaded, |(_, frame, alive)| (frame.frame_id, *alive));
        for (path, running_frame, alive) in duplicates {
            if alive {
                warn!(
                    "Snapshot {} of {} is a duplicate of another live snapshot and is not \
                     recovered. Its process is left running",
                    path, running_frame
                );
            } else {
                info!(
                    "Removing stale snapshot {} of {}, another snapshot of the frame is recovered",
                    path, running_frame
                );
                if let Err(err) = fs::remove_file(&path) {
                    warn!("Snapshot {} failed to be cleared. {}", path, err);
                };
            }
        }

        for (path, running_frame, _) in recovered {
            // Recovering docker frames is not supported yet. Skip the snapshot (keeping
            // the file for manual inspection) instead of crashing: a todo!/panic here
            // would put the service in a startup crash-loop under its supervisor.
            if CONFIG.runner.run_on_docker {
                error!(
                    "Skipping snapshot of {}: recovering docker frames is not \
                     supported yet. The frame may still be running unmanaged; \
                     remove {} to silence this on the next startup",
                    running_frame, &path
                );
                continue;
            }

            // Update reservations. If a thread_ids list exists, the frame was booked using affinity
            if let Err(err) = match &running_frame.thread_ids {
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
            } {
                recovery.errors.push(err.to_string());
            }

            let resource_id = running_frame.request.resource_id();
            if self.spawn_running_frame(running_frame, true).is_err() {
                if let Err(err) = self.machine.release_cores(&resource_id).await {
                    warn!(
                        "Failed to release cores reserved for {} during recover spawn error. {}",
                        &resource_id, err
                    );
                }
            }
        }

        Ok(recovery)
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

        // A reboot or service restart is pending. Accepting a frame would either extend the
        // idle wait indefinitely or race the imminent process exit (a frame spawned right
        // before the exit could die before its snapshot is written, leaking an unmanaged
        // render that Cuebot would then double-book).
        if self.machine.idle_action_pending().await {
            Err(FrameManagerError::Aborted(
                "Not launching, host has a pending reboot or rqd service restart".to_string(),
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
    /// Sends the frame a termination signal and arms a monitor that escalates to a force kill
    /// when the frame's processes linger (see [`Self::monitor_killed_frame`]). The monitor is
    /// armed even when the signal fails for some of the processes, so the frame is still
    /// escalated.
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
    ///     - The signal failed for some of the frame's processes (the monitor is still armed)
    pub async fn kill_running_frame(&self, frame_id: &Uuid, reason: String) -> Result<Option<()>> {
        match self.get_running_frame(frame_id) {
            Some(running_frame) => {
                self.kill_frame(&running_frame, &reason, "by request")
                    .await?;
                Ok(Some(()))
            }
            None => Ok(None),
        }
    }

    /// Kills all running frames on this host.
    ///
    /// Every running frame is killed as in [`Self::kill_running_frame`]. A failure on one frame
    /// doesn't stop the others from being killed.
    ///
    /// # Arguments
    ///
    /// * `reason` - A string describing why the frames are being killed
    ///
    /// # Returns
    ///
    /// * `Ok(count)` - The number of frames killed, each with a monitor armed
    /// * `Err(miette::Error)` - Combines the errors of every frame that failed: frames without a
    ///   pid assigned (invalid state) and frames whose signal failed for some of their
    ///   processes. The latter still have a monitor armed.
    pub async fn kill_all_running_frames(&self, reason: &str) -> Result<usize> {
        let mut count = 0;
        let mut errors = Vec::new();
        for frame_id in self.machine.all_running_frame_ids() {
            let Some(running_frame) = self.get_running_frame(&frame_id) else {
                continue;
            };
            match self
                .kill_frame(&running_frame, reason, "as a kill_all request")
                .await
            {
                Ok(()) => count += 1,
                Err(KillError::Signal(err)) => {
                    count += 1;
                    errors.push(err);
                }
                Err(KillError::NoPid(err)) => errors.push(err),
            }
        }
        if errors.is_empty() {
            Ok(count)
        } else {
            Err(miette!(
                "Failed to kill {} frames, {count} frames are monitored: {}",
                errors.len(),
                errors.iter().map(|err| err.to_string()).join("; ")
            ))
        }
    }

    /// Signals `running_frame` and arms its kill monitor, whether or not the signal reached
    /// every process. `context` tells in the log why the frame is killed.
    async fn kill_frame(
        &self,
        running_frame: &RunningFrame,
        reason: &str,
        context: &str,
    ) -> Result<(), KillError> {
        let frame_pid = running_frame.get_pid_to_kill(reason).map_err(|_| {
            KillError::NoPid(miette!(
                "Kill frame with invalid State. Frame {running_frame} exists but has \
                no pid assigned to it"
            ))
        })?;
        info!(
            "Killing frame {running_frame}({frame_pid}) {context}.\n\
            Reason: {reason}"
        );
        let signalled = self
            .machine
            .kill_session(running_frame.launch(), frame_pid, false)
            .await;
        self.monitor_killed_frame(frame_pid, running_frame);
        signalled.map_err(|err| KillError::Signal(miette!("Frame {running_frame}: {err}")))
    }

    /// Monitors a killed frame to ensure it fully terminates.
    ///
    /// After a frame is killed, this function spawns a background task that periodically checks
    /// if the frame's processes have fully terminated. Processes still running after the
    /// time limit (see [`KillEscalation`]) are force killed, or reported when force killing is
    /// off. A contained launch is only ever force killed through its cgroup, never by pid.
    ///
    /// # Arguments
    ///
    /// * `frame_pid` - The process ID of the killed frame
    /// * `running_frame` - Reference to the RunningFrame object that was killed
    fn monitor_killed_frame(&self, frame_pid: u32, running_frame: &RunningFrame) {
        // Tracked by launch, so a retry of the frame on this host is out of reach.
        let launch = running_frame.launch();
        let escalation = KillEscalation::for_frame(launch.contained, &CONFIG.runner);
        let interval_seconds = escalation.interval.as_secs();
        let mut monitor_limit_seconds = escalation.timeout.as_secs();
        let force_kill = escalation.force;
        let mut tried_to_force_kill_session = false;
        let mut interval = time::interval(escalation.interval);

        // Now into localized timestamp
        let time_str: DateTime<Local> = SystemTime::now().into();
        let kill_request_time = time_str.format("%Y-%m-%d %H:%M:%S").to_string();

        let job_str = format!("{}", running_frame);
        let machine = Arc::clone(&self.machine);

        tokio::spawn(async move {
            loop {
                interval.tick().await;

                let active_lineage = match machine.get_active_proc_lineage(launch, frame_pid).await
                {
                    Lineage::Active(lineage) => Some(lineage),
                    Lineage::Gone => None,
                    Lineage::Unknown => {
                        warn!(
                            "Couldn't tell whether {} is still being killed, checking again later",
                            job_str
                        );
                        monitor_limit_seconds =
                            monitor_limit_seconds.saturating_sub(interval_seconds);
                        continue;
                    }
                };
                if let Some(lineage) = active_lineage {
                    let lineage = tracked_lineage(launch.contained, lineage, frame_pid);
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
                            match machine.kill_session(launch, frame_pid, true).await {
                                Ok(()) => {
                                    info!(
                                        "Kill timeout for {}. Used force_kill on the processes \
                                        of frame pid {} to kill {:?}",
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
                        } else if launch.contained {
                            // The wrapper pid may have been reused once the wrapper exited, so
                            // only the cgroup is trusted to tell the frame's processes.
                            match machine.kill_session(launch, frame_pid, true).await {
                                Ok(()) => info!(
                                    "Kill timeout for {}. Killed the cgroup again to kill {:?}",
                                    job_str, lineage
                                ),
                                Err(err) => warn!(
                                    "Failed to force_kill {} lineage = {:?}. {}",
                                    job_str, lineage, err
                                ),
                            }
                            break;
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

                monitor_limit_seconds = monitor_limit_seconds.saturating_sub(interval_seconds);
            }
        });
    }
}

/// What [`FrameManager::recover_snapshots`] got back from the snapshots on disk.
#[derive(Debug, Default)]
pub struct Recovery {
    /// Launch ids of the snapshotted frames whose processes run in a frame cgroup. Every other
    /// frame cgroup belongs to a frame rqd has lost track of.
    pub claimed_launches: Vec<Uuid>,
    /// Frames that were recovered but couldn't get their resources back.
    pub errors: Vec<String>,
}

/// Paths of the `.bin` snapshot files in `dir`. Fails unless the whole directory could be listed.
fn list_snapshots(dir: &Path) -> std::io::Result<Vec<String>> {
    let mut snapshots = Vec::new();
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if entry.file_type()?.is_file() && path.extension().is_some_and(|ext| ext == "bin") {
            if let Some(path) = path.to_str() {
                snapshots.push(path.to_string());
            }
        }
    }
    Ok(snapshots)
}

/// Splits `snapshots` into one to recover per frame id and the duplicates to drop, `key` giving
/// a snapshot's frame id and whether its process is alive.
///
/// A snapshot file is named after the frame's pid, so one left behind by an earlier run of a
/// frame can share its frame id with the current run. A live snapshot wins over a stale one,
/// otherwise the first one listed wins.
fn prefer_live_snapshots<T>(
    snapshots: Vec<T>,
    key: impl Fn(&T) -> (Uuid, bool),
) -> (Vec<T>, Vec<T>) {
    let mut kept: Vec<T> = Vec::new();
    let mut kept_index: HashMap<Uuid, usize> = HashMap::new();
    let mut duplicates = Vec::new();
    for snapshot in snapshots {
        let (frame_id, alive) = key(&snapshot);
        match kept_index.get(&frame_id) {
            None => {
                kept_index.insert(frame_id, kept.len());
                kept.push(snapshot);
            }
            Some(&index) if alive && !key(&kept[index]).1 => {
                duplicates.push(std::mem::replace(&mut kept[index], snapshot));
            }
            Some(_) => duplicates.push(snapshot),
        }
    }
    (kept, duplicates)
}

/// The processes the kill monitor reports and, for a session-tracked launch, force kills by pid.
///
/// A session-tracked lineage always includes the frame's `frame_pid`. A contained launch is
/// tracked by its cgroup members only: once the wrapper exits its pid may belong to an unrelated
/// process.
fn tracked_lineage(contained: bool, mut lineage: Vec<u32>, frame_pid: u32) -> Vec<u32> {
    if !contained && !lineage.contains(&frame_pid) {
        lineage.push(frame_pid);
    }
    lineage
}

/// Why [`FrameManager::kill_frame`] failed.
enum KillError {
    /// The frame has no pid to kill, nothing was signalled.
    NoPid(miette::Report),
    /// The signal failed for some of the frame's processes, its kill monitor is armed.
    Signal(miette::Report),
}

impl From<KillError> for miette::Report {
    fn from(err: KillError) -> Self {
        match err {
            KillError::NoPid(err) | KillError::Signal(err) => err,
        }
    }
}

/// How a kill request is followed up while the frame's processes linger.
#[derive(Debug, PartialEq, Eq)]
struct KillEscalation {
    /// How often the frame's processes are checked.
    interval: Duration,
    /// Time after the kill request when lingering processes are force killed, or reported.
    timeout: Duration,
    /// Whether lingering processes are force killed after `timeout` instead of only reported.
    force: bool,
}

impl KillEscalation {
    /// Frames contained in a cgroup are always force killed once
    /// `frame_cgroup_kill_grace_period` is over, every other frame follows the kill monitor
    /// settings.
    fn for_frame(contained: bool, config: &RunnerConfig) -> Self {
        if contained {
            let grace = config
                .frame_cgroup_kill_grace_period
                .max(Duration::from_secs(1));
            Self {
                interval: grace,
                timeout: grace,
                force: true,
            }
        } else {
            Self {
                interval: config.kill_monitor_interval,
                timeout: config.kill_monitor_timeout,
                force: config.force_kill_after_timeout,
            }
        }
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

#[cfg(test)]
mod tests {
    use std::time::Duration;

    use uuid::Uuid;

    use super::{list_snapshots, prefer_live_snapshots, tracked_lineage, KillEscalation};
    use crate::config::RunnerConfig;

    #[test]
    fn frames_without_cgroup_follow_the_kill_monitor_settings() {
        let config = RunnerConfig::default();

        assert_eq!(
            KillEscalation::for_frame(false, &config),
            KillEscalation {
                interval: config.kill_monitor_interval,
                timeout: config.kill_monitor_timeout,
                force: config.force_kill_after_timeout,
            }
        );
    }

    #[test]
    fn contained_frames_are_force_killed_after_the_grace_period() {
        let mut config = RunnerConfig::default();
        config.frame_cgroup_kill_grace_period = Duration::from_secs(45);
        config.force_kill_after_timeout = false;

        assert_eq!(
            KillEscalation::for_frame(true, &config),
            KillEscalation {
                interval: Duration::from_secs(45),
                timeout: Duration::from_secs(45),
                force: true,
            }
        );
    }

    #[test]
    fn session_lineage_includes_the_frame_pid() {
        assert_eq!(tracked_lineage(false, vec![20, 30], 10), vec![20, 30, 10]);
        assert_eq!(tracked_lineage(false, vec![10, 20], 10), vec![10, 20]);
    }

    #[test]
    fn contained_lineage_is_only_the_cgroup_members() {
        assert_eq!(tracked_lineage(true, vec![20, 30], 10), vec![20, 30]);
        assert_eq!(tracked_lineage(true, vec![10, 20], 10), vec![10, 20]);
    }

    #[test]
    fn zero_grace_period_is_clamped() {
        let mut config = RunnerConfig::default();
        config.frame_cgroup_kill_grace_period = Duration::ZERO;

        assert_eq!(
            KillEscalation::for_frame(true, &config).interval,
            Duration::from_secs(1)
        );
    }

    /// (frame id, alive, name) as a snapshot stand-in.
    fn snapshot(frame_id: Uuid, alive: bool, name: &'static str) -> (Uuid, bool, &'static str) {
        (frame_id, alive, name)
    }

    fn names(snapshots: &[(Uuid, bool, &'static str)]) -> Vec<&'static str> {
        snapshots.iter().map(|(_, _, name)| *name).collect()
    }

    fn pick(snapshots: Vec<(Uuid, bool, &'static str)>) -> (Vec<&'static str>, Vec<&'static str>) {
        let (kept, duplicates) =
            prefer_live_snapshots(snapshots, |&(frame_id, alive, _)| (frame_id, alive));
        (names(&kept), names(&duplicates))
    }

    #[test]
    fn a_live_snapshot_wins_over_a_stale_one_whatever_the_order() {
        let frame = Uuid::new_v4();

        assert_eq!(
            pick(vec![
                snapshot(frame, false, "stale"),
                snapshot(frame, true, "live")
            ]),
            (vec!["live"], vec!["stale"])
        );
        assert_eq!(
            pick(vec![
                snapshot(frame, true, "live"),
                snapshot(frame, false, "stale")
            ]),
            (vec!["live"], vec!["stale"])
        );
    }

    #[test]
    fn the_first_snapshot_wins_between_equally_live_ones() {
        let frame = Uuid::new_v4();

        assert_eq!(
            pick(vec![
                snapshot(frame, false, "first"),
                snapshot(frame, false, "second")
            ]),
            (vec!["first"], vec!["second"])
        );
        assert_eq!(
            pick(vec![
                snapshot(frame, true, "first"),
                snapshot(frame, true, "second")
            ]),
            (vec!["first"], vec!["second"])
        );
    }

    #[test]
    fn snapshots_of_distinct_frames_are_all_kept() {
        let (first, second) = (Uuid::new_v4(), Uuid::new_v4());

        assert_eq!(
            pick(vec![
                snapshot(first, false, "first"),
                snapshot(second, true, "second")
            ]),
            (vec!["first", "second"], vec![])
        );
    }

    #[test]
    fn lists_only_snapshot_files() {
        let dir = tempfile::TempDir::new().unwrap();
        std::fs::write(dir.path().join("job_frame_10.bin"), "").unwrap();
        std::fs::write(dir.path().join("notes.txt"), "").unwrap();
        std::fs::create_dir(dir.path().join("dir.bin")).unwrap();

        assert_eq!(
            list_snapshots(dir.path()).unwrap(),
            vec![dir.path().join("job_frame_10.bin").to_str().unwrap()]
        );
    }

    #[test]
    fn listing_a_missing_snapshot_dir_fails() {
        let dir = tempfile::TempDir::new().unwrap();

        assert!(list_snapshots(&dir.path().join("missing")).is_err());
    }
}
