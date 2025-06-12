use std::{
    collections::{HashMap, HashSet},
    sync::Arc,
};

use async_trait::async_trait;
use bytesize::KIB;
use miette::{IntoDiagnostic, Result, miette};
use opencue_proto::{
    host::HardwareState,
    report::{CoreDetail, HostReport, RenderHost},
};
use tokio::{
    select,
    sync::{
        Mutex,
        oneshot::{self, Sender},
    },
    time,
};
use tracing::{debug, error, info, warn};
use uuid::Uuid;

#[cfg(target_os = "macos")]
use crate::system::macos::MacOsSystem;
use crate::{
    config::config::{Config, MachineConfig},
    frame::{
        cache::RunningFrameCache,
        running_frame::{FrameState, RunningFrame, RunningState},
    },
    report::report_client::{ReportClient, ReportInterface},
};

use super::{
    linux::LinuxSystem,
    manager::{ReservationError, SystemManagerType},
};

/// Constantly monitor the state of this machine and report back to Cuebot
///
/// Example:
/// ```
/// #[tokio::main]
/// async fn main() -> miette::Result<()> {
///   let running_frame_cache = RunningFrameCache::init();
///   // Inicialize cuebot client
///   let report_client = Arc::new(ReportClient::build(&config).await?);
///   // Initialize rqd machine monitor
///   let machine_monitor =
///      MachineMonitor::init(
///         &config,
///         report_client,
///         Arc::clone(&running_frame_cache))?;
///   tokio::spawn(async move { machine_monitor.start().await });
/// }
/// ```
pub struct MachineMonitor {
    maching_config: MachineConfig,
    report_client: Arc<ReportClient>,
    pub system_manager: Mutex<SystemManagerType>,
    pub running_frames_cache: Arc<RunningFrameCache>,
    core_state: Arc<Mutex<CoreDetail>>,
    last_host_state: Arc<Mutex<Option<RenderHost>>>,
    interrupt: Mutex<Option<Sender<()>>>,
    reboot_when_idle: Mutex<bool>,
}

impl MachineMonitor {
    /// Initializes the object without starting the monitor loop
    /// Will gather the initial state of this machine
    pub fn init(config: &Config, report_client: Arc<ReportClient>) -> Result<Self> {
        #[cfg(any(target_os = "macos"))]
        #[allow(unused_variables)]
        let system_manager: SystemManagerType = Box::new(MacOsSystem::init(&config.machine)?);

        // Allow linux logic compilation from mac development environments
        #[cfg(any(target_os = "linux", all(debug_assertions)))]
        let system_manager: SystemManagerType = Box::new(LinuxSystem::init(&config.machine)?);

        Ok(Self {
            maching_config: config.machine.clone(),
            report_client,
            system_manager: Mutex::new(system_manager),
            running_frames_cache: RunningFrameCache::init(),
            core_state: Arc::new(Mutex::new(CoreDetail::default())),
            last_host_state: Arc::new(Mutex::new(None)),
            interrupt: Mutex::new(None),
            reboot_when_idle: Mutex::new(false),
        })
    }

    /// Starts an async loop that will update the machine state every `monitor_interval_seconds`.
    pub async fn start(&self) -> Result<()> {
        let report_client = self.report_client.clone();

        let system_lock = self.system_manager.lock().await;
        let host_state = Self::inspect_host_state(&self.maching_config, &system_lock)?;
        drop(system_lock);

        self.last_host_state
            .lock()
            .await
            .replace(host_state.clone());
        let total_cores = host_state.num_procs * host_state.cores_per_proc as i32;
        let initial_core_state = CoreDetail {
            total_cores,
            idle_cores: total_cores,
            locked_cores: 0,
            booked_cores: 0,
            reserved_cores: HashMap::default(),
        };
        {
            // Setup initial state
            let mut core_state_lock = self.core_state.lock().await;
            *core_state_lock = initial_core_state.clone();
        }
        debug!("Sending start report: {:?}", host_state);
        report_client
            .send_start_up_report(host_state, initial_core_state)
            .await?;

        let mut interval = time::interval(self.maching_config.monitor_interval);

        let (sender, mut receiver) = oneshot::channel::<()>();
        let mut interrupt_lock = self.interrupt.lock().await;
        interrupt_lock.replace(sender);
        drop(interrupt_lock);

        loop {
            select! {
                message = &mut receiver => {
                    match message {
                        Ok(_) => {
                            info!("Loop interrupted");
                            break;
                        },
                        Err(_) => info!("Sender dropped"),
                    }
                }
                _ = interval.tick() => {
                    self.collect_and_send_host_report().await?;
                    self.check_reboot_flag().await;
                }
            }
        }
        Ok(())
    }

