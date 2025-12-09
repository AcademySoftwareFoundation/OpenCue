use actix::{Actor, ActorFutureExt, AsyncContext, Handler, ResponseActFuture, WrapFuture};

use itertools::Itertools;
use miette::IntoDiagnostic;
use scc::{hash_map::OccupiedEntry, HashMap, HashSet};
use std::{
    cmp::Ordering,
    sync::{
        atomic::{self, AtomicU64},
        Arc,
    },
    time::{Duration, SystemTime},
};

use futures::{stream, StreamExt};
use miette::Result;
use tokio::sync::Semaphore;
use tracing::{debug, error, info, trace};

use crate::{
    cluster_key::{ClusterKey, Tag, TagType},
    config::CONFIG,
    dao::HostDao,
    host_cache::*,
    host_cache::{messages::*, store},
    models::Host,
};

#[derive(Clone)]
pub struct HostCacheService {
    host_dao: Arc<HostDao>,
    cluster_index: Arc<HashMap<ClusterKey, HostCache>>,
    reserved_hosts: Arc<HashMap<HostId, HostReservation>>,
    cache_hit: Arc<AtomicU64>,
    cache_miss: Arc<AtomicU64>,
    concurrency_semaphore: Arc<Semaphore>,
}

/// Use a reservation system to prevent race conditions when trying to book a host
/// that belongs to multiple groups.
struct HostReservation {
    reserved_time: SystemTime,
}

impl HostReservation {
    pub fn new() -> Self {
        HostReservation {
            reserved_time: SystemTime::now(),
        }
    }

    pub fn expired(&self) -> bool {
        self.reserved_time.elapsed().unwrap_or_default() > Duration::from_secs(10)
    }
}

impl Actor for HostCacheService {
    type Context = actix::Context<Self>;

    fn started(&mut self, ctx: &mut Self::Context) {
        let service_for_monitor = self.clone();
        let service_for_clean_up = self.clone();

        ctx.run_interval(CONFIG.host_cache.monitoring_interval, move |_act, ctx| {
            let service = service_for_monitor.clone();
            let actor_clone = service.clone();
            ctx.spawn(async move { service.refresh_cache().await }.into_actor(&actor_clone));
        });

        ctx.run_interval(CONFIG.host_cache.clean_up_interval, move |_act, _ctx| {
            let service = service_for_clean_up.clone();

            // Clean up stale hosts from the host store
            service.cleanup_stale_hosts();
        });

        info!("HostCacheService actor started");
    }

    fn stopped(&mut self, _ctx: &mut Self::Context) {
        info!("HostCacheService actor stopped");
    }
}

impl<F> Handler<CheckOut<F>> for HostCacheService
where
    F: Fn(&Host) -> bool + 'static,
{
    type Result = ResponseActFuture<Self, Result<CheckedOutHost, HostCacheError>>;

    fn handle(&mut self, msg: CheckOut<F>, _ctx: &mut Self::Context) -> Self::Result {
        let CheckOut {
            facility_id,
            show_id,
            tags,
            resource_request,
            validation,
        } = msg;

        let service = self.clone();

        Box::pin(
            async move {
                let out = service
                    .check_out(facility_id, show_id, tags, resource_request, validation)
                    .await;
                if let Ok(host) = &out {
                    debug!("Checked out {}", host.1);
                }
                out
            }
            .into_actor(self)
            .map(|result, _, _| result),
        )
    }
}

impl Handler<CheckIn> for HostCacheService {
    type Result = ();

    fn handle(&mut self, msg: CheckIn, _ctx: &mut Self::Context) -> Self::Result {
        let CheckIn(cluster_key, payload) = msg;
        match payload {
            CheckInPayload::Host(host) => {
                let host_str = format!("{}", host);
                self.check_in(cluster_key, host);

                debug!("Checked in {}", &host_str);
            }
            CheckInPayload::Invalidate(host_id) => {
                let _ = self.reserved_hosts.remove_sync(&host_id);

                debug!("Checked in {} (invalid)", &host_id);
            }
        }
    }
}

impl Handler<CacheRatio> for HostCacheService {
    type Result = CacheRatioResponse;

    fn handle(&mut self, _msg: CacheRatio, _ctx: &mut Self::Context) -> Self::Result {
        CacheRatioResponse {
            hit: self.cache_hit.load(atomic::Ordering::Relaxed),
            miss: self.cache_miss.load(atomic::Ordering::Relaxed),
            hit_ratio: self.cache_hit_ratio(),
        }
    }
}

