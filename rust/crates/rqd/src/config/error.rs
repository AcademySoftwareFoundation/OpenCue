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
