use std::{
    collections::HashMap,
    env,
    fmt::Display,
    fs::{self, File, OpenOptions},
    io::{BufRead, BufReader, BufWriter, Read},
    os::{
        fd::{FromRawFd, IntoRawFd, RawFd},
        unix::process::CommandExt,
    },
    path::Path,
    process::ExitStatus,
    sync::{Arc, Mutex, RwLock, mpsc::Receiver},
    thread::JoinHandle,
    time::{Duration, SystemTime},
};
use std::{os::unix::process::ExitStatusExt, sync::mpsc};
use std::{process::Stdio, thread};

use chrono::{DateTime, Local};
use itertools::Itertools;
use tracing::{error, info, warn};

use crate::{frame::frame_cmd::FrameCmdBuilder, system::manager::ProcessStats};

use serde::{Deserialize, Serialize};
use sysinfo::{Pid, System};

use miette::{IntoDiagnostic, Result, miette};
use opencue_proto::{report::RunningFrameInfo, rqd::RunFrame};
use uuid::Uuid;

use super::logging::{FrameLogger, FrameLoggerBuilder};
use crate::config::config::RunnerConfig;

/// Wrapper around protobuf message RunningFrameInfo
#[derive(Serialize, Deserialize)]
pub struct RunningFrame {
    pub request: RunFrame,
    pub job_id: Uuid,
    pub frame_id: Uuid,
    pub layer_id: Uuid,
    pub frame_stats: RwLock<Option<ProcessStats>>,
    pub log_path: String,
    uid: u32,
    config: RunnerConfig,
    pub cpu_list: Option<Vec<u32>>,
    pub gpu_list: Option<Vec<u32>>,
    env_vars: HashMap<String, String>,
    pub hostname: String,
    raw_stdout_path: String,
    raw_stderr_path: String,
    pub exit_file_path: String,
    pub entrypoint_file_path: String,
    state: Mutex<FrameState>,
}

#[derive(Serialize, Deserialize, Debug)]
pub enum FrameState {
    Created(CreatedState),
    Running(RunningState),
    Finished(FinishedState),
}

