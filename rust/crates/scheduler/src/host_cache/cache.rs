use std::{
    collections::{BTreeMap, HashMap},
    ops::RangeBounds,
    sync::RwLock,
    time::{Duration, SystemTime},
};

use bytesize::ByteSize;
use miette::Result;
use tracing::debug;

use crate::{
    config::CONFIG,
    host_cache::HostCacheError,
    models::{CoreSize, Host},
};

type HostId = String;
type CoreKey = u32;
type MemoryKey = u64;

pub struct HostCache {
    host_keys_by_host_id: HostKeysByHostId,
    hosts_by_core_and_memory: HostsByCoreAndMemory,
    /// If a cache stops being queried for a certain amount of time, stop keeping it up to date
    last_queried: RwLock<SystemTime>,
    /// Marks if the data on this cache have expired
    last_fetched: RwLock<Option<SystemTime>>,
    _mode: HostBookingStrategy,
}

struct HostKeysByHostId {
    map: RwLock<HashMap<HostId, (CoreKey, MemoryKey)>>,
}

impl HostKeysByHostId {
    fn new() -> Self {
        Self {
            map: RwLock::new(HashMap::new()),
        }
    }

    fn remove(&self, host_id: &str) -> Option<(CoreKey, MemoryKey)> {
        let mut lock = self
            .map
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        lock.remove(host_id)
    }

    fn insert(
        &self,
        host_id: String,
        core_key: CoreKey,
        memory_key: MemoryKey,
    ) -> Option<(CoreKey, MemoryKey)> {
        let mut lock = self
            .map
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        lock.insert(host_id, (core_key, memory_key))
    }

    #[allow(dead_code)]
    fn contains_key(&self, host_id: &String) -> bool {
        let lock = self
            .map
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        lock.contains_key(host_id)
    }

    #[allow(dead_code)]
    fn is_empty(&self) -> bool {
        let lock = self
            .map
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        lock.is_empty()
    }

    #[allow(dead_code)]
    fn len(&self) -> usize {
        let lock = self
            .map
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        lock.len()
    }

    #[allow(dead_code)]
    fn get(&self, host_id: &str) -> Option<(CoreKey, MemoryKey)> {
        let lock = self
            .map
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        lock.get(host_id).cloned()
    }
}

pub type MemoryBTree = BTreeMap<MemoryKey, HashMap<HostId, Host>>;
struct HostsByCoreAndMemory {
    map: RwLock<BTreeMap<CoreKey, MemoryBTree>>,
}

impl HostsByCoreAndMemory {
    fn new() -> Self {
        Self {
            map: RwLock::new(BTreeMap::new()),
        }
    }

    fn find_map_in_range<R, F>(&self, range: R, f: F) -> Option<(CoreKey, MemoryKey, String)>
    where
        Self: Sized,
        F: FnMut(
            (&u32, &BTreeMap<MemoryKey, HashMap<HostId, Host>>),
        ) -> Option<(CoreKey, MemoryKey, String)>,
        R: RangeBounds<CoreKey>,
    {
        let lock = self
            .map
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        lock.range(range).find_map(f)
    }

    fn remove(&self, core_key: &CoreKey, memory_key: &MemoryKey, host_key: String) -> Option<Host> {
        let mut write_lock = self
            .map
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        if let Some(hosts_by_memory) = write_lock.get_mut(core_key) {
            if let Some(hosts) = hosts_by_memory.get_mut(memory_key) {
                return hosts.remove(&host_key);
            }
        }
        None
    }

    fn insert(
        &self,
        core_key: CoreKey,
        memory_key: MemoryKey,
        host_id: String,
        host: Host,
    ) -> Option<Host> {
        let mut write_lock = self
            .map
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        write_lock
            .entry(core_key)
            .or_default()
            .entry(memory_key)
            .or_default()
            .insert(host_id.clone(), host)
    }

    #[allow(dead_code)]
    fn is_empty(&self) -> bool {
        let lock = self
            .map
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        lock.is_empty()
    }

    #[allow(dead_code)]
    fn len(&self) -> usize {
        let lock = self
            .map
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        lock.len()
    }

    #[allow(dead_code)]
    fn get(&self, core_key: &CoreKey, memory_key: &MemoryKey, host_id: &String) -> Option<Host> {
        let lock = self
            .map
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner());

        lock.get(core_key)
            .map(|hosts_by_memory| {
                hosts_by_memory
                    .get(memory_key)
                    .map(|hosts| hosts.get(host_id))
            })
            .unwrap_or_default()
            .unwrap_or_default()
            .cloned()
    }
}

pub enum HostBookingStrategy {
    /// Prioritize high utilization of hosts
    /// TODO: Strategy not implemented yet
    _PrioritizeResourceSaturation,

    /// Prioritize high distribution of hosts
    PrioritizeLoadDistribution,
}

