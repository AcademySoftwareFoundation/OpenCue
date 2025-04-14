use std::{
    collections::{HashMap, HashSet},
    fs::File,
    io::{BufRead, BufReader, ErrorKind},
    net::ToSocketAddrs,
    path::Path,
    process::Command,
    sync::{Mutex, MutexGuard},
    time::UNIX_EPOCH,
};

use dashmap::DashMap;
use itertools::Itertools;
use miette::{IntoDiagnostic, Result, miette};
use nix::sys::signal::{Signal, kill, killpg};
use opencue_proto::host::HardwareState;
use sysinfo::{
    DiskRefreshKind, Disks, MemoryRefreshKind, Pid, ProcessRefreshKind, RefreshKind, System,
};
use tracing::{debug, warn};
use uuid::Uuid;

use crate::config::config::MachineConfig;

use super::manager::{
    CoreReservation, CpuStat, MachineGpuStats, MachineStat, ProcessStats, ReservationError,
    SystemManager,
};

pub struct UnixSystem {
    config: MachineConfig,
    /// Map of procids indexed by physid and coreid
    procid_by_physid_and_core_id: HashMap<u32, HashMap<u32, u32>>,
    /// The inverse map of procid_by_physid_and_core_id
    physid_and_coreid_by_procid: HashMap<u32, (u32, u32)>,
    cpu_stat: CpuStat,
    // Information colleced once at init time
    static_info: MachineStaticInfo,
    hardware_state: HardwareState,
    attributes: HashMap<String, String>,
    sysinfo_system: Mutex<sysinfo::System>,
    // Cache of all processes and their children
    // This cache is only active if use_session_id_for_proc_lineage=true
    procs_children_cache: Option<DashMap<u32, Vec<u32>>>,
    // Cache of monitored processes and their lineage
    procs_lineage_cache: DashMap<u32, Vec<u32>>,
}

#[derive(Debug)]
struct ProcessorInfoData {
    hyperthreading_multiplier: u32,
    num_procs: u32,
    num_sockets: u32,
    cores_per_proc: u32,
}

struct MachineStaticInfo {
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
    // Free + Cached
    pub available_memory: u64,
    pub free_swap: u64,
    pub total_temp_storage: u64,
    pub free_temp_storage: u64,
    pub load: u32,
}

