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
}

impl From<RqdConfigError> for Status {
    fn from(e: RqdConfigError) -> Self {
        match e {
            _ => Status::invalid_argument("Server failed to start due to an invalid config file"),
        }
    }
}
