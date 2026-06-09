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

use crate::config::RunnerConfig;
use chrono::{DateTime, Local, Utc};
use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::rqd::RunFrame;
use serde_derive::Serialize;
use std::collections::HashMap;
use std::time::Duration;
use std::{
    fs::{self, File, Permissions},
    io::Write,
    path::Path,
    sync::{Arc, Mutex},
    time::SystemTime,
};
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use tracing::error;
use ureq::Agent;

pub type FrameLogger = Arc<dyn FrameLoggerT + Sync + Send>;

pub trait FrameLoggerT {
    // Write a string as a line
    fn writeln(&self, line: &str);
    // Write a byte stream
    #[allow(dead_code)]
    fn write(&self, bytes: &[u8]);
}

pub struct FrameLoggerBuilder {}

impl FrameLoggerBuilder {
    pub fn from_cuebot(
        run_frame: RunFrame,
        path: String,
        runner_config: RunnerConfig,
        uid_gid: Option<(u32, u32)>,
    ) -> Result<Arc<dyn FrameLoggerT + Send + Sync + 'static>> {
        if !run_frame.loki_url.is_empty() {
            FrameLokiLogger::init(run_frame)
                .map(|a| Arc::new(a) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
        } else {
            FrameFileLogger::init(path, runner_config.prepend_timestamp, uid_gid)
                .map(|a| Arc::new(a) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
        }
    }
}

pub struct FrameFileLogger {
    _path: String,
    prepend_timestamp: bool,
    file_descriptor: Mutex<File>,
}

impl FrameFileLogger {
    pub fn init(
        path: String,
        prepend_timestamp: bool,
        uid_gid: Option<(u32, u32)>,
    ) -> Result<Self> {
        let log_path = Path::new(path.as_str());
        if log_path.exists() {
            Self::rotate_existing_files(&path)
                .wrap_err_with(|| format!("failed to rotate existing frame log {log_path:?}"))?;
        } else if let Some(parent_path) = log_path.parent() {
            if !parent_path.exists() {
                if let Err(err) = fs::create_dir_all(parent_path) {
                    let diag = Self::describe_path_failure(parent_path, uid_gid, Some(&err));
                    return Err(err).into_diagnostic().wrap_err(format!(
                        "failed to create parent log dir {parent_path:?}{diag}"
                    ));
                }
                if let Some((uid, gid)) = uid_gid {
                    Self::change_ownership(parent_path, uid, gid)?;
                }
            }
        }

        let file = match File::create(log_path) {
            Ok(file) => file,
            Err(err) => {
                let diag = Self::describe_path_failure(log_path, uid_gid, Some(&err));
                return Err(err).into_diagnostic().wrap_err(format!(
                    "failed to create frame log file {log_path:?}{diag}"
                ));
            }
        };
        if let Some((uid, gid)) = uid_gid {
            Self::change_ownership(log_path, uid, gid)?;
        }
        let file_descriptor = Mutex::new(file);
        Ok(FrameFileLogger {
            _path: path,
            prepend_timestamp,
            file_descriptor,
        })
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn change_ownership(path: &Path, uid: u32, gid: u32) -> Result<()> {
        use std::os::unix::fs::chown;

        fs::set_permissions(path, Permissions::from_mode(0o775))
            .into_diagnostic()
            .wrap_err(format!("Failed to change log dir permissions: {path:?}"))?;

        chown(path, Some(uid), Some(gid))
            .into_diagnostic()
            .wrap_err(format!("Failed to change log dir ownership: {path:?}"))
    }

    #[cfg(target_os = "windows")]
    fn change_ownership(_path: &Path, _uid: u32, _gid: u32) -> Result<()> {
        Ok(())
    }

    /// Best-effort diagnostics gathered when a log-path operation fails, so the error
    /// explains *why* (process creds, the directory's ownership/mode/writability, and the
    /// backing filesystem) instead of a bare `os error 13`. Never panics; only invoked on
    /// the error path, so the cost is irrelevant.
    #[cfg(any(target_os = "linux", target_os = "macos"))]
    fn describe_path_failure(
        path: &Path,
        intended: Option<(u32, u32)>,
        err: Option<&std::io::Error>,
    ) -> String {
        use std::os::unix::fs::MetadataExt;

        // SAFETY: geteuid/getegid are always-successful syscalls with no preconditions.
        let (euid, egid) = unsafe { (nix::libc::geteuid(), nix::libc::getegid()) };

        let mut out = format!("\n  diagnostics: process euid={euid} egid={egid}");
        if let Some((uid, gid)) = intended {
            out.push_str(&format!(", intended chown uid={uid} gid={gid}"));
        }

        // The directory we actually need write access to (a new entry is created inside it).
        let dir = path.parent().unwrap_or(path);
        match fs::metadata(dir) {
            Ok(md) => {
                let writable = nix::unistd::access(dir, nix::unistd::AccessFlags::W_OK).is_ok();
                out.push_str(&format!(
                    "\n  parent dir {dir:?}: owner uid={} gid={} mode={:#o} writable_by_euid={writable}",
                    md.uid(),
                    md.gid(),
                    md.mode() & 0o7777,
                ));
            }
            Err(stat_err) => {
                out.push_str(&format!("\n  parent dir {dir:?}: stat failed: {stat_err}"));
            }
        }

        if let Some((fstype, source)) = Self::mount_for_path(path) {
            out.push_str(&format!("\n  filesystem: type={fstype} source={source}"));

            let denied = err.and_then(|e| e.raw_os_error()).is_some_and(|code| {
                code == nix::libc::EACCES || code == nix::libc::EPERM || code == nix::libc::ESTALE
            });
            if denied && fstype.starts_with("nfs") && euid == 0 {
                out.push_str(
                    "\n  hint: a permission/stale error as root on an NFS path almost always means a \
                     stale or divergent NFS mount (or a private mount namespace), not a permission \
                     bug. Check: `findmnt -T <path>`; compare `/proc/<rqd-pid>/ns/mnt` against a \
                     fresh shell; `nsenter -t <rqd-pid> -m -- touch <dir>/probe`.",
                );
            }
        }

        out
    }

    #[cfg(target_os = "windows")]
    fn describe_path_failure(
        _path: &Path,
        _intended: Option<(u32, u32)>,
        _err: Option<&std::io::Error>,
    ) -> String {
        String::new()
    }

    /// Returns `(fstype, source)` of the mount that contains `path`, matching the longest
    /// mount-point prefix in `/proc/self/mountinfo` (Linux only).
    #[cfg(target_os = "linux")]
    fn mount_for_path(path: &Path) -> Option<(String, String)> {
        let target = fs::canonicalize(path).unwrap_or_else(|_| path.to_path_buf());
        let content = fs::read_to_string("/proc/self/mountinfo").ok()?;

        let mut best: Option<(usize, String, String)> = None;
        for line in content.lines() {
            // mountinfo: `<fields...> - <fstype> <source> <super opts>`
            let Some((left, right)) = line.split_once(" - ") else {
                continue;
            };
            let left_fields: Vec<&str> = left.split_whitespace().collect();
            let right_fields: Vec<&str> = right.split_whitespace().collect();
            if left_fields.len() < 5 || right_fields.len() < 2 {
                continue;
            }
            let mount_point = left_fields[4];
            if target.starts_with(mount_point) {
                let len = mount_point.len();
                let better = match &best {
                    Some((best_len, _, _)) => len > *best_len,
                    None => true,
                };
                if better {
                    best = Some((
                        len,
                        right_fields[0].to_string(),
                        right_fields[1].to_string(),
                    ));
                }
            }
        }
        best.map(|(_, fstype, source)| (fstype, source))
    }

    #[cfg(target_os = "macos")]
    fn mount_for_path(_path: &Path) -> Option<(String, String)> {
        None
    }

    fn rotate_existing_files(path: &String) -> Result<()> {
        let log_path = Path::new(path);
        if log_path.is_file() {
            let mut rotate_count = 1;
            while Path::new(&format!("{}.{}", path, rotate_count)).is_file() && rotate_count < 100 {
                rotate_count += 1;
            }
            let rotate_path = format!("{}.{}", path, rotate_count);
            fs::rename(log_path, Path::new(&rotate_path)).into_diagnostic()?;
        }
        Ok(())
    }
}

// Structs to model the Loki JSON payload structure
#[derive(Serialize, Debug)]
struct LokiPayload {
    streams: Vec<Stream>,
}

#[derive(Serialize, Debug)]
struct Stream {
    stream: HashMap<String, String>,
    values: Vec<[String; 2]>,
}

#[derive(Serialize)]
struct LokiLabels {
    host: String,
    job_name: String,
    frame_name: String,
    username: String,
    frame_id: String,
    session_start_time: String,
}

pub struct FrameLokiLogger {
    agent: Agent,
    loki_url: String,
    labels: HashMap<String, String>,
}

impl FrameLokiLogger {
    pub fn init(run_frame: RunFrame) -> Result<Self> {
        let agent: Agent = Agent::config_builder()
            .timeout_global(Some(Duration::from_secs(5)))
            .build()
            .into();

        let (labels, loki_url) = Self::build_loki_components(run_frame)?;

        Ok(FrameLokiLogger {
            agent,
            loki_url,
            labels,
        })
    }

