use std::{collections::HashMap, sync::Arc};

use miette::Result;
use opencue_proto::{
    host::HardwareState,
    report::{CoreDetail, RenderHost},
};
use tokio::{sync::Mutex, time};

use crate::{
    config::config::{Config, MachineConfig},
    report_client::{ReportClient, ReportInterface},
    running_frame::RunningFrameCache,
};

use super::linux_monitor::LinuxMachineStat;

type MachineStatT = Box<dyn MachineStat + Sync + Send>;

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
    stats_collector: MachineStatT,
    pub host_state: Arc<Mutex<RenderHost>>,
    pub core_state: Arc<Mutex<CoreDetail>>,
    pub running_frames_cache: Arc<RunningFrameCache>,
}

impl MachineMonitor {
    /// Initializes the object without starting the monitor loop
    /// Will gather the initial state of this machine
    pub fn init(
        config: &Config,
        report_client: Arc<ReportClient>,
        running_frames_cache: Arc<RunningFrameCache>,
    ) -> Result<Self> {
        let stats_collector: MachineStatT = Box::new(LinuxMachineStat::init(&config.machine)?);
        let host_state = Arc::new(Mutex::new(Self::inspect_host_state(
            &config.machine,
            &stats_collector,
        )?));
        // TODO: identify which OS is running and initialize stats_collector accordingly
        Ok(Self {
            maching_config: config.machine.clone(),
            report_client,
            stats_collector,
            host_state,
            core_state: Arc::new(Mutex::new(Self::init_core_state()?)),
            running_frames_cache,
        })
    }

    /// Starts an async loop that will update the machine state every `monitor_interval_seconds`.
    pub async fn start(&self) -> Result<()> {
        let report_client = self.report_client.clone();

        report_client
            .send_start_up_report(
                (*self.host_state).lock().await.clone(),
                self.core_state.lock().await.clone(),
            )
            .await?;

        let mut interval = time::interval(time::Duration::from_secs(
            self.maching_config.monitor_interval_seconds,
        ));
        for _i in 0..5 {
            interval.tick().await;
            self.refresh_state().await?;
            report_client
                .send_host_report(
                    self.host_state.lock().await.clone(),
                    Arc::clone(&self.running_frames_cache).into_running_frame_vec(),
                    self.core_state.lock().await.clone(),
                )
                .await?;
        }
        Ok(())
    }

    /// Update machine state objects
    async fn refresh_state(&self) -> Result<()> {
        let mut host_state_ref = self.host_state.lock().await;
        *host_state_ref = Self::inspect_host_state(&self.maching_config, &self.stats_collector)?;
        Ok(())
    }

    fn inspect_host_state(
        config: &MachineConfig,
        stats_collector: &MachineStatT,
    ) -> Result<RenderHost> {
        let static_stats = stats_collector.static_stats();
        let dynamic_stats = stats_collector.collect_dynamic_stats();
        let gpu_stats = stats_collector.collect_gpu_stats();

        Ok(RenderHost {
            name: static_stats.hostname,
            nimby_enabled: stats_collector.init_nimby()?,
            nimby_locked: false, // TODO: implement nimby lock
            facility: config.facility.clone(),
            num_procs: static_stats.num_procs as i32,
            cores_per_proc: (static_stats.num_sockets / static_stats.cores_per_proc) as i32,
            total_swap: static_stats.total_swap as i64,
            total_mem: static_stats.total_memory as i64,
            total_mcp: dynamic_stats.total_temp_storage as i64,
            free_swap: dynamic_stats.free_swap as i64,
            free_mem: dynamic_stats.free_memory as i64,
            free_mcp: dynamic_stats.free_temp_storage as i64,
            load: dynamic_stats.load as i32,
            boot_time: static_stats.boot_time as i32,
            tags: static_stats.tags,
            state: stats_collector.hardware_state().clone() as i32,
            attributes: stats_collector.attributes().clone(),
            num_gpus: gpu_stats.count as i32,
            free_gpu_mem: gpu_stats.free_memory as i64,
            total_gpu_mem: gpu_stats.total_memory as i64,
        })
    }

    fn init_core_state() -> Result<CoreDetail> {
        todo!()
    }
}

/// Represents attributes on a machine that should never change withour restarting the
/// entire servive
#[derive(Clone)]
pub struct MachineStaticInfo {
    pub hostname: String,
    /// Number of proc units (also known as virtual cores)
    pub num_procs: u32,
    pub total_memory: u64,
    pub total_swap: u64,
    /// Number of sockets (also know as physical cores)
    pub num_sockets: u32,
    pub cores_per_proc: u32,
    // Unlike the python counterpart, the multiplier is not automatically applied to total_procs
    pub hyperthreading_multiplier: u32,
    pub boot_time: u32,
    pub tags: Vec<String>,
}

pub struct MachineDynamicInfo {
    pub free_memory: u64,
    pub free_swap: u64,
    pub total_temp_storage: u64,
    pub free_temp_storage: u64,
    pub load: u32,
}

pub struct MachineGpuStats {
    count: u32,
    total_memory: u64,
    free_memory: u64,
    used_memory_by_unit: HashMap<u32, u64>,
}

pub trait MachineStat {
    /// Returns static information about this machine
    fn static_stats(&self) -> MachineStaticInfo;
    /// Collects live information about the status of this machine
    fn collect_dynamic_stats(&self) -> MachineDynamicInfo;
    /// Collects live information about the gpus on this machine
    fn collect_gpu_stats(&self) -> MachineGpuStats;
    fn hardware_state(&self) -> &HardwareState;
    fn attributes(&self) -> &HashMap<String, String>;
    fn init_nimby(&self) -> Result<bool>;
}
