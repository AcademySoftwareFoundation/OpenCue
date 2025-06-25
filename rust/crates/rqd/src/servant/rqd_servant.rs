use std::sync::Arc;

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
use tracing::info;

pub type MachineImpl = dyn Machine + Sync + Send;

/// Servant for the grpc Rqd interface
pub struct RqdServant {
    machine: Arc<MachineImpl>,
    frame_manager: Arc<FrameManager>,
}

impl RqdServant {
    pub fn init(machine: Arc<MachineImpl>, frame_manager: Arc<FrameManager>) -> Self {
        Self {
            machine,
            frame_manager,
        }
    }
}

#[async_trait]
impl RqdInterface for RqdServant {
    /// [Deprecated] Return the RunFrame by id
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
            .map(|frame| frame.clone_into_running_frame_info())
            .ok_or(tonic::Status::not_found(format!(
                "Could not find frame with id {frame_id}"
            )))?;

        Ok(Response::new(RqdStaticGetRunningFrameStatusResponse {
            running_frame_info: Some(running_frame),
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
        let cores_to_lock = request.into_inner().cores;
        let effectively_locked_amount = self.machine.lock_cores(cores_to_lock as u32).await;
        info!("Lock: {effectively_locked_amount} cores locked from the requeted {cores_to_lock}");

        Ok(Response::new(RqdStaticLockResponse {}))
    }

    /// Lock all
    async fn lock_all(
        &self,
        _request: Request<RqdStaticLockAllRequest>,
    ) -> Result<Response<RqdStaticLockAllResponse>> {
        self.machine.lock_all_cores().await;
        info!("Lock: All cores have been locked");

        Ok(Response::new(RqdStaticLockAllResponse {}))
    }

    /// Disable NIMBY on host
    async fn nimby_off(
        &self,
        _request: Request<RqdStaticNimbyOffRequest>,
    ) -> Result<Response<RqdStaticNimbyOffResponse>> {
        todo!()
    }

    /// Enable NIMBY on host
    async fn nimby_on(
        &self,
        _request: Request<RqdStaticNimbyOnRequest>,
    ) -> Result<Response<RqdStaticNimbyOnResponse>> {
        todo!()
    }

    /// Reboot the host when it becomes idle
    async fn reboot_idle(
        &self,
        _request: Request<RqdStaticRebootIdleRequest>,
    ) -> Result<Response<RqdStaticRebootIdleResponse>> {
        if let Err(err) = self.machine.reboot_if_idle().await {
            Err(tonic::Status::aborted(format!(
                "Failed to request reboot. {}",
                err
            )))?;
        }
        Ok(Response::new(RqdStaticRebootIdleResponse {}))
    }

    /// [Deprecated] Reboot the host now
    async fn reboot_now(
        &self,
        request: Request<RqdStaticRebootNowRequest>,
    ) -> Result<Response<RqdStaticRebootNowResponse>> {
        todo!(
            "Deprecated method not implemented by this interface {:?}",
            request
        )
    }

    /// Return the HostReport
    async fn report_status(
        &self,
        _request: Request<RqdStaticReportStatusRequest>,
    ) -> Result<Response<RqdStaticReportStatusResponse>> {
        let host_report = self.machine.collect_host_report().await;

        match host_report {
            Ok(report) => Ok(Response::new(RqdStaticReportStatusResponse {
                host_report: Some(report),
            })),
            Err(err) => Err(tonic::Status::internal(format!(
                "Failed to collect host report {:?}",
                err
            ))),
        }
    }

    /// [Deprecated] Restart the rqd process when it becomes idle
    async fn restart_rqd_idle(
        &self,
        request: Request<RqdStaticRestartIdleRequest>,
    ) -> Result<Response<RqdStaticRestartIdleResponse>> {
        todo!(
            "Deprecated method not implemented by this interface {:?}",
            request
        )
    }

    /// [Deprecated] Restart rqd process now
    async fn restart_rqd_now(
        &self,
        request: Request<RqdStaticRestartNowRequest>,
    ) -> Result<Response<RqdStaticRestartNowResponse>> {
        todo!(
            "Deprecated method not implemented by this interface {:?}",
            request
        )
    }

    /// [Deprecated] Turn off rqd when it becomes idle
    async fn shutdown_rqd_idle(
        &self,
        request: Request<RqdStaticShutdownIdleRequest>,
    ) -> Result<Response<RqdStaticShutdownIdleResponse>> {
        todo!(
            "Deprecated method not implemented by this interface {:?}",
            request
        )
    }
    /// Stop rqd now
    async fn shutdown_rqd_now(
        &self,
        _request: Request<RqdStaticShutdownNowRequest>,
    ) -> Result<Response<RqdStaticShutdownNowResponse>> {
        self.machine.quit().await;
        Ok(Response::new(RqdStaticShutdownNowResponse {}))
    }

    /// Unlock a number of cores
    async fn unlock(
        &self,
        request: Request<RqdStaticUnlockRequest>,
    ) -> Result<Response<RqdStaticUnlockResponse>> {
        let cores_to_unlock = request.into_inner().cores;
        let effectively_locked_amount = self.machine.unlock_cores(cores_to_unlock as u32).await;
        info!(
            "Unlock: {effectively_locked_amount} cores unlocked from the requeted {cores_to_unlock}"
        );

        Ok(Response::new(RqdStaticUnlockResponse {}))
    }

    /// Unlock all cores
    async fn unlock_all(
        &self,
        _request: Request<RqdStaticUnlockAllRequest>,
    ) -> Result<Response<RqdStaticUnlockAllResponse>> {
        self.machine.unlock_all_cores().await;
        info!("Unlock: All cores have been unlocked");

        Ok(Response::new(RqdStaticUnlockAllResponse {}))
    }
}
