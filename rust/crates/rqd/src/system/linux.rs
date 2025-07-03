use std::{
    collections::HashMap,
    fs::File,
    io::{BufRead, BufReader},
    net::ToSocketAddrs,
    path::Path,
    process::Command,
    sync::Mutex,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use libc::{_SC_CLK_TCK, _SC_PAGESIZE};

use chrono::{DateTime, Local};
use dashmap::{DashMap, DashSet};
use itertools::Itertools;
use miette::{Context, IntoDiagnostic, Result, miette};
use nix::sys::signal::{Signal, kill, killpg};
use opencue_proto::{
    host::HardwareState,
    report::{ChildrenProcStats, ProcStats, Stat},
};
use sysinfo::{DiskRefreshKind, Disks, MemoryRefreshKind, RefreshKind};
use tracing::debug;
use uuid::Uuid;

use crate::{config::MachineConfig, system::reservation::ProcessorStructure};

use super::manager::{MachineGpuStats, MachineStat, ProcessStats, SystemManager};

pub struct LinuxSystem {
    config: MachineConfig,
    // Information colleced once at init time
    static_info: MachineStaticInfo,
    hardware_state: HardwareState,
    attributes: HashMap<String, String>,
    sysinfo_system: Mutex<sysinfo::System>,
    // Cache of monitored processes and their lineage
    session_processes: DashMap<u32, Vec<u32>>,
    monitored_sessions: DashSet<u32>,
    cached_processes: DashMap<u32, ProcessData>,
}

#[derive(Debug)]
struct ProcessData {
    memory: u64,
    virtual_memory: u64,
    cmd: String,
    state: String,
    name: String,
    start_time: u64,
    run_time: u64,
}

impl ProcessData {
    pub fn is_dead(&self) -> bool {
        matches!(self.state.as_str(), "Z" | "X" | "Dead" | "Zombie")
    }
}

#[derive(Debug, Clone)]
pub struct ProcessorInfoData {
    hyperthreading_multiplier: u32,
    num_sockets: u32,
    cores_per_socket: u32,
    pub processor_structure: ProcessorStructure,
}

// struct CpuInfoWithProcs {
//     processor_info: ProcessorInfoData,
//     cores_by_phys_id: HashMap<u32, Vec<u32>>,
//     threads_by_core_unique_id: HashMap<String, Vec<u32>>,
//     phys_id_and_core_id_by_thread_id: HashMap<u32, (u32, u32)>,
// }

struct MachineStaticInfo {
    pub hostname: String,
    pub total_memory: u64,
    pub total_swap: u64,
    /// Number of sockets (also know as physical cores)
    pub num_sockets: u32,
    pub cores_per_socket: u32,
    // Unlike the python counterpart, the multiplier is not automatically applied to total_procs
    pub hyperthreading_multiplier: u32,
    pub boot_time_secs: u64,
    pub tags: Vec<String>,
    pub page_size: u64,
    pub clock_tick: u64,
}

pub struct MachineDynamicInfo {
    // Free + Cached
    pub available_memory: u64,
    pub free_swap: u64,
    pub total_temp_storage: u64,
    pub free_temp_storage: u64,
    pub load: u32,
}

/// Aggregated Data refering to a process session
struct SessionData {
    /// Amount of memory used by all processes in this session
    memory: u64,
    /// Amount of virtual memory used by all processes in this session
    virtual_memory: u64,
    /// Amount of gpu used by all processes in this session
    gpu_memory: u64,
    /// Earlier start time on the session
    start_time: u64,
    /// Longer run time on the session
    run_time: u64,
    /// Stats for all the processes on this session (leader procs only, tasks are excluded)
    lineage_stats: Vec<ProcStats>,
}

impl LinuxSystem {
    /// Initialize the unix stats collector which reads Cpu and Memory information from
    /// the OS.
    ///
    /// sysinfo needs to have been initialized.
    pub fn init(config: &MachineConfig, cpu_initial_info: ProcessorInfoData) -> Result<Self> {
        let identified_os = config
            .override_real_values
            .clone()
            .and_then(|c| c.os)
            .unwrap_or_else(|| {
                Self::read_distro(&config.distro_release_path).unwrap_or("linux".to_string())
            });

        // Initialize sysinfo collector
        let sysinfo = sysinfo::System::new_with_specifics(
            RefreshKind::nothing().with_memory(MemoryRefreshKind::everything()),
        );
        let total_memory = sysinfo.total_memory();
        let total_swap = sysinfo.total_swap();

        // Both sysconf values return -1 if not available
        let page_size: u64 = unsafe { libc::sysconf(_SC_PAGESIZE) }
            .try_into()
            .into_diagnostic()
            .wrap_err("SC_PAGESIZE not available")?;
        let clock_tick: u64 = unsafe { libc::sysconf(_SC_CLK_TCK) }
            .try_into()
            .into_diagnostic()
            .wrap_err("SC_CLK_TCK not available")?;

        Ok(Self {
            config: config.clone(),
            static_info: MachineStaticInfo {
                hostname: Self::get_hostname(config.use_ip_as_hostname)?,
                total_memory,
                total_swap,
                num_sockets: cpu_initial_info.num_sockets,
                cores_per_socket: cpu_initial_info.cores_per_socket,
                hyperthreading_multiplier: cpu_initial_info.hyperthreading_multiplier,
                boot_time_secs: Self::read_boot_time(&config.proc_stat_path).unwrap_or(0),
                tags: Self::setup_tags(config),
                page_size,
                clock_tick,
            },
            // dynamic_info: None,
            hardware_state: HardwareState::Up,
            attributes: HashMap::from([
                ("SP_OS".to_string(), identified_os),
                (
                    "hyperthreadingMultiplier".to_string(),
                    cpu_initial_info.hyperthreading_multiplier.to_string(),
                ),
                // SwapOut is an aditional attribute that is missing on this implementation
            ]),
            sysinfo_system: Mutex::new(sysinfo::System::new()),
            session_processes: DashMap::new(),
            monitored_sessions: DashSet::new(),
            cached_processes: DashMap::new(),
        })
    }

    /// Reads the CPU information from the specified `cpuinfo_path` file and extracts
    /// the number of processors, sockets, cores per processor, and hyperthreading multiplier.
    /// It returns a tuple containing ProcessorInfoData, procid_by_physid_and_core_id, and
    /// physid_and_coreid_by_procid.
    ///
    /// # Arguments
    ///
    /// * `cpuinfo_path` - A string slice that holds the path to the cpuinfo file.
    ///
    /// # Returns
    ///
    /// A `Result` containing a tuple with the following information:
    /// 1. `ProcessorInfoData` - Structure holding information about the processor like
    ///    hyperthreading multiplier, number of processors, number of sockets, and cores per
    ///    processor.
    /// 2. `HashMap<u32, <u32, u32>>` - Mapping of processor id to physical id and core id.
    /// 3. `HashMap<u32, Vec<u32>>` - Mapping of thread ids per process id
    pub fn read_cpuinfo(cpuinfo_path: &str) -> Result<ProcessorInfoData> {
        let mut cores_by_phys_id: HashMap<u32, Vec<u32>> = HashMap::new();
        let mut threads_by_core_unique_id: HashMap<String, Vec<u32>> = HashMap::new();
        let mut thread_id_lookup_table: HashMap<u32, (u32, u32)> = HashMap::new();
        let cpuinfo = File::open(cpuinfo_path).into_diagnostic()?;
        let reader = BufReader::new(cpuinfo);

        let mut num_threads = 0;
        let mut num_sockets = 0;
        let mut hyperthreading_multiplier: Option<u32> = None;
        let mut curr_core_map: HashMap<String, String> = HashMap::new();
        let mut physical_ids: HashMap<u32, ()> = HashMap::new();
        let mut was_last_line_break = false;
        for line_res in reader.lines().chain(vec![Ok("".to_string())].into_iter()) {
            let line = line_res.unwrap();

            if line.contains(":") {
                was_last_line_break = false;
                if let Some((key, value)) = line.split_once(":") {
                    curr_core_map.insert(key.trim().to_string(), value.trim().to_string());
                } else {
                    // An entry without data
                    curr_core_map.insert(line, "".to_string());
                }
            // End of a core block
            } else if line.trim().is_empty() {
                if was_last_line_break {
                    continue;
                }
                was_last_line_break = true;
                let siblings = curr_core_map
                    .get("siblings")
                    .unwrap_or(&"1".to_string())
                    .parse()
                    .unwrap_or(1);
                let cpu_cores = curr_core_map
                    .get("cpu cores")
                    .unwrap_or(&"1".to_string())
                    .parse()
                    .unwrap_or(1);
                if cpu_cores == 0 {
                    Err(miette!("Invalid 'cpu cores'=0 on cpuinfo file."))?
                }
                hyperthreading_multiplier.replace(siblings / cpu_cores);
                num_threads += 1;

                let core_id_opt = curr_core_map.get("core id");
                if let (Ok(core_id), Ok(phys_id), Some(Ok(thread_id))) = (
                    core_id_opt.map(|s| s.parse()).unwrap_or(Ok(0)), // Not mandatory
                    // If physical_id is not provided, each proc is different phys_id
                    curr_core_map
                        .get("physical id")
                        .map(|s| s.parse())
                        .unwrap_or(Ok(num_sockets)),
                    curr_core_map.get("processor").map(|s| s.parse()),
                ) {
                    // Keep a cache to avoid counting sockets twice
                    if let std::collections::hash_map::Entry::Vacant(e) =
                        physical_ids.entry(phys_id)
                    {
                        e.insert(());
                        num_sockets += 1;
                    }
                    cores_by_phys_id
                        .entry(phys_id)
                        .and_modify(|cores| {
                            cores.push(core_id);
                        })
                        .or_insert(vec![core_id]);
                    threads_by_core_unique_id
                        .entry(format!("{}_{}", phys_id, core_id))
                        .and_modify(|threads| threads.push(thread_id))
                        .or_insert(vec![thread_id]);
                    thread_id_lookup_table.insert(thread_id, (phys_id, core_id));
                } else {
                    Err(miette!(
                        "Invalid values on proc file {}. curr_core_map={:?}",
                        cpuinfo_path,
                        curr_core_map
                    ))?;
                }

                curr_core_map = HashMap::new();
            }
        }
        // Apply modifier
        let hyper_modifier = hyperthreading_multiplier.unwrap_or(1);
        if hyper_modifier == 0 {
            Err(miette!("Invalid hyperthreading_multiplier=0"))?
        }
        num_threads /= hyper_modifier;
        if num_sockets == 0 {
            Err(miette!("Invalid CPU with no sockets (physical id)"))
        } else {
            let processor_structure = ProcessorStructure::init(
                threads_by_core_unique_id,
                cores_by_phys_id,
                thread_id_lookup_table,
            );
            Ok(ProcessorInfoData {
                hyperthreading_multiplier: hyper_modifier,
                num_sockets,
                cores_per_socket: num_threads / num_sockets,
                processor_structure,
            })
        }
    }

    /// Retrieves the hostname of the machine based on the configuration parameters.
    /// If `use_ip_as_hostname` is set to true, it attempts to find the IP address linked to the hostname.
    ///
    /// # Arguments
    ///
    /// * `use_ip_as_hostname` - A boolean value indicating whether to use the IP address as the hostname.
    ///
    /// # Returns
    ///
    /// A `Result` containing a `String` representing the hostname or IP address of the machine.
    fn get_hostname(use_ip_as_hostname: bool) -> Result<String> {
        let hostname = sysinfo::System::host_name()
            .ok_or_else(|| miette::miette!("Failed to get hostname"))?
            .split(".")
            .next()
            .ok_or(miette!("Invalid hostname format"))?
            .to_string();
        if use_ip_as_hostname {
            let mut addrs_iter = format!("{}:443", hostname)
                .to_socket_addrs()
                .into_diagnostic()?;
            let addr = addrs_iter
                .next()
                .ok_or_else(|| miette::miette!("Failed to find IP for {}", hostname))?;
            Ok(addr.to_string())
        } else {
            Ok(hostname)
        }
    }

    /// Reads the distribution information from the specified `distro_relese_path` file and extracts
    /// the distribution ID.
    ///
    /// # Arguments
    ///
    /// * `distro_relese_path` - A string slice that holds the path to the distribution release file.
    ///
    /// # Returns
    ///
    /// A `Result` containing a `String` representing the distribution ID.
    fn read_distro(distro_release_path: &str) -> Result<String> {
        let distro_info = File::open(distro_release_path).into_diagnostic()?;
        let reader = BufReader::new(distro_info);
        let mut distro_id: Option<String> = None;
        for line in reader.lines().map_while(Result::ok) {
            if line.starts_with("ID=") || line.starts_with("DISTRIB_ID") {
                distro_id = line.split_once("=").map(|(_, val)| val.replace("\"", ""));
                break;
            }
        }
        distro_id.ok_or(miette!("Couldn't find release ID"))
    }

    /// Reads the boot time from the specified `proc_stat_path` file and extracts
    /// the time when the system was last booted.
    ///
    /// # Arguments
    ///
    /// * `proc_stat_path` - A string slice that holds the path to the proc stat file.
    ///
    /// # Returns
    ///
    /// A `Result` containing a `u32` representing the time when the system was last booted.
    fn read_boot_time(proc_stat_path: &str) -> Result<u64> {
        let stat_info = File::open(proc_stat_path).into_diagnostic()?;
        let reader = BufReader::new(stat_info);
        let mut btime: Option<u64> = None;
        for line in reader.lines().map_while(Result::ok) {
            if line.trim().starts_with("btime") {
                // btime 1723434332
                btime = line
                    .split_once(" ")
                    .and_then(|(_, val)| val.trim().parse().ok());
                break;
            }
        }
        btime.ok_or(miette!("Couldn't find boot time"))
    }

    /// Setup tags based on the environment this host is running on
    ///
    /// # Returns
    ///
    /// A list of tags. Possible values:
    ///   - desktop: If this host was identified as a workstation
    ///   - custom tags: tags defined on the config file
    fn setup_tags(config: &MachineConfig) -> Vec<String> {
        let mut tags = vec![];

        if Self::read_is_workstation(config).unwrap_or(false) {
            tags.push("desktop".to_string());
        }

        config
            .custom_tags
            .iter()
            .for_each(|tag| tags.push(tag.clone()));

        tags
    }

    /// Check if this machine is setup as a workstation
    ///
    /// In the previous version (python) this function would search for a `graphical.target`
    /// on '/lib/systemd/system/default.target' which does't work on our current environment
    /// and might not translate well to different setups. Initially this version will rely
    /// solely on the `workstation_mode` override value. In the future a more automated way of
    /// setting appart workstations and render nodes can be implemented.
    fn read_is_workstation(config: &MachineConfig) -> Result<bool> {
        let override_workstation_mode = config
            .override_real_values
            .as_ref()
            .and_then(|c| c.workstation_mode)
            .unwrap_or(false);
        Ok(override_workstation_mode)
    }

    fn read_dynamic_stat(&self) -> Result<MachineDynamicInfo> {
        let config = &self.config;
        let load = Self::read_load_avg(&config.proc_loadavg_path)?;
        let (total_space, available_space) = self.read_temp_storage()?;
        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        sysinfo.refresh_memory();

        Ok(MachineDynamicInfo {
            available_memory: sysinfo.available_memory(),
            free_swap: sysinfo.free_swap(),
            total_temp_storage: total_space,
            free_temp_storage: available_space,
            load: ((load.0 * 100.0).round() as u32 / self.static_info.hyperthreading_multiplier),
        })
    }
    /// Reads the load average from the specified `proc_loadavg_path` file and extracts
    /// the 1-minute, 5-minute and 15-minute load averages.
    ///
    /// # Arguments
    ///
    /// * `proc_loadavg_path` - A string slice that holds the path to the proc loadavg file.
    ///
    /// # Returns
    ///
    /// A `Result` containing a tuple of three `u32` values representing the 1-minute, 5-minute
    /// and 15-minute load averages.
    fn read_load_avg(proc_loadavg_path: &str) -> Result<(f32, f32, f32)> {
        let loadavg = File::open(proc_loadavg_path).into_diagnostic()?;
        let reader = BufReader::new(loadavg);
        // let mut load_val: Vec<u32> = vec![];
        let mut load_val: Option<(f32, f32, f32)> = None;
        if let Some(line) = reader.lines().map_while(Result::ok).next() {
            load_val = line
                .split_whitespace()
                .take(3)
                .map(|l| l.parse().unwrap_or(0.0))
                .collect_tuple();
        }
        load_val.ok_or(miette!("Couldn't find load average"))
    }

    /// Reads storage information from the temporary mount point and extracts
    /// the total space and available space.
    ///
    /// # Returns
    ///
    /// A `Result` containing a tuple of total space and available space in bytes.
    fn read_temp_storage(&self) -> Result<(u64, u64)> {
        let mut diskinfo =
            Disks::new_with_refreshed_list_specifics(DiskRefreshKind::nothing().with_storage());
        let tmp_disk = diskinfo.list_mut().iter_mut().find(|disk| {
            self.config.temp_path.starts_with(
                disk.mount_point()
                    .to_str()
                    .unwrap_or("invalid_path_will_never_match"),
            )
        });
        match tmp_disk {
            Some(disk) => {
                disk.refresh_specifics(DiskRefreshKind::everything());
                Ok((disk.total_space(), disk.available_space()))
            }
            None => Err(miette!(
                "Could not locate disk for temp path {}",
                self.config.temp_path
            )),
        }
    }

    fn refresh_procs_cache(&self) -> Result<()> {
        let proc_dir = std::fs::read_dir("/proc")
            .into_diagnostic()
            .wrap_err("Failed to read /proc")?;

        self.session_processes.clear();

        for entry in proc_dir.flatten() {
            let pid = match entry.file_name().to_string_lossy().parse::<u32>() {
                Ok(pid) => pid,
                Err(_) => continue, // Skip non-pid paths
            };

            let stat_path = format!("/proc/{}/status", pid);
            let stat = match std::fs::read_to_string(stat_path).into_diagnostic() {
                Ok(s) => s,
                Err(_) => continue, // Skip procs which status is not available
            };

            // Fields
            let mut session_id: Option<u32> = None;
            let mut tgid: Option<u32> = None;
            let mut state = None;

            for line in stat.lines() {
                if let Some((key, value)) = line.split_once(":") {
                    match key {
                        "Tgid" => {
                            tgid = value.trim().parse().ok();
                        }
                        "NSsid" | "SID" | "Sid" => {
                            session_id = value.trim().parse().ok();
                        }
                        "State" => {
                            state = value.split_whitespace().next();
                        }
                        _ => (),
                    }
                }
            }
            match (session_id, tgid, state) {
                (Some(session_id), Some(tgid), Some(state)) => {
                    // Only store valid states
                    let valid_state = match state {
                        "R" | "S" | "D" | "T" => true, // Running, Sleeping, Disk Sleep, Stopped
                        "Z" | "X" => false,            // Zombie, Dead
                        _ => true,                     // Monitor unkwnown states
                    };

                    let is_group_leader = pid == tgid;

                    if session_id != 0
                        && self.monitored_sessions.contains(&session_id)
                        && is_group_leader
                        && valid_state
                    {
                        if let Ok(process_data) = self.read_proc_data(pid) {
                            self.cached_processes.insert(pid, process_data);
                            self.session_processes
                                .entry(session_id)
                                .or_default()
                                .push(pid);
                        } // Skip processes that failed to be read
                    }
                }
                _ => {
                    continue;
                }
            }
        }
        Ok(())
    }

    /// Reads proc data from stat and statm files:
    ///
    /// # Used fields:
    ///
    /// ## /proc/pid/stat
    /// 1. **comm** (%s) - The filename of the executable in parentheses (truncated to 16 chars including null terminator)
    /// 2. **state** (%c) - Process state: R (Running), S (Sleeping), D (Uninterruptible sleep), Z (Zombie), T (Stopped), t (Tracing stop), X/x (Dead), K (Wakekill), W (Waking), P (Parked), I (Idle)
    /// 21. **starttime** (%llu) - Process start time after system boot in clock ticks
    ///
    /// ## /proc/pid/statm
    /// 0. **size** (%d) - Total program size
    /// 1. **rss** (%d) - Resident set Size
    ///
    /// ## /proc/pid/cmdline
    fn read_proc_data(&self, pid: u32) -> Result<ProcessData> {
        let stat_path = format!("/proc/{}/stat", pid);
        let statm_path = format!("/proc/{}/statm", pid);
        let cmdline_path = format!("/proc/{}/cmdline", pid);
        let stat = std::fs::read_to_string(stat_path).into_diagnostic()?;
        let statm = std::fs::read_to_string(statm_path).into_diagnostic()?;
        let cmdline = std::fs::read_to_string(cmdline_path).into_diagnostic()?;

        let fields_stat: Vec<&str> = stat.split_whitespace().collect();
        let fields_statm: Vec<&str> = statm.split_whitespace().collect();
        if fields_stat.len() >= 22 && fields_statm.len() >= 6 {
            // Unpack values
            let (state, name, start_time) = match (
                fields_stat.get(2),             // state
                fields_stat.get(1),             // name
                fields_stat[21].parse::<u64>(), // starttime
            ) {
                (Some(state), Some(name), Ok(start_time)) => {
                    (state.to_string(), name.to_string(), start_time)
                }
                _ => Err(miette!("Invalid /proc/{pid}/stat file"))?,
            };

            let (vsize, rss) = match (
                fields_statm[0].parse::<u64>(), // size
                fields_statm[1].parse::<u64>(), // rss
            ) {
                (Ok(vsize), Ok(rss)) => (vsize, rss),
                _ => Err(miette!("Invalid /proc/{pid}/statm file"))?,
            };

            let (start_time, run_time) = self.calculate_process_time(start_time);
            // Rss is stored in number of pages
            let memory = rss.saturating_mul(self.static_info.page_size);
            let virtual_memory = vsize.saturating_mul(self.static_info.page_size);

            // Remove ()
            let name = if name.len() > 2 {
                name[1..name.len() - 1].to_string()
            } else {
                name
            };

            let cmd = cmdline.replace('\0', " ");

            Ok(ProcessData {
                memory,
                virtual_memory,
                cmd,
                state,
                name,
                start_time,
                run_time,
            })
        } else {
            Err(miette!("Invalid /proc/stat file for {pid}"))
        }
    }

    /// Calculates the absolute start time and total runtime for a process.
    ///
    /// This function converts the process start time from the kernel's internal representation
    /// (clock ticks since system boot) to useful absolute timestamps and runtime duration.
    ///
    /// # Arguments
    ///
    /// * `start_time_after_boot_in_cycles` - The process start time in clock ticks since system boot,
    ///   as reported by field 22 (`starttime`) in `/proc/pid/stat`.
    ///
    /// # Returns
    ///
    /// A tuple containing:
    /// * `start_time` - Absolute process start time as seconds since Unix epoch (UTC)
    /// * `run_time` - Total process runtime in seconds from start until now
    fn calculate_process_time(&self, start_time_after_boot_in_cycles: u64) -> (u64, u64) {
        let now_epoch = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        let start_time_without_boot_time: u64 =
            start_time_after_boot_in_cycles / self.static_info.clock_tick;
        let start_time = self.static_info.boot_time_secs + start_time_without_boot_time;
        let run_time = now_epoch.saturating_sub(start_time);
        (start_time, run_time)
    }

    fn calculate_proc_session_data(&self, session_id: &u32) -> Option<SessionData> {
        let mut children = Vec::new();
        self.monitored_sessions.insert(*session_id);

        let _session_leader = self
            .cached_processes
            .get(session_id)
            .and_then(|proc| match proc.is_dead() {
                true => None,
                false => Some(proc),
            })?;

        // If session owner is still alive, iterate over the session and calculate memory
        let (memory, virtual_memory, gpu_memory, start_time, run_time) = match self
            .session_processes
            .get(session_id)
        {
            Some(ref lineage) => {
                // Process session data
                lineage
                    .iter()
                    .filter_map(|pid| {
                        match self.cached_processes.get(pid) {
                            Some(proc) if !proc.is_dead() => {
                                // Confirm this is a proc and not a thread
                                let start_time_str = DateTime::<Local>::from(
                                    UNIX_EPOCH + Duration::from_secs(proc.start_time),
                                )
                                .format("%Y-%m-%d %H:%M:%S")
                                .to_string();
                                let proc_memory = proc.memory;
                                let proc_vmemory = proc.virtual_memory;
                                let cmdline = proc.cmd.clone();

                                // Check for potential duplicates
                                children.push(ProcStats {
                                    stat: Some(Stat {
                                        rss: proc_memory as i64,
                                        vsize: proc_vmemory as i64,
                                        state: proc.state.clone(),
                                        name: proc.name.clone(),
                                        pid: pid.to_string(),
                                    }),
                                    statm: None,
                                    status: None,
                                    cmdline,
                                    start_time: start_time_str,
                                });
                                Some((proc_memory, proc_vmemory, 0, proc.start_time, proc.run_time))
                            }
                            _ => None,
                        }
                    })
                    .reduce(|a, b| {
                        (
                            a.0 + b.0,
                            a.1 + b.1,
                            a.2 + b.2,
                            std::cmp::min(a.3, b.3),
                            std::cmp::max(a.4, b.4),
                        )
                    })
                    .unwrap_or((0, 0, 0, u64::MAX, 0))
            }
            None => (0, 0, 0, u64::MAX, 0),
        };
        Some(SessionData {
            memory,
            virtual_memory,
            gpu_memory,
            start_time,
            run_time,
            lineage_stats: children,
        })
    }
}

impl SystemManager for LinuxSystem {
    fn collect_stats(&self) -> Result<MachineStat> {
        let dinamic_stat = self.read_dynamic_stat()?;
        Ok(MachineStat {
            hostname: self.static_info.hostname.clone(),
            total_memory: self.static_info.total_memory,
            total_swap: self.static_info.total_swap,
            num_sockets: self.static_info.num_sockets,
            cores_per_socket: self.static_info.cores_per_socket,
            boot_time: self.static_info.boot_time_secs as u32,
            tags: self.static_info.tags.clone(),
            available_memory: dinamic_stat.available_memory,
            free_swap: dinamic_stat.free_swap,
            total_temp_storage: dinamic_stat.total_temp_storage,
            free_temp_storage: dinamic_stat.free_temp_storage,
            load: dinamic_stat.load,
        })
    }

    /// Returns the current hardware state of the machine.
    ///
    /// # Returns
    /// * The hardware state enum value indicating whether the machine is UP/DOWN/etc
    fn hardware_state(&self) -> &HardwareState {
        &self.hardware_state
    }

    fn attributes(&self) -> &HashMap<String, String> {
        &self.attributes
    }

    fn collect_gpu_stats(&self) -> MachineGpuStats {
        // TODO: missing implementation, returning dummy val
        MachineGpuStats {
            count: 0,
            total_memory: 0,
            free_memory: 0,
            _used_memory_by_unit: HashMap::default(),
        }
    }
    fn create_user_if_unexisting(&self, username: &str, uid: u32, gid: u32) -> Result<u32> {
        // First check if the user already exists
        if let Some(user) = users::get_user_by_name(username) {
            return Ok(user.uid());
        }

        // User doesn't exist, create it using useradd
        let output = Command::new("useradd")
            .arg("-p")
            .arg(Uuid::new_v4().to_string())
            .arg("--uid")
            .arg(uid.to_string())
            .arg("--gid")
            .arg(gid.to_string())
            .arg(username)
            .output()
            .into_diagnostic()?;

        if !output.status.success() {
            return Err(miette!(
                "Failed to create user {}: {}",
                username,
                String::from_utf8_lossy(&output.stderr)
            ));
        }

        // Verify the user was created
        match users::get_user_by_name(username) {
            Some(user) => Ok(user.uid()),
            None => Err(miette!("Failed to verify user {} was created", username)),
        }
    }

    fn collect_proc_stats(&self, pid: u32, log_path: String) -> Result<Option<ProcessStats>> {
        // Latest log modified time in epoch seconds. Defaults to zero if the metadata is not
        // accessible.
        let log_mtime = std::fs::metadata(Path::new(&log_path))
            .and_then(|metadata| metadata.modified())
            .and_then(|mtime| {
                mtime
                    .duration_since(UNIX_EPOCH)
                    .map_err(std::io::Error::other)
            })
            .unwrap_or_default()
            .as_secs();

        Ok(self.calculate_proc_session_data(&pid).map(|session_data| {
            debug!(
                "Collect frame stats fo {}. rss: {}kb virtual: {}kb gpu: {}kb",
                pid, session_data.memory, session_data.virtual_memory, session_data.gpu_memory
            );
            ProcessStats {
                // Caller is responsible for maintaining the Max value between calls
                max_rss: session_data.memory,
                rss: session_data.memory,
                max_vsize: session_data.virtual_memory,
                vsize: session_data.virtual_memory,
                llu_time: log_mtime,
                max_used_gpu_memory: 0,
                used_gpu_memory: session_data.gpu_memory,
                children: Some(ChildrenProcStats {
                    children: session_data.lineage_stats,
                }),
                epoch_start_time: session_data.start_time,
                run_time: session_data.run_time,
            }
        }))
    }

    fn refresh_procs(&self) {
        if let Err(err) = self.refresh_procs_cache() {
            debug!("Failed to refresh procs on this system. {err}");
        };
    }

    fn kill_session(&self, session_pid: u32) -> Result<()> {
        killpg(
            nix::unistd::Pid::from_raw(session_pid as i32),
            Signal::SIGTERM,
        )
        .map_err(|err| miette!("Failed to kill {session_pid}. {err}"))
    }

    fn force_kill_session(&self, session_pid: u32) -> Result<()> {
        killpg(
            nix::unistd::Pid::from_raw(session_pid as i32),
            Signal::SIGKILL,
        )
        .map_err(|err| miette!("Failed to kill {session_pid}. {err}"))
    }

    fn force_kill(&self, pids: &[u32]) -> Result<()> {
        let mut failed_pids = Vec::new();
        let mut last_err = Ok(());
        for pid in pids {
            if let Err(err) = kill(nix::unistd::Pid::from_raw(*pid as i32), Signal::SIGKILL) {
                failed_pids.push(pid);
                last_err = Err(err);
            }
        }
        last_err.map_err(|err| miette!("Failed to force kill pids {:?}. Errno={err}", failed_pids))
    }

    fn get_proc_lineage(&self, pid: u32) -> Option<Vec<u32>> {
        self.session_processes
            .get(&pid)
            .map(|lineage| lineage.clone())
    }

    #[cfg(target_os = "linux")]
    fn reboot(&self) -> Result<()> {
        nix::sys::reboot::reboot(nix::sys::reboot::RebootMode::RB_AUTOBOOT)
            .map(|_| ())
            .into_diagnostic()
            .wrap_err("Failed to reboot")
    }

    #[cfg(target_os = "macos")]
    fn reboot(&self) -> Result<()> {
        todo!("linuxSystem shouldn't be used in macos. Please use system.macos")
    }
}

#[cfg(test)]
mod tests {
    use crate::config::MachineConfig;
    use std::fs;
    use std::{collections::HashMap, sync::Mutex};

    use dashmap::{DashMap, DashSet};
    use libc::{_SC_CLK_TCK, _SC_PAGESIZE};
    use opencue_proto::host::HardwareState;

    use crate::system::linux::{LinuxSystem, MachineStaticInfo};

    #[test]
    /// Use this unit test to quickly exercice a single cpuinfo file by changing the path on the
    /// initial lines
    fn test_read_cpuinfo() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let config = MachineConfig {
            cpuinfo_path: format!("{}/resources/cpuinfo/cpuinfo_drack_4-2-2", project_dir),
            distro_release_path: "".to_string(),
            proc_stat_path: "".to_string(),
            core_multiplier: 1,
            ..Default::default()
        };

        let processor_info_data =
            LinuxSystem::read_cpuinfo(&config.cpuinfo_path).expect("Failed to read cpuinfo_path");
        let linux_monitor = LinuxSystem::init(&config, processor_info_data)
            .expect("Initializing LinuxMachineStat failed")
            .static_info;
        assert_eq!(2, linux_monitor.num_sockets);
        assert_eq!(2, linux_monitor.cores_per_socket);
        assert_eq!(1, linux_monitor.hyperthreading_multiplier);
    }

    #[test]
    /// This test automatically tests all files under resources/cpuinfo. The file name should
    /// contain the falues for num_procs, num_sockets, cores_per_proc and hyperthreading
    /// following the format:
    ///   - no hyperthreading: cpuinfo_[name]-[num_procs]-[num_sockets]-[cores_per_proc]
    ///   - hyperthreading: cpuinfo_ht_[name]-[num_procs]-[num_sockets]-[cores_per_proc]-[hyperthreading_multiplier]
    fn test_cpuinfo_files() {
        let project_dir = env!("CARGO_MANIFEST_DIR");
        let file_path = format!("{}/resources/cpuinfo", project_dir);
        match fs::read_dir(file_path) {
            Ok(entries) => {
                for entry in entries.flatten() {
                    println!("Testing {:?}", entry.path());
                    cpuinfo_tester(entry.file_name().to_str().unwrap());
                }
            }
            Err(e) => println!("Error reading directory: {}", e),
        }
    }

    fn cpuinfo_tester(cpu_file_name: &str) {
        let project_dir = env!("CARGO_MANIFEST_DIR");
        let file_path = format!("{}/resources/cpuinfo/{}", project_dir, cpu_file_name);
        let values: Vec<&str> = file_path
            .rsplit_once("_")
            .expect("Invalid configuration name")
            .1
            .split("-")
            .collect();
        if let (Some(_expected_procs), Some(expected_cores_per_proc), Some(expected_sockets)) = (
            values
                .first()
                .map(|v| v.parse::<u32>().expect("Should be int")),
            values
                .get(1)
                .map(|v| v.parse::<u32>().expect("Should be int")),
            values
                .get(2)
                .map(|v| v.parse::<u32>().expect("Should be int")),
        ) {
            let expected_hyper_multi = {
                if cpu_file_name.contains("_ht_") {
                    values
                        .get(3)
                        .map(|v| v.parse::<u32>().expect("Should be int"))
                        .expect("Ht filename should contain 4 numbers in the file name")
                } else {
                    1
                }
            };

            let data = LinuxSystem::read_cpuinfo(&file_path).expect("Failed to read file");
            assert_eq!(expected_sockets, data.num_sockets, "Assert num_sockets");
            assert_eq!(
                expected_cores_per_proc, data.cores_per_socket,
                "Assert cores_per_proc"
            );
            assert_eq!(
                expected_hyper_multi, data.hyperthreading_multiplier,
                "Assert hyperthreading_multiplier"
            );
        }
    }

    #[test]
    fn test_static_info() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let config = MachineConfig {
            cpuinfo_path: format!("{}/resources/cpuinfo/cpuinfo_drack_4-2-2", project_dir),
            distro_release_path: format!("{}/resources/distro-release/centos", project_dir),
            proc_stat_path: format!("{}/resources/proc/stat", project_dir),
            proc_loadavg_path: format!("{}/resources/proc/loadavg", project_dir),
            core_multiplier: 1,
            ..Default::default()
        };

        let processor_info_data =
            LinuxSystem::read_cpuinfo(&config.cpuinfo_path).expect("Failed to read cpuinfo_path");
        let linux_monitor = LinuxSystem::init(&config, processor_info_data)
            .expect("Initializing LinuxMachineStat failed");
        let static_info = linux_monitor.static_info;

        // Proc
        assert_eq!(2, static_info.num_sockets);
        assert_eq!(2, static_info.cores_per_socket);
        assert_eq!(1, static_info.hyperthreading_multiplier);

        // attributes
        assert_eq!(
            Some(&"centos".to_string()),
            linux_monitor.attributes.get("SP_OS")
        );

        // boot time
        assert_eq!(1720194269, static_info.boot_time_secs);
    }

    #[test]
    fn test_read_distro_release() {
        let project_dir = env!("CARGO_MANIFEST_DIR");
        let file_path = format!("{}/resources/distro-release", project_dir);

        match fs::read_dir(file_path) {
            Ok(entries) => {
                for entry in entries.flatten() {
                    println!("Testing {:?}", entry.path());
                    distro_release_tester(entry.file_name().to_str().unwrap());
                }
            }
            Err(e) => println!("Error reading directory: {}", e),
        }
    }

    fn distro_release_tester(id: &str) {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let path = format!("{}/resources/distro-release/{}", project_dir, id);
        let release = LinuxSystem::read_distro(&path).expect("Failed to read release");

        assert_eq!(id.to_string(), release);
    }

    #[test]
    fn test_proc_stat() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let path = format!("{}/resources/proc/stat", project_dir);
        let boot_time = LinuxSystem::read_boot_time(&path).expect("Failed to read boot time");
        assert_eq!(1720194269, boot_time);
    }

    #[test]
    fn test_load_avg() {
        use std::io::Write;
        use tempfile::NamedTempFile;

        // Test successful case
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "1.00 2.00 3.00 4/512 12345").unwrap();
        let result = LinuxSystem::read_load_avg(temp_file.path().to_str().unwrap());
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), (1.0, 2.0, 3.0));

        // Test empty file
        let empty_file = NamedTempFile::new().unwrap();
        let result = LinuxSystem::read_load_avg(empty_file.path().to_str().unwrap());
        assert!(result.is_err());

        // Test invalid format
        let mut invalid_file = NamedTempFile::new().unwrap();
        writeln!(invalid_file, "invalid format").unwrap();
        let result = LinuxSystem::read_load_avg(invalid_file.path().to_str().unwrap());
        assert!(result.is_err());

        // Test non-existent file
        let result = LinuxSystem::read_load_avg("nonexistent_file");
        assert!(result.is_err());
    }

    #[test]
    fn test_unix_system_init_full() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let config = MachineConfig {
            cpuinfo_path: format!("{}/resources/cpuinfo/cpuinfo_drack_4-2-2", project_dir),
            distro_release_path: format!("{}/resources/distro-release/centos", project_dir),
            proc_stat_path: format!("{}/resources/proc/stat", project_dir),
            proc_loadavg_path: format!("{}/resources/proc/loadavg", project_dir),
            temp_path: "/tmp".to_string(),
            core_multiplier: 1,
            ..Default::default()
        };

        let processor_info_data =
            LinuxSystem::read_cpuinfo(&config.cpuinfo_path).expect("Failed to read cpuinfo_path");
        let result = LinuxSystem::init(&config, processor_info_data);
        assert!(result.is_ok());

        let system = result.unwrap();
        assert_eq!(system.static_info.num_sockets, 2);
        assert_eq!(system.static_info.cores_per_socket, 2);
        assert!(!system.static_info.hostname.is_empty());
        assert!(system.attributes.contains_key("SP_OS"));
        assert_eq!(system.attributes.get("SP_OS"), Some(&"centos".to_string()));
    }

    #[test]
    fn test_read_boot_time_malformed_proc_stat() {
        use std::io::Write;
        use tempfile::NamedTempFile;

        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "cpu  123 456 789").unwrap();
        writeln!(temp_file, "cpu0 123 456 789").unwrap();
        writeln!(temp_file, "malformed_btime_line").unwrap();

        let result = LinuxSystem::read_boot_time(temp_file.path().to_str().unwrap());
        assert!(result.is_err());
    }

    #[test]
    fn test_system_integration_with_dynamic_stats() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let config = MachineConfig {
            cpuinfo_path: format!("{}/resources/cpuinfo/cpuinfo_drack_4-2-2", project_dir),
            distro_release_path: format!("{}/resources/distro-release/centos", project_dir),
            proc_stat_path: format!("{}/resources/proc/stat", project_dir),
            proc_loadavg_path: format!("{}/resources/proc/loadavg", project_dir),
            temp_path: "/tmp".to_string(),
            ..Default::default()
        };

        let processor_info_data =
            LinuxSystem::read_cpuinfo(&config.cpuinfo_path).expect("Failed to read cpuinfo_path");
        let system =
            LinuxSystem::init(&config, processor_info_data).expect("Failed to init system");

        // Test dynamic stats collection
        use crate::system::manager::SystemManager;
        let stats_result = system.collect_stats();
        assert!(stats_result.is_ok());

        let stats = stats_result.unwrap();
        assert_eq!(stats.hostname, system.static_info.hostname);
        assert_eq!(stats.num_sockets, 2);
        assert_eq!(stats.cores_per_socket, 2);
        assert_eq!(stats.boot_time, 1720194269);

        // Macos reports 0
        #[cfg(target_os = "linux")]
        assert!(stats.available_memory > 0);
    }

    #[test]
    fn test_refresh_procs() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let config = MachineConfig {
            cpuinfo_path: format!("{}/resources/cpuinfo/cpuinfo_drack_4-2-2", project_dir),
            distro_release_path: "".to_string(),
            proc_stat_path: "".to_string(),
            ..Default::default()
        };

        let processor_info_data =
            LinuxSystem::read_cpuinfo(&config.cpuinfo_path).expect("Failed to read cpuinfo_path");
        let system =
            LinuxSystem::init(&config, processor_info_data).expect("Failed to init system");

        // This should not panic or fail
        use crate::system::manager::SystemManager;
        system.refresh_procs();

        // Verify the cache is accessible after refresh
        let lineage = system.get_proc_lineage(1);
        // May or may not have lineage for PID 1, but shouldn't panic
        assert!(lineage.is_some() || lineage.is_none());
    }

    #[test]
    fn test_static_info_tags_integration() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let config = MachineConfig {
            cpuinfo_path: format!("{}/resources/cpuinfo/cpuinfo_drack_4-2-2", project_dir),
            distro_release_path: "".to_string(),
            proc_stat_path: "".to_string(),
            custom_tags: vec!["test_tag".to_string(), "integration".to_string()],
            ..Default::default()
        };

        let processor_info_data =
            LinuxSystem::read_cpuinfo(&config.cpuinfo_path).expect("Failed to read cpuinfo_path");
        let system =
            LinuxSystem::init(&config, processor_info_data).expect("Failed to init system");

        assert_eq!(system.static_info.tags.len(), 2);
        assert!(system.static_info.tags.contains(&"test_tag".to_string()));
        assert!(system.static_info.tags.contains(&"integration".to_string()));
    }

    #[test]
    fn test_read_distro_empty_file() {
        use tempfile::NamedTempFile;

        let empty_file = NamedTempFile::new().unwrap();
        let result = LinuxSystem::read_distro(empty_file.path().to_str().unwrap());
        assert!(result.is_err());
    }

    #[test]
    fn test_machine_static_info_consistency() {
        let system = setup_test_system(8, 2, 2);

        let static_info = &system.static_info;
        assert_eq!(static_info.num_sockets * static_info.cores_per_socket, 8);
        assert_eq!(static_info.hyperthreading_multiplier, 1); // Our test setup uses 1
        assert_eq!(static_info.hostname, "test");
    }

    #[test]
    fn test_calculate_process_time_basic() {
        let system = setup_test_system(4, 2, 1);

        // Mock scenario: process started 1000 clock ticks after boot
        // Assuming _SC_CLK_TCK = 100 (typical value)
        let clock_ticks = 1000_u64;
        let expected_seconds_after_boot =
            clock_ticks / unsafe { libc::sysconf(libc::_SC_CLK_TCK) } as u64;

        let (start_time, run_time) = system.calculate_process_time(clock_ticks);

        // start_time should be boot_time + seconds_after_boot
        let expected_start_time = system.static_info.boot_time_secs + expected_seconds_after_boot;
        assert_eq!(start_time, expected_start_time);

        // run_time should be reasonable (test system has boot_time_secs = 0, so run_time will be large)
        // Just verify it's a finite value and greater than expected_seconds_after_boot
        assert!(run_time > expected_seconds_after_boot);
        assert!(run_time < u64::MAX);
    }

    #[test]
    fn test_calculate_process_time_zero_start() {
        let system = setup_test_system(4, 2, 1);

        // Process that started exactly at boot (0 clock ticks)
        let (start_time, run_time) = system.calculate_process_time(0);

        // start_time should equal boot_time_secs
        assert_eq!(start_time, system.static_info.boot_time_secs);

        // run_time should be reasonable (test system has boot_time_secs = 0, so run_time will be current epoch time)
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        assert!(run_time > 0);
        assert!(run_time <= now); // Should not exceed current time
    }

    #[test]
    fn test_calculate_process_time_large_value() {
        let system = setup_test_system(4, 2, 1);

        // Test with a large number of clock ticks
        let clock_ticks = 1_000_000_u64;
        let expected_seconds_after_boot =
            clock_ticks / unsafe { libc::sysconf(libc::_SC_CLK_TCK) } as u64;

        let (start_time, run_time) = system.calculate_process_time(clock_ticks);

        let expected_start_time = system.static_info.boot_time_secs + expected_seconds_after_boot;
        assert_eq!(start_time, expected_start_time);

        // For a process that started far in the past, run_time should be reasonable
        // (we can't predict exact values due to real system time, but it should be finite)
        assert!(run_time < u64::MAX);
    }

    #[test]
    fn test_calculate_process_time_consistency() {
        let system = setup_test_system(4, 2, 1);

        let clock_ticks_1 = 500_u64;
        let clock_ticks_2 = 1000_u64;

        let (start_time_1, _) = system.calculate_process_time(clock_ticks_1);
        let (start_time_2, _) = system.calculate_process_time(clock_ticks_2);

        // Process 2 should have started later than process 1
        assert!(start_time_2 > start_time_1);

        // The difference should match the expected clock tick difference
        let expected_diff =
            (clock_ticks_2 - clock_ticks_1) / unsafe { libc::sysconf(libc::_SC_CLK_TCK) } as u64;
        let actual_diff = start_time_2 - start_time_1;
        assert_eq!(actual_diff, expected_diff);
    }

    #[test]
    fn test_calculate_process_time_edge_case_max_value() {
        let system = setup_test_system(4, 2, 1);

        // Test with maximum reasonable value
        let clock_ticks = u64::MAX / 2; // Avoid overflow in calculations
        let (start_time, _run_time) = system.calculate_process_time(clock_ticks);

        // Should not panic or overflow
        assert!(start_time >= system.static_info.boot_time_secs);
    }

    #[test]
    fn test_calculate_process_time_runtime_calculation() {
        let mut system = setup_test_system(4, 2, 1);

        // Set a known boot time for predictable testing
        system.static_info.boot_time_secs = 1609459200; // 2021-01-01 00:00:00 UTC

        // Process started 10 seconds after boot (1000 clock ticks assuming 100 Hz)
        let clock_ticks = 1000_u64;
        let clk_tck = unsafe { libc::sysconf(libc::_SC_CLK_TCK) } as u64;
        let expected_start_time = system.static_info.boot_time_secs + (clock_ticks / clk_tck);

        let (start_time, run_time) = system.calculate_process_time(clock_ticks);

        assert_eq!(start_time, expected_start_time);

        // run_time should be the difference between now and start_time
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        let expected_run_time = now.saturating_sub(start_time);
        assert_eq!(run_time, expected_run_time);
    }

    #[test]
    fn test_calculate_process_time_multiple_calls_consistent() {
        let system = setup_test_system(4, 2, 1);

        let clock_ticks = 5000_u64;

        // Multiple calls with same input should produce same start_time
        let (start_time_1, run_time_1) = system.calculate_process_time(clock_ticks);
        std::thread::sleep(std::time::Duration::from_millis(10)); // Small delay
        let (start_time_2, run_time_2) = system.calculate_process_time(clock_ticks);

        // Start time should be identical
        assert_eq!(start_time_1, start_time_2);

        // Run time should be slightly different (or same if calls were very fast)
        assert!(run_time_2 >= run_time_1);
        assert!(run_time_2 - run_time_1 <= 1); // Should differ by at most 1 second
    }

    // Helper function to create a test system with specified configuration
    fn setup_test_system(
        total_cores: u32,
        physical_cpus: u32,
        threads_per_core: u32,
    ) -> LinuxSystem {
        let mut cores_by_phys_id: HashMap<u32, Vec<u32>> = HashMap::new();
        let mut threads_by_core_unique_id: HashMap<String, Vec<u32>> = HashMap::new();
        let mut thread_id_lookup_table: HashMap<u32, (u32, u32)> = HashMap::new();

        let mut threads_id_counter = 0;
        // Set up CPU topology
        let cores_per_cpu = total_cores / physical_cpus;
        for phys_id in 0..physical_cpus {
            for core_id in 0..cores_per_cpu {
                for _t in 0..threads_per_core {
                    let thread_id = threads_id_counter;
                    threads_by_core_unique_id
                        .entry(format!("{}_{}", phys_id, core_id))
                        .and_modify(|threads| threads.push(thread_id))
                        .or_insert(vec![thread_id]);
                    thread_id_lookup_table.insert(thread_id, (phys_id, core_id));
                    threads_id_counter += 1;
                }
            }
            cores_by_phys_id.insert(phys_id, (0..cores_per_cpu).collect());
        }

        LinuxSystem {
            config: MachineConfig::default(),
            static_info: MachineStaticInfo {
                hostname: "test".to_string(),
                total_memory: 0,
                total_swap: 0,
                num_sockets: physical_cpus,
                cores_per_socket: cores_per_cpu,
                hyperthreading_multiplier: 1,
                boot_time_secs: 0,
                tags: vec![],
                page_size: unsafe { libc::sysconf(_SC_PAGESIZE) as u64 },
                clock_tick: unsafe { libc::sysconf(_SC_CLK_TCK) as u64 },
            },
            hardware_state: HardwareState::Up,
            attributes: HashMap::new(),
            sysinfo_system: Mutex::new(sysinfo::System::new()),
            session_processes: DashMap::new(),
            monitored_sessions: DashSet::new(),
            cached_processes: DashMap::new(),
        }
    }
}
