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

use std::net::{Ipv4Addr, SocketAddr};

use miette::IntoDiagnostic;
use opencue_proto::report::rqd_report_interface_server::RqdReportInterfaceServer;
use opencue_proto::report::{
    rqd_report_interface_server::RqdReportInterface, RqdReportRqdStartupRequest,
    RqdReportRqdStartupResponse, RqdReportRunningFrameCompletionRequest,
    RqdReportRunningFrameCompletionResponse, RqdReportStatusRequest, RqdReportStatusResponse,
};
use opencue_proto::report::{
    RqdReportGetHostSlotsLimitRequest, RqdReportGetHostSlotsLimitResponse,
};
use tonic::transport::Server;
use tonic::{async_trait, Request, Response, Status};

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

    /// Get the host's slot limit
    async fn get_host_slots_limit(
        &self,
        request: tonic::Request<RqdReportGetHostSlotsLimitRequest>,
    ) -> std::result::Result<tonic::Response<RqdReportGetHostSlotsLimitResponse>, tonic::Status>
    {
        let name = request.into_inner().name;
        println!(
            "RqdReport: Received a get_host_slots_limit request with: {:?}",
            name
        );

        Ok(Response::new(RqdReportGetHostSlotsLimitResponse {
            slots_limit: -1,
        }))
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
