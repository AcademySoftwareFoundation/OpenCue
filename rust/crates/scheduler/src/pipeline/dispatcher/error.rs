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

    #[error("DispatchError: Unexpected Failure")]
    DbFailure(sqlx::Error),

    #[error("DispatchError: Allocation over burst")]
    AllocationOverBurst(String),

    #[error("DispatchError: Dispatch happened but something failed after that")]
    FailureAfterDispatch(Error),

    #[error("DispatchError: Failed to update frame on the database")]
    FailedToStartOnDb(sqlx::Error),

    #[error("DispatchError: Failed to open a GRPC connection")]
    FailureGrpcConnection(String, Error),

    #[error("DispatchError: Failed to execute command on GRPC interface")]
    GrpcFailure(tonic::Status),
}

#[derive(Debug, Error, Diagnostic)]
pub enum DispatchVirtualProcError {
    #[error("Allocation over burst")]
    AllocationOverBurst(DispatchError),

    #[error("Failed to start frame on database")]
    FailedToStartOnDb(DispatchError),

    #[error("Failed to lock frame on database")]
    FailedToLockForUpdate(sqlx::Error),

    #[error("Failed to connect to RQD on host {host}")]
    RqdConnectionFailed { host: String, error: Error },

    #[error("Failure after dispatch")]
    FailureAfterDispatch(DispatchError),
}
