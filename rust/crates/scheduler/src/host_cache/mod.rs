mod cache;
pub use cache::HostCache;

use bytesize::ByteSize;
use itertools::Itertools;
use miette::{Diagnostic, IntoDiagnostic, miette};
use scc::{HashMap, hash_map::OccupiedEntry};
use std::{
    cmp::Ordering,
    sync::{
        Arc, Mutex,
        atomic::{self, AtomicU64},
    },
};
use thiserror::Error;

use futures::{StreamExt, stream};
use miette::Result;
use tokio::{
    sync::{OnceCell, Semaphore},
    time,
};
use tracing::{debug, error};

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

#[allow(dead_code)]
pub async fn hit_ratio() -> usize {
    let host_cache = host_cache_service().await;
    match host_cache {
        Ok(cache) => cache.cache_hit_ratio(),
        Err(_) => 0,
    }
}

pub struct HostCacheService {
    host_dao: HostDao,
    groups: HashMap<ClusterKey, HostCache>,
    cache_hit: AtomicU64,
    cache_miss: AtomicU64,
    concurrency_semaphore: Arc<Semaphore>,
}

#[derive(Debug, Error, Diagnostic)]
pub enum HostCacheError {
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
        let cache_hit: AtomicU64 = AtomicU64::new(0);
        let cache_miss: AtomicU64 = AtomicU64::new(0);

        Ok(HostCacheService {
            host_dao,
            groups: HashMap::new(),
            cache_hit,
            cache_miss,
            concurrency_semaphore: Arc::new(Semaphore::new(
                CONFIG.host_cache.concurrent_fetch_permit,
            )),
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
            // Attempt to read from the cache
            let cached_candidate = self
                .groups
                // Using the async counterpart here to prevent blocking during checkout.
                // As the number of groups is not very large, consumers are eventually going to
                // fight for the same rows.
                .read_async(&cache_key, |_, cached_group| {
                    if !cached_group.expired() {
                        cached_group
                            // Checkout host from a group
                            .check_out(cores, memory, &validation)
                            .map(|host| (cache_key.clone(), host.clone()))
                            .ok()
                    } else {
                        None
                    }
                })
                .await
                .flatten();

            // Fetch form the database if not found on cache
            match cached_candidate {
                Some(cached) => {
                    self.cache_hit.fetch_add(1, atomic::Ordering::Relaxed);
                    return Ok(cached);
                }
                None => {
                    self.cache_miss.fetch_add(1, atomic::Ordering::Relaxed);
                    let group = self
                        .fetch_group_data(&cache_key)
                        .await
                        .map_err(|err| HostCacheError::FailedToQueryHostCache(err.to_string()))?;
                    let checked_out_host = group
                        // Checkout host from a group
                        .check_out(cores, memory, &validation)
                        .map(|host| (cache_key, host.clone()));

                    // If a valid host couldn't not be found in this group, try the next tag_key
                    if checked_out_host.is_ok() {
                        return checked_out_host;
                    }
                }
            }
        }
        Err(HostCacheError::NoCandidateAvailable)
    }

    pub fn check_in(&self, cluster_key: ClusterKey, host: Host) {
        debug!("{}: Attempting to checkin", cluster_key);

        match self.groups.get_sync(&cluster_key) {
            Some(group) => {
                group.check_in(host);
            }
            None => {
                // Noop. The group might have expired and will be updated on demand
            }
        }
        debug!("{}: Done checkin", cluster_key);
    }

    pub fn cache_hit_ratio(&self) -> usize {
        let hit = self.cache_hit.load(atomic::Ordering::Relaxed) as f64;
        let miss = self.cache_miss.load(atomic::Ordering::Relaxed) as f64;

        ((hit / (hit + miss)) * 100.0) as usize
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
            let mut cloned_keys = Vec::new();
            self.groups.iter_sync(|key, value| {
                cloned_keys.push((key.clone(), value.is_idle()));
                true
            });

            let groups_for_removal = Arc::new(Mutex::new(vec![]));

            stream::iter(cloned_keys)
                .map(|(group_key, is_idle)| {
                    let groups_for_removal = groups_for_removal.clone();

                    async move {
                        // Skip groups if it exists on the cache but haven't been queried for a while
                        if is_idle {
                            groups_for_removal
                                .lock()
                                .expect("Failed to acquire lock")
                                .push(group_key)
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
            for key in groups_for_removal
                .lock()
                .expect("Failed to acquire lock")
                .iter()
            {
                caches.remove_sync(key);
            }
        }
    }

    async fn fetch_group_data(
        &self,
        key: &ClusterKey,
    ) -> Result<OccupiedEntry<'_, ClusterKey, HostCache>> {
        let _permit = self
            .concurrency_semaphore
            .acquire()
            .await
            .into_diagnostic()?;

        let tag = key.tag.to_string();
        let hosts = self
            .host_dao
            .fetch_hosts_by_show_facility_tag(key.show_id.clone(), key.facility_id.clone(), &tag)
            .await
            .into_diagnostic()?;

        let cache = self.groups.entry_sync(key.clone()).or_default();
        for host_model in hosts {
            cache.check_in(host_model.into());
        }
        cache.ping_fetch();
        Ok(cache)
    }
}
