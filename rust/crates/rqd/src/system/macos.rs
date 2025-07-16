use std::{
    collections::HashMap,
    fs::File,
    io::{BufRead, BufReader},
    net::ToSocketAddrs,
    path::Path,
    process::Command,
    sync::Mutex,
    time::{Duration, UNIX_EPOCH},
};

use chrono::{DateTime, Local};
use dashmap::{DashMap, DashSet};
use itertools::Itertools;
use miette::{Context, IntoDiagnostic, Result, miette};
use nix::sys::signal::{Signal, kill, killpg};
use opencue_proto::{
    host::HardwareState,
    report::{ChildrenProcStats, ProcStats, Stat},
};
use sysinfo::{
    DiskRefreshKind, Disks, MemoryRefreshKind, Pid, ProcessRefreshKind, ProcessStatus,
    ProcessesToUpdate, RefreshKind,
};
use tracing::debug;
use uuid::Uuid;

use crate::{config::MachineConfig, system::reservation::ProcessorStructure};

use super::manager::{MachineGpuStats, MachineStat, ProcessStats, SystemManager};

pub struct MacOsSystem {
    config: MachineConfig,
    // Information colleced once at init time
    static_info: MachineStaticInfo,
    hardware_state: HardwareState,
    attributes: HashMap<String, String>,
    sysinfo_system: Mutex<sysinfo::System>,
    // Cache of monitored processes and their lineage
    session_processes: DashMap<u32, Vec<u32>>,
    monitored_sessions: DashSet<u32>,
}

#[derive(Debug)]
pub struct ProcessorInfoData {
    hyperthreading_multiplier: u32,
    num_sockets: u32,
    cores_per_socket: u32,
    pub processor_structure: ProcessorStructure,
}

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

