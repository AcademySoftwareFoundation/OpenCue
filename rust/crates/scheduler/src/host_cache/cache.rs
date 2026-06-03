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
    sync::{Arc, Mutex, RwLock},
    time::{Duration, SystemTime},
};

use bytesize::ByteSize;
use miette::Result;
use uuid::Uuid;

use crate::{
    config::{HostBookingStrategy, CONFIG},
    host_cache::{store::HOST_STORE, HostCacheError, HostId},
    models::{CoreSize, Host},
};

type CoreKey = u32;
type MemoryKey = u64;

/// A B-Tree of Hosts ordered by memory
pub type MemoryBTree = BTreeMap<MemoryKey, HashSet<HostId>>;

/// Per-CoreKey bucket. Wrapped in an `Arc<Mutex>` so concurrent check-outs and
/// check-ins on disjoint core sizes don't contend with each other — the outer
/// `RwLock` only protects the (rarely changing) bucket directory.
type MemoryBucket = Arc<Mutex<MemoryBTree>>;

pub struct HostCache {
    /// Bucket directory keyed by available cores. The outer `RwLock` is read
    /// on every check-out / check-in to look up a bucket and almost never
    /// upgraded to write (only when a brand-new `CoreKey` shows up). Once a
    /// bucket Arc is obtained, the outer lock is released; the bucket's own
    /// `Mutex` guards the inner `MemoryBTree`, so different buckets are fully
    /// independent.
    hosts_index: RwLock<BTreeMap<CoreKey, MemoryBucket>>,
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

    /// Checks out the best matching host from the cache.
    ///
    /// Finds a host with sufficient resources that passes the validation function,
    /// removes it from the cache, and returns it. The host must be checked back in
    /// after use.
    ///
    /// # Arguments
    ///
    /// * `cores` - Minimum number of cores required
    /// * `memory` - Minimum memory required
    /// * `validation` - Function to validate additional host requirements
    ///
    /// # Returns
    ///
    /// * `Ok(Host)` - Successfully checked out host
    /// * `Err(HostCacheError)` - No suitable host available
    pub fn check_out<F>(
        &self,
        cores: CoreSize,
        memory: ByteSize,
        validation: F,
    ) -> Result<Host, HostCacheError>
    where
        F: Fn(&Host) -> bool,
    {
        self.ping_query();

        let host = self
            .remove_host(cores, memory, validation)
            .ok_or(HostCacheError::NoCandidateAvailable)?;

        Ok(host)
    }

