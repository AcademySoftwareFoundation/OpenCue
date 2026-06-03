// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use futures::{stream, StreamExt};
use tokio::sync::mpsc;
use tokio_stream::wrappers::ReceiverStream;
use tracing::{debug, error, info};

use crate::cluster::{ClusterFeed, FeedMessage};
use crate::config::CONFIG;
use crate::dao::JobDao;
use crate::metrics;
use crate::models::DispatchJob;
use crate::pipeline::MatchingService;
use crate::resource_accounting::resource_accounting_service;

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
    // Initialize the resource accounting service (starts its periodic recomputation loop).
    resource_accounting_service().await?;

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
                let jobs = job_fetcher
                    .query_pending_jobs_by_show_facility_and_tags(
                        cluster.show_id,
                        cluster.facility_id,
                        cluster.tags.iter().map(|tag| tag.name.clone()),
                    )
                    .await;

                let (processed_count, should_stop) = match jobs {
                    Ok(jobs) => {
                        metrics::increment_jobs_queried(jobs.len());

                        let processed_jobs = AtomicUsize::new(0);
                        stream::iter(jobs)
                            .for_each_concurrent(
                                CONFIG.queue.stream.job_buffer_size,
                                |job_model| async {
                                    processed_jobs.fetch_add(1, Ordering::Relaxed);
                                    metrics::increment_jobs_processed(&job_model.show_name);
                                    let job = DispatchJob::new(job_model, cluster.clone());
                                    debug!("Found job: {}", job);
                                    matcher.process(job).await;
                                },
                            )
                            .await;

                        let processed = processed_jobs.load(Ordering::Relaxed);

                        let stop = match CONFIG.queue.empty_job_cycles_before_quiting {
                            Some(limit) => {
                                // Combine the update and read into a single atomic
                                // operation so concurrent clusters can't race between
                                // a fetch_add/store and a separate load. SeqCst gives
                                // us a strict total order across all clusters.
                                let new_count = if processed == 0 {
                                    cycles_without_jobs.fetch_add(1, Ordering::SeqCst) + 1
                                } else {
                                    cycles_without_jobs.swap(0, Ordering::SeqCst);
                                    0
                                };
                                new_count >= limit
                            }
                            None => false,
                        };

                        (processed, stop)
                    }
                    Err(err) => {
                        // Don't halt the entire scheduler for a single cluster's
                        // fetch error (network blip, transient DB load). Treat
                        // the cluster as empty for this cycle so it gets the
                        // configured back-off and other clusters keep running.
                        // The `empty_job_cycles_before_quiting` safety net still
                        // applies if the error persists across all clusters.
                        error!(
                            "Failed to fetch jobs for cluster {}: {}",
                            cluster, err
                        );
                        (0, false)
                    }
                };

                // Re-insert the cluster into the priority queue. An empty cycle gets a
                // back-off so neighbors aren't starved while this cluster waits for work.
                let sleep = if processed_count == 0 {
                    Some(CONFIG.queue.cluster_empty_back_off)
                } else {
                    None
                };
                let _ = feed_sender
                    .send(FeedMessage::Done {
                        cluster,
                        processed_jobs: processed_count,
                        sleep,
                    })
                    .await;

                if should_stop {
                    let _ = feed_sender.send(FeedMessage::Stop).await;
                }
            }
        })
        .await;

    Ok(())
}
