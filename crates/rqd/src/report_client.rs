use std::sync::Arc;

use crate::config::config::Config;
use async_trait::async_trait;
use miette::{Context, IntoDiagnostic, Result};
use opencue_proto::report::{self as pb, rqd_report_interface_client::RqdReportInterfaceClient};
use tokio::sync::Mutex;
use tonic::transport::Channel;

pub(crate) struct ReportClient {
    client: Arc<Mutex<RqdReportInterfaceClient<Channel>>>,
}

impl ReportClient {
    pub async fn build(config: &Config) -> Result<Self> {
        let client =
            RqdReportInterfaceClient::connect(format!("http://{}", config.grpc.cuebot_url))
                .await
                .into_diagnostic()
                .wrap_err("Failed to connect to Cuebot Report Server")?;
        Ok(Self {
            client: Arc::new(Mutex::new(client)),
        })
    }
}

#[async_trait]
pub trait ReportInterface {
    async fn send_start_up_report(
        &self,
        render_host: pb::RenderHost,
        core_detail: pb::CoreDetail,
    ) -> Result<()>;
    async fn send_frame_complete_report(
        &self,
        host: pb::RenderHost,
        frame: pb::RunningFrameInfo,
        exit_status: u32,
        exit_signal: u32,
        run_time: u32,
    ) -> Result<()>;
    async fn send_host_report(
        &self,
        host: pb::RenderHost,
        frames: Vec<pb::RunningFrameInfo>,
        core_info: pb::CoreDetail,
    ) -> Result<()>;
}

#[async_trait]
impl ReportInterface for ReportClient {
    async fn send_start_up_report(
        &self,
        render_host: pb::RenderHost,
        core_detail: pb::CoreDetail,
    ) -> Result<()> {
        let mut client = self.client.lock().await;
        let mut request = pb::RqdReportRqdStartupRequest::default();
        request.boot_report = Some(pb::BootReport {
            host: Some(render_host),
            core_info: Some(core_detail),
        });
        client.report_rqd_startup(request).await.into_diagnostic()?;
        Ok(())
    }

    async fn send_frame_complete_report(
        &self,
        render_host: pb::RenderHost,
        running_frame: pb::RunningFrameInfo,
        exit_status: u32,
        exit_signal: u32,
        run_time: u32,
    ) -> Result<()> {
        let mut client = self.client.lock().await;
        let mut request = pb::RqdReportRunningFrameCompletionRequest::default();
        request.frame_complete_report = Some(pb::FrameCompleteReport {
            host: Some(render_host),
            frame: Some(running_frame),
            exit_status: exit_status as i32,
            exit_signal: exit_signal as i32,
            run_time: run_time as i32,
        });
        client
            .report_running_frame_completion(request)
            .await
            .into_diagnostic()?;
        Ok(())
    }

    async fn send_host_report(
        &self,
        render_host: pb::RenderHost,
        running_frames: Vec<pb::RunningFrameInfo>,
        core_detail: pb::CoreDetail,
    ) -> Result<()> {
        let mut client = self.client.lock().await;
        let mut request = pb::RqdReportStatusRequest::default();
        request.host_report = Some(pb::HostReport {
            host: Some(render_host),
            frames: running_frames,
            core_info: Some(core_detail),
        });
        client.report_status(request).await.into_diagnostic()?;
        Ok(())
    }
}
