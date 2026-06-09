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

/// A cache of hosts organized in B-trees to speed up searching and traversing hosts in order.
///
/// Host are queried by their number of available cores and available memory. To speed up this
/// search, they are stored in groups organized as the example bellow:
///
/// * 2-cores:
///   - <= 2GB
///   - > 2GB <= 4GB
///   - > 4GB <= 6GB
///   - > 6GB <= 8GB
/// * 4-cores:
///   - <= 2GB
///   - > 2GB <= 4GB
///   - > 4GB <= 6GB
///   - > 6GB <= 8GB
/// * 5-cores:
///   - <= 2GB
///   - > 2GB <= 4GB
///   - > 4GB <= 6GB
///   - > 6GB <= 8GB
///
/// ...
use std::{
    cell::RefCell,
    collections::{BTreeMap, HashSet},
    sync::RwLock,
    time::{Duration, SystemTime},
};

use bytesize::ByteSize;
use miette::Result;
use uuid::Uuid;

use crate::{
    config::{HostBookingStrategy, CONFIG},
    host_cache::{store::HOST_STORE, HostCacheError, HostId},
    metrics,
    models::{CoreSize, Host},
    pipeline::placement::LayerProfile,
};

type CoreKey = u32;
type MemoryKey = u64;

/// A B-Tree of Hosts ordered by memory
pub type MemoryBTree = BTreeMap<MemoryKey, HashSet<HostId>>;

/// Signature shared by every host-booking gate. Returns `Some(score)` when the
/// host is a valid candidate (lower scores rank better for Epvm); `None` when
/// the host fails validation or floor checks. Fn pointer instead of a closure
/// so the actor's `CheckOut` message stays non-generic.
pub type Gate = fn(&Host, &LayerProfile) -> Option<f64>;

pub struct HostCache {
    /// B-Tree of host groups ordered by their number of available cores
    hosts_index: RwLock<BTreeMap<CoreKey, MemoryBTree>>,
    /// If a cache stops being queried for a certain amount of time, stop keeping it up to date
    last_queried: RwLock<SystemTime>,
    /// Marks if the data on this cache have expired
    last_fetched: RwLock<Option<SystemTime>>,
    strategy: HostBookingStrategy,
}

impl Default for HostCache {
    fn default() -> Self {
        HostCache {
            hosts_index: RwLock::new(BTreeMap::new()),
            last_queried: RwLock::new(SystemTime::now()),
            last_fetched: RwLock::new(None),
            strategy: CONFIG.queue.host_booking_strategy,
        }
    }
}

impl HostCache {
    /// Updates the last queried timestamp to prevent cache expiration.
    ///
    /// Called whenever the cache is accessed to track activity and prevent
    /// idle timeout expiration.
    fn ping_query(&self) {
        let mut lock = self
            .last_queried
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        *lock = SystemTime::now();
    }

    /// Updates the last fetched timestamp to mark cache data as fresh.
    ///
    /// Called after fetching new data from the database to mark when the
    /// cache was last refreshed.
    pub fn ping_fetch(&self) {
        let mut lock = self
            .last_fetched
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        *lock = Some(SystemTime::now());
    }

    /// Checks if the cache data has expired and needs refreshing.
    ///
    /// Cache expires after the configured group_idle_timeout period has elapsed
    /// since the last fetch.
    ///
    /// # Returns
    ///
    /// * `bool` - True if cache data has expired
    pub fn expired(&self) -> bool {
        let lock = self
            .last_fetched
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        matches!(*lock,
            Some(last_fetched)
                if last_fetched.elapsed().unwrap_or(Duration::from_secs(1))
                > CONFIG.host_cache.group_idle_timeout)
    }

    /// Checks if the cache has been idle for too long without queries.
    ///
    /// Used to determine if a cache group should be removed to save memory.
    ///
    /// # Returns
    ///
    /// * `bool` - True if cache hasn't been queried within the idle timeout period
    pub fn is_idle(&self) -> bool {
        self.last_queried
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .elapsed()
            .unwrap_or(Duration::from_secs(1))
            > CONFIG.host_cache.group_idle_timeout
    }

