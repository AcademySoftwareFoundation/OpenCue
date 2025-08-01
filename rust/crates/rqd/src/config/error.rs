use miette::Diagnostic;
use thiserror::Error;
use tonic::Status;

//===Scheduler Config Error===
#[derive(Debug, Error, Diagnostic)]
pub enum RqdConfigError {
    #[error("Failed to load config file")]
    LoadConfigError(String),

    #[error("Failed to start application via config file")]
    StartFromConfigError(String),

    #[error("Invalid Path configuration")]
    InvalidPath(String),
}

impl From<RqdConfigError> for Status {
    fn from(e: RqdConfigError) -> Self {
        match e {
            RqdConfigError::LoadConfigError(msg) => {
                Status::invalid_argument(format!("Failed to load config: {}", msg))
            }
            RqdConfigError::StartFromConfigError(msg) => {
                Status::internal(format!("Failed to start: {}", msg))
            }
            RqdConfigError::InvalidPath(msg) => {
                Status::invalid_argument(format!("Invalid path: {}", msg))
            }
        }
    }
}
