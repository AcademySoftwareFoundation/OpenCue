mod cache;
pub use cache::HostCache;

use bytesize::ByteSize;
use itertools::Itertools;
use miette::Diagnostic;
use std::{cmp::Ordering, sync::Arc};
use thiserror::Error;

use dashmap::DashMap;
use futures::{StreamExt, stream};
use miette::Result;
use tokio::{
    sync::{Mutex, OnceCell},
    time,
};
use tracing::error;
use uuid::Uuid;

use crate::{
    cluster_key::{ClusterKey, Tag, TagType},
    config::CONFIG,
    dao::HostDao,
    models::{CoreSize, Host},
};

static HOST_CACHE: OnceCell<Arc<HostCacheService>> = OnceCell::const_new();

/// Singleton getter for the cache service
pub async fn host_cache_service() -> Result<Arc<HostCacheService>> {
    HOST_CACHE
        .get_or_try_init(|| async {
            let service = Arc::new(HostCacheService::new().await?);
            service.start().await;

            Ok(service)
        })
        .await
        .map(Arc::clone)
}

pub struct HostCacheService {
    host_dao: HostDao,
    groups: DashMap<ClusterKey, HostCache>,
}

#[derive(Debug, Error, Diagnostic)]
pub enum HostCacheError {
    #[error("Key not found on Cache")]
    KeyNotFoundError(ClusterKey),
    #[error("No host found with the required resources")]
    NoCandidateAvailable,
}

impl HostCacheService {
    async fn new() -> Result<Self> {
        let host_dao = HostDao::from_config(&CONFIG.database).await?;

        Ok(HostCacheService {
            host_dao,
            groups: DashMap::new(),
        })
    }

    pub async fn checkout<F>(
        &self,
        facility_id: Uuid,
        show_id: Uuid,
        tags: Vec<Tag>,
        cores: CoreSize,
        memory: ByteSize,
        validation: F,
    ) -> Result<(ClusterKey, Host), HostCacheError>
    where
        F: Fn(&Host) -> bool,
    {
        let cache_keys = self.gen_cache_keys(&facility_id, &show_id, tags);
        for cache_key in cache_keys {
            let cached_groups = self.groups.get(&cache_key);
            let candidate = match cached_groups {
                Some(cached_group) if !cached_group.expired() => cached_group,
                _ => {
                    self.fetch_group_data(&cache_key).await;
                    self.groups
                        .get(&cache_key)
                        .ok_or(HostCacheError::KeyNotFoundError(cache_key.clone()))?
                }
            }
            .checkout(cores, memory, &validation)
            .map(|host| (cache_key, host.clone()));

            if candidate.is_ok() {
                return candidate;
            }
        }
        Err(HostCacheError::NoCandidateAvailable)
    }

    pub fn checkin(&self, cluster_key: ClusterKey, host: Host) {
        if let Some(group) = self.groups.get(&cluster_key) {
            group.checkin(&host);
        }
    }

    #[allow(clippy::map_entry)]
    fn gen_cache_keys(
        &self,
        facility_id: &Uuid,
        show_id: &Uuid,
        tags: Vec<Tag>,
    ) -> impl IntoIterator<Item = ClusterKey> {
        tags.into_iter()
            .map(|tag| ClusterKey {
                facility_id: *facility_id,
                show_id: *show_id,
                tag,
            })
            // Make sure tags are evaluated in this order: MANUAL -> HOSTNAME -> ALLOC
            .sorted_by(|l, r| match (&l.tag.ttype, &r.tag.ttype) {
                (TagType::Alloc, TagType::Alloc)
                | (TagType::HostName, TagType::HostName)
                | (TagType::Manual, TagType::Manual) => Ordering::Equal,
                (TagType::Manual, _) => Ordering::Less,
                (TagType::HostName, _) => Ordering::Less,
                (TagType::Alloc, _) => Ordering::Greater,
            })
    }

    /// Will loop forever. Should be started on its own thread
    async fn start(&self) {
        let caches = Arc::new(&self.groups);
        // Fetch refresh active groups cashes preemptively on an interval
        let mut interval = time::interval(CONFIG.host_cache.monitoring_interval);

        loop {
            interval.tick().await;

            // Clone list of groups keys to avoid keeping a lock through the stream lifetime
            let group_keys: Vec<ClusterKey> = self
                .groups
                .iter()
                .map(|entry| entry.key().clone())
                .collect();

            let groups_for_removal = Arc::new(Mutex::new(vec![]));

            stream::iter(&group_keys)
                .map(|group_key| {
                    let caches = caches.clone();
                    let groups_for_removal = groups_for_removal.clone();

                    async move {
                        // Skip groups if it exists on the cache but haven't been queried for a while
                        match caches.get(group_key) {
                            Some(group) if group.is_idle() => {
                                groups_for_removal.lock().await.push(group.key().clone())
                            }
                            _ => {
                                self.fetch_group_data(group_key).await;
                            }
                        }
                    }
                })
                .buffer_unordered(CONFIG.host_cache.concurrent_groups)
                .collect::<Vec<()>>()
                .await;

            // Clean up caches that haven't been queried for a while
            for key in groups_for_removal.lock().await.iter() {
                caches.remove(key);
            }
        }
    }

    async fn fetch_group_data(&self, key: &ClusterKey) {
        let tag = key.tag.to_string();
        let mut hosts_stream =
            self.host_dao
                .fetch_hosts_by_show_facility_tag(&key.show_id, &key.facility_id, &tag);

        let mut cache = self.groups.entry(key.clone()).or_insert(HostCache::new());
        while let Some(host) = hosts_stream.next().await {
            match host {
                Ok(host_model) => cache.insert(host_model.into()),
                Err(err) => {
                    error!("Failed to query host for group {}. {}", key, err);
                }
            }
        }
        cache.ping_fetch();
    }
}
