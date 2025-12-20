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

    #[error("DispatchError: Failed to update frame on the database")]
    FailedToStartOnDb(sqlx::Error),

    #[error("DispatchError: Failed to create proc on database for frame={frame_id}, host={host_id}. {error:?}")]
    FailedToCreateProc {
        error: sqlx::Error,
        frame_id: String,
        host_id: String,
    },

    #[error("DispatchError: Failed to update proc resources on database")]
    FailedToUpdateResources(Error),

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
    FrameCouldNotBeUpdated,

    #[error("Failed to connect to RQD on host {host}")]
    RqdConnectionFailed { host: String, error: Error },
}
