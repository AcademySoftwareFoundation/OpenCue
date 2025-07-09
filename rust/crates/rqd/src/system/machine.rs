use std::sync::Arc;

use async_trait::async_trait;
use bytesize::KIB;
use itertools::Either;
use miette::Result;
use opencue_proto::{
    host::{HardwareState, LockState},
    report::{HostReport, RenderHost},
};
use tokio::{
    select,
    sync::{
        Mutex, RwLock,
        broadcast::{self, Receiver},
        oneshot,
    },
    time,
};
use tracing::{debug, error, info, warn};
use uuid::Uuid;

#[cfg(target_os = "macos")]
use crate::system::macos::MacOsSystem;
use crate::{
    config::{Config, MachineConfig},
    frame::{
        cache::RunningFrameCache,
        running_frame::{FrameState, RunningFrame, RunningState},
    },
    report::report_client::{ReportClient, ReportInterface},
    system::{manager::ReservationError, nimby::Nimby, reservation::CoreStateManager},
};

use super::{linux::LinuxSystem, manager::SystemManagerType};

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
    pub core_manager: Arc<RwLock<CoreStateManager>>,
    pub running_frames_cache: Arc<RunningFrameCache>,
    last_host_state: Arc<Mutex<Option<RenderHost>>>,
    interrupt: Mutex<Option<broadcast::Sender<()>>>,
    reboot_when_idle: Mutex<bool>,
    nimby: Arc<Option<Nimby>>,
    nimby_state: RwLock<LockState>,
}

impl MachineMonitor {
    /// Initializes the object without starting the monitor loop
    /// Will gather the initial state of this machine
    pub fn init(config: &Config, report_client: Arc<ReportClient>) -> Result<Self> {
        #[cfg(target_os = "macos")]
        #[allow(unused_variables)]
        let (system_manager, core_manager): (
            SystemManagerType,
            Arc<RwLock<CoreStateManager>>,
        ) = {
            let processor_info_data = MacOsSystem::read_cpuinfo(&config.machine.cpuinfo_path)?;
            let core_manager = Arc::new(RwLock::new(CoreStateManager::new(
                processor_info_data.processor_structure.clone(),
            )));

            (Box::new(MacOsSystem::init(&config.machine)?), core_manager)
        };

        // Use debug_assertions to allow linux logic compilation from mac development environments
        #[cfg(any(target_os = "linux", debug_assertions))]
        let (system_manager, core_manager): (
            SystemManagerType,
            Arc<RwLock<CoreStateManager>>,
        ) = {
            let processor_info_data = LinuxSystem::read_cpuinfo(&config.machine.cpuinfo_path)?;
            let core_manager = Arc::new(RwLock::new(CoreStateManager::new(
                processor_info_data.processor_structure.clone(),
            )));

            (
                Box::new(LinuxSystem::init(&config.machine, processor_info_data)?),
                core_manager,
            )
        };

        // Init nimby
        let nimby = if config.machine.nimby_mode {
            let nimby = Nimby::init(
                config.machine.nimby_idle_threshold,
                config.machine.nimby_display_file_path.clone(),
                config.machine.nimby_display_xauthority_path.clone(),
            );
            info!("NIMBY mode enabled and initialized");
            Arc::new(Some(nimby))
        } else {
            Arc::new(None)
        };

        Ok(Self {
            maching_config: config.machine.clone(),
            report_client,
            system_manager: Mutex::new(system_manager),
            running_frames_cache: RunningFrameCache::init(),
            last_host_state: Arc::new(Mutex::new(None)),
            interrupt: Mutex::new(None),
            reboot_when_idle: Mutex::new(false),
            nimby,
            nimby_state: RwLock::new(LockState::Open),
            core_manager,
        })
    }