#[derive(Serialize, Deserialize, Debug)]
pub struct CreatedState {
    // Attention: Recovered frames will never have a joinHandle
    #[serde(skip_serializing)]
    #[serde(skip_deserializing)]
    launch_thread_handle: Option<JoinHandle<()>>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct RunningState {
    pid: u32,
    start_time: SystemTime,
    // Attention: Recovered frames will never have a joinHandle
    #[serde(skip_serializing)]
    #[serde(skip_deserializing)]
    launch_thread_handle: Option<JoinHandle<()>>,
    kill_reason: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct FinishedState {
    pub pid: u32,
    // Attention: Recovered frames will never have a joinHandle
    #[serde(skip_serializing)]
    #[serde(skip_deserializing)]
    launch_thread_handle: Option<JoinHandle<()>>,
    pub start_time: SystemTime,
    pub end_time: SystemTime,
    pub exit_code: i32,
    pub exit_signal: Option<i32>,
    pub kill_reason: Option<String>,
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
        let resource_id = request.resource_id();
        let log_path = Path::new(&request.log_dir)
            .join(format!("{}.{}.rqlog", request.job_name, request.frame_name))
            .to_string_lossy()
            .to_string();
        let raw_stdout_path = std::path::Path::new(&request.log_dir)
            .join(format!(
                "{}.{}.{}.raw_stdout.rqlog",
                request.job_name, request.frame_name, resource_id
            ))
            .to_string_lossy()
            .to_string();
        let raw_stderr_path = std::path::Path::new(&request.log_dir)
            .join(format!(
                "{}.{}.{}.raw_stderr.rqlog",
                request.job_name, request.frame_name, resource_id
            ))
            .to_string_lossy()
            .to_string();
        let exit_file_path = std::path::Path::new(&request.log_dir)
            .join(format!(
                "{}.{}.{}.exit_status",
                request.job_name, request.frame_name, resource_id
            ))
            .to_string_lossy()
            .to_string();
        let entrypoint_file_path = std::path::Path::new(&request.log_dir)
            .join(format!(
                "{}.{}.{}.sh",
                request.job_name, request.frame_name, resource_id
            ))
            .to_string_lossy()
            .to_string();
        let env_vars = Self::setup_env_vars(&config, &request, hostname.clone(), log_path.clone());

        RunningFrame {
            request,
            job_id,
            frame_id,
            layer_id,
            frame_stats: RwLock::new(None),
            log_path,
            uid,
            config,
            cpu_list,
            gpu_list,
            env_vars,
            hostname,
            raw_stdout_path,
            raw_stderr_path,
            exit_file_path,
            entrypoint_file_path,
            state: Mutex::new(FrameState::Created(CreatedState {
                launch_thread_handle: None,
            })),
        }
    }

    pub fn get_finished_state(&self) -> Option<FinishedState> {
        let state = self.state.lock().unwrap_or_else(|err| err.into_inner());
        match *state {
            FrameState::Created(_) => None,
            FrameState::Running(_) => None,
            FrameState::Finished(ref finished_state) => Some(FinishedState {
                pid: finished_state.pid,
                launch_thread_handle: None,
                start_time: finished_state.start_time,
                end_time: finished_state.end_time,
                exit_code: finished_state.exit_code,
                exit_signal: finished_state.exit_signal,
                kill_reason: None,
            }),
        }
    }

    /// Updates the launch thread handle for this running frame
    ///
    /// # Parameters
    /// * `thread_handle` - The JoinHandle for the thread that launched this frame
    ///
    /// This method is used to store the handle of the thread responsible
    /// for launching and monitoring this frame. It allows the system to
    /// properly manage the thread lifecycle.
    pub fn update_launch_thread_handle(&self, thread_handle: JoinHandle<()>) -> Result<()> {
        let mut state = self.state.lock().unwrap_or_else(|err| err.into_inner());
        match *state {
            FrameState::Created(ref mut created_state) => {
                created_state.launch_thread_handle = Some(thread_handle);
                Ok(())
            }
            FrameState::Running(ref mut running_state) => {
                running_state.launch_thread_handle = Some(thread_handle);
                Ok(())
            }
            FrameState::Finished(_) => Err(miette!("Invalid State. Frame has already finished")),
        }
    }

    /// Updates the exit code and signal for this frame
    ///
    /// # Parameters
    /// * `exit_code` - The exit code from the frame process (0 for success, non-zero for failure)
    /// * `exit_signal` - Optional signal number that terminated the process (e.g., 15 for SIGTERM, 9 for SIGKILL)
    ///
    /// This method updates the internal finished state with the termination information,
    /// which can later be used to determine if the frame succeeded or failed.
    pub fn finish(&self, exit_code: i32, exit_signal: Option<i32>) -> Result<()> {
        let mut state = self.state.lock().unwrap_or_else(|err| err.into_inner());
        match &mut *state {
            FrameState::Created(_) => Err(miette!("Invalid State. Frame {} hasn't started", self)),
            FrameState::Running(running_state) => {
                // Create a new FinishedState with the current running state values
                let finished_state = FinishedState {
                    pid: running_state.pid,
                    launch_thread_handle: running_state.launch_thread_handle.take(),
                    start_time: running_state.start_time,
                    end_time: SystemTime::now(),
                    exit_code,
                    exit_signal,
                    kill_reason: running_state.kill_reason.clone(),
                };

                // Replace state with the new FinishedState
                *state = FrameState::Finished(finished_state);
                Ok(())
            }
            FrameState::Finished(_) => Err(miette!(
                "Invalid State. Frame {} has already finished",
                self
            )),
        }
    }

    /// Transition the frame state from Created to Running.
    ///
    /// If the frame has already started or finished, log the error and don't change the status.
    /// Returning an error is pointless as we want the frame that trigger this transition to finish
    /// regardless
    fn start(&self, pid: u32) {
        let mut state = self.state.lock().unwrap_or_else(|err| err.into_inner());

        match &mut *state {
            FrameState::Created(created_state) => {
                *state = FrameState::Running(RunningState {
                    pid,
                    start_time: SystemTime::now(),
                    launch_thread_handle: created_state.launch_thread_handle.take(),
                    kill_reason: None,
                });
            }
            FrameState::Running(running_state) => warn!(
                "Invalid State. Frame {} has already started {:?}",
                self, running_state
            ),
            FrameState::Finished(_) => warn!("Invalid States. Frame {} has already finished", self),
        }
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
    fn get_path_env_var() -> &'static str {
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    }

    #[cfg(target_os = "windows")]
    fn get_path_env_var() -> &'static str {
        "C:/Windows/system32;C:/Windows;C:/Windows/System32/Wbem"
    }

