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
    collections::{BTreeMap, HashMap},
    sync::RwLock,
    time::{Duration, SystemTime},
};

use bytesize::ByteSize;
use miette::Result;
use tracing::{info, trace};

use crate::{
    config::{HostBookingStrategy, CONFIG},
    host_cache::HostCacheError,
    models::{CoreSize, Host},
};

type HostId = String;
type CoreKey = u32;
type MemoryKey = u64;

/// A B-Tree of Hosts ordered by memory
pub type MemoryBTree = BTreeMap<MemoryKey, HashMap<HostId, Host>>;

/// Combined data structure that holds both mappings under a single lock.
/// This ensures atomic updates across both data structures, preventing race conditions
/// where check_in and check_out operations could see inconsistent state.
struct HostCacheData {
    // TODO: This cache structure is a mess. Redesign it to have a central repository for all hosts
    // key'ed by id. Add last_updated to Host entries to ensure a host check_in doesn't race a cache refresh
    //
    /// HashMap of cache keys belonging to a host
    host_keys_by_host_id: HashMap<HostId, (CoreKey, MemoryKey)>,
    /// B-Tree of host groups ordered by their number of available cores
    hosts_by_core_and_memory: BTreeMap<CoreKey, MemoryBTree>,
}

impl HostCacheData {
    fn new() -> Self {
        Self {
            host_keys_by_host_id: HashMap::new(),
            hosts_by_core_and_memory: BTreeMap::new(),
        }
    }
}

pub struct HostCache {
    /// Single lock protecting both data structures to ensure atomic operations
    data: RwLock<HostCacheData>,
    /// If a cache stops being queried for a certain amount of time, stop keeping it up to date
    last_queried: RwLock<SystemTime>,
    /// Marks if the data on this cache have expired
    last_fetched: RwLock<Option<SystemTime>>,
    strategy: HostBookingStrategy,
}

