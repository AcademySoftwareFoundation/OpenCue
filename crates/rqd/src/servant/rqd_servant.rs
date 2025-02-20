use std::panic::catch_unwind;
use std::sync::Arc;

use crate::config::config::Config;
use crate::monitor::system::Machine;
use crate::running_frame::RunningFrame;
use crate::running_frame::RunningFrameCache;
use crate::servant::Result;
use opencue_proto::host::HardwareState;
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

pub type MachineImpl = dyn Machine + Sync + Send;

/// Servant for the grpc Rqd interface
pub struct RqdServant {
    config: Config,
    running_frame_cache: Arc<RunningFrameCache>,
    machine: Arc<MachineImpl>,
}

impl RqdServant {
    pub fn init(
        config: Config,
        running_frame_cache: Arc<RunningFrameCache>,
        machine: Arc<MachineImpl>,
    ) -> Self {
        Self {
            config,
            running_frame_cache,
            machine,
        }
    }

    fn validate_frame(&self, running_frame: &RunningFrame) -> Result<()> {
        // Frame is already running
        if self.running_frame_cache.contains(&running_frame) {
            Err(tonic::Status::already_exists(format!(
                "Not lauching, frame is already running on this host {}",
                running_frame.frame_id
            )))?
        }
        // Trying to run as root
        if running_frame.requested_uid.unwrap_or(1) <= 0 {
            Err(tonic::Status::invalid_argument(format!(
                "Not launching, will not run frame as uid = {}",
                running_frame.requested_uid.unwrap_or(1)
            )))?
        }
        // Invalid number of cores
        if running_frame.num_cores <= 0 {
            Err(tonic::Status::invalid_argument(
                "Not launching, num_cores must be positive",
            ))?
        }
        // Fractional cpu cores are not allowed
        if running_frame.num_cores % 100 != 0 {
            Err(tonic::Status::invalid_argument(
                "Not launching, num_cores must be multiple of 100 (Fractional Cores are not allowed)"
            ))?
        }

        Ok(())
    }

    async fn validate_machine_state(&self, ignore_nimby: bool) -> Result<()> {
        // Hardware state is not UP
        if self
            .machine
            .hardware_state()
            .await
            .unwrap_or(HardwareState::Down)
            != HardwareState::Up
        {
            Err(tonic::Status::failed_precondition(
                "Not launching, host HardwareState is not Up",
            ))?
        }
        // Nimby locked
        if self.machine.nimby_locked().await && !ignore_nimby {}
        // TODO: Chech if nimby is active and user activity was detected

        Ok(())
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

        let running_frame: RunningFrame = run_frame.into();

        // Validate frame and machine state
        self.validate_frame(&running_frame)?;
        self.validate_machine_state(running_frame.ignore_nimby)
            .await?;

        // On cuebot, num_cores are multiplied by 100 to account for fractional reservations
        // rqd doesn't follow the same concept
        let cpu_request = running_frame.num_cores as u32 / 100;
        let cpu_list = self
            .machine
            .reserve_cpus(cpu_request)
            .await
            .map_err(|err| {
                tonic::Status::aborted(format!(
                    "Not launching, failed to reserve cpu resources {:?}",
                    err
                ))
            })?;

        // Although num_gpus is not required on a frame, the field is not optional on the proto
        // layer. =0 means None, !=0 means Some
        let gpu_list = match running_frame.num_gpus {
            0 => Vec::new(),
            _ => self
                .machine
                .reserve_gpus(running_frame.num_gpus as u32)
                .await
                .map_err(|err| {
                    tonic::Status::aborted(format!(
                        "Not launching, insufficient resources {:?}",
                        err
                    ))
                })?,
        };

        // Create user if required. uid and gid ranges have already been verified
        let uid = match running_frame.requested_uid {
            Some(uid) => self
                .machine
                .create_user_if_unexisting(&running_frame.user_name, uid, running_frame.gid)
                .await
                .map_err(|err| {
                    tonic::Status::aborted(format!(
                        "Not launching, user {}({}:{}) could not be created. {:?}",
                        running_frame.user_name, uid, running_frame.gid, err
                    ))
                })?,
            None => self.config.runner.default_uid,
        };

        // Update resource values on running_frame
        let running_frame = Arc::new(running_frame.with_resources(
            self.config.runner.clone(),
            uid,
            cpu_list,
            gpu_list,
        ));

        self.running_frame_cache
            .insert_running_frame(Arc::clone(&running_frame));

        // Fire and forget
        let _t = tokio::task::spawn_blocking(move || {
            if let Err(e) = catch_unwind(|| {
                if let Err(e) = running_frame.run() {
                    error!("Failed to run frame {:?}", e);
                }
            }) {
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
