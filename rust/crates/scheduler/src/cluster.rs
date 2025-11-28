use std::{
    collections::HashMap,
    sync::{
        atomic::{AtomicBool, AtomicUsize, Ordering},
        Arc, Mutex, RwLock,
    },
    time::{Duration, SystemTime},
};

use futures::StreamExt;
use itertools::Itertools;
use miette::{IntoDiagnostic, Result};
use serde::{Deserialize, Serialize};
use tokio::sync::mpsc;
use tracing::{debug, error, warn};
use uuid::Uuid;

use crate::{
    cluster_key::{ClusterKey, Tag, TagType},
    config::CONFIG,
    dao::{helpers::parse_uuid, ClusterDao},
};

pub static CLUSTER_ROUNDS: AtomicUsize = AtomicUsize::new(0);

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq)]
pub enum Cluster {
    ComposedKey(ClusterKey),
    TagsKey(Vec<Tag>),
}

#[derive(Debug)]
pub struct ClusterFeed {
    pub clusters: Arc<RwLock<Vec<Cluster>>>,
    current_index: Arc<AtomicUsize>,
    stop_flag: Arc<AtomicBool>,
    sleep_map: Arc<Mutex<HashMap<Cluster, SystemTime>>>,
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

impl Cluster {
    /// Returns an iterator over the tags associated with this cluster.
    ///
    /// # Returns
    ///
    /// * `Box<dyn Iterator<Item = &Tag>>` - Iterator over tag references
    pub fn tags(&self) -> Box<dyn Iterator<Item = &Tag> + '_> {
        match self {
            Cluster::ComposedKey(cluster_key) => Box::new(std::iter::once(&cluster_key.tag)),
            Cluster::TagsKey(tags) => Box::new(tags.iter()),
        }
    }
}

