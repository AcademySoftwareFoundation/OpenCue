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
    collections::{BTreeMap, HashMap, HashSet},
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

/// Sentinel B-tree index key for slot-based hosts. Slot hosts are indexed
/// independently of their idle cores/memory (which are ignored for slot
/// scheduling) so a slot host can never slide out of the search range while it
/// still has free slots. Slot-layer checkouts query this exact key, so they only
/// scan slot hosts; regular checkouts may also visit this bucket, but the
/// placement gate rejects the pairing mismatch.
const SLOT_CORE_KEY: CoreKey = u32::MAX;
const SLOT_MEMORY_KEY: MemoryKey = u64::MAX;

/// A B-Tree of Hosts ordered by memory
pub type MemoryBTree = BTreeMap<MemoryKey, HashSet<HostId>>;

/// Signature shared by every host-booking gate. Returns `Some(score)` when the
/// host is a valid candidate (lower scores rank better for Epvm); `None` when
/// the host fails validation or floor checks. Fn pointer instead of a closure
/// so the actor's `CheckOut` message stays non-generic.
pub type Gate = fn(&Host, &LayerProfile) -> Option<f64>;

/// One Phase-1 candidate captured by the Epvm scan: the CAS witness
/// (`expected_last_updated`) and the score that determines commit order in
/// Phase 3.
struct ScoredCandidate {
    host_id: Uuid,
    expected_last_updated: chrono::DateTime<chrono::Utc>,
    score: f64,
}

/// Dual index of hosts: a B-tree keyed by (cores, memory) buckets for ordered
/// scans, plus a reverse map recording each host's current bucket.
///
/// The reverse map keeps the B-tree consistent when a host is re-indexed with
/// different idle resources (e.g. by the periodic database refresh): without
/// it, the host would be inserted at its new bucket while the entry at the old
/// bucket lingered forever, growing the index unboundedly and degrading scan
/// order.
#[derive(Default)]
struct HostIndex {
    by_resources: BTreeMap<CoreKey, MemoryBTree>,
    locations: HashMap<HostId, (CoreKey, MemoryKey)>,
}

impl HostIndex {
    /// Inserts a host at the bucket for (core_key, memory_key), moving it from
    /// its previous bucket if it was already indexed elsewhere.
    fn upsert(&mut self, host_id: HostId, core_key: CoreKey, memory_key: MemoryKey) {
        if let Some(old_location) = self.locations.insert(host_id, (core_key, memory_key)) {
            if old_location != (core_key, memory_key) {
                self.remove_from_bucket(&host_id, old_location.0, old_location.1);
            }
        }
        self.by_resources
            .entry(core_key)
            .or_default()
            .entry(memory_key)
            .or_default()
            .insert(host_id);
    }

    /// Removes a host from the index, pruning buckets left empty.
    fn remove(&mut self, host_id: &HostId) {
        if let Some((core_key, memory_key)) = self.locations.remove(host_id) {
            self.remove_from_bucket(host_id, core_key, memory_key);
        }
    }

    fn remove_from_bucket(&mut self, host_id: &HostId, core_key: CoreKey, memory_key: MemoryKey) {
        if let Some(by_memory) = self.by_resources.get_mut(&core_key) {
            if let Some(hosts) = by_memory.get_mut(&memory_key) {
                hosts.remove(host_id);
                if hosts.is_empty() {
                    by_memory.remove(&memory_key);
                }
            }
            if by_memory.is_empty() {
                self.by_resources.remove(&core_key);
            }
        }
    }
}

pub struct HostCache {
    /// Index of hosts ordered by their available resources
    hosts_index: RwLock<HostIndex>,
    /// If a cache stops being queried for a certain amount of time, stop keeping it up to date
    last_queried: RwLock<SystemTime>,
    /// Marks if the data on this cache have expired
    last_fetched: RwLock<Option<SystemTime>>,
    strategy: HostBookingStrategy,
}

