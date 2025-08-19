use std::{str::FromStr, time::Duration};

use miette::IntoDiagnostic;
use structopt::StructOpt;
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};

use crate::config::CONFIG;

mod config;
mod dao;
mod job_dispatcher;
mod job_fetcher;
mod models;
mod pgpool;

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
struct JobDispatcherCmd {}

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
    async fn run(&self) -> miette::Result<()> {
        match &self.subcommands {
            SubCommands::JobProducer(job_producer_cmd) => {
                job_fetcher::run(
                    job_producer_cmd
                        .monitor_interval_seconds
                        .map(Duration::from_secs),
                )
                .await
            }
            SubCommands::JobDispatcher(_) => job_dispatcher::run().await,
        }
    }
}

fn main() -> miette::Result<()> {
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(CONFIG.queue.worker_threads)
        .enable_all()
        .build()
        .into_diagnostic()?;

    runtime.block_on(async_main())
}

async fn async_main() -> miette::Result<()> {
    let log_level =
        tracing::Level::from_str(CONFIG.logging.level.as_str()).expect("Invalid log level");
    let log_builder = tracing_subscriber::fmt()
        .with_timer(tracing_subscriber::fmt::time::SystemTime)
        .pretty()
        .with_max_level(log_level);
    if CONFIG.logging.file_appender {
        let file_appender = RollingFileAppenderBase::new(
            CONFIG.logging.path.clone(),
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
    opts.run().await
}
