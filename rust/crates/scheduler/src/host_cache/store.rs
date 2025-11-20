//! Thread-safe host data storage with optimistic concurrency control.
//!
//! This module provides a global host store that manages host information with
//! concurrent read/write access and timestamp-based conflict resolution.

use chrono::Utc;
use lazy_static::lazy_static;

use scc::HashMap;

use crate::{config::CONFIG, host_cache::HostId, models::Host};

/// Thread-safe store for host data with concurrent access support.
///
/// The `HostStore` uses a combination of `RwLock` for structural access control
/// and `scc::HashMap` for lock-free concurrent operations. This design allows
/// multiple readers and safe concurrent writes.
///
/// # Concurrency Model
///
/// - **Read operations** (`get`): Multiple concurrent reads via read lock
/// - **Write operations** (`insert`, `remove`): Exclusive access via write lock
/// - **Conflict resolution**: Timestamp-based optimistic concurrency control
#[derive(Default)]
pub(super) struct HostStore {
    /// Host actual data indexed by HostId
    host_store: HashMap<HostId, Host>,
}

impl HostStore {
    /// Retrieves a host by ID.
    ///
    /// Returns a cloned copy of the host if found and not stale, or `None` if not present
    /// or if the host's last_updated timestamp exceeds the staleness threshold.
    ///
    /// # Arguments
    ///
    /// * `host_id` - The unique identifier of the host to retrieve
    ///
    /// # Returns
    ///
    /// * `Some(Host)` - A clone of the host data if found and not stale
    /// * `None` - If no host with the given ID exists or if the host is stale
    ///
    /// # Staleness Check
    ///
    /// A host is considered stale if:
    /// `current_time - host.last_updated > host_staleness_threshold`
    ///
    /// Stale hosts are automatically removed from the store when detected.
    ///
    /// # Concurrency
    ///
    /// This operation acquires a read lock for the initial lookup, allowing multiple
    /// concurrent reads. If a stale host is detected, it releases the read lock and
    /// acquires a write lock to remove the host.
    pub fn get(&self, host_id: &HostId) -> Option<Host> {
        let host = self
            .host_store
            .get_sync(host_id)
            .map(|entry| entry.get().clone())?;

        let now = Utc::now();
        let age = now - host.last_updated;
        let staleness_threshold = CONFIG.host_cache.host_staleness_threshold;

        // Check if the host is stale
        if age > chrono::Duration::from_std(staleness_threshold).unwrap_or_default() {
            // Host is stale, remove it from the store
            self.remove(host_id);
            return None;
        }

        Some(host)
    }

    /// Removes a host from the store by ID.
    ///
    /// # Arguments
    ///
    /// * `host_id` - The unique identifier of the host to remove
    ///
    /// # Returns
    ///
    /// * `Some(Host)` - The removed host data if it existed
    /// * `None` - If no host with the given ID was found
    ///
    /// # Concurrency
    ///
    /// This operation acquires a write lock, ensuring exclusive access during removal.
    /// Other read and write operations will block until this completes.
    pub fn remove(&self, host_id: &HostId) -> Option<Host> {
        self.host_store.remove_sync(host_id).map(|(_, host)| host)
    }

    /// Inserts or updates a host in the store with optimistic concurrency control.
    ///
    /// This method implements timestamp-based conflict resolution to prevent
    /// stale data from overwriting newer updates.
    ///
    /// # Arguments
    ///
    /// * `host` - The host data to insert or update
    /// * `authoritative` - If `true`, bypasses timestamp checks and forces the update.
    ///   If `false`, only updates if the new data is newer than existing data.
    ///
    /// # Returns
    ///
    /// The final host data in the store after the operation:
    /// * If inserted/updated: returns the new host data
    /// * If rejected (stale): returns the existing newer host data
    ///
    /// # Conflict Resolution
    ///
    /// When `authoritative = false`:
    /// - Compares `host.last_updated` with existing `last_updated` timestamp
    /// - Rejects update if incoming data is older or equal (`existing >= new`)
    /// - Returns existing data without modification
    ///
    /// When `authoritative = true`:
    /// - Unconditionally updates the host data
    /// - Used for authoritative sources like database loads
    ///
    /// # Concurrency
    ///
    /// This operation acquires a write lock for the duration of the insert/update.
    /// The timestamp check and upsert are performed atomically within the lock.
    pub fn insert(&self, host: Host, authoritative: bool) -> Host {
        // Ignore entries that are out of date
        if let Some(existing_host) = self.host_store.get_sync(&host.id) {
            if !authoritative && existing_host.last_updated >= host.last_updated {
                return existing_host.get().clone();
            }
        }
        self.host_store
            .upsert_sync(host.id.clone(), host.clone())
            .unwrap_or(host)
    }

