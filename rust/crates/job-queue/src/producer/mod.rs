mod job_dao;
mod queue;

use std::time::Duration;

use futures::StreamExt;
use tokio::time;
use tracing::{error, info, warn};

use crate::config::Config;

pub async fn run(config: Config, monitor_interval: Option<Duration>) -> miette::Result<()> {
    let job_fetcher = job_dao::JobDao::from_config(&config.database).await?;
    let queue_manager = queue::GeneralJobQueue::from_config(&config.kafka)?;
    queue_manager.create_topic().await?;

    let mut interval = time::interval(monitor_interval.unwrap_or(config.queue.monitor_interval));
    loop {
        interval.tick().await;

        let mut stream = job_fetcher.query_active_jobs();

        while let Some(job) = stream.next().await {
            match job {
                Ok(job_model) => {
                    let job = job_model.into();
                    info!("Found job: {}", job);
                    if let Err(err) = queue_manager.send(&job).await {
                        warn!("Failed to send job: {} to kafka", err)
                    }
                }
                Err(err) => {
                    error!("Failed to fetch job: {}", err);
                }
            }
        }
        info!("Finished streaming all jobs for this round")
    }
}
