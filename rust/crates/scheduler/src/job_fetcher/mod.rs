mod job_producer;

use std::time::Duration;

use futures::StreamExt;
use tokio::time;
use tracing::{error, info, warn};

use crate::config::CONFIG;
use crate::dao::JobDao;
use crate::models::DispatchJob;

pub async fn run(monitor_interval: Option<Duration>) -> miette::Result<()> {
    let job_fetcher = JobDao::from_config(&CONFIG.database).await?;
    let queue_manager = job_producer::GeneralJobQueue::from_config(&CONFIG.kafka)?;
    queue_manager.create_topic().await?;

    let mut interval = time::interval(monitor_interval.unwrap_or(CONFIG.queue.monitor_interval));
    loop {
        interval.tick().await;

        let mut stream = job_fetcher.query_active_jobs();

        while let Some(job) = stream.next().await {
            match job {
                Ok(job_model) => {
                    let job: DispatchJob = job_model.into();
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
