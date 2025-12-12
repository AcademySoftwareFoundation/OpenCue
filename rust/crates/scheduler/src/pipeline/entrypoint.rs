use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

use futures::{stream, StreamExt};
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;
use tracing::{debug, error, info};

use crate::cluster::{Cluster, ClusterFeed, FeedMessage};
use crate::config::CONFIG;
use crate::dao::JobDao;
use crate::metrics;
use crate::models::DispatchJob;
use crate::pipeline::MatchingService;

/// Runs the scheduler feed loop, processing jobs for each cluster.
///
/// Iterates through the cluster feed, fetching and processing jobs for each cluster.
/// Jobs are processed concurrently within configurable buffer sizes. The loop can
/// optionally terminate after a configured number of empty cycles.
///
/// # Arguments
///
/// * `cluster_feed` - Iterator over clusters to process
///
/// # Returns
///
/// * `Ok(())` - Scheduler completed successfully
/// * `Err(miette::Error)` - Fatal error occurred during processing
pub async fn run(cluster_feed: ClusterFeed) -> miette::Result<()> {
    let job_fetcher = Arc::new(JobDao::new().await?);
    let matcher = Arc::new(MatchingService::new().await?);
    let cycles_without_jobs = Arc::new(AtomicUsize::new(0));
    info!("Starting scheduler feed");

    let (tx, cluster_receiver) = mpsc::channel(16);
    let feed_sender = cluster_feed.stream(tx).await;

    ReceiverStream::new(cluster_receiver)
        .for_each_concurrent(CONFIG.queue.stream.cluster_buffer_size, |cluster| {
            let job_fetcher = job_fetcher.clone();
            let matcher = matcher.clone();
            let cycles_without_jobs = cycles_without_jobs.clone();
            let feed_sender = feed_sender.clone();

            async move {
                let jobs = match &cluster {
                    Cluster::ComposedKey(cluster_key) => {
                        job_fetcher
                            .query_pending_jobs_by_show_facility_tag(
                                cluster_key.show_id,
                                cluster_key.facility_id,
                                cluster_key.tag.to_string(),
                            )
                            .await
                    }
                    Cluster::TagsKey(facility_id, tags) => {
                        job_fetcher
                            .query_pending_jobs_by_tags(
                                tags.iter().map(|v| v.to_string()).collect(),
                                *facility_id,
                            )
                            .await
                    }
                };

                match jobs {
                    Ok(jobs) => {
                        // Track number of jobs queried
                        metrics::increment_jobs_queried(jobs.len());

                        let processed_jobs = AtomicUsize::new(0);
                        stream::iter(jobs)
                            .for_each_concurrent(
                                CONFIG.queue.stream.job_buffer_size,
                                |job_model| async {
                                    processed_jobs.fetch_add(1, Ordering::Relaxed);
                                    metrics::increment_jobs_processed();
                                    let job = DispatchJob::new(job_model, cluster.clone());
                                    debug!("Found job: {}", job);
                                    matcher.process(job).await;
                                },
                            )
                            .await;
                        // If no jobs got processed, sleep to prevent hammering the database with
                        // queries with no outcome
                        if processed_jobs.load(Ordering::Relaxed) == 0 {
                            let _ = feed_sender
                                .send(FeedMessage::Sleep(cluster, Duration::from_secs(3)))
                                .await;
                        }

                        // If empty_jobs_cycles_before_quiting is set, quit if nothing got processed
                        if let Some(limit) = CONFIG.queue.empty_job_cycles_before_quiting {
                            // Count cycles that couldn't find any job
                            if processed_jobs.load(Ordering::Relaxed) == 0 {
                                cycles_without_jobs.fetch_add(1, Ordering::Relaxed);
                            } else {
                                cycles_without_jobs.store(0, Ordering::Relaxed);
                            }

                            // Cancel stream processing after empty cycles
                            if cycles_without_jobs.load(Ordering::Relaxed) >= limit {
                                let _ = feed_sender.send(FeedMessage::Stop()).await;
                            }
                        }
                    }
                    Err(err) => {
                        let _ = feed_sender.send(FeedMessage::Stop()).await;
                        error!("Failed to fetch job: {}", err);
                    }
                }
            }
        })
        .await;

    Ok(())
}