    pub async fn interrupt(&self) {
        let mut lock = self.interrupt.lock().await;
        match lock.take() {
            Some(sender) => {
                if let Err(_) = sender.send(()) {
                    warn!("Failed to request a monitor interruption")
                }
            }
            None => warn!("Interrupt channel has already been used"),
        }
    }

    async fn collect_and_send_host_report(&self) -> Result<()> {
        let report_client = self.report_client.clone();
        let host_report = self.collect_host_report().await?;

        debug!("Sending host report: {:?}", host_report.host);
        report_client.send_host_report(host_report).await?;
        Ok(())
    }

    async fn check_reboot_flag(&self) {
        if *self.reboot_when_idle.lock().await {
            warn!("Machine became idle. Rebooting..");
            if let Err(err) = self.system_manager.lock().await.reboot() {
                error!("Failed to reboot when became idle. {err}");
            };
        }
    }

    async fn monitor_running_frames(&self) -> Result<()> {
        let mut finished_frames: Vec<Arc<RunningFrame>> = Vec::new();
        let mut running_frames: Vec<(Arc<RunningFrame>, RunningState)> = Vec::new();

        // Only keep running frames on the cache and store a copy of their state
        // to avoid having to deal with the state lock
        self.running_frames_cache
            .retain(|_, running_frame| match running_frame.get_state_copy() {
                FrameState::Created(_) => true,
                FrameState::Running(running_state) => {
                    running_frames.push((Arc::clone(&running_frame), running_state));
                    true
                }
                FrameState::Finished(_) => {
                    finished_frames.push(Arc::clone(running_frame));
                    false
                }
                FrameState::FailedBeforeStart => {
                    finished_frames.push(Arc::clone(running_frame));
                    false
                }
            });

        // Handle Running frames separately to avoid deadlocks when trying to get a frame state
        for (running_frame, running_state) in running_frames {
            // Collect stats about the procs related to this frame
            let proc_stats_opt = {
                let system_monitor = self.system_manager.lock().await;
                system_monitor
                    .collect_proc_stats(running_state.pid, running_frame.log_path.clone())
                    .unwrap_or_else(|err| {
                        warn!("Failed to collect proc_stats. {}", err);
                        None
                    })
            };

            if let Some(proc_stats) = proc_stats_opt {
                // Update stats for running frames
                running_frame.update_frame_stats(proc_stats);
            } else if running_frame.is_marked_for_cache_removal() {
                // Only remove procs that have been marked for removal
                warn!(
                    "Removing {} from the cache. Could not find proc {} for frame that was supposed to be running.",
                    running_frame.to_string(),
                    running_state.pid
                );
                // Attempt to finish the process
                let _ = running_frame.finish(1, Some(19));
                finished_frames.push(Arc::clone(&running_frame));
                self.running_frames_cache.remove(&running_frame.frame_id);
            } else {
                // Proc finished but frame is waiting for the lock on `is_finished` to update the status
                // keep frame around for another round
                running_frame.mark_for_cache_removal();
            }
        }

        self.handle_finished_frames(finished_frames).await;
        Ok(())
    }