impl Default for HostCache {
    fn default() -> Self {
        HostCache {
            data: RwLock::new(HostCacheData::new()),
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
    /// passes the validation function. Uses a range-based search for efficient
    /// resource matching.
    ///
    /// This method now acquires a single write lock for the entire operation,
    /// ensuring atomicity between finding the host and removing it from both
    /// data structures.
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

        let mut data = self
            .data
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        // Find and remove the host atomically under a single lock
        let found_keys = {
            let mut iter: Box<dyn Iterator<Item = (&CoreKey, &MemoryBTree)>> =
                if !self.strategy.core_saturation {
                    // Reverse order to find hosts with max amount of cores available
                    Box::new(data.hosts_by_core_and_memory.range(core_key..).rev())
                } else {
                    Box::new(data.hosts_by_core_and_memory.range(core_key..))
                };

            iter.find_map(|(by_core_key, hosts_by_memory)| {
                let find_fn = |(by_memory_key, hosts): (&u64, &HashMap<String, _>)| {
                    let found_host = hosts.iter().find(|(_, host)| {
                        // Only select a host that pass the validation function.
                        // Check memory capacity as a memory key groups a range of
                        // different memory values
                        validation(host) && host.idle_memory >= memory
                    });
                    found_host.map(|(host_key, _)| (*by_core_key, *by_memory_key, host_key.clone()))
                };

                if self.strategy.memory_saturation {
                    // Search for hosts with at least the same amount of memory requested
                    hosts_by_memory.range(memory_key..).find_map(find_fn)
                } else {
                    // Search for hosts with the most amount of memory available
                    hosts_by_memory.range(memory_key..).rev().find_map(find_fn)
                }
            })
        };

        // Now remove the host using the found keys, all under the same write lock
        if let Some((by_core_key, by_memory_key, host_key)) = found_keys {
            // Remove from hosts_by_core_and_memory
            let removed = data
                .hosts_by_core_and_memory
                .get_mut(&by_core_key)
                .and_then(|hosts_by_memory| hosts_by_memory.get_mut(&by_memory_key))
                .and_then(|hosts| hosts.remove(&host_key));

            if let Some(host) = removed {
                // Remove from host_keys_by_host_id
                data.host_keys_by_host_id.remove(&host_key);
                return Some(host);
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
    pub fn check_in(&self, host: Host) {
        let core_key = host.idle_cores.value() as CoreKey;
        let memory_key = Self::gen_memory_key(host.idle_memory);
        let host_id = host.id.clone();

        let mut data = self
            .data
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        // Atomically: remove old entry (if exists) and insert new entry
        // This prevents race conditions where check_out could see partial state
        if let Some((old_core_key, old_memory_key)) = data.host_keys_by_host_id.remove(&host_id) {
            // Remove from the old location in hosts_by_core_and_memory
            if let Some(hosts_by_memory) = data.hosts_by_core_and_memory.get_mut(&old_core_key) {
                if let Some(hosts) = hosts_by_memory.get_mut(&old_memory_key) {
                    hosts.remove(&host_id);
                }
            }
        } else {
            info!("---Failed to find key to remove {}", host.id);
        }

        // Insert at the new location
        data.hosts_by_core_and_memory
            .entry(core_key)
            .or_default()
            .entry(memory_key)
            .or_default()
            .insert(host_id.clone(), host);

        // Update the host_keys_by_host_id mapping
        data.host_keys_by_host_id
            .insert(host_id, (core_key, memory_key));
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
    use opencue_proto::host::ThreadMode;
    use std::thread;
    use std::time::Duration;
    use tokio_test::{assert_err, assert_ok};
    use uuid::Uuid;

    fn create_test_host(id: Uuid, idle_cores: i32, idle_memory: ByteSize) -> Host {
        Host {
            id: id.to_string(),
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
            alloc_id: Uuid::new_v4().to_string(),
            alloc_name: "test".to_string(),
        }
    }

    #[test]
    fn test_new_host_cache() {
        let cache = HostCache::default();
        let data = cache.data.read().unwrap();
        assert!(data.host_keys_by_host_id.is_empty());
        assert!(data.hosts_by_core_and_memory.is_empty());
        drop(data);
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

        cache.check_in(host.clone());

        let data = cache.data.read().unwrap();
        assert!(data.host_keys_by_host_id.contains_key(&host_id.to_string()));
        assert!(!data.hosts_by_core_and_memory.is_empty());
    }

    #[test]
    fn test_insert_host_updates_existing() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host1 = create_test_host(host_id, 4, ByteSize::gb(8));
        let mut host2 = create_test_host(host_id, 8, ByteSize::gb(16));
        host2.name = "updated-host".to_string();

        cache.check_in(host1);
        cache.check_in(host2.clone());

        // Should still have only one entry for this host ID
        let data = cache.data.read().unwrap();
        assert_eq!(data.host_keys_by_host_id.len(), 1);

        // The host should be updated with new resources
        let (core_key, memory_key) = data.host_keys_by_host_id.get(&host_id.to_string()).unwrap();
        assert_eq!(*core_key, 8);
        assert!(*memory_key > 0);
    }

    #[test]
    fn test_checkout_success() {
        let cache = HostCache::default();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.check_in(host);

        let result = cache.check_out(
            CoreSize(2),
            ByteSize::gb(4),
            |_| true, // Always validate true
        );

        let checked_out_host = assert_ok!(result);
        let memory_key = HostCache::gen_memory_key(checked_out_host.idle_memory);
        let core_key = checked_out_host.idle_cores.value() as u32;

        assert_eq!(checked_out_host.id, host_id.to_string());

        let data = cache.data.read().unwrap();
        assert!(!data.host_keys_by_host_id.contains_key(&host_id.to_string()));

        let left_over_host = data
            .hosts_by_core_and_memory
            .get(&core_key)
            .and_then(|hosts_by_memory| hosts_by_memory.get(&memory_key))
            .and_then(|hosts| hosts.get(&checked_out_host.id));
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

        cache.check_in(host);

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

        cache.check_in(host);

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

        cache.check_in(host);

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

        cache.check_in(host);

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

        cache.check_in(host.clone());

        // Checkout the host
        let mut checked_host = assert_ok!(cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true));
        assert_eq!(checked_host.idle_cores.value(), 4);

        // Reduce the number of cores and checkin to ensure cache is updated
        checked_host.idle_cores = CoreSize(1);

        // Check it back in
        cache.check_in(checked_host);
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

        cache.check_in(host1);
        cache.check_in(host2);
        cache.check_in(host3);

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

        cache.check_in(host1);
        cache.check_in(host2);

        // First checkout should succeed
        let result1 = cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result1.is_ok());

        // Second checkout should also succeed (different host)
        let result2 = cache.check_out(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result2.is_ok());

        // The hosts should be different
        assert_ne!(result1.unwrap().id, result2.unwrap().id);
    }
}
