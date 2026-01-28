// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use std::{
    collections::HashMap,
    net::ToSocketAddrs,
    path::Path,
    process::Command,
    sync::Mutex,
    time::{Duration, UNIX_EPOCH},
};

use chrono::{DateTime, Local};
use dashmap::{DashMap, DashSet};
use itertools::Itertools;
use miette::{miette, Context, IntoDiagnostic, Result};
use opencue_proto::{
    host::HardwareState,
    report::{ChildrenProcStats, ProcStats, Stat},
};
use sysinfo::{
    DiskRefreshKind, Disks, MemoryRefreshKind, Pid, ProcessRefreshKind, ProcessStatus,
    ProcessesToUpdate, RefreshKind,
};
use tracing::{debug, warn};

use crate::{config::MachineConfig, system::reservation::ProcessorStructure};

use super::manager::{MachineGpuStats, MachineStat, ProcessStats, SystemManager};

pub struct WindowsSystem {
    config: MachineConfig,
    // Information collected once at init time
    static_info: MachineStaticInfo,
    hardware_state: HardwareState,
    attributes: HashMap<String, String>,
    sysinfo_system: Mutex<sysinfo::System>,
    // Cache of monitored processes and their lineage
    session_processes: DashMap<u32, Vec<u32>>,
    monitored_sessions: DashSet<u32>,
}

#[derive(Debug, Clone)]
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

