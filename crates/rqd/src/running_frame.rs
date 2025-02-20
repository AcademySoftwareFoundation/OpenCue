use std::{collections::HashMap, sync::Arc};

use dashmap::DashMap;
use miette::{miette, IntoDiagnostic, Result};
use opencue_proto::{
    report::{ChildrenProcStats, RunningFrameInfo},
    rqd::RunFrame,
};
use uuid::Uuid;

use crate::config::config::RunnerConfig;

/// Wrapper around protobuf message RunningFrameInfo
#[derive(Clone)]
pub struct RunningFrame {
    pub resource_id: String,
    pub job_id: Uuid,
    pub job_name: String,
    pub frame_id: Uuid,
    pub frame_name: String,
    pub layer_id: Uuid,
    pub show: String,
    pub shot: String,
    pub command: String,
    pub user_name: String,
    pub num_cores: u32,
    pub num_gpus: u32,
    pub frame_temp_dir: String,
    pub log_path: String,
    pub requested_uid: Option<u32>,
    pub gid: u32,
    pub ignore_nimby: bool,
    pub environment: HashMap<String, String>,
    /// additional data can be provided about the running frame
    pub attributes: HashMap<String, String>,
    pub frame_stats: Option<FrameStats>,
    initialized_resources: Option<InitializedResources>,
}

#[derive(Clone)]
struct InitializedResources {
    pub uid: u32,
    pub config: RunnerConfig,
    pub cpu_list: Vec<u32>,
    pub gpu_list: Vec<u32>,
}

#[derive(Clone)]
pub struct FrameStats {
    /// Maximum resident set size (KB) - maximum amount of physical memory used.
    max_rss: u64,
    /// Current resident set size (KB) - amount of physical memory currently in use.
    rss: u64,
    /// Maximum virtual memory size (KB) - maximum amount of virtual memory used.
    max_vsize: u64,
    /// Current virtual memory size (KB) - amount of virtual memory currently in use.
    vsize: u64,
    /// Last level cache utilization time.
    llu_time: u64,
    /// Maximum GPU memory usage (KB).
    max_used_gpu_memory: u64,
    /// Current GPU memory usage (KB).
    used_gpu_memory: u64,
    /// Additional data about the running frame's child processes.
    pub children: Option<ChildrenProcStats>,
    /// Unix timestamp denoting the start time of the frame process.
    epoch_start_time: u64,
}

impl Default for FrameStats {
    fn default() -> Self {
        FrameStats {
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

impl RunningFrame {
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn run(&self) -> Result<()> {
        // Windows, Linux or Docker
        // Setup:
        //  - tmp dir
        //  - log path
        //  - check and create user
        //  - Create log stream

        if self.resources().config.run_on_docker {
            return self.run_on_docker();
        }

        todo!()
    }

    pub fn run_on_docker(&self) -> Result<()> {
        todo!()
    }

    #[cfg(target_os = "windows")]
    pub fn run(&self) {
        todo!("Windows runner needs to be implemented")
    }

    pub fn kill(&self) {
        todo!()
    }

    fn resources(&self) -> &InitializedResources {
        self.initialized_resources.as_ref().expect(
            "Running Frame should have initialized resources at this point. Unexpected behaviour!",
        )
    }

    pub fn with_resources(
        self,
        config: RunnerConfig,
        uid: u32,
        cpu_list: Vec<u32>,
        gpu_list: Vec<u32>,
    ) -> Self {
        RunningFrame {
            initialized_resources: Some(InitializedResources {
                uid,
                config,
                cpu_list,
                gpu_list,
            }),
            ..self
        }
    }
}

impl From<RunningFrame> for RunningFrameInfo {
    fn from(frame_info: RunningFrame) -> Self {
        let frame_stats = frame_info.frame_stats.unwrap_or(FrameStats::default());
        RunningFrameInfo {
            resource_id: frame_info.resource_id.clone(),
            job_id: frame_info.job_id.to_string(),
            job_name: frame_info.job_name.clone(),
            frame_id: frame_info.frame_id.to_string(),
            frame_name: frame_info.frame_name.clone(),
            layer_id: frame_info.layer_id.to_string(),
            num_cores: frame_info.num_cores as i32,
            start_time: frame_stats.epoch_start_time as i64,
            max_rss: frame_stats.max_rss as i64,
            rss: frame_stats.rss as i64,
            max_vsize: frame_stats.max_vsize as i64,
            vsize: frame_stats.vsize as i64,
            attributes: frame_info.attributes.clone(),
            llu_time: frame_stats.llu_time as i64,
            num_gpus: frame_info.num_gpus as i32,
            max_used_gpu_memory: frame_stats.max_used_gpu_memory as i64,
            used_gpu_memory: frame_stats.used_gpu_memory as i64,
            children: frame_stats.children.clone(),
        }
    }
}

impl From<RunFrame> for RunningFrame {
    fn from(run_frame: RunFrame) -> Self {
        let job_id = run_frame.job_id();
        let frame_id = run_frame.frame_id();
        let layer_id = run_frame.layer_id();
        let log_path = std::path::Path::new(&run_frame.log_dir)
            .join(format!(
                "{}.{}.rqlog",
                run_frame.job_name, run_frame.frame_name
            ))
            .to_string_lossy()
            .to_string();
        RunningFrame {
            resource_id: run_frame.resource_id,
            job_id,
            job_name: run_frame.job_name.clone(),
            frame_id,
            frame_name: run_frame.frame_name.clone(),
            layer_id,
            command: run_frame.command,
            user_name: run_frame.user_name,
            show: run_frame.show,
            shot: run_frame.shot,
            frame_temp_dir: run_frame.frame_temp_dir,
            log_path,
            num_cores: run_frame.num_cores as u32,
            requested_uid: run_frame.uid_optional.map(|optional| match optional {
                opencue_proto::rqd::run_frame::UidOptional::Uid(uid) => uid as u32,
            }),
            gid: run_frame.gid as u32,
            ignore_nimby: run_frame.ignore_nimby,
            environment: run_frame.environment,
            attributes: run_frame.attributes,
            num_gpus: run_frame.num_gpus as u32,
            frame_stats: None,
            initialized_resources: None,
        }
    }
}

/// Keep track of all frames currently running
/// TODO: Implement recovery strategy to allow restarting rqd
/// without losing track of what's running
#[derive(Clone)]
pub struct RunningFrameCache {
    cache: DashMap<Uuid, Arc<RunningFrame>>,
}

impl RunningFrameCache {
    pub fn init() -> Arc<Self> {
        Arc::new(Self {
            cache: DashMap::with_capacity(30),
        })
    }

    /// Clones the contents of the cache into a vector. This method is potentially expensive,
    /// it should only be used when a snapshot of the current state is required
    pub fn into_running_frame_vec(&self) -> Vec<RunningFrameInfo> {
        self.cache
            .iter()
            .map(|item| RunningFrameInfo::from(item.value().as_ref().clone()))
            .collect()
    }

    pub fn insert_running_frame(
        &self,
        running_frame: Arc<RunningFrame>,
    ) -> Option<Arc<RunningFrame>> {
        self.cache.insert(running_frame.frame_id, running_frame)
    }

    pub fn contains(&self, running_frame: &RunningFrame) -> bool {
        self.cache.contains_key(&running_frame.frame_id)
    }
}
