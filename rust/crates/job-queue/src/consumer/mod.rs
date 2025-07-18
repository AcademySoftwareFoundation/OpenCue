mod dispatcher;
mod executor;
mod host_fetcher;
mod job_consumer;
mod layer_fetcher;

use crate::config::Config;
use job_consumer::GeneralJobDispatcher;

pub async fn run(config: Config, dry_run: bool) -> miette::Result<()> {
    let job_dispatcher = GeneralJobDispatcher::from_config(&config).await?;

    job_dispatcher.start(dry_run).await
}