    /// Builds the labels for Loki and extracts the Loki URL from the RunFrame.
    fn build_loki_components(run_frame: RunFrame) -> Result<(HashMap<String, String>, String)> {
        #[cfg(unix)]
        let host = nix::unistd::gethostname().map_or_else(
            |_| "hostname-unavailable".to_string(),
            |h| h.to_string_lossy().into_owned(),
        );
        #[cfg(windows)]
        let host = sysinfo::System::host_name().unwrap_or_else(|| "hostname-unavailable".to_string());

        let loki_labels = LokiLabels {
            host,
            job_name: run_frame.job_name,
            frame_name: run_frame.frame_name,
            username: run_frame.user_name,
            frame_id: run_frame.frame_id,
            session_start_time: Utc::now().timestamp().to_string(),
        };

        let labels: HashMap<String, String> =
            serde_json::from_value(serde_json::to_value(loki_labels).into_diagnostic()?)
                .into_diagnostic()?;

        Ok((labels, run_frame.loki_url))
    }
}

impl FrameLoggerT for FrameLokiLogger {
    fn writeln(&self, line: &str) {
        let timestamp = Utc::now().timestamp_nanos_opt().unwrap_or(0).to_string();
        let payload = LokiPayload {
            streams: vec![Stream {
                stream: self.labels.clone(),
                values: vec![[timestamp, line.to_string()]],
            }],
        };
        if let Err(err) = self
            .agent
            .post(format!("{}/loki/api/v1/push", self.loki_url))
            .send_json(payload)
            .into_diagnostic()
        {
            error!("Failed to write line to loki: {err}");
        };
    }
    fn write(&self, bytes: &[u8]) {
        let unserialized = std::str::from_utf8(bytes);
        match unserialized {
            Ok(line) => self.writeln(line),
            Err(err) => {
                error!("Failed to write line to loki: {err}");
            }
        }
    }
}

impl FrameLoggerT for FrameFileLogger {
    fn writeln(&self, text: &str) {
        let mut line = String::with_capacity(text.len() + 8);
        if self.prepend_timestamp {
            let time_str: DateTime<Local> = SystemTime::now().into();
            let timestamp = time_str.format("%H:%M:%S").to_string();
            line.push('[');
            line.push_str(timestamp.as_str());
            line.push_str("] ");
        }
        line.push_str(text);
        line.push('\n');

        match self.file_descriptor.lock() {
            Ok(mut fd) => {
                if let Err(io_err) = fd.write_all(line.as_bytes()) {
                    error!("Failed to write line to frame logger: {io_err}");
                }
            }
            Err(poison_err) => {
                error!("Failed to acquire lock: {poison_err}");
            }
        }
    }

