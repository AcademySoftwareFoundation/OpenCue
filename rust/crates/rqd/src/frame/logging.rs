use crate::config::{LoggerType, RunnerConfig};
use chrono::{DateTime, Local};
use miette::{IntoDiagnostic, Result};
use std::{
    fs::{self, File, Permissions},
    io::Write,
    os::unix::fs::PermissionsExt,
    path::Path,
    sync::{Arc, Mutex},
    time::SystemTime,
};
use tracing::error;

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
    pub fn from_logger_config(
        path: String,
        logger_config: &RunnerConfig,
        uid_gid: Option<(u32, u32)>,
    ) -> Result<Arc<dyn FrameLoggerT + Send + Sync + 'static>> {
        match logger_config.logger {
            LoggerType::File => {
                FrameFileLogger::init(path, logger_config.prepend_timestamp, uid_gid)
                    .map(|a| Arc::new(a) as Arc<dyn FrameLoggerT + Send + Sync + 'static>)
            }
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
            Self::rotate_existing_files(&path)?;
        } else if let Some(parent_path) = log_path.parent() {
            if !parent_path.exists() {
                fs::create_dir_all(parent_path).into_diagnostic()?;
                if let Some((uid, gid)) = uid_gid {
                    Self::change_ownership(parent_path, uid, gid)?;
                }
            }
        }

        let file = File::create(log_path).into_diagnostic()?;
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

        use miette::Context;

        fs::set_permissions(path, Permissions::from_mode(0o775))
            .into_diagnostic()
            .wrap_err(format!("Failed to change log dir permissions: {path:?}"))?;

        chown(path, Some(uid), Some(gid))
            .into_diagnostic()
            .wrap_err(format!("Failed to change log dir ownership: {path:?}"))
    }

    #[cfg(target_os = "windows")]
    fn change_ownership(_path: &String, _uid: u32, _gid: u32) -> Result<()> {
        Ok(())
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