    async fn handle_finished_frames(&self, finished_frames: Vec<Arc<RunningFrame>>) {
        if finished_frames.is_empty() {
            return;
        }

        // Avoid holding a lock while reporting back to cuebot
        let host_state_opt = {
            let host_state_lock = self.last_host_state.lock().await;
            host_state_lock.clone()
        };

        let host_state = match host_state_opt {
            Some(state) => state,
            None => {
                warn!("Invalid state. Could not find host state");
                return;
            }
        };

        for frame in finished_frames {
            let exit_code_and_signal: Option<(u32, u32)> = match frame.get_state_copy() {
                FrameState::Finished(finished_state) => {
                    let exit_signal = match finished_state.exit_signal {
                        Some(signal) => signal as u32,
                        None => 0,
                    };
                    Some((finished_state.exit_code as u32, exit_signal))
                }
                FrameState::FailedBeforeStart => {
                    Some((
                        1,  // Mark frame as failed
                        10, // Use signal to indicate it failed before starting
                    ))
                }
                _ => None,
            };

            if let Some((exit_code, exit_signal)) = exit_code_and_signal {
                let frame_report = frame.into_running_frame_info();
                info!("Sending frame complete report: {}", frame);

                // Release resources
                if let Some(threads) = &frame.thread_ids {
                    self.release_threads(threads).await;
                } else {
                    // Ensure the division rounds up if num_cores is not a multiple of
                    // core_multiplier
                    let num_cores_to_release =
                        (frame.request.num_cores as u32 + self.maching_config.core_multiplier - 1)
                            / self.maching_config.core_multiplier;
                    self.release_cores(num_cores_to_release).await;
                }

                // Send complete report
                if let Err(err) = self
                    .report_client
                    .send_frame_complete_report(
                        host_state.clone(),
                        frame_report,
                        exit_code,
                        exit_signal,
                        0,
                    )
                    .await
                {
                    error!(
                        "Failed to send frame_complete_report for {}. {}",
                        frame, err
                    );
                };
            }
        }
    }

    fn inspect_host_state(
        config: &MachineConfig,
        system: &SystemManagerType,
    ) -> Result<RenderHost> {
        let stats = system.collect_stats()?;
        let gpu_stats = system.collect_gpu_stats();

        Ok(RenderHost {
            name: stats.hostname,
            nimby_enabled: system.init_nimby()?,
            nimby_locked: false, // TODO: implement nimby lock
            facility: config.facility.clone(),
            num_procs: stats.num_sockets as i32,
            cores_per_proc: (stats.cores_per_socket * config.core_multiplier) as i32,
            total_swap: (stats.total_swap / KIB) as i64,
            total_mem: (stats.total_memory / KIB) as i64,
            total_mcp: (stats.total_temp_storage / KIB) as i64,
            free_swap: (stats.free_swap / KIB) as i64,
            free_mem: (stats.available_memory / KIB) as i64,
            free_mcp: (stats.free_temp_storage / KIB) as i64,
            load: stats.load as i32,
            boot_time: stats.boot_time as i32,
            tags: stats.tags,
            state: system.hardware_state().clone() as i32,
            attributes: system.attributes().clone(),
            num_gpus: gpu_stats.count as i32,
            free_gpu_mem: gpu_stats.free_memory as i64,
            total_gpu_mem: gpu_stats.total_memory as i64,
        })
    }
}

/// Performe actions on a machine with an async lock
#[async_trait]
pub trait Machine {
    async fn hardware_state(&self) -> Option<HardwareState>;
    async fn nimby_locked(&self) -> bool;

    /// Reserve CPU cores
    ///
    /// # Argument
    ///
    /// * `num_cores` - The number of cores to reserve
    /// * `resource_id` - Id of the resource to be associated to the reservation
    /// * `with_affinity` - If true, use `taskset` to attempt to reserve cores that
    ///    might share the same cache
    ///
    /// # Returns
    ///
    /// List of threads ids belonging to the reserved cores
    async fn reserve_cores(
        &self,
        num_cores: usize,
        resource_id: Uuid,
        with_affinity: bool,
    ) -> Result<Option<Vec<u32>>>;

