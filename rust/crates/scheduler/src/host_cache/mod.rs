mod cache;
pub use cache::HostCache;

use bytesize::ByteSize;
use itertools::Itertools;
use miette::Diagnostic;
use std::{cmp::Ordering, collections::HashMap, sync::Arc};
use thiserror::Error;

use dashmap::DashMap;
use futures::{StreamExt, stream};
use miette::Result;
use tokio::{sync::OnceCell, time};
use tracing::error;
use uuid::Uuid;

use crate::{
    cluster_key::ClusterKey,
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
    alloc_tags: HashMap<String, ()>,
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

        let alloc_tags = host_dao.fetch_all_alloc_tags().await?;

        Ok(HostCacheService {
            host_dao,
            groups: DashMap::new(),
            alloc_tags,
        })
    }

    pub async fn checkout<F>(
        &self,
        facility_id: Uuid,
        show_id: Uuid,
        tags: Vec<String>,
        cores: CoreSize,
        memory: ByteSize,
        validation: F,
    ) -> Result<(ClusterKey, Host), HostCacheError>
    where
        F: Fn(&Host) -> bool,
    {
        let cache_keys = self.gen_cache_keys(facility_id, show_id, tags);
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
        facility_id: Uuid,
        show_id: Uuid,
        tags: Vec<String>,
    ) -> impl IntoIterator<Item = ClusterKey> {
        tags.into_iter()
            .map(|tag| {
                if self.alloc_tags.contains_key(&tag) {
                    ClusterKey {
                        facility_show: Some((facility_id, show_id)),
                        tag,
                    }
                } else {
                    ClusterKey {
                        facility_show: None,
                        tag,
                    }
                }
            })
            .sorted_by(|l, r| match (l.is_custom_tag(), r.is_custom_tag()) {
                (true, false) => Ordering::Less,
                (false, true) => Ordering::Greater,
                _ => Ordering::Equal,
            })
    }

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

            stream::iter(&group_keys)
                .map(|group_key| {
                    let caches = caches.clone();

                    async move {
                        // Skip groups if it exists on the cache but haven't been queried for a while
                        match caches.get(group_key) {
                            Some(group) if group.is_idle() => {}
                            _ => {
                                self.fetch_group_data(group_key).await;
                            }
                        }
                    }
                })
                .buffer_unordered(CONFIG.host_cache.concurrent_groups)
                .collect::<Vec<()>>()
                .await;
        }
    }

    async fn fetch_group_data(&self, key: &ClusterKey) {
        // TODO: When jobs as searching for hosts, they don't know if they should search by facility+show+tag or just tag.k
        let tag = key.tag.clone();
        let mut hosts_stream:
            // Ugly splicit type is needed here to make the compiler happy
            Box<dyn futures::Stream<Item = Result<_, sqlx::Error>> + Unpin + Send,
        > = match key.facility_show {
            Some(facility_show) => Box::new(
                self.host_dao.fetch_hosts_by_show_facility_tag(&facility_show.0, &facility_show.1, tag)),
            None => Box::new(self.host_dao.fetch_hosts_by_tag(tag)),
        };

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
