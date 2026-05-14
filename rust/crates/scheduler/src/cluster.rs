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

use std::{
    cmp::Ordering as CmpOrdering,
    collections::{BTreeSet, BinaryHeap, HashMap, HashSet},
    sync::{
        atomic::{AtomicBool, AtomicUsize, Ordering},
        Arc, Mutex,
    },
    time::{Duration, Instant},
};

use futures::StreamExt;
use itertools::Itertools;
use miette::{IntoDiagnostic, Result};
use serde::{Deserialize, Serialize};
use tokio::sync::{mpsc, Notify};
use tracing::{debug, error, warn};
use uuid::Uuid;

use crate::{
    cluster_key::{Tag, TagType},
    config::CONFIG,
    dao::{helpers::parse_uuid, ClusterDao},
    metrics,
};

/// Counts how many times a cluster has been emitted by the feed.
///
/// Kept as a process-global atomic for source-level compatibility with smoke tests that
/// read it directly. Production observability is provided via the Prometheus
/// `scheduler_cluster_polls_total` counter (see [`metrics`]).
pub static CLUSTER_ROUNDS: AtomicUsize = AtomicUsize::new(0);

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq, PartialOrd, Ord)]
pub struct Cluster {
    pub facility_id: Uuid,
    pub show_id: Uuid,
    pub tags: BTreeSet<Tag>,
}

impl std::fmt::Display for Cluster {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}:{}:{}",
            self.facility_id,
            self.show_id,
            self.tags.iter().join(",")
        )
    }
}

impl Cluster {
    pub fn single_tag(facility_id: Uuid, show_id: Uuid, tag: Tag) -> Self {
        Cluster {
            facility_id,
            show_id,
            tags: BTreeSet::from([tag]),
        }
    }

    pub fn multiple_tag(facility_id: Uuid, show_id: Uuid, tags: Vec<Tag>) -> Self {
        Cluster {
            facility_id,
            show_id,
            tags: tags.into_iter().collect(),
        }
    }
}

/// A cluster scheduled for dispatch, ordered by eligibility time and recent productivity.
///
/// `BinaryHeap` is a max-heap, so [`Scheduled::cmp`] inverts `next_eligible_at`
/// (earliest wins) and keeps `last_dispatched_jobs` in natural order (busier wins
/// as a tiebreaker when productivity bias is enabled).
#[derive(Debug, Clone)]
struct Scheduled {
    cluster: Cluster,
    /// When this cluster becomes eligible for dispatch. A past `Instant` means
    /// the cluster is ready right now.
    next_eligible_at: Instant,
    /// Number of jobs processed in the most recent dispatch: used as the
    /// productivity bias tiebreaker.
    last_dispatched_jobs: usize,
}

impl PartialEq for Scheduled {
    fn eq(&self, other: &Self) -> bool {
        self.next_eligible_at == other.next_eligible_at
            && self.last_dispatched_jobs == other.last_dispatched_jobs
            && self.cluster == other.cluster
    }
}
impl Eq for Scheduled {}

impl Ord for Scheduled {
    fn cmp(&self, other: &Self) -> CmpOrdering {
        // Earliest `next_eligible_at` is highest priority. Invert for max-heap.
        let by_time = other.next_eligible_at.cmp(&self.next_eligible_at);
        if by_time != CmpOrdering::Equal {
            return by_time;
        }
        // Productivity bias: more jobs in the last dispatch ranks higher.
        if CONFIG.queue.cluster_productivity_bias {
            let by_jobs = self.last_dispatched_jobs.cmp(&other.last_dispatched_jobs);
            if by_jobs != CmpOrdering::Equal {
                return by_jobs;
            }
        }
        // Deterministic tiebreaker on the cluster identity.
        self.cluster.cmp(&other.cluster)
    }
}
impl PartialOrd for Scheduled {
    fn partial_cmp(&self, other: &Self) -> Option<CmpOrdering> {
        Some(self.cmp(other))
    }
}

