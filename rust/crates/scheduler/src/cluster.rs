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
    collections::{BTreeMap, BTreeSet, HashMap, HashSet},
    ops::ControlFlow,
    panic::AssertUnwindSafe,
    sync::{
        atomic::{AtomicBool, AtomicUsize, Ordering},
        Arc, Mutex, RwLock,
    },
    time::{Duration, Instant, SystemTime},
};

use futures::{FutureExt, StreamExt};
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
    metrics::observe_cluster_round_trip,
};

pub static CLUSTER_ROUNDS: AtomicUsize = AtomicUsize::new(0);

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq, PartialOrd, Ord)]
pub struct Cluster {
    pub facility_id: String,
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
    pub fn single_tag(facility_id: String, show_id: Uuid, tag: Tag) -> Self {
        Cluster {
            facility_id,
            show_id,
            tags: BTreeSet::from([tag]),
        }
    }

    pub fn multiple_tag(facility_id: String, show_id: Uuid, tags: Vec<Tag>) -> Self {
        Cluster {
            facility_id,
            show_id,
            tags: tags.into_iter().collect(),
        }
    }
}

/// Inputs retained by a DB-backed [`ClusterFeed`] so it can periodically reload
/// its cluster set. Absent on feeds built from an explicit list (tests), which
/// never reload.
#[derive(Debug, Clone)]
struct ReloadCtx {
    facility_id: Option<String>,
    ignore_tags: Vec<String>,
}

/// Interval the producer idles for when the cluster set is currently empty
/// (e.g. every show was flipped to Cuebot-managed). The reload loop will
/// repopulate the set; this is just how often the producer re-checks.
const EMPTY_FEED_POLL_INTERVAL: Duration = Duration::from_secs(5);

#[derive(Debug)]
pub struct ClusterFeed {
    pub clusters: Arc<RwLock<Vec<Cluster>>>,
    current_index: Arc<AtomicUsize>,
    stop_flag: Arc<AtomicBool>,
    /// Pinged alongside `stop_flag` so the reload loop can break its
    /// `interval.tick()` immediately on shutdown instead of waiting up to
    /// `cluster_reload_interval`.
    stop_notify: Arc<Notify>,
    sleep_map: Arc<Mutex<HashMap<Cluster, SystemTime>>>,
    /// Tracks the last emission time per active cluster for the round-trip
    /// histogram. Owned by the feed so `apply_reload_inner` can prune entries
    /// for clusters that no longer exist; the producer/receiver tasks share
    /// clones of this `Arc`.
    last_sent_map: Arc<Mutex<HashMap<Cluster, Instant>>>,
    /// `Some` for DB-backed feeds (enables periodic reload), `None` for feeds
    /// built from an explicit cluster list.
    reload: Option<ReloadCtx>,
}

/// Control messages for the cluster feed stream.
///
/// These messages are sent to the control channel returned by `ClusterFeed::stream()`
/// to influence feed behavior during runtime.
pub enum FeedMessage {
    /// Stops the cluster feed stream gracefully.
    Stop(),
    /// Puts a specific cluster to sleep for the given duration.
    ///
    /// # Fields
    ///
    /// * `Cluster` - The cluster to put to sleep
    /// * `Duration` - How long to sleep before the cluster can be processed again
    Sleep(Cluster, Duration),
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
///     .build()
///     .await?;
/// ```
pub struct ClusterFeedBuilder {
    facility_id: Option<String>,
    ignore_tags: Vec<String>,
}

impl ClusterFeedBuilder {
    /// Adds tags to ignore when loading clusters.
    pub fn with_ignore_tags(mut self, tags: Vec<String>) -> Self {
        self.ignore_tags = tags;
        self
    }

