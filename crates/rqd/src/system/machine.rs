use std::{collections::HashMap, sync::Arc};

use async_trait::async_trait;
use bytesize::KIB;
use miette::{IntoDiagnostic, Result, miette};
use opencue_proto::{
    host::HardwareState,
    report::{CoreDetail, RenderHost},
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

use crate::{
    config::config::{Config, MachineConfig},
    frame::{cache::RunningFrameCache, running_frame::RunningFrame},
    report::report_client::{ReportClient, ReportInterface},
};

use super::{
    manager::{ReservationError, SystemManagerType},
    unix::UnixSystem,
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
}

impl MachineMonitor {
    /// Initializes the object without starting the monitor loop
    /// Will gather the initial state of this machine
    pub fn init(
        config: &Config,
        report_client: Arc<ReportClient>,
        running_frames_cache: Arc<RunningFrameCache>,
    ) -> Result<Self> {
        let system_manager: SystemManagerType = Box::new(UnixSystem::init(&config.machine)?);
        // TODO: identify which OS is running and initialize system_manager accordingly
        Ok(Self {
            maching_config: config.machine.clone(),
            report_client,
            system_manager: Mutex::new(system_manager),
            running_frames_cache,
            core_state: Arc::new(Mutex::new(CoreDetail::default())),
            last_host_state: Arc::new(Mutex::new(None)),
            interrupt: Mutex::new(None),
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
        let total_cores = host_state.num_procs * self.maching_config.core_multiplier as i32;
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
                    self.update_procs().await;
                    self.collect_and_send_host_report().await?;
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

    async fn update_procs(&self) {
        let system_manager = self.system_manager.lock().await;
        system_manager.refresh_procs();
    }

    async fn collect_and_send_host_report(&self) -> Result<()> {
        let report_client = self.report_client.clone();
        let system_manager = self.system_manager.lock().await;
        let host_state = Self::inspect_host_state(&self.maching_config, &system_manager)?;
        drop(system_manager);
        // Store the last host_state on self
        let mut self_host_state_lock = self.last_host_state.lock().await;
        self_host_state_lock.replace(host_state.clone());
        drop(self_host_state_lock);

        let core_state = { self.core_state.lock().await.clone() };
        self.monitor_running_frames().await?;

        debug!("Sending host report: {:?}", host_state);
        report_client
            .send_host_report(
                host_state,
                Arc::clone(&self.running_frames_cache).into_running_frame_vec(),
                core_state,
            )
            .await?;
        Ok(())
    }

    async fn monitor_running_frames(&self) -> Result<()> {
        let system_monitor = self.system_manager.lock().await;
        let mut finished_frames: Vec<Arc<RunningFrame>> = Vec::new();

        self.running_frames_cache.retain(|_, running_frame| {
            // A frame that hasn't properly started will not have a pid
            if let Some(pid) = running_frame.pid() {
                if running_frame.is_finished() {
                    finished_frames.push(Arc::clone(running_frame));
                    false
                } else if let Some(proc_stats) = system_monitor
                    .collect_proc_stats(pid, running_frame.log_path.clone())
                    .unwrap_or_else(|err| {
                        warn!("Failed to collect proc_stats. {}", err);
                        None
                    })
                {
                    if let Ok(mut frame_stats) = running_frame.frame_stats.lock() {
                        if let Some(old_frame_stats) = frame_stats.as_mut() {
                            old_frame_stats.update(proc_stats);
                        } else {
                            *frame_stats = Some(proc_stats);
                        }
                    }
                    true
                } else {
                    warn!(
                        "Removing {} from the cache. Could not find proc {} for frame that was supposed to be running.",
                        running_frame.to_string(),
                        pid
                    );
                    false
                }
            } else {
                true
            }
        });
        self.handle_finished_frames(finished_frames).await;
        Ok(())
    }

    async fn handle_finished_frames(&self, finished_frames: Vec<Arc<RunningFrame>>) {
        let host_state_lock = self.last_host_state.lock().await;
        let host_state = host_state_lock.clone();
        // Avoid holding a lock while reporting back to cuebot
        drop(host_state_lock);

        if let Some(host_state) = host_state {
            for frame in finished_frames {
                if let (Some(finished_state), Some(frame_report)) =
                    (frame.get_finished_state(), frame.into_running_frame_info())
                {
                    let exit_signal = match finished_state.exit_signal {
                        Some(signal) => signal as u32,
                        None => 0,
                    };

                    // Release resources
                    if let Some(procs) = &frame.cpu_list {
                        self.release_cpus(procs).await;
                    } else {
                        self.release_cores(
                            frame.request.num_cores as u32 / self.maching_config.core_multiplier,
                        )
                        .await;
                    }

                    // Send complete report
                    if let Err(err) = self
                        .report_client
                        .send_frame_complete_report(
                            host_state.clone(),
                            frame_report,
                            finished_state.exit_code as u32,
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
                } else {
                    warn!("Invalid state on supposedly finished frame. {}", frame);
                }
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
            num_procs: stats.num_procs as i32,
            cores_per_proc: (stats.cores_per_proc * config.core_multiplier) as i32,
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
    /// List of procs (Argument called cpu-list in the unix taskset cmd) reserved
    /// by this request
    async fn reserve_cores(
        &self,
        num_cores: u32,
        resource_id: Uuid,
        with_affinity: bool,
    ) -> Result<Option<Vec<u32>>>;

    /// Reserve specific CPU cores by their IDs
    ///
    /// # Arguments
    ///
    /// * `cpu_list` - Vector of CPU core IDs to reserve
    /// * `resource_id` - Unique identifier for the resource that will use these cores
    ///
    /// # Returns
    ///
    /// Vector of successfully reserved CPU core IDs
    async fn reserve_cores_by_id(&self, cpu_list: &Vec<u32>, resource_id: Uuid)
    -> Result<Vec<u32>>;

    /// Release specific CPU cores by their IDs
    ///
    /// # Arguments
    ///
    /// * `procs` - Vector of CPU core IDs to release
    async fn release_cpus(&self, procs: &Vec<u32>);

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
        num_cores: u32,
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
            info!("Before: {:?}", *core_state);
            core_state
                .reserve(num_cores * self.maching_config.core_multiplier)
                .map_err(|err| miette!(err))?;
            info!("After: {:?}", *core_state);
        }
        cores_result
    }

    async fn reserve_cores_by_id(
        &self,
        cpu_list: &Vec<u32>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>> {
        // Reserve cores on the socket level
        let cores_result = {
            let mut system_lock = self.system_manager.lock().await;
            system_lock
                .reserve_cores_by_id(cpu_list, resource_id)
                .into_diagnostic()
        };

        // Record reservation to be reported to cuebot
        if let Ok(_) = &cores_result {
            let mut core_state = self.core_state.lock().await;
            core_state
                .reserve(cpu_list.len() as u32 * self.maching_config.core_multiplier)
                .map_err(|err| miette!(err))?;
        }
        cores_result
    }

    async fn release_cpus(&self, procs: &Vec<u32>) {
        {
            let mut system = self.system_manager.lock().await;
            for core_id in procs {
                if let Err(err) = system.release_core(core_id) {
                    match err {
                        ReservationError::NotFoundError(_) => {
                            warn!("Failed to release proc {core_id}. Reservation not found")
                        }
                        _ => {
                            error!("Failed to release proc {core_id}. Unexpected error")
                        }
                    }
                }
            }
        }
        // Record reservation to be reported to cuebot
        let mut core_state = self.core_state.lock().await;
        if let Err(err) = core_state
            .release(procs.len() as u32 * self.maching_config.core_multiplier)
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

    async fn reserve_gpus(&self, num_gpus: u32) -> Result<Vec<u32>> {
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
}