impl Default for HostCache {
    fn default() -> Self {
        HostCache {
            host_keys_by_host_id: HostKeysByHostId::new(),
            hosts_by_core_and_memory: HostsByCoreAndMemory::new(),
            last_queried: RwLock::new(SystemTime::now()),
            last_fetched: RwLock::new(None),
            _mode: HostBookingStrategy::PrioritizeLoadDistribution,
        }
    }
}

impl HostCache {
    fn ping_query(&self) {
        let mut lock = self
            .last_queried
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        *lock = SystemTime::now();
    }

    pub fn ping_fetch(&self) {
        let mut lock = self
            .last_fetched
            .write()
            .unwrap_or_else(|poisoned| poisoned.into_inner());
        *lock = Some(SystemTime::now());
    }

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

    pub fn is_idle(&self) -> bool {
        self.last_queried
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .elapsed()
            .unwrap_or(Duration::from_secs(1))
            > CONFIG.host_cache.group_idle_timeout
    }

    /// Get best candidate and "remove" it from the list
    pub fn check_out<F>(
        &self,
        cores: CoreSize,
        memory: ByteSize,
        validation: F,
    ) -> Result<Host, HostCacheError>
    where
        F: Fn(&Host) -> bool,
    {
        debug!("Initialized actual check_out");
        self.ping_query();

        let host = self
            .remove_host(cores, memory, validation)
            .ok_or(HostCacheError::NoCandidateAvailable)?;

        self.host_keys_by_host_id.remove(&host.id);
        debug!("Finalized actual check_out");

        Ok(host)
    }

    fn remove_host<F>(&self, cores: CoreSize, memory: ByteSize, validation: F) -> Option<Host>
    where
        F: Fn(&Host) -> bool,
    {
        // Takes checked_out_hosts into consideration
        let core_key = cores.value() as u32;
        let memory_key = Self::gen_memory_key(memory);

        // First find the host we want to remove without borrowing mutably
        let found_keys = {
            // Start searching from the core_key
            self.hosts_by_core_and_memory.find_map_in_range(
                core_key..,
                |(by_core_key, hosts_by_memory)| {
                    hosts_by_memory
                        // On each entry, search for hosts with at least the same amount of memory requested
                        .range(memory_key..)
                        .find_map(|(by_memory_key, hosts)| {
                            let found_host = hosts.iter().find(|(_, host)|
                                    // Only select a host that pass the validation function.
                                    // Check memory capacity as a memory key groups a range of different memory values
                                    validation(host) && host.idle_memory >= memory);
                            found_host.map(|(host_key, _)| {
                                (*by_core_key, *by_memory_key, host_key.clone())
                            })
                        })
                },
            )
        };

        // Now remove the host using the found keys
        if let Some((by_core_key, by_memory_key, host_key)) = found_keys {
            let removed =
                self.hosts_by_core_and_memory
                    .remove(&by_core_key, &by_memory_key, host_key);
            if removed.is_some() {
                return removed;
            }
        }
        None
        // TODO: Make this logic strategy aware
    }

    pub fn check_in(&self, host: Host) {
        // First clear the old version of the host from memory
        if let Some((old_core_key, old_memory_key)) = self.host_keys_by_host_id.remove(&host.id) {
            self.hosts_by_core_and_memory
                .remove(&old_core_key, &old_memory_key, host.id.clone());
        }

        let core_key = host.idle_cores.value() as CoreKey;
        let memory_key = Self::gen_memory_key(host.idle_memory);
        let host_id = host.id.clone();

        self.hosts_by_core_and_memory
            .insert(core_key, memory_key, host_id.clone(), host);

        // Update the host_keys_by_host_id mapping
        self.host_keys_by_host_id
            .insert(host_id, core_key, memory_key);
    }

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
            allocation_name: "test".to_string(),
        }
    }

    #[test]
    fn test_new_host_cache() {
        let cache = HostCache::default();
        assert!(cache.host_keys_by_host_id.is_empty());
        assert!(cache.hosts_by_core_and_memory.is_empty());
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

        assert!(
            cache
                .host_keys_by_host_id
                .contains_key(&host_id.to_string())
        );
        assert!(!cache.hosts_by_core_and_memory.is_empty());
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
        assert_eq!(cache.host_keys_by_host_id.len(), 1);

        // The host should be updated with new resources
        let (core_key, memory_key) = cache
            .host_keys_by_host_id
            .get(&host_id.to_string())
            .unwrap();
        assert_eq!(core_key, 8);
        assert!(memory_key > 0);
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
        assert!(
            !cache
                .host_keys_by_host_id
                .contains_key(&host_id.to_string())
        );

        let left_over_host =
            cache
                .hosts_by_core_and_memory
                .get(&core_key, &memory_key, &checked_out_host.id);
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

    #[test]
    fn test_host_booking_strategy() {
        let cache = HostCache::default();
        // Just verify the strategy is set correctly
        assert!(matches!(
            cache._mode,
            HostBookingStrategy::PrioritizeLoadDistribution
        ));
    }
}