impl ClusterFeed {
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
    pub async fn load_all(facility_id: &Option<Uuid>, ignore_tags: &[String]) -> Result<Self> {
        let cluster_dao = ClusterDao::new().await?;

        // Fetch clusters for both facilitys+shows+tags and just tags
        let mut clusters_stream = cluster_dao
            .fetch_alloc_clusters()
            .chain(cluster_dao.fetch_non_alloc_clusters());
        let mut clusters = Vec::new();
        let mut manual_tags = Vec::new();
        let mut hostname_tags = Vec::new();

        // Collect all tags
        while let Some(record) = clusters_stream.next().await {
            match record {
                Ok(cluster) => {
                    // Skip tags that are in the ignore list
                    if ignore_tags.contains(&cluster.tag) {
                        continue;
                    }

                    match cluster.ttype.as_str() {
                        // Each alloc tag becomes its own cluster
                        "ALLOC" => {
                            let cluster_facility_id = parse_uuid(&cluster.facility_id);
                            if facility_id
                                .as_ref()
                                .map(|fid| fid == &cluster_facility_id)
                                .unwrap_or(true)
                            {
                                clusters.push(Cluster::ComposedKey(ClusterKey {
                                    facility_id: cluster_facility_id,
                                    show_id: parse_uuid(&cluster.show_id),
                                    tag: Tag {
                                        name: cluster.tag,
                                        ttype: TagType::Alloc,
                                    },
                                }));
                            }
                        }
                        // Manual and hostname tags are collected to be chunked
                        "MANUAL" => manual_tags.push(cluster.tag),
                        "HOSTNAME" => hostname_tags.push(cluster.tag),
                        _ => (),
                    };
                }
                Err(err) => error!("Failed to fetch clusters. {err}"),
            }
        }

        // Chunk Manual tags
        for chunk in &manual_tags
            .into_iter()
            .chunks(CONFIG.queue.manual_tags_chunk_size)
        {
            clusters.push(Cluster::TagsKey(
                chunk
                    .map(|name| Tag {
                        name,
                        ttype: TagType::Manual,
                    })
                    .collect(),
            ))
        }

        // Chunk Hostname tags
        for chunk in &hostname_tags
            .into_iter()
            .chunks(CONFIG.queue.hostname_tags_chunk_size)
        {
            clusters.push(Cluster::TagsKey(
                chunk
                    .map(|name| Tag {
                        name,
                        ttype: TagType::HostName,
                    })
                    .collect(),
            ))
        }
        Ok(ClusterFeed {
            clusters: Arc::new(RwLock::new(clusters)),
            current_index: Arc::new(AtomicUsize::new(0)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            sleep_map: Arc::new(Mutex::new(HashMap::new())),
        })
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
    #[allow(dead_code)]
    pub fn load_from_clusters(clusters: Vec<Cluster>, ignore_tags: &[String]) -> Self {
        // Filter out ignored tags from clusters
        let filtered_clusters: Vec<Cluster> = clusters
            .into_iter()
            .filter_map(|cluster| match cluster {
                // For ComposedKey, remove the entire cluster if its tag is ignored
                Cluster::ComposedKey(key) => {
                    if ignore_tags.contains(&key.tag.name) {
                        None
                    } else {
                        Some(Cluster::ComposedKey(key))
                    }
                }
                // For TagsKey, filter out ignored tags from the list
                Cluster::TagsKey(tags) => {
                    let filtered_tags: Vec<Tag> = tags
                        .into_iter()
                        .filter(|tag| !ignore_tags.contains(&tag.name))
                        .collect();
                    // Only keep the cluster if it still has tags after filtering
                    if filtered_tags.is_empty() {
                        None
                    } else {
                        Some(Cluster::TagsKey(filtered_tags))
                    }
                }
            })
            .collect();

        ClusterFeed {
            clusters: Arc::new(RwLock::new(filtered_clusters)),
            current_index: Arc::new(AtomicUsize::new(0)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            sleep_map: Arc::new(Mutex::new(HashMap::new())),
        }
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
        let (cancel_sender, mut feed_receiver) = mpsc::channel(8);

        let stop_flag = self.stop_flag.clone();
        let sleep_map = self.sleep_map.clone();

        // Stream clusters on the caller channel
        tokio::spawn(async move {
            let mut all_sleeping_rounds = 0;
            let feed = self.clusters.clone();
            let current_index_atomic = self.current_index.clone();

            loop {
                // Check stop flag
                if stop_flag.load(Ordering::Relaxed) {
                    warn!("Cluster received a stop message. Stopping feed.");
                    break;
                }

                let (item, cluster_size, completed_round) = {
                    let clusters = feed.read().unwrap_or_else(|poisoned| poisoned.into_inner());
                    if clusters.is_empty() {
                        break;
                    }

                    let current_index = current_index_atomic.load(Ordering::Relaxed);
                    let item = clusters[current_index].clone();
                    let next_index = (current_index + 1) % clusters.len();
                    let completed_round = next_index == 0; // Detect wrap-around
                    current_index_atomic.store(next_index, Ordering::Relaxed);

                    (item, clusters.len(), completed_round)
                };

                // Skip cluster if it is marked as sleeping
                let is_sleeping = {
                    let mut sleep_map_lock = sleep_map.lock().unwrap_or_else(|p| p.into_inner());
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

                if !is_sleeping && sender.send(item).await.is_err() {
                    warn!("Cluster receiver dropped. Stopping feed.");
                    break;
                }

                // At end of round, add backoff sleep
                if completed_round {
                    CLUSTER_ROUNDS.fetch_add(1, Ordering::Relaxed);

                    // Check if all/most clusters are sleeping
                    let sleeping_count = {
                        let sleep_map_lock = sleep_map.lock().unwrap_or_else(|p| p.into_inner());
                        sleep_map_lock.len()
                    };
                    if sleeping_count >= cluster_size {
                        // Ensure this doesn't loop forever when there's a limit configured
                        all_sleeping_rounds += 1;
                        if let Some(max_empty_cycles) = CONFIG.queue.empty_job_cycles_before_quiting
                        {
                            if all_sleeping_rounds > max_empty_cycles {
                                warn!("All clusters have been sleeping for too long");
                                break;
                            }
                        }

                        // All clusters sleeping, sleep longer
                        tokio::time::sleep(Duration::from_secs(5)).await;
                    } else if sleeping_count > 0 {
                        // Some clusters sleeping, brief pause
                        tokio::time::sleep(Duration::from_millis(100)).await;
                    } else {
                        // Active work, minimal pause
                        tokio::time::sleep(Duration::from_millis(10)).await;
                    }
                }
            }
        });

        // Process messages on the receiving end
        let sleep_map = self.sleep_map.clone();
        tokio::spawn(async move {
            while let Some(message) = feed_receiver.recv().await {
                match message {
                    FeedMessage::Sleep(cluster, duration) => {
                        if let Some(wake_up_time) = SystemTime::now().checked_add(duration) {
                            debug!("{:?} put to sleep for {}s", cluster, duration.as_secs());
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
                    }
                    FeedMessage::Stop() => {
                        self.stop_flag.store(true, Ordering::Relaxed);
                        break;
                    }
                }
            }
        });

        cancel_sender
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