impl HostCacheService {
    /// Creates a new HostCacheService with empty cache groups.
    ///
    /// Initializes the service with DAO access, cache tracking metrics,
    /// and concurrency controls.
    ///
    /// # Returns
    ///
    /// * `Ok(HostCacheService)` - New service instance
    /// * `Err(miette::Error)` - Failed to initialize dependencies
    pub(in crate::host_cache) async fn new() -> Result<Self> {
        Ok(HostCacheService {
            host_dao: Arc::new(HostDao::new().await?),
            cluster_index: Arc::new(HashMap::new()),
            cache_hit: Arc::new(AtomicU64::new(0)),
            cache_miss: Arc::new(AtomicU64::new(0)),
            concurrency_semaphore: Arc::new(Semaphore::new(
                CONFIG.host_cache.concurrent_fetch_permit,
            )),
            reserved_hosts: Arc::new(HashMap::new()),
        })
    }

    /// Checks out a host from the cache that matches the requirements.
    ///
    /// Searches through cache groups for each tag until a suitable host is found.
    /// If not found in cache, fetches from database. Implements host reservation
    /// to prevent race conditions.
    ///
    /// # Arguments
    ///
    /// * `facility_id` - Facility identifier
    /// * `show_id` - Show identifier
    /// * `tags` - List of tags to search (tried in priority order)
    /// * `cores` - Minimum cores required
    /// * `memory` - Minimum memory required
    /// * `validation` - Additional validation function
    ///
    /// # Returns
    ///
    /// * `Ok(CheckedOutHost)` - Host with cluster key
    /// * `Err(HostCacheError)` - No suitable host found or database error
    async fn check_out<F>(
        &self,
        facility_id: Uuid,
        show_id: Uuid,
        tags: Vec<Tag>,
        resource_request: ResourceRequest,
        validation: F,
    ) -> Result<CheckedOutHost, HostCacheError>
    where
        F: Fn(&Host) -> bool,
    {
        let cache_keys = self.gen_cache_keys(facility_id, show_id, tags);

        // Extend validation to also check for hosts that are already reserved
        let validation = |host: &Host| {
            let available = self
                .reserved_hosts
                .read_sync(&host.id, |_, reservation| reservation.expired())
                .unwrap_or(true);
            validation(host) && available
        };

        for cache_key in cache_keys {
            // Attempt to read from the cache
            let cached_candidate = self
                .cluster_index
                // Using the async counterpart here to prevent blocking during checkout.
                // As the number of groups is not very large, consumers are eventually going to
                // fight for the same rows.
                .read_async(&cache_key, |_, cached_group| {
                    if !cached_group.expired() {
                        // Checkout host from a group
                        cached_group
                            .check_out(resource_request, validation)
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
                    self.reserve_host(cached.1.id, true);
                    return Ok(CheckedOutHost(cached.0, cached.1));
                }
                None => {
                    let group = self
                        .fetch_group_data(&cache_key)
                        .await
                        .map_err(|err| HostCacheError::FailedToQueryHostCache(err.to_string()))?;
                    let checked_out_host = group
                        // Checkout host from a group
                        .check_out(resource_request, validation)
                        .map(|host| CheckedOutHost(cache_key.clone(), host.clone()));

                    if let Ok(checked_out_host) = checked_out_host {
                        self.reserve_host(checked_out_host.1.id, false);
                        // Only count as a cache miss if there was a host candidate available
                        return Ok(checked_out_host);
                    } else {
                        debug!(
                            "Wasn't able to find suitable hosts for group {:?}",
                            &cache_key
                        );
                    }
                }
            }
        }
        Err(HostCacheError::NoCandidateAvailable)
    }

    /// Reserves a host to prevent concurrent checkout and tracks cache metrics.
    ///
    /// Marks the host as reserved and updates hit/miss counters for cache
    /// performance tracking.
    ///
    /// # Arguments
    ///
    /// * `host_id` - ID of the host to reserve
    /// * `cache_hit` - Whether this was a cache hit (true) or miss (false)
    fn reserve_host(&self, host_id: HostId, cache_hit: bool) {
        if cache_hit {
            self.cache_hit.fetch_add(1, atomic::Ordering::Relaxed);
        } else {
            self.cache_miss.fetch_add(1, atomic::Ordering::Relaxed);
        }
        // Mark host as reserved
        let _ = self
            .reserved_hosts
            .insert_sync(host_id, HostReservation::new());
    }

    /// Returns a host to the cache group after use.
    ///
    /// Removes the host from reservation and adds it back to the appropriate
    /// cache group. If the group has expired, the host is dropped.
    ///
    /// # Arguments
    ///
    /// * `cluster_key` - The cluster key identifying the cache group
    /// * `host` - Host to return to the cache
    fn check_in(&self, cluster_key: ClusterKey, host: Host) {
        trace!(
            "{}: Attempting to checkin ({}, {})",
            cluster_key,
            host.id,
            host.idle_cores
        );
        let host_id = host.id;

        match self.cluster_index.get_sync(&cluster_key) {
            Some(group) => {
                group.check_in(host, false);
            }
            None => {
                info!(
                    "{} checking in on unexisting group ({}).",
                    host.id, cluster_key
                );
                // Noop. The group might have expired and will be updated on demand
            }
        }
        let _ = self.reserved_hosts.remove_sync(&host_id);

        trace!("{}: Done checkin", cluster_key);
    }

    /// Calculates the cache hit ratio as a percentage.
    ///
    /// # Returns
    ///
    /// * `usize` - Hit ratio percentage (0-100)
    fn cache_hit_ratio(&self) -> usize {
        let hit = self.cache_hit.load(atomic::Ordering::Relaxed) as f64;
        let miss = self.cache_miss.load(atomic::Ordering::Relaxed) as f64;

        ((hit / (hit + miss)) * 100.0) as usize
    }

    /// Generates cache keys from tags in priority order.
    ///
    /// Creates ClusterKey instances for each tag and sorts them by priority:
    /// MANUAL > HOSTNAME > ALLOC. This order ensures more specific tags are
    /// checked first.
    ///
    /// # Arguments
    ///
    /// * `facility_id` - Facility identifier
    /// * `show_id` - Show identifier
    /// * `tags` - Tags to convert to cache keys
    ///
    /// # Returns
    ///
    /// * `impl IntoIterator<Item = ClusterKey>` - Sorted cache keys
    #[allow(clippy::map_entry)]
    fn gen_cache_keys(
        &self,
        facility_id: Uuid,
        show_id: Uuid,
        tags: Vec<Tag>,
    ) -> impl IntoIterator<Item = ClusterKey> {
        tags.into_iter()
            .map(|tag| ClusterKey {
                facility_id,
                show_id,
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

    /// Periodically refreshes cache data and removes idle groups.
    ///
    /// Runs on a timer to update active cache groups from the database and
    /// remove groups that haven't been queried recently.
    async fn refresh_cache(&self) {
        let caches = Arc::new(&self.cluster_index);

        // Clone list of groups keys to avoid keeping a lock through the stream lifetime
        let mut cloned_keys = Vec::new();
        self.cluster_index.iter_sync(|key, value| {
            cloned_keys.push((key.clone(), value.is_idle()));
            true
        });

        let groups_for_removal = HashSet::new();

        stream::iter(cloned_keys)
            .map(|(group_key, is_idle)| {
                let groups_for_removal = groups_for_removal.clone();

                async move {
                    // Skip groups if it exists on the cache but haven't been queried for a while
                    if is_idle {
                        if let Err(err) = groups_for_removal.insert_async(group_key).await {
                            error!("Failed to mark group for removal on host_cache. {}", err);
                        }
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
        groups_for_removal.iter_sync(|key| {
            caches.remove_sync(key);
            true
        });
    }

    /// Removes stale hosts from the global host store.
    ///
    /// This method triggers cleanup of hosts that haven't been updated within
    /// the configured `host_staleness_threshold` duration. It logs the number
    /// of hosts removed for monitoring purposes.
    fn cleanup_stale_hosts(&self) {
        let removed_count = store::HOST_STORE.cleanup_stale_hosts();
        if removed_count > 0 {
            info!("Cleaned up {} stale hosts from store", removed_count);
        }
    }

    /// Fetches host data from the database and populates a cache group.
    ///
    /// Queries the database for hosts matching the cluster key and adds them
    /// to the cache. Uses a semaphore to limit concurrent database queries.
    ///
    /// # Arguments
    ///
    /// * `key` - Cluster key identifying which hosts to fetch
    ///
    /// # Returns
    ///
    /// * `Ok(OccupiedEntry)` - Cache entry with fetched hosts
    /// * `Err(miette::Error)` - Database query failed
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
            .fetch_hosts_by_show_facility_tag(key.show_id, key.facility_id, &tag)
            .await
            .into_diagnostic()?;

        let cache = self.cluster_index.entry_sync(key.clone()).or_default();

        if hosts.is_empty() {
            debug!(
                "Found no suitable hosts on the database for the cluster key {:?}",
                key
            );
        }

        for host in hosts {
            let h: Host = host.into();
            cache.check_in(h, false);
        }
        cache.ping_fetch();
        Ok(cache)
    }
}