    /// Builds the [`ClusterFeed`].
    ///
    /// Loads every cluster for shows where `b_scheduler_managed = true` from the
    /// database, filtered to the configured facility and ignore tags. The returned
    /// feed retains its facility/ignore-tags so [`ClusterFeed::start_reload_loop`]
    /// can refresh the set without a restart.
    pub async fn build(self) -> Result<ClusterFeed> {
        let loaded =
            ClusterFeed::load_clusters(self.facility_id.clone(), &self.ignore_tags).await?;
        let clusters = ClusterFeed::filter_clusters(loaded, &self.ignore_tags);
        Ok(ClusterFeed {
            clusters: Arc::new(RwLock::new(clusters)),
            current_index: Arc::new(AtomicUsize::new(0)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            stop_notify: Arc::new(Notify::new()),
            sleep_map: Arc::new(Mutex::new(HashMap::new())),
            last_sent_map: Arc::new(Mutex::new(HashMap::new())),
            reload: Some(ReloadCtx {
                facility_id: self.facility_id,
                ignore_tags: self.ignore_tags,
            }),
        })
    }
}

impl ClusterFeed {
    /// Returns a builder for a feed scoped to the given facility.
    pub fn facility(facility_id: String) -> ClusterFeedBuilder {
        ClusterFeedBuilder {
            facility_id: Some(facility_id),
            ignore_tags: Vec::new(),
        }
    }

    /// Returns a builder for a feed not scoped to any specific facility.
    pub fn no_facility() -> ClusterFeedBuilder {
        ClusterFeedBuilder {
            facility_id: None,
            ignore_tags: Vec::new(),
        }
    }

