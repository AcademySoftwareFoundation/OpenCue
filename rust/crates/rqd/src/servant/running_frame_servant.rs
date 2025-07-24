use std::sync::Arc;

use opencue_proto::{
    WithUuid,
    rqd::{
        RunningFrameKillRequest, RunningFrameKillResponse, RunningFrameStatusRequest,
        RunningFrameStatusResponse, running_frame_server::RunningFrame,
    },
};
use tonic::{Response, async_trait};

use crate::{frame::manager::FrameManager, servant::Result};

/// Servant for the grpc RunningFrame interface
pub struct RunningFrameServant {
    frame_manager: Arc<FrameManager>,
}

impl RunningFrameServant {
    pub fn init(frame_manager: Arc<FrameManager>) -> Self {
        Self { frame_manager }
    }
}

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

        match self
            .frame_manager
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

        match self.frame_manager.get_running_frame(&status_request.uuid()) {
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
