use std::{
    collections::HashMap,
    env,
    fmt::Display,
    fs::{self, File, OpenOptions},
    io::{BufRead, BufReader},
    os::{
        fd::{FromRawFd, IntoRawFd, RawFd},
        unix::process::CommandExt,
    },
    path::Path,
    sync::{mpsc::Receiver, Arc, Mutex},
    thread::JoinHandle,
    time::Duration,
};
use std::{process::Stdio, thread};

use tracing::{error, warn};

use dashmap::DashMap;
use miette::{miette, IntoDiagnostic, Result};
use opencue_proto::{
    report::{ChildrenProcStats, RunningFrameInfo},
    rqd::RunFrame,
};
use uuid::Uuid;

use super::logging::FrameLogger;
use crate::config::config::RunnerConfig;
use crate::system::{frame_cmd::FrameCmdBuilder, logging::FrameLoggerBuilder};

/// Wrapper around protobuf message RunningFrameInfo
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
    env_vars: HashMap<String, String>,
    hostname: String,
    raw_stdout_path: String,
    raw_stderr_path: String,
    mutable_state: Arc<Mutex<RunningState>>,
}

pub struct RunningState {
    pid: Option<u32>,
    exit_code: Option<i32>,
    launch_thread_handle: Option<JoinHandle<()>>,
}
impl RunningState {
    fn default() -> RunningState {
        RunningState {
            pid: None,
            launch_thread_handle: None,
            exit_code: None,
        }
    }
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

impl Display for RunningFrame {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}.{}({})",
            self.request.job_name, self.request.frame_name, self.frame_id
        )
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
        let log_path = Path::new(&request.log_dir)
            .join(format!("{}.{}.rqlog", request.job_name, request.frame_name))
            .to_string_lossy()
            .to_string();
        let raw_job_random_id = Uuid::new_v4();
        let raw_stdout = std::path::Path::new(&request.log_dir)
            .join(format!(
                "{}.{}.{}.raw_stdout.rqlog",
                request.job_name, request.frame_name, raw_job_random_id
            ))
            .to_string_lossy()
            .to_string();
        let raw_stderr = std::path::Path::new(&request.log_dir)
            .join(format!(
                "{}.{}.{}.raw_stderr.rqlog",
                request.job_name, request.frame_name, raw_job_random_id
            ))
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
            raw_stdout_path: raw_stdout,
            raw_stderr_path: raw_stderr,
            mutable_state: Arc::new(Mutex::new(RunningState::default())),
        }
    }

    pub fn update_launch_thread_handle(&self, thread_handle: JoinHandle<()>) {
        let mut state = self
            .mutable_state
            .lock()
            .expect("Lock should be available for this thread.");
        state.launch_thread_handle = Some(thread_handle);
    }

    pub fn update_exit_code(&self, exit_code: i32) {
        let mut state = self
            .mutable_state
            .lock()
            .expect("Lock should be available for this thread.");
        state.exit_code = Some(exit_code);
    }

    fn update_pid(&self, pid: u32) {
        let mut state = self
            .mutable_state
            .lock()
            .expect("Lock should be available for this thread.");
        state.pid = Some(pid);
    }

    fn setup_env_vars(
        config: &RunnerConfig,
        request: &RunFrame,
        hostname: String,
        log_path: String,
    ) -> HashMap<String, String> {
        let path_env_var = match config.use_host_path_env_var {
            true => env::var("PATH").unwrap_or("".to_string()),
            false => Self::get_path_env_var().to_string(),
        };
        let mut env_vars = request.environment.clone();
        env_vars.insert("PATH".to_string(), path_env_var);
        env_vars.insert("TERM".to_string(), "unknown".to_string());
        env_vars.insert("USER".to_string(), request.user_name.clone());
        env_vars.insert("LOGNAME".to_string(), request.user_name.clone());
        env_vars.insert("mcp".to_string(), "1".to_string());
        env_vars.insert("show".to_string(), request.show.clone());
        env_vars.insert("shot".to_string(), request.shot.clone());
        env_vars.insert("jobid".to_string(), request.job_name.clone());
        env_vars.insert("jobhost".to_string(), hostname);
        env_vars.insert("frame".to_string(), request.frame_name.clone());
        env_vars.insert("zframe".to_string(), request.frame_name.clone());
        env_vars.insert("logfile".to_string(), log_path);
        env_vars.insert("maxframetime".to_string(), "0".to_string());
        env_vars.insert("minspace".to_string(), "200".to_string());
        env_vars.insert("CUE3".to_string(), "True".to_string());
        env_vars.insert("SP_NOMYCSHRC".to_string(), "1".to_string());
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

    pub fn run(&self) {
        let logger_base =
            FrameLoggerBuilder::from_logger_config(self.log_path.clone(), &self.config);
        if let Err(_) = logger_base {
            error!("Failed to create log stream for {}", self.log_path);
            return;
        }
        let logger = Arc::new(logger_base.unwrap());
        match self.run_inner(Arc::clone(&logger)) {
            Ok(exit_code) => self.update_exit_code(exit_code),
            Err(err) => {
                let msg = format!("Frame {} failed to be spawned. {}", self.to_string(), err);
                logger.writeln(&msg);
                error!(msg);
            }
        }
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn run_inner(&self, logger: FrameLogger) -> Result<i32> {
        use std::{os::unix::process::ExitStatusExt, sync::mpsc};

        use tracing::{info, warn};

        if self.config.run_on_docker {
            return self.run_on_docker();
        }

        logger.writeln(self.write_header().as_str());

        let mut command = FrameCmdBuilder::new(&self.config.shell_path);
        if self.config.desktop_mode {
            command.with_nice();
        }
        if let Some(cpu_list) = &self.cpu_list {
            command.with_taskset(cpu_list.clone());
        }
        let raw_stdout = Self::setup_raw_fd(&self.raw_stdout_path)?;
        let raw_stderr = Self::setup_raw_fd(&self.raw_stderr_path)?;

        let cmd = command
            .with_frame_cmd(self.request.command.clone())
            .build()
            .envs(&self.env_vars)
            .current_dir(&self.config.temp_path)
            // An spawn job should be able to run independent of rqd.
            // If this process dies, the process continues to write to its assigned file
            // descriptor.
            .stdout(unsafe { Stdio::from_raw_fd(raw_stdout) })
            .stderr(unsafe { Stdio::from_raw_fd(raw_stderr) });

        if self.config.run_as_user {
            cmd.uid(self.uid);
        }

        // Launch frame process
        let mut child = cmd.spawn().into_diagnostic()?;

        // Update frame state with frame pid
        let pid = child.id();
        self.update_pid(child.id());

        info!(
            "Frame {self} started with pid {pid}, with {}",
            self.taskset()
        );

        // Make sure process has been spawned before creating a backup
        let _ = self.backup()?;

        let raw_stdout_path = self.raw_stdout_path.clone();
        let raw_stderr_path = self.raw_stderr_path.clone();
        // Open a oneshot channel to inform the thread it can stop reading the log
        let (sender, receiver) = mpsc::channel();
        // The logger thread streams the content of both stdout and stderr from
        // their raw file descriptors to the logger output. This allows augumenting its
        // content with timestamps for example.
        let log_pipe_handle = thread::spawn(move || {
            if let Err(e) =
                Self::pipe_output_to_logger(logger, &raw_stdout_path, &raw_stderr_path, receiver)
            {
                let msg = format!(
                    "Failed to follow_log: {}.\nPlease check the raw stdout and stderr:\n - {}\n - {}",
                    e,
                    raw_stdout_path,
                    raw_stderr_path
                );
                error!(msg);
            }
        });

        let output = child.wait();
        // Send a signal to the logger thread
        if sender.send(()).is_err() {
            warn!("Failed to notify log thread");
        }
        if let Err(_) = log_pipe_handle.join() {
            warn!("Failed to join log thread");
        }
        let output = output.into_diagnostic()?;

        // Return either output.signal or output.code.
        // Signal is only Some if a process is terminated by a signal,
        // in this case output.code is None.
        let exit_code = output.signal().unwrap_or(output.code().unwrap_or(-1));
        let msg = match exit_code {
            0 => format!("Frame {} finished successfully with pid={}", self, pid),
            _ => format!(
                "Frame {} finished with pid={} and exit_code={}. Log: {}",
                self, pid, exit_code, self.log_path
            ),
        };
        info!(msg);

        Ok(exit_code)
    }

    pub fn run_on_docker(&self) -> Result<i32> {
        todo!()
    }

    #[cfg(target_os = "windows")]
    pub fn run_inner(&self, logger: FrameLogger) -> Result<i32> {
        todo!("Windows runner needs to be implemented")
    }

    pub fn kill(&self) {
        todo!()
    }

    fn setup_raw_fd(path: &str) -> Result<RawFd> {
        let file = OpenOptions::new()
            .create(true)
            .write(true)
            .append(true)
            .open(path)
            .into_diagnostic()?;
        Ok(file.into_raw_fd())
    }

    fn pipe_output_to_logger(
        logger: FrameLogger,
        raw_stdout_path: &String,
        raw_stderr_path: &String,
        stop_flag: Receiver<()>,
    ) -> Result<()> {
        let stdout_file = File::open(raw_stdout_path)
            .map_err(|err| miette!("Failed to open raw stdout ({raw_stdout_path}). {err}"))?;
        let mut stdout = BufReader::new(stdout_file).lines().peekable();

        let stderr_file = File::open(raw_stderr_path)
            .map_err(|err| miette!("Failed to open raw stderr ({raw_stderr_path}). {err}"))?;
        let mut stderr = BufReader::new(stderr_file).lines().peekable();

        loop {
            let stdout_line = stdout.next();
            let stderr_line = stderr.next();

            if stdout_line.is_none() && stderr_line.is_none() {
                // Check if this thread has been notified the process has finished
                if let Ok(_) = stop_flag.try_recv() {
                    // Remove raw files as they finished being copied
                    if let Err(err) = fs::remove_file(raw_stdout_path) {
                        warn!("Failed to remove raw log file {}. {}", raw_stdout_path, err);
                    }
                    if let Err(err) = fs::remove_file(raw_stderr_path) {
                        warn!("Failed to remove raw log file {}. {}", raw_stderr_path, err);
                    }

                    break;
                } else {
                    thread::sleep(Duration::from_millis(300));
                }
                // TODO: Consider implementing a mechanism that will kill the frame
                // if there are no new lines for too long
            }

            if let Some(Ok(line)) = stdout_line {
                logger.writeln(line.as_str());
            }
            if let Some(Ok(line)) = stderr_line {
                logger.writeln(line.as_str());
            }
        }
        Ok(())
    }

    fn backup(&self) -> Result<()> {
        // TODO
        Ok(())
    }

    fn write_header(&self) -> String {
        let env_var_list = self
            .env_vars
            .iter()
            .map(|(key, value)| format!("{key}={value}"))
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

    fn taskset(&self) -> String {
        self.cpu_list
            .clone()
            .unwrap_or(vec![0])
            .into_iter()
            .map(|i| i.to_string())
            .collect::<Vec<_>>()
            .join(",")
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
            .map(|running_frame| {
                let frame_stats = running_frame
                    .frame_stats
                    .clone()
                    .unwrap_or(FrameStats::default());
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
            })
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

#[cfg(test)]
mod tests {
    use opencue_proto::rqd::{run_frame::UidOptional, RunFrame};
    use std::collections::HashMap;
    use std::sync::Arc;
    use uuid::Uuid;

    use crate::{config::config::RunnerConfig, system::logging::FrameLoggerT};

    use super::RunningFrame;

    fn create_running_frame(
        command: &str,
        num_cores: u32,
        uid: u32,
        environment: HashMap<String, String>,
    ) -> RunningFrame {
        let frame_id = Uuid::new_v4().to_string();
        let mut config = RunnerConfig::default();
        config.run_as_user = false;

        RunningFrame::init(
            RunFrame {
                resource_id: Uuid::new_v4().to_string(),
                job_id: Uuid::new_v4().to_string(),
                job_name: "job_name".to_string(),
                frame_id,
                frame_name: "frame_name".to_string(),
                layer_id: Uuid::new_v4().to_string(),
                command: command.to_string(),
                user_name: "username".to_string(),
                log_dir: "/tmp".to_string(),
                show: "show".to_string(),
                shot: "shot".to_string(),
                job_temp_dir: "".to_string(),
                frame_temp_dir: "".to_string(),
                log_file: "".to_string(),
                log_dir_file: "".to_string(),
                start_time: 0,
                num_cores: num_cores as i32,
                gid: 10,
                ignore_nimby: false,
                environment,
                attributes: HashMap::new(),
                num_gpus: 0,
                children: None,
                uid_optional: Some(UidOptional::Uid(uid as i32)),
            },
            uid,
            config,
            None,
            None,
            "localhost".to_string(),
        )
    }

    #[test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn test_run_logs_stdout_stderr() {
        use crate::system::logging::TestLogger;

        let mut env = HashMap::with_capacity(1);
        env.insert("TEST_ENV".to_string(), "test".to_string());
        let running_frame = create_running_frame(
            r#"echo "stdout $TEST_ENV" && echo "stderr $TEST_ENV" >&2"#,
            1,
            1,
            env,
        );

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>);
        assert!(status.is_ok());
        assert_eq!(0, status.unwrap());
        assert_eq!("stderr test", logger.pop().unwrap());
        assert_eq!("stdout test", logger.pop().unwrap());
    }
}