/// Aggregated Data referring to a process session
struct SessionData {
    /// Amount of memory used by all processes in this session calculated by rss
    rss: u64,
    /// Amount of memory used by all processes in this session calculated by pss
    pss: u64,
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

impl WindowsSystem {
    /// Initialize the stats collector which reads CPU and Memory information from the OS.
    pub fn init(config: &MachineConfig, cpu_initial_info: ProcessorInfoData) -> Result<Self> {
        let identified_os = config
            .override_real_values
            .clone()
            .and_then(|c| c.os)
            .unwrap_or_else(|| "windows".to_string());

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
                num_sockets: cpu_initial_info.num_sockets,
                cores_per_socket: cpu_initial_info.cores_per_socket,
                hyperthreading_multiplier: cpu_initial_info.hyperthreading_multiplier,
                boot_time_secs: sysinfo::System::boot_time(),
                tags: Self::setup_tags(config),
            },
            hardware_state: HardwareState::Up,
            attributes: HashMap::from([
                ("SP_OS".to_string(), identified_os),
                (
                    "hyperthreadingMultiplier".to_string(),
                    cpu_initial_info.hyperthreading_multiplier.to_string(),
                ),
            ]),
            sysinfo_system: Mutex::new(sysinfo::System::new()),
            session_processes: DashMap::new(),
            monitored_sessions: DashSet::new(),
        })
    }

    /// Reads the CPU information from the system and extracts core topology.
    pub fn read_cpuinfo(_cpuinfo_path: &str) -> Result<ProcessorInfoData> {
        let mut sysinfo = sysinfo::System::new();
        sysinfo.refresh_cpu_all();

        let logical_cpus = sysinfo.cpus().len().max(1) as u32;
        let physical_cores = sysinfo
            .physical_core_count()
            .unwrap_or(logical_cpus as usize)
            .max(1) as u32;

        let hyperthreading_multiplier = (logical_cpus / physical_cores).max(1);

        let (threads_by_core_unique_id, cores_by_phys_id, thread_id_lookup_table) =
            Self::build_processor_structure(
                logical_cpus,
                physical_cores,
                hyperthreading_multiplier,
            );

        let processor_structure = ProcessorStructure::init(
            threads_by_core_unique_id,
            cores_by_phys_id,
            thread_id_lookup_table,
        );

        Ok(ProcessorInfoData {
            hyperthreading_multiplier,
            num_sockets: 1,
            cores_per_socket: physical_cores,
            processor_structure,
        })
    }

    fn build_processor_structure(
        logical_cpus: u32,
        physical_cores: u32,
        hyperthreading_multiplier: u32,
    ) -> (
        HashMap<String, Vec<u32>>,
        HashMap<u32, Vec<u32>>,
        HashMap<u32, (u32, u32)>,
    ) {
        let mut threads_by_core_unique_id: HashMap<String, Vec<u32>> = HashMap::new();
        let mut cores_by_phys_id: HashMap<u32, Vec<u32>> = HashMap::new();
        let mut thread_id_lookup_table: HashMap<u32, (u32, u32)> = HashMap::new();

        let mut core_ids = Vec::with_capacity(physical_cores as usize);
        for core_id in 0..physical_cores {
            core_ids.push(core_id);

            let start_thread = core_id * hyperthreading_multiplier;
            let mut threads = Vec::new();
            for offset in 0..hyperthreading_multiplier {
                let thread_id = start_thread + offset;
                if thread_id < logical_cpus {
                    threads.push(thread_id);
                    thread_id_lookup_table.insert(thread_id, (0, core_id));
                }
            }
            threads_by_core_unique_id.insert(format!("0_{}", core_id), threads);
        }
        cores_by_phys_id.insert(0, core_ids);

        (
            threads_by_core_unique_id,
            cores_by_phys_id,
            thread_id_lookup_table,
        )
    }

    /// Retrieves the hostname of the machine based on the configuration parameters.
    fn get_hostname(use_ip_as_hostname: bool) -> Result<String> {
        let hostname = sysinfo::System::host_name()
            .ok_or_else(|| miette::miette!("Failed to get hostname"))?
            .split('.')
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

    /// Setup tags based on the environment this host is running on
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

    fn read_is_workstation(config: &MachineConfig) -> Result<bool> {
        let override_workstation_mode = config
            .override_real_values
            .as_ref()
            .and_then(|c| c.workstation_mode)
            .unwrap_or(false);
        Ok(override_workstation_mode)
    }

    fn read_dynamic_stat(&self) -> Result<MachineDynamicInfo> {
        let load = sysinfo::System::load_average();
        let (total_space, available_space) = self.read_temp_storage()?;
        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        sysinfo.refresh_memory();

        let hyperthreading = self.static_info.hyperthreading_multiplier.max(1);
        Ok(MachineDynamicInfo {
            available_memory: sysinfo.available_memory(),
            free_swap: sysinfo.free_swap(),
            total_temp_storage: total_space,
            free_temp_storage: available_space,
            load: ((load.one as f32 * 100.0).round() as u32 / hyperthreading),
        })
    }

    /// Reads storage information from the temporary mount point and extracts
    /// the total space and available space.
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
    fn refresh_procs_cache(&self) {
        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        sysinfo.refresh_processes_specifics(
            ProcessesToUpdate::All,
            true,
            ProcessRefreshKind::nothing().with_cpu().with_memory(),
        );

        self.session_processes.clear();
        for (pid, proc) in sysinfo.processes() {
            if Self::is_proc_dead(Some(proc)) {
                continue;
            }

            if let Some(parent_pid) = proc.parent() {
                let parent_id = parent_pid.as_u32();
                if parent_id != pid.as_u32() {
                    self.session_processes
                        .entry(parent_id)
                        .and_modify(|procs| procs.push(pid.as_u32()))
                        .or_insert(vec![pid.as_u32()]);
                }
            } else {
                self.session_processes.entry(pid.as_u32()).or_insert(vec![]);
            }
        }
    }

    fn is_proc_dead(process: Option<&sysinfo::Process>) -> bool {
        match process {
            Some(proc) if [ProcessStatus::Dead, ProcessStatus::Zombie].contains(&proc.status()) => {
                true
            }
            None => true,
            _ => false,
        }
    }

    fn collect_lineage(&self, root_pid: u32) -> Vec<u32> {
        let mut stack = vec![root_pid];
        let mut visited = std::collections::HashSet::new();
        let mut lineage = Vec::new();

        while let Some(pid) = stack.pop() {
            if !visited.insert(pid) {
                continue;
            }
            lineage.push(pid);
            if let Some(children) = self.session_processes.get(&pid) {
                for child in children.iter().rev() {
                    stack.push(*child);
                }
            }
        }

        lineage
    }

    fn calculate_proc_session_data(&self, session_id: &u32) -> Option<SessionData> {
        self.monitored_sessions.insert(*session_id);

        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        let mut children = Vec::new();

        let session_pid = Pid::from_u32(*session_id);
        sysinfo.refresh_processes_specifics(
            ProcessesToUpdate::Some(&[session_pid]),
            true,
            ProcessRefreshKind::nothing().with_cpu().with_memory(),
        );

        if Self::is_proc_dead(sysinfo.process(session_pid)) {
            return None;
        }

        let lineage = self.collect_lineage(*session_id);
        if lineage.is_empty() {
            return None;
        }

        let (memory, virtual_memory, gpu_memory, start_time, run_time) = lineage
            .iter()
            .filter_map(|pid| {
                sysinfo.refresh_processes_specifics(
                    ProcessesToUpdate::Some(&[Pid::from_u32(*pid)]),
                    true,
                    ProcessRefreshKind::nothing().with_cpu().with_memory(),
                );

                match sysinfo.process(Pid::from_u32(*pid)) {
                    Some(proc) if !Self::is_proc_dead(Some(proc)) => {
                        let start_time_str = DateTime::<Local>::from(
                            UNIX_EPOCH + Duration::from_secs(proc.start_time()),
                        )
                        .format("%Y-%m-%d %H:%M:%S")
                        .to_string();
                        let proc_memory = proc.memory();
                        let proc_vmemory = proc.virtual_memory();
                        let cmdline = proc.cmd().iter().map(|oss| oss.to_string_lossy()).join(" ");

                        children.push(ProcStats {
                            stat: Some(Stat {
                                rss: proc_memory as i64,
                                // Fallback to RSS as PSS is not available on sysinfo
                                pss: proc_memory as i64,
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
            .unwrap_or((0, 0, 0, u64::MAX, 0));

        Some(SessionData {
            rss: memory,
            pss: memory,
            virtual_memory,
            gpu_memory,
            start_time,
            run_time,
            lineage_stats: children,
        })
    }

    fn kill_session_internal(&self, session_pid: u32, force: bool) -> Result<()> {
        let lineage = self.collect_lineage(session_pid);
        if lineage.is_empty() {
            return Err(miette!("Failed to find session {} to kill", session_pid));
        }

        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        let pids: Vec<Pid> = lineage.iter().map(|pid| Pid::from_u32(*pid)).collect();
        sysinfo.refresh_processes_specifics(
            ProcessesToUpdate::Some(&pids),
            true,
            ProcessRefreshKind::nothing().with_cpu().with_memory(),
        );

        let mut failed_pids = Vec::new();
        for pid in lineage.into_iter().rev() {
            let pid = Pid::from_u32(pid);
            if let Some(proc) = sysinfo.process(pid) {
                let killed = if force { proc.kill() } else { proc.kill() };
                if !killed {
                    failed_pids.push(pid.as_u32());
                }
            }
        }

        if failed_pids.is_empty() {
            Ok(())
        } else {
            Err(miette!("Failed to kill pids {:?}", failed_pids))
        }
    }
}

impl SystemManager for WindowsSystem {
    fn collect_stats(&self) -> Result<MachineStat> {
        let dynamic_stat = self.read_dynamic_stat()?;
        Ok(MachineStat {
            hostname: self.static_info.hostname.clone(),
            total_memory: self.static_info.total_memory,
            total_swap: self.static_info.total_swap,
            num_sockets: self.static_info.num_sockets,
            cores_per_socket: self.static_info.cores_per_socket,
            boot_time: self.static_info.boot_time_secs as u32,
            tags: self.static_info.tags.clone(),
            available_memory: dynamic_stat.available_memory,
            free_swap: dynamic_stat.free_swap,
            total_temp_storage: dynamic_stat.total_temp_storage,
            free_temp_storage: dynamic_stat.free_temp_storage,
            load: dynamic_stat.load,
        })
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

    fn hardware_state(&self) -> &HardwareState {
        &self.hardware_state
    }

    fn attributes(&self) -> &HashMap<String, String> {
        &self.attributes
    }

    fn create_user_if_unexisting(&self, username: &str, uid: u32, _gid: u32) -> Result<u32> {
        let current_user = std::env::var("USERNAME").unwrap_or_default();
        if !current_user.is_empty() && current_user != username {
            warn!(
                "User creation is not supported on Windows. Requested user '{}' will be ignored.",
                username
            );
        }
        Ok(uid)
    }

    fn collect_proc_stats(&self, pid: u32, log_path: String) -> Result<Option<ProcessStats>> {
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
                pid, session_data.rss, session_data.virtual_memory, session_data.gpu_memory
            );
            ProcessStats {
                max_rss: session_data.rss,
                rss: session_data.rss,
                max_pss: session_data.pss,
                pss: session_data.pss,
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
        self.kill_session_internal(session_pid, false)
    }

    fn force_kill_session(&self, session_pid: u32) -> Result<()> {
        self.kill_session_internal(session_pid, true)
    }

    fn force_kill(&self, pids: &[u32]) -> Result<()> {
        let mut failed_pids = Vec::new();
        let mut sysinfo = self
            .sysinfo_system
            .lock()
            .unwrap_or_else(|err| err.into_inner());
        let pid_handles: Vec<Pid> = pids.iter().map(|pid| Pid::from_u32(*pid)).collect();
        sysinfo.refresh_processes_specifics(
            ProcessesToUpdate::Some(&pid_handles),
            true,
            ProcessRefreshKind::nothing().with_cpu().with_memory(),
        );

        for pid in pids {
            if let Some(proc) = sysinfo.process(Pid::from_u32(*pid)) {
                if !proc.kill() {
                    failed_pids.push(*pid);
                }
            }
        }

        if failed_pids.is_empty() {
            Ok(())
        } else {
            Err(miette!("Failed to force kill pids {:?}", failed_pids))
        }
    }

    fn get_proc_lineage(&self, pid: u32) -> Option<Vec<u32>> {
        let lineage = self.collect_lineage(pid);
        if lineage.is_empty() {
            None
        } else {
            Some(lineage)
        }
    }

    fn reboot(&self) -> Result<()> {
        Command::new("shutdown")
            .args(["/r", "/t", "0"])
            .status()
            .map(|_| ())
            .into_diagnostic()
            .wrap_err("Failed to reboot")
    }
}