    fn write(&self, bytes: &[u8]) {
        let mut buff: Vec<u8> = Vec::with_capacity(bytes.len());

        if self.prepend_timestamp {
            let linebreak = b'\n';
            for c in bytes {
                buff.push(*c);
                if *c == linebreak {
                    let time_str: DateTime<Local> = SystemTime::now().into();
                    let timestamp = time_str.format("%H:%M:%S").to_string();
                    buff.extend_from_slice(timestamp.as_bytes());
                }
            }
        } else {
            buff.append(&mut bytes.to_vec());
        }

        match self.file_descriptor.lock() {
            Ok(mut fd) => {
                if let Err(io_err) = fd.write_all(&buff) {
                    error!("Failed to write line to frame logger: {io_err}");
                }
            }
            Err(poison_err) => {
                error!("Failed to acquire lock: {poison_err}");
            }
        }
    }
}

#[cfg(test)]
/// A memory logger, meant for being used on test environments
pub struct TestLogger {
    lines: Mutex<Vec<String>>,
}

#[cfg(test)]
impl TestLogger {
    pub fn init() -> Self {
        TestLogger {
            lines: Mutex::new(Vec::new()),
        }
    }

    pub fn pop(&self) -> Option<String> {
        self.lines.lock().unwrap().pop()
    }