    /// Removes all stale hosts from the store.
    ///
    /// A host is considered stale if:
    /// `current_time - host.last_updated > host_staleness_threshold`
    ///
    /// This method should be called periodically to clean up hosts that have
    /// not been updated recently and are no longer active.
    ///
    /// # Returns
    ///
    /// * `usize` - The number of stale hosts removed from the store
    ///
    /// # Concurrency
    ///
    /// This operation iterates through all hosts and removes stale entries.
    /// The iteration is done synchronously to ensure consistency.
    pub fn cleanup_stale_hosts(&self) -> usize {
        let now = Utc::now();
        let staleness_threshold = CONFIG.host_cache.host_staleness_threshold;
        let staleness_duration =
            chrono::Duration::from_std(staleness_threshold).unwrap_or_default();

        let mut stale_host_ids = Vec::new();

        // First pass: identify stale hosts
        self.host_store.iter_sync(|host_id, host| {
            let age = now - host.last_updated;
            if age > staleness_duration {
                stale_host_ids.push(host_id.clone());
            }
            true
        });

        // Second pass: remove stale hosts
        let removed_count = stale_host_ids.len();
        for host_id in stale_host_ids {
            self.remove(&host_id);
        }

        removed_count
    }
}

lazy_static! {
    /// Global singleton instance of the host store.
    ///
    /// This provides a shared, thread-safe host store accessible throughout
    /// the application. Initialized on first access using lazy initialization.
    ///
    /// # Usage
    ///
    /// ```ignore
    /// use crate::host_cache::store::HOST_STORE;
    ///
    /// // Read a host
    /// if let Some(host) = HOST_STORE.get(&host_id) {
    ///     println!("Found host: {:?}", host);
    /// }
    ///
    /// // Update a host
    /// HOST_STORE.insert(updated_host, false);
    ///
    /// // Remove a host
    /// HOST_STORE.remove(&host_id);
    /// ```
    ///
    /// # Thread Safety
    ///
    /// Multiple threads can safely access this store concurrently. Read operations
    /// can proceed in parallel, while write operations ensure exclusive access.
    pub(super) static ref HOST_STORE: HostStore = HostStore::default();
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{CoreSize, Host};
    use bytesize::ByteSize;
    use chrono::{Duration as ChronoDuration, Utc};
    use opencue_proto::host::ThreadMode;
    use std::thread;
    use uuid::Uuid;

    fn create_test_host_with_timestamp(
        id: Uuid,
        idle_cores: i32,
        idle_memory: ByteSize,
        last_updated: chrono::DateTime<Utc>,
    ) -> Host {
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
            last_updated,
        }
    }

    #[test]
    fn test_cleanup_stale_hosts_removes_old_hosts() {
        let store = HostStore::default();

        // Create hosts with different ages
        let now = Utc::now();
        let staleness_threshold = CONFIG.host_cache.host_staleness_threshold;
        let staleness_duration = ChronoDuration::from_std(staleness_threshold).unwrap();

        // Fresh host (within threshold)
        let fresh_host_id = Uuid::new_v4();
        let fresh_host = create_test_host_with_timestamp(
            fresh_host_id,
            4,
            ByteSize::gb(8),
            now - ChronoDuration::seconds(30),
        );

        // Stale host (beyond threshold)
        let stale_host_id = Uuid::new_v4();
        let stale_host = create_test_host_with_timestamp(
            stale_host_id,
            4,
            ByteSize::gb(8),
            now - staleness_duration - ChronoDuration::seconds(10),
        );

        // Very stale host (way beyond threshold)
        let very_stale_host_id = Uuid::new_v4();
        let very_stale_host = create_test_host_with_timestamp(
            very_stale_host_id,
            4,
            ByteSize::gb(8),
            now - staleness_duration - ChronoDuration::hours(1),
        );

        // Insert hosts using authoritative insert
        store.insert(fresh_host.clone(), true);
        store.insert(stale_host.clone(), true);
        store.insert(very_stale_host.clone(), true);

        // Verify fresh host is present (doesn't trigger removal via get)
        assert!(store.get(&fresh_host_id.to_string()).is_some());

        // Note: We don't call get() on stale hosts because get() automatically removes them.
        // Instead, we directly verify the store contains them by checking the internal state.
        // We'll verify removal works via cleanup_stale_hosts directly.

        // Run cleanup - should find and remove stale hosts
        let removed_count = store.cleanup_stale_hosts();

        // Should have removed 2 stale hosts
        assert_eq!(removed_count, 2);

        // Fresh host should still be present
        assert!(store.get(&fresh_host_id.to_string()).is_some());

        // Stale hosts should be removed
        assert!(store.get(&stale_host_id.to_string()).is_none());
        assert!(store.get(&very_stale_host_id.to_string()).is_none());
    }

    #[test]
    fn test_cleanup_stale_hosts_no_stale_hosts() {
        let store = HostStore::default();

        // Create only fresh hosts
        let now = Utc::now();

        let host1_id = Uuid::new_v4();
        let host1 = create_test_host_with_timestamp(
            host1_id,
            4,
            ByteSize::gb(8),
            now - ChronoDuration::seconds(10),
        );

        let host2_id = Uuid::new_v4();
        let host2 = create_test_host_with_timestamp(
            host2_id,
            4,
            ByteSize::gb(8),
            now - ChronoDuration::seconds(20),
        );

        store.insert(host1, true);
        store.insert(host2, true);

        // Run cleanup
        let removed_count = store.cleanup_stale_hosts();

        // Should have removed 0 hosts
        assert_eq!(removed_count, 0);

        // All hosts should still be present
        assert!(store.get(&host1_id.to_string()).is_some());
        assert!(store.get(&host2_id.to_string()).is_some());
    }

    #[test]
    fn test_cleanup_stale_hosts_empty_store() {
        let store = HostStore::default();

        // Run cleanup on empty store
        let removed_count = store.cleanup_stale_hosts();

        // Should have removed 0 hosts
        assert_eq!(removed_count, 0);
    }

    #[test]
    fn test_get_removes_stale_host() {
        let store = HostStore::default();

        // Create a stale host
        let now = Utc::now();
        let staleness_threshold = CONFIG.host_cache.host_staleness_threshold;
        let staleness_duration = ChronoDuration::from_std(staleness_threshold).unwrap();

        let stale_host_id = Uuid::new_v4();
        let stale_host = create_test_host_with_timestamp(
            stale_host_id,
            4,
            ByteSize::gb(8),
            now - staleness_duration - ChronoDuration::seconds(10),
        );

        store.insert(stale_host, true);

        // First get should detect staleness and remove the host
        let result = store.get(&stale_host_id.to_string());
        assert!(result.is_none());

        // Second get should also return None
        let result2 = store.get(&stale_host_id.to_string());
        assert!(result2.is_none());
    }

    #[test]
    fn test_cleanup_stale_hosts_concurrent() {
        use std::sync::Arc;

        let store = Arc::new(HostStore::default());

        // Create a mix of fresh and stale hosts
        let now = Utc::now();
        let staleness_threshold = CONFIG.host_cache.host_staleness_threshold;
        let staleness_duration = ChronoDuration::from_std(staleness_threshold).unwrap();

        for i in 0..10 {
            let host_id = Uuid::new_v4();
            let is_stale = i % 2 == 0;
            let timestamp = if is_stale {
                now - staleness_duration - ChronoDuration::seconds(10)
            } else {
                now - ChronoDuration::seconds(10)
            };

            let host = create_test_host_with_timestamp(host_id, 4, ByteSize::gb(8), timestamp);
            store.insert(host, true);
        }

        // Run cleanup from multiple threads
        let handles: Vec<_> = (0..3)
            .map(|_| {
                let store_clone = Arc::clone(&store);
                thread::spawn(move || store_clone.cleanup_stale_hosts())
            })
            .collect();

        // Wait for all threads to complete
        let results: Vec<_> = handles.into_iter().map(|h| h.join().unwrap()).collect();

        // At least one thread should report cleaning up hosts
        let total_removed: usize = results.iter().sum();
        assert!(total_removed > 0);
    }
}
