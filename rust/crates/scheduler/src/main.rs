use std::str::FromStr;

use miette::IntoDiagnostic;
use structopt::StructOpt;
use tracing_rolling_file::{RollingConditionBase, RollingFileAppenderBase};

use crate::{cluster::ClusterFeed, config::CONFIG};

mod cluster;
mod cluster_key;
mod config;
mod dao;
mod host_cache;
mod job_dispatcher;
mod job_fetcher;
mod models;
mod pgpool;

#[derive(StructOpt, Debug)]
pub struct JobQueueCli {
    #[structopt(
        long,
        short = "a",
        long_help = "A comma separated list of allocations (eg. lax.general). \
        When provided, the service will not query for existing allocations"
    )]
    allocations: Option<CommaSeparatedList>,

    #[structopt(
        long,
        short = "s",
        long_help = "A comma separated list of Shows. When provided, the service will not query for existing shows",
        required_if("allocations", "")
    )]
    shows: Option<CommaSeparatedList>,
}

#[derive(Debug, Clone)]
pub struct CommaSeparatedList(pub Vec<String>);

impl FromStr for CommaSeparatedList {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(CommaSeparatedList(
            s.split(",").map(|v| v.trim().to_string()).collect(),
        ))
    }
}

impl JobQueueCli {
    async fn run(&self) -> miette::Result<()> {
        // let cluster_feed = match (&self.allocations, &self.shows) {
        //     (Some(allocations), Some(shows)) => {
        //         ClusterFeed::from_predefined_values(&allocations.0, &shows.0).await
        //     }
        //     (None, None) => {
        //         let subscription_dao = SubscriptionDao::from_config(&CONFIG.database).await?;
        //         ClusterFeed::from_database(subscription_dao).await
        //     }
        //     _ => Err(miette!("")),
        // }?;
        let cluster_feed = ClusterFeed::load_all().await?;
        job_fetcher::run(cluster_feed).await
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
