use std::net::{Ipv4Addr, SocketAddr};

use miette::IntoDiagnostic;
use opencue_proto::report::rqd_report_interface_server::RqdReportInterfaceServer;
use opencue_proto::report::{
    RqdReportRqdStartupRequest, RqdReportRqdStartupResponse,
    RqdReportRunningFrameCompletionRequest, RqdReportRunningFrameCompletionResponse,
    RqdReportStatusRequest, RqdReportStatusResponse,
    rqd_report_interface_server::RqdReportInterface,
};
use tonic::transport::Server;
use tonic::{Request, Response, Status, async_trait};

pub struct ReportServant {}
#[async_trait]
impl RqdReportInterface for ReportServant {
    /// Send in when RQD starts up to announce new idle procs to the cue
    async fn report_rqd_startup(
        &self,
        request: Request<RqdReportRqdStartupRequest>,
    ) -> std::result::Result<Response<RqdReportRqdStartupResponse>, Status> {
        let report = request.into_inner().boot_report;
        println!(
            "RqdReport: Received a report_rqd_startup request with: {:?}",
            report
        );

        Ok(Response::new(RqdReportRqdStartupResponse {}))
    }
    /// Reports in a running frame
    async fn report_running_frame_completion(
        &self,
        request: Request<RqdReportRunningFrameCompletionRequest>,
    ) -> std::result::Result<Response<RqdReportRunningFrameCompletionResponse>, Status> {
        let report = request.into_inner().frame_complete_report;
        println!(
            "RqdReport: Received a report_running_frame_completion request with: {:?}",
            report
        );

        Ok(Response::new(RqdReportRunningFrameCompletionResponse {}))
    }
    /// An incremental status report sent by RQD
    async fn report_status(
        &self,
        request: Request<RqdReportStatusRequest>,
    ) -> std::result::Result<Response<RqdReportStatusResponse>, Status> {
        let report = request.into_inner().host_report;
        println!(
            "RqdReport: Received a report_status request with: {:?}",
            report
        );

        Ok(Response::new(RqdReportStatusResponse {}))
    }
}

pub struct DummyCuebotServer {}

impl DummyCuebotServer {
    pub async fn start_server(port: u16) -> miette::Result<()> {
        let address = SocketAddr::new(std::net::IpAddr::V4(Ipv4Addr::new(0, 0, 0, 0)), port);

        println!("Starting server at {}", address);
        Server::builder()
            .add_service(RqdReportInterfaceServer::new(ReportServant {}))
            .serve(address)
            .await
            .into_diagnostic()
    }
}
