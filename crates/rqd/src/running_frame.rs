use std::{collections::HashMap, sync::Arc};

use dashmap::DashMap;
use opencue_proto::{
    report::{ChildrenProcStats, RunningFrameInfo},
    rqd::RunFrame,
};
use uuid::Uuid;

/// Wrapper around protobuf message RunningFrameInfo
#[derive(Clone)]
pub struct RunningFrame {
    resource_id: String,
    job_id: Uuid,
    job_name: String,
    frame_id: Uuid,
    frame_name: String,
    layer_id: Uuid,
    show: String,
    shot: String,
    command: String,
    user_name: String,
    num_cores: i32,
    num_gpus: i32,
    frame_temp_dir: String,
    log_path: String,
    gid: i32,
    ignore_nimby: bool,
    environment: HashMap<String, String>,
    /// additional data can be provided about the running frame
    attributes: HashMap<String, String>,
    frame_stats: Option<FrameStats>,
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
    pub fn run(&self) {
        // Windows, Linux or Docker
        // Setup:
        //  - tmp dir
        //  - log path
        //  - check and create user
        //  - Create log stream
        //
        todo!()
    }
    pub fn kill(&self) {
        todo!()
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
            num_cores: frame_info.num_cores,
            start_time: frame_stats.epoch_start_time as i64,
            max_rss: frame_stats.max_rss as i64,
            rss: frame_stats.rss as i64,
            max_vsize: frame_stats.max_vsize as i64,
            vsize: frame_stats.vsize as i64,
            attributes: frame_info.attributes.clone(),
            llu_time: frame_stats.llu_time as i64,
            num_gpus: frame_info.num_gpus,
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
            num_cores: run_frame.num_cores,
            gid: run_frame.gid,
            ignore_nimby: run_frame.ignore_nimby,
            environment: run_frame.environment,
            attributes: run_frame.attributes,
            num_gpus: run_frame.num_gpus,
            frame_stats: None,
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
}