    /// Creates a feed from an explicit list of clusters, bypassing the database.
    ///
    /// Intended for tests: the resulting feed is static (`reload = None`) and
    /// will not refresh from the DB.
    // Only used by the lib's test consumers (integration + unit tests); the
    // `cue-scheduler` binary crate never calls it.
    #[allow(dead_code)]
    pub fn load_from_clusters(clusters: Vec<Cluster>, ignore_tags: &[String]) -> ClusterFeed {
        let clusters = ClusterFeed::filter_clusters(clusters, ignore_tags);
        ClusterFeed {
            clusters: Arc::new(RwLock::new(clusters)),
            current_index: Arc::new(AtomicUsize::new(0)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            stop_notify: Arc::new(Notify::new()),
            sleep_map: Arc::new(Mutex::new(HashMap::new())),
            last_sent_map: Arc::new(Mutex::new(HashMap::new())),
            reload: None,
        }
    }

    /// Loads all clusters for scheduler-managed shows and organizes them by tag type.
    ///
    /// Loads allocation clusters (one per facility+show+tag), and chunks manual/hostname tags
    /// into groups based on configured chunk sizes. Only shows where
    /// `b_scheduler_managed = true` are included (enforced in SQL). In a distributed
    /// system, this should be scheduled and coordinated across nodes.
    ///
    /// # Arguments
    ///
    /// * `facility_id` - Optional facility ID to filter clusters
    /// * `ignore_tags` - List of tag names to ignore when loading clusters
    ///
    /// # Returns
    ///
    /// * `Ok(Vec<Cluster>)` - Successfully loaded clusters
    /// * `Err(miette::Error)` - Failed to load clusters from database
    pub async fn load_clusters(
        facility_id: Option<String>,
        ignore_tags: &[String],
    ) -> Result<Vec<Cluster>> {
        let cluster_dao = ClusterDao::new().await?;

        // Fetch clusters for alloc and non_alloc tags
        let mut clusters_stream = cluster_dao
            .fetch_alloc_clusters(facility_id.clone())
            .chain(cluster_dao.fetch_non_alloc_clusters(facility_id));
        let mut clusters = Vec::new();
        // BTreeMap/BTreeSet are deliberate: their iteration order is
        // deterministic, so chunking produces a stable set of Cluster instances
        // for the same DB state. With HashMap/HashSet's randomized iteration,
        // the change-gate in apply_reload_inner would see "changed" on every
        // reload and pointlessly swap the set.
        let mut manual_tags: BTreeMap<(Uuid, String), BTreeSet<Tag>> = BTreeMap::new();
        let mut hardware_tags: BTreeMap<(Uuid, String), BTreeSet<Tag>> = BTreeMap::new();
        let mut hostname_tags: BTreeMap<(Uuid, String), BTreeSet<Tag>> = BTreeMap::new();

        // Collect all tags
        while let Some(record) = clusters_stream.next().await {
            match record {
                Ok(cluster) => {
                    // Skip tags that are in the ignore list
                    if ignore_tags.contains(&cluster.tag) {
                        continue;
                    }

                    let facility_id = cluster.facility_id;
                    let show_id = parse_uuid(&cluster.show_id);
                    match cluster.ttype.as_str() {
                        // Each alloc tag becomes its own cluster. Carry pk_alloc
                        // through Tag so the matcher can snapshot the
                        // (show, alloc) subscription burst from Redis before
                        // host checkout (see `MatchingService::process_layer`).
                        "ALLOC" => {
                            let alloc_id = cluster.alloc_id.as_deref().map(parse_uuid);
                            clusters.push(Cluster::single_tag(
                                facility_id,
                                show_id,
                                Tag {
                                    name: cluster.tag,
                                    ttype: TagType::Alloc,
                                    alloc_id,
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
                                    alloc_id: None,
                                });
                        }
                        "HOSTNAME" => {
                            hostname_tags
                                .entry((show_id, facility_id))
                                .or_default()
                                .insert(Tag {
                                    name: cluster.tag,
                                    ttype: TagType::HostName,
                                    alloc_id: None,
                                });
                        }
                        "HARDWARE" => {
                            hardware_tags
                                .entry((show_id, facility_id))
                                .or_default()
                                .insert(Tag {
                                    name: cluster.tag,
                                    ttype: TagType::Hardware,
                                    alloc_id: None,
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
                clusters.push(Cluster::multiple_tag(
                    facility_id.clone(),
                    show_id,
                    chunk.collect(),
                ))
            }
        }

        // Chunk Hostname tags
        for ((show_id, facility_id), tags) in hostname_tags.into_iter() {
            for chunk in &tags
                .into_iter()
                .chunks(CONFIG.queue.hostname_tags_chunk_size)
            {
                clusters.push(Cluster::multiple_tag(
                    facility_id.clone(),
                    show_id,
                    chunk.collect(),
                ))
            }
        }

        // Chunk Hardware tags
        for ((show_id, facility_id), tags) in hardware_tags.into_iter() {
            for chunk in &tags
                .into_iter()
                // Hardware share the same size as manual to simplify configuration
                .chunks(CONFIG.queue.manual_tags_chunk_size)
            {
                clusters.push(Cluster::multiple_tag(
                    facility_id.clone(),
                    show_id,
                    chunk.collect(),
                ))
            }
        }

        Ok(clusters)
    }

    /// Removes ignored tags from each cluster, dropping clusters left empty.
    ///
    /// # Arguments
    ///
    /// * `clusters` - Clusters to filter
    /// * `ignore_tags` - List of tag names to strip from every cluster
    ///
    /// # Returns
    ///
    /// * `Vec<Cluster>` - Clusters with ignored tags removed
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

    /// Replaces the live cluster set with `new_clusters` if it differs from the
    /// current set, returning whether a swap happened.
    ///
    /// The comparison is set-based (order-insensitive), since `load_clusters`
    /// produces clusters in nondeterministic Vec order. On an actual change the
    /// whole set is swapped and the round-robin index is reset. Sleep and
    /// last-sent entries for clusters that no longer exist are dropped;
    /// survivors keep their backoff state and round-trip baseline, which are
    /// unrelated to topology changes.
    // The reload loop calls `apply_reload_inner` directly; this wrapper exists
    // for unit tests, so the `cue-scheduler` binary crate never calls it.
    #[allow(dead_code)]
    pub fn apply_reload(&self, new_clusters: Vec<Cluster>) -> bool {
        Self::apply_reload_inner(
            &self.clusters,
            &self.current_index,
            &self.sleep_map,
            &self.last_sent_map,
            new_clusters,
        )
    }

    /// Shared swap logic, operating on the feed's `Arc`-held state so the reload
    /// loop (which can't hold `&self`) and [`apply_reload`](Self::apply_reload)
    /// can both use it.
    fn apply_reload_inner(
        clusters: &Arc<RwLock<Vec<Cluster>>>,
        current_index: &Arc<AtomicUsize>,
        sleep_map: &Arc<Mutex<HashMap<Cluster, SystemTime>>>,
        last_sent_map: &Arc<Mutex<HashMap<Cluster, Instant>>>,
        new_clusters: Vec<Cluster>,
    ) -> bool {
        // Change-gate: only the expensive swap/disruption happens on a real change.
        let changed = {
            let current = clusters.read().unwrap_or_else(|p| p.into_inner());
            let current_set: HashSet<&Cluster> = current.iter().collect();
            let new_set: HashSet<&Cluster> = new_clusters.iter().collect();
            current_set != new_set
        };
        if !changed {
            return false;
        }

        {
            // Drop sleep / last-sent entries for clusters that no longer exist;
            // preserve survivors' backoff state and round-trip baseline.
            let new_set: HashSet<&Cluster> = new_clusters.iter().collect();
            {
                let mut sleep = sleep_map.lock().unwrap_or_else(|p| p.into_inner());
                sleep.retain(|k, _| new_set.contains(k));
            }
            {
                let mut last_sent = last_sent_map.lock().unwrap_or_else(|p| p.into_inner());
                last_sent.retain(|k, _| new_set.contains(k));
            }
        }

        let new_len = new_clusters.len();
        {
            // Reset the index under the same write lock that swaps the Vec. The
            // producer reads `current_index` inside the `clusters` read lock, so
            // this serializes the swap and prevents an out-of-bounds index.
            let mut current = clusters.write().unwrap_or_else(|p| p.into_inner());
            *current = new_clusters;
            current_index.store(0, Ordering::Relaxed);
        }
        debug!("Cluster set reloaded: {} clusters", new_len);
        true
    }

    /// Spawns a background task that periodically reloads the cluster set from
    /// the database, picking up `b_scheduler_managed` flips and host-tag /
    /// subscription churn without a restart.
    ///
    /// No-op for feeds built from an explicit cluster list (`reload = None`).
    /// Mirrors `ManagedShowsCache::start_refresh_loop`: skip-first-tick,
    /// per-iteration `catch_unwind`, and keep the current set on DB error. The
    /// loop exits when the feed's stop flag is set.
    pub fn start_reload_loop(&self) {
        let Some(reload) = self.reload.clone() else {
            return;
        };
        let clusters = self.clusters.clone();
        let current_index = self.current_index.clone();
        let sleep_map = self.sleep_map.clone();
        let last_sent_map = self.last_sent_map.clone();
        let stop_flag = self.stop_flag.clone();
        let stop_notify = self.stop_notify.clone();

        tokio::spawn(async move {
            let mut interval = tokio::time::interval(CONFIG.queue.cluster_reload_interval);
            // Skip the immediate first tick - build() already loaded on startup.
            // Still race the notify so an immediate Stop doesn't block on a full
            // interval before exit.
            tokio::select! {
                _ = interval.tick() => {}
                _ = stop_notify.notified() => {
                    debug!("Cluster reload loop stopping (feed stopped).");
                    return;
                }
            }
            loop {
                tokio::select! {
                    _ = interval.tick() => {}
                    _ = stop_notify.notified() => {
                        debug!("Cluster reload loop stopping (feed stopped).");
                        break;
                    }
                }
                if stop_flag.load(Ordering::Relaxed) {
                    debug!("Cluster reload loop stopping (feed stopped).");
                    break;
                }
                let result = AssertUnwindSafe(async {
                    match ClusterFeed::load_clusters(
                        reload.facility_id.clone(),
                        &reload.ignore_tags,
                    )
                    .await
                    {
                        Ok(loaded) => {
                            let filtered =
                                ClusterFeed::filter_clusters(loaded, &reload.ignore_tags);
                            Self::apply_reload_inner(
                                &clusters,
                                &current_index,
                                &sleep_map,
                                &last_sent_map,
                                filtered,
                            );
                        }
                        // Keep the current set on a transient failure - never wipe.
                        Err(err) => warn!("Failed to reload clusters: {err}"),
                    }
                })
                .catch_unwind()
                .await;
                if let Err(e) = result {
                    error!("Cluster reload iteration panicked: {:?}", e);
                }
            }
        });
    }

    /// Streams clusters to a channel receiver with backpressure control.
    ///
    /// Creates a producer-consumer pattern where clusters are sent through a channel
    /// to the provided sender. The stream can be controlled via the returned message
    /// channel (for sleep/stop commands).
    ///
    /// # Arguments
    ///
    /// * `sender` - Channel sender for emitting clusters
    ///
    /// # Returns
    ///
    /// * `mpsc::Sender<FeedMessage>` - Control channel for sending sleep/stop messages
    ///
    /// # Behavior
    ///
    /// - Iterates through clusters in round-robin fashion
    /// - Skips sleeping clusters until their wake time expires
    /// - Applies backoff delays between rounds (varies based on sleeping cluster count)
    /// - Stops when receiving a Stop message or when configured empty cycles limit is reached
    /// - Automatically cleans up expired sleep entries
    pub async fn stream(self, sender: mpsc::Sender<Cluster>) -> mpsc::Sender<FeedMessage> {
        // Use a small channel to ensure the producer waits for items to be consumed before
        // generating more
        let (feed_sender, mut feed_receiver) = mpsc::channel(8);

        let stop_flag = self.stop_flag.clone();
        let sleep_map = self.sleep_map.clone();

        // Tracks the last emission time per active cluster, for round-trip
        // histogram. Entries are dropped when a cluster is put to sleep so
        // wake-up doesn't produce a spurious sample covering the sleep
        // duration, and `apply_reload_inner` prunes entries for clusters
        // that no longer exist.
        let last_sent_map = self.last_sent_map.clone();
        let last_sent_map_producer = last_sent_map.clone();

        // Stream clusters on the caller channel
        let feed = self.clusters.clone();
        let current_index_atomic = self.current_index.clone();
        tokio::spawn(async move {
            let mut all_sleeping_rounds: usize = 0;

            loop {
                let iteration = async {
                    // Check stop flag
                    if stop_flag.load(Ordering::Relaxed) {
                        warn!("Cluster received a stop message. Stopping feed.");
                        return ControlFlow::Break(());
                    }

                    let snapshot = {
                        let clusters = feed.read().unwrap_or_else(|poisoned| poisoned.into_inner());
                        if clusters.is_empty() {
                            None
                        } else {
                            // Clamp defensively: a concurrent reload may have shrunk the
                            // Vec since the index was last stored.
                            let current_index =
                                current_index_atomic.load(Ordering::Relaxed) % clusters.len();
                            let item = clusters[current_index].clone();
                            let next_index = (current_index + 1) % clusters.len();
                            let completed_round = next_index == 0; // Detect wrap-around
                            current_index_atomic.store(next_index, Ordering::Relaxed);

                            Some((item, clusters.len(), completed_round))
                        }
                    };

                    // An empty set is transient with hot reload (e.g. every show
                    // was flipped to Cuebot-managed). Idle and re-check rather than
                    // terminating; the reload loop will repopulate.
                    let Some((item, cluster_size, completed_round)) = snapshot else {
                        tokio::time::sleep(EMPTY_FEED_POLL_INTERVAL).await;
                        return ControlFlow::Continue(());
                    };

                    // Skip cluster if it is marked as sleeping
                    let is_sleeping = {
                        let mut sleep_map_lock =
                            sleep_map.lock().unwrap_or_else(|p| p.into_inner());
                        if let Some(wake_up_time) = sleep_map_lock.get(&item) {
                            if *wake_up_time > SystemTime::now() {
                                // Still sleeping, skip it
                                true
                            } else {
                                // Remove expired entries
                                sleep_map_lock.remove(&item);
                                false
                            }
                        } else {
                            false
                        }
                    };

                    if !is_sleeping {
                        if sender.send(item.clone()).await.is_err() {
                            warn!("Cluster receiver dropped. Stopping feed.");
                            return ControlFlow::Break(());
                        }
                        let now = Instant::now();
                        let mut last_sent_lock = last_sent_map_producer
                            .lock()
                            .unwrap_or_else(|p| p.into_inner());
                        if let Some(prev) = last_sent_lock.insert(item, now) {
                            observe_cluster_round_trip(now.duration_since(prev));
                        }
                    } else if !completed_round {
                        // Skipped a sleeping cluster mid-round; yield so we don't starve the runtime.
                        tokio::task::yield_now().await;
                    }

                    // At end of round, add backoff sleep
                    if completed_round {
                        CLUSTER_ROUNDS.fetch_add(1, Ordering::Relaxed);

                        // Check if all/most clusters are sleeping
                        let sleeping_count = {
                            let sleep_map_lock =
                                sleep_map.lock().unwrap_or_else(|p| p.into_inner());
                            sleep_map_lock.len()
                        };
                        if sleeping_count >= cluster_size {
                            // Ensure this doesn't loop forever when there's a limit configured
                            all_sleeping_rounds += 1;
                            if let Some(max_empty_cycles) =
                                CONFIG.queue.empty_job_cycles_before_quiting
                            {
                                if all_sleeping_rounds > max_empty_cycles {
                                    warn!("All clusters have been sleeping for too long");
                                    return ControlFlow::Break(());
                                }
                            }

                            // All clusters sleeping, sleep longer
                            tokio::time::sleep(Duration::from_secs(5)).await;
                        } else if sleeping_count > 0 {
                            // Some clusters sleeping, brief pause
                            all_sleeping_rounds = 0;
                            tokio::time::sleep(Duration::from_millis(100)).await;
                        } else {
                            // Active work, minimal pause
                            all_sleeping_rounds = 0;
                            tokio::time::sleep(Duration::from_millis(10)).await;
                        }
                    }
                    ControlFlow::Continue(())
                };

                match AssertUnwindSafe(iteration).catch_unwind().await {
                    Ok(ControlFlow::Break(())) => break,
                    Ok(ControlFlow::Continue(())) => {}
                    Err(e) => {
                        error!("Cluster feed producer iteration panicked: {:?}", e);
                        // Back off before retrying to avoid a tight spin loop on
                        // deterministic panics.
                        tokio::time::sleep(Duration::from_secs(1)).await;
                    }
                }
            }
        });

        // Process messages on the receiving end
        let stop_flag_recv = self.stop_flag.clone();
        let stop_notify_recv = self.stop_notify.clone();
        let sleep_map = self.sleep_map.clone();
        let last_sent_map_receiver = last_sent_map.clone();
        tokio::spawn(async move {
            loop {
                let iteration = async {
                    let Some(message) = feed_receiver.recv().await else {
                        return ControlFlow::Break(());
                    };
                    match message {
                        FeedMessage::Sleep(cluster, duration) => {
                            let requested_wake_up_time = SystemTime::now().checked_add(duration);
                            if let Some(wake_up_time) = requested_wake_up_time {
                                debug!("{:?} put to sleep for {}s", cluster, duration.as_secs());
                                {
                                    let mut last_sent_lock = last_sent_map_receiver
                                        .lock()
                                        .unwrap_or_else(|p| p.into_inner());
                                    last_sent_lock.remove(&cluster);
                                }
                                {
                                    let mut sleep_map_lock =
                                        sleep_map.lock().unwrap_or_else(|p| p.into_inner());
                                    sleep_map_lock.insert(cluster, wake_up_time);
                                }
                            } else {
                                warn!(
                                    "Sleep request ignored for {:?}. Invalid duration={}s",
                                    cluster,
                                    duration.as_secs()
                                );
                            }
                            ControlFlow::Continue(())
                        }
                        FeedMessage::Stop() => {
                            stop_flag_recv.store(true, Ordering::Relaxed);
                            // notify_one() stores a permit if nobody's parked
                            // yet, so the reload loop sees the wake even if it
                            // was mid-body when Stop arrived.
                            stop_notify_recv.notify_one();
                            ControlFlow::Break(())
                        }
                    }
                };

                match AssertUnwindSafe(iteration).catch_unwind().await {
                    Ok(ControlFlow::Break(())) => break,
                    Ok(ControlFlow::Continue(())) => {}
                    Err(e) => {
                        error!("Cluster feed receiver iteration panicked: {:?}", e);
                        // Back off before retrying to avoid a tight spin loop on
                        // deterministic panics.
                        tokio::time::sleep(Duration::from_secs(1)).await;
                    }
                }
            }
        });

        feed_sender
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
/// * `Ok(String)` - The facility ID (verbatim from the DB, canonical casing)
/// * `Err(miette::Error)` - If facility not found or database error
pub async fn get_facility_id(facility_name: &str) -> Result<String> {
    let cluster_dao = ClusterDao::new().await?;
    cluster_dao
        .get_facility_id(facility_name)
        .await
        .into_diagnostic()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cluster(tag: &str) -> Cluster {
        Cluster::single_tag(
            "facility".to_string(),
            Uuid::nil(),
            Tag {
                name: tag.to_string(),
                ttype: TagType::Alloc,
                alloc_id: None,
            },
        )
    }

    fn cluster_names(feed: &ClusterFeed) -> Vec<String> {
        let clusters = feed.clusters.read().unwrap();
        let mut names: Vec<String> = clusters
            .iter()
            .flat_map(|c| c.tags.iter().map(|t| t.name.clone()))
            .collect();
        names.sort();
        names
    }

    /// A genuinely different set is swapped in; the index resets, sleep and
    /// last-sent entries for survivors are preserved, and entries for removed
    /// clusters are dropped.
    #[test]
    fn apply_reload_swaps_on_change() {
        let feed = ClusterFeed::load_from_clusters(vec![cluster("a"), cluster("b")], &[]);
        // Simulate an advanced round-robin position and two sleeping clusters
        // with last-sent baselines, one of which will survive the swap and one
        // that will be removed.
        feed.current_index.store(5, Ordering::Relaxed);
        let now = SystemTime::now();
        feed.sleep_map.lock().unwrap().insert(cluster("a"), now);
        feed.sleep_map.lock().unwrap().insert(cluster("b"), now);
        let baseline = Instant::now();
        feed.last_sent_map
            .lock()
            .unwrap()
            .insert(cluster("a"), baseline);
        feed.last_sent_map
            .lock()
            .unwrap()
            .insert(cluster("b"), baseline);

        // "a" survives, "b" is removed, "c" is new.
        let changed = feed.apply_reload(vec![cluster("a"), cluster("c")]);

        assert!(changed);
        assert_eq!(cluster_names(&feed), vec!["a".to_string(), "c".to_string()]);
        assert_eq!(feed.current_index.load(Ordering::Relaxed), 0);
        let sleep = feed.sleep_map.lock().unwrap();
        assert_eq!(sleep.len(), 1);
        assert!(sleep.contains_key(&cluster("a")));
        let last_sent = feed.last_sent_map.lock().unwrap();
        assert_eq!(last_sent.len(), 1);
        assert!(last_sent.contains_key(&cluster("a")));
    }

    /// The same members in a different order are not a change: no swap, and
    /// the existing index / sleep state is left untouched.
    #[test]
    fn apply_reload_is_noop_when_unchanged_ignoring_order() {
        let feed = ClusterFeed::load_from_clusters(vec![cluster("a"), cluster("b")], &[]);
        feed.current_index.store(1, Ordering::Relaxed);
        feed.sleep_map
            .lock()
            .unwrap()
            .insert(cluster("a"), SystemTime::now());

        let changed = feed.apply_reload(vec![cluster("b"), cluster("a")]);

        assert!(!changed);
        assert_eq!(feed.current_index.load(Ordering::Relaxed), 1);
        assert_eq!(feed.sleep_map.lock().unwrap().len(), 1);
    }

    /// Reloading to an empty set is a valid change (every show un-managed):
    /// the feed goes empty without panicking; the producer idles on it.
    #[test]
    fn apply_reload_to_empty_set() {
        let feed = ClusterFeed::load_from_clusters(vec![cluster("a")], &[]);

        let changed = feed.apply_reload(vec![]);

        assert!(changed);
        assert!(feed.clusters.read().unwrap().is_empty());
        assert_eq!(feed.current_index.load(Ordering::Relaxed), 0);
    }
}