impl UnixSystem {
    /// Initialize the unix sstats collector which reads Cpu and Memory information from
    /// the OS.
    ///
    /// sysinfo needs to have been initialized.
    pub fn init(config: &MachineConfig) -> Result<Self> {
        let (processor_info, procid_by_physid_and_core_id, physid_and_coreid_by_procid) =
            Self::read_cpuinfo(&config.cpuinfo_path)?;

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

        let available_core_count = procid_by_physid_and_core_id
            .values()
            .map(|sockets| sockets.iter().count())
            .reduce(|a, b| a + b)
            .unwrap_or(0) as u32;

        Ok(Self {
            config: config.clone(),
            procid_by_physid_and_core_id,
            physid_and_coreid_by_procid,
            static_info: MachineStaticInfo {
                hostname: Self::get_hostname(config.use_ip_as_hostname)?,
                num_procs: processor_info.num_procs,
                total_memory,
                total_swap,
                num_sockets: processor_info.num_sockets,
                cores_per_proc: processor_info.cores_per_proc,
                hyperthreading_multiplier: processor_info.hyperthreading_multiplier,
                boot_time: Self::read_boot_time(&config.proc_stat_path).unwrap_or(0),
                tags: Self::setup_tags(&config),
            },
            // dynamic_info: None,
            hardware_state: HardwareState::Up,
            attributes: HashMap::from([
                ("SP_OS".to_string(), identified_os),
                (
                    "hyperthreadingMultiplier".to_string(),
                    processor_info.hyperthreading_multiplier.to_string(),
                ),
                // SwapOut is an aditional attribute that is missing on this implementation
            ]),
            cpu_stat: CpuStat {
                reserved_cores_by_physid: HashMap::new(),
                available_cores: available_core_count,
            },
            sysinfo_system: Mutex::new(sysinfo::System::new()),
            procs_children_cache: match config.use_session_id_for_proc_lineage {
                true => None,
                false => Some(DashMap::new()),
            },
            procs_lineage_cache: DashMap::new(),
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
    ///     hyperthreading multiplier, number of processors, number of sockets, and cores per
    ///     processor.
    /// 2. `HashMap<u32, HashMap<u32, u32>>` - Mapping of processor id to physical id and core id.
    /// 3. `HashMap<u32, (u32, u32)>` - Mapping of processor id to physical id and core id.
    fn read_cpuinfo(
        cpuinfo_path: &str,
    ) -> Result<(
        ProcessorInfoData,
        HashMap<u32, HashMap<u32, u32>>, // procid_by_physid_and_core_id
        HashMap<u32, (u32, u32)>,        // physid_and_coreid_by_procid
    )> {
        let mut procid_by_physid_and_core_id: HashMap<u32, HashMap<u32, u32>> = HashMap::new();
        let mut physid_and_coreid_by_procid = HashMap::new();
        let cpuinfo = File::open(cpuinfo_path).into_diagnostic()?;
        let reader = BufReader::new(cpuinfo);

        let mut num_procs = 0;
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
            } else if line.trim().len() == 0 {
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
                num_procs += 1;

                let core_id_opt = curr_core_map.get("core id");
                if let (Ok(core_id), Ok(phys_id), Some(Ok(proc_id))) = (
                    core_id_opt.map(|s| s.parse()).unwrap_or(Ok(0)), // Not mandatory
                    // If physical_id is not provided, each proc is different phys_id
                    curr_core_map
                        .get("physical id")
                        .map(|s| s.parse())
                        .unwrap_or(Ok(num_sockets)),
                    curr_core_map.get("processor").map(|s| s.parse()),
                ) {
                    // Keep a cache to avoid counting sockets twice
                    if !physical_ids.contains_key(&phys_id) {
                        physical_ids.insert(phys_id.clone(), ());
                        num_sockets += 1;
                    }
                    procid_by_physid_and_core_id
                        .entry(phys_id)
                        .and_modify(|e| {
                            e.insert(core_id, proc_id);
                        })
                        .or_insert(HashMap::from([(core_id, proc_id)]));
                    physid_and_coreid_by_procid.insert(proc_id, (phys_id, core_id));
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
        num_procs = num_procs / hyper_modifier;
        if num_sockets == 0 {
            Err(miette!("Invalid CPU with no sockets (physical id)"))
        } else {
            Ok((
                ProcessorInfoData {
                    hyperthreading_multiplier: hyper_modifier,
                    num_procs,
                    num_sockets,
                    cores_per_proc: num_procs / num_sockets,
                },
                procid_by_physid_and_core_id,
                physid_and_coreid_by_procid,
            ))
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
            .ok_or_else(|| miette::miette!("Failed to get hostname"))?;
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
        for line_res in reader.lines().into_iter() {
            if let Ok(line) = line_res {
                if line.contains("ID") {
                    // ID="rocky"
                    // DISTRIB_ID=Ubuntu
                    println!("id={}", line);
                    distro_id = line
                        .split_once("=")
                        .and_then(|(_, val)| Some(val.replace("\"", "")));
                    break;
                }
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
    fn read_boot_time(proc_stat_path: &str) -> Result<u32> {
        let stat_info = File::open(proc_stat_path).into_diagnostic()?;
        let reader = BufReader::new(stat_info);
        let mut btime: Option<u32> = None;
        for line_res in reader.lines().into_iter() {
            if let Ok(line) = line_res {
                if line.trim().starts_with("btime") {
                    // btime 1723434332
                    btime = line
                        .split_once(" ")
                        .and_then(|(_, val)| val.trim().parse().ok());
                    break;
                }
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

    #[cfg(target_os = "linux")]
    fn read_dynamic_stat(&self) -> Result<MachineDynamicInfo> {
        let config = &self.config;
        let load = Self::read_load_avg(&config.proc_loadavg_path)?;
        let (total_space, available_space) = self.read_temp_storage()?;
        let sysinfo = sysinfo::System::new_with_specifics(
            RefreshKind::nothing().with_memory(MemoryRefreshKind::everything()),
        );

        Ok(MachineDynamicInfo {
            // TODO: Confirm available_memory is the best option for linux
            available_memory: sysinfo.available_memory(),
            free_swap: sysinfo.free_swap(),
            total_temp_storage: total_space,
            free_temp_storage: available_space,
            load: ((load.0 * 100.0).round() as u32 / self.static_info.hyperthreading_multiplier),
        })
    }

    #[cfg(target_os = "macos")]
    fn read_dynamic_stat(&self) -> Result<MachineDynamicInfo> {
        let config = &self.config;
        let load = Self::read_load_avg(&config.proc_loadavg_path)?;
        let (total_space, available_space) = self.read_temp_storage()?;
        let sysinfo = sysinfo::System::new_with_specifics(
            RefreshKind::nothing().with_memory(MemoryRefreshKind::everything()),
        );

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
        for line_res in reader.lines().into_iter() {
            if let Ok(line) = line_res {
                load_val = line
                    .split_whitespace()
                    .take(3)
                    .map(|l| l.parse().unwrap_or(0.0))
                    .collect_tuple();

                break;
            }
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

    fn reserve_core(
        &mut self,
        phys_id: u32,
        core_id: u32,
        reserver_id: Uuid,
    ) -> Result<(), ReservationError> {
        if self.cpu_stat.available_cores <= 0 {
            Err(ReservationError::NotEnoughResourcesAvailable)?
        }
        self.cpu_stat
            .reserved_cores_by_physid
            .entry(phys_id)
            .or_insert_with(|| CoreReservation::new(reserver_id))
            .insert(core_id);
        self.cpu_stat.available_cores -= 1;
        Ok(())
    }

    /// Gets the the list of all cores available to be reserved, organized by their socker id (phys_id)
    ///
    /// # Returns
    ///  - Vec(phys_id, Vec<core_id>)
    fn calculate_available_cores(&self) -> Result<Vec<(&u32, Vec<u32>)>, ReservationError> {
        let reserved_cores = &self.cpu_stat.reserved_cores_by_physid;
        let all_cores_map = &self.procid_by_physid_and_core_id;

        // Iterate over all phys_id=>core_id's and filter out cores that have been reserved
        let available_cores = all_cores_map
            .into_iter()
            .filter_map(
                |(phys_id, core_ids_map)| match reserved_cores.get(&phys_id) {
                    Some(reserved_core_ids) => {
                        // Filter out cores that are present in any of the sockets on the
                        // reserved_cores map
                        let available_cores: Vec<u32> = core_ids_map
                            .keys()
                            .cloned()
                            .filter(|core_id| !reserved_core_ids.iter().contains(core_id))
                            .collect();
                        // Filter out sockets that are completelly reserved
                        if available_cores.len() > 0 {
                            Some((phys_id, available_cores))
                        } else {
                            None
                        }
                    }
                    // If the phys_id doesn't exit on the reserved_cores map, consider the sockets available
                    None => Some((phys_id, core_ids_map.keys().copied().collect())),
                },
            )
            // Sort sockets with more available cores first
            .sorted_by(|a, b| Ord::cmp(&b.1.len(), &a.1.len()));

        Ok(available_cores.collect())
    }

    /// Refresh the cache of children procs.
    ///
    /// This method relies on sysinfo to have been updated periodically
    /// throught the read_dynamic_stat method to gather the updated list
    /// of running processes
    fn refresh_procs_cache(&self) {
        let sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        if self.config.use_session_id_for_proc_lineage {
            self.procs_lineage_cache.clear();
            // Group all processes by session_id
            for (session_pid, pid) in sysinfo.processes().iter().map(|(children_pid, proc)| {
                let session_pid = proc.session_id().unwrap_or(Pid::from_u32(0)).as_u32();
                (session_pid, children_pid.clone().as_u32())
            }) {
                self.procs_lineage_cache
                    .entry(session_pid)
                    .and_modify(|procs| procs.push(pid))
                    .or_insert(vec![pid]);
            }
        } else {
            let procs_children_cache = self.procs_children_cache.as_ref().expect(
                "Invalid State. \
                    procs_children_cache should be some if use_session_id_for_proc_lineage is true",
            );
            procs_children_cache.clear();

            // Collect all procs and its direct children
            for (parent_pid, pid) in sysinfo.processes().iter().map(|(children_pid, proc)| {
                let parent_pid = proc.parent().unwrap_or(Pid::from_u32(0)).as_u32();
                (parent_pid, children_pid.clone().as_u32())
            }) {
                procs_children_cache
                    .entry(parent_pid)
                    .and_modify(|children| children.push(pid))
                    .or_insert(vec![pid]);
            }
            // Clear up procs that have finished (disapeared from procs_children_cache)
            let procs_to_clear: Vec<u32> = self
                .procs_lineage_cache
                .iter()
                .filter(|item| !procs_children_cache.contains_key(item.key()))
                .map(|item| item.key().clone())
                .collect();
            for pid in procs_to_clear {
                self.procs_lineage_cache.remove(&pid);
            }
        }
    }

    /// Calculates memory usage of all processes associated with a session ID.
    ///
    /// # Arguments
    ///
    /// * `session_id` - The session ID to calculate memory for
    /// * `sysinfo` - A mutex guard containing system information
    ///
    /// # Returns
    ///
    /// A tuple containing:
    /// * Memory usage in bytes
    /// * Virtual memory usage in bytes
    /// * GPU memory usage in bytes (currently always 0)
    /// * The updated mutex guard reference
    fn calculate_session_memory<'a>(
        &self,
        session_id: &u32,
        sysinfo: MutexGuard<'a, System>,
    ) -> (u64, u64, u64, MutexGuard<'a, System>) {
        let (memory, virtual_memory, gpu_memory) = match self.procs_lineage_cache.get(session_id) {
            Some(ref lineage) => lineage
                .iter()
                .map(
                    |pid| match sysinfo.process(Pid::from(pid.clone() as usize)) {
                        Some(proc) => (proc.memory(), proc.virtual_memory(), 0),
                        None => (0, 0, 0),
                    },
                )
                .reduce(|a, b| (a.0 + b.0, a.1 + b.1, a.2 + b.2))
                .unwrap_or((0, 0, 0)),
            None => (0, 0, 0),
        };
        (memory, virtual_memory, gpu_memory, sysinfo)
    }

    /// Recursively calculates memory usage of a process and all of its child processes.
    ///
    /// # Arguments
    ///
    /// * `pid` - Process ID to calculate memory usage for
    /// * `sysinfo` - Mutex guard containing system information
    /// * `cycle_trace` - Vector of process IDs to detect recursive loops
    ///
    /// # Returns
    ///
    /// A tuple containing:
    /// * Memory usage in bytes
    /// * Virtual memory usage in bytes
    /// * GPU memory usage in bytes
    /// * The updated mutex guard reference
    /// * The updated cycle_trace vector
    ///
    /// # Implementation Notes
    ///
    /// This function recursively traverses the process tree to sum up memory usage.
    /// It uses cycle detection to prevent infinite loops in process hierarchies.
    ///
    /// GPU memory calculation is still pending
    fn calculate_children_memory_traverse_lineage<'a>(
        &'a self,
        pid: &u32,
        mut sysinfo: MutexGuard<'a, System>,
        mut cycle_trace: Vec<u32>,
    ) -> (u64, u64, u64, MutexGuard<'a, System>, Vec<u32>) {
        if let Some(procs_children_cache) = &self.procs_children_cache {
            match sysinfo.process(Pid::from(pid.clone() as usize)) {
                Some(proc) => match procs_children_cache.get(pid) {
                    Some(children_pids) => {
                        cycle_trace.push(pid.clone());
                        let (mut sum_memory, mut sum_virtual_memory, mut sum_gpu_memory) =
                            (proc.memory(), proc.virtual_memory(), 0);
                        for child_pid in children_pids.iter() {
                            // Check for cycles to avoid an infinite loop
                            if cycle_trace.contains(child_pid) {
                                warn!(
                                    "calculate_children_memory recursion found a loop.\
                                Incomplete memory calculation for {pid}."
                                );
                                break;
                            }
                            let (
                                child_memory,
                                child_virtual_memory,
                                child_gpu_memory,
                                updated_sysinfo,
                                updated_cycle_trace,
                            ) = self.calculate_children_memory_traverse_lineage(
                                child_pid,
                                sysinfo,
                                cycle_trace,
                            );
                            sum_memory += child_memory;
                            sum_virtual_memory += child_virtual_memory;
                            sum_gpu_memory += child_gpu_memory;
                            // Update our reference to the mutex guard and cycle_trace
                            sysinfo = updated_sysinfo;
                            cycle_trace = updated_cycle_trace;
                        }
                        (
                            sum_memory,
                            sum_virtual_memory,
                            sum_gpu_memory,
                            sysinfo,
                            cycle_trace,
                        )
                    }
                    // Process has no children
                    None => (proc.memory(), proc.virtual_memory(), 0, sysinfo, Vec::new()),
                },
                // Process no longer exists
                None => (0, 0, 0, sysinfo, Vec::new()),
            }
        } else {
            (0, 0, 0, sysinfo, Vec::new())
        }
    }
}

impl SystemManager for UnixSystem {
    fn collect_stats(&self) -> Result<MachineStat> {
        let dinamic_stat = self.read_dynamic_stat()?;
        Ok(MachineStat {
            hostname: self.static_info.hostname.clone(),
            num_procs: self.static_info.num_procs,
            total_memory: self.static_info.total_memory,
            total_swap: self.static_info.total_swap,
            num_sockets: self.static_info.num_sockets,
            cores_per_proc: self.static_info.cores_per_proc,
            hyperthreading_multiplier: self.static_info.hyperthreading_multiplier,
            boot_time: self.static_info.boot_time,
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

    fn init_nimby(&self) -> Result<bool> {
        // TODO: missing implementation, returning dummy val
        Ok(false)
    }

    fn collect_gpu_stats(&self) -> MachineGpuStats {
        // TODO: missing implementation, returning dummy val
        MachineGpuStats {
            count: 0,
            total_memory: 0,
            free_memory: 0,
            used_memory_by_unit: HashMap::default(),
        }
    }

    fn cpu_stat(&self) -> CpuStat {
        self.cpu_stat.clone()
    }

    fn release_core(&mut self, core_id: &u32) -> Result<(), ReservationError> {
        if self.cpu_stat.available_cores <= 0 {
            Err(ReservationError::NotEnoughResourcesAvailable)?
        }
        self.cpu_stat
            .reserved_cores_by_physid
            .iter_mut()
            .find_map(|(_, core_ids)| core_ids.remove(core_id).then_some(()))
            .ok_or(ReservationError::NotFoundError(core_id.clone()))
    }

    fn reserve_cores(&mut self, count: u32, frame_id: Uuid) -> Result<Vec<u32>, ReservationError> {
        if count > self.cpu_stat.available_cores {
            Err(ReservationError::NotEnoughResourcesAvailable)?
        }

        let mut selected_cores = Vec::with_capacity(count as usize);
        let available_cores = self.calculate_available_cores()?;

        let cores_to_reserve: Vec<(u32, u32)> = available_cores
            .into_iter()
            .flat_map(|(phys_id, core_ids)| {
                core_ids.into_iter().map(move |core_id| (*phys_id, core_id))
            })
            .take(count as usize)
            .collect();

        for (phys_id, core_id) in cores_to_reserve {
            self.reserve_core(phys_id, core_id, frame_id)?;
            selected_cores.push(core_id);
        }

        // Not having all cores reserved at this point is an unconsistent state, as it has been
        // initially checked if the system had enough cores for this reservation
        assert_eq!(
            count,
            selected_cores.len() as u32,
            "Not having all cores reserved at this point is an unconsistent state, as we haves
            initially checked if there are cores availabLe for this reservation"
        );
        if count != selected_cores.len() as u32 {
            Err(ReservationError::NotEnoughResourcesAvailable)?
        }

        Ok(selected_cores)
    }

    fn reserve_cores_by_id(
        &mut self,
        cpu_list: &Vec<u32>,
        resource_id: Uuid,
    ) -> Result<Vec<u32>, ReservationError> {
        let available_cores = self.calculate_available_cores()?;
        let reserved_cores: HashSet<&u32> = cpu_list.iter().collect();
        let mut result = Vec::new();

        let phyid_coreid_list: Vec<(u32, u32)> = available_cores
            .into_iter()
            .flat_map(|(phys_id, core_ids)| {
                let cores: HashSet<&u32> = core_ids.iter().collect();
                reserved_cores
                    .intersection(&cores)
                    .map(|core_id| (phys_id.clone(), **core_id))
                    .collect::<Vec<_>>()
            })
            .collect();

        for (phys_id, core_id) in phyid_coreid_list {
            self.reserve_core(phys_id, core_id, resource_id)?;
            result.push(core_id);
        }
        Ok(result)
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
                    .map_err(|err| std::io::Error::new(ErrorKind::Other, err))
            })
            .unwrap_or_default()
            .as_secs();

        let sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        if self.config.use_session_id_for_proc_lineage {
            let (summed_memory, summed_virtual_memory, summed_gpu_memory, guard) =
                self.calculate_session_memory(&pid, sysinfo);

            debug!(
                "Collect frame stats fo {}. rss: {}mb virtual: {}mb gpu: {}mb",
                pid,
                summed_memory / 1024 / 1024,
                summed_virtual_memory / 1024 / 1024,
                summed_gpu_memory / 1024 / 1024
            );
            Ok(guard
                .process(Pid::from(pid as usize))
                .map(|proc| ProcessStats {
                    // Caller is responsible for maintaining the Max value between calls
                    max_rss: summed_memory,
                    rss: summed_memory,
                    max_vsize: summed_virtual_memory,
                    vsize: summed_virtual_memory,
                    llu_time: log_mtime,
                    max_used_gpu_memory: 0,
                    used_gpu_memory: summed_gpu_memory,
                    children: None,
                    epoch_start_time: proc.start_time(),
                }))
        } else {
            // Traverse the tree of procs using their parent id and calculate memory consumption
            let (summed_memory, summed_virtual_memory, summed_gpu_memory, guard, lineage) =
                self.calculate_children_memory_traverse_lineage(&pid, sysinfo, Vec::new());

            debug!(
                "Collect frame stats fo {}. rss: {}mb virtual: {}mb gpu: {}mb",
                pid,
                summed_memory / 1024 / 1024,
                summed_virtual_memory / 1024 / 1024,
                summed_gpu_memory / 1024 / 1024
            );

            self.procs_lineage_cache.insert(pid, lineage);
            Ok(guard
                .process(Pid::from(pid as usize))
                .map(|proc| ProcessStats {
                    // Caller is responsible for maintaining the Max value between calls
                    max_rss: summed_memory,
                    rss: summed_memory,
                    max_vsize: summed_virtual_memory,
                    vsize: summed_virtual_memory,
                    llu_time: log_mtime,
                    max_used_gpu_memory: 0,
                    used_gpu_memory: summed_gpu_memory,
                    children: None,
                    epoch_start_time: proc.start_time(),
                }))
        }
    }

    fn refresh_procs(&self) {
        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());

        *sysinfo = sysinfo::System::new_with_specifics(
            RefreshKind::nothing().with_processes(ProcessRefreshKind::nothing().with_memory()),
        );
        drop(sysinfo);
        self.refresh_procs_cache();
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

    fn force_kill(&self, pids: &Vec<u32>) -> Result<()> {
        let mut failed_pids = Vec::new();
        let mut last_err = Ok(());
        for pid in pids {
            if let Err(err) = kill(
                nix::unistd::Pid::from_raw(pid.clone() as i32),
                Signal::SIGKILL,
            ) {
                failed_pids.push(pid);
                last_err = Err(err);
            }
        }
        last_err.map_err(|err| miette!("Failed to force kill pids {:?}. Errno={err}", failed_pids))
    }

    fn get_proc_lineage(&self, pid: u32) -> Option<Vec<u32>> {
        self.procs_lineage_cache
            .get(&pid)
            .map(|lineage| lineage.clone())
    }

    // fn get_procs_by_pgid(&self, pgid: u32) -> Option<Vec<u32>> {}
}

#[cfg(test)]
mod tests {
    use super::UnixSystem;
    use crate::config::config::MachineConfig;
    use std::fs;

    #[test]
    /// Use this unit test to quickly exercice a single cpuinfo file by changing the path on the
    /// initial lines
    fn test_read_cpuinfo() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let mut config = MachineConfig::default();
        config.cpuinfo_path = format!("{}/resources/cpuinfo/cpuinfo_drack_4-2-2", project_dir);
        config.distro_release_path = "".to_string();
        config.proc_stat_path = "".to_string();
        config.inittab_path = "".to_string();
        config.core_multiplier = 1;

        let linux_monitor = UnixSystem::init(&config)
            .expect("Initializing LinuxMachineStat failed")
            .static_info;
        assert_eq!(4, linux_monitor.num_procs);
        assert_eq!(2, linux_monitor.num_sockets);
        assert_eq!(2, linux_monitor.cores_per_proc);
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
                for entry in entries {
                    if let Ok(entry) = entry {
                        println!("Testing {:?}", entry.path());
                        cpuinfo_tester(entry.file_name().to_str().unwrap());
                    }
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
        if let (Some(expected_procs), Some(expected_cores_per_proc), Some(expected_sockets)) = (
            values
                .get(0)
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

            let (cpuinfo, procid_by_physid_and_core_id, physid_and_coreid_by_procid) =
                UnixSystem::read_cpuinfo(&file_path).expect("Failed to read file");
            // Assert that the mapping between processor ID, physical ID, and core ID is correct
            let mut found_mapping = false;
            println!(
                "procid_by_physid_and_core_id={:?}",
                procid_by_physid_and_core_id
            );
            println!(
                "physid_and_coreid_by_procid={:?}",
                physid_and_coreid_by_procid
            );
            for (phys_id, core_map) in procid_by_physid_and_core_id.iter() {
                for (core_id, proc_id) in core_map.iter() {
                    // Check bidirectional mapping
                    if let Some((mapped_phys, mapped_core)) =
                        physid_and_coreid_by_procid.get(proc_id)
                    {
                        assert_eq!(phys_id, mapped_phys);
                        assert_eq!(core_id, mapped_core);
                        found_mapping = true;
                    } else {
                        panic!("Missing mapping for processor ID {}", proc_id);
                    }
                }
            }
            assert!(
                found_mapping,
                "No mappings found between processor IDs and physical/core IDs"
            );
            assert_eq!(expected_procs, cpuinfo.num_procs, "Assert num_procs");
            assert_eq!(expected_sockets, cpuinfo.num_sockets, "Assert num_sockets");
            assert_eq!(
                expected_cores_per_proc, cpuinfo.cores_per_proc,
                "Assert cores_per_proc"
            );
            assert_eq!(
                expected_hyper_multi, cpuinfo.hyperthreading_multiplier,
                "Assert hyperthreading_multiplier"
            );
            // TODO: Assert contents of proxid_by_physid_and_core_id and physid_and_coreid_by_procid
        }
    }

    #[test]
    fn test_static_info() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let mut config = MachineConfig::default();
        config.cpuinfo_path = format!("{}/resources/cpuinfo/cpuinfo_drack_4-2-2", project_dir);
        config.distro_release_path = format!("{}/resources/distro-release/centos", project_dir);
        config.proc_stat_path = format!("{}/resources/proc/stat", project_dir);
        config.proc_loadavg_path = format!("{}/resources/proc/loadavg", project_dir);
        config.inittab_path = "".to_string();
        config.core_multiplier = 1;

        let stat = UnixSystem::init(&config).expect("Initializing LinuxMachineStat failed");
        let static_info = stat.static_info;

        // Proc
        assert_eq!(4, static_info.num_procs);
        assert_eq!(2, static_info.num_sockets);
        assert_eq!(2, static_info.cores_per_proc);
        assert_eq!(1, static_info.hyperthreading_multiplier);

        // attributes
        assert_eq!(Some(&"centos".to_string()), stat.attributes.get("SP_OS"));

        // boot time
        assert_eq!(1720194269, static_info.boot_time);
    }

    #[test]
    fn test_read_distro_release() {
        let project_dir = env!("CARGO_MANIFEST_DIR");
        let file_path = format!("{}/resources/distro-release", project_dir);

        match fs::read_dir(file_path) {
            Ok(entries) => {
                for entry in entries {
                    if let Ok(entry) = entry {
                        println!("Testing {:?}", entry.path());
                        distro_release_tester(entry.file_name().to_str().unwrap());
                    }
                }
            }
            Err(e) => println!("Error reading directory: {}", e),
        }
    }

    fn distro_release_tester(id: &str) {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let path = format!("{}/resources/distro-release/{}", project_dir, id);
        let release = UnixSystem::read_distro(&path).expect("Failed to read release");

        assert_eq!(id.to_string(), release);
    }

    #[test]
    fn test_proc_stat() {
        let project_dir = env!("CARGO_MANIFEST_DIR");

        let path = format!("{}/resources/proc/stat", project_dir);
        let boot_time = UnixSystem::read_boot_time(&path).expect("Failed to read boot time");
        assert_eq!(1720194269, boot_time);
    }

    #[test]
    fn test_load_avg() {
        use std::io::Write;
        use tempfile::NamedTempFile;

        // Test successful case
        let mut temp_file = NamedTempFile::new().unwrap();
        writeln!(temp_file, "1.00 2.00 3.00 4/512 12345").unwrap();
        let result = UnixSystem::read_load_avg(temp_file.path().to_str().unwrap());
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), (1.0, 2.0, 3.0));

        // Test empty file
        let empty_file = NamedTempFile::new().unwrap();
        let result = UnixSystem::read_load_avg(empty_file.path().to_str().unwrap());
        assert!(result.is_err());

        // Test invalid format
        let mut invalid_file = NamedTempFile::new().unwrap();
        writeln!(invalid_file, "invalid format").unwrap();
        let result = UnixSystem::read_load_avg(invalid_file.path().to_str().unwrap());
        assert!(result.is_err());

        // Test non-existent file
        let result = UnixSystem::read_load_avg("nonexistent_file");
        assert!(result.is_err());
    }

    #[cfg(test)]
    mod tests {
        // ... existing imports ...

        use std::{collections::HashMap, sync::Mutex};

        use dashmap::DashMap;
        use itertools::Itertools;
        use opencue_proto::host::HardwareState;
        use uuid::Uuid;

        use crate::{
            config::config::MachineConfig,
            system::{
                manager::{CpuStat, ReservationError, SystemManager},
                unix::{MachineStaticInfo, UnixSystem},
            },
        };

        #[test]
        fn test_reserve_cores_success() {
            let mut system = setup_test_system(4, 2); // 4 cores total, 2 physical CPUs

            // Reserve 2 cores
            let result = system.reserve_cores(2, Uuid::new_v4());

            assert!(result.is_ok());
            let reserved = result.unwrap();
            assert_eq!(reserved.len(), 2);
            assert_eq!(system.cpu_stat.available_cores, 2);
        }

        #[test]
        fn test_reserve_cores_insufficient_resources() {
            let mut system = setup_test_system(4, 2);

            // Try to reserve more cores than available
            let result = system.reserve_cores(5, Uuid::new_v4());
            assert!(matches!(
                result,
                Err(ReservationError::NotEnoughResourcesAvailable)
            ));
            assert_eq!(system.cpu_stat.available_cores, 4); // Should remain unchanged
        }

        #[test]
        fn test_reserve_cores_all_available() {
            let mut system = setup_test_system(4, 2);

            // Reserve all cores
            let result = system.reserve_cores(4, Uuid::new_v4());
            assert!(result.is_ok());
            let reserved = result.unwrap();
            assert_eq!(reserved.len(), 4);
            assert_eq!(system.cpu_stat.available_cores, 0);
        }

        #[test]
        fn test_reserve_cores_affinity() {
            let mut system = setup_test_system(12, 3);

            // Reserve 2 cores
            let result = system.reserve_cores(7, Uuid::new_v4());
            assert!(result.is_ok());

            // Check that cores are distributed across physical CPUs when possible
            let reserved_count_per_socket: Vec<usize> = system
                .cpu_stat
                .reserved_cores_by_physid
                .iter()
                .map(|(_, proc_ids)| proc_ids.iter().len())
                .sorted()
                .collect();
            assert_eq!(
                vec![3, 4],
                reserved_count_per_socket,
                "Cores should be grouped as much as possible into physical CPUs",
            );
        }

        #[test]
        fn test_reserve_cores_sequential_reservations() {
            let mut system = setup_test_system(4, 2);

            // First reservation
            let result1 = system.reserve_cores(2, Uuid::new_v4());
            assert!(result1.is_ok());
            assert_eq!(system.cpu_stat.available_cores, 2);

            // Second reservation
            let result2 = system.reserve_cores(1, Uuid::new_v4());
            assert!(result2.is_ok());
            assert_eq!(system.cpu_stat.available_cores, 1);

            // Third reservation - should fail
            let result3 = system.reserve_cores(2, Uuid::new_v4());
            assert!(matches!(
                result3,
                Err(ReservationError::NotEnoughResourcesAvailable)
            ));
        }

        // Helper function to create a test system with specified configuration
        fn setup_test_system(total_cores: u32, physical_cpus: u32) -> UnixSystem {
            let mut procid_by_physid_and_core_id = HashMap::new();
            let mut physid_and_coreid_by_procid = HashMap::new();

            // Set up CPU topology
            let cores_per_cpu = total_cores / physical_cpus;
            for phys_id in 0..physical_cpus {
                let mut core_map = HashMap::new();
                for core_id in 0..cores_per_cpu {
                    let proc_id = phys_id * cores_per_cpu + core_id;
                    core_map.insert(core_id, proc_id);
                    physid_and_coreid_by_procid.insert(proc_id, (phys_id, core_id));
                }
                procid_by_physid_and_core_id.insert(phys_id, core_map);
            }

            UnixSystem {
                config: MachineConfig::default(),
                procid_by_physid_and_core_id,
                physid_and_coreid_by_procid,
                cpu_stat: CpuStat {
                    reserved_cores_by_physid: HashMap::new(),
                    available_cores: total_cores,
                },
                static_info: MachineStaticInfo {
                    hostname: "test".to_string(),
                    num_procs: total_cores,
                    total_memory: 0,
                    total_swap: 0,
                    num_sockets: physical_cpus,
                    cores_per_proc: cores_per_cpu,
                    hyperthreading_multiplier: 1,
                    boot_time: 0,
                    tags: vec![],
                },
                hardware_state: HardwareState::Up,
                attributes: HashMap::new(),
                sysinfo_system: Mutex::new(sysinfo::System::new()),
                procs_children_cache: Some(DashMap::new()),
                procs_lineage_cache: DashMap::new(),
            }
        }
    }
}