    /// Checks out a host from the cache that matches the gate's requirements.
    ///
    /// Dispatches to either the Saturation (first-fit) or Epvm (lowest-score)
    /// path based on the configured `strategy`. The B-tree index is queried
    /// by `(cores, memory)`; floor checks on other dimensions (GPUs, GPU mem)
    /// live inside the `gate`.
    ///
    /// # Arguments
    ///
    /// * `cores`, `memory` — minimum range hints for the B-tree query
    /// * `profile` — layer placement context (caps, weights, floors)
    /// * `gate` — `Some(score)` when valid, `None` to reject
    /// * `reserved_check` — actor-supplied availability test (true when not
    ///   reserved by another in-flight checkout)
    pub fn check_out(
        &self,
        cores: CoreSize,
        memory: ByteSize,
        profile: &LayerProfile,
        gate: Gate,
        reserved_check: impl Fn(&Host) -> bool,
    ) -> Result<Host, HostCacheError> {
        self.ping_query();

        let host = match self.strategy {
            HostBookingStrategy::Saturation {
                core_saturation,
                memory_saturation,
            } => self.remove_host_first_fit(
                cores,
                memory,
                profile,
                gate,
                &reserved_check,
                core_saturation,
                memory_saturation,
            ),
            HostBookingStrategy::Epvm { max_candidates, .. } => self.remove_host_best(
                cores,
                memory,
                profile,
                gate,
                &reserved_check,
                max_candidates,
            ),
        };

        host.ok_or(HostCacheError::NoCandidateAvailable)
    }

    /// Saturation strategy: scan the B-tree in the configured direction and
    /// take the first valid host. Retries up to 5 times when CAS races lose
    /// to concurrent checkouts.
    #[allow(clippy::too_many_arguments)]
    fn remove_host_first_fit(
        &self,
        cores: CoreSize,
        memory: ByteSize,
        profile: &LayerProfile,
        gate: Gate,
        reserved_check: &impl Fn(&Host) -> bool,
        core_saturation: bool,
        memory_saturation: bool,
    ) -> Option<Host> {
        let core_key = cores.value() as u32;
        let memory_key = Self::gen_memory_key(memory);

        let failed_candidates: RefCell<Vec<Uuid>> = RefCell::new(Vec::new());
        let host_validation = |host: &Host| {
            gate(host, profile).is_some()
                && reserved_check(host)
                && !failed_candidates.borrow().contains(&host.id)
        };

        let mut attempts = 5;
        loop {
            // Step 1: Find a candidate host in the index
            let candidate_info = {
                let host_index_lock = self.hosts_index.read().unwrap_or_else(|p| p.into_inner());
                let mut iter: Box<dyn Iterator<Item = (&CoreKey, &MemoryBTree)>> =
                    if !core_saturation {
                        // Reverse order to find hosts with max amount of cores available
                        Box::new(host_index_lock.range(core_key..).rev())
                    } else {
                        Box::new(host_index_lock.range(core_key..))
                    };

                iter.find_map(|(by_core_key, hosts_by_memory)| {
                    let find_fn = |(by_memory_key, hosts): (&u64, &HashSet<Uuid>)| {
                        hosts.iter().find_map(|host_id| {
                            HOST_STORE.get(host_id).and_then(|host| {
                                if host_validation(&host) {
                                    Some((
                                        *by_core_key,
                                        *by_memory_key,
                                        *host_id,
                                        host.last_updated,
                                    ))
                                } else {
                                    None
                                }
                            })
                        })
                    };

                    if memory_saturation {
                        hosts_by_memory.range(memory_key..).find_map(find_fn)
                    } else {
                        // Search for hosts with the most amount of memory available
                        hosts_by_memory.range(memory_key..).rev().find_map(find_fn)
                    }
                })
            };

            // Step 2: Attempt atomic removal if we found a candidate
            if let Some((by_core_key, by_memory_key, host_id, expected_last_updated)) =
                candidate_info
            {
                // Atomic check-and-remove from HOST_STORE
                // Ensure host is still valid when it's time to remove it
                match HOST_STORE.atomic_remove_if_valid(
                    &host_id,
                    expected_last_updated,
                    host_validation,
                ) {
                    Ok(Some(removed_host)) => {
                        // Successfully removed from store, now remove from index
                        let mut host_index_lock =
                            self.hosts_index.write().unwrap_or_else(|p| p.into_inner());

                        // Remove from hosts_by_core_and_memory index
                        host_index_lock
                            .get_mut(&by_core_key)
                            .and_then(|hosts_by_memory| hosts_by_memory.get_mut(&by_memory_key))
                            .map(|hosts| hosts.remove(&host_id));

                        return Some(removed_host);
                    }
                    Ok(None) | Err(()) => {
                        // Host was removed by another thread. Try another candidate
                        attempts -= 1;
                        // Mark the failed candidate to avoid retrying it again.
                        failed_candidates.borrow_mut().push(host_id);
                        if attempts <= 0 {
                            break;
                        }
                    }
                }
            } else {
                break;
            }
        }

        None
    }

