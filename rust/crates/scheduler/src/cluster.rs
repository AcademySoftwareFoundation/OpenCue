use futures::StreamExt;
use itertools::Itertools;
use miette::Result;
use serde::{Deserialize, Serialize};
use tracing::error;

use crate::{
    cluster_key::{ClusterKey, Tag, TagType},
    config::CONFIG,
    dao::ClusterDao,
};

#[derive(Serialize, Deserialize, Debug, Clone, Hash, PartialEq, Eq)]
pub enum Cluster {
    ComposedKey(ClusterKey),
    TagsKey(Vec<Tag>),
}

#[derive(Debug)]
pub struct ClusterFeed {
    pub keys: Vec<Cluster>,
    current_index: usize,
    rounds: usize,
    run_once: bool,
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
    /// * `run_once` - If true, iterator will only iterate through clusters once
    ///
    /// # Returns
    ///
    /// * `Ok(ClusterFeed)` - Successfully loaded cluster feed
    /// * `Err(miette::Error)` - Failed to load clusters from database
    pub async fn load_all(run_once: bool) -> Result<Self> {
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
                    match cluster.ttype.as_str() {
                        // Each alloc tag becomes its own cluster
                        "ALLOC" => {
                            clusters.push(Cluster::ComposedKey(ClusterKey {
                                facility_id: cluster.facility_id,
                                show_id: cluster.show_id,
                                tag: Tag {
                                    name: cluster.tag,
                                    ttype: TagType::Alloc,
                                },
                            }));
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
            keys: clusters,
            current_index: 0,
            run_once,
            rounds: 0,
        })
    }

    /// Creates a ClusterFeed from a predefined list of clusters for testing.
    ///
    /// # Arguments
    ///
    /// * `keys` - List of clusters to iterate over
    ///
    /// # Returns
    ///
    /// * `ClusterFeed` - Feed configured to run once through the provided clusters
    #[allow(dead_code)]
    pub fn new_for_test(keys: Vec<Cluster>) -> Self {
        ClusterFeed {
            keys,
            current_index: 0,
            run_once: true,
            rounds: 0,
        }
    }
}

impl Iterator for ClusterFeed {
    type Item = Cluster;

    fn next(&mut self) -> Option<Self::Item> {
        if self.keys.is_empty() || (self.rounds > 0 && self.run_once) {
            return None;
        }

        // Count number of rounds if we got to the last element
        if self.current_index == self.keys.len() - 1 {
            self.rounds += 1
        }

        let item = self.keys[self.current_index].clone();
        self.current_index = (self.current_index + 1) % self.keys.len();
        let _item_tag: Vec<_> = item.tags().collect();
        Some(item)
        // TODO: Every loop restart should fetch
    }
}