    /// Reserve specific CPU cores by their IDs
    ///
    /// # Arguments
    ///
    /// * `thread_ids` - Vector of thread ids to reserve
    /// * `resource_id` - Unique identifier for the resource that will use these cores
    ///
    /// # Returns
    ///
    /// Vector of successfully reserved CPU core IDs
    async fn reserve_cores_by_id(
        &self,
        thread_ids: &Vec<u32>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>>;

    /// Release specific threads
    ///
    /// # Arguments
    ///
    /// * `threads` - Vector of thread IDs to release
    async fn release_threads(&self, thread_ids: &Vec<u32>);

    /// Releases a specified number of CPU cores
    ///
    /// # Arguments
    ///
    /// * `num_cores` - The number of cores to release
    async fn release_cores(&self, num_cores: u32);

    /// Reserve GPU units
    ///
    /// # Argument
    ///
    /// * `num_gpus` - Number of gpu units to be reserved
    ///
    /// # Returns
    ///
    /// List of gpu units
    async fn reserve_gpus(&self, num_gpus: u32) -> Result<Vec<u32>>;

    /// Creates a user account if it doesn't already exist in the system
    ///
    /// # Arguments
    ///
    /// * `username` - The name of the user to create
    /// * `uid` - The user ID to assign to the new user
    /// * `gid` - The group ID to assign to the new user
    ///
    /// # Returns
    ///
    /// The user ID (uid) of the created or existing user
    async fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32>;

    async fn get_host_name(&self) -> String;

    /// Send a signal to kill a process
    ///
    /// # Returns Errors:
    ///  * [EINVAL] The value of the sig argument is an invalid or unsupported signal number.
    ///  * [EPERM] The process does not have permission to send the signal to any receiving process.
    ///  * [ESRCH] No process or process group can be found corresponding to that specified by pid.
    async fn kill_session(&self, pid: u32, force: bool) -> Result<()>;

    async fn force_kill(&self, pids: &Vec<u32>) -> Result<()>;

    /// Check if this pid and any of its children are still active
    /// Returns the list of active children, and none if the pid itself is not active
    async fn get_active_proc_lineage(&self, pid: u32) -> Option<Vec<u32>>;

    async fn lock_cores(&self, count: u32) -> u32;

    async fn lock_all_cores(&self);

    async fn unlock_cores(&self, count: u32) -> u32;

    async fn unlock_all_cores(&self);

    async fn reboot_if_idle(&self) -> Result<()>;

    async fn collect_host_report(&self) -> Result<HostReport>;

    async fn quit(&self);

    fn add_running_frame(&self, running_frame: Arc<RunningFrame>);

    fn is_frame_running(&self, frame_id: &Uuid) -> bool;

    fn get_running_frame(&self, frame_id: &Uuid) -> Option<Arc<RunningFrame>>;
}

#[async_trait]
impl Machine for MachineMonitor {
    async fn hardware_state(&self) -> Option<HardwareState> {
        self.last_host_state
            .lock()
            .await
            .as_ref()
            .map(|hs| hs.state().clone())
    }

    async fn nimby_locked(&self) -> bool {
        self.last_host_state
            .lock()
            .await
            .as_ref()
            .map(|hs| hs.nimby_locked)
            .unwrap_or(false)
    }

    async fn reserve_cores(
        &self,
        num_cores: usize,
        resource_id: Uuid,
        with_affinity: bool,
    ) -> Result<Option<Vec<u32>>> {
        // Reserve cores on the socket level
        let cores_result = if with_affinity {
            let mut system_lock = self.system_manager.lock().await;
            system_lock
                .reserve_cores(num_cores, resource_id)
                .into_diagnostic()
                .map(|v| Some(v))
        } else {
            Ok(None)
        };

        // Record reservation to be reported to cuebot
        if let Ok(_) = &cores_result {
            let mut core_state = self.core_state.lock().await;
            debug!("Before: {:?}", *core_state);
            core_state
                .reserve(num_cores * self.maching_config.core_multiplier as usize)
                .map_err(|err| miette!(err))?;
            debug!("After: {:?}", *core_state);
        }
        cores_result
    }