    /// Starts an async loop that will update the machine state every `monitor_interval_seconds`.
    pub async fn start(&self, startup_flag: oneshot::Sender<()>) -> Result<()> {
        let report_client = self.report_client.clone();

        let host_state = {
            let system_lock = self.system_manager.lock().await;
            Self::inspect_host_state(&self.maching_config, &system_lock, false)?
        };

        let core_info = {
            let core_manager = self.core_manager.read().await;
            core_manager.get_core_info_report(self.maching_config.core_multiplier)
        };

        self.last_host_state
            .lock()
            .await
            .replace(host_state.clone());

        debug!("Sending start report: {:?}", host_state);
        report_client
            .send_start_up_report(host_state, core_info)
            .await?;

        // Notify caller that the machine state is ready
        let _ = startup_flag.send(());

        let (term_sender, mut term_receiver) = broadcast::channel::<()>(5);

        // Start nimby monitor
        self.start_nimby(term_receiver.resubscribe()).await;
        let mut interval = time::interval(self.maching_config.monitor_interval);

        let mut interrupt_lock = self.interrupt.lock().await;
        interrupt_lock.replace(term_sender);
        drop(interrupt_lock);

        let mut last_lock_state = LockState::Open;
        loop {
            select! {
                    message = term_receiver.recv() => {
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

                        if let Some(nimby) = &*self.nimby {
                            match (nimby.is_user_active(), last_lock_state) {
                                // Became locked
                                (true, LockState::Open) => {
                                    last_lock_state = LockState::NimbyLocked;

                                    // Update registered state
                                    let mut nimby_state = self.nimby_state.write().await;
                                    *nimby_state = last_lock_state;
                                    drop(nimby_state);

                                    info!("Host became nimby locked");
                                    self.lock_all_cores().await;
                                }
                                // Continues locked
                                (true, LockState::NimbyLocked) => {}
                                // Continues open
                                (false, LockState::Open) => {}
                                // Became unlocked
                                (false, LockState::NimbyLocked) => {
                                    last_lock_state = LockState::Open;

                                    // Update registered state
                                    let mut nimby_state = self.nimby_state.write().await;
                                    *nimby_state = last_lock_state;
                                    drop(nimby_state);

                                    info!("Host became nimby unlocked");
                                    self.unlock_all_cores().await;
                                }
                                // NoOp
                                _ => ()
                            }
                        }
                }

            }
        }
        Ok(())
    }

    async fn start_nimby(&self, term_receiver: Receiver<()>) {
        // Start nimby monitor
        let nimby_clone = Arc::clone(&self.nimby);
        let nimby_start_retry_interval = self.maching_config.nimby_start_retry_interval;
        if nimby_clone.as_ref().is_some() {
            tokio::spawn(async move {
                let mut interval = time::interval(nimby_start_retry_interval);
                loop {
                    let mut term_listener = term_receiver.resubscribe();
                    // Await for another chance to start nimby
                    interval.tick().await;
                    if let Some(nimby) = nimby_clone.as_ref() {
                        match nimby.start(&mut term_listener).await {
                            Ok(_) => break,
                            Err(err) => {
                                info!(
                                    "Nimby startup failed, retrying in {}s. {err}",
                                    nimby_start_retry_interval.as_secs()
                                );
                            }
                        }
                    }
                }
            });
        }
    }

