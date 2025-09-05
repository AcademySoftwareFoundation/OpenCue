use std::sync::Arc;

use futures::{StreamExt, stream};
use tracing::{debug, error, info};

use crate::cluster::{Cluster, ClusterFeed};
use crate::config::CONFIG;
use crate::dao::JobDao;
use crate::job_dispatcher::BookJobEventHandler;
use crate::models::DispatchJob;

pub async fn run(cluster_feed: ClusterFeed) -> miette::Result<()> {
    let job_fetcher = Arc::new(JobDao::from_config(&CONFIG.database).await?);
    let job_event_handler = Arc::new(BookJobEventHandler::new().await?);
    debug!("Starting scheduler feed");

    stream::iter(cluster_feed)
        .map(|cluster| {
            let job_fetcher = job_fetcher.clone();
            let job_event_handler = job_event_handler.clone();
            async move {
                let mut stream:
                    // Ugly splicit type is needed here to make the compiler happy
                    Box<dyn futures::Stream<Item = Result<_, sqlx::Error>> + Unpin + Send> =
                match &cluster {
                    Cluster::ComposedKey(cluster_key) => Box::new(
                                        job_fetcher.query_pending_jobs_by_show_facility_tag(
                                            cluster_key.show_id.clone(),
                                            cluster_key.facility_id.clone(),
                                            cluster_key.tag.to_string())),
                    Cluster::TagsKey(tags) =>
                        Box::new(
                            job_fetcher.query_pending_jobs_by_tags(
                                tags.iter()
                                    .map(|v| v.to_string()).collect())
                        ),
                };

                while let Some(job) = stream.next().await {
                    match job {
                        Ok(job_model) => {
                            let job = DispatchJob::new(job_model, cluster.clone());
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
