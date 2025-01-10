use std::net::{Ipv4Addr, SocketAddr};

use miette::{IntoDiagnostic, Result};
use opencue_proto::report::rqd_report_interface_server::RqdReportInterfaceServer;
use report_servant::ReportServant;
use structopt::StructOpt;
use tonic::transport::Server;
mod report_servant;

#[derive(StructOpt, Debug)]
pub struct DummyCuebotCli {
    #[structopt(subcommand)]
    subcommands: SubCommands,
}

#[derive(StructOpt, Debug)]
enum SubCommands {
    ReportServer(ReportServerCmd),
    RqdClient(RqdClientCmd),
}

#[derive(StructOpt, Debug)]
struct ReportServerCmd {
    #[structopt(long, short = "p", long_help = "Port to bind to")]
    port: Option<u16>,
}

#[derive(StructOpt, Debug)]
struct RqdClientCmd {
    #[structopt(long, short = "h", long_help = "Rqd's hostname")]
    hostname: Option<String>,

    #[structopt(long, short = "p", long_help = "Port to bind to")]
    port: Option<String>,

    #[structopt(subcommand)]
    api_method: ApiMethod,
}

#[derive(StructOpt, Debug)]
enum ApiMethod {
    LaunchFrame(LaunchFrameCmd),
}

#[derive(StructOpt, Debug)]
struct LaunchFrameCmd {}

impl DummyCuebotCli {
    pub async fn run(&self) -> Result<()> {
        match &self.subcommands {
            SubCommands::ReportServer(report_server_cmd) => {
                Self::start_server(report_server_cmd.port.clone().unwrap_or(4343)).await
            }
            SubCommands::RqdClient(rqd_client_cmd) => todo!(),
        }
    }

    async fn start_server(port: u16) -> Result<()> {
        let address = SocketAddr::new(std::net::IpAddr::V4(Ipv4Addr::new(0, 0, 0, 0)), port);

        println!("Starting server at {}", address);
        Server::builder()
            .add_service(RqdReportInterfaceServer::new(ReportServant {}))
            .serve(address)
            .await
            .into_diagnostic()
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let opt = DummyCuebotCli::from_args();
    opt.run().await
}