    /// Epvm strategy: snapshot up to `max_candidates` hosts (saturated-first
    /// iteration so the best-likely candidates are scanned when the cap
    /// engages), score them via the gate, and try `atomic_remove_if_valid`
    /// in ascending score order. First successful CAS wins.
    ///
    /// By design, this is a single-pass operation: if every Phase-3
    /// commit fails its CAS, returns `None` and the matcher's outer retry
    /// loop re-enumerates on the next iteration.
    fn remove_host_best(
        &self,
        cores: CoreSize,
        memory: ByteSize,
        profile: &LayerProfile,
        gate: Gate,
        reserved_check: &impl Fn(&Host) -> bool,
        max_candidates: usize,
    ) -> Option<Host> {
        let core_key = cores.value() as u32;
        let memory_key = Self::gen_memory_key(memory);

        // Phase 1 + 2: scan and score under the index read lock. Memory floor
        // is enforced by the `memory_key..` range; cores floor by `core_key..`.
        // Saturated-first iteration on both dims so candidates are visited in
        // best-first order until `max_candidates` is hit.
        let mut scored: Vec<(CoreKey, MemoryKey, Uuid, chrono::DateTime<chrono::Utc>, f64)> = {
            let host_index_lock = self.hosts_index.read().unwrap_or_else(|p| p.into_inner());
            let mut acc = Vec::with_capacity(max_candidates.min(64));

            'outer: for (by_core_key, hosts_by_memory) in host_index_lock.range(core_key..) {
                for (by_memory_key, hosts) in hosts_by_memory.range(memory_key..) {
                    for host_id in hosts.iter() {
                        if let Some(host) = HOST_STORE.get(host_id) {
                            if !reserved_check(&host) {
                                continue;
                            }
                            if let Some(score) = gate(&host, profile) {
                                acc.push((
                                    *by_core_key,
                                    *by_memory_key,
                                    *host_id,
                                    host.last_updated,
                                    score,
                                ));
                                if acc.len() >= max_candidates {
                                    break 'outer;
                                }
                            }
                        }
                    }
                }
            }
            acc
        };

        // Sort ascending: lowest stranding wins.
        scored.sort_by(|a, b| a.4.partial_cmp(&b.4).unwrap_or(std::cmp::Ordering::Equal));

        // Phase 3: try commits in score order. The validation closure must
        // re-check the gate because the host may have changed between Phase 1
        // and Phase 3 (atomic_remove_if_valid already CAS-guards last_updated,
        // so a successful commit means we have the same snapshot).
        let host_validation = |host: &Host| gate(host, profile).is_some() && reserved_check(host);

