mod cache;
pub use cache::HostCache;

use bytesize::ByteSize;
use itertools::Itertools;
use miette::{Diagnostic, miette};
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
            // TODO: Uncomment and make test aware
            // service.clone().start();

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
    #[error(
        "Failed to query Host. Cache is functional, but can't probably load new values from the database"
    )]
    FailedToQueryHostCache(String),
}

impl HostCacheService {
    async fn new() -> Result<Self> {
        let host_dao = HostDao::from_config(&CONFIG.database).await?;

        Ok(HostCacheService {
            host_dao,
            groups: DashMap::new(),
        })
    }

    pub async fn check_out<F>(
        &self,
        facility_id: String,
        show_id: String,
        tags: Vec<Tag>,
        cores: CoreSize,
        memory: ByteSize,
        validation: F,
    ) -> Result<(ClusterKey, Host), HostCacheError>
    where
        F: Fn(&Host) -> bool,
    {
        let cache_keys = self.gen_cache_keys(facility_id, show_id, tags);
        for cache_key in cache_keys {
            // Get group from caches, or database if it a group has expired
            let candidate = match self.groups.get_mut(&cache_key) {
                Some(cached_group) if !cached_group.expired() => cached_group,
                _ => self
                    .fetch_group_data(&cache_key)
                    .await
                    .map_err(|err| HostCacheError::FailedToQueryHostCache(err.to_string()))?,
            }
            // Checkout host from a group
            .check_out(cores, memory, &validation)
            .map(|host| (cache_key, host.clone()));

            if candidate.is_ok() {
                return candidate;
            }
        }
        Err(HostCacheError::NoCandidateAvailable)
    }

    pub fn check_in(&self, cluster_key: ClusterKey, host: Host) {
        if let Some(mut group) = self.groups.get_mut(&cluster_key) {
            group.check_in(host);
        }
    }

    #[allow(clippy::map_entry)]
    fn gen_cache_keys(
        &self,
        facility_id: String,
        show_id: String,
        tags: Vec<Tag>,
    ) -> impl IntoIterator<Item = ClusterKey> {
        tags.into_iter()
            .map(|tag| ClusterKey {
                facility_id: facility_id.clone(),
                show_id: show_id.clone(),
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

    fn start(self: Arc<Self>) {
        let service = self.clone();
        // Will loop forever on its own thread
        tokio::spawn(async move { service.start_loop().await });
    }

    async fn start_loop(&self) {
        let caches = Arc::new(&self.groups);
        // Fetch refresh active groups cashes preemptively on an interval
        let mut interval = time::interval(CONFIG.host_cache.monitoring_interval);

        loop {
            interval.tick().await;

            // Clone list of groups keys to avoid keeping a lock through the stream lifetime
            let group_keys: Vec<_> = self
                .groups
                .iter()
                .map(|entry| (entry.key().clone(), entry.value().is_idle()))
                .collect();

            let groups_for_removal = Arc::new(Mutex::new(vec![]));

            stream::iter(group_keys)
                .map(|(group_key, is_idle)| {
                    let groups_for_removal = groups_for_removal.clone();

                    async move {
                        // Skip groups if it exists on the cache but haven't been queried for a while
                        if is_idle {
                            groups_for_removal.lock().await.push(group_key)
                        } else if let Err(err) = self.fetch_group_data(&group_key).await {
                            error!(
                                "Failed to fetch cache data on cache loop for key {}.{}",
                                group_key, err
                            );
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

    async fn fetch_group_data(
        &self,
        key: &ClusterKey,
    ) -> Result<dashmap::mapref::one::RefMut<'_, ClusterKey, HostCache>> {
        let tag = key.tag.to_string();
        let mut hosts_stream = self.host_dao.fetch_hosts_by_show_facility_tag(
            key.show_id.clone(),
            key.facility_id.clone(),
            &tag,
        );

        let mut cache = self.groups.entry(key.clone()).or_default();
        while let Some(host) = hosts_stream.next().await {
            match host {
                Ok(host_model) => cache.check_in(host_model.into()),
                Err(err) => Err(miette!("Failed to query host for group {}. {}", key, err))?,
            }
        }
        cache.ping_fetch();
        Ok(cache)
    }
}