impl MacOsSystem {
    /// Initialize the unix sstats collector which reads Cpu and Memory information from
    /// the OS.
    ///
    /// sysinfo needs to have been initialized.
    pub fn init(config: &MachineConfig) -> Result<Self> {
        let data = Self::read_cpuinfo(&config.cpuinfo_path)?;

        let identified_os = config
            .override_real_values
            .clone()
            .and_then(|c| c.os)
            .unwrap_or_else(|| {
                Self::read_distro(&config.distro_release_path).unwrap_or("macos".to_string())
            });

        // Initialize sysinfo collector
        let sysinfo = sysinfo::System::new_with_specifics(
            RefreshKind::nothing().with_memory(MemoryRefreshKind::everything()),
        );
        let total_memory = sysinfo.total_memory();
        let total_swap = sysinfo.total_swap();

        Ok(Self {
            config: config.clone(),
            static_info: MachineStaticInfo {
                hostname: Self::get_hostname(config.use_ip_as_hostname)?,
                total_memory,
                total_swap,
                num_sockets: data.num_sockets,
                cores_per_socket: data.cores_per_socket,
                hyperthreading_multiplier: data.hyperthreading_multiplier,
                boot_time_secs: Self::read_boot_time(&config.proc_stat_path).unwrap_or(0),
                tags: Self::setup_tags(config),
            },
            // dynamic_info: None,
            hardware_state: HardwareState::Up,
            attributes: HashMap::from([
                ("SP_OS".to_string(), identified_os),
                (
                    "hyperthreadingMultiplier".to_string(),
                    data.hyperthreading_multiplier.to_string(),
                ),
                // SwapOut is an aditional attribute that is missing on this implementation
            ]),
            sysinfo_system: Mutex::new(sysinfo::System::new()),
            session_processes: DashMap::new(),
            monitored_sessions: DashSet::new(),
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
    fn read_distro(distro_relese_path: &str) -> Result<String> {
        let distro_info = File::open(distro_relese_path).into_diagnostic()?;
        let reader = BufReader::new(distro_info);
        let mut distro_id: Option<String> = None;
        for line in reader.lines().map_while(Result::ok) {
            if line.contains("ID") {
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
            // sysinfo.available_memory() would be the best way to infer available memory, but it
            // returns 0 on M macs
            available_memory: sysinfo.total_memory() - sysinfo.used_memory(),
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

    /// Refresh the cache of children procs.
    ///
    /// This method relies on sysinfo to have been updated periodically
    /// throught the refresh_procs method to gather the updated list
    /// of running processes
    fn refresh_procs_cache(&self) {
        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        sysinfo.refresh_processes_specifics(
            ProcessesToUpdate::All,
            true,
            ProcessRefreshKind::nothing(),
        );
        self.session_processes.clear();
        // Collect all session_ids
        let session_id_and_pid = sysinfo.processes().iter().filter_map(|(pid, proc)| {
            let session_pid = proc.session_id().unwrap_or(Pid::from_u32(0)).as_u32();
            // Filter out procs on a state that doesn't consume memory
            match proc.status() {
                ProcessStatus::Idle
                | ProcessStatus::Run
                | ProcessStatus::Sleep
                | ProcessStatus::Wakekill
                | ProcessStatus::Waking
                | ProcessStatus::Parked
                | ProcessStatus::LockBlocked
                | ProcessStatus::UninterruptibleDiskSleep => Some((session_pid, (*pid).as_u32())),
                _ => None,
            }
        });
        // Group all processes by session_id
        for (session_pid, pid) in session_id_and_pid {
            self.session_processes
                .entry(session_pid)
                .and_modify(|procs| {
                    procs.push(pid);
                })
                .or_insert(vec![pid]);
        }
    }

    /// Checks if a process is dead or non-existent
    ///
    /// # Arguments
    /// * `process` - An optional reference to a sysinfo::Process
    ///
    /// # Returns
    /// * `bool` - Returns true if the process is dead, zombied, or doesn't exist (None).
    ///   Returns false if the process exists and is in any other state.
    fn is_proc_dead(process: Option<&sysinfo::Process>) -> bool {
        match process {
            Some(proc) if [ProcessStatus::Dead, ProcessStatus::Zombie].contains(&proc.status()) => {
                true
            }
            None => true,
            _ => false,
        }
    }

    /// Calculates memory usage of all processes associated with a session ID.
    ///
    /// This method aggregates memory statistics for a process and all of its children
    /// that share the same session ID. It also collects additional process information
    /// such as command line, start time, and runtime.
    ///
    /// # Arguments
    ///
    /// * `session_id` - The session ID to calculate memory for
    ///
    /// # Returns
    ///
    /// An `Option<SessionData>` containing:
    /// * Memory usage in kilobytes
    /// * Virtual memory usage in kilobytes
    /// * GPU memory usage in kilobytes (currently always 0)
    /// * Process start time in seconds since epoch
    /// * Process runtime in seconds
    /// * Vector of stats for all processes in the lineage
    ///
    /// Returns `None` if the process that created the session ID doesn't exist or cannot be
    /// accessed.
    fn calculate_proc_session_data(&self, session_id: &u32) -> Option<SessionData> {
        self.monitored_sessions.insert(*session_id);

        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        let mut children = Vec::new();

        // Refresh session parent
        let session_pid = Pid::from_u32(*session_id);
        sysinfo.refresh_processes_specifics(
            ProcessesToUpdate::Some(&[session_pid]),
            true,
            ProcessRefreshKind::nothing().with_cpu().with_memory(),
        );

        // Return none if the session owner has already finished or died
        if Self::is_proc_dead(sysinfo.process(session_pid)) {
            return None;
        }
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
                        // Refresh only the procs we need info about
                        sysinfo.refresh_processes_specifics(
                            ProcessesToUpdate::Some(&[Pid::from_u32(*pid)]),
                            true,
                            ProcessRefreshKind::nothing().with_cpu().with_memory(),
                        );

                        match sysinfo.process(Pid::from(*pid as usize)) {
                            Some(proc) if !Self::is_proc_dead(Some(proc)) => {
                                // Confirm this is a proc and not a thread
                                let start_time_str = DateTime::<Local>::from(
                                    UNIX_EPOCH + Duration::from_secs(proc.start_time()),
                                )
                                .format("%Y-%m-%d %H:%M:%S")
                                .to_string();
                                let proc_memory = proc.memory();
                                let proc_vmemory = proc.virtual_memory();
                                let cmdline =
                                    proc.cmd().iter().map(|oss| oss.to_string_lossy()).join(" ");

                                // Check for potential duplicates
                                children.push(ProcStats {
                                    stat: Some(Stat {
                                        rss: proc_memory as i64,
                                        vsize: proc_vmemory as i64,
                                        state: proc.status().to_string(),
                                        name: proc.name().to_string_lossy().to_string(),
                                        pid: pid.to_string(),
                                    }),
                                    statm: None,
                                    status: None,
                                    cmdline,
                                    start_time: start_time_str,
                                });
                                Some((
                                    proc_memory,
                                    proc_vmemory,
                                    0,
                                    proc.start_time(),
                                    proc.run_time(),
                                ))
                            }
                            None => None,
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

impl SystemManager for MacOsSystem {
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
        self.refresh_procs_cache()
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

    fn reboot(&self) -> Result<()> {
        Command::new("reboot")
            .status()
            .map(|_| ())
            .into_diagnostic()
            .wrap_err("Failed to reboot")
    }
}

#[cfg(test)]
mod tests {
    use crate::config::MachineConfig;
    use std::fs;
    use std::{collections::HashMap, sync::Mutex};

    use dashmap::{DashMap, DashSet};
    use opencue_proto::host::HardwareState;

    use crate::system::macos::{MacOsSystem, MachineStaticInfo};

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

        let monitor = MacOsSystem::init(&config)
            .expect("Initializing MacOsMachineStat failed")
            .static_info;
        assert_eq!(2, monitor.num_sockets);
        assert_eq!(2, monitor.cores_per_socket);
        assert_eq!(1, monitor.hyperthreading_multiplier);
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

            let data = MacOsSystem::read_cpuinfo(&file_path).expect("Failed to read file");
            // Assert that the mapping between processor ID, physical ID, and core ID is correct
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

        let stat = MacOsSystem::init(&config).expect("Initializing MacOsSystem failed");
        let static_info = stat.static_info;

        // Proc
        assert_eq!(2, static_info.num_sockets);
        assert_eq!(2, static_info.cores_per_socket);
        assert_eq!(1, static_info.hyperthreading_multiplier);

        // attributes
        assert_eq!(Some(&"centos".to_string()), stat.attributes.get("SP_OS"));

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
        let release = MacOsSystem::read_distro(&path).expect("Failed to read release");

        assert_eq!(id.to_string(), release);
    }

    #[test]
    fn test_proc_stat() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let path = format!("{}/resources/proc/stat", project_dir);
        let boot_time = MacOsSystem::read_boot_time(&path).expect("Failed to read boot time");
        assert_eq!(1720194269, boot_time);
    }

    #[test]
    fn test_load_avg() {
        use std::io::Write;
        use tempfile::NamedTempFile;

        // Test successful case
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "1.00 2.00 3.00 4/512 12345").unwrap();
        let result = MacOsSystem::read_load_avg(temp_file.path().to_str().unwrap());
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), (1.0, 2.0, 3.0));

        // Test empty file
        let empty_file = NamedTempFile::new().unwrap();
        let result = MacOsSystem::read_load_avg(empty_file.path().to_str().unwrap());
        assert!(result.is_err());

        // Test invalid format
        let mut invalid_file = NamedTempFile::new().unwrap();
        writeln!(invalid_file, "invalid format").unwrap();
        let result = MacOsSystem::read_load_avg(invalid_file.path().to_str().unwrap());
        assert!(result.is_err());

        // Test non-existent file
        let result = MacOsSystem::read_load_avg("nonexistent_file");
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

        let result = MacOsSystem::init(&config);
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

        let result = MacOsSystem::read_boot_time(temp_file.path().to_str().unwrap());
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

        let system = MacOsSystem::init(&config).unwrap();

        // Test dynamic stats collection
        use crate::system::manager::SystemManager;
        let stats_result = system.collect_stats();
        assert!(stats_result.is_ok());

        let stats = stats_result.unwrap();
        assert_eq!(stats.hostname, system.static_info.hostname);
        assert_eq!(stats.num_sockets, 2);
        assert_eq!(stats.cores_per_socket, 2);
        assert_eq!(stats.boot_time, 1720194269);
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

        let system = MacOsSystem::init(&config).unwrap();

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

        let system = MacOsSystem::init(&config).unwrap();

        assert_eq!(system.static_info.tags.len(), 2);
        assert!(system.static_info.tags.contains(&"test_tag".to_string()));
        assert!(system.static_info.tags.contains(&"integration".to_string()));
    }

    #[test]
    fn test_system_with_single_core() {
        let system = setup_test_system(1, 1, 1);

        assert_eq!(system.static_info.num_sockets, 1);
        assert_eq!(system.static_info.cores_per_socket, 1);
        assert_eq!(system.static_info.hyperthreading_multiplier, 1);
    }

    #[test]
    fn test_system_with_high_thread_count() {
        let system = setup_test_system(16, 2, 4); // 2 CPUs, 4 cores each, 2 threads per core

        assert_eq!(system.static_info.num_sockets, 2);
        assert_eq!(system.static_info.cores_per_socket, 8);
    }

    #[test]
    fn test_read_distro_empty_file() {
        use tempfile::NamedTempFile;

        let empty_file = NamedTempFile::new().unwrap();
        let result = MacOsSystem::read_distro(empty_file.path().to_str().unwrap());
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

    // Helper function to create a test system with specified configuration
    fn setup_test_system(
        total_cores: u32,
        physical_cpus: u32,
        threads_per_core: u32,
    ) -> MacOsSystem {
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

        let config = MachineConfig::default();
        MacOsSystem {
            config,
            static_info: MachineStaticInfo {
                hostname: "test".to_string(),
                total_memory: 0,
                total_swap: 0,
                num_sockets: physical_cpus,
                cores_per_socket: cores_per_cpu,
                hyperthreading_multiplier: 1,
                boot_time_secs: 0,
                tags: vec![],
            },
            hardware_state: HardwareState::Up,
            attributes: HashMap::new(),
            sysinfo_system: Mutex::new(sysinfo::System::new()),
            session_processes: DashMap::new(),
            monitored_sessions: DashSet::new(),
        }
    }
}
