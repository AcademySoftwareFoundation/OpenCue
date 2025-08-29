use std::{
    collections::{BTreeMap, HashMap},
    sync::RwLock,
    time::{Duration, SystemTime},
};

use bytesize::ByteSize;
use dashmap::DashMap;
use miette::Result;
use tracing::error;
use uuid::Uuid;

use crate::{
    config::CONFIG,
    host_cache::HostCacheError,
    models::{CoreSize, Host},
};

type HostId = Uuid;
type CoreKey = u32;
type MemoryKey = u64;

pub struct HostCache {
    host_keys_by_host_id: DashMap<HostId, (CoreKey, MemoryKey)>,
    hosts_by_core_and_memory: BTreeMap<CoreKey, BTreeMap<MemoryKey, HashMap<HostId, Host>>>,
    /// If a cache stops being queried for a certain amount of time, stop keeping it up to date
    last_queried: RwLock<SystemTime>,
    /// Marks if the data on this cache have expired
    last_fetched: RwLock<Option<SystemTime>>,
    _mode: HostBookingStrategy,
    /// A registry of hosts that have been checked_out and their checkout time.
    checked_out_hosts: DashMap<HostId, SystemTime>,
}

pub enum HostBookingStrategy {
    /// Prioritize high utilization of hosts
    _PrioritizeResourceSaturation,

    /// Prioritize high distribution of hosts
    PrioritizeLoadDistribution,
}

impl HostCache {
    pub fn new() -> Self {
        HostCache {
            host_keys_by_host_id: DashMap::new(),
            hosts_by_core_and_memory: BTreeMap::new(),
            last_queried: RwLock::new(SystemTime::now()),
            last_fetched: RwLock::new(None),
            _mode: HostBookingStrategy::PrioritizeLoadDistribution,
            checked_out_hosts: DashMap::new(),
        }
    }

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
    pub fn checkout<F>(
        &self,
        cores: CoreSize,
        memory: ByteSize,
        validation: F,
    ) -> Result<&Host, HostCacheError>
    where
        F: Fn(&Host) -> bool,
    {
        self.ping_query();

        let host = self
            .find_candidate(cores, memory, validation)
            .ok_or(HostCacheError::NoCandidateAvailable)?;

        self.checked_out_hosts.insert(host.id, SystemTime::now());
        Ok(host)
    }

    /// Release the host to be checked out by another agent
    ///
    /// Hosts don't need to be re-added to the resource_map as the service loop constantly reads
    /// their updated state from the database
    pub fn checkin(&self, host: &Host) {
        let _ = self.checked_out_hosts.remove(&host.id);
    }

    fn find_candidate<F>(&self, cores: CoreSize, memory: ByteSize, validation: F) -> Option<&Host>
    where
        F: Fn(&Host) -> bool,
    {
        // Should take checked_out_hosts into consideration
        let core_key = cores.value() as u32;
        let memory_key = Self::gen_memory_key(memory);
        self.hosts_by_core_and_memory
            // Start searching from the core_key
            .range(core_key..)
            .find_map(|(_, hosts_by_memory)| {
                hosts_by_memory
                    // On each entry, search for hosts with at least the same amount of memory requested
                    .range(memory_key..)
                    .find_map(|(_, hosts)| {
                        hosts.iter().find(|(_, host)|
                                // Only select a host that pass the validation function
                                validation(host) &&
                                // Skip hosts that are currently checked out
                                !self.is_checked_out(&host.id))
                    })
            })
            .map(|(_, h)| h)
        // TODO: Make this logic strategy aware
    }

    /// Check if a host is checked out.
    ///
    /// Warning: This function has a side-effect, it remotes expired checkout records
    fn is_checked_out(&self, host_id: &HostId) -> bool {
        if let Some(checked_out_host) = self.checked_out_hosts.get(host_id) {
            // If elapsed fails due to clock drift, fallback to a small number to prevent releasing the lock
            // accidentally
            let checkout_duration = checked_out_host
                .elapsed()
                .unwrap_or(Duration::from_millis(1));
            if checkout_duration > CONFIG.host_cache.checkout_timeout {
                self.checked_out_hosts.remove(host_id);
                false
            } else {
                true
            }
        } else {
            false
        }
    }

