use std::sync::Arc;

use opencue_proto::rqd::{
    RunningFrameKillRequest, RunningFrameKillResponse, RunningFrameStatusRequest,
    RunningFrameStatusResponse, running_frame_server::RunningFrame,
};
use tonic::async_trait;

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
        todo!()
    }

    async fn status(
        &self,
        request: tonic::Request<RunningFrameStatusRequest>,
    ) -> Result<tonic::Response<RunningFrameStatusResponse>> {
        todo!()
    }
}
