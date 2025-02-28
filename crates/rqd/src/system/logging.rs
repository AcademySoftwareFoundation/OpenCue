use crate::config::config::{LoggerType, RunnerConfig};
use chrono::Utc;
use miette::{IntoDiagnostic, Result, miette};
use std::{
    fs::{self, File, Permissions},
    io::Write,
    os::unix::fs::PermissionsExt,
    path::Path,
    sync::{Arc, Mutex},
};
use tracing::error;

pub type FrameLogger = Arc<dyn FrameLoggerT + Sync + Send>;

pub trait FrameLoggerT {
    // Open logger for writing
    fn writeln(&self, line: &str);
}

pub struct FrameLoggerBuilder {}

impl FrameLoggerBuilder {
    pub fn from_logger_config(
        path: String,
        logger_config: &RunnerConfig,
    ) -> Result<Arc<dyn FrameLoggerT + Send + Sync + 'static>> {
        match logger_config.logger {
            LoggerType::File => FrameFileLogger::init(path, logger_config.prepend_timestamp)
                .map(|a| Arc::new(a) as Arc<dyn FrameLoggerT + Send + Sync + 'static>),
        }
    }
}

pub struct FrameFileLogger {
    _path: String,
    prepend_timestamp: bool,
    file_descriptor: Mutex<File>,
}

impl FrameFileLogger {
    pub fn init(path: String, prepend_timestamp: bool) -> Result<Self> {
        let log_path = Path::new(path.as_str());
        if log_path.exists() {
            Self::rotate_existing_files(&path)?;
        } else if let Some(parent_path) = log_path.parent() {
            if !parent_path.exists() {
                fs::create_dir_all(parent_path).into_diagnostic()?;
                fs::set_permissions(parent_path, Permissions::from_mode(0o777))
                    .into_diagnostic()?;
            }
        }
        // TODO: Evaluate if changing the log file ownership is necessary

        let file = File::create(log_path).into_diagnostic()?;
        let file_descriptor = Mutex::new(file);
        Ok(FrameFileLogger {
            _path: path,
            prepend_timestamp,
            file_descriptor,
        })
    }

    fn rotate_existing_files(path: &String) -> Result<()> {
        let log_path = Path::new(path);
        if log_path.is_file() {
            let mut rotate_count = 1;
            let proposed_path = format!("{}.{}", path, rotate_count);
            while Path::new(&proposed_path).is_file() && rotate_count < 100 {
                rotate_count += 1;
            }
            let rotate_path = format!("{}.{}", path, rotate_count);
            fs::rename(log_path, Path::new(&rotate_path)).into_diagnostic()?;
        }
        Ok(())
    }
}

impl FrameLoggerT for FrameFileLogger {
    fn writeln(&self, text: &str) {
        let mut line = String::with_capacity(text.len() + 1);
        if self.prepend_timestamp {
            let timestamp = Utc::now().format("%H:%M:%S").to_string();
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
}