    pub fn insert(&mut self, host: Host) {
        // First clear the old version of the host from memory
        if let Some((host_id, (old_core_key, old_memory_key))) =
            self.host_keys_by_host_id.remove(&host.id)
        {
            match self.hosts_by_core_and_memory.get_mut(&old_core_key) {
                Some(hosts_by_memory) => {
                    if let Some(hosts) = hosts_by_memory.get_mut(&old_memory_key) {
                        let removed = hosts.remove(&host_id);
                        if removed.is_none() {
                            error!(
                                "Invalid state. Host exists on host_map_keys but could not be found on resource_map"
                            )
                        }
                    }
                }
                None => error!(
                    "Invalid state. Host exists on host_map_keys but could not be found on resource_map"
                ),
            }
        }
        let core_key = host.idle_cores.value() as CoreKey;
        let memory_key = Self::gen_memory_key(host.idle_memory);
        let host_id = host.id;
        self.hosts_by_core_and_memory
            .entry(core_key)
            .or_default()
            .entry(memory_key)
            .or_default()
            .insert(host.id, host);
        
        // Update the host_keys_by_host_id mapping
        self.host_keys_by_host_id.insert(host_id, (core_key, memory_key));
    }

    fn gen_memory_key(memory: ByteSize) -> MemoryKey {
        memory.as_u64() / CONFIG.host_cache.memory_key_divisor.as_u64()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration;
    use opencue_proto::host::ThreadMode;

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
            idle_gpu_memory: ByteSize::b(0),
            thread_mode: ThreadMode::Auto,
            alloc_available_cores: CoreSize(idle_cores),
            allocation_name: "test".to_string(),
        }
    }

    #[test]
    fn test_new_host_cache() {
        let cache = HostCache::new();
        assert!(cache.host_keys_by_host_id.is_empty());
        assert!(cache.hosts_by_core_and_memory.is_empty());
        assert!(cache.checked_out_hosts.is_empty());
        assert!(!cache.expired());
    }

    #[test]
    fn test_ping_query_updates_last_queried() {
        let cache = HostCache::new();
        let initial_time = *cache.last_queried.read().unwrap();
        
        thread::sleep(Duration::from_millis(1));
        cache.ping_query();
        
        let updated_time = *cache.last_queried.read().unwrap();
        assert!(updated_time > initial_time);
    }

    #[test]
    fn test_ping_fetch_updates_last_fetched() {
        let cache = HostCache::new();
        assert!(cache.last_fetched.read().unwrap().is_none());
        
        cache.ping_fetch();
        
        assert!(cache.last_fetched.read().unwrap().is_some());
    }

    #[test]
    fn test_expired_when_never_fetched() {
        let cache = HostCache::new();
        assert!(!cache.expired());
    }

    #[test]
    fn test_expired_when_recently_fetched() {
        let cache = HostCache::new();
        cache.ping_fetch();
        assert!(!cache.expired());
    }

    #[test]
    fn test_is_idle_when_recently_queried() {
        let cache = HostCache::new();
        cache.ping_query();
        assert!(!cache.is_idle());
    }

    #[test]
    fn test_insert_host() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.insert(host.clone());

        assert!(cache.host_keys_by_host_id.contains_key(&host_id));
        assert!(!cache.hosts_by_core_and_memory.is_empty());
    }

    #[test]
    fn test_insert_host_updates_existing() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host1 = create_test_host(host_id, 4, ByteSize::gb(8));
        let mut host2 = create_test_host(host_id, 8, ByteSize::gb(16));
        host2.name = "updated-host".to_string();

        cache.insert(host1);
        cache.insert(host2.clone());

        // Should still have only one entry for this host ID
        assert_eq!(cache.host_keys_by_host_id.len(), 1);
        
        // The host should be updated with new resources
        let (core_key, memory_key) = cache.host_keys_by_host_id.get(&host_id).unwrap().clone();
        assert_eq!(core_key, 8);
        assert!(memory_key > 0);
    }

    #[test]
    fn test_checkout_success() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.insert(host);

        let result = cache.checkout(
            CoreSize(2),
            ByteSize::gb(4),
            |_| true, // Always validate true
        );

        assert!(result.is_ok());
        let checked_out_host = result.unwrap();
        assert_eq!(checked_out_host.id, host_id);
        assert!(cache.checked_out_hosts.contains_key(&host_id));
    }

    #[test]
    fn test_checkout_no_candidate_available() {
        let cache = HostCache::new();

        let result = cache.checkout(
            CoreSize(4),
            ByteSize::gb(8),
            |_| true,
        );

        assert!(result.is_err());
        assert!(matches!(result, Err(HostCacheError::NoCandidateAvailable)));
    }

    #[test]
    fn test_checkout_insufficient_cores() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 2, ByteSize::gb(8));

        cache.insert(host);

        let result = cache.checkout(
            CoreSize(4), // Request more cores than available
            ByteSize::gb(4),
            |_| true,
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_insufficient_memory() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(4));

        cache.insert(host);

        let result = cache.checkout(
            CoreSize(2),
            ByteSize::gb(8), // Request more memory than available
            |_| true,
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_validation_fails() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.insert(host);

        let result = cache.checkout(
            CoreSize(2),
            ByteSize::gb(4),
            |_| false, // Always fail validation
        );

        assert!(result.is_err());
    }

    #[test]
    fn test_checkout_already_checked_out() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.insert(host);

        // First checkout should succeed
        let result1 = cache.checkout(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result1.is_ok());

        // Second checkout should fail because host is already checked out
        let result2 = cache.checkout(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result2.is_err());
    }

    #[test]
    fn test_checkin() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.insert(host.clone());

        // Checkout the host
        let result = cache.checkout(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result.is_ok());
        assert!(cache.checked_out_hosts.contains_key(&host_id));

        // Check it back in
        cache.checkin(&host);
        assert!(!cache.checked_out_hosts.contains_key(&host_id));
    }

    #[test]
    fn test_is_checked_out_false_when_not_checked_out() {
        let cache = HostCache::new();
        let host_id = Uuid::new_v4();
        
        assert!(!cache.is_checked_out(&host_id));
    }

    #[test]
    fn test_is_checked_out_true_when_recently_checked_out() {
        let mut cache = HostCache::new();
        let host_id = Uuid::new_v4();
        let host = create_test_host(host_id, 4, ByteSize::gb(8));

        cache.insert(host);
        let _ = cache.checkout(CoreSize(2), ByteSize::gb(4), |_| true);

        assert!(cache.is_checked_out(&host_id));
    }

    #[test]
    fn test_find_candidate_with_multiple_hosts() {
        let mut cache = HostCache::new();
        
        // Add hosts with different resources
        let host1_id = Uuid::new_v4();
        let host1 = create_test_host(host1_id, 2, ByteSize::gb(4));
        
        let host2_id = Uuid::new_v4();
        let host2 = create_test_host(host2_id, 4, ByteSize::gb(8));
        
        let host3_id = Uuid::new_v4();
        let host3 = create_test_host(host3_id, 8, ByteSize::gb(16));

        cache.insert(host1);
        cache.insert(host2);
        cache.insert(host3);

        // Request 3 cores, 6GB - should get host2 (4 cores, 8GB) or host3 (8 cores, 16GB)
        let result = cache.checkout(CoreSize(3), ByteSize::gb(6), |_| true);
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
        let mut cache = HostCache::new();
        
        // Add multiple hosts with same resource configuration
        let host1_id = Uuid::new_v4();
        let host1 = create_test_host(host1_id, 4, ByteSize::gb(8));
        
        let host2_id = Uuid::new_v4();  
        let host2 = create_test_host(host2_id, 4, ByteSize::gb(8));

        cache.insert(host1);
        cache.insert(host2);

        // First checkout should succeed
        let result1 = cache.checkout(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result1.is_ok());

        // Second checkout should also succeed (different host)
        let result2 = cache.checkout(CoreSize(2), ByteSize::gb(4), |_| true);
        assert!(result2.is_ok());

        // The hosts should be different
        assert_ne!(result1.unwrap().id, result2.unwrap().id);
    }

    #[test]
    fn test_host_booking_strategy() {
        let cache = HostCache::new();
        // Just verify the strategy is set correctly
        assert!(matches!(cache._mode, HostBookingStrategy::PrioritizeLoadDistribution));
    }
}