    pub async fn interrupt(&self) {
        let mut lock = self.interrupt.lock().await;
        match lock.take() {
            Some(sender) => {
                if sender.send(()).is_err() {
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
                    running_frames.push((Arc::clone(running_frame), running_state));
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
        for (running_frame, running_state) in &running_frames {
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
                finished_frames.push(Arc::clone(running_frame));
                self.running_frames_cache.remove(&running_frame.frame_id);
            } else {
                // Proc finished but frame is waiting for the lock on `is_finished` to update the status
                // keep frame around for another round
                running_frame.mark_for_cache_removal();
            }
        }

        self.handle_finished_frames(finished_frames).await;

        // Sanitize dangling reservations
        // This mechanism is redundant as handle_finished_frames releases resources reserved to
        // finished frames. But leaking core reservations would lead to waste of resoures, so
        // having a safety check sounds reasonable even when reduntant.
        {
            let running_resources: Vec<Uuid> = running_frames
                .iter()
                .map(|(running_frame, _)| running_frame.request.resource_id())
                .collect();
            self.core_manager
                .write()
                .await
                .sanitize_reservations(&running_resources);
        }

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
                let frame_report = frame.clone_into_running_frame_info();
                info!("Sending frame complete report: {}", frame);

                if let Err(err) = self.release_cores(&frame.request.resource_id()).await {
                    warn!(
                        "Failed to release cores reserved by {}: {}",
                        frame.request.resource_id(),
                        err
                    );
                };

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
        nimby_locked: bool,
    ) -> Result<RenderHost> {
        let stats = system.collect_stats()?;
        let gpu_stats = system.collect_gpu_stats();

        Ok(RenderHost {
            name: stats.hostname,
            nimby_enabled: config.nimby_mode,
            nimby_locked,
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
            state: *system.hardware_state() as i32,
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

    /// Reserve CPU cores for a resource
    ///
    /// # Arguments
    ///
    /// * `request` - Either the number of cores to reserve (Left) or specific thread IDs to reserve (Right)
    /// * `resource_id` - Unique identifier for the resource requesting the cores
    ///
    /// # Returns
    ///
    /// A vector of core/thread IDs that were successfully reserved
    ///
    /// # Errors
    ///
    /// Returns `ReservationError` if the cores cannot be reserved (e.g., insufficient available cores)
    async fn reserve_cores(
        &self,
        request: Either<usize, Vec<u32>>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>, ReservationError>;

    /// Release CPU cores previously reserved by a resource
    ///
    /// # Arguments
    ///
    /// * `resource_id` - Unique identifier for the resource that previously reserved the cores
    ///
    /// # Returns
    ///
    /// Returns `Ok(())` if the cores were successfully released
    ///
    /// # Errors
    ///
    /// Returns `ReservationError` if the resource_id is not found or cores cannot be released
    async fn release_cores(&self, resource_id: &Uuid) -> Result<(), ReservationError>;

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

    async fn force_kill(&self, pids: &[u32]) -> Result<()>;

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
            .map(|hs| hs.state())
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
        request: Either<usize, Vec<u32>>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>, ReservationError> {
        let mut core_manager = self.core_manager.write().await;
        match request {
            Either::Left(num_cores) => core_manager.reserve_cores(num_cores, resource_id),
            #[allow(deprecated)]
            Either::Right(thread_ids) => core_manager.reserve_cores_by_id(thread_ids, resource_id),
        }
    }

    async fn release_cores(&self, resource_id: &Uuid) -> Result<(), ReservationError> {
        let mut core_manager = self.core_manager.write().await;
        core_manager.release_cores(resource_id).map(|_| ())
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

    async fn force_kill(&self, pids: &[u32]) -> Result<()> {
        let system = self.system_manager.lock().await;
        system.force_kill(pids)
    }

    async fn get_active_proc_lineage(&self, pid: u32) -> Option<Vec<u32>> {
        let system = self.system_manager.lock().await;
        system.get_proc_lineage(pid)
    }

    async fn lock_cores(&self, count: u32) -> u32 {
        let mut core_manager = self.core_manager.write().await;
        core_manager.lock_cores(count)
    }

    async fn lock_all_cores(&self) {
        let mut core_manager = self.core_manager.write().await;
        core_manager.lock_all_cores();
    }

    async fn unlock_cores(&self, count: u32) -> u32 {
        let mut core_manager = self.core_manager.write().await;
        core_manager.unlock_cores(count)
    }

    async fn unlock_all_cores(&self) {
        let mut core_manager = self.core_manager.write().await;
        core_manager.unlock_all_cores();
    }

    async fn reboot_if_idle(&self) -> Result<()> {
        // Prevent new frames from booking
        self.lock_all_cores().await;

        if !self.running_frames_cache.is_empty() {
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
        let render_host = {
            let system_manager = self.system_manager.lock().await;
            // If there are frames running update the list of procs on the machine
            if !self.running_frames_cache.is_empty() {
                system_manager.refresh_procs();
            }

            let nimby_state_lock = self.nimby_state.read().await;

            Self::inspect_host_state(
                &self.maching_config,
                &system_manager,
                *nimby_state_lock == LockState::NimbyLocked,
            )?
        }; // Scope ensures all mutex are released

        let core_state = {
            let core_manager = self.core_manager.read().await;
            core_manager.get_core_info_report(self.maching_config.core_multiplier)
        };

        // Store the last host_state on self
        let mut self_host_state_lock = self.last_host_state.lock().await;
        self_host_state_lock.replace(render_host.clone());
        drop(self_host_state_lock);

        self.monitor_running_frames().await?;

        Ok(HostReport {
            host: Some(render_host),
            frames: Arc::clone(&self.running_frames_cache).clone_to_running_frame_vec(),
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
