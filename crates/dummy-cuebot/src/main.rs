use std::{collections::HashMap, str::FromStr};

use miette::Result;
use report_servant::DummyCuebotServer;
use rqd_client::DummyRqdClient;
use structopt::StructOpt;
mod report_servant;
mod rqd_client;

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
    #[structopt(
        long,
        short = "p",
        default_value = "4343",
        long_help = "Port to bind to"
    )]
    port: u16,
}

#[derive(StructOpt, Debug)]
struct RqdClientCmd {
    #[structopt(
        long,
        short = "h",
        default_value = "localhost",
        long_help = "Rqd's hostname"
    )]
    hostname: String,

    #[structopt(
        long,
        short = "p",
        default_value = "8444",
        long_help = "Port to bind to"
    )]
    port: u16,

    #[structopt(subcommand)]
    api_method: ApiMethod,
}

#[derive(StructOpt, Debug)]
enum ApiMethod {
    LaunchFrame(LaunchFrameCmd),
}

#[derive(StructOpt, Debug)]
struct LaunchFrameCmd {
    cmd: String,
    #[structopt(long, long_help = "Comma separate list of environment variables")]
    env: Option<EnvVars>,
    #[structopt(long, long_help = "Run command as myself")]
    run_as_user: bool,
}

#[derive(Debug, Clone)]
pub struct EnvVars(pub HashMap<String, String>);

impl FromStr for EnvVars {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let mut map = HashMap::new();

        for pair in s.split(',') {
            let parts: Vec<&str> = pair.split('=').collect();
            if parts.len() != 2 {
                return Err(format!("Invalid key-value pair: {}", pair));
            }

            map.insert(parts[0].trim().to_string(), parts[1].trim().to_string());
        }

        Ok(EnvVars(map))
    }
}

impl DummyCuebotCli {
    pub async fn run(&self) -> Result<()> {
        match &self.subcommands {
            SubCommands::ReportServer(report_server_cmd) => {
                DummyCuebotServer::start_server(report_server_cmd.port.clone()).await
            }
            SubCommands::RqdClient(rqd_client_cmd) => {
                let client =
                    DummyRqdClient::build(rqd_client_cmd.hostname.clone(), rqd_client_cmd.port)
                        .await?;
                match &rqd_client_cmd.api_method {
                    ApiMethod::LaunchFrame(launch_frame_cmd) => {
                        let uid = launch_frame_cmd
                            .run_as_user
                            .then(|| users::get_current_uid());
                        client
                            .launch_frame(
                                launch_frame_cmd.cmd.clone(),
                                launch_frame_cmd
                                    .env
                                    .clone()
                                    .unwrap_or(EnvVars(HashMap::new()))
                                    .0,
                                uid,
                            )
                            .await
                    }
                }
            }
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let opt = DummyCuebotCli::from_args();
    opt.run().await
}
