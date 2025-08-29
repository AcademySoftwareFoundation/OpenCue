use futures::StreamExt;
use miette::Result;
use std::sync::Arc;
use tracing::error;

use uuid::Uuid;

use crate::{cluster_key::ClusterKey, config::CONFIG, dao::ClusterDao};

pub struct ClusterFeed {
    pub keys: Vec<ClusterKey>,
    current_index: usize,
}

impl ClusterFeed {
    /// As of now, with a single node, we're loading all clusters at once
    /// in real live, this should happen on a schedule and should negotiate with
    /// other nodes
    pub async fn load_all() -> Result<Self> {
        let cluster_dao = ClusterDao::from_config(&CONFIG.database).await?;
        let mut stream = cluster_dao.fetch_alloc_clusters();
        let mut keys = Vec::new();

        while let Some(record) = stream.next().await {
            match record {
                Ok(cluster) => keys.push(ClusterKey {
                    facility_show: Some((
                        Uuid::parse_str(&cluster.facility_id).unwrap_or_default(),
                        Uuid::parse_str(&cluster.show_id).unwrap_or_default(),
                    )),
                    tag: cluster.tag,
                }),
                Err(err) => error!("Failed to fetch clusters. {err}"),
            }
        }

        Ok(ClusterFeed {
            keys,
            current_index: 0,
        })
    }
}

impl Iterator for ClusterFeed {
    type Item = ClusterKey;

    fn next(&mut self) -> Option<Self::Item> {
        if self.keys.is_empty() {
            return None;
        }

        let item = self.keys[self.current_index].clone();
        self.current_index = (self.current_index + 1) % self.keys.len();
        Some(item)
    }
}