    #[allow(dead_code)]
    pub fn all(&self) -> Vec<String> {
        self.lines.lock().unwrap().clone()
    }
}

#[cfg(test)]
impl FrameLoggerT for TestLogger {
    fn writeln(&self, line: &str) {
        self.lines.lock().unwrap().push(line.to_string());

        println!("{}", line);
    }

    fn write(&self, bytes: &[u8]) {
        if let Ok(text) = std::str::from_utf8(bytes) {
            self.lines.lock().unwrap().push(text.to_string());
            print!("{}", text);
        } else {
            // If not valid UTF-8, store a descriptive message
            self.lines
                .lock()
                .unwrap()
                .push(format!("<binary data of {} bytes>", bytes.len()));
            println!("<binary data of {} bytes>", bytes.len());
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Read;
    use tempfile::NamedTempFile;

    #[test]
    fn test_frame_file_logger_write_basic() {
        // Create a temporary file for testing
        let temp_file = NamedTempFile::new().unwrap();
        let temp_path = temp_file.path().to_string_lossy().to_string();

        // Create logger with timestamp disabled
        let logger = FrameFileLogger::init(temp_path.clone(), false, None).unwrap();

        // Write some test content
        let test_content = b"Test content";
        logger.write(test_content);

        // Read back the content and verify
        let mut file = File::open(temp_path).unwrap();
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer).unwrap();

        assert_eq!(buffer, test_content);
    }

    #[test]
    fn test_frame_file_logger_write_with_timestamp() {
        // Create a temporary file for testing
        let temp_file = NamedTempFile::new().unwrap();
        let temp_path = temp_file.path().to_string_lossy().to_string();

        // Create logger with timestamp enabled
        let logger = FrameFileLogger::init(temp_path.clone(), true, None).unwrap();

        // Write content with newlines to test timestamp prepending
        let test_content = b"Line 1\nLine 2\nLine 3";
        logger.write(test_content);

        // Read back the content and verify
        let mut file = File::open(temp_path).unwrap();
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer).unwrap();

        // Validate that the buffer contains the original content
        assert!(buffer.len() >= test_content.len());

        // The output should contain the original content but may have timestamps added
        let output = String::from_utf8_lossy(&buffer);
        assert!(output.contains("Line 1"));
        assert!(output.contains("Line 2"));
        assert!(output.contains("Line 3"));
    }

