// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use actix::{Actor, ActorFutureExt, AsyncContext, Handler, ResponseActFuture, WrapFuture};

use bytesize::ByteSize;
use itertools::Itertools;
use miette::IntoDiagnostic;
use scc::{hash_map::OccupiedEntry, HashMap, HashSet};
use std::{
    cmp::Ordering,
    sync::{
        atomic::{self, AtomicU32, AtomicU64},
        Arc, Mutex,
    },
    time::{Duration, Instant, SystemTime},
};

use futures::{stream, StreamExt};
use miette::Result;
use tokio::sync::Semaphore;
use tracing::{debug, error, info, trace, warn};

use crate::{
    cluster_key::{ClusterKey, Tag, TagType},
    config::CONFIG,
    dao::HostDao,
    host_cache::{messages::*, store, *},
    models::{CoreSize, Host},
};

#[derive(Clone)]
pub struct HostCacheService {
    host_dao: Arc<HostDao>,
    cluster_index: Arc<HashMap<ClusterKey, HostCache>>,
    reserved_hosts: Arc<HashMap<HostId, HostReservation>>,
    cache_hit: Arc<AtomicU64>,
    cache_miss: Arc<AtomicU64>,
    concurrency_semaphore: Arc<Semaphore>,
    db_circuit: Arc<DbCircuitBreaker>,
}

/// Circuit breaker around host-cache DB queries.
///
/// A transient query failure (network blip, statement timeout) trips the
/// breaker for an exponentially growing window so concurrent callers fail
/// fast instead of all hitting the DB. On success the breaker resets.
/// After `failure_threshold` consecutive failures the scheduler exits with
/// status 1 — the orchestration layer (k8s, systemd) handles the restart.
pub(super) struct DbCircuitBreaker {
    consecutive_failures: AtomicU32,
    open_until: Mutex<Option<Instant>>,
}

impl DbCircuitBreaker {
    fn new() -> Self {
        Self {
            consecutive_failures: AtomicU32::new(0),
            open_until: Mutex::new(None),
        }
    }

    /// Returns `Some(remaining)` if the breaker is currently open; the caller
    /// should short-circuit. Returns `None` if it's safe to proceed.
    fn check_open(&self) -> Option<Duration> {
        let guard = self.open_until.lock().unwrap_or_else(|p| p.into_inner());
        match *guard {
            Some(until) => {
                let now = Instant::now();
                if until > now {
                    Some(until - now)
                } else {
                    None
                }
            }
            None => None,
        }
    }

    fn record_success(&self) {
        self.consecutive_failures
            .store(0, atomic::Ordering::Relaxed);
        *self
            .open_until
            .lock()
            .unwrap_or_else(|p| p.into_inner()) = None;
    }

    /// Records a failure and opens the breaker for an exponential backoff.
    /// Returns `true` when the consecutive-failure threshold has been reached
    /// and the caller should escalate to a clean process exit.
    fn record_failure(&self) -> bool {
        let cfg = &CONFIG.host_cache.db_circuit_breaker;
        let count = self
            .consecutive_failures
            .fetch_add(1, atomic::Ordering::Relaxed)
            + 1;
        if count >= cfg.failure_threshold {
            return true;
        }
        // Exponential backoff (capped). Clamp the shift so the multiplier
        // can't overflow u64 even on huge failure counts.
        let shift = count.min(20).saturating_sub(1);
        let multiplier = 1u64.checked_shl(shift).unwrap_or(u64::MAX);
        let base_ms = cfg.base_backoff.as_millis() as u64;
        let backoff_ms = base_ms.saturating_mul(multiplier);
        let backoff = Duration::from_millis(backoff_ms).min(cfg.max_backoff);
        *self
            .open_until
            .lock()
            .unwrap_or_else(|p| p.into_inner()) = Some(Instant::now() + backoff);
        false
    }
}

