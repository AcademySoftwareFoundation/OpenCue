use miette::{Diagnostic, Error};
use thiserror::Error;

#[derive(Debug, Error, Diagnostic)]
pub enum VirtualProcError {
    #[error("Failed to create Virtual Proc. Host resources extinguished.")]
    HostResourcesExtinguished(String),
}

#[derive(Debug, Error, Diagnostic)]
pub enum DispatchError {
    #[error("DispatchError: Failed to acquire lock")]
    HostLock(String),

    #[error("DispatchError: Unexpected Failure")]
    Failure(Error),

    #[error("DispatchError: Allocation over burst")]
    AllocationOverBurst(String),

    #[error("DispatchError: Dipatch happened but something failed after that")]
    FailureAfterDispatch(Error),

    #[error("DispatchError: Host resources extinguished")]
    HostResourcesExtinguished,

    #[error("DispatchError: Failed to update frame on the database")]
    FailedToStartOnDb(Error),
}
