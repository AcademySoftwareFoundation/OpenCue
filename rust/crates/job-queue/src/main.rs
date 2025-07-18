use std::{str::FromStr, time::Duration};

use futures::StreamExt;
use miette::IntoDiagnostic;
use structopt::StructOpt;
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};

use crate::config::Config;

mod config;
mod consumer;
mod models;
mod pgpool;
mod producer;

#[derive(StructOpt, Debug)]
pub struct JobQueueCli {
    #[structopt(subcommand)]
    subcommands: SubCommands,
}

#[derive(StructOpt, Debug)]
enum SubCommands {
    JobProducer(JobProducerCmd),
    JobDispatcher(JobDispatcherCmd),
}

#[derive(StructOpt, Debug)]
struct JobDispatcherCmd {
    #[structopt(long, long_help = "Don't dispatch jobs, only print to stdout")]
    dry_run: bool,
}

#[derive(StructOpt, Debug)]
struct JobProducerCmd {
    #[structopt(
        long,
        short = "i",
        long_help = "Interval the consumer loop should query and publish job updates to the queue"
    )]
    monitor_interval_seconds: Option<u64>,
}

impl JobQueueCli {
    async fn run(&self, config: Config) -> miette::Result<()> {
        match &self.subcommands {
            SubCommands::JobProducer(job_producer_cmd) => {
                producer::run(
                    config,
                    job_producer_cmd
                        .monitor_interval_seconds
                        .map(Duration::from_secs),
                )
                .await
            }
            SubCommands::JobDispatcher(job_dispatcher_cmd) => {
                consumer::run(config, job_dispatcher_cmd.dry_run).await
            }
        }
    }
}

fn main() -> miette::Result<()> {
    let config = Config::load()?;

    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(config.queue.worker_threads)
        .enable_all()
        .build()
        .into_diagnostic()?;

    runtime.block_on(async_main(config))
}

async fn async_main(config: Config) -> miette::Result<()> {
    let log_level =
        tracing::Level::from_str(config.logging.level.as_str()).expect("Invalid log level");
    let log_builder = tracing_subscriber::fmt()
        .with_timer(tracing_subscriber::fmt::time::SystemTime)
        .pretty()
        .with_max_level(log_level);
    if config.logging.file_appender {
        let file_appender = RollingFileAppenderBase::new(
            config.logging.path.clone(),
            RollingConditionBase::new().max_size(1024 * 1024),
            7,
        )
        .expect("Failed to create appender");
        let (non_blocking, _guard) = tracing_appender::non_blocking(file_appender);
        log_builder.with_writer(non_blocking).init();
    } else {
        log_builder.init();
    }

    let opts = JobQueueCli::from_args();
    opts.run(config).await
}