/// Reservation guard preventing a host from being booked twice while it's
/// checked out. The primary lifecycle is explicit: `check_out` reserves and
/// `check_in` / `Invalidate` releases. [`expired`](Self::expired) is only a
/// safety net for leaked reservations (e.g. a task panics between check-out
/// and check-in). The TTL is configurable via
/// [`HostCacheConfig::host_reservation_safety_ttl`] and should be larger than
/// the longest plausible dispatch so a slow RQD call cannot accidentally
/// release the reservation mid-flight.
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
        self.reserved_time.elapsed().unwrap_or_default()
            > CONFIG.host_cache.host_reservation_safety_ttl
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
            cores,
            memory,
            validation,
        } = msg;

        let service = self.clone();

        Box::pin(
            async move {
                let out = service
                    .check_out(facility_id, show_id, tags, cores, memory, validation)
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
            db_circuit: Arc::new(DbCircuitBreaker::new()),
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
        cores: CoreSize,
        memory: ByteSize,
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
                        cached_group
                            // Checkout host from a group
                            .check_out(cores, memory, validation)
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
                        .check_out(cores, memory, validation)
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
            // Make sure tags are evaluated in this order:
            // MANUAL -> HOSTNAME -> HARDWARE -> ALLOC
            .sorted_by(|l, r| match (&l.tag.ttype, &r.tag.ttype) {
                (TagType::Alloc, TagType::Alloc)
                | (TagType::HostName, TagType::HostName)
                | (TagType::Hardware, TagType::Hardware)
                | (TagType::Manual, TagType::Manual) => Ordering::Equal,
                (TagType::Manual, _) => Ordering::Less,
                (TagType::HostName, _) => Ordering::Less,
                (TagType::Hardware, _) => Ordering::Less,
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
        // If a recent failure tripped the breaker, fail fast without hitting
        // the DB. Callers (matcher) treat this as "no candidates available"
        // and skip the current layer cleanly.
        if let Some(remaining) = self.db_circuit.check_open() {
            debug!(
                "Host cache circuit open for {:?} more — short-circuiting fetch",
                remaining
            );
            return Err(miette::miette!(
                "host cache DB circuit open (retry in {:?})",
                remaining
            ));
        }

        let _permit = self
            .concurrency_semaphore
            .acquire()
            .await
            .into_diagnostic()?;

        let tag = key.tag.to_string();
        let hosts = match self
            .host_dao
            .fetch_hosts_by_show_facility_tag(key.show_id, key.facility_id, &tag)
            .await
        {
            Ok(hosts) => {
                self.db_circuit.record_success();
                hosts
            }
            Err(err) => {
                let escalate = self.db_circuit.record_failure();
                if escalate {
                    error!(
                        "Host cache DB query failed past circuit-breaker threshold. \
                         Exiting so the orchestrator can restart the scheduler. Last error: {}",
                        err
                    );
                    // Clean exit (no panic backtrace). The orchestration layer
                    // (k8s, systemd, etc.) handles the restart.
                    std::process::exit(1);
                }
                warn!(
                    "Host cache DB query failed (transient, circuit will back off): {}",
                    err
                );
                return Err(err).into_diagnostic();
            }
        };

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn breaker_closed_by_default() {
        let cb = DbCircuitBreaker::new();
        assert!(cb.check_open().is_none());
    }

    #[test]
    fn breaker_opens_after_failure_and_closes_after_success() {
        let cb = DbCircuitBreaker::new();

        let escalate = cb.record_failure();
        assert!(!escalate, "single failure shouldn't escalate");
        assert!(
            cb.check_open().is_some(),
            "breaker should open after a failure"
        );

        cb.record_success();
        assert!(cb.check_open().is_none(), "success should reset breaker");
    }

    #[test]
    fn breaker_escalates_after_threshold() {
        let cb = DbCircuitBreaker::new();
        let threshold = CONFIG.host_cache.db_circuit_breaker.failure_threshold;
        // Trip up to (threshold - 1) without escalating, then the next call escalates.
        for _ in 0..threshold - 1 {
            assert!(!cb.record_failure());
        }
        assert!(
            cb.record_failure(),
            "Nth consecutive failure should signal escalation"
        );
    }
}
