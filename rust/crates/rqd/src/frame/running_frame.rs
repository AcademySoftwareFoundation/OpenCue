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

use opencue_proto::job::LayerSetTimeoutRequest;
use std::cmp;
#[cfg(unix)]
use std::os::fd::IntoRawFd;
#[cfg(unix)]
use std::os::fd::{FromRawFd, RawFd};
#[cfg(unix)]
use std::os::unix::process::ExitStatusExt;
use std::time::SystemTime;
use std::{
    collections::HashMap,
    env,
    fmt::Display,
    path::Path,
    process::ExitStatus,
    sync::atomic::{AtomicBool, Ordering},
    sync::{Arc, RwLock},
};
use std::{process::Stdio, thread};
use tokio::time::{self, Duration};

use bytesize::KIB;
use chrono::{DateTime, Local};
use itertools::Itertools;
use tokio::fs::File;
use tokio::io::AsyncReadExt;
use tokio::{io::AsyncBufReadExt, task::JoinHandle};
use tracing::{error, info, trace, warn};

use crate::system::OOM_REASON_MSG;
use crate::{
    frame::frame_cmd::FrameCmdBuilder,
    system::manager::{HostMemSnapshot, PeerMem, ProcessStats},
};

use serde::{Deserialize, Serialize};
use sysinfo::{Pid, System};

use miette::{miette, Context, IntoDiagnostic, Result};
use opencue_proto::{report::RunningFrameInfo, rqd::RunFrame};
use uuid::Uuid;

use super::logging::{FrameLogger, FrameLoggerBuilder};
use crate::config::{CompiledExitStatusRule, RunnerConfig};

/// Maximum number of bytes read from the tail of a frame log when scanning for
/// exit-status-override patterns. Bounds the IO regardless of the configured line count so a
/// pathologically large log can never be read in full.
const LOG_SCAN_MAX_BYTES: u64 = 1024 * 1024; // 1 MiB

/// Granularity of the backward tail read in [`read_last_lines`]. The tail is read in chunks of
/// this size, newest-first, stopping as soon as enough line breaks have been seen — so a typical
/// scan touches only one chunk instead of the full [`LOG_SCAN_MAX_BYTES`] cap. Sized so the
/// default 50-line tail of a frame log (~4 KiB, including the multi-line process footer) fits in
/// a single read with headroom.
const LOG_SCAN_CHUNK_BYTES: u64 = 16 * 1024; // 16 KiB

/// Returns the `(name, exit_status)` of the first rule that matches anywhere in `log_tail`.
fn match_exit_status_rules(
    log_tail: &str,
    rules: &[CompiledExitStatusRule],
) -> Option<(String, i32)> {
    rules
        .iter()
        .find(|rule| rule.regex.is_match(log_tail))
        .map(|rule| (rule.name.clone(), rule.exit_status))
}

/// Reads up to `max_lines` from the end of `path`, reading at most [`LOG_SCAN_MAX_BYTES`] from
/// the tail. When the byte cap truncates mid-line, the leading partial line is dropped so a
/// rule can't match against half a line. (Consequence of that cap: a single trailing line
/// longer than [`LOG_SCAN_MAX_BYTES`] is dropped entirely and won't be scanned — acceptable,
/// since the patterns this feature targets are short diagnostic messages.)
async fn read_last_lines(path: &str, max_lines: usize) -> Result<Vec<String>> {
    use tokio::io::{AsyncReadExt, AsyncSeekExt, SeekFrom};

    let mut file = tokio::fs::File::open(path)
        .await
        .into_diagnostic()
        .wrap_err_with(|| format!("failed to open {path} for exit-status scan"))?;
    let size = file.metadata().await.into_diagnostic()?.len();

    // Read the tail backward in fixed-size chunks, stopping once we've seen one more newline than
    // requested: `max_lines` lines are delimited by `max_lines` newlines, plus one extra whose
    // trailing partial line is dropped below. `floor` keeps the total read within the byte cap.
    let want_newlines = max_lines + 1;
    let floor = size.saturating_sub(LOG_SCAN_MAX_BYTES);
    let mut buf: Vec<u8> = Vec::new();
    let mut newlines = 0usize;
    let mut pos = size;
    while pos > floor {
        let chunk = LOG_SCAN_CHUNK_BYTES.min(pos - floor);
        let chunk_start = pos - chunk;
        file.seek(SeekFrom::Start(chunk_start))
            .await
            .into_diagnostic()?;
        let mut chunk_buf = vec![0u8; chunk as usize];
        file.read_exact(&mut chunk_buf).await.into_diagnostic()?;
        newlines += chunk_buf.iter().filter(|&&b| b == b'\n').count();
        // Prepend this earlier chunk in front of the tail collected so far.
        chunk_buf.extend_from_slice(&buf);
        buf = chunk_buf;
        pos = chunk_start;
        if newlines >= want_newlines {
            break;
        }
    }
    // `pos == 0` means we reached the real start of the file, so the first line is complete and
    // must be kept. Otherwise the read began mid-file and the leading line is possibly truncated.
    let at_file_start = pos == 0;

    let text = String::from_utf8_lossy(&buf);
    let mut lines = text.lines();
    if !at_file_start {
        lines.next();
    }
    let collected: Vec<String> = lines.map(|line| line.to_string()).collect();
    let begin = collected.len().saturating_sub(max_lines);
    Ok(collected[begin..].to_vec())
}

/// Wrapper around protobuf message RunningFrameInfo
#[derive(Serialize, Deserialize)]
pub struct RunningFrame {
    pub request: RunFrame,
    pub job_id: Uuid,
    pub frame_id: Uuid,
    pub layer_id: Uuid,
    frame_stats: RwLock<ProcessStats>,
    pub log_path: String,
    pub(super) uid: u32,
    pub(super) gid: u32,
    // The runner config is host-level policy, not per-frame state, and is always replaced from
    // the live config on recovery (`from_snapshot`). Keeping it out of the snapshot avoids
    // bloating every snapshot and, because bincode is positional, stops future additions to
    // RunnerConfig from breaking the layout of previously written snapshots.
    #[serde(skip)]
    pub(super) config: RunnerConfig,
    pub thread_ids: Option<Vec<u32>>,
    pub gpu_list: Option<Vec<u32>>,
    pub(super) env_vars: HashMap<String, String>,
    pub hostname: String,
    raw_stdout_path: String,
    raw_stderr_path: String,
    pub exit_file_path: String,
    pub entrypoint_file_path: String,
    state: RwLock<FrameState>,
    dangling_state_registed_at: RwLock<Option<SystemTime>>,
    #[serde(skip_serializing)]
    #[serde(skip_deserializing)]
    stats_frozen: AtomicBool,
    /// Latest host-wide memory distribution, refreshed each monitor cycle. Read by the log
    /// footer of a failing frame to expose potential memory starvation from co-tenants.
    /// Transient host state, never persisted in frame snapshots.
    #[serde(skip_serializing)]
    #[serde(skip_deserializing)]
    latest_host_mem_snapshot: RwLock<Option<Arc<HostMemSnapshot>>>,
}