    async fn reserve_cores_by_id(
        &self,
        thread_ids: &Vec<u32>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>> {
        // Reserve cores on the socket level
        let thread_ids = {
            let mut system_lock = self.system_manager.lock().await;
            system_lock
                .reserve_cores_by_id(thread_ids, resource_id)
                .into_diagnostic()
        }?;

        // Record reservation to be reported to cuebot
        let mut core_state = self.core_state.lock().await;
        core_state
            .reserve(thread_ids.len() * self.maching_config.core_multiplier as usize)
            .map_err(|err| miette!(err))?;

        Ok(thread_ids)
    }

    async fn release_threads(&self, thread_ids: &Vec<u32>) {
        let mut released_cores = HashSet::new();
        {
            let mut system = self.system_manager.lock().await;
            for thread_id in thread_ids {
                match system.release_core_by_thread(thread_id) {
                    Ok((phys_id, core_id)) => {
                        released_cores.insert((phys_id, core_id));
                    }
                    Err(err) => match err {
                        ReservationError::ReservationNotFound(_) => {
                            // NoOp. When releasing a thread, the entire core might be released,
                            // threfore misses are expected
                        }
                        _ => {
                            error!("Failed to release proc {thread_id}. Unexpected error")
                        }
                    },
                }
            }
        }
        // Record reservation to be reported to cuebot
        let mut core_state = self.core_state.lock().await;
        if let Err(err) = core_state
            .release(released_cores.len() as u32 * self.maching_config.core_multiplier)
            .map_err(|err| miette!(err))
        {
            error!(
                "Accountability error. Failed to release the requested number of cores. {}",
                err
            )
        };
    }

    async fn release_cores(&self, num_cores: u32) {
        // Record reservation to be reported to cuebot
        let mut core_state = self.core_state.lock().await;
        if let Err(err) = core_state
            .release(num_cores as u32 * self.maching_config.core_multiplier)
            .map_err(|err| miette!(err))
        {
            error!(
                "Accountability error. Failed to release the requested number of cores. {}",
                err
            )
        };
    }

    async fn reserve_gpus(&self, _num_gpus: u32) -> Result<Vec<u32>> {
        todo!()
    }

    async fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32> {
        let system = self.system_manager.lock().await;
        system.create_user_if_unexisting(username, uid, gid)
    }

    async fn get_host_name(&self) -> String {
        let lock = self.last_host_state.lock().await;

        lock.as_ref()
            .map(|h| h.name.clone())
            .unwrap_or("noname".to_string())
    }

    async fn kill_session(&self, pid: u32, force: bool) -> Result<()> {
        let system = self.system_manager.lock().await;
        if force {
            system.force_kill_session(pid)
        } else {
            system.kill_session(pid)
        }
    }

    async fn force_kill(&self, pids: &Vec<u32>) -> Result<()> {
        let system = self.system_manager.lock().await;
        system.force_kill(pids)
    }

    async fn get_active_proc_lineage(&self, pid: u32) -> Option<Vec<u32>> {
        let system = self.system_manager.lock().await;
        system.get_proc_lineage(pid)
    }

    async fn lock_cores(&self, count: u32) -> u32 {
        let mut core_state = self.core_state.lock().await;
        core_state.lock_cores(count * self.maching_config.core_multiplier)
    }

    async fn lock_all_cores(&self) {
        let mut core_state = self.core_state.lock().await;
        core_state.lock_all_cores();
    }

    async fn unlock_cores(&self, count: u32) -> u32 {
        let mut core_state = self.core_state.lock().await;
        core_state.unlock_cores(count * self.maching_config.core_multiplier)
    }

    async fn unlock_all_cores(&self) {
        let mut core_state = self.core_state.lock().await;
        core_state.unlock_all_cores();
    }

    async fn reboot_if_idle(&self) -> Result<()> {
        // Prevent new frames from booking
        self.lock_all_cores().await;

        if self.running_frames_cache.len() > 0 {
            // Schedule reboot if the machine is not idle
            let mut reboot_when_idle = self.reboot_when_idle.lock().await;

            warn!("Machine set to reboot when idle");
            *reboot_when_idle = true;
        } else {
            // Reboot now
            let system = self.system_manager.lock().await;

            warn!("Rebooting machine on request");
            system.reboot()?;
        }
        Ok(())
    }

    async fn collect_host_report(&self) -> Result<HostReport> {
        let system_manager = self.system_manager.lock().await;
        // If there are frames running update the list of procs on the machine
        if !self.running_frames_cache.is_empty() {
            system_manager.refresh_procs();
        }
        let render_host = Self::inspect_host_state(&self.maching_config, &system_manager)?;
        drop(system_manager);
        // Store the last host_state on self
        let mut self_host_state_lock = self.last_host_state.lock().await;
        self_host_state_lock.replace(render_host.clone());
        drop(self_host_state_lock);

        let core_state = { self.core_state.lock().await.clone() };
        self.monitor_running_frames().await?;

        Ok(HostReport {
            host: Some(render_host),
            frames: Arc::clone(&self.running_frames_cache).into_running_frame_vec(),
            core_info: Some(core_state),
        })
    }

    async fn quit(&self) {
        self.interrupt().await;
        std::process::exit(0);
    }

    fn add_running_frame(&self, running_frame: Arc<RunningFrame>) {
        self.running_frames_cache
            .insert_running_frame(running_frame);
    }

    fn is_frame_running(&self, frame_id: &Uuid) -> bool {
        self.running_frames_cache.contains(frame_id)
    }
    fn get_running_frame(&self, frame_id: &Uuid) -> Option<Arc<RunningFrame>> {
        self.running_frames_cache
            .get(frame_id)
            .as_ref()
            .map(|f| Arc::clone(f))
    }
}
