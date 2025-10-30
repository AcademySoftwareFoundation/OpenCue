use miette::Diagnostic;
use thiserror::Error;
use tonic::Status;

//===Scheduler Config Error===
#[derive(Debug, Error, Diagnostic)]
pub enum JobQueueConfigError {
    #[error("Failed to load config file")]
    LoadConfigError(String),

    #[error("Failed to start application via config file")]
    StartFromConfigError(String),

    #[error("Invalid Path configuration")]
    InvalidPath(String),
}

impl From<JobQueueConfigError> for Status {
    fn from(e: JobQueueConfigError) -> Self {
        match e {
            JobQueueConfigError::LoadConfigError(msg) => {
                Status::invalid_argument(format!("Failed to load config: {}", msg))
            }
            JobQueueConfigError::StartFromConfigError(msg) => {
                Status::internal(format!("Failed to start: {}", msg))
            }
            JobQueueConfigError::InvalidPath(msg) => {
                Status::invalid_argument(format!("Invalid path: {}", msg))
            }
        }
    }
}