    #[test]
    fn test_frame_file_logger_write_no_timestamp_binary_data() {
        // Create a temporary file for testing
        let temp_file = NamedTempFile::new().unwrap();
        let temp_path = temp_file.path().to_string_lossy().to_string();

        // Create logger with timestamp disabled
        let logger = FrameFileLogger::init(temp_path.clone(), false, None).unwrap();

        // Write binary data
        let binary_data = [0u8, 1u8, 2u8, 3u8, 4u8, 255u8];
        logger.write(&binary_data);

        // Read back the content and verify
        let mut file = File::open(temp_path).unwrap();
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer).unwrap();

        assert_eq!(buffer, binary_data);
    }

    #[test]
    fn test_frame_file_logger_write_multiple_writes() {
        // Create a temporary file for testing
        let temp_file = NamedTempFile::new().unwrap();
        let temp_path = temp_file.path().to_string_lossy().to_string();

        // Create logger with timestamp disabled for simplicity
        let logger = FrameFileLogger::init(temp_path.clone(), false, None).unwrap();

        // Write multiple times
        logger.write(b"First write. ");
        logger.write(b"Second write. ");
        logger.write(b"Third write.");

        // Read back the content and verify
        let mut file = File::open(temp_path).unwrap();
        let mut buffer = String::new();
        file.read_to_string(&mut buffer).unwrap();

        assert_eq!(buffer, "First write. Second write. Third write.");
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    #[test]
    fn test_describe_path_failure_reports_creds_and_dir() {
        let temp_file = NamedTempFile::new().unwrap();
        let path = temp_file.path();

        let diag = FrameFileLogger::describe_path_failure(path, Some((1234, 5678)), None);

        assert!(diag.contains("euid="), "diag missing euid: {diag}");
        assert!(
            diag.contains("intended chown uid=1234 gid=5678"),
            "diag missing intended chown: {diag}"
        );
        assert!(
            diag.contains("parent dir"),
            "diag missing parent dir: {diag}"
        );
        assert!(diag.contains("mode="), "diag missing mode: {diag}");
    }

    #[cfg(any(target_os = "linux", target_os = "macos"))]
    #[test]
    fn test_init_into_unwritable_dir_reports_failing_op() {
        // root bypasses DAC, so the unwritable-dir scenario can't be reproduced there.
        // SAFETY: geteuid is an always-successful syscall with no preconditions.
        if unsafe { nix::libc::geteuid() } == 0 {
            return;
        }

        let dir = tempfile::tempdir().unwrap();
        let locked = dir.path().join("locked");
        fs::create_dir(&locked).unwrap();
        fs::set_permissions(&locked, Permissions::from_mode(0o000)).unwrap();

        let log_path = locked.join("frame.rqlog");
        let result = FrameFileLogger::init(log_path.to_string_lossy().to_string(), false, None);

        // Restore perms so the tempdir can be cleaned up.
        let _ = fs::set_permissions(&locked, Permissions::from_mode(0o755));

        let err = match result {
            Ok(_) => panic!("expected init to fail on an unwritable dir"),
            Err(err) => err,
        };
        let msg = format!("{err:?}");
        assert!(
            msg.contains("failed to create frame log file"),
            "error should name the failing op: {msg}"
        );
        assert!(
            msg.contains("euid="),
            "error should include diagnostics: {msg}"
        );
    }

    #[test]
    fn test_frame_file_logger_write_empty() {
        // Create a temporary file for testing
        let temp_file = NamedTempFile::new().unwrap();
        let temp_path = temp_file.path().to_string_lossy().to_string();

        // Create logger with timestamp disabled
        let logger = FrameFileLogger::init(temp_path.clone(), false, None).unwrap();

        // Write empty content
        logger.write(b"");

        // Read back the content and verify
        let mut file = File::open(temp_path).unwrap();
        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer).unwrap();

        assert_eq!(buffer.len(), 0);
    }
}
