use std::{
    collections::{HashMap, HashSet},
    sync::{Arc, Mutex as SyncMutex},
};

use async_trait::async_trait;
use miette::{Diagnostic, IntoDiagnostic, Result};
use opencue_proto::{
    host::HardwareState,
    report::{CoreDetail, RenderHost},
};
use sysinfo::{Disks, System};
use thiserror::Error;
use tokio::{sync::Mutex, time};
use tracing::debug;

use crate::{
    config::config::{Config, MachineConfig},
    report_client::{ReportClient, ReportInterface},
};

use super::{linux::LinuxSystem, running_frame::RunningFrameCache};

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
    core_state: Arc<Mutex<Option<CoreDetail>>>,
    host_state: Arc<Mutex<Option<RenderHost>>>,
}

impl MachineMonitor {
    /// Initializes the object without starting the monitor loop
    /// Will gather the initial state of this machine
    pub fn init(
        config: &Config,
        report_client: Arc<ReportClient>,
        running_frames_cache: Arc<RunningFrameCache>,
        sysinfo: Arc<SyncMutex<System>>,
        diskinfo: Arc<SyncMutex<Disks>>,
    ) -> Result<Self> {
        let system_controller: SystemControllerType =
            Box::new(LinuxSystem::init(&config.machine, sysinfo, diskinfo)?);
        // TODO: identify which OS is running and initialize stats_collector accordingly
        Ok(Self {
            maching_config: config.machine.clone(),
            report_client,
            system_controller: Mutex::new(system_controller),
            running_frames_cache,
            core_state: Arc::new(Mutex::new(None)),
            host_state: Arc::new(Mutex::new(None)),
        })
    }

    /// Starts an async loop that will update the machine state every `monitor_interval_seconds`.
    pub async fn start(&self) -> Result<()> {
        let report_client = self.report_client.clone();

        let stats_collector_lock = self.system_controller.lock().await;
        let host_state = Self::inspect_host_state(&self.maching_config, &stats_collector_lock)?;
        drop(stats_collector_lock);

        self.host_state.lock().await.replace(host_state.clone());
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
            self.core_state
                .lock()
                .await
                .replace(initial_core_state.clone());
        }
        debug!("Sending start report: {:?}", host_state);
        report_client
            .send_start_up_report(host_state, initial_core_state)
            .await?;

        let mut interval = time::interval(time::Duration::from_secs(
            self.maching_config.monitor_interval_seconds,
        ));
        for _i in 0..5 {
            interval.tick().await;
            let stats_collector_lock = self.system_controller.lock().await;
            let host_state = Self::inspect_host_state(&self.maching_config, &stats_collector_lock)?;
            drop(stats_collector_lock);

            let core_state_guard = self.core_state.lock().await;
            let core_state = core_state_guard
                .as_ref()
                .expect("A state must be set at this point");

            debug!("Sending host report: {:?}", host_state);
            report_client
                .send_host_report(
                    host_state,
                    Arc::clone(&self.running_frames_cache).into_running_frame_vec(),
                    core_state.clone(),
                )
                .await?;
        }
        Ok(())
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
            cores_per_proc: (stats.num_sockets / stats.cores_per_proc) as i32,
            total_swap: stats.total_swap as i64,
            total_mem: stats.total_memory as i64,
            total_mcp: stats.total_temp_storage as i64,
            free_swap: stats.free_swap as i64,
            free_mem: stats.free_memory as i64,
            free_mcp: stats.free_temp_storage as i64,
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
    ///
    /// # Returns
    ///
    /// List of procs (Argument called cpu-list in the unix taskset cmd) reserved
    /// by this request
    async fn reserve_cpus(&self, num_cores: u32) -> Result<Vec<u32>>;

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

    async fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32>;

    async fn get_host_name(&self) -> String;
}

#[async_trait]
impl Machine for MachineMonitor {
    async fn hardware_state(&self) -> Option<HardwareState> {
        self.host_state
            .lock()
            .await
            .as_ref()
            .map(|hs| hs.state().clone())
    }

    async fn nimby_locked(&self) -> bool {
        self.host_state
            .lock()
            .await
            .as_ref()
            .map(|hs| hs.nimby_locked)
            .unwrap_or(false)
    }

    async fn reserve_cpus(&self, num_cores: u32) -> Result<Vec<u32>> {
        let mut stats_collector = self.system_controller.lock().await;
        stats_collector.reserve_cores(num_cores).into_diagnostic()
    }

    async fn reserve_gpus(&self, num_gpus: u32) -> Result<Vec<u32>> {
        todo!()
    }

    async fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32> {
        let stats_collector = self.system_controller.lock().await;
        stats_collector.create_user_if_unexisting(username, uid, gid)
    }

    async fn get_host_name(&self) -> String {
        let lock = self.host_state.lock().await;

        lock.as_ref()
            .map(|h| h.name.clone())
            .unwrap_or("noname".to_string())
    }
}

/// Represents attributes on a machine that should never change withour restarting the
/// entire servive
#[derive(Clone)]
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
    /// Amount of free memory on the machine
    pub free_memory: u64,
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
    fn reserve_cores(&mut self, count: u32) -> Result<Vec<u32>, ReservationError>;

    /// Release a core
    fn release_core(&mut self, core_id: &u32) -> Result<(), ReservationError>;

    /// Creates an user if it doesn't already exist
    fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32>;
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
    pub reserved_cores_by_physid: HashMap<u32, HashSet<u32>>,
    pub available_cores: u32,
}