#[derive(Debug)]
pub struct ClusterFeed {
    /// Priority queue of clusters awaiting dispatch.
    queue: Arc<Mutex<BinaryHeap<Scheduled>>>,
    stop_flag: Arc<AtomicBool>,
    /// Wakes the dispatch loop when an entry is pushed back or shutdown is signaled.
    notify: Arc<Notify>,
}

/// Control messages for the cluster feed stream.
///
/// Sent to the channel returned by [`ClusterFeed::stream`] to report back the
/// outcome of processing a cluster (so the priority queue can re-rank it) or
/// to signal a graceful shutdown.
pub enum FeedMessage {
    /// Stops the cluster feed stream gracefully.
    Stop,
    /// Reports the result of processing a cluster and re-inserts it into the
    /// priority queue.
    ///
    /// # Fields
    ///
    /// * `cluster` - The cluster that was just processed.
    /// * `processed_jobs` - Jobs dispatched on this cycle. Drives the productivity-bias tiebreaker.
    /// * `sleep` - Optional back-off duration. `None` re-queues the cluster as eligible now;
    ///   `Some(d)` defers it for at least `d`.
    Done {
        cluster: Cluster,
        processed_jobs: usize,
        sleep: Option<Duration>,
    },
}

/// Builder for constructing a [`ClusterFeed`].
///
/// Start with [`ClusterFeed::facility`] or [`ClusterFeed::no_facility`], chain optional
/// configuration methods, then call [`build`](ClusterFeedBuilder::build) to produce the feed.
///
/// # Example
///
/// ```ignore
/// let feed = ClusterFeed::facility(facility_id)
///     .with_ignore_tags(ignore_tags)
///     .with_clusters(clusters)
///     .with_entire_shows(shows)
///     .build()
///     .await?;
/// ```
pub struct ClusterFeedBuilder {
    facility_id: Option<Uuid>,
    ignore_tags: Vec<String>,
    clusters: Vec<Cluster>,
    entire_shows: Vec<String>,
}

impl ClusterFeedBuilder {
    /// Adds tags to ignore when loading clusters.
    pub fn with_ignore_tags(mut self, tags: Vec<String>) -> Self {
        self.ignore_tags = tags;
        self
    }

    /// Provides an explicit list of clusters instead of loading from the database.
    pub fn with_clusters(mut self, clusters: Vec<Cluster>) -> Self {
        self.clusters = clusters;
        self
    }

    /// Specifies show names whose frames should be scheduled in their entirety.
    pub fn with_entire_shows(mut self, shows: Vec<String>) -> Self {
        self.entire_shows = shows;
        self
    }

    /// Builds the [`ClusterFeed`].
    ///
    /// If explicit clusters were provided via [`with_clusters`](Self::with_clusters), they are
    /// used directly (filtered by ignore tags). Otherwise all clusters are loaded from the
    /// database, filtered to the configured facility and ignore tags.
    pub async fn build(self) -> Result<ClusterFeed> {
        let clusters = if self.clusters.is_empty() && self.entire_shows.is_empty() {
            let all = ClusterFeed::load_clusters(self.facility_id, &self.ignore_tags, None).await?;
            ClusterFeed::filter_clusters(all, &self.ignore_tags)
        } else {
            let mut clusters: HashSet<Cluster> = self.clusters.into_iter().collect();
            if !self.entire_shows.is_empty() {
                let show_clusters = ClusterFeed::load_clusters(
                    self.facility_id,
                    &self.ignore_tags,
                    Some(self.entire_shows),
                )
                .await?;
                clusters.extend(show_clusters);
            }
            ClusterFeed::filter_clusters(clusters.into_iter().collect(), &self.ignore_tags)
        };
        let now = Instant::now();
        let mut heap = BinaryHeap::with_capacity(clusters.len().max(1));
        for cluster in clusters {
            heap.push(Scheduled {
                cluster,
                next_eligible_at: now,
                last_dispatched_jobs: 0,
            });
        }
        Ok(ClusterFeed {
            queue: Arc::new(Mutex::new(heap)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            notify: Arc::new(Notify::new()),
        })
    }
}

impl ClusterFeed {
    /// Returns a builder for a feed scoped to the given facility.
    pub fn facility(facility_id: Uuid) -> ClusterFeedBuilder {
        ClusterFeedBuilder {
            facility_id: Some(facility_id),
            ignore_tags: Vec::new(),
            clusters: Vec::new(),
            entire_shows: Vec::new(),
        }
    }

