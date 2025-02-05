use std::panic::catch_unwind;
use std::sync::Arc;

use crate::running_frame::RunningFrame;
use crate::running_frame::RunningFrameCache;
use crate::servant::Result;
use opencue_proto::rqd::{
    rqd_interface_server::RqdInterface, RqdStaticGetRunFrameRequest, RqdStaticGetRunFrameResponse,
    RqdStaticGetRunningFrameStatusRequest, RqdStaticGetRunningFrameStatusResponse,
    RqdStaticKillRunningFrameRequest, RqdStaticKillRunningFrameResponse,
    RqdStaticLaunchFrameRequest, RqdStaticLaunchFrameResponse, RqdStaticLockAllRequest,
    RqdStaticLockAllResponse, RqdStaticLockRequest, RqdStaticLockResponse,
    RqdStaticNimbyOffRequest, RqdStaticNimbyOffResponse, RqdStaticNimbyOnRequest,
    RqdStaticNimbyOnResponse, RqdStaticRebootIdleRequest, RqdStaticRebootIdleResponse,
    RqdStaticRebootNowRequest, RqdStaticRebootNowResponse, RqdStaticReportStatusRequest,
    RqdStaticReportStatusResponse, RqdStaticRestartIdleRequest, RqdStaticRestartIdleResponse,
    RqdStaticRestartNowRequest, RqdStaticRestartNowResponse, RqdStaticShutdownIdleRequest,
    RqdStaticShutdownIdleResponse, RqdStaticShutdownNowRequest, RqdStaticShutdownNowResponse,
    RqdStaticUnlockAllRequest, RqdStaticUnlockAllResponse, RqdStaticUnlockRequest,
    RqdStaticUnlockResponse,
};
use tonic::{async_trait, Request, Response};
use tracing::error;

/// Servant for the grpc Rqd interface
pub struct RqdServant {
    running_frame_cache: Arc<RunningFrameCache>,
}

impl RqdServant {
    pub fn init(running_frame_cache: Arc<RunningFrameCache>) -> Self {
        Self {
            running_frame_cache,
        }
    }
}

#[async_trait]
impl RqdInterface for RqdServant {
    /// Return the RunFrame by id
    async fn get_run_frame(
        &self,
        request: Request<RqdStaticGetRunFrameRequest>,
    ) -> Result<Response<RqdStaticGetRunFrameResponse>> {
        todo!()
    }
    /// Return the RunningFrameStatus report
    async fn get_running_frame_status(
        &self,
        request: Request<RqdStaticGetRunningFrameStatusRequest>,
    ) -> Result<Response<RqdStaticGetRunningFrameStatusResponse>> {
        todo!()
    }
    /// Kill the running frame by frame id
    async fn kill_running_frame(
        &self,
        request: Request<RqdStaticKillRunningFrameRequest>,
    ) -> Result<Response<RqdStaticKillRunningFrameResponse>> {
        todo!()
    }

    /// Launch a new running frame
    async fn launch_frame(
        &self,
        request: Request<RqdStaticLaunchFrameRequest>,
    ) -> Result<Response<RqdStaticLaunchFrameResponse>> {
        let run_frame = request
            .into_inner()
            .run_frame
            .ok_or_else(|| tonic::Status::invalid_argument("Missing run_frame in request"))?;

        let running_frame: Arc<RunningFrame> = Arc::new(run_frame.into());
        self.running_frame_cache
            .insert_running_frame(Arc::clone(&running_frame));

        // Fire and forget
        let _t = tokio::task::spawn_blocking(move || {
            if let Err(e) = catch_unwind(|| running_frame.run()) {
                error!("Panicked while trying to run a frame {:?}", e);
                // TODO: Trigger frame clean up logic
            }
        });
        // Don't wait for frame to complete to return a response
        Ok(Response::new(RqdStaticLaunchFrameResponse {}))
    }

    /// Lock a number of cores
    async fn lock(
        &self,
        request: Request<RqdStaticLockRequest>,
    ) -> Result<Response<RqdStaticLockResponse>> {
        todo!()
    }
    /// Lock all
    async fn lock_all(
        &self,
        request: Request<RqdStaticLockAllRequest>,
    ) -> Result<Response<RqdStaticLockAllResponse>> {
        todo!()
    }
    /// Disable NIMBY on host
    async fn nimby_off(
        &self,
        request: Request<RqdStaticNimbyOffRequest>,
    ) -> Result<Response<RqdStaticNimbyOffResponse>> {
        todo!()
    }
    /// Enable NIMBY on host
    async fn nimby_on(
        &self,
        request: Request<RqdStaticNimbyOnRequest>,
    ) -> Result<Response<RqdStaticNimbyOnResponse>> {
        todo!()
    }
    /// Reboot the host when it becomes idle
    async fn reboot_idle(
        &self,
        request: Request<RqdStaticRebootIdleRequest>,
    ) -> Result<Response<RqdStaticRebootIdleResponse>> {
        todo!()
    }
    /// Reboot the host now
    async fn reboot_now(
        &self,
        request: Request<RqdStaticRebootNowRequest>,
    ) -> Result<Response<RqdStaticRebootNowResponse>> {
        todo!()
    }
    /// Return the HostReport
    async fn report_status(
        &self,
        request: Request<RqdStaticReportStatusRequest>,
    ) -> Result<Response<RqdStaticReportStatusResponse>> {
        todo!()
    }
    /// [Deprecated] Restart the rqd process when it becomes idle
    async fn restart_rqd_idle(
        &self,
        request: Request<RqdStaticRestartIdleRequest>,
    ) -> Result<Response<RqdStaticRestartIdleResponse>> {
        todo!()
    }
    /// [Deprecated] Restart rqd process now
    async fn restart_rqd_now(
        &self,
        request: Request<RqdStaticRestartNowRequest>,
    ) -> Result<Response<RqdStaticRestartNowResponse>> {
        let _ = request;
        todo!()
    }
    /// Turn off rqd when it becomes idle
    async fn shutdown_rqd_idle(
        &self,
        request: Request<RqdStaticShutdownIdleRequest>,
    ) -> Result<Response<RqdStaticShutdownIdleResponse>> {
        todo!()
    }
    /// Stop rqd now
    async fn shutdown_rqd_now(
        &self,
        request: Request<RqdStaticShutdownNowRequest>,
    ) -> Result<Response<RqdStaticShutdownNowResponse>> {
        todo!()
    }
    /// Unlock a number of cores
    async fn unlock(
        &self,
        request: Request<RqdStaticUnlockRequest>,
    ) -> Result<Response<RqdStaticUnlockResponse>> {
        todo!()
    }
    /// Unlock all cores
    async fn unlock_all(
        &self,
        request: Request<RqdStaticUnlockAllRequest>,
    ) -> Result<Response<RqdStaticUnlockAllResponse>> {
        todo!()
    }
}
