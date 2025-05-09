use std::{
    collections::{HashMap, HashSet},
    time::Instant,
};

use miette::{Diagnostic, Result};
use opencue_proto::{host::HardwareState, report::ChildrenProcStats};
use thiserror::Error;
use tracing::error;
use uuid::Uuid;

use serde::{Deserialize, Serialize};

pub type SystemManagerType = Box<dyn SystemManager + Sync + Send>;

pub trait SystemManager {
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
    fn refresh_procs(&self);

    /// Kill a session using the session pid
    fn kill_session(&self, session_pid: u32) -> Result<()>;

    /// Force kill a session using the session pid
    fn force_kill_session(&self, session_pid: u32) -> Result<()>;

    /// Force kill a list of pids
    fn force_kill(&self, pids: &Vec<u32>) -> Result<()>;

    /// Returns the list of active children, and none if the pid itself is not active
    fn get_proc_lineage(&self, pid: u32) -> Option<Vec<u32>>;

    /// Request a system reboot
    fn reboot(&self) -> Result<()>;
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
    /// Total runtime of the longer lasting process in the lineage
    pub run_time: u64,
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
            run_time: 0,
        }
    }
}

impl ProcessStats {
    pub fn update(&mut self, new: Self) {
        *self = ProcessStats {
            max_rss: std::cmp::max(new.max_rss, self.max_rss),
            max_vsize: std::cmp::max(new.max_vsize, self.max_vsize),
            max_used_gpu_memory: std::cmp::max(new.max_used_gpu_memory, self.max_used_gpu_memory),
            run_time: std::cmp::max(new.run_time, self.run_time),
            ..new
        };
    }
}
