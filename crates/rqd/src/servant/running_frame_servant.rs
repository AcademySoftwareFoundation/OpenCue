use std::sync::Arc;

use crate::running_frame::RunningFrameCache;
use opencue_proto::rqd::{
    running_frame_server::RunningFrame, RunningFrameKillRequest, RunningFrameKillResponse,
    RunningFrameStatusRequest, RunningFrameStatusResponse,
};
use tonic::async_trait;

use crate::servant::Result;

/// Servant for the grpc RunningFrame interface
pub struct RunningFrameServant {
    running_frame_cache: Arc<RunningFrameCache>,
}

impl RunningFrameServant {
    pub fn init(running_frame_cache: Arc<RunningFrameCache>) -> Self {
        Self {
            running_frame_cache,
        }
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
