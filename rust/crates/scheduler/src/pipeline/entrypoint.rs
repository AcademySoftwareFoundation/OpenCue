use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

use futures::{StreamExt, stream};
use tokio_util::sync::CancellationToken;
use tracing::info;

use crate::cluster::{Cluster, ClusterFeed};
use crate::config::CONFIG;
use crate::dao::JobDao;
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
    let cancel_token = CancellationToken::new();
    let cycles_without_jobs = Arc::new(AtomicUsize::new(0));
    info!("Starting scheduler feed");

    stream::iter(cluster_feed)
        .map(|cluster| {
            let job_fetcher = job_fetcher.clone();
            let job_event_handler = matcher.clone();
            let cancel_token = cancel_token.clone();
            let cycles_without_jobs = cycles_without_jobs.clone();

            async move {
                let jobs = match &cluster {
                    Cluster::ComposedKey(cluster_key) => {
                        job_fetcher
                            .query_pending_jobs_by_show_facility_tag(
                                cluster_key.show_id.clone(),
                                cluster_key.facility_id.clone(),
                                cluster_key.tag.to_string(),
                            )
                            .await
                    }
                    Cluster::TagsKey(tags) => {
                        job_fetcher
                            .query_pending_jobs_by_tags(
                                tags.iter().map(|v| v.to_string()).collect(),
                            )
                            .await
                    }
                };

                match jobs {
                    Ok(jobs) => {
                        let processed_jobs = AtomicUsize::new(0);
                        stream::iter(jobs)
                            .for_each_concurrent(
                                CONFIG.queue.stream.job_buffer_size,
                                |job_model| async {
                                    processed_jobs.fetch_add(1, Ordering::Relaxed);
                                    let job = DispatchJob::new(job_model, cluster.clone());
                                    info!("Found job: {}", job);
                                    job_event_handler.process(job).await;
                                },
                            )
                            .await;

                        if let Some(limit) = CONFIG.queue.empty_job_cycles_before_quiting {
                            // Count cycles that couldn't find any job
                            if processed_jobs.load(Ordering::Relaxed) == 0 {
                                cycles_without_jobs.fetch_add(1, Ordering::Relaxed);
                            } else {
                                cycles_without_jobs.fetch_min(0, Ordering::Relaxed);
                            }

                            // Cancel stream processing after empty cycles
                            if cycles_without_jobs.load(Ordering::Relaxed) >= limit {
                                cancel_token.cancel();
                            }
                        }
                    }
                    Err(err) => {
                        cancel_token.cancel();
                        panic!("Failed to fetch job: {}", err);
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
