use crate::config::config::{LoggerType, RunnerConfig};
use miette::{IntoDiagnostic, Result};
use std::{
    fs::File,
    io::Write,
    sync::{Arc, Mutex},
};
use tracing::error;

pub type FrameLogger = Box<dyn FrameLoggerT + Sync + Send>;

pub trait FrameLoggerT {
    // Open logger for writing
    fn writeln(&self, line: &str);
}

pub struct FrameLoggerBuilder {}

impl FrameLoggerBuilder {
    pub fn fromLoggerConfig(
        path: String,
        logger_config: &RunnerConfig,
    ) -> Result<impl FrameLoggerT> {
        match logger_config.logger {
            crate::config::config::LoggerType::File => {
                FrameFileLogger::init(path, logger_config.prepend_timestamp)
            }
        }
    }
}

pub struct FrameFileLogger {
    path: String,
    prepend_timestamp: bool,
    file_descriptor: Mutex<File>,
}

impl FrameFileLogger {
    pub fn init(path: String, prepend_timestamp: bool) -> Result<Self> {
        let file_descriptor = Mutex::new(File::create(path.clone()).into_diagnostic()?);
        // TODO: Check if dir exists, check permissions and cycle old logs
        Ok(FrameFileLogger {
            path,
            prepend_timestamp,
            file_descriptor,
        })
    }
}

impl FrameLoggerT for FrameFileLogger {
    fn writeln(&self, line: &str) {
        let mut line_with_newline = String::with_capacity(line.len() + 1);
        line_with_newline.push_str(line);
        line_with_newline.push('\n');
        
        match self.file_descriptor.lock() {
            Ok(mut fd) => {
                if let Err(io_err) = fd.write_all(line_with_newline.as_bytes()) {
                    error!("Failed to write line to frame logger: {io_err}");
                }
            }
            Err(poison_err) => {
                error!("Failed to acquire lock: {poison_err}");
            }
        }
    }
}