    /// Runs the frame as a subprocess.
    ///
    /// This method is the main entry point for executing a frame. It:
    /// 1. Creates a logger for the frame
    /// 2. Runs the frame command on a new process
    /// 3. Updates the frame's exit code based on the result
    /// 4. Cleans up any snapshots created during execution
    ///
    /// If the process fails to spawn, it logs the error but doesn't set an exit code.
    /// The method handles both successful and failed execution scenarios.
    pub fn run(&self, recover_mode: bool) {
        let logger_base =
            FrameLoggerBuilder::from_logger_config(self.log_path.clone(), &self.config);
        if let Err(_) = logger_base {
            error!("Failed to create log stream for {}", self.log_path);
            return;
        }
        let logger = Arc::new(logger_base.unwrap());

        let exit_code = if recover_mode {
            match self.recover_inner(Arc::clone(&logger)) {
                Ok((exit_code, exit_signal)) => {
                    if let Err(err) = self.finish(exit_code, exit_signal) {
                        warn!("Failed to mark frame {} as finished. {}", self, err);
                    }
                    logger.writeln(&self.write_footer());
                    Some(exit_code)
                }
                Err(err) => {
                    let msg = format!("Frame {} failed to be recovered. {}", self.to_string(), err);
                    logger.writeln(&msg);
                    error!(msg);
                    None
                }
            }
        } else {
            match self.run_inner(Arc::clone(&logger)) {
                Ok((exit_code, exit_signal)) => {
                    if let Err(err) = self.finish(exit_code, exit_signal) {
                        warn!("Failed to mark frame {} as finished. {}", self, err);
                    }
                    logger.writeln(&self.write_footer());
                    Some(exit_code)
                }
                Err(err) => {
                    let msg = format!("Frame {} failed to be spawned. {}", self.to_string(), err);
                    logger.writeln(&msg);
                    error!(msg);
                    None
                }
            }
        };
        if let Err(err) = self.clear_snapshot() {
            // Only warn if a job was actually launched
            if exit_code.is_some() {
                warn!(
                    "Failed to clear snapshot {}: {}",
                    self.snapshot_path().unwrap_or("empty_path".to_string()),
                    err
                );
            }
        };
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn run_inner(&self, logger: FrameLogger) -> Result<(i32, Option<i32>)> {
        use miette::Context;
        use nix::libc;
        use tracing::trace;

        if self.config.run_on_docker {
            return self.run_on_docker();
        }

        logger.writeln(self.write_header().as_str());

        let mut command =
            FrameCmdBuilder::new(&self.config.shell_path, self.entrypoint_file_path.clone());
        if self.config.desktop_mode {
            command.with_nice();
        }
        if let Some(cpu_list) = &self.cpu_list {
            command.with_taskset(cpu_list.clone());
        }
        let raw_stdout = Self::setup_raw_fd(&self.raw_stdout_path)?;
        let raw_stderr = Self::setup_raw_fd(&self.raw_stderr_path)?;

        let (cmd, cmd_str) = command
            .with_frame_cmd(self.request.command.clone())
            .with_exit_file(self.exit_file_path.clone())
            .build()?;
        unsafe {
            cmd.envs(&self.env_vars)
                .current_dir(&self.config.temp_path)
                .pre_exec(|| {
                    libc::setsid();
                    Ok(())
                })
                // An spawn job should be able to run independent of rqd.
                // If this process dies, the process continues to write to its assigned file
                // descriptor.
                .stdout(Stdio::from_raw_fd(raw_stdout))
                .stderr(Stdio::from_raw_fd(raw_stderr));
        }

        if self.config.run_as_user {
            cmd.uid(self.uid);
        }

        trace!("Running {}: {}", self.entrypoint_file_path, cmd_str);
        logger.writeln(format!("Running {}:", self.entrypoint_file_path).as_str());

        // Launch frame process
        let mut child = cmd.spawn().into_diagnostic().map_err(|e| {
            miette!(
                "Failed to spawn process for command '{}': {}",
                self.request.command,
                e
            )
        })?;

        // Update frame state with frame pid
        let pid = child.id();
        self.start(child.id());

        info!(
            "Frame {self} started with pid {pid}, with taskset {}",
            self.taskset()
        );

        // Make sure process has been spawned before creating a backup
        let _ = self.snapshot();

        // Spawn a new thread to follow frame logs
        let (log_pipe_handle, sender) = self.spawn_logger(logger);

        let output = child.wait();
        // Send a signal to the logger thread
        if sender.send(()).is_err() {
            warn!("Failed to notify log thread");
        }
        if let Err(_) = log_pipe_handle.join() {
            warn!("Failed to join log thread");
        }
        let output = output
            .into_diagnostic()
            .wrap_err(format!("Command for {self} didn't start!"))?;

        let (exit_code, exit_signal) = Self::interprete_output(output);

        let msg = match exit_code {
            0 => format!("Frame {}(pid={}) finished successfully", self, pid),
            _ => format!(
                "Frame {}(pid={}) finished with exit_code={} and exit_signal={}. Log: {}",
                self,
                pid,
                exit_code,
                exit_signal.unwrap_or(0),
                self.log_path,
            ),
        };
        info!(msg);

        Ok((exit_code, exit_signal))
    }

    fn interprete_output(output: ExitStatus) -> (i32, Option<i32>) {
        let mut exit_signal = output.signal();
        // If a process got terminated by a signal, set the exit_code to 1
        let mut exit_code = output.code().unwrap_or(1);

        // If the cmd wrapper interprets the signal as an output, 128 needs to be subtracted
        // from the code to recover the received signal
        if exit_code > 128 {
            exit_code = 1;
            exit_signal = Some(exit_code - 128);
        }
        (exit_code, exit_signal)
    }

    pub fn run_on_docker(&self) -> Result<(i32, Option<i32>)> {
        todo!()
    }

    #[cfg(target_os = "windows")]
    pub fn run_inner(&self, logger: FrameLogger) -> Result<(i32, Option<i32>)> {
        todo!("Windows runner needs to be implemented")
    }

    /// Spawns a new thread to pipe raw logs (stdout and stderr) into a logger
    ///
    /// # Returns:
    /// * A tuple with a handle to the spawned thread and a mpsc::Sender that will signal the thread
    ///   to end.
    ///
    /// __Attention: this thread will loop forever until signalled otherwise__
    fn spawn_logger(&self, logger: FrameLogger) -> (JoinHandle<()>, mpsc::Sender<()>) {
        let raw_stdout_path = self.raw_stdout_path.clone();
        let raw_stderr_path = self.raw_stderr_path.clone();
        // Open a oneshot channel to inform the thread it can stop reading the log
        let (sender, receiver) = mpsc::channel();
        // The logger thread streams the content of both stdout and stderr from
        // their raw file descriptors to the logger output. This allows augumenting its
        // content with timestamps for example.
        let handle = thread::spawn(move || {
            if let Err(e) =
                Self::pipe_output_to_logger(logger, &raw_stdout_path, &raw_stderr_path, receiver)
            {
                let msg = format!(
                    "Failed to follow_log: {}.\nPlease check the raw stdout and stderr:\n - {}\n - {}",
                    e, raw_stdout_path, raw_stderr_path
                );
                error!(msg);
            }
        });
        (handle, sender)
    }

    /// Recovers a frame that was previously running but RQD had to restart
    ///
    /// This function assumes the frame is already running with a valid PID.
    /// It will:
    /// 1. Write header information to the log file
    /// 2. Start following the raw stdout/stderr files
    /// 3. Wait for the process to complete
    /// 4. Read the exit status from the exit file or assume termination if not available
    ///
    /// # Returns
    /// Returns a tuple containing:
    /// - The exit code (0 for success, non-zero for failure)
    /// - The optional exit signal if the process was terminated by a signal
    ///
    /// # Errors
    /// Returns an error if the frame doesn't have a valid PID or if process monitoring fails
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn recover_inner(&self, logger: FrameLogger) -> Result<(i32, Option<i32>)> {
        logger.writeln(self.write_header().as_str());

        let pid = self.pid().ok_or(miette!(
            "Invalid state. Trying to recover a frame that hasn't started. {}",
            self
        ))?;

        // Spawn a new thread to follow frame logs
        let (log_pipe_handle, logger_signal) = self.spawn_logger(logger);

        info!("Frame {self} recovered with pid {pid}");
        self.wait()?;

        // Send a signal to the logger thread
        if logger_signal.send(()).is_err() {
            warn!("Failed to notify log thread");
        }
        if let Err(_) = log_pipe_handle.join() {
            warn!("Failed to join log thread");
        }

        info!("Frame {} finished successfully with pid={}", self, pid);

        // If a recovered frame fails to read the exit code from
        // the exit file, mark the frame as killed (SIGTERM)
        Ok(self.read_exit_file().unwrap_or((1, Some(143))))
    }

    /// Get the process ID (PID) of the running frame process
    ///
    /// # Returns
    /// - `Some(u32)` containing the process ID if the frame is running
    /// - `None` if the frame has not been started or the PID is unavailable
    ///
    /// This method safely accesses the thread-protected running state to retrieve
    /// the current PID of the frame process.
    pub(crate) fn pid(&self) -> Option<u32> {
        let state = self.state.lock().unwrap_or_else(|err| err.into_inner());
        match *state {
            FrameState::Created(_) => None,
            FrameState::Running(ref running_state) => Some(running_state.pid),
            FrameState::Finished(ref finished_state) => Some(finished_state.pid),
        }
    }

    /// Reads the exit status from the exit file written by the frame process
    ///
    /// # Returns
    /// A tuple containing:
    /// - The exit code (0 for success, non-zero for failure)
    /// - An optional signal number if the process was terminated by a signal
    ///
    /// # Details
    /// Each frame forwards its exit status to a file, which is necessary to allow
    /// recovering the status if the frame process is no longer a child of this thread.
    /// This is especially important for process recovery after RQD restarts.
    ///
    /// When a process is terminated by a signal, the exit status is calculated as:
    /// `128 + signal_number`. For example, SIGTERM (15) results in exit code 143.
    ///
    /// # Errors
    /// Returns an error if:
    /// - The exit file cannot be opened or read
    /// - The content of the exit file cannot be parsed as an integer
    pub(self) fn read_exit_file(&self) -> Result<(i32, Option<i32>)> {
        let mut file = File::open(&self.exit_file_path).map_err(|err| {
            let msg = format!(
                "Failed to open exit_file({}) when recovering frame {}. {}",
                self.exit_file_path, self, err
            );
            warn!(msg);
            miette!(msg)
        })?;
        let mut buffer = String::new();
        file.read_to_string(&mut buffer).map_err(|err| {
            let msg = format!(
                "Failed to read exit_file({}) when recovering frame {}. {}",
                self.exit_file_path, self, err
            );
            warn!(msg);
            miette!(msg)
        })?;

        let exit_code = buffer.trim().parse::<i32>().map_err(|err| {
            let msg = format!(
                "Failed to parse value ({}) exit_file({}) when recovering frame {}. {}",
                buffer, self.exit_file_path, self, err
            );
            warn!(msg);
            miette!(msg)
        })?;

        // When a process is terminated by a signal, the exit status is calculated as:
        // `128 + signal_number`
        // For example:
        // - SIGTERM (15) → exit code 143 (128+15)
        // - SIGKILL (9) → exit code 137 (128+9)
        if exit_code < 128 {
            Ok((exit_code, None))
        } else {
            Ok((1, Some(exit_code - 128)))
        }
    }

    /// Waits for a process to exit by checking its status periodically
    ///
    /// # Returns
    /// Returns `Ok(())` if the process successfully exits or is already gone.
    ///
    /// # Errors
    /// Returns an error if:
    /// - There's no valid PID for the frame
    /// - There's an error when checking the process status (not including ESRCH)
    ///
    /// # Details
    /// This function polls the process status every 500ms using the kill(2) syscall
    /// with a null signal. When the process exits, the syscall will return ESRCH
    /// (No such process) error, indicating the process has terminated.
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    pub fn wait(&self) -> Result<()> {
        use nix::sys::signal;
        use nix::unistd::Pid;

        let pid = self.pid().ok_or(miette!(
            "Failed to wait for frame. Process have never started: {}",
            self
        ))?;

        // Convert to nix Pid
        let nix_pid = Pid::from_raw(pid as i32);

        // Poll process status periodically
        loop {
            // Check if process is still running
            match signal::kill(nix_pid, None) {
                Ok(_) => {
                    // Process still running, wait a bit and check again
                    thread::sleep(Duration::from_millis(500));
                }
                Err(nix::Error::ESRCH) => {
                    // Process has exited
                    break;
                }
                Err(e) => {
                    return Err(miette!("Error checking process status: {}", e));
                }
            }
        }
        Ok(())
    }

    /// Retrieves the process ID (PID) that should be killed when terminating this frame
    ///
    /// # Returns
    /// Returns a `Result` containing the PID if the frame is in a running state
    ///
    /// # Errors
    /// Returns an error if:
    /// - The frame has not been started yet (is in Created state)
    /// - The frame has already finished (is in Finished state)
    ///
    /// # Details
    /// This method safely accesses the thread-protected state to retrieve
    /// the current PID of the running frame process. A warning is logged
    /// if the frame doesn't have an associated thread handle.
    pub fn get_pid_to_kill(&self, reason: &String) -> Result<u32> {
        let mut lock = self
            .state
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        match *lock {
            FrameState::Created(_) => Err(miette!("Frame has been created but hasn't started yet")),
            FrameState::Running(ref mut running_state) => {
                running_state.kill_reason = Some(reason.clone());
                Ok(running_state.pid)
            }
            FrameState::Finished(ref finished_state) => {
                let end_time: DateTime<Local> = finished_state.end_time.into();
                Err(miette!(
                    "Frame has already terminated at {} with exit_code={} and exit_signal={:?}",
                    end_time.format("%Y-%m-%d %H:%M:%S").to_string(),
                    finished_state.exit_code,
                    finished_state.exit_signal
                ))
            }
        }
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

    fn snapshot_path(&self) -> Result<String> {
        let pid = self.pid().ok_or_else(|| {
            warn!("Failed to snapshot frame {}. No pid available", self);
            miette!("No pid available for frame snapshot")
        })?;

        Ok(format!(
            "{}/snapshot_{}-{}-{}.bin",
            self.config.snapshots_path, self.job_id, self.frame_id, pid
        ))
    }

    /// Save a snapshot of the frame into disk to enable recovering its status in case
    /// rqd restarts.
    ///
    fn snapshot(&self) -> Result<()> {
        let snapshot_path = self.snapshot_path()?;
        let file = File::create(&snapshot_path).into_diagnostic()?;
        let writer = BufWriter::new(file);

        bincode::serialize_into(writer, self)
            .into_diagnostic()
            .map_err(|e| miette!("Failed to serialize frame snapshot: {}", e))?;
        Ok(())
    }

    fn clear_snapshot(&self) -> Result<()> {
        let snapshot_path = self.snapshot_path()?;
        fs::remove_file(snapshot_path).into_diagnostic()
    }

    /// Load a frame from a snapshot file
    ///
    /// # Parameters
    /// * `path` - The file path to the snapshot file to load
    /// * `config` - The runner configuration to use for the loaded frame
    ///
    /// # Returns
    /// Returns a `Result` containing the deserialized `RunningFrame` if successful
    ///
    /// # Errors
    /// Returns an error if:
    /// - The snapshot file cannot be opened or read
    /// - The snapshot data cannot be deserialized
    /// - The frame's process is no longer running
    /// - The snapshot doesn't contain a valid PID
    ///
    /// # Details
    /// This function loads a previously saved frame state from a snapshot file,
    /// updates it with the provided configuration, and verifies that the process
    /// is still running before returning the frame. This is primarily used for
    /// recovering frames after RQD restarts.
    ///
    /// # Known issues:
    /// This function relies on pid uniqueness, which is not ensured at the OS level.
    /// TODO: Consider discarding old snapshots, or add additional checks to ensures
    /// the snapshot is binding to the correct process
    ///
    pub fn from_snapshot(path: &str, config: RunnerConfig) -> Result<Self> {
        let file =
            File::open(path).map_err(|err| miette!("Failed to open snapshot file. {}", err))?;
        let reader = BufReader::new(file);

        let mut frame: RunningFrame = bincode::deserialize_from(reader)
            .into_diagnostic()
            .map_err(|e| miette!("Failed to deserialize frame snapshot: {}", e))?;

        // Replace snapshot config with the new config:
        frame.config = config;

        let pid = frame.pid();

        // Check if pid is still active
        match pid {
            Some(pid) => Self::is_process_running(pid).then(|| pid).ok_or(miette!(
                "Frame pid {} not found for this snapshot. {}",
                pid,
                frame.to_string()
            )),
            None => Err(miette!("Invalid snapshot. Pid not present. {}", frame)),
        }
        .map(|_| frame)
    }

    fn is_process_running(pid: u32) -> bool {
        let mut system = System::new_all();
        system.refresh_processes(
            sysinfo::ProcessesToUpdate::Some(&[Pid::from_u32(pid)]),
            true,
        );
        system.process(Pid::from_u32(pid)).is_some()
    }

    pub fn is_finished(&self) -> bool {
        let state = self.state.lock().unwrap_or_else(|err| err.into_inner());

        match *state {
            FrameState::Created(_) => false,
            FrameState::Running(_) => false,
            FrameState::Finished(ref finished_state) => {
                let thread_finished = match &finished_state.launch_thread_handle {
                    Some(handle) => handle.is_finished(),
                    None => {
                        warn!("Thread handle missing");
                        true
                    }
                };
                let pid_running = Self::is_process_running(finished_state.pid);
                thread_finished && !pid_running
            }
        }
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

    fn write_footer(&self) -> String {
        let frame_stats_lock = self
            .frame_stats
            .read()
            .unwrap_or_else(|err| err.into_inner());
        let frame_stats = frame_stats_lock.clone().unwrap_or(ProcessStats::default());
        drop(frame_stats_lock);

        let state = self.state.lock().unwrap_or_else(|err| err.into_inner());
        match *state {
            FrameState::Finished(ref finished_state) => {
                let exit_status = finished_state.exit_code;
                let exit_signal = finished_state.exit_signal.unwrap_or(0);
                let kill_message = match finished_state.exit_signal {
                    Some(_) => {
                        format!(
                            "\nkillMessage          {}\n",
                            finished_state
                                .kill_reason
                                .clone()
                                .unwrap_or("No reason defined".to_string())
                        )
                    }
                    None => "".to_string(),
                };
                let start_time = DateTime::<Local>::from(finished_state.start_time)
                    .format("%Y-%m-%d %H:%M:%S")
                    .to_string();
                let end_time = DateTime::<Local>::from(finished_state.end_time)
                    .format("%Y-%m-%d %H:%M:%S")
                    .to_string();
                let maxrss = frame_stats.max_rss;
                let max_gpu_memory = frame_stats.max_used_gpu_memory;
                let run_time = frame_stats.run_time;

                let children = frame_stats
                    .children
                    .map(|children_stats| {
                        children_stats
                            .children
                            .iter()
                            .map(|child| {
                                let child_stat = child.stat.clone().unwrap_or_default();
                                format!(
                                    r#"
____________________________________________________________________________________________________
    child_pid           {}
    cmdline             {}
    maxrss              {}
    start_time          {}"#,
                                    child_stat.pid, child.cmdline, child_stat.rss, child.start_time
                                )
                            })
                            .join("\n")
                    })
                    .unwrap_or("".to_string());

                format!(
                    r#"
====================================================================================================
Render Frame Completed
exitStatus          {exit_status}
exitSignal          {exit_signal}{kill_message}
startTime           {start_time}
endTime             {end_time}
maxrss              {maxrss}
maxUsedGpuMemory    {max_gpu_memory}
runTime             {run_time}

Processes:{children}
===================================================================================================="#
                )
            }
            _ => format!(
                r#"
====================================================================================================
Render Frame Completed
        ),
        "#
            ),
        }
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

    /// Produce a copy of this running frame in the format expected by the grpc interface
    pub fn into_running_frame_info(&self) -> Option<RunningFrameInfo> {
        let frame_stats_lock = self
            .frame_stats
            .read()
            .unwrap_or_else(|err| err.into_inner());
        // Start time defauls to 0 if a frame hasn't started
        let start_time = frame_stats_lock
            .as_ref()
            .map(|stats| stats.epoch_start_time)
            .unwrap_or(0);
        if let Some(ref stats) = *frame_stats_lock {
            Some(RunningFrameInfo {
                resource_id: self.request.resource_id.clone(),
                job_id: self.request.job_id.clone(),
                job_name: self.request.job_name.clone(),
                frame_id: self.request.frame_id.clone(),
                frame_name: self.request.frame_name.clone(),
                layer_id: self.request.layer_id.clone(),
                num_cores: self.request.num_cores,
                start_time: start_time as i64,
                max_rss: stats.max_rss as i64,
                rss: stats.rss as i64,
                max_vsize: stats.max_vsize as i64,
                vsize: stats.vsize as i64,
                attributes: self.request.attributes.clone(),
                llu_time: stats.llu_time as i64,
                num_gpus: self.request.num_gpus,
                max_used_gpu_memory: stats.max_used_gpu_memory as i64,
                used_gpu_memory: stats.used_gpu_memory as i64,
                // Not recording proc children for now
                children: None,
            })
        } else {
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use opencue_proto::rqd::{RunFrame, run_frame::UidOptional};
    use std::collections::HashMap;
    use std::sync::Arc;
    use uuid::Uuid;

    use crate::config::config::Config;
    use crate::frame::logging::FrameLoggerT;
    use crate::frame::logging::TestLogger;

    use super::RunningFrame;

    fn create_running_frame(
        command: &str,
        num_cores: u32,
        uid: u32,
        environment: HashMap<String, String>,
    ) -> RunningFrame {
        let frame_id = Uuid::new_v4().to_string();
        let general_config = Config::default();
        general_config.setup().unwrap();
        let mut config = general_config.runner;
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
        assert_eq!((0, None), status.unwrap());
        assert_eq!("stderr test", logger.pop().unwrap());
        assert_eq!("stdout test", logger.pop().unwrap());

        // Assert the output on the exit_file is the same
        let status = running_frame.read_exit_file();
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
    }

    #[test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn test_run_failed() {
        let mut env = HashMap::with_capacity(1);
        env.insert("TEST_ENV".to_string(), "test".to_string());
        let running_frame = create_running_frame(r#"echo "stdout $TEST_ENV" && exit 1"#, 1, 1, env);

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>);
        assert!(status.is_ok());
        assert_eq!((1, None), status.unwrap());
        assert_eq!("stdout test", logger.pop().unwrap());
    }

    #[test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn test_run_multiline_stdout() {
        let running_frame = create_running_frame(
            r#"echo "line1" && echo "line2" && echo "line3""#,
            1,
            1,
            HashMap::new(),
        );

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>);
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
        assert_eq!("line3", logger.pop().unwrap());
        assert_eq!("line2", logger.pop().unwrap());
        assert_eq!("line1", logger.pop().unwrap());

        // Assert the output on the exit_file is the same
        let status = running_frame.read_exit_file();
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
    }

    #[test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn test_run_env_variables() {
        let mut env = HashMap::new();
        env.insert("VAR1".to_string(), "value1".to_string());
        env.insert("VAR2".to_string(), "value2".to_string());

        let running_frame = create_running_frame(r#"echo "$VAR1 $VAR2""#, 1, 1, env);

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>);
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
        assert_eq!("value1 value2", logger.pop().unwrap());

        // Assert the output on the exit_file is the same
        let status = running_frame.read_exit_file();
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
    }

    #[test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn test_run_command_not_found() {
        let running_frame =
            create_running_frame(r#"command_that_does_not_exist"#, 1, 1, HashMap::new());

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>);
        assert!(status.is_ok());
        // The exact exit code might vary by system, but it should be non-zero
        assert_ne!((0, None), status.unwrap());

        // Assert the output on the exit_file is the same
        let status = running_frame.read_exit_file();
        assert!(status.is_ok());
        assert_ne!((0, None), status.unwrap());
    }