        for (by_core_key, by_memory_key, host_id, expected_last_updated, score) in scored {
            match HOST_STORE.atomic_remove_if_valid(
                &host_id,
                expected_last_updated,
                host_validation,
            ) {
                Ok(Some(removed_host)) => {
                    let mut host_index_lock =
                        self.hosts_index.write().unwrap_or_else(|p| p.into_inner());

                    host_index_lock
                        .get_mut(&by_core_key)
                        .and_then(|hosts_by_memory| hosts_by_memory.get_mut(&by_memory_key))
                        .map(|hosts| hosts.remove(&host_id));

                    metrics::observe_placement_score_chosen(score);
                    return Some(removed_host);
                }
                Ok(None) | Err(()) => continue,
            }
        }

        None
    }

    /// Returns a host to the cache after use.
    pub fn check_in(&self, host: Host, authoritative: bool) {
        let host_id = host.id;

        // Update the data_store with new version
        let last_host_version = HOST_STORE.insert(host, authoritative);

        let core_key = last_host_version.idle_cores.value() as CoreKey;
        let memory_key = Self::gen_memory_key(last_host_version.idle_memory);

        let mut host_index = self
            .hosts_index
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        // Insert at the new location
        host_index
            .entry(core_key)
            .or_default()
            .entry(memory_key)
            .or_default()
            .insert(host_id);
    }

    /// Generates a memory key for cache indexing by bucketing memory values.
    ///
    /// Divides memory by the configured divisor to group hosts with similar
    /// memory into the same bucket, reducing cache fragmentation.
    ///
    /// # Arguments
    ///
    /// * `memory` - Memory amount to convert to a key
    ///
    /// # Returns
    ///
    /// * `MemoryKey` - Bucketed memory key for indexing
    fn gen_memory_key(memory: ByteSize) -> MemoryKey {
        memory.as_u64() / CONFIG.host_cache.memory_key_divisor.as_u64()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ScoreWeights;
    use chrono::Utc;
    use opencue_proto::host::ThreadMode;
    use std::thread;
    use std::time::Duration;
    use tokio_test::{assert_err, assert_ok};
    use uuid::Uuid;

    fn create_test_host(id: Uuid, idle_cores: i32, idle_memory: ByteSize) -> Host {
        Host {
            id,
            name: format!("test-host-{}", id),
            str_os: Some("Linux".to_string()),
            total_cores: CoreSize(idle_cores),
            total_memory: idle_memory,
            idle_cores: CoreSize(idle_cores),
            idle_memory,
            idle_gpus: 0,
            idle_gpu_memory: ByteSize::kb(0),
            thread_mode: ThreadMode::Auto,
            alloc_available_cores: CoreSize(idle_cores),
            alloc_id: Uuid::new_v4(),
            alloc_name: "test".to_string(),
            last_updated: Utc::now(),
        }
    }

    fn test_profile(cores_min: i32, mem_min: ByteSize) -> LayerProfile {
        LayerProfile {
            cores_min: CoreSize(cores_min),
            mem_min,
            gpus_min: 0,
            gpu_mem_min: ByteSize::gb(0),
            os: None,
            threadable: true,
            job_max_cores: 0,
            show_burst: 0,
            job_cores_in_use: 0,
            show_cores_in_use: 0,
            weights: ScoreWeights::default(),
        }
    }

    /// Trivial gate: always valid, constant score 0.0. For tests that exercise
    /// the structural checkout path without scoring concerns.
    fn always_valid(_: &Host, _: &LayerProfile) -> Option<f64> {
        Some(0.0)
    }

    /// Always-reject gate. For tests that the gate's None short-circuits.
    fn always_reject(_: &Host, _: &LayerProfile) -> Option<f64> {
        None
    }

    fn no_reservation_check(_: &Host) -> bool {
        true
    }

    #[test]
    fn test_new_host_cache() {
        let cache = HostCache::default();
        let hosts_index = cache.hosts_index.read().unwrap();
        assert!(hosts_index.is_empty());
        drop(hosts_index);
        assert!(!cache.expired());
    }

    #[test]
    fn test_ping_query_updates_last_queried() {
        let cache = HostCache::default();
        let initial_time = *cache.last_queried.read().unwrap();

        thread::sleep(Duration::from_millis(1));
        cache.ping_query();

        let updated_time = *cache.last_queried.read().unwrap();
        assert!(updated_time > initial_time);
    }

    #[test]
    fn test_ping_fetch_updates_last_fetched() {
        let cache = HostCache::default();
        assert!(cache.last_fetched.read().unwrap().is_none());

        cache.ping_fetch();

        assert!(cache.last_fetched.read().unwrap().is_some());
    }

    #[test]
    fn test_expired_when_never_fetched() {
        let cache = HostCache::default();
        assert!(!cache.expired());
    }

    #[test]
    fn test_expired_when_recently_fetched() {
        let cache = HostCache::default();
        cache.ping_fetch();
        assert!(!cache.expired());
    }

    #[test]
    fn test_is_idle_when_recently_queried() {
        let cache = HostCache::default();
        cache.ping_query();
        assert!(!cache.is_idle());
    }

    #[test]
    fn test_insert_host() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host.clone(), false);

        assert!(HOST_STORE.get(&host_id).is_some());
        let hosts_index = cache.hosts_index.read().unwrap();
        assert!(!hosts_index.is_empty());
    }

    #[test]
    fn test_insert_host_updates_existing() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host1 = create_test_host(host_id, 4, ByteSize::gb(8));
        let mut host2 = create_test_host(host_id, 8, ByteSize::gb(16));
        host2.name = "updated-host".to_string();

        cache.check_in(host1, false);
        cache.check_in(host2.clone(), false);

        let stored_host = HOST_STORE.get(&host_id).unwrap();
        assert_eq!(stored_host.idle_cores.value(), 8);
        assert_eq!(stored_host.idle_memory, ByteSize::gb(16));
        assert_eq!(stored_host.name, "updated-host");
    }

    #[test]
    fn test_checkout_success() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host, false);

        let profile = test_profile(2, ByteSize::gb(4));
        let result = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile,
            always_valid,
            no_reservation_check,
        );

        let checked_out_host = assert_ok!(result);
        assert_eq!(checked_out_host.id, host_id);
        assert!(HOST_STORE.get(&host_id).is_none());
    }

    #[test]
    fn test_checkout_no_candidate_available() {
        let cache = HostCache::default();
        let profile = test_profile(4, ByteSize::gb(8));

        let result = cache.check_out(
            CoreSize(4),
            ByteSize::gb(8),
            &profile,
            always_valid,
            no_reservation_check,
        );

        assert!(result.is_err());
        assert!(matches!(result, Err(HostCacheError::NoCandidateAvailable)));
    }

    #[test]
    fn test_checkout_insufficient_cores() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 2, ByteSize::gb(8));

        cache.check_in(host, false);

        let profile = test_profile(4, ByteSize::gb(4));
        let result = cache.check_out(
            CoreSize(4),
            ByteSize::gb(4),
            &profile,
            always_valid,
            no_reservation_check,
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_insufficient_memory() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(4));

        cache.check_in(host, false);

        let profile = test_profile(2, ByteSize::gb(8));
        let result = cache.check_out(
            CoreSize(2),
            ByteSize::gb(8),
            &profile,
            always_valid,
            no_reservation_check,
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_validation_fails() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host, false);

        let profile = test_profile(2, ByteSize::gb(4));
        let result = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile,
            always_reject,
            no_reservation_check,
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_already_checked_out() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host, false);

        let profile = test_profile(2, ByteSize::gb(4));
        let result1 = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile,
            always_valid,
            no_reservation_check,
        );
        assert!(result1.is_ok());

        let result2 = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile,
            always_valid,
            no_reservation_check,
        );
        assert!(result2.is_err());
    }

    #[test]
    fn test_checkin() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host.clone(), false);

        let profile = test_profile(2, ByteSize::gb(4));
        let mut checked_host = assert_ok!(cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile,
            always_valid,
            no_reservation_check,
        ));
        assert_eq!(checked_host.idle_cores.value(), 4);

        checked_host.idle_cores = CoreSize(1);
        cache.check_in(checked_host, false);

        let profile2 = test_profile(2, ByteSize::gb(4));
        assert_err!(cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile2,
            always_valid,
            no_reservation_check,
        ));
        let profile1 = test_profile(1, ByteSize::gb(4));
        assert_ok!(cache.check_out(
            CoreSize(1),
            ByteSize::gb(4),
            &profile1,
            always_valid,
            no_reservation_check,
        ));
    }

    #[test]
    fn test_find_candidate_with_multiple_hosts() {
        let cache = HostCache::default();

        let host1_id = Uuid::new_v4();
        let host1 = create_test_host(host1_id, 2, ByteSize::gb(4));

        let host2_id = Uuid::new_v4();
        let host2 = create_test_host(host2_id, 4, ByteSize::gb(8));

        let host3_id = Uuid::new_v4();
        let host3 = create_test_host(host3_id, 8, ByteSize::gb(16));

        cache.check_in(host1, false);
        cache.check_in(host2, false);
        cache.check_in(host3, false);

        let profile = test_profile(3, ByteSize::gb(6));
        let result = cache.check_out(
            CoreSize(3),
            ByteSize::gb(6),
            &profile,
            always_valid,
            no_reservation_check,
        );
        assert!(result.is_ok());

        let chosen_host = result.unwrap();
        assert!(chosen_host.idle_cores.value() >= 3);
        assert!(chosen_host.idle_memory >= ByteSize::gb(6));
    }

    #[test]
    fn test_gen_memory_key() {
        let memory1 = ByteSize::gb(4);
        let memory2 = ByteSize::gb(8);

        let key1 = HostCache::gen_memory_key(memory1);
        let key2 = HostCache::gen_memory_key(memory2);

        assert_ne!(key1, key2);
        assert_eq!(key1, HostCache::gen_memory_key(memory1));

        assert_eq!(key1, 1);
        assert_eq!(key2, 3);
    }

    #[test]
    fn test_multiple_hosts_same_resources() {
        let cache = HostCache::default();

        let host1_id = Uuid::new_v4();
        let host1 = create_test_host(host1_id, 4, ByteSize::gb(8));

        let host2_id = Uuid::new_v4();
        let host2 = create_test_host(host2_id, 4, ByteSize::gb(8));

        cache.check_in(host1, false);
        cache.check_in(host2, false);

        let profile = test_profile(2, ByteSize::gb(4));
        let result1 = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile,
            always_valid,
            no_reservation_check,
        );
        assert!(result1.is_ok());

        let result2 = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile,
            always_valid,
            no_reservation_check,
        );
        assert!(result2.is_ok());

        assert_ne!(result1.unwrap().id, result2.unwrap().id);
    }

    // ---- Epvm K-candidate path (T2) ---------------------------------------

    /// Build a HostCache with the Epvm strategy explicitly set, bypassing
    /// the global CONFIG. Useful for testing the K-candidate path without
    /// reconfiguring the whole process.
    fn epvm_cache(max_candidates: usize) -> HostCache {
        HostCache {
            hosts_index: RwLock::new(BTreeMap::new()),
            last_queried: RwLock::new(SystemTime::now()),
            last_fetched: RwLock::new(None),
            strategy: HostBookingStrategy::Epvm {
                weights: ScoreWeights::default(),
                max_candidates,
            },
        }
    }

    /// Gate that scores by host id's first byte — deterministic ordering for
    /// tests of the K-candidate sort/pick.
    fn id_byte_gate(host: &Host, _: &LayerProfile) -> Option<f64> {
        Some(host.id.as_bytes()[0] as f64)
    }

    #[test]
    fn epvm_picks_lowest_score() {
        let cache = epvm_cache(10);

        // Three hosts with deterministic first-byte ids: 0x10, 0x20, 0x05.
        // The 0x05 host should win.
        let high_id = Uuid::from_bytes([0x10; 16]);
        let med_id = Uuid::from_bytes([0x20; 16]);
        let low_id = Uuid::from_bytes([0x05; 16]);

        cache.check_in(create_test_host(high_id, 8, ByteSize::gb(16)), false);
        cache.check_in(create_test_host(med_id, 8, ByteSize::gb(16)), false);
        cache.check_in(create_test_host(low_id, 8, ByteSize::gb(16)), false);

        let profile = test_profile(2, ByteSize::gb(4));
        let chosen = cache
            .check_out(
                CoreSize(2),
                ByteSize::gb(4),
                &profile,
                id_byte_gate,
                no_reservation_check,
            )
            .expect("expected a checkout");

        assert_eq!(chosen.id, low_id, "lowest-score host should win");
    }

    #[test]
    fn epvm_respects_max_candidates_cap() {
        let cache = epvm_cache(2);

        // Add three hosts. Cap = 2 means only the first 2 visited are scored;
        // the 3rd is never considered even if it would score lowest.
        // B-tree iterates saturated-first; with all hosts at same (cores, mem),
        // iteration order within a bucket is HashSet-arbitrary but bounded.
        let id_a = Uuid::from_bytes([0x10; 16]);
        let id_b = Uuid::from_bytes([0x20; 16]);
        let id_c = Uuid::from_bytes([0x05; 16]);

        cache.check_in(create_test_host(id_a, 8, ByteSize::gb(16)), false);
        cache.check_in(create_test_host(id_b, 8, ByteSize::gb(16)), false);
        cache.check_in(create_test_host(id_c, 8, ByteSize::gb(16)), false);

        let profile = test_profile(2, ByteSize::gb(4));
        let chosen = cache
            .check_out(
                CoreSize(2),
                ByteSize::gb(4),
                &profile,
                id_byte_gate,
                no_reservation_check,
            )
            .expect("expected a checkout");

        // With cap=2 and HashSet iteration arbitrary, the lowest score winner
        // is one of the first 2 visited — not necessarily id_c (0x05). The
        // chosen host's id MUST be one of the three checked-in ids though.
        assert!(
            chosen.id == id_a || chosen.id == id_b || chosen.id == id_c,
            "unexpected host id {}",
            chosen.id
        );
    }

    #[test]
    fn epvm_no_candidate_when_all_rejected() {
        let cache = epvm_cache(10);

        let host_id = Uuid::new_v4();
        cache.check_in(create_test_host(host_id, 8, ByteSize::gb(16)), false);

        let profile = test_profile(2, ByteSize::gb(4));
        let result = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            &profile,
            always_reject,
            no_reservation_check,
        );

        assert!(matches!(result, Err(HostCacheError::NoCandidateAvailable)));
    }

    #[test]
    fn epvm_skips_reserved_hosts() {
        let cache = epvm_cache(10);

        let reserved_id = Uuid::from_bytes([0x01; 16]);
        let free_id = Uuid::from_bytes([0xFF; 16]);

        cache.check_in(create_test_host(reserved_id, 8, ByteSize::gb(16)), false);
        cache.check_in(create_test_host(free_id, 8, ByteSize::gb(16)), false);

        let profile = test_profile(2, ByteSize::gb(4));
        // Reservation check: pretend reserved_id is unavailable. id_byte_gate
        // would normally rank reserved_id (0x01) ahead of free_id (0xFF).
        let chosen = cache
            .check_out(
                CoreSize(2),
                ByteSize::gb(4),
                &profile,
                id_byte_gate,
                |host: &Host| host.id != reserved_id,
            )
            .expect("expected a checkout");

        assert_eq!(chosen.id, free_id, "reserved host should be skipped");
    }
}
