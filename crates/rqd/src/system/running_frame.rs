use std::{collections::HashMap, env, sync::Arc};

use dashmap::DashMap;
use miette::{miette, Result};
use opencue_proto::{
    report::{ChildrenProcStats, RunningFrameInfo},
    rqd::RunFrame,
};
use uuid::Uuid;

use crate::config::config::RunnerConfig;

use super::logging::{FrameLogger, FrameLoggerT};

/// Wrapper around protobuf message RunningFrameInfo
#[derive(Clone)]
pub struct RunningFrame {
    request: RunFrame,
    job_id: Uuid,
    frame_id: Uuid,
    layer_id: Uuid,
    frame_stats: Option<FrameStats>,
    log_path: String,
    uid: u32,
    config: RunnerConfig,
    cpu_list: Option<Vec<u32>>,
    gpu_list: Option<Vec<u32>>,
    env_vars: HashMap<&'static str, String>,
    hostname: String,
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
    pub fn init(
        request: RunFrame,
        uid: u32,
        config: RunnerConfig,
        cpu_list: Option<Vec<u32>>,
        gpu_list: Option<Vec<u32>>,
        hostname: String,
    ) -> Self {
        let job_id = request.job_id();
        let frame_id = request.frame_id();
        let layer_id = request.layer_id();
        let log_path = std::path::Path::new(&request.log_dir)
            .join(format!("{}.{}.rqlog", request.job_name, request.frame_name))
            .to_string_lossy()
            .to_string();
        let env_vars = Self::setup_env_vars(&config, &request, hostname.clone(), log_path.clone());
        RunningFrame {
            request,
            job_id,
            frame_id,
            layer_id,
            frame_stats: None,
            log_path,
            uid,
            config,
            cpu_list,
            gpu_list,
            env_vars,
            hostname,
        }
    }

    fn setup_env_vars(
        config: &RunnerConfig,
        request: &RunFrame,
        hostname: String,
        log_path: String,
    ) -> HashMap<&'static str, String> {
        let path_env_var = match config.use_host_path_env_var {
            true => env::var("PATH").unwrap_or("".to_string()),
            false => Self::get_path_env_var().to_string(),
        };
        let mut env_vars = HashMap::new();
        env_vars.insert("PATH", path_env_var);
        env_vars.insert("TERM", "unknown".to_string());
        env_vars.insert("USER", request.user_name.clone());
        env_vars.insert("LOGNAME", request.user_name.clone());
        env_vars.insert("mcp", "1".to_string());
        env_vars.insert("show", request.show.clone());
        env_vars.insert("shot", request.shot.clone());
        env_vars.insert("jobid", request.job_name.clone());
        env_vars.insert("jobhost", hostname);
        env_vars.insert("frame", request.frame_name.clone());
        env_vars.insert("zframe", request.frame_name.clone());
        env_vars.insert("logfile", log_path);
        env_vars.insert("maxframetime", "0".to_string());
        env_vars.insert("minspace", "200".to_string());
        env_vars.insert("CUE3", "True".to_string());
        env_vars.insert("SP_NOMYCSHRC", "1".to_string());
        env_vars
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn get_path_env_var() -> &'static str {
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    }

    #[cfg(target_os = "windows")]
    pub fn get_path_env_var() -> &'static str {
        "C:/Windows/system32;C:/Windows;C:/Windows/System32/Wbem"
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn run(&self) -> Result<()> {
        use crate::system::logging::{FrameLoggerBuilder, FrameLoggerT};

        if self.config.run_on_docker {
            return self.run_on_docker();
        }

        let logger = FrameLoggerBuilder::fromLoggerConfig(self.log_path.clone(), &self.config)?;
        logger.writeln(self.write_header().as_str());

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

    fn write_header(&self) -> String {
        let env_var_list = self
            .env_vars
            .iter()
            .map(|(key, value)| format!("{key}               {value}"))
            .reduce(|a, b| a + "\n" + b.as_str())
            .unwrap_or("".to_string());
        let hyperthread = match &self.cpu_list {
            Some(cpu_list) => format!(
                "Hyperthreading cores {}",
                cpu_list
                    .into_iter()
                    .map(|v| format!("{}", v))
                    .reduce(|a, b| a + ", " + b.as_str())
                    .unwrap_or("".to_string())
            ),
            None => "Hyperthreading disabled".to_string(),
        };
        format!(
            r#"
====================================================================================================
RenderQ JobSpec     {start_time}
command             {command}
uid                 {uid}
gid                 {gid}
log_path            {log_path}
render_host         {hostname}
job_id              {job_id}
frame_id            {frame_id}
{hyperthread}
----------------------------------------------------------------------------------------------------
Environment Variables:
{env_var_list}
====================================================================================================
            "#,
            start_time = "",
            command = self.request.command,
            uid = self.uid,
            gid = self.request.gid,
            log_path = self.log_path,
            hostname = self.hostname,
            job_id = self.job_id,
            frame_id = self.frame_id,
        )
    }
}

impl From<RunningFrame> for RunningFrameInfo {
    fn from(running_frame: RunningFrame) -> Self {
        let frame_stats = running_frame.frame_stats.unwrap_or(FrameStats::default());
        RunningFrameInfo {
            resource_id: running_frame.request.resource_id.clone(),
            job_id: running_frame.request.job_id.to_string(),
            job_name: running_frame.request.job_name.clone(),
            frame_id: running_frame.request.frame_id.to_string(),
            frame_name: running_frame.request.frame_name.clone(),
            layer_id: running_frame.request.layer_id.to_string(),
            num_cores: running_frame.request.num_cores as i32,
            start_time: frame_stats.epoch_start_time as i64,
            max_rss: frame_stats.max_rss as i64,
            rss: frame_stats.rss as i64,
            max_vsize: frame_stats.max_vsize as i64,
            vsize: frame_stats.vsize as i64,
            attributes: running_frame.request.attributes.clone(),
            llu_time: frame_stats.llu_time as i64,
            num_gpus: running_frame.request.num_gpus as i32,
            max_used_gpu_memory: frame_stats.max_used_gpu_memory as i64,
            used_gpu_memory: frame_stats.used_gpu_memory as i64,
            children: frame_stats.children.clone(),
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

    pub fn contains(&self, frame_id: &Uuid) -> bool {
        self.cache.contains_key(frame_id)
    }
}