impl Default for HostCache {
    fn default() -> Self {
        HostCache {
            hosts_index: RwLock::new(HostIndex::default()),
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
        // Slot layers query the fixed slot sentinel bucket; regular layers query
        // by their cores/memory floor.
        let (core_key, memory_key) = if profile.slots_required > 0 {
            (SLOT_CORE_KEY, SLOT_MEMORY_KEY)
        } else {
            (cores.value() as u32, Self::gen_memory_key(memory))
        };

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
                        Box::new(host_index_lock.by_resources.range(core_key..).rev())
                    } else {
                        Box::new(host_index_lock.by_resources.range(core_key..))
                    };

                iter.find_map(|(_, hosts_by_memory)| {
                    let find_fn = |(_, hosts): (&u64, &HashSet<Uuid>)| {
                        hosts.iter().find_map(|host_id| {
                            HOST_STORE.get(host_id).and_then(|host| {
                                if host_validation(&host) {
                                    Some((*host_id, host.last_updated))
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
            if let Some((host_id, expected_last_updated)) = candidate_info {
                // Atomic check-and-remove from HOST_STORE
                // Ensure host is still valid when it's time to remove it
                match HOST_STORE.atomic_remove_if_valid(
                    &host_id,
                    expected_last_updated,
                    host_validation,
                ) {
                    Ok(Some(removed_host)) => {
                        // Successfully removed from store, now remove from index
                        self.hosts_index
                            .write()
                            .unwrap_or_else(|p| p.into_inner())
                            .remove(&host_id);

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
    /// Under contention every Phase-3 commit can lose its CAS to a concurrent
    /// checkout. In that case we re-scan (up to `EPVM_INNER_RETRIES` times)
    /// with the just-busted host ids excluded so the re-scan doesn't pick the
    /// same losers again — mirrors the Saturation path's `failed_candidates`
    /// retry. If retries are exhausted, returns `None` and the matcher's outer
    /// retry loop re-enumerates from scratch.
    fn remove_host_best(
        &self,
        cores: CoreSize,
        memory: ByteSize,
        profile: &LayerProfile,
        gate: Gate,
        reserved_check: &impl Fn(&Host) -> bool,
        max_candidates: usize,
    ) -> Option<Host> {
        const EPVM_INNER_RETRIES: usize = 3;

        // Slot layers query the fixed slot sentinel bucket; regular layers query
        // by their cores/memory floor.
        let (core_key, memory_key) = if profile.slots_required > 0 {
            (SLOT_CORE_KEY, SLOT_MEMORY_KEY)
        } else {
            (cores.value() as u32, Self::gen_memory_key(memory))
        };

        // Phase 3 CAS failures within this call. Any host_id added here is
        // skipped by subsequent re-scans so we don't burn retries scoring and
        // re-failing the same losing candidates.
        let mut failed_candidates: HashSet<Uuid> = HashSet::new();

        // Phase 3 validation: re-check the gate (atomic_remove_if_valid
        // CAS-guards last_updated, so a successful commit means the host
        // snapshot is identical to what we scored).
        let host_validation = |host: &Host| gate(host, profile).is_some() && reserved_check(host);

        for _ in 0..EPVM_INNER_RETRIES {
            // Phase 1 + 2: scan and score under the index read lock. Memory
            // floor is enforced by the `memory_key..` range; cores floor by
            // `core_key..`. Saturated-first iteration on both dims so
            // candidates are visited in best-first order until `max_candidates`
            // is hit. Hosts in `failed_candidates` (CAS-busted earlier in this
            // call) are skipped here.
            let mut scored: Vec<ScoredCandidate> = {
                let host_index_lock = self.hosts_index.read().unwrap_or_else(|p| p.into_inner());
                let mut acc = Vec::with_capacity(max_candidates.min(64));

                'outer: for (_, hosts_by_memory) in host_index_lock.by_resources.range(core_key..) {
                    for (_, hosts) in hosts_by_memory.range(memory_key..) {
                        for host_id in hosts.iter() {
                            if failed_candidates.contains(host_id) {
                                continue;
                            }
                            if let Some(host) = HOST_STORE.get(host_id) {
                                if !reserved_check(&host) {
                                    continue;
                                }
                                if let Some(score) = gate(&host, profile) {
                                    acc.push(ScoredCandidate {
                                        host_id: *host_id,
                                        expected_last_updated: host.last_updated,
                                        score,
                                    });
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

            if scored.is_empty() {
                return None;
            }

            // Sort ascending: lowest stranding wins.
            scored.sort_by(|a, b| {
                a.score
                    .partial_cmp(&b.score)
                    .unwrap_or(std::cmp::Ordering::Equal)
            });

            // Phase 3: try commits in score order. Within this attempt the
            // `for ... continue` already skips past CAS failures; the
            // failed_candidates set protects the *next* attempt's re-scan from
            // re-picking the same losers.
            for candidate in scored {
                match HOST_STORE.atomic_remove_if_valid(
                    &candidate.host_id,
                    candidate.expected_last_updated,
                    host_validation,
                ) {
                    Ok(Some(removed_host)) => {
                        self.hosts_index
                            .write()
                            .unwrap_or_else(|p| p.into_inner())
                            .remove(&candidate.host_id);

                        metrics::observe_placement_score_chosen(candidate.score);
                        return Some(removed_host);
                    }
                    Ok(None) | Err(()) => {
                        failed_candidates.insert(candidate.host_id);
                        continue;
                    }
                }
            }
        }

        // Fell through every retry attempt without committing — every scan
        // had candidates but every CAS lost. The `scored.is_empty()` early
        // return above filters out the no-candidate case, so this is purely
        // a contention signal.
        metrics::increment_placement_inner_retries_exhausted();
        None
    }

    /// Returns a host to the cache after use.
    pub fn check_in(&self, host: Host, authoritative: bool) {
        let host_id = host.id;

        // Update the data_store with new version
        let last_host_version = HOST_STORE.insert(host, authoritative);

        // Slot hosts are indexed at a fixed sentinel key, decoupled from their
        // idle cores/memory, so they stay findable while free slots remain.
        let (core_key, memory_key) = if last_host_version.is_slot_host() {
            (SLOT_CORE_KEY, SLOT_MEMORY_KEY)
        } else {
            (
                last_host_version.idle_cores.value() as CoreKey,
                Self::gen_memory_key(last_host_version.idle_memory),
            )
        };

        // Insert at the new location, removing any entry left at the host's
        // previous bucket
        self.hosts_index
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .upsert(host_id, core_key, memory_key);
    }

    /// Removes index entries for hosts absent from `live_ids`.
    ///
    /// Called right after a database refresh to drop hosts the query no longer
    /// returns (newly locked, down, re-tagged, or unsubscribed) so the group's
    /// candidate set stays authoritative instead of merging stale members on
    /// top of fresh ones. Hosts currently checked out are already absent from
    /// the index, so in-flight dispatches are never disturbed.
    ///
    /// Returns the number of entries removed.
    pub(super) fn prune_absent(&self, live_ids: &HashSet<HostId>) -> usize {
        let mut host_index = self
            .hosts_index
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        let absent: Vec<HostId> = host_index
            .locations
            .keys()
            .filter(|host_id| !live_ids.contains(*host_id))
            .copied()
            .collect();
        for host_id in &absent {
            host_index.remove(host_id);
        }
        absent.len()
    }

    /// Removes index entries whose hosts are no longer present in the store
    /// (e.g. removed by staleness cleanup while still referenced here).
    ///
    /// Returns the number of entries removed. Called periodically by the cache
    /// service so indexes don't accumulate references to dead hosts.
    pub(super) fn sweep_dead_entries(&self, is_live: impl Fn(&HostId) -> bool) -> usize {
        let mut host_index = self
            .hosts_index
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        let dead: Vec<HostId> = host_index
            .locations
            .keys()
            .filter(|host_id| !is_live(host_id))
            .copied()
            .collect();
        for host_id in &dead {
            host_index.remove(host_id);
        }
        dead.len()
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
            concurrent_slots_limit: None,
            running_slots_count: 0,
        }
    }

    fn test_profile(cores_min: i32, mem_min: ByteSize) -> LayerProfile {
        LayerProfile {
            cores_min: CoreSize(cores_min),
            mem_min,
            gpus_min: 0,
            gpu_mem_min: ByteSize::gb(0),
            slots_required: 0,
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
        assert!(hosts_index.by_resources.is_empty());
        assert!(hosts_index.locations.is_empty());
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
        assert!(!hosts_index.by_resources.is_empty());
        assert!(hosts_index.locations.contains_key(&host_id));
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
    fn test_checkin_reindexes_host_without_leaving_ghost_entry() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();

        // Insert at one bucket, then re-insert (as the periodic refresh does)
        // with different idle resources. The old bucket entry must be removed.
        let host_before = create_test_host(host_id, 16, ByteSize::gb(32));
        cache.check_in(host_before, false);
        let mut host_after = create_test_host(host_id, 2, ByteSize::gb(4));
        host_after.last_updated = Utc::now() + chrono::Duration::seconds(1);
        cache.check_in(host_after, false);

        let hosts_index = cache.hosts_index.read().unwrap();
        let occurrences: usize = hosts_index
            .by_resources
            .values()
            .flat_map(|by_memory| by_memory.values())
            .filter(|hosts| hosts.contains(&host_id))
            .count();
        assert_eq!(
            occurrences, 1,
            "host should be indexed in exactly one bucket"
        );
        assert_eq!(
            hosts_index.locations.get(&host_id),
            Some(&(2, HostCache::gen_memory_key(ByteSize::gb(4))))
        );
        drop(hosts_index);

        // Cleanup global store state for other tests
        let _ = HOST_STORE.remove(&host_id);
        cache.sweep_dead_entries(|id| HOST_STORE.contains(id));
        assert!(cache.hosts_index.read().unwrap().locations.is_empty());
    }

    #[test]
    fn test_prune_absent_removes_hosts_missing_from_fresh_query() {
        let cache = HostCache::default();
        let kept_id = Uuid::new_v4();
        let dropped_id = Uuid::new_v4();

        cache.check_in(create_test_host(kept_id, 8, ByteSize::gb(16)), false);
        cache.check_in(create_test_host(dropped_id, 4, ByteSize::gb(8)), false);

        // Simulate a refresh whose fresh query no longer returns `dropped_id`
        // (e.g. it was just locked). Only `kept_id` is live.
        let live_ids = HashSet::from([kept_id]);
        let removed = cache.prune_absent(&live_ids);

        assert_eq!(removed, 1, "exactly one absent host should be pruned");

        let hosts_index = cache.hosts_index.read().unwrap();
        assert!(
            hosts_index.locations.contains_key(&kept_id),
            "live host must remain indexed"
        );
        assert!(
            !hosts_index.locations.contains_key(&dropped_id),
            "host absent from the fresh query must be pruned"
        );
        // The dropped host's bucket should be gone entirely, not left empty.
        let still_referenced = hosts_index
            .by_resources
            .values()
            .flat_map(|by_memory| by_memory.values())
            .any(|hosts| hosts.contains(&dropped_id));
        assert!(
            !still_referenced,
            "pruned host must not linger in any bucket"
        );
        drop(hosts_index);

        // A second prune with the same live set is a no-op.
        assert_eq!(cache.prune_absent(&live_ids), 0);

        // Cleanup global store state for other tests
        let _ = HOST_STORE.remove(&kept_id);
        let _ = HOST_STORE.remove(&dropped_id);
        cache.sweep_dead_entries(|id| HOST_STORE.contains(id));
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
            hosts_index: RwLock::new(HostIndex::default()),
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

        // Place each host in its own B-tree bucket so the scan order is
        // deterministic: ascending (core_key, memory_key). With cap=2 only
        // the first two buckets are visited; the third host is never scored
        // even though its id_byte gives it the lowest (best) score.
        //
        // Bucket A: ( 2 cores,  2GB) — visited 1st — id_byte 0x42 (worst)
        // Bucket B: ( 4 cores,  4GB) — visited 2nd — id_byte 0x21 (medium)
        // Bucket C: ( 8 cores,  8GB) — NEVER visited under cap=2 — id_byte 0x07 (best)
        //
        // UUIDs avoid the 0x05/0x10/0x20 bytes used by `epvm_picks_lowest_score`
        // — the global HOST_STORE leaks state across tests, and reusing those
        // ids causes the prior test's host resources to mask this test's
        // bucket assignments.
        let id_a = Uuid::from_bytes([0x42; 16]);
        let id_b = Uuid::from_bytes([0x21; 16]);
        let id_c = Uuid::from_bytes([0x07; 16]);

        cache.check_in(create_test_host(id_a, 2, ByteSize::gb(2)), false);
        cache.check_in(create_test_host(id_b, 4, ByteSize::gb(4)), false);
        cache.check_in(create_test_host(id_c, 8, ByteSize::gb(8)), false);

        let profile = test_profile(2, ByteSize::gb(2));
        let chosen = cache
            .check_out(
                CoreSize(2),
                ByteSize::gb(2),
                &profile,
                id_byte_gate,
                no_reservation_check,
            )
            .expect("expected a checkout");

        // With the cap enforced: id_c is never scored, so the winner is the
        // lowest of {id_a, id_b}, which is id_b (0x10 < 0x20).
        //
        // Without the cap (regression): id_c WOULD be scored and would win
        // since 0x05 is the lowest. So an assertion that the chosen host is
        // id_b actively verifies the cap is enforced.
        assert_eq!(
            chosen.id, id_b,
            "expected id_b to win under cap=2 (id_c should not have been scored)"
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
