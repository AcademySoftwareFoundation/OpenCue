use std::sync::Arc;
use std::sync::atomic::AtomicUsize;

use futures::{StreamExt, stream};
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info};

use crate::cluster::{Cluster, ClusterFeed};
use crate::config::CONFIG;
use crate::dao::JobDao;
use crate::job_dispatcher::BookJobEventHandler;
use crate::models::DispatchJob;

pub async fn run(cluster_feed: ClusterFeed) -> miette::Result<()> {
    let job_fetcher = Arc::new(JobDao::from_config(&CONFIG.database).await?);
    let job_event_handler = Arc::new(BookJobEventHandler::new().await?);
    let cancel_token = CancellationToken::new();
    let cycles_without_jobs = Arc::new(AtomicUsize::new(0));
    debug!("Starting scheduler feed");

    stream::iter(cluster_feed)
        .map(|cluster| {
            let job_fetcher = job_fetcher.clone();
            let job_event_handler = job_event_handler.clone();
            let cancel_token = cancel_token.clone();
            let cycles_without_jobs = cycles_without_jobs.clone();

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

                let processed_jobs = AtomicUsize::new(0);
                while let Some(job) = stream.next().await {
                    match job {
                        Ok(job_model) => {
                            processed_jobs.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                            let job = DispatchJob::new(job_model, cluster.clone());
                            info!("Found job: {}", job);
                            job_event_handler.process(job).await;
                        }
                        Err(err) => {
                            cancel_token.cancel();
                            error!("Failed to fetch job: {}", err);
                            panic!("Failed to fetch job: {}", err);
                        }
                    }
                }

                if let Some(limit) = CONFIG.queue.empty_job_cycles_before_quiting {
                    // Count cycles that couldn't find any job
                    if processed_jobs.load(std::sync::atomic::Ordering::Relaxed) == 0 {
                        cycles_without_jobs.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                    } else {
                        cycles_without_jobs.fetch_min(0, std::sync::atomic::Ordering::Relaxed);
                    }

                    // Cancel stream processing after empty cycles
                    if cycles_without_jobs.load(std::sync::atomic::Ordering::Relaxed) >= limit {
                        cancel_token.cancel();
                    }
                }
            }
        })
        .buffer_unordered(CONFIG.queue.stream.cluster_buffer_size)
        .take_while(|_| {
            let token = cancel_token.clone();
            async move { !token.is_cancelled() }
        })
        .collect::<Vec<()>>()
        .await;

    Ok(())
}
