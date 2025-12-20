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

use opencue_proto::{
    rqd::{
        running_frame_server::RunningFrame, RunningFrameKillRequest, RunningFrameKillResponse,
        RunningFrameStatusRequest, RunningFrameStatusResponse,
    },
    WithUuid,
};
use tonic::{async_trait, Response};

use crate::{frame::manager, servant::Result};

/// Servant for the grpc RunningFrame interface
pub struct RunningFrameServant {}

#[async_trait]
impl RunningFrame for RunningFrameServant {
    async fn kill(
        &self,
        request: tonic::Request<RunningFrameKillRequest>,
    ) -> Result<tonic::Response<RunningFrameKillResponse>> {
        let kill_request = request.into_inner();
        if kill_request.message.is_empty() {
            return Err(tonic::Status::failed_precondition(format!(
                "Could not kill frame {} without a reason (message is empty)",
                kill_request.uuid()
            )));
        }
        let frame_manager = manager::instance()
            .await
            .map_err(|err| tonic::Status::internal(err.to_string()))?;

        match frame_manager
            .kill_running_frame(&kill_request.uuid(), kill_request.message.clone())
            .await
        {
            Ok(Some(_)) => Ok(Response::new(RunningFrameKillResponse {})),
            Ok(None) => Err(tonic::Status::not_found(format!(
                "Could not find frame with id {} to kill",
                kill_request.uuid()
            ))),
            Err(err) => Err(tonic::Status::failed_precondition(format!(
                "Could not kill frame {} due to: {}",
                kill_request.uuid(),
                err,
            ))),
        }
    }

    async fn status(
        &self,
        request: tonic::Request<RunningFrameStatusRequest>,
    ) -> Result<tonic::Response<RunningFrameStatusResponse>> {
        let status_request = request.into_inner();

        let frame_manager = manager::instance()
            .await
            .map_err(|err| tonic::Status::internal(err.to_string()))?;

        match frame_manager.get_running_frame(&status_request.uuid()) {
            Some(running_frame) => Ok(Response::new(RunningFrameStatusResponse {
                running_frame_info: Some(running_frame.clone_into_running_frame_info()),
            })),
            None => Err(tonic::Status::not_found(format!(
                "Could not find frame with id {} on this host",
                status_request.uuid()
            ))),
        }
    }
}