#[derive(Serialize, Deserialize, Debug)]
pub enum FrameState {
    Created(CreatedState),
    Running(RunningState),
    Finished(FinishedState),
    FailedBeforeStart,
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
    pub pid: u32,
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
        hyperthreading_multiplier: u32,
    ) -> Self {
        let job_id = request.job_id();
        let frame_id = request.frame_id();
        let layer_id = request.layer_id();
        // Use a random id as part of the file prefix to prevent multiple frames from
        // sharing the same control files
        let random_id = Uuid::new_v4();
        let log_path = Path::new(&request.log_dir)
            .join(format!("{}.{}.rqlog", request.job_name, request.frame_name))
            .to_string_lossy()
            .to_string();
        let frame_file_prefix = format!("{}.{}", request.frame_name, &random_id.to_string()[0..7]);
        let raw_stdout_path = std::path::Path::new(&config.temp_path)
            .join(format!("{}.raw_stdout.rqlog", frame_file_prefix))
            .to_string_lossy()
            .to_string();
        let raw_stderr_path = std::path::Path::new(&config.temp_path)
            .join(format!("{}.raw_stderr.rqlog", frame_file_prefix))
            .to_string_lossy()
            .to_string();
        let exit_file_path = std::path::Path::new(&config.temp_path)
            .join(format!("{}.exit_status", frame_file_prefix))
            .to_string_lossy()
            .to_string();
        let entrypoint_file_path = std::path::Path::new(&config.temp_path)
            .join(format!(
                "{}.{}",
                frame_file_prefix,
                Self::entrypoint_extension()
            ))
            .to_string_lossy()
            .to_string();
        let env_vars = Self::setup_env_vars(
            &config,
            &request,
            hostname.clone(),
            log_path.clone(),
            cpu_list.as_ref().map(|l| l.len() as i32),
            hyperthreading_multiplier,
        );

        // Protection against frames that want to become root
        let gid = if request.gid <= 0 {
            config.default_gid
        } else {
            request.gid as u32
        };

        RunningFrame {
            request,
            job_id,
            frame_id,
            layer_id,
            frame_stats: RwLock::new(ProcessStats::default()),
            log_path,
            uid,
            gid,
            config,
            thread_ids: cpu_list,
            gpu_list,
            env_vars,
            hostname,
            raw_stdout_path,
            raw_stderr_path,
            exit_file_path,
            entrypoint_file_path,
            state: RwLock::new(FrameState::Created(CreatedState {
                launch_thread_handle: None,
            })),
            dangling_state_registed_at: RwLock::new(None),
            stats_frozen: AtomicBool::new(false),
            latest_host_mem_snapshot: RwLock::new(None),
        }
    }

    #[cfg(test)]
    pub fn init_started_for_test(
        request: RunFrame,
        uid: u32,
        config: RunnerConfig,
        cpu_list: Option<Vec<u32>>,
        gpu_list: Option<Vec<u32>>,
        hostname: String,
        duration: Duration,
    ) -> Self {
        let instance = Self::init(request, uid, config, cpu_list, gpu_list, hostname, 1);

        {
            let mut state = instance
                .state
                .write()
                .unwrap_or_else(|err| err.into_inner());

            match &mut *state {
                FrameState::Created(created_state) => {
                    *state = FrameState::Running(RunningState {
                        pid: 999, // Dummy pid
                        start_time: SystemTime::now()
                            .checked_sub(duration)
                            .unwrap_or(SystemTime::now()),
                        launch_thread_handle: created_state.launch_thread_handle.take(),
                        kill_reason: None,
                    });
                }
                FrameState::Running(running_state) => warn!(
                    "Invalid State. Frame {} has already started {:?}",
                    instance, running_state
                ),
                FrameState::Finished(_) => {
                    warn!("Invalid States. Frame {} has already finished", instance)
                }
                FrameState::FailedBeforeStart => {
                    warn!("Invalid States. Frame {} failed before starting", instance)
                }
            }
        } // state is dropped here

        instance
    }

    pub fn update_frame_stats(&self, proc_stats: ProcessStats) {
        // Don't update stats if they've been frozen (e.g., when frame is being killed for OOM)
        if self.stats_frozen.load(Ordering::SeqCst) {
            return;
        }

        // Make sure
        self.unmark_dangling();

        self.frame_stats
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .update(proc_stats);
    }

    pub fn get_duration(&self) -> Duration {
        let state = self.state.read().unwrap_or_else(|err| err.into_inner());

        match *state {
            FrameState::Created(_) => Duration::ZERO,
            FrameState::Running(ref r) => r.start_time.elapsed().unwrap_or(Duration::ZERO),
            FrameState::Finished(ref r) => r.start_time.elapsed().unwrap_or(Duration::ZERO),
            FrameState::FailedBeforeStart => Duration::ZERO,
        }
    }

    pub fn get_state_copy(&self) -> FrameState {
        let state = self.state.read().unwrap_or_else(|err| err.into_inner());

        match *state {
            FrameState::Created(_) => FrameState::Created(CreatedState {
                launch_thread_handle: None,
            }),
            FrameState::Running(ref r) => FrameState::Running(RunningState {
                pid: r.pid,
                start_time: r.start_time,
                launch_thread_handle: None,
                kill_reason: r.kill_reason.clone(),
            }),
            FrameState::Finished(ref finished_state) => FrameState::Finished(FinishedState {
                pid: finished_state.pid,
                start_time: finished_state.start_time,
                end_time: finished_state.end_time,
                exit_code: finished_state.exit_code,
                exit_signal: finished_state.exit_signal,
                kill_reason: None,
            }),
            FrameState::FailedBeforeStart => FrameState::FailedBeforeStart,
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
        let mut state = self.state.write().unwrap_or_else(|err| err.into_inner());
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
            FrameState::FailedBeforeStart => {
                Err(miette!("Invalid State. Frame failed before starting"))
            }
        }
    }

    /// Updates the exit code and signal for this frame
    ///
    /// # Parameters
    /// * `exit_code` - The exit code from the frame process (0 for success, non-zero for failure)
    /// * `exit_signal` - Optional signal number that terminated the process (e.g., 15 for SIGTERM, 9 for SIGKILL)
    /// * `external_kill_reason` - Optional message to explain why the frame was marked as failed
    ///
    /// This method updates the internal finished state with the termination information,
    /// which can later be used to determine if the frame succeeded or failed.
    pub fn finish(
        &self,
        exit_code: i32,
        exit_signal: Option<i32>,
        external_kill_reason: Option<String>,
    ) -> Result<()> {
        let mut state = self.state.write().unwrap_or_else(|err| err.into_inner());
        match &mut *state {
            FrameState::Created(_) => Err(miette!("Invalid State. Frame {} hasn't started", self)),
            FrameState::Running(running_state) => {
                // Replace exit_signal to memory signal if kill_reason matches the memory check message
                let modified_exit_signal = match &running_state.kill_reason {
                    Some(reason) if reason.contains(OOM_REASON_MSG) => {
                        // 33 is the error signal hardcoded on Cuebot for memory issues
                        // (See Dispatcher.java:EXIT_STATUS_MEMORY_FAILURE)
                        Some(33)
                    }
                    _ => exit_signal,
                };

                // Create a new FinishedState with the current running state values
                let finished_state = FinishedState {
                    pid: running_state.pid,
                    start_time: running_state.start_time,
                    end_time: SystemTime::now(),
                    exit_code,
                    exit_signal: modified_exit_signal,
                    kill_reason: running_state.kill_reason.clone().or(external_kill_reason),
                };

                // Replace state with the new FinishedState
                *state = FrameState::Finished(finished_state);
                Ok(())
            }
            FrameState::Finished(_) => Err(miette!(
                "Invalid State. Frame {} has already finished",
                self
            )),
            FrameState::FailedBeforeStart => Err(miette!(
                "Invalid State. Frame {} Failed before starting",
                self
            )),
        }
    }

    pub fn fail_before_start(&self) -> Result<()> {
        let mut state = self.state.write().unwrap_or_else(|err| err.into_inner());
        match &mut *state {
            FrameState::Created(_) => {
                *state = FrameState::FailedBeforeStart;
                Ok(())
            }
            FrameState::Running(_) => {
                Err(miette!("Invalid State. Frame {} has already started", self))
            }
            FrameState::Finished(_) => Err(miette!(
                "Invalid State. Frame {} has already finished",
                self
            )),
            FrameState::FailedBeforeStart => Err(miette!(
                "Invalid State. Frame {} Failed before starting",
                self
            )),
        }
    }

    /// Transition the frame state from Created to Running.
    ///
    /// If the frame has already started or finished, log the error and don't change the status.
    /// Returning an error is pointless as we want the frame that trigger this transition to finish
    /// regardless
    pub(super) fn start(&self, pid: u32) {
        let mut state = self.state.write().unwrap_or_else(|err| err.into_inner());

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
            FrameState::FailedBeforeStart => {
                warn!("Invalid States. Frame {} failed before starting", self)
            }
        }
    }

    fn setup_env_vars(
        config: &RunnerConfig,
        request: &RunFrame,
        hostname: String,
        log_path: String,
        affinity_thread_count: Option<i32>,
        hyperthreading_multiplier: u32,
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

        // CUE_THREADS should be the max between what the server requested and
        // what was actually assigned
        let cue_threads_from_server = env_vars
            .remove("CUE_THREADS")
            .and_then(|thread_count_str| thread_count_str.parse().ok())
            .unwrap_or(request.num_cores);
        let assigned = affinity_thread_count.unwrap_or(0);
        let cue_threads = cmp::max(cue_threads_from_server, assigned);
        env_vars.insert("CUE_THREADS".to_string(), cue_threads.to_string());

        // When a frame has CPU affinity, set CUE_HT so scripts/renderers
        // know whether hyperthreading is enabled
        if affinity_thread_count.is_some() {
            env_vars.insert(
                "CUE_HT".to_string(),
                if hyperthreading_multiplier > 1 {
                    "True"
                } else {
                    "False"
                }
                .to_string(),
            );
        }

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

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn entrypoint_extension() -> &'static str {
        "sh"
    }

    #[cfg(target_os = "windows")]
    fn entrypoint_extension() -> &'static str {
        "bat"
    }

    /// Returns the kill reason if RQD has requested this (still-running) frame be killed.
    fn kill_reason(&self) -> Option<String> {
        let state = self.state.read().unwrap_or_else(|err| err.into_inner());
        match &*state {
            FrameState::Running(running_state) => running_state.kill_reason.clone(),
            _ => None,
        }
    }

    /// Scans the tail of the frame log for configured `log_exit_status_rules` and returns an
    /// override exit status when one matches.
    ///
    /// Only failed frames are scanned (`exit_code != 0`), so a successful frame is never
    /// reclassified. Any error like a missing/unreadable log, a Loki-only frame with no local
    /// log file is treated as "no override" and never blocks or fails frame completion.
    ///
    /// On a match returns the matching rule's name alongside the override status, so the caller
    /// can record the reclassification in the frame log for artists debugging the frame.
    pub(super) async fn scan_log_for_exit_status_override(
        &self,
        exit_code: i32,
    ) -> Option<(String, i32)> {
        // A successful frame keeps its status; only failures are reinterpreted.
        if exit_code == 0 {
            return None;
        }
        // Read the rules through the live cell rather than this frame's frozen raw config, so
        // rules added by a config reload apply to frames that were already running when the
        // reload happened.
        let rule_set = self.config.compiled_exit_status_rules();
        if rule_set.rules.is_empty() || rule_set.scan_last_lines == 0 {
            return None;
        }
        // If RQD itself killed this frame (OOM, NIMBY, timeout, manual kill), that reason is
        // authoritative and drives its own retry semantics (e.g. OOM -> exit_signal 33). Don't
        // let an incidental log-pattern match reclassify it and hide why the frame really died.
        if self.kill_reason().is_some() {
            return None;
        }
        // Loki-backed frames don't write a local log file, so there is nothing to scan.
        if !self.request.loki_url.is_empty() {
            return None;
        }

        let lines = match read_last_lines(&self.log_path, rule_set.scan_last_lines).await {
            Ok(lines) => lines,
            Err(err) => {
                warn!(
                    "Frame {}: skipping exit-status log scan, could not read {}: {}",
                    self, self.log_path, err
                );
                return None;
            }
        };

        let log_tail = lines.join("\n");
        match match_exit_status_rules(&log_tail, &rule_set.rules) {
            Some((name, exit_status)) => {
                info!(
                    "Frame {}: log matched rule '{}'; overriding exit status {} -> {}",
                    self, name, exit_code, exit_status
                );
                Some((name, exit_status))
            }
            None => None,
        }
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
    pub async fn run(&self, recover_mode: bool) {
        let logger_base = FrameLoggerBuilder::from_cuebot(
            self.request.clone(),
            self.log_path.clone(),
            self.config.clone(),
            self.config.run_as_user.then_some((self.uid, self.gid)),
        );
        if let Err(err) = logger_base {
            error!("Failed to create log stream for {}: {}", self.log_path, err);
            if let Err(err) = self.fail_before_start() {
                error!("Failed to update failed status for {}: {}", self, err);
            };
            return;
        }
        let logger = Arc::new(logger_base.unwrap());

        let output = if recover_mode {
            self.recover_inner(Arc::clone(&logger)).await
        } else {
            self.run_inner(Arc::clone(&logger)).await
        };
        let was_spawned = match output {
            Ok((exit_code, exit_signal)) => {
                // Reclassify known failures (e.g. license shortages) before persisting the
                // finished state, so both the footer and the report to Cuebot see the override.
                let exit_code = match self.scan_log_for_exit_status_override(exit_code).await {
                    Some((name, override_code)) => {
                        // Record the reclassification in the frame log itself; otherwise the
                        // footer would show only the overridden status and the original exit
                        // code the process actually returned would appear nowhere artists look.
                        logger.writeln(&format!(
                            "Exit status {exit_code} overridden to {override_code} by rule '{name}'"
                        ));
                        override_code
                    }
                    None => exit_code,
                };
                if let Err(err) = self.finish(exit_code, exit_signal, None) {
                    error!("Failed to mark frame {} as finished. {}", self, err);
                }
                logger.writeln(&self.write_footer());
                true
            }
            Err(err) => {
                let msg = format!("Frame {} failed to be spawned. {}", self, err);
                logger.writeln(&msg);
                error!(msg);
                if let Err(err) = self.fail_before_start() {
                    error!("Failed to mark frame {} as finished. {}", self, err);
                }
                false
            }
        };
        if let Err(err) = self.clear_snapshot().await {
            // Only warn if a job was actually launched
            if was_spawned {
                warn!(
                    "Failed to clear snapshot {}: {}",
                    self.snapshot_path().unwrap_or("empty_path".to_string()),
                    err
                );
            }
        };
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    async fn run_inner(&self, logger: FrameLogger) -> Result<(i32, Option<i32>)> {
        use nix::libc;

        logger.writeln(self.write_header().as_str());

        let mut command =
            FrameCmdBuilder::new(&self.config.shell_path, self.entrypoint_file_path.clone());
        if self.config.desktop_mode {
            command.with_nice();
        }
        if let Some(cpu_list) = &self.thread_ids {
            command.with_taskset(cpu_list.clone());
        }
        let raw_stdout = Self::setup_raw_fd(&self.raw_stdout_path).await?;
        let raw_stderr = Self::setup_raw_fd(&self.raw_stderr_path).await?;

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
            cmd.gid(self.gid);
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
        let pid = child.id().ok_or(miette!(
            "Failed to get process ID after spawn - \
            process may have failed to start or already finished"
        ))?;
        self.start(pid);

        info!(
            "Frame {self} started with pid {pid}, with taskset {}",
            self.taskset()
        );

        // Make sure process has been spawned before creating a backup
        let _ = self.create_snapshot().await;

        // Spawn a new thread to follow frame logs
        let (log_pipe_handle, sender) = self.spawn_logger(logger).await;

        let output = child.wait().await;
        // Send a signal to the logger thread
        if sender.send(()).await.is_err() {
            warn!("Failed to notify log thread");
        }
        if let Err(err) = log_pipe_handle.await {
            warn!("Failed to join log thread. {}", err);
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

    #[cfg(unix)]
    fn interprete_output(exit_status: ExitStatus) -> (i32, Option<i32>) {
        let mut exit_signal = exit_status.signal();
        let mut exit_code = exit_status.code().unwrap_or(1);

        // If the cmd wrapper interprets the signal as an output, 128 needs to be subtracted
        // from the code to recover the received signal
        if exit_code > 128 {
            exit_signal = Some(exit_code - 128);
            exit_code = 1;
        }
        (exit_code, exit_signal)
    }

    #[cfg(windows)]
    fn interprete_output(exit_status: ExitStatus) -> (i32, Option<i32>) {
        let exit_code = exit_status.code().unwrap_or(1);
        (exit_code, None)
    }

    #[cfg(target_os = "windows")]
    pub async fn run_inner(&self, logger: FrameLogger) -> Result<(i32, Option<i32>)> {
        logger.writeln(self.write_header().as_str());

        let mut command =
            FrameCmdBuilder::new(&self.config.shell_path, self.entrypoint_file_path.clone());
        if self.config.run_as_user {
            return Err(miette!(
                "`runner.run_as_user` is not supported on Windows yet"
            ));
        }
        if self.config.desktop_mode {
            command.with_nice();
        }
        if let Some(cpu_list) = &self.thread_ids {
            command.with_taskset(cpu_list.clone());
        }

        let raw_stdout = Self::setup_raw_file(&self.raw_stdout_path).await?;
        let raw_stderr = Self::setup_raw_file(&self.raw_stderr_path).await?;

        let (cmd, cmd_str) = command
            .with_frame_cmd(self.request.command.clone())
            .with_exit_file(self.exit_file_path.clone())
            .build()?;

        cmd.envs(&self.env_vars)
            .current_dir(&self.config.temp_path)
            .stdout(Stdio::from(raw_stdout))
            .stderr(Stdio::from(raw_stderr));
        trace!("Running {}: {}", self.entrypoint_file_path, cmd_str);
        logger.writeln(format!("Running {}:", self.entrypoint_file_path).as_str());

        let mut child = cmd.spawn().into_diagnostic().map_err(|e| {
            miette!(
                "Failed to spawn process for command '{}': {}",
                self.request.command,
                e
            )
        })?;

        let pid = child.id().ok_or(miette!(
            "Failed to get process ID after spawn - \
            process may have failed to start or already finished"
        ))?;
        self.start(pid);

        info!("Frame {self} started with pid {pid}");

        let _ = self.create_snapshot().await;

        let (log_pipe_handle, sender) = self.spawn_logger(logger).await;

        let output = child.wait().await;
        if sender.send(()).await.is_err() {
            warn!("Failed to notify log thread");
        }
        if let Err(err) = log_pipe_handle.await {
            warn!("Failed to join log thread. {}", err);
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

    /// Spawns a new thread to pipe raw logs (stdout and stderr) into a logger
    ///
    /// # Returns:
    /// * A tuple with a handle to the spawned thread and a mpsc::Sender that will signal the thread
    ///   to end.
    ///
    /// __Attention: this thread will loop forever until signalled otherwise__
    async fn spawn_logger(
        &self,
        logger: FrameLogger,
    ) -> (JoinHandle<Result<()>>, tokio::sync::mpsc::Sender<()>) {
        let raw_stdout_path = self.raw_stdout_path.clone();
        let raw_stderr_path = self.raw_stderr_path.clone();

        // Open a oneshot channel to inform the thread it can stop reading the log
        let (sender, receiver) = tokio::sync::mpsc::channel(1);
        // The logger thread streams the content of both stdout and stderr from
        // their raw file descriptors to the logger output. This allows augumenting its
        // content with timestamps for example.
        let handle = tokio::spawn(Self::pipe_output_to_logger(
            logger,
            raw_stdout_path,
            raw_stderr_path,
            receiver,
        ));
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
    pub(super) async fn recover_inner(&self, logger: FrameLogger) -> Result<(i32, Option<i32>)> {
        logger.writeln(self.write_header().as_str());

        let pid = self.pid().ok_or(miette!(
            "Invalid state. Trying to recover a frame that hasn't started. {}",
            self
        ))?;

        // Spawn a new thread to follow frame logs
        let (log_pipe_handle, logger_signal) = self.spawn_logger(logger).await;

        info!("Frame {self} recovered with pid {pid}");
        self.wait()?;

        // Send a signal to the logger thread
        if logger_signal.send(()).await.is_err() {
            warn!("Failed to notify log thread");
        }
        if log_pipe_handle.await.is_err() {
            warn!("Failed to join log thread");
        }

        info!("Frame {} finished successfully with pid={}", self, pid);

        #[cfg(any(target_os = "linux", target_os = "macos"))]
        {
            // If a recovered frame fails to read the exit code from
            // the exit file, mark the frame as killed (SIGTERM)
            Ok(self.read_exit_file().await.unwrap_or((1, Some(143))))
        }
        #[cfg(target_os = "windows")]
        {
            Ok(self.read_exit_file().await.unwrap_or((1, None)))
        }
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
        let state = self.state.read().unwrap_or_else(|err| err.into_inner());
        match *state {
            FrameState::Created(_) => None,
            FrameState::Running(ref running_state) => Some(running_state.pid),
            FrameState::Finished(ref finished_state) => Some(finished_state.pid),
            FrameState::FailedBeforeStart => None,
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
    pub(self) async fn read_exit_file(&self) -> Result<(i32, Option<i32>)> {
        let mut file = File::open(&self.exit_file_path).await.map_err(|err| {
            let msg = format!(
                "Failed to open exit_file({}) when recovering frame {}. {}",
                self.exit_file_path, self, err
            );
            warn!(msg);
            miette!(msg)
        })?;
        let mut buffer = String::new();
        file.read_to_string(&mut buffer).await.map_err(|err| {
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

        #[cfg(unix)]
        {
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
        #[cfg(windows)]
        {
            Ok((exit_code, None))
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
                    thread::sleep(Duration::from_millis(1500));
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

    #[cfg(target_os = "windows")]
    pub fn wait(&self) -> Result<()> {
        let pid = self.pid().ok_or(miette!(
            "Failed to wait for frame. Process have never started: {}",
            self
        ))?;

        let mut sysinfo = System::new();
        loop {
            sysinfo.refresh_processes(
                sysinfo::ProcessesToUpdate::Some(&[Pid::from_u32(pid)]),
                true,
            );
            if sysinfo.process(Pid::from_u32(pid)).is_none() {
                break;
            }
            thread::sleep(Duration::from_millis(1500));
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
    pub fn get_pid_to_kill(&self, reason: &str) -> Result<u32> {
        let mut lock = self
            .state
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        match *lock {
            FrameState::Created(_) => Err(miette!("Frame has been created but hasn't started yet")),
            FrameState::Running(ref mut running_state) => {
                running_state.kill_reason = Some(reason.to_owned());
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
            FrameState::FailedBeforeStart => {
                Err(miette!("Frame has been created and failed before starting"))
            }
        }
    }

    #[cfg(unix)]
    async fn setup_raw_fd(path: &str) -> Result<RawFd> {
        let file = tokio::fs::OpenOptions::new()
            .create(true)
            .write(true)
            .append(true)
            .open(path)
            .await
            .into_diagnostic()?;

        Ok(file.into_std().await.into_raw_fd())
    }

    #[cfg(windows)]
    async fn setup_raw_file(path: &str) -> Result<std::fs::File> {
        let file = tokio::fs::OpenOptions::new()
            .create(true)
            .write(true)
            .append(true)
            .open(path)
            .await
            .into_diagnostic()?;

        Ok(file.into_std().await)
    }

    async fn pipe_output_to_logger(
        logger: FrameLogger,
        raw_stdout_path: String,
        raw_stderr_path: String,
        mut stop_flag: tokio::sync::mpsc::Receiver<()>,
    ) -> Result<()> {
        let mut stdout_position: u64 = 0;
        let mut stderr_position: u64 = 0;
        let mut last_stdout_refresh = SystemTime::now();
        let mut last_stderr_refresh = SystemTime::now();

        // Refresh readers every 5 seconds to catch new data after EOF
        let refresh_interval = Duration::from_secs(5);

        let mut stdout_interval = time::interval(Duration::from_millis(300));
        let mut stderr_interval = time::interval(Duration::from_millis(500));

        loop {
            tokio::select! {
                _ = stdout_interval.tick() => {
                    let now = SystemTime::now();
                    let should_refresh = now.duration_since(last_stdout_refresh)
                        .unwrap_or(Duration::ZERO) >= refresh_interval;

                    stdout_position = Self::read_log_lines(
                        &raw_stdout_path,
                        stdout_position,
                        &logger,
                        should_refresh,
                    ).await.unwrap_or(stdout_position);

                    if should_refresh {
                        last_stdout_refresh = now;
                    }
                }
                _ = stderr_interval.tick() => {
                    let now = SystemTime::now();
                    let should_refresh = now.duration_since(last_stderr_refresh)
                        .unwrap_or(Duration::ZERO) >= refresh_interval;

                    stderr_position = Self::read_log_lines(
                        &raw_stderr_path,
                        stderr_position,
                        &logger,
                        should_refresh,
                    ).await.unwrap_or(stderr_position);

                    if should_refresh {
                        last_stderr_refresh = now;
                    }
                }
                _ = stop_flag.recv() => {
                    // Final drain of both log files
                    let _ = Self::read_log_lines(&raw_stdout_path, stdout_position, &logger, true).await;
                    let _ = Self::read_log_lines(&raw_stderr_path, stderr_position, &logger, true).await;

                    // Remove temporary files
                    let _ = tokio::fs::remove_file(raw_stdout_path).await;
                    let _ = tokio::fs::remove_file(raw_stderr_path).await;
                    break;
                }
            }
        }
        Ok(())
    }

    async fn read_log_lines(
        path: &str,
        start_position: u64,
        logger: &FrameLogger,
        force_reopen: bool,
    ) -> Result<u64> {
        use tokio::io::{AsyncSeekExt, SeekFrom};

        // Check if file exists and get its current size
        let metadata = match tokio::fs::metadata(path).await {
            Ok(meta) => meta,
            Err(_) => return Ok(start_position), // File doesn't exist yet
        };

        let file_size = metadata.len();

        // If file hasn't grown and we're not forcing a reopen, nothing to read
        if file_size <= start_position && !force_reopen {
            return Ok(start_position);
        }

        // Open file and seek to our last position
        let mut file = match tokio::fs::File::open(path).await {
            Ok(f) => f,
            Err(_) => return Ok(start_position), // Can't open file
        };

        if file.seek(SeekFrom::Start(start_position)).await.is_err() {
            return Ok(start_position);
        }

        let reader = tokio::io::BufReader::new(file);
        let mut lines = reader.lines();
        let mut current_position = start_position;

        // Read all available lines
        while let Ok(Some(line)) = lines.next_line().await {
            logger.writeln(&line);
            // Estimate position (this is approximate but sufficient for our needs)
            current_position += line.len() as u64 + 1; // +1 for newline
        }

        Ok(current_position)
    }

    pub(super) fn snapshot_path(&self) -> Result<String> {
        let pid = self
            .pid()
            .ok_or_else(|| miette!("No pid available for frame snapshot"))?;

        Ok(format!(
            "{}/snapshot_{}-{}-{}.bin",
            self.config.snapshots_path, self.job_id, self.frame_id, pid
        ))
    }

    /// Save a snapshot of the frame into disk to enable recovering its status in case
    /// rqd restarts.
    ///
    pub(super) async fn create_snapshot(&self) -> Result<()> {
        let snapshot_path = self.snapshot_path()?;
        let serialized_data = bincode::serialize(self)
            .into_diagnostic()
            .map_err(|e| miette!("Failed to serialize frame snapshot: {}", e))?;
        tokio::fs::write(snapshot_path, serialized_data)
            .await
            .into_diagnostic()
            .map_err(|e| miette!("Failed to write frame snapshot: {}", e))?;
        Ok(())
    }

    pub(super) async fn clear_snapshot(&self) -> Result<()> {
        let snapshot_path = self.snapshot_path()?;
        tokio::fs::remove_file(snapshot_path)
            .await
            .into_diagnostic()
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
    pub async fn from_snapshot(path: &str, config: RunnerConfig) -> Result<Self> {
        let buff = tokio::fs::read(path).await.into_diagnostic()?;

        let mut frame: RunningFrame = bincode::deserialize(&buff)
            .into_diagnostic()
            .map_err(|e| miette!("Failed to deserialize frame snapshot: {}", e))?;

        // Replace snapshot config with the new config:
        frame.config = config;
        // Initialize stats_frozen (skipped during deserialization)
        frame.stats_frozen = AtomicBool::new(false);
        // Initialize host mem snapshot (skipped during deserialization)
        frame.latest_host_mem_snapshot = RwLock::new(None);

        let pid = frame.pid();

        // Check if pid is still active
        match pid {
            Some(pid) => Self::is_process_running(pid).then_some(pid).ok_or(miette!(
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

    pub(super) fn write_header(&self) -> String {
        let env_var_list = self
            .env_vars
            .iter()
            .map(|(key, value)| format!("{key}={value}"))
            .reduce(|a, b| a + "\n" + b.as_str())
            .unwrap_or("".to_string());
        let hyperthread = match &self.thread_ids {
            Some(cpu_list) => format!(
                "Hyperthreading cores {}",
                cpu_list
                    .iter()
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
            gid = self.gid,
            log_path = self.log_path,
            hostname = self.hostname,
            job_id = self.job_id,
            frame_id = self.frame_id,
        )
    }

    pub(super) fn write_footer(&self) -> String {
        let frame_stats_lock = self
            .frame_stats
            .read()
            .unwrap_or_else(|err| err.into_inner());
        let frame_stats = frame_stats_lock.clone();
        drop(frame_stats_lock);

        let state = self.state.read().unwrap_or_else(|err| err.into_inner());
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
                                    r#"____________________________________________________________________________________________________
    child_pid           {}
    name                {} - {}
    cmdline             {}
    maxrss              {}
    start_time          {}"#,
                                    child_stat.pid, child_stat.name, child_stat.state, child.cmdline, child_stat.rss, child.start_time
                                )
                            })
                            .join("\n")
                    })
                    .unwrap_or("".to_string());

                // Only failed frames get the host memory distribution, to keep it a
                // diagnostic signal rather than noise on every successful frame.
                let host_mem_section = if exit_status != 0 {
                    self.render_host_mem_distribution(finished_state.end_time)
                } else {
                    String::new()
                };

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

Processes:
{children}{host_mem_section}
===================================================================================================="#
                )
            }
            _ => r#"
====================================================================================================
Render Frame Completed
        ),
        "#
            .to_string(),
        }
    }

    pub(super) fn taskset(&self) -> String {
        self.thread_ids
            .clone()
            .unwrap_or(vec![0])
            .into_iter()
            .map(|i| i.to_string())
            .collect::<Vec<_>>()
            .join(",")
    }

    /// Produce a copy of this running frame in the format expected by the grpc interface
    pub fn clone_into_running_frame_info(&self) -> RunningFrameInfo {
        let frame_stats_lock = self
            .frame_stats
            .read()
            .unwrap_or_else(|err| err.into_inner());
        // Start time defauls to 0 if a frame hasn't started
        let start_time = frame_stats_lock.epoch_start_time;

        let children = frame_stats_lock.children.clone();

        let stats = frame_stats_lock.clone();
        RunningFrameInfo {
            resource_id: self.request.resource_id.clone(),
            job_id: self.request.job_id.clone(),
            job_name: self.request.job_name.clone(),
            frame_id: self.request.frame_id.clone(),
            frame_name: self.request.frame_name.clone(),
            layer_id: self.request.layer_id.clone(),
            num_cores: self.request.num_cores,
            start_time: (start_time * 1000) as i64,
            max_rss: (stats.max_rss / KIB) as i64,
            rss: (stats.rss / KIB) as i64,
            max_pss: (stats.max_pss / KIB) as i64,
            pss: (stats.pss / KIB) as i64,
            max_vsize: (stats.max_vsize / KIB) as i64,
            vsize: (stats.vsize / KIB) as i64,
            attributes: self.request.attributes.clone(),
            llu_time: stats.llu_time as i64,
            num_gpus: self.request.num_gpus,
            max_used_gpu_memory: (stats.max_used_gpu_memory / KIB) as i64,
            used_gpu_memory: (stats.used_gpu_memory / KIB) as i64,
            children,
            ..Default::default()
        }
    }

    pub fn mark_dangling(&self) {
        let mut lock = self
            .dangling_state_registed_at
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        // Never reset dangling marker
        if lock.is_none() {
            *lock = Some(SystemTime::now());
        }
    }

    pub fn unmark_dangling(&self) {
        let mut lock = self
            .dangling_state_registed_at
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        *lock = None
    }

    pub fn is_dangling_expired(&self) -> bool {
        let last_occurrence = *self
            .dangling_state_registed_at
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        match last_occurrence {
            Some(time) => time.elapsed().unwrap_or(Duration::ZERO) > Duration::from_secs(15),
            None => false,
        }
    }

    /// Freezes the frame statistics to prevent further updates.
    ///
    /// This is typically called when a frame is being killed for OOM (out of memory),
    /// to capture the accurate memory measurement at the moment of kill detection
    /// and prevent corruption from reading zombie/dying processes.
    ///
    /// Once frozen, calls to `update_frame_stats()` will be ignored.
    pub fn freeze_stats(&self) {
        self.stats_frozen.store(true, Ordering::SeqCst);
    }

    /// Stores the latest host-wide memory snapshot, shared from the monitor loop.
    ///
    /// The same `Arc` is pushed into every running frame each monitor cycle so that a
    /// failing frame's footer can render the host memory distribution without touching
    /// the machine singleton or any global lock on the failure path.
    pub fn set_host_mem_snapshot(&self, snapshot: Arc<HostMemSnapshot>) {
        let mut lock = self
            .latest_host_mem_snapshot
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        *lock = Some(snapshot);
    }

    /// Builds this frame's contribution to the host memory snapshot from its current stats.
    ///
    /// Memory values are in bytes. `reserved` is `None` when the frame declares no soft
    /// memory limit, in which case it is never flagged as overusing memory.
    pub fn to_peer_mem(&self) -> PeerMem {
        let stats = self
            .frame_stats
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        let reserved = if self.request.soft_memory_limit > 0 {
            Some(self.request.soft_memory_limit as u64)
        } else {
            None
        };
        PeerMem {
            frame_id: self.frame_id,
            label: format!("{}.{}", self.request.job_name, self.request.frame_name),
            current_rss: stats.rss,
            max_rss: stats.max_rss,
            reserved,
        }
    }

    /// Renders the host memory distribution block for the footer of a failed frame.
    ///
    /// Lists co-tenant frames (top 15 by current RSS) with current/peak session RSS and
    /// their reservation, flagging any frame using more than it reserved. Helps pinpoint
    /// whether the frame may have been starved by a memory-overusing neighbor.
    ///
    /// This frame's own row is always shown, even when 15 other frames outrank it by
    /// current RSS: in that case it takes the last displayed slot.
    fn render_host_mem_distribution(&self, end_time: SystemTime) -> String {
        const TOP_N: usize = 15;
        // Bytes -> GiB as a float, for compact human-readable sizes.
        let gib = |bytes: u64| bytes as f64 / bytesize::GIB as f64;

        let snapshot = self
            .latest_host_mem_snapshot
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .clone();

        let snapshot = match snapshot {
            Some(snapshot) => snapshot,
            None => {
                return "\n\nHost Memory Distribution: unavailable (no sample captured)".to_string()
            }
        };

        // Snapshot was captured before the frame exited; guard against clock skew.
        let age_secs = end_time
            .duration_since(snapshot.captured_at)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        let mut out = format!(
            "\n\nHost Memory Distribution   (captured {age_secs}s before exit)\n\
             host: {:.1} GiB total, {:.1} GiB available\n\
             \x20  RSS now |    peak  | reserved |\n",
            gib(snapshot.total_memory),
            gib(snapshot.available_memory),
        );

        // Display the top-N peers by current RSS, but always keep this frame's own row:
        // if it falls outside the natural top-N, reserve the last slot for it. Peers are
        // already sorted by current RSS descending, so appending self preserves ordering.
        let self_pos = snapshot
            .peers
            .iter()
            .position(|peer| peer.frame_id == self.frame_id);
        let display: Vec<&PeerMem> = match self_pos {
            Some(pos) if pos >= TOP_N => {
                let mut peers: Vec<&PeerMem> = snapshot.peers.iter().take(TOP_N - 1).collect();
                peers.push(&snapshot.peers[pos]);
                peers
            }
            _ => snapshot.peers.iter().take(TOP_N).collect(),
        };

        for peer in display {
            let reserved_str = match peer.reserved {
                Some(reserved) => format!("{:.1}G", gib(reserved)),
                None => "—".to_string(),
            };
            let over_flag = match peer.reserved {
                Some(reserved) if peer.current_rss > reserved => {
                    format!("OVER +{:.1}G", gib(peer.current_rss - reserved))
                }
                _ => String::new(),
            };
            let self_marker = if peer.frame_id == self.frame_id {
                " ◀ this frame"
            } else {
                ""
            };
            out.push_str(&format!(
                "  {:>7} {:>8} {:>8}   {:<12} {}{}\n",
                format!("{:.1}G", gib(peer.current_rss)),
                format!("{:.1}G", gib(peer.max_rss)),
                reserved_str,
                over_flag,
                peer.label,
                self_marker,
            ));
        }

        if snapshot.peers.len() > TOP_N {
            out.push_str(&format!("  … +{} more\n", snapshot.peers.len() - TOP_N));
        }

        out.trim_end().to_string()
    }
}

#[cfg(test)]
mod tests {
    use opencue_proto::rqd::{run_frame::UidOptional, RunFrame};
    use std::collections::HashMap;
    use std::sync::Arc;
    use uuid::Uuid;

    use crate::config::{compile_exit_status_rules, Config, LogExitStatusRule, RunnerConfig};
    use crate::frame::logging::FrameLoggerT;
    use crate::frame::logging::TestLogger;

    use super::{match_exit_status_rules, read_last_lines, RunningFrame, LOG_SCAN_MAX_BYTES};

    fn create_running_frame(
        command: &str,
        num_cores: u32,
        uid: u32,
        environment: HashMap<String, String>,
    ) -> RunningFrame {
        create_running_frame_cfg(command, num_cores, uid, environment, "", |_| {})
    }

    /// Like [`create_running_frame`], but allows setting a Loki URL and mutating the runner
    /// config (e.g. to install `log_exit_status_rules`) before the frame is built.
    fn create_running_frame_cfg<F: FnOnce(&mut RunnerConfig)>(
        command: &str,
        num_cores: u32,
        uid: u32,
        environment: HashMap<String, String>,
        loki_url: &str,
        configure: F,
    ) -> RunningFrame {
        let frame_id = Uuid::new_v4().to_string();
        let general_config = Config::default();
        general_config.setup().unwrap();
        let mut config = general_config.runner;
        config.run_as_user = false;
        configure(&mut config);

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
                frame_temp_dir: "".to_string(),
                num_cores: num_cores as i32,
                gid: 10,
                ignore_nimby: false,
                environment,
                attributes: HashMap::new(),
                num_gpus: 0,
                children: None,
                uid_optional: Some(UidOptional::Uid(uid as i32)),
                os: "rhel9".to_string(),
                soft_memory_limit: 0,
                hard_memory_limit: 0,
                pid: 0,
                loki_url: loki_url.to_string(),

                #[allow(deprecated)]
                job_temp_dir: "".to_string(),

                #[allow(deprecated)]
                log_file: "".to_string(),

                #[allow(deprecated)]
                log_dir_file: "".to_string(),

                #[allow(deprecated)]
                start_time: 0,
            },
            uid,
            config,
            None,
            None,
            "localhost".to_string(),
            1,
        )
    }

    /// Builds a frame whose runner config has a single license-error rule (exit status 330) and
    /// writes `log_contents` to a unique log file, ready for a scan. The frame's `log_path` is
    /// repointed at that file so parallel tests never collide on the derived path.
    fn frame_with_license_rule(loki_url: &str, log_contents: &str) -> RunningFrame {
        let mut frame = create_running_frame_cfg("false", 1, 1, HashMap::new(), loki_url, |cfg| {
            cfg.log_scan_last_lines = 50;
            cfg.log_exit_status_rules = vec![rule(
                "HOUDINI_LICENSE_ERROR",
                "A usable license to run the application is installed but they are all in use",
                330,
            )];
        });
        let log_file = std::env::temp_dir().join(format!("rqd_scan_test_{}.rqlog", Uuid::new_v4()));
        std::fs::write(&log_file, log_contents).unwrap();
        frame.log_path = log_file.to_string_lossy().to_string();
        frame
    }

    const LICENSE_LOG: &str = "\
[12:40:13] Some earlier unrelated output
[12:40:13] A usable license to run the application is installed but they are all in use.
[12:40:13] Please contact your companies license administrator to create availability
[12:40:14] Process completed with exit status: 3
";

    fn rule(name: &str, regex: &str, exit_status: i32) -> LogExitStatusRule {
        LogExitStatusRule {
            name: name.to_string(),
            regex: regex.to_string(),
            exit_status,
        }
    }

    #[test]
    fn test_match_exit_status_rules_first_match_wins() {
        let rules = compile_exit_status_rules(&[
            rule("LICENSE", "all in use", 330),
            rule("GENERIC", "error", 331),
        ]);
        // Both patterns are present; the earlier rule in the list must win.
        let tail = "some error occurred\nlicenses are all in use now";
        assert_eq!(
            match_exit_status_rules(tail, &rules),
            Some(("LICENSE".to_string(), 330))
        );
    }

    #[test]
    fn test_match_exit_status_rules_no_match() {
        let rules = compile_exit_status_rules(&[rule("LICENSE", "all in use", 330)]);
        assert_eq!(match_exit_status_rules("frame rendered fine", &rules), None);
    }

    #[test]
    fn test_compile_exit_status_rules_skips_invalid_regex() {
        // The middle rule has an invalid pattern and must be dropped without failing the rest.
        let compiled = compile_exit_status_rules(&[
            rule("GOOD", "valid", 1),
            rule("BAD", "(unclosed", 2),
            rule("ALSO_GOOD", "also", 3),
        ]);
        assert_eq!(compiled.len(), 2);
        assert_eq!(
            match_exit_status_rules("also valid", &compiled),
            Some(("GOOD".to_string(), 1))
        );
    }

    #[tokio::test]
    async fn test_read_last_lines_returns_tail() {
        let mut file = tempfile::NamedTempFile::new().unwrap();
        use std::io::Write;
        for i in 0..100 {
            writeln!(file, "line {i}").unwrap();
        }
        let path = file.path().to_string_lossy().to_string();

        let lines = read_last_lines(&path, 5).await.unwrap();
        assert_eq!(
            lines,
            vec!["line 95", "line 96", "line 97", "line 98", "line 99"]
        );
    }

    #[tokio::test]
    async fn test_read_last_lines_fewer_than_requested() {
        let mut file = tempfile::NamedTempFile::new().unwrap();
        use std::io::Write;
        writeln!(file, "only line").unwrap();
        let path = file.path().to_string_lossy().to_string();

        let lines = read_last_lines(&path, 50).await.unwrap();
        assert_eq!(lines, vec!["only line"]);
    }

    #[tokio::test]
    async fn test_read_last_lines_matches_license_error() {
        // End-to-end: the exact license message from a real Houdini failure must match.
        let mut file = tempfile::NamedTempFile::new().unwrap();
        use std::io::Write;
        writeln!(file, "[12:40:13] Some earlier unrelated output").unwrap();
        writeln!(
            file,
            "[12:40:13] A usable license to run the application is installed but they are all in use."
        )
        .unwrap();
        writeln!(
            file,
            "[12:40:13] Please contact your companies license administrator to create availability"
        )
        .unwrap();
        writeln!(file, "[12:40:14] Process completed with exit status: 3").unwrap();
        let path = file.path().to_string_lossy().to_string();

        let lines = read_last_lines(&path, 10).await.unwrap();
        let tail = lines.join("\n");
        let rules = compile_exit_status_rules(&[rule(
            "HOUDINI_LICENSE_ERROR",
            "A usable license to run the application is installed but they are all in use",
            330,
        )]);
        assert_eq!(
            match_exit_status_rules(&tail, &rules),
            Some(("HOUDINI_LICENSE_ERROR".to_string(), 330))
        );
    }

    #[tokio::test]
    async fn test_read_last_lines_spans_multiple_chunks() {
        // A file far larger than LOG_SCAN_CHUNK_BYTES forces the backward read to walk several
        // chunks; the tail must still be exact and correctly ordered across chunk boundaries.
        let mut file = tempfile::NamedTempFile::new().unwrap();
        use std::io::Write;
        // ~200 bytes/line * 2000 lines ≈ 400 KiB, well beyond the 16 KiB chunk.
        let filler = "x".repeat(180);
        for i in 0..2000 {
            writeln!(file, "line {i:04} {filler}").unwrap();
        }
        file.flush().unwrap();
        let path = file.path().to_string_lossy().to_string();

        let lines = read_last_lines(&path, 3).await.unwrap();
        assert_eq!(
            lines,
            vec![
                format!("line 1997 {filler}"),
                format!("line 1998 {filler}"),
                format!("line 1999 {filler}"),
            ]
        );
    }

    #[tokio::test]
    async fn test_read_last_lines_respects_byte_cap() {
        // A single line longer than LOG_SCAN_MAX_BYTES is dropped entirely (its leading partial
        // is truncated at the floor and discarded), matching the documented cap behavior.
        let mut file = tempfile::NamedTempFile::new().unwrap();
        use std::io::Write;
        let giant = "y".repeat((LOG_SCAN_MAX_BYTES as usize) + 4096);
        writeln!(file, "{giant}").unwrap();
        writeln!(file, "short tail line").unwrap();
        file.flush().unwrap();
        let path = file.path().to_string_lossy().to_string();

        let lines = read_last_lines(&path, 10).await.unwrap();
        assert_eq!(lines, vec!["short tail line"]);
    }

    #[tokio::test]
    async fn test_scan_returns_none_on_success() {
        let frame = create_running_frame("true", 1, 1, HashMap::new());
        // exit_code 0 must never trigger a scan/override, regardless of config.
        assert_eq!(frame.scan_log_for_exit_status_override(0).await, None);
    }

    #[tokio::test]
    async fn test_scan_returns_none_without_rules() {
        // Default config has no rules configured, so a failure yields no override.
        let frame = create_running_frame("false", 1, 1, HashMap::new());
        assert_eq!(frame.scan_log_for_exit_status_override(1).await, None);
    }

    #[tokio::test]
    async fn test_scan_overrides_on_license_match() {
        // End-to-end: a failed frame whose log contains the license message is reclassified.
        let frame = frame_with_license_rule("", LICENSE_LOG);
        assert_eq!(
            frame.scan_log_for_exit_status_override(3).await,
            Some(("HOUDINI_LICENSE_ERROR".to_string(), 330))
        );
        let _ = std::fs::remove_file(&frame.log_path);
    }

    #[tokio::test]
    async fn test_scan_no_override_when_pattern_absent() {
        // A failure whose log doesn't match any rule keeps its original exit status.
        let frame = frame_with_license_rule("", "frame rendered fine\nexit status: 1\n");
        assert_eq!(frame.scan_log_for_exit_status_override(1).await, None);
        let _ = std::fs::remove_file(&frame.log_path);
    }

    #[tokio::test]
    async fn test_scan_skips_loki_frames() {
        // Even with a matching local file, a Loki-backed frame must not be scanned.
        let frame = frame_with_license_rule("http://loki.example.com", LICENSE_LOG);
        assert_eq!(frame.scan_log_for_exit_status_override(3).await, None);
        let _ = std::fs::remove_file(&frame.log_path);
    }

    #[tokio::test]
    async fn test_scan_uses_rules_added_after_frame_creation() {
        // The live-reload guarantee: a frame launched with NO rules configured must pick up
        // rules swapped in later (as the config watcher does on file change), because every
        // RunnerConfig clone shares the compiled-rules cell.
        let mut config_handle: Option<RunnerConfig> = None;
        let mut frame = create_running_frame_cfg("false", 1, 1, HashMap::new(), "", |cfg| {
            config_handle = Some(cfg.clone());
        });
        let log_file = std::env::temp_dir().join(format!("rqd_scan_test_{}.rqlog", Uuid::new_v4()));
        std::fs::write(&log_file, LICENSE_LOG).unwrap();
        frame.log_path = log_file.to_string_lossy().to_string();

        // No rules yet: the failure keeps its exit status (this also seeds the shared cell,
        // proving a reload replaces an already-seeded set).
        assert_eq!(frame.scan_log_for_exit_status_override(3).await, None);

        config_handle.unwrap().reload_exit_status_rules(
            50,
            &[rule(
                "HOUDINI_LICENSE_ERROR",
                "A usable license to run the application is installed but they are all in use",
                330,
            )],
        );

        assert_eq!(
            frame.scan_log_for_exit_status_override(3).await,
            Some(("HOUDINI_LICENSE_ERROR".to_string(), 330))
        );
        let _ = std::fs::remove_file(&frame.log_path);
    }

    #[tokio::test]
    async fn test_scan_skips_killed_frames() {
        // A frame RQD killed keeps its kill-driven classification, even if the log matches.
        let frame = frame_with_license_rule("", LICENSE_LOG);
        frame.start(12345);
        frame.get_pid_to_kill("manual kill").unwrap();
        assert_eq!(frame.scan_log_for_exit_status_override(1).await, None);
        let _ = std::fs::remove_file(&frame.log_path);
    }

    #[tokio::test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    async fn test_run_logs_stdout_stderr() {
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
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
            .await;
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());

        let possible_out = ["stderr test", "stdout test"];
        assert!(possible_out.contains(&logger.pop().unwrap().as_str()));
        assert!(possible_out.contains(&logger.pop().unwrap().as_str()));

        // Assert the output on the exit_file is the same
        if let Ok(status) = running_frame.read_exit_file().await {
            assert_eq!((0, None), status);
        }
    }

    #[tokio::test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    async fn test_run_failed() {
        let mut env = HashMap::with_capacity(1);
        env.insert("TEST_ENV".to_string(), "test".to_string());
        let running_frame = create_running_frame(r#"echo "stdout $TEST_ENV" && exit 1"#, 1, 1, env);

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
            .await;
        assert!(status.is_ok());
        assert_eq!((1, None), status.unwrap());
        assert_eq!("stdout test", logger.pop().unwrap());
    }

    #[tokio::test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    async fn test_run_multiline_stdout() {
        let running_frame = create_running_frame(
            r#"echo "line1" && echo "line2" && echo "line3""#,
            1,
            1,
            HashMap::new(),
        );

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
            .await;
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
        assert_eq!("line3", logger.pop().unwrap());
        assert_eq!("line2", logger.pop().unwrap());
        assert_eq!("line1", logger.pop().unwrap());

        // Assert the output on the exit_file is the same
        if let Ok(status) = running_frame.read_exit_file().await {
            assert_eq!((0, None), status);
        }
    }

    #[tokio::test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    async fn test_run_env_variables() {
        let mut env = HashMap::new();
        env.insert("VAR1".to_string(), "value1".to_string());
        env.insert("VAR2".to_string(), "value2".to_string());

        let running_frame = create_running_frame(r#"echo "$VAR1 $VAR2""#, 1, 1, env);

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
            .await;
        assert!(status.is_ok());
        assert_eq!((0, None), status.unwrap());
        assert_eq!("value1 value2", logger.pop().unwrap());

        // Assert the output on the exit_file is the same
        if let Ok(status) = running_frame.read_exit_file().await {
            assert_eq!((0, None), status);
        }
    }

    #[tokio::test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    async fn test_run_command_not_found() {
        let running_frame =
            create_running_frame(r#"command_that_does_not_exist"#, 1, 1, HashMap::new());

        let logger = Arc::new(TestLogger::init());
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
            .await;
        assert!(status.is_ok());
        // The exact exit code might vary by system, but it should be non-zero
        assert_ne!((0, None), status.unwrap());

        // Assert the output on the exit_file is the same
        if let Ok(status) = running_frame.read_exit_file().await {
            // Exit status should be an error code usually 127
            assert_ne!((0, None), status);
        }
    }

    #[tokio::test]
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    async fn test_run_sleep_command() {
        use std::time::{Duration, Instant};

        let running_frame =
            create_running_frame(r#"sleep 0.5 && echo "Done sleeping""#, 1, 1, HashMap::new());

        let logger = Arc::new(TestLogger::init());
        let start = Instant::now();
        let status = running_frame
            .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
            .await;
        let elapsed = start.elapsed();

        assert_eq!((0, None), status.expect("status should be OK"));
        assert!(
            elapsed >= Duration::from_millis(500),
            "Command didn't run for expected duration"
        );
        assert_eq!("Done sleeping", logger.pop().unwrap());

        // Assert the output on the exit_file is the same
        if let Ok(status) = running_frame.read_exit_file().await {
            assert_eq!((0, None), status);
        }
    }

    fn set_test_snapshot(frame: &RunningFrame, include_self: bool, extra_peers: usize) {
        use crate::system::manager::{HostMemSnapshot, PeerMem};
        use std::sync::Arc;
        use std::time::SystemTime;

        let gib = bytesize::GIB;
        let mut peers = vec![
            // Over-reserved co-tenant: biggest current RSS, should top the list + be flagged.
            PeerMem {
                frame_id: Uuid::new_v4(),
                label: "bigshow-sq010.comp_v3".to_string(),
                current_rss: 180 * gib,
                max_rss: 190 * gib,
                reserved: Some(16 * gib),
            },
            // Innocent whale: within its reservation, no flag.
            PeerMem {
                frame_id: Uuid::new_v4(),
                label: "bigshow-sq010.light_v1".to_string(),
                current_rss: 58 * gib,
                max_rss: 60 * gib,
                reserved: Some(60 * gib),
            },
        ];
        if include_self {
            // Unreserved frame (soft limit unset) -> reserved shown as dash, never flagged.
            peers.push(PeerMem {
                frame_id: frame.frame_id,
                label: "othershow-sh05.sim".to_string(),
                current_rss: 40 * gib,
                max_rss: 41 * gib,
                reserved: None,
            });
        }
        for i in 0..extra_peers {
            peers.push(PeerMem {
                frame_id: Uuid::new_v4(),
                label: format!("filler.frame_{i}"),
                current_rss: (1 + i as u64) * gib,
                max_rss: (1 + i as u64) * gib,
                reserved: Some(gib),
            });
        }
        peers.sort_by(|a, b| b.current_rss.cmp(&a.current_rss));

        frame.set_host_mem_snapshot(Arc::new(HostMemSnapshot {
            captured_at: SystemTime::now(),
            total_memory: 512 * gib,
            available_memory: 8 * gib,
            peers,
        }));
    }

    #[test]
    fn test_to_peer_mem_maps_stats_and_reservation() {
        use crate::system::manager::ProcessStats;
        let gib = bytesize::GIB;

        // Unreserved frame (soft_memory_limit == 0) -> reserved is None.
        let frame = create_running_frame("true", 1, 1, HashMap::new());
        frame.update_frame_stats(ProcessStats {
            rss: 10 * gib,
            max_rss: 12 * gib,
            ..Default::default()
        });
        let peer = frame.to_peer_mem();
        assert_eq!(peer.frame_id, frame.frame_id);
        assert_eq!(peer.label, "job_name.frame_name");
        assert_eq!(peer.current_rss, 10 * gib);
        assert_eq!(peer.max_rss, 12 * gib);
        assert_eq!(peer.reserved, None);

        // Reserved frame (soft_memory_limit > 0) -> reserved is Some(limit as bytes).
        let mut reserved_frame = create_running_frame("true", 1, 1, HashMap::new());
        reserved_frame.request.soft_memory_limit = (8 * gib) as i64;
        reserved_frame.update_frame_stats(ProcessStats {
            rss: 4 * gib,
            max_rss: 5 * gib,
            ..Default::default()
        });
        let reserved_peer = reserved_frame.to_peer_mem();
        assert_eq!(reserved_peer.reserved, Some(8 * gib));
        assert_eq!(reserved_peer.current_rss, 4 * gib);
        assert_eq!(reserved_peer.max_rss, 5 * gib);
    }

    #[test]
    fn test_footer_host_mem_on_failure() {
        let frame = create_running_frame("true", 1, 1, HashMap::new());
        frame.start(1234);
        set_test_snapshot(&frame, true, 0);
        frame.finish(1, None, None).unwrap();

        let footer = frame.write_footer();

        assert!(
            footer.contains("Host Memory Distribution"),
            "failed frame should render the memory distribution: {footer}"
        );
        assert!(
            footer.contains("512.0 GiB total, 8.0 GiB available"),
            "host header line missing: {footer}"
        );
        // Over-reserved frame (180G used vs 16G reserved) flagged with the overage.
        assert!(
            footer.contains("OVER +164.0G"),
            "over-reservation flag missing/incorrect: {footer}"
        );
        // Unreserved self frame: dash for reserved, no OVER, marked as this frame.
        assert!(footer.contains("—"), "unreserved dash missing: {footer}");
        assert!(
            footer.contains("◀ this frame"),
            "self marker missing: {footer}"
        );
        // Innocent whale within reservation is not flagged.
        assert!(
            footer.contains("bigshow-sq010.light_v1"),
            "within-reservation peer missing: {footer}"
        );
    }

    #[test]
    fn test_footer_no_host_mem_on_success() {
        let frame = create_running_frame("true", 1, 1, HashMap::new());
        frame.start(1234);
        set_test_snapshot(&frame, true, 0);
        frame.finish(0, None, None).unwrap();

        let footer = frame.write_footer();

        assert!(
            !footer.contains("Host Memory Distribution"),
            "successful frame must not render the memory distribution: {footer}"
        );
    }

    #[test]
    fn test_footer_host_mem_unavailable() {
        let frame = create_running_frame("true", 1, 1, HashMap::new());
        frame.start(1234);
        // No snapshot set.
        frame.finish(1, None, None).unwrap();

        let footer = frame.write_footer();

        assert!(
            footer.contains("Host Memory Distribution: unavailable (no sample captured)"),
            "missing-snapshot case should be reported: {footer}"
        );
    }

    #[test]
    fn test_footer_host_mem_top_n_cap() {
        let frame = create_running_frame("true", 1, 1, HashMap::new());
        frame.start(1234);
        // 2 base peers + self + 16 fillers = 19 peers, cap is 15 -> "+4 more".
        set_test_snapshot(&frame, true, 16);
        frame.finish(1, None, None).unwrap();

        let footer = frame.write_footer();

        assert!(
            footer.contains("… +4 more"),
            "top-N truncation summary missing/incorrect: {footer}"
        );

        // Now the case where 15 peers all outrank this frame by current RSS: the self
        // row must still be shown, taking the last displayed slot, displacing the
        // lowest-RSS non-self peer from the top-15.
        let outranked = create_running_frame("true", 1, 1, HashMap::new());
        outranked.start(1234);
        {
            use crate::system::manager::{HostMemSnapshot, PeerMem};
            use std::sync::Arc;
            use std::time::SystemTime;

            let gib = bytesize::GIB;
            let mut peers: Vec<PeerMem> = (0..15)
                .map(|i| PeerMem {
                    frame_id: Uuid::new_v4(),
                    label: format!("bigshow.frame_{i}"),
                    current_rss: (100 + i as u64) * gib, // all above self's 40G
                    max_rss: (100 + i as u64) * gib,
                    reserved: Some(200 * gib),
                })
                .collect();
            peers.push(PeerMem {
                frame_id: outranked.frame_id,
                label: "othershow.sim".to_string(),
                current_rss: 40 * gib,
                max_rss: 41 * gib,
                reserved: None,
            });
            peers.sort_by(|a, b| b.current_rss.cmp(&a.current_rss));
            outranked.set_host_mem_snapshot(Arc::new(HostMemSnapshot {
                captured_at: SystemTime::now(),
                total_memory: 512 * gib,
                available_memory: 8 * gib,
                peers,
            }));
        }
        outranked.finish(1, None, None).unwrap();

        let footer = outranked.write_footer();
        assert!(
            footer.contains("◀ this frame"),
            "self row must be retained even when outside the natural top-15: {footer}"
        );
        // 16 peers, 15 displayed (14 top + self) -> exactly one hidden.
        assert!(
            footer.contains("… +1 more"),
            "hidden count should be '+1 more' with self reserved: {footer}"
        );
        // The displaced peer is the lowest-RSS non-self one (frame_0 @ 100G); it must
        // not be displayed, proving self took a reserved slot rather than a 16th row.
        assert!(
            !footer.contains("bigshow.frame_0"),
            "lowest non-self peer should be hidden to make room for self: {footer}"
        );
    }

    #[test]
    #[cfg(unix)]
    fn test_interprete_output_signal_killed() {
        use std::os::unix::process::ExitStatusExt;
        use std::process::ExitStatus;

        // Bash wrapper exits normally with code `128 + signal` when the child
        // is killed by a signal. Construct an ExitStatus that mirrors that:
        // wait status encodes a normal exit as `exit_code << 8`.
        let exit_status = ExitStatus::from_raw(137 << 8); // SIGKILL (9)
        assert_eq!(
            (1, Some(9)),
            RunningFrame::interprete_output(exit_status),
            "SIGKILL-wrapped exit code 137 should produce (1, Some(9))",
        );

        let exit_status = ExitStatus::from_raw(143 << 8); // SIGTERM (15)
        assert_eq!(
            (1, Some(15)),
            RunningFrame::interprete_output(exit_status),
            "SIGTERM-wrapped exit code 143 should produce (1, Some(15))",
        );

        let exit_status = ExitStatus::from_raw(139 << 8); // SIGSEGV (11)
        assert_eq!(
            (1, Some(11)),
            RunningFrame::interprete_output(exit_status),
            "SIGSEGV-wrapped exit code 139 should produce (1, Some(11))",
        );
    }

    #[test]
    #[cfg(unix)]
    fn test_interprete_output_normal_exit() {
        use std::os::unix::process::ExitStatusExt;
        use std::process::ExitStatus;

        let exit_status = ExitStatus::from_raw(0);
        assert_eq!((0, None), RunningFrame::interprete_output(exit_status));

        let exit_status = ExitStatus::from_raw(1 << 8);
        assert_eq!((1, None), RunningFrame::interprete_output(exit_status));

        let exit_status = ExitStatus::from_raw(42 << 8);
        assert_eq!((42, None), RunningFrame::interprete_output(exit_status));
    }

    #[test]
    #[cfg(unix)]
    fn test_interprete_output_direct_signal() {
        use std::os::unix::process::ExitStatusExt;
        use std::process::ExitStatus;

        // Direct-signal case: wait status low 7 bits hold the signal number.
        // ExitStatus::code() returns None here, so the wrapper-translation
        // branch must not run and `exit_signal` should reflect the raw signal.
        let exit_status = ExitStatus::from_raw(9);
        assert_eq!(
            (1, Some(9)),
            RunningFrame::interprete_output(exit_status),
            "direct SIGKILL should produce (1, Some(9))",
        );
    }

    // Test fails intermitently. Commenting it out for now as the outputs are correct,
    // only misaligned
    // #[tokio::test]
    // #[cfg(any(target_os = "linux", target_os = "macos"))]
    // async fn test_run_interleaved_stdout_stderr() {
    //     let running_frame = create_running_frame(
    //         r#"echo "stdout1" && echo "stderr1" >&2 && echo "stdout2" && echo "stderr2" >&2"#,
    //         1,
    //         1,
    //         HashMap::new(),
    //     );

    //     let logger = Arc::new(TestLogger::init());
    //     let status = running_frame
    //         .run_inner(Arc::clone(&logger) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
    //         .await;
    //     assert!(status.is_ok());
    //     assert_eq!((0, None), status.unwrap());

    //     let logs = logger.all();
    //     assert!(logs.contains(&"stdout1".to_string()));
    //     assert!(logs.contains(&"stderr1".to_string()));
    //     assert!(logs.contains(&"stdout2".to_string()));
    //     assert!(logs.contains(&"stderr2".to_string()));

    //     // Assert the output on the exit_file is the same
    //     let status = running_frame.read_exit_file().await;
    //     assert!(status.is_ok());
    //     assert_eq!((0, None), status.unwrap());
    // }
}