    /// Returns a builder for a feed not scoped to any specific facility.
    pub fn no_facility() -> ClusterFeedBuilder {
        ClusterFeedBuilder {
            facility_id: None,
            ignore_tags: Vec::new(),
            clusters: Vec::new(),
            entire_shows: Vec::new(),
        }
    }

    /// Builds a feed from a fixed list of clusters with optional tag filtering.
    ///
    /// Intended for tests and direct construction where the cluster set is already
    /// known. Production code should prefer the builder ([`facility`](Self::facility) /
    /// [`no_facility`](Self::no_facility)) which can also load clusters from the database.
    ///
    /// # Arguments
    ///
    /// * `clusters` - Explicit list of clusters to feed.
    /// * `ignore_tags` - Tag names to drop; a cluster whose tag set becomes empty is excluded.
    pub fn load_from_clusters(clusters: Vec<Cluster>, ignore_tags: &[String]) -> Self {
        let filtered = Self::filter_clusters(clusters, ignore_tags);
        let now = Instant::now();
        let mut heap = BinaryHeap::with_capacity(filtered.len().max(1));
        for cluster in filtered {
            heap.push(Scheduled {
                cluster,
                next_eligible_at: now,
                last_dispatched_jobs: 0,
            });
        }
        ClusterFeed {
            queue: Arc::new(Mutex::new(heap)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            notify: Arc::new(Notify::new()),
        }
    }

    /// Loads all clusters from the database and organizes them by tag type.
    ///
    /// Loads allocation clusters (one per facility+show+tag), and chunks manual/hostname tags
    /// into groups based on configured chunk sizes. In a distributed system, this should be
    /// scheduled and coordinated across nodes.
    ///
    /// # Arguments
    ///
    /// * `facility_id` - Optional facility ID to filter clusters
    /// * `ignore_tags` - List of tag names to ignore when loading clusters
    ///
    /// # Returns
    ///
    /// * `Ok(ClusterFeed)` - Successfully loaded cluster feed
    /// * `Err(miette::Error)` - Failed to load clusters from database
    pub async fn load_clusters(
        facility_id: Option<Uuid>,
        ignore_tags: &[String],
        shows_filter: Option<Vec<String>>,
    ) -> Result<Vec<Cluster>> {
        let cluster_dao = ClusterDao::new().await?;

        // Fetch clusters for alloc and non_alloc tags
        let mut clusters_stream = cluster_dao
            .fetch_alloc_clusters(facility_id, shows_filter.clone())
            .chain(cluster_dao.fetch_non_alloc_clusters(facility_id, shows_filter));
        let mut clusters = Vec::new();
        let mut manual_tags: HashMap<(Uuid, Uuid), HashSet<Tag>> = HashMap::new();
        let mut hardware_tags: HashMap<(Uuid, Uuid), HashSet<Tag>> = HashMap::new();
        let mut hostname_tags: HashMap<(Uuid, Uuid), HashSet<Tag>> = HashMap::new();

        // Collect all tags
        while let Some(record) = clusters_stream.next().await {
            match record {
                Ok(cluster) => {
                    // Skip tags that are in the ignore list
                    if ignore_tags.contains(&cluster.tag) {
                        continue;
                    }

                    let facility_id = parse_uuid(&cluster.facility_id);
                    let show_id = parse_uuid(&cluster.show_id);
                    match cluster.ttype.as_str() {
                        // Each alloc tag becomes its own cluster
                        "ALLOC" => {
                            clusters.push(Cluster::single_tag(
                                facility_id,
                                show_id,
                                Tag {
                                    name: cluster.tag,
                                    ttype: TagType::Alloc,
                                },
                            ));
                        }
                        // Manual and hostname tags are collected to be chunked
                        "MANUAL" => {
                            manual_tags
                                .entry((show_id, facility_id))
                                .or_default()
                                .insert(Tag {
                                    name: cluster.tag,
                                    ttype: TagType::Manual,
                                });
                        }
                        "HOSTNAME" => {
                            hostname_tags
                                .entry((show_id, facility_id))
                                .or_default()
                                .insert(Tag {
                                    name: cluster.tag,
                                    ttype: TagType::HostName,
                                });
                        }
                        "HARDWARE" => {
                            hardware_tags
                                .entry((show_id, facility_id))
                                .or_default()
                                .insert(Tag {
                                    name: cluster.tag,
                                    ttype: TagType::Hardware,
                                });
                        }
                        _ => (),
                    };
                }
                Err(err) => error!("Failed to fetch clusters. {err}"),
            }
        }

        // Chunk Manual tags
        for ((show_id, facility_id), tags) in manual_tags.into_iter() {
            for chunk in &tags.into_iter().chunks(CONFIG.queue.manual_tags_chunk_size) {
                clusters.push(Cluster::multiple_tag(facility_id, show_id, chunk.collect()))
            }
        }

        // Chunk Hostname tags
        for ((show_id, facility_id), tags) in hostname_tags.into_iter() {
            for chunk in &tags
                .into_iter()
                .chunks(CONFIG.queue.hostname_tags_chunk_size)
            {
                clusters.push(Cluster::multiple_tag(facility_id, show_id, chunk.collect()))
            }
        }

        // Chunk Hardware tags
        for ((show_id, facility_id), tags) in hardware_tags.into_iter() {
            for chunk in &tags
                .into_iter()
                // Hardware share the same size as manual to simplify configuration
                .chunks(CONFIG.queue.manual_tags_chunk_size)
            {
                clusters.push(Cluster::multiple_tag(facility_id, show_id, chunk.collect()))
            }
        }

        Ok(clusters)
    }

    /// Creates a ClusterFeed from a predefined list of clusters for testing.
    ///
    /// # Arguments
    ///
    /// * `clusters` - List of clusters to iterate over
    /// * `ignore_tags` - List of tag names to ignore when loading clusters
    ///
    /// # Returns
    ///
    /// * `ClusterFeed` - Feed configured to run once through the provided clusters
    pub fn filter_clusters(clusters: Vec<Cluster>, ignore_tags: &[String]) -> Vec<Cluster> {
        if ignore_tags.is_empty() {
            return clusters;
        }
        clusters
            .into_iter()
            .filter_map(|mut cluster| {
                cluster.tags.retain(|tag| !ignore_tags.contains(&tag.name));
                if cluster.tags.is_empty() {
                    None
                } else {
                    Some(cluster)
                }
            })
            .collect()
    }

    /// Streams clusters from a priority queue to a channel receiver.
    ///
    /// Creates a producer-consumer pattern backed by a `BinaryHeap<Scheduled>`
    /// keyed on `(next_eligible_at asc, last_dispatched_jobs desc)`. The consumer
    /// must report each cluster back via [`FeedMessage::Done`] so it can be
    /// re-inserted with updated stats; otherwise the cluster is lost.
    ///
    /// # Arguments
    ///
    /// * `sender` - Channel sender for emitting eligible clusters.
    ///
    /// # Returns
    ///
    /// * `mpsc::Sender<FeedMessage>` - Channel to send `Done` (re-insert) and `Stop` messages.
    ///
    /// # Behavior
    ///
    /// - Pops the highest-priority cluster (earliest eligible, busiest as tiebreaker).
    /// - If the popped entry is not yet eligible, sleeps until it is, but wakes
    ///   immediately on `Notify` so a freshly inserted higher-priority entry can preempt.
    /// - On `FeedMessage::Done` re-inserts the cluster with the reported sleep
    ///   deadline and `last_dispatched_jobs` for the productivity bias.
    /// - On `FeedMessage::Stop` sets the stop flag and exits.
    pub async fn stream(self, sender: mpsc::Sender<Cluster>) -> mpsc::Sender<FeedMessage> {
        // Backpressure: bounded channel keeps the consumer from queueing unbounded Done messages.
        let (control_sender, mut control_receiver) = mpsc::channel(32);

        let stop_flag = self.stop_flag.clone();
        let queue = self.queue.clone();
        let notify = self.notify.clone();

        // Dispatch loop: pop highest-priority cluster, sleep until eligible, send.
        let queue_dispatch = queue.clone();
        let notify_dispatch = notify.clone();
        let stop_flag_dispatch = stop_flag.clone();
        tokio::spawn(async move {
            loop {
                if stop_flag_dispatch.load(Ordering::Relaxed) {
                    warn!("Cluster feed received stop signal. Exiting dispatch loop.");
                    break;
                }

                let scheduled = {
                    let mut heap =
                        queue_dispatch.lock().unwrap_or_else(|p| p.into_inner());
                    heap.pop()
                };

                let scheduled = match scheduled {
                    Some(s) => s,
                    None => {
                        // No clusters available: all in flight. Wait for a re-insert
                        // or a stop signal. The short fallback sleep guarantees we
                        // re-check `stop_flag` if no notify ever arrives.
                        tokio::select! {
                            _ = notify_dispatch.notified() => {}
                            _ = tokio::time::sleep(Duration::from_millis(100)) => {}
                        }
                        continue;
                    }
                };

                let now = Instant::now();
                if scheduled.next_eligible_at > now {
                    let sleep_dur = scheduled.next_eligible_at - now;
                    let preempted = tokio::select! {
                        _ = tokio::time::sleep(sleep_dur) => false,
                        _ = notify_dispatch.notified() => true,
                    };
                    if preempted {
                        // A new entry was pushed: re-pop to pick the new best.
                        let mut heap =
                            queue_dispatch.lock().unwrap_or_else(|p| p.into_inner());
                        heap.push(scheduled);
                        continue;
                    }
                    if stop_flag_dispatch.load(Ordering::Relaxed) {
                        break;
                    }
                }

                CLUSTER_ROUNDS.fetch_add(1, Ordering::Relaxed);
                metrics::increment_cluster_polls(
                    &scheduled.cluster.show_id,
                    &scheduled.cluster.facility_id,
                );

                if sender.send(scheduled.cluster).await.is_err() {
                    warn!("Cluster receiver dropped. Stopping feed.");
                    break;
                }
            }
        });

        // Control loop: handle Done (re-insert) and Stop messages from the consumer.
        let queue_ctrl = queue.clone();
        let notify_ctrl = notify.clone();
        let stop_flag_ctrl = stop_flag.clone();
        tokio::spawn(async move {
            while let Some(message) = control_receiver.recv().await {
                match message {
                    FeedMessage::Done {
                        cluster,
                        processed_jobs,
                        sleep,
                    } => {
                        let next_eligible_at = match sleep {
                            Some(d) => {
                                debug!(
                                    "{:?} re-queued with back-off of {}s ({} jobs processed)",
                                    cluster,
                                    d.as_secs(),
                                    processed_jobs
                                );
                                Instant::now()
                                    .checked_add(d)
                                    .unwrap_or_else(Instant::now)
                            }
                            None => Instant::now(),
                        };
                        metrics::set_cluster_last_dispatched_jobs(
                            &cluster.show_id,
                            &cluster.facility_id,
                            processed_jobs,
                        );
                        {
                            let mut heap =
                                queue_ctrl.lock().unwrap_or_else(|p| p.into_inner());
                            heap.push(Scheduled {
                                cluster,
                                next_eligible_at,
                                last_dispatched_jobs: processed_jobs,
                            });
                        }
                        notify_ctrl.notify_one();
                    }
                    FeedMessage::Stop => {
                        stop_flag_ctrl.store(true, Ordering::Relaxed);
                        notify_ctrl.notify_one();
                        break;
                    }
                }
            }
        });

        control_sender
    }
}

/// Looks up a facility ID by facility name.
///
/// # Arguments
///
/// * `facility_name` - The name of the facility
///
/// # Returns
///
/// * `Ok(Uuid)` - The facility ID
/// * `Err(miette::Error)` - If facility not found or database error
pub async fn get_facility_id(facility_name: &str) -> Result<Uuid> {
    let cluster_dao = ClusterDao::new().await?;
    cluster_dao
        .get_facility_id(facility_name)
        .await
        .into_diagnostic()
}

/// Looks up a show ID by show name.
///
/// # Arguments
///
/// * `show_name` - The name of the show
///
/// # Returns
///
/// * `Ok(Uuid)` - The show ID
/// * `Err(miette::Error)` - If show not found or database error
pub async fn get_show_id(show_name: &str) -> Result<Uuid> {
    let cluster_dao = ClusterDao::new().await?;
    cluster_dao.get_show_id(show_name).await.into_diagnostic()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    fn make_cluster(name: &str) -> Cluster {
        Cluster {
            facility_id: Uuid::new_v4(),
            show_id: Uuid::new_v4(),
            tags: BTreeSet::from([Tag {
                name: name.to_string(),
                ttype: TagType::Alloc,
            }]),
        }
    }

    fn scheduled(cluster: Cluster, at: Instant, jobs: usize) -> Scheduled {
        Scheduled {
            cluster,
            next_eligible_at: at,
            last_dispatched_jobs: jobs,
        }
    }

    #[test]
    fn earlier_next_eligible_at_pops_first() {
        let now = Instant::now();
        let later = scheduled(make_cluster("a"), now + Duration::from_secs(10), 100);
        let sooner = scheduled(make_cluster("b"), now, 0);

        let mut heap = BinaryHeap::new();
        heap.push(later);
        heap.push(sooner);

        let popped = heap.pop().expect("heap not empty");
        assert_eq!(popped.last_dispatched_jobs, 0);
    }

    #[test]
    fn busier_cluster_pops_first_when_eligibility_ties() {
        // This test relies on the default `cluster_productivity_bias = true`.
        assert!(
            CONFIG.queue.cluster_productivity_bias,
            "test assumes default config: productivity bias enabled"
        );

        let now = Instant::now();
        let idle = scheduled(make_cluster("idle"), now, 0);
        let busy = scheduled(make_cluster("busy"), now, 500);

        let mut heap = BinaryHeap::new();
        heap.push(idle);
        heap.push(busy);

        let popped = heap.pop().expect("heap not empty");
        assert_eq!(popped.last_dispatched_jobs, 500);
    }

    #[test]
    fn sleeping_cluster_does_not_block_eligible_neighbor() {
        let now = Instant::now();
        let sleeping = scheduled(
            make_cluster("sleeping"),
            now + Duration::from_secs(60),
            10,
        );
        let ready = scheduled(make_cluster("ready"), now, 0);

        let mut heap = BinaryHeap::new();
        heap.push(sleeping);
        heap.push(ready);

        let first = heap.pop().expect("heap not empty");
        let first_tag = first.cluster.tags.iter().next().unwrap().name.clone();
        assert_eq!(first_tag, "ready");
    }

    #[tokio::test]
    async fn stream_round_trip_re_inserts_via_done() {
        let cluster = make_cluster("solo");
        let mut heap = BinaryHeap::new();
        heap.push(Scheduled {
            cluster: cluster.clone(),
            next_eligible_at: Instant::now(),
            last_dispatched_jobs: 0,
        });

        let feed = ClusterFeed {
            queue: Arc::new(Mutex::new(heap)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            notify: Arc::new(Notify::new()),
        };

        let (tx, mut rx) = mpsc::channel::<Cluster>(8);
        let control = feed.stream(tx).await;

        // Receive the cluster, report it back as productive, receive it again.
        let emitted = rx.recv().await.expect("feed emitted a cluster");
        assert_eq!(emitted, cluster);

        control
            .send(FeedMessage::Done {
                cluster: emitted.clone(),
                processed_jobs: 7,
                sleep: None,
            })
            .await
            .expect("control channel open");

        let emitted_again = tokio::time::timeout(Duration::from_secs(1), rx.recv())
            .await
            .expect("cluster re-emitted within 1s")
            .expect("cluster present");
        assert_eq!(emitted_again, cluster);

        // Tidy up so the spawned tasks exit.
        control.send(FeedMessage::Stop).await.ok();
    }

    #[tokio::test]
    async fn busy_cluster_gets_more_polls_than_idle() {
        // Two clusters share the feed. The "busy" cluster reports productive
        // work with no back-off; the "idle" cluster reports zero jobs with a
        // 100ms back-off. Over a 500ms window busy should be polled many more
        // times than idle.
        let busy = make_cluster("busy");
        let idle = make_cluster("idle");
        let now = Instant::now();
        let mut heap = BinaryHeap::new();
        heap.push(Scheduled {
            cluster: busy.clone(),
            next_eligible_at: now,
            last_dispatched_jobs: 0,
        });
        heap.push(Scheduled {
            cluster: idle.clone(),
            next_eligible_at: now,
            last_dispatched_jobs: 0,
        });

        let feed = ClusterFeed {
            queue: Arc::new(Mutex::new(heap)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            notify: Arc::new(Notify::new()),
        };

        let (tx, mut rx) = mpsc::channel::<Cluster>(16);
        let control = feed.stream(tx).await;

        let mut busy_polls = 0usize;
        let mut idle_polls = 0usize;
        let test_duration = Duration::from_millis(500);
        let idle_back_off = Duration::from_millis(100);
        let deadline = Instant::now() + test_duration;

        while Instant::now() < deadline {
            let remaining = deadline.saturating_duration_since(Instant::now());
            let next = tokio::time::timeout(remaining, rx.recv()).await;
            let Ok(Some(cluster)) = next else { break };

            let is_busy = cluster.tags.iter().next().unwrap().name == "busy";
            let (processed_jobs, sleep) = if is_busy {
                busy_polls += 1;
                (100, None)
            } else {
                idle_polls += 1;
                (0, Some(idle_back_off))
            };
            control
                .send(FeedMessage::Done {
                    cluster,
                    processed_jobs,
                    sleep,
                })
                .await
                .ok();
        }

        control.send(FeedMessage::Stop).await.ok();

        // Idle is back-off-bound: in 500ms with a 100ms back-off it can be
        // polled at most ~5 times. Busy has no back-off and is only limited
        // by task scheduling, so it should run away.
        assert!(
            busy_polls > idle_polls * 2,
            "expected busy polls (>2x) idle polls; busy={busy_polls} idle={idle_polls}"
        );
        assert!(busy_polls > 0 && idle_polls > 0, "both clusters polled at least once");
    }

    #[tokio::test]
    async fn stream_respects_sleep_back_off() {
        let cluster = make_cluster("naps");
        let mut heap = BinaryHeap::new();
        heap.push(Scheduled {
            cluster: cluster.clone(),
            next_eligible_at: Instant::now(),
            last_dispatched_jobs: 0,
        });

        let feed = ClusterFeed {
            queue: Arc::new(Mutex::new(heap)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            notify: Arc::new(Notify::new()),
        };

        let (tx, mut rx) = mpsc::channel::<Cluster>(8);
        let control = feed.stream(tx).await;

        // First emission is immediate.
        rx.recv().await.expect("first emission");

        // Re-queue with a 250ms back-off.
        let back_off = Duration::from_millis(250);
        let started = Instant::now();
        control
            .send(FeedMessage::Done {
                cluster: cluster.clone(),
                processed_jobs: 0,
                sleep: Some(back_off),
            })
            .await
            .expect("control channel open");

        // Should not arrive before the back-off, should arrive shortly after.
        let _ = tokio::time::timeout(Duration::from_secs(2), rx.recv())
            .await
            .expect("cluster re-emitted within 2s")
            .expect("cluster present");
        let elapsed = started.elapsed();
        assert!(
            elapsed >= back_off,
            "cluster re-emitted in {elapsed:?}, expected >= {back_off:?}"
        );

        control.send(FeedMessage::Stop).await.ok();
    }
}
