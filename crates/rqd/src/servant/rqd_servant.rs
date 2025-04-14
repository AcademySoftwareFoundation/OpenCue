use std::sync::Arc;

use crate::config::config::Config;
use crate::frame::manager::FrameManager;
use crate::servant::Result;
use crate::system::machine::Machine;
use opencue_proto::{
    WithUuid,
    rqd::{
        RqdStaticGetRunFrameRequest, RqdStaticGetRunFrameResponse,
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
        RqdStaticUnlockResponse, rqd_interface_server::RqdInterface,
    },
};
use tonic::{Request, Response, async_trait};

pub type MachineImpl = dyn Machine + Sync + Send;

/// Servant for the grpc Rqd interface
pub struct RqdServant {
    config: Config,
    machine: Arc<MachineImpl>,
    frame_manager: Arc<FrameManager>,
}

impl RqdServant {
    pub fn init(
        config: Config,
        machine: Arc<MachineImpl>,
        frame_manager: Arc<FrameManager>,
    ) -> Self {
        Self {
            config,
            machine,
            frame_manager,
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
        todo!(
            "Deprecated method not implemented by this interface {:?}",
            request
        )
    }

    /// Return the RunningFrameStatus report
    async fn get_running_frame_status(
        &self,
        request: Request<RqdStaticGetRunningFrameStatusRequest>,
    ) -> Result<Response<RqdStaticGetRunningFrameStatusResponse>> {
        let frame_id = request.into_inner().uuid();
        let running_frame = self
            .frame_manager
            .get_running_frame(&frame_id)
            .map(|frame| frame.into_running_frame_info())
            .ok_or(tonic::Status::not_found(format!(
                "Could not find frame with id {frame_id}"
            )))?;

        Ok(Response::new(RqdStaticGetRunningFrameStatusResponse {
            running_frame_info: running_frame,
        }))
    }

    /// Kill the running frame by frame id
    async fn kill_running_frame(
        &self,
        request: Request<RqdStaticKillRunningFrameRequest>,
    ) -> Result<Response<RqdStaticKillRunningFrameResponse>> {
        let kill_request = request.into_inner();
        if kill_request.message.is_empty() {
            return Err(tonic::Status::failed_precondition(format!(
                "Could not kill frame {} without a reason (message is empty)",
                kill_request.frame_id
            )));
        }

        match self
            .frame_manager
            .kill_running_frame(&kill_request.uuid(), kill_request.message)
            .await
        {
            Ok(Some(_)) => Ok(Response::new(RqdStaticKillRunningFrameResponse {})),
            Ok(None) => Err(tonic::Status::not_found(format!(
                "Could not find frame with id {} to kill",
                kill_request.frame_id
            ))),
            Err(err) => Err(tonic::Status::failed_precondition(format!(
                "Could not kill frame {} due to: {}",
                kill_request.frame_id, err,
            ))),
        }
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

        self.frame_manager.spawn(run_frame).await?;

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
