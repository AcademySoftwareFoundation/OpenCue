use std::{
    collections::{HashMap, HashSet},
    sync::Arc,
    time::Instant,
};

use async_trait::async_trait;
use bytesize::KIB;
use miette::{Diagnostic, IntoDiagnostic, Result, miette};
use opencue_proto::{
    host::HardwareState,
    report::{ChildrenProcStats, CoreDetail, RenderHost},
};
use thiserror::Error;
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
    report_client::{ReportClient, ReportInterface},
};
use serde::{Deserialize, Serialize};

use super::unix::UnixSystem;

type SystemControllerType = Box<dyn SystemController + Sync + Send>;

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
    pub system_controller: Mutex<SystemControllerType>,
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
        let system_controller: SystemControllerType = Box::new(UnixSystem::init(&config.machine)?);
        // TODO: identify which OS is running and initialize stats_collector accordingly
        Ok(Self {
            maching_config: config.machine.clone(),
            report_client,
            system_controller: Mutex::new(system_controller),
            running_frames_cache,
            core_state: Arc::new(Mutex::new(CoreDetail::default())),
            last_host_state: Arc::new(Mutex::new(None)),
            interrupt: Mutex::new(None),
        })
    }

    /// Starts an async loop that will update the machine state every `monitor_interval_seconds`.
    pub async fn start(&self) -> Result<()> {
        let report_client = self.report_client.clone();

        let stats_collector_lock = self.system_controller.lock().await;
        let host_state = Self::inspect_host_state(&self.maching_config, &stats_collector_lock)?;
        drop(stats_collector_lock);

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

        let mut interval = time::interval(time::Duration::from_secs(
            self.maching_config.monitor_interval_seconds,
        ));

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
        let system_controller = self.system_controller.lock().await;
        system_controller.update_procs(self.running_frames_cache.pids());
    }

    async fn collect_and_send_host_report(&self) -> Result<()> {
        let report_client = self.report_client.clone();
        let system_controller = self.system_controller.lock().await;
        let host_state = Self::inspect_host_state(&self.maching_config, &system_controller)?;
        drop(system_controller);
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
        let system_monitor = self.system_controller.lock().await;
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
        stats_collector: &SystemControllerType,
    ) -> Result<RenderHost> {
        let stats = stats_collector.collect_stats()?;
        let gpu_stats = stats_collector.collect_gpu_stats();

        Ok(RenderHost {
            name: stats.hostname,
            nimby_enabled: stats_collector.init_nimby()?,
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
            state: stats_collector.hardware_state().clone() as i32,
            attributes: stats_collector.attributes().clone(),
            num_gpus: gpu_stats.count as i32,
            free_gpu_mem: gpu_stats.free_memory as i64,
            total_gpu_mem: gpu_stats.total_memory as i64,
        })
    }
}

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
            let mut stats_collector = self.system_controller.lock().await;
            stats_collector
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
            let mut stats_collector = self.system_controller.lock().await;
            stats_collector
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
            let mut stats_collector = self.system_controller.lock().await;
            for core_id in procs {
                if let Err(err) = stats_collector.release_core(core_id) {
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
        let stats_collector = self.system_controller.lock().await;
        stats_collector.create_user_if_unexisting(username, uid, gid)
    }

    async fn get_host_name(&self) -> String {
        let lock = self.last_host_state.lock().await;

        lock.as_ref()
            .map(|h| h.name.clone())
            .unwrap_or("noname".to_string())
    }
}

/// Represents attributes on a machine that should never change withour restarting the
/// entire servive
#[derive(Clone, Debug)]
pub struct MachineStat {
    /// Machine name
    pub hostname: String,
    /// Total number of processing units (also known as virtual cores)
    pub num_procs: u32,
    /// Total amount of memory on the machine
    pub total_memory: u64,
    /// Total amount of swap space on the machine
    pub total_swap: u64,
    /// Total number of physical cores (also known as sockets)
    pub num_sockets: u32,
    /// Number of cores per processor unit
    pub cores_per_proc: u32,
    /// Multiplier value for hyper-threading, does not apply to total_procs unlike in python version
    pub hyperthreading_multiplier: u32,
    /// Timestamp for when the machine was booted up
    pub boot_time: u32,
    /// List of tags associated with this machine
    pub tags: Vec<String>,
    /// Amount of available memory on the machine. For Linux/Macos Free + Cached
    pub available_memory: u64,
    /// Amount of free swap space on the machine
    pub free_swap: u64,
    /// Total temporary storage available on the machine
    pub total_temp_storage: u64,
    /// Amount of free temporary storage on the machine
    pub free_temp_storage: u64,
    /// Current load on the machine
    pub load: u32,
}

