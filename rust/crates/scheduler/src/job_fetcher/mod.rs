use std::sync::Arc;

use futures::{StreamExt, stream};
use tracing::{error, info};

use crate::cluster::ClusterFeed;
use crate::config::CONFIG;
use crate::dao::JobDao;
use crate::job_dispatcher::BookJobEventHandler;
use crate::models::DispatchJob;

pub async fn run(cluster_feed: ClusterFeed) -> miette::Result<()> {
    let job_fetcher = Arc::new(JobDao::from_config(&CONFIG.database).await?);
    let job_event_handler = Arc::new(BookJobEventHandler::new().await?);

    stream::iter(cluster_feed)
        .map(|cluster| {
            let job_fetcher = job_fetcher.clone();
            let job_event_handler = job_event_handler.clone();
            async move {
                let mut stream:
                    // Ugly splicit type is needed here to make the compiler happy
                    Box<dyn futures::Stream<Item = Result<_, sqlx::Error>> + Unpin + Send> =
                match cluster.facility_show {
                    Some((facility_id, show_id)) => Box::new(
                        job_fetcher.query_active_jobs_by_show_facility_tag(
                            show_id,
                            facility_id,
                            cluster.tag)),
                    None => Box::new(job_fetcher.query_active_jobs_by_tag(cluster.tag))
                };

                while let Some(job) = stream.next().await {
                    match job {
                        Ok(job_model) => {
                            let job: DispatchJob = job_model.into();
                            info!("Found job: {}", job);
                            job_event_handler.process(job).await;
                        }
                        Err(err) => {
                            error!("Failed to fetch job: {}", err);
                        }
                    }
                }
            }
        })
        .buffer_unordered(CONFIG.queue.stream.cluster_buffer_size)
        .collect::<Vec<()>>()
        .await;

    Ok(())
}