    #[test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn test_run_sleep_command() {
        use std::time::{Duration, Instant};

        let running_frame =
            create_running_frame(r#"sleep 0.5 && echo "Done sleeping""#, 1, 1, HashMap::new());

        let logger = Arc::new(TestLogger::init());
        let start = Instant::now();
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>);
        let elapsed = start.elapsed();

        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
        assert!(
            elapsed >= Duration::from_millis(500),
            "Command didn't run for expected duration"
        );
        assert_eq!("Done sleeping", logger.pop().unwrap());

        // Assert the output on the exit_file is the same
        let status = running_frame.read_exit_file();
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
    }

    #[test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn test_run_interleaved_stdout_stderr() {
        let running_frame = create_running_frame(
            r#"echo "stdout1" && echo "stderr1" >&2 && echo "stdout2" && echo "stderr2" >&2"#,
            1,
            1,
            HashMap::new(),
        );

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>);
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());

        let logs = logger.all();
        assert!(logs.contains(&"stdout1".to_string()));
        assert!(logs.contains(&"stderr1".to_string()));
        assert!(logs.contains(&"stdout2".to_string()));
        assert!(logs.contains(&"stderr2".to_string()));

        // Assert the output on the exit_file is the same
        let status = running_frame.read_exit_file();
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
    }
}