    /// Removes a suitable host from the cache based on resource requirements.
    ///
    /// Searches for a host with at least the requested cores and memory that
    /// passes the validation function. Uses atomic operations with retry logic
    /// to prevent race conditions where host state changes between lookup and removal.
    ///
    /// # Arguments
    ///
    /// * `cores` - Minimum number of cores required
    /// * `memory` - Minimum memory required
    /// * `validation` - Function to validate additional requirements
    ///
    /// # Returns
    ///
    /// * `Some(Host)` - Host that meets all requirements
    /// * `None` - No suitable host found
    fn remove_host<F>(&self, cores: CoreSize, memory: ByteSize, validation: F) -> Option<Host>
    where
        F: Fn(&Host) -> bool,
    {
        let core_key = cores.value() as u32;
        let memory_key = Self::gen_memory_key(memory);

        let failed_candidates: RefCell<Vec<Uuid>> = RefCell::new(Vec::new());
        let host_validation = |host: &Host| {
            // Check caller validation
            validation(host) &&
            // Check memory and core requirements just in case
            host.idle_memory >= memory &&
            host.idle_cores >= cores &&
            // Ensure we're not retrying the same host as last attempts
            !failed_candidates.borrow().contains(&host.id)
        };

        let mut attempts = 5;
        loop {
            // Step 1: Snapshot the candidate bucket list under the outer read
            // lock — this clones a handful of Arc<Mutex<_>> handles and drops
            // the outer lock immediately, so check-ins on other buckets are
            // not blocked while we scan.
            let bucket_arcs: Vec<(CoreKey, MemoryBucket)> = {
                let outer = self.hosts_index.read().unwrap_or_else(|p| p.into_inner());
                if !self.strategy.core_saturation {
                    // Reverse order: prefer hosts with the most cores
                    outer
                        .range(core_key..)
                        .rev()
                        .map(|(&k, v)| (k, v.clone()))
                        .collect()
                } else {
                    outer
                        .range(core_key..)
                        .map(|(&k, v)| (k, v.clone()))
                        .collect()
                }
            };

            // Step 2: Scan each bucket independently. Holding only one bucket
            // mutex at a time keeps disjoint core groups concurrent.
            let candidate_info =
                bucket_arcs
                    .into_iter()
                    .find_map(|(by_core_key, bucket)| {
                        let bucket_lock = bucket.lock().unwrap_or_else(|p| p.into_inner());
                        let find_fn =
                            |(by_memory_key, hosts): (&u64, &HashSet<Uuid>)| {
                                hosts.iter().find_map(|host_id| {
                                    HOST_STORE.get(host_id).and_then(|host| {
                                        if host_validation(&host) {
                                            Some((
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
                        let inner = if self.strategy.memory_saturation {
                            bucket_lock.range(memory_key..).find_map(find_fn)
                        } else {
                            bucket_lock.range(memory_key..).rev().find_map(find_fn)
                        };
                        drop(bucket_lock);
                        inner.map(|(mk, hid, ts)| {
                            (by_core_key, mk, hid, ts, bucket.clone())
                        })
                    });

            // Step 3: Attempt atomic removal if we found a candidate
            if let Some((_by_core_key, by_memory_key, host_id, expected_last_updated, bucket)) =
                candidate_info
            {
                match HOST_STORE.atomic_remove_if_valid(
                    &host_id,
                    expected_last_updated,
                    host_validation,
                ) {
                    Ok(Some(removed_host)) => {
                        // Remove from this single bucket's index. Other buckets
                        // are untouched.
                        let mut bucket_lock =
                            bucket.lock().unwrap_or_else(|p| p.into_inner());
                        if let Some(hosts) = bucket_lock.get_mut(&by_memory_key) {
                            hosts.remove(&host_id);
                        }
                        return Some(removed_host);
                    }
                    Ok(None) | Err(()) => {
                        // Host was removed by another thread. Try another candidate
                        attempts -= 1;
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

    /// Returns a host to the cache after use.
    ///
    /// Updates the cache with the host's current resource state. If the host
    /// already exists in the cache, it's updated with the new values. The host
    /// is indexed by its current idle cores and memory for efficient lookup.
    ///
    /// This method now performs all updates atomically under a single write lock,
    /// preventing race conditions with concurrent check_out operations.
    ///
    /// # Arguments
    ///
    /// * `host` - Host to return to the cache
    pub fn check_in(&self, host: Host, authoritative: bool) {
        let host_id = host.id;

        // Update the data_store with new version
        let last_host_version = HOST_STORE.insert(host, authoritative);

        let core_key = last_host_version.idle_cores.value() as CoreKey;
        let memory_key = Self::gen_memory_key(last_host_version.idle_memory);

        // Double-checked locking: fast path takes only the outer read lock
        // and grabs an existing bucket Arc. Slow path (rare) upgrades to the
        // outer write lock only when a brand-new CoreKey appears.
        let bucket: MemoryBucket = {
            let outer = self
                .hosts_index
                .read()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            outer.get(&core_key).cloned()
        }
        .unwrap_or_else(|| {
            let mut outer = self
                .hosts_index
                .write()
                .unwrap_or_else(|poisoned| poisoned.into_inner());
            outer
                .entry(core_key)
                .or_insert_with(|| Arc::new(Mutex::new(BTreeMap::new())))
                .clone()
        });

        // Per-bucket mutex insert. Disjoint core sizes proceed in parallel.
        let mut bucket_lock = bucket.lock().unwrap_or_else(|p| p.into_inner());
        bucket_lock.entry(memory_key).or_default().insert(host_id);
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

        // The host should be updated with new resources
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

        let result = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            |_| true, // Always validate true
        );

        let checked_out_host = assert_ok!(result);
        let memory_key = HostCache::gen_memory_key(checked_out_host.idle_memory);
        let core_key = checked_out_host.idle_cores.value() as u32;

        assert_eq!(checked_out_host.id, host_id);

        assert!(HOST_STORE.get(&host_id).is_none());

        let hosts_index = cache.hosts_index.read().unwrap();
        let left_over_host = hosts_index.get(&core_key).and_then(|bucket| {
            let bucket_lock = bucket.lock().unwrap();
            bucket_lock
                .get(&memory_key)
                .and_then(|hosts| hosts.get(&checked_out_host.id))
                .copied()
        });
        assert!(left_over_host.is_none())
    }

    #[test]
    fn test_checkout_no_candidate_available() {
        let cache = HostCache::default();

        let result = cache.check_out(CoreSize(4), ByteSize::gb(8), |_| true);

        assert!(result.is_err());
        assert!(matches!(result, Err(HostCacheError::NoCandidateAvailable)));
    }

    #[test]
    fn test_checkout_insufficient_cores() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 2, ByteSize::gb(8));

        cache.check_in(host, false);

        let result = cache.check_out(
            CoreSize(4), // Request more cores than available
            ByteSize::gb(4),
            |_| true,
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_insufficient_memory() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(4));

        cache.check_in(host, false);

        let result = cache.check_out(
            CoreSize(2),
            ByteSize::gb(8), // Request more memory than available
            |_| true,
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_validation_fails() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host, false);

        let result = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            |_| false, // Always fail validation
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_already_checked_out() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host, false);

        // First checkout should succeed
        let result1 = cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result1.is_ok());

        // Second checkout should fail because host is already checked out
        let result2 = cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result2.is_err());
    }

    #[test]
    fn test_checkin() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host.clone(), false);

        // Checkout the host
        let mut checked_host = assert_ok!(cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true));
        assert_eq!(checked_host.idle_cores.value(), 4);

        // Reduce the number of cores and checkin to ensure cache is updated
        checked_host.idle_cores = CoreSize(1);

        // Check it back in
        cache.check_in(checked_host, false);
        assert_err!(cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true));
        assert_ok!(cache.check_out(CoreSize(1), ByteSize::gb(4), |_| true));
    }

    #[test]
    fn test_find_candidate_with_multiple_hosts() {
        let cache = HostCache::default();

        // Add hosts with different resources
        let host1_id = Uuid::new_v4();
        let host1 = create_test_host(host1_id, 2, ByteSize::gb(4));

        let host2_id = Uuid::new_v4();
        let host2 = create_test_host(host2_id, 4, ByteSize::gb(8));

        let host3_id = Uuid::new_v4();
        let host3 = create_test_host(host3_id, 8, ByteSize::gb(16));

        cache.check_in(host1, false);
        cache.check_in(host2, false);
        cache.check_in(host3, false);

        // Request 3 cores, 6GB - should get host2 (4 cores, 8GB) or host3 (8 cores, 16GB)
        let result = cache.check_out(CoreSize(3), ByteSize::gb(6), |_| true);
        assert!(result.is_ok());

        let chosen_host = result.unwrap();
        assert!(chosen_host.idle_cores.value() >= 3);
        assert!(chosen_host.idle_memory >= ByteSize::gb(6));
    }

    #[test]
    fn test_gen_memory_key() {
        // The memory key formula is: memory / CONFIG.host_cache.memory_key_divisor.as_u64()
        // With default 2.1GB divisor:
        // 4GB / 2.1GB = 1 (rounded down)
        // 8GB / 2.1GB = 3 (rounded down)
        let memory1 = ByteSize::gb(4); // 4GB
        let memory2 = ByteSize::gb(8); // 8GB

        let key1 = HostCache::gen_memory_key(memory1);
        let key2 = HostCache::gen_memory_key(memory2);

        // Keys should be different and deterministic
        assert_ne!(key1, key2);
        assert_eq!(key1, HostCache::gen_memory_key(memory1)); // Should be deterministic

        // With 2.1GB divisor, should get expected values
        assert_eq!(key1, 1); // 4GB / 2.1GB = ~1.9, rounded down to 1
        assert_eq!(key2, 3); // 8GB / 2.1GB = ~3.8, rounded down to 3
    }

    #[test]
    fn test_multiple_hosts_same_resources() {
        let cache = HostCache::default();

        // Add multiple hosts with same resource configuration
        let host1_id = Uuid::new_v4();
        let host1 = create_test_host(host1_id, 4, ByteSize::gb(8));

        let host2_id = Uuid::new_v4();
        let host2 = create_test_host(host2_id, 4, ByteSize::gb(8));

        cache.check_in(host1, false);
        cache.check_in(host2, false);

        // First checkout should succeed
        let result1 = cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result1.is_ok());

        // Second checkout should also succeed (different host)
        let result2 = cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result2.is_ok());

        // The hosts should be different
        assert_ne!(result1.unwrap().id, result2.unwrap().id);
    }

    /// Concurrent check-ins on disjoint core buckets must not interfere — this
    /// is the whole point of the sharded design. All N inserts complete and
    /// land in distinct buckets.
    #[test]
    fn concurrent_check_ins_on_disjoint_buckets() {
        use std::sync::Arc as StdArc;

        let cache = StdArc::new(HostCache::default());
        let mut handles = Vec::new();
        // Each thread checks in a host with a unique core count → distinct
        // bucket → no per-bucket contention.
        for cores in 1i32..=8 {
            let cache = cache.clone();
            handles.push(thread::spawn(move || {
                let host_id = Uuid::new_v4();
                let host = create_test_host(host_id, cores, ByteSize::gb(8));
                cache.check_in(host, false);
                host_id
            }));
        }

        let host_ids: Vec<Uuid> = handles
            .into_iter()
            .map(|h| h.join().expect("worker panicked"))
            .collect();

        // Every bucket should be populated.
        let outer = cache.hosts_index.read().unwrap();
        assert_eq!(outer.len(), 8, "one bucket per core size");
        for (core_key, bucket) in outer.iter() {
            let bucket_lock = bucket.lock().unwrap();
            let total_hosts: usize = bucket_lock.values().map(|set| set.len()).sum();
            assert_eq!(
                total_hosts, 1,
                "bucket at core_key={core_key} should contain exactly one host"
            );
        }
        // And every checked-in host id is reachable.
        for id in host_ids {
            assert!(HOST_STORE.get(&id).is_some(), "host {id} present in store");
        }
    }
}