pub struct MachineGpuStats {
    /// Count of GPUs
    pub count: u32,
    /// Total memory of all GPUs
    pub total_memory: u64,
    /// Available free memory of all GPUs
    pub free_memory: u64,
    /// Used memory by unit of each GPU, where the key in the HashMap is the unit ID, and the value is the used memory
    pub used_memory_by_unit: HashMap<u32, u64>,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct ProcessStats {
    /// Maximum resident set size (KB) - maximum amount of physical memory used.
    pub max_rss: u64,
    /// Current resident set size (KB) - amount of physical memory currently in use.
    pub rss: u64,
    /// Maximum virtual memory size (KB) - maximum amount of virtual memory used.
    pub max_vsize: u64,
    /// Current virtual memory size (KB) - amount of virtual memory currently in use.
    pub vsize: u64,
    /// Last time the log was updated
    pub llu_time: u64,
    /// Maximum GPU memory usage (KB).
    pub max_used_gpu_memory: u64,
    /// Current GPU memory usage (KB).
    pub used_gpu_memory: u64,
    /// Additional data about the running frame's child processes.
    pub children: Option<ChildrenProcStats>,
    /// Unix timestamp denoting the start time of the frame process.
    pub epoch_start_time: u64,
}

impl Default for ProcessStats {
    fn default() -> Self {
        ProcessStats {
            max_rss: 0,
            rss: 0,
            max_vsize: 0,
            vsize: 0,
            llu_time: 0,
            max_used_gpu_memory: 0,
            used_gpu_memory: 0,
            children: None,
            epoch_start_time: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_else(|_| std::time::Duration::from_secs(0))
                .as_secs(),
        }
    }
}

/// Get the max between two u64s
fn max_u64(left: u64, right: u64) -> u64 {
    (left > right).then(|| left).unwrap_or(right)
}

impl ProcessStats {
    fn update(&mut self, new: Self) {
        *self = ProcessStats {
            max_rss: max_u64(new.max_rss, self.max_rss),
            max_vsize: max_u64(new.max_vsize, self.max_vsize),
            max_used_gpu_memory: max_u64(new.max_used_gpu_memory, self.max_used_gpu_memory),
            ..new
        };
    }
}

pub trait SystemController {
    /// Collects information about the status of this machine
    fn collect_stats(&self) -> Result<MachineStat>;

    /// Collects information about the gpus on this machine
    fn collect_gpu_stats(&self) -> MachineGpuStats;

    /// Up, Down, Rebooting...
    fn hardware_state(&self) -> &HardwareState;

    /// List of attributes collected from the machine. Eg. SP_OS
    fn attributes(&self) -> &HashMap<String, String>;

    /// Init NotInMyBackyard logic
    fn init_nimby(&self) -> Result<bool>;

    /// Returns a map of cores per socket that are not reserved
    fn cpu_stat(&self) -> CpuStat;

    /// Reserver a number of cores.
    ///
    /// # Returns:
    ///
    /// * Vector of core ids
    fn reserve_cores(&mut self, count: u32, frame_id: Uuid) -> Result<Vec<u32>, ReservationError>;

    /// Reserver specific cores by id.
    ///
    /// # Returns:
    ///
    /// * Vector of core ids
    fn reserve_cores_by_id(
        &mut self,
        cpu_list: &Vec<u32>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>, ReservationError>;

    /// Release a core
    fn release_core(&mut self, core_id: &u32) -> Result<(), ReservationError>;

    /// Creates an user if it doesn't already exist
    fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32>;

    /// Collects stats of a process
    fn collect_proc_stats(&self, pid: u32, log_path: String) -> Result<Option<ProcessStats>>;

    /// Update info about procs currently active
    fn update_procs(&self, pids: Vec<u32>);
}

#[derive(Debug, Clone, Diagnostic, Error)]
pub enum ReservationError {
    #[error("No resources available to be reserved")]
    NotEnoughResourcesAvailable,

    #[error("Could not find resource with provided key: {0}")]
    NotFoundError(u32),
}

#[derive(Debug, Clone)]
pub struct CpuStat {
    /// List of cores currently reserved
    pub reserved_cores_by_physid: HashMap<u32, CoreReservation>,
    pub available_cores: u32,
}

#[derive(Debug, Clone)]
pub struct CoreReservation {
    pub reserved_cores: HashSet<u32>,
    pub reserver_id: Uuid,
    pub start_time: Instant,
}

impl CoreReservation {
    pub fn new(reserver_id: Uuid) -> Self {
        CoreReservation {
            reserved_cores: HashSet::new(),
            reserver_id,
            start_time: Instant::now(),
        }
    }

    pub fn iter(&self) -> std::collections::hash_set::Iter<'_, u32> {
        self.reserved_cores.iter()
    }

    pub fn insert(&mut self, core_id: u32) -> bool {
        self.reserved_cores.insert(core_id)
    }

    pub fn remove(&mut self, core_id: &u32) -> bool {
        self.reserved_cores.remove(core_id)
    }
}
