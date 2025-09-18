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

pub struct ClusterFeed {
    pub keys: Vec<Cluster>,
    current_index: usize,
    rounds: usize,
    run_once: bool,
}

impl Cluster {
    pub fn tags(&self) -> Box<dyn Iterator<Item = &Tag> + '_> {
        match self {
            Cluster::ComposedKey(cluster_key) => Box::new(std::iter::once(&cluster_key.tag)),
            Cluster::TagsKey(tags) => Box::new(tags.iter()),
        }
    }
}

impl ClusterFeed {
    /// As of now, with a single node, we're loading all clusters at once
    /// in real live, this should happen on a schedule and should negotiate with
    /// other nodes
    pub async fn load_all(run_once: bool) -> Result<Self> {
        let cluster_dao = ClusterDao::from_config(&CONFIG.database).await?;

        // Fetch clusters for both facilitys+shows+tags and just tags
        let mut stream = cluster_dao
            .fetch_alloc_clusters()
            .chain(cluster_dao.fetch_non_alloc_clusters());
        let mut clusters = Vec::new();
        let mut manual_tags = Vec::new();
        let mut hostname_tags = Vec::new();

        // Collect all tags
        while let Some(record) = stream.next().await {
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

    /// Constructor for testing purposes
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
