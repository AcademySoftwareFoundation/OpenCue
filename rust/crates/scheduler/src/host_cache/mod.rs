mod cache;
pub use cache::HostCache;

use bytesize::ByteSize;
use itertools::Itertools;
use miette::{Diagnostic, IntoDiagnostic, miette};
use std::{
    cmp::Ordering,
    sync::{
        Arc,
        atomic::{self, AtomicU64, AtomicUsize},
    },
};
use thiserror::Error;

use dashmap::{DashMap, try_result::TryResult};
use futures::{StreamExt, stream};
use miette::Result;
use tokio::{
    sync::{Mutex, OnceCell, Semaphore},
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
    groups: DashMap<ClusterKey, HostCache>,
    cache_hit: AtomicU64,
    cache_miss: AtomicU64,
    concurrency_semaphore: Arc<Semaphore>,
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
        let cache_hit: AtomicU64 = AtomicU64::new(0);
        let cache_miss: AtomicU64 = AtomicU64::new(0);

        Ok(HostCacheService {
            host_dao,
            groups: DashMap::new(),
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
        debug!("Entered check_out");
        for cache_key in cache_keys {
            debug!("attempting key {}", cache_key);
            // Get group from caches
            let cached_candidate = match self.groups.try_get_mut(&cache_key) {
                TryResult::Present(mut cached_group) if !cached_group.expired() => {
                    debug!("{}: Found on cache", cache_key);
                    self.cache_hit.fetch_add(1, atomic::Ordering::Relaxed);
                    cached_group
                        // Checkout host from a group
                        .check_out(cores, memory, &validation)
                        .map(|host| (cache_key.clone(), host.clone()))
                        .ok()
                }
                // If this group is already locked, there's another thread loading it from the
                // database. Skip to the next tag or rely on the retry trigerred by
                // NoCandidateAvailable
                TryResult::Locked => continue,
                _ => {
                    debug!("{}: NotFound on cache", cache_key);
                    self.cache_miss.fetch_add(1, atomic::Ordering::Relaxed);
                    None
                }
            };
            match cached_candidate {
                Some(cached) => {
                    return Ok(cached);
                }
                None => {
                    debug!("{}: Going to fetch group data", cache_key);
                    let mut group = self
                        .fetch_group_data(&cache_key)
                        .await
                        .map_err(|err| HostCacheError::FailedToQueryHostCache(err.to_string()))?;
                    debug!("{}: got group data", cache_key);
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

        match self.groups.try_get_mut(&cluster_key) {
            TryResult::Present(mut group) => {
                group.check_in(host);
            }
            TryResult::Absent => {
                // Noop. The group might have expired, therefore checkin in makes no sense
            }
            TryResult::Locked => {
                panic!("Dead")
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
        debug!("{}: Getting permit", key);
        let _permit = self
            .concurrency_semaphore
            .acquire()
            .await
            .into_diagnostic()?;
        debug!("{}: Got permit", key);

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
