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

use crate::accounting::{accounting_service, bootstrap, limit_reseed, recompute};
use crate::cluster::{ClusterFeed, FeedMessage};
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
    // Initialize the Redis-backed accounting service. Bootstrap reseed (limits + booked
    // counters) must complete before the scheduler accepts work - see design §4.3.
    let accounting = accounting_service().await?;
    bootstrap::run_blocking_reseed(&accounting).await?;
    // TODO: gate behind leader-election when multi-scheduler lands (design §5).
    recompute::spawn_loop(accounting.clone());
    // TODO: gate behind leader-election when multi-scheduler lands (design §5).
    limit_reseed::spawn_loop(accounting.clone());

    let job_fetcher = Arc::new(JobDao::new().await?);
    let matcher = Arc::new(MatchingService::new().await?);
    let cycles_without_jobs = Arc::new(AtomicUsize::new(0));
    info!("Starting scheduler feed");

    let (tx, cluster_receiver) = mpsc::channel(16);
    // Periodically reload the cluster set from the DB so b_scheduler_managed
    // flips (and host-tag/subscription churn) are picked up without a restart.
    // No-op for feeds built from an explicit cluster list (tests).
    cluster_feed.start_reload_loop();
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
                        &cluster.facility_id,
                        cluster.tags.iter().map(|tag| tag.name.clone()),
                    )
                    .await;

                match jobs {
                    Ok(jobs) => {
                        // Track number of jobs queried
                        metrics::increment_jobs_queried(jobs.len());

                        let processed_jobs = AtomicUsize::new(0);
                        let dispatched_frames = AtomicUsize::new(0);
                        stream::iter(jobs)
                            .for_each_concurrent(
                                CONFIG.queue.stream.job_buffer_size,
                                |job_model| async {
                                    processed_jobs.fetch_add(1, Ordering::Relaxed);
                                    metrics::increment_jobs_processed(&job_model.show_name);
                                    let job = DispatchJob::new(job_model, cluster.clone());
                                    debug!("Found job: {}", job);
                                    let dispatched = matcher.process(job, &feed_sender).await;
                                    dispatched_frames.fetch_add(dispatched, Ordering::Relaxed);
                                },
                            )
                            .await;
                        // If no jobs got processed, sleep to prevent hammering the database with
                        // queries with no outcome
                        if processed_jobs.load(Ordering::Relaxed) == 0 {
                            let _ = feed_sender
                                .send(FeedMessage::Sleep(
                                    cluster,
                                    CONFIG.queue.cluster_empty_sleep,
                                ))
                                .await;
                        } else if dispatched_frames.load(Ordering::Relaxed) == 0 {
                            // Jobs are pending but the whole pass placed nothing —
                            // typically a saturated farm (no host fits anywhere).
                            // Without a back-off this cluster would re-query its
                            // jobs and layers continuously while accomplishing
                            // nothing. A short sleep keeps booking latency low
                            // (host state refreshes on a similar cadence) while
                            // cutting the no-op query load drastically.
                            let _ = feed_sender
                                .send(FeedMessage::Sleep(
                                    cluster,
                                    CONFIG.queue.cluster_saturated_sleep,
                                ))
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
                        // A failed job query is usually transient (pool pressure,
                        // network blip, failover). Stopping the whole feed here
                        // would shut the scheduler down on the first hiccup; back
                        // this cluster off instead and let the next pass retry.
                        error!("Failed to fetch jobs for cluster {}: {}", cluster, err);
                        let _ = feed_sender
                            .send(FeedMessage::Sleep(
                                cluster,
                                CONFIG.queue.cluster_empty_sleep,
                            ))
                            .await;
                    }
                }
            }
        })
        .await;

    Ok(())
}
