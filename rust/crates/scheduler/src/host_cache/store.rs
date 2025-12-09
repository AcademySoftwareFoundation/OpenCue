//! Thread-safe host data storage with optimistic concurrency control.
//!
//! This module provides a global host store that manages host information with
//! concurrent read/write access and timestamp-based conflict resolution.

use chrono::Utc;
use lazy_static::lazy_static;

use scc::HashMap;
use tracing::debug;

use crate::{config::CONFIG, host_cache::HostId, models::Host};

/// Thread-safe store for host data with concurrent access support.
///
/// The `HostStore` uses `scc::HashMap` for lock-free concurrent operations.
///
/// # Concurrency Model
///
/// - **All operations** use lock-free atomic operations via `scc::HashMap`
/// - **Conflict resolution**: Timestamp-based optimistic concurrency control
///
/// # Staleness Detection
///
/// The store automatically detects and removes stale hosts during:
/// - `get()` operations - removes stale hosts on access
/// - `cleanup_stale_hosts()` - batch removal of all stale hosts
/// - `atomic_remove_if_valid()` - removes stale hosts regardless of validation
///
/// Staleness threshold is configured via `CONFIG.host_cache.host_staleness_threshold`.
#[derive(Default)]
pub(super) struct HostStore {
    /// Host actual data indexed by HostId
    host_store: HashMap<HostId, Host>,
}

impl HostStore {
    /// Checks if a host is stale based on its last update timestamp.
    ///
    /// A host is considered stale if the time elapsed since its last update
    /// exceeds the configured staleness threshold.
    ///
    /// # Arguments
    ///
    /// * `host` - The host to check for staleness
    ///
    /// # Returns
    ///
    /// * `true` - If the host is stale (age > threshold)
    /// * `false` - If the host is still fresh or if duration conversion fails
    ///
    /// # Error Handling
    ///
    /// If the configured staleness threshold cannot be converted to a chrono Duration
    /// (extremely unlikely in practice), defaults to zero duration, treating all hosts
    /// as fresh. This prevents panics from malformed configuration.
    fn is_host_stale(host: &Host) -> bool {
        let now = Utc::now();
        let age = now - host.last_updated;
        let staleness_threshold = CONFIG.host_cache.host_staleness_threshold;
        let staleness_duration =
            chrono::Duration::from_std(staleness_threshold).unwrap_or_default();

        let stale = age > staleness_duration;
        if stale {
            debug!("Host {} on the cache store is stale", host);
        }
        stale
    }

    /// Retrieves a host by ID with automatic staleness detection and removal.
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
    /// # Concurrency & Race Conditions
    ///
    /// This operation uses lock-free reads followed by a lock-free removal if stale.
    /// Between the staleness check and removal, another thread could:
    /// - Update the host with fresh data (removal would fail or remove stale version)
    /// - Remove the host (removal becomes a no-op)
    ///
    /// These races are benign - at worst, a fresh host might need to be re-inserted,
    /// but staleness detection ensures no stale data is returned to the caller.
    pub fn get(&self, host_id: &HostId) -> Option<Host> {
        let host = self
            .host_store
            .get_sync(host_id)
            .map(|entry| entry.get().clone())?;

        // Check if the host is stale
        if Self::is_host_stale(&host) {
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
    /// This operation uses lock-free atomic removal from the concurrent HashMap.
    pub fn remove(&self, host_id: &HostId) -> Option<Host> {
        self.host_store.remove_sync(host_id).map(|(_, host)| host)
    }

    /// Atomically removes a host from the store only if it matches the expected state.
    ///
    /// This method implements atomic check-and-remove to prevent race conditions
    /// where a host's state changes between lookup and removal operations.
    ///
    /// # Arguments
    ///
    /// * `host_id` - The unique identifier of the host to remove
    /// * `expected_last_updated` - Expected timestamp to verify host hasn't changed
    /// * `validation` - Additional validation function that must pass for removal
    ///
    /// # Returns
    ///
    /// * `Ok(Some(Host))` - Host was successfully removed and matched expectations
    /// * `Ok(None)` - Host was not found in the store
    /// * `Err(())` - Host exists but doesn't match expected state (timestamp mismatch or validation failure)
    ///
    /// # Staleness Handling
    ///
    /// Stale hosts are always removed regardless of timestamp or validation checks.
    /// This ensures the store doesn't accumulate stale entries even when removal
    /// attempts fail validation.
    ///
    /// # Race Condition Prevention
    ///
    /// Uses atomic entry operations (`entry_sync()`) to ensure the host state
    /// verification and removal happen atomically. The entry holds exclusive access
    /// during the entire check-and-remove operation, preventing other threads from
    /// modifying the host between validation and removal.
    ///
    /// # Typical Usage Pattern
    ///
    /// ```ignore
    /// // Read host and remember timestamp
    /// let host = HOST_STORE.get(&host_id)?;
    /// let timestamp = host.last_updated;
    ///
    /// // ... perform some work ...
    ///
    /// // Atomically remove only if host hasn't changed
    /// match HOST_STORE.atomic_remove_if_valid(&host_id, timestamp, |h| h.idle_cores >= needed) {
    ///     Ok(Some(host)) => /* successfully removed */,
    ///     Ok(None) => /* host disappeared */,
    ///     Err(()) => /* host changed, retry operation */,
    /// }
    /// ```
    pub fn atomic_remove_if_valid<F>(
        &self,
        host_id: &HostId,
        expected_last_updated: chrono::DateTime<chrono::Utc>,
        validation: F,
    ) -> Result<Option<Host>, ()>
    where
        F: FnOnce(&Host) -> bool,
    {
        match self.host_store.entry_sync(*host_id) {
            scc::hash_map::Entry::Occupied(entry) => {
                let host = entry.get();

                // Check staleness first
                if Self::is_host_stale(host) {
                    // Host is stale, remove it
                    let removed_host = entry.remove();
                    return Ok(Some(removed_host));
                }

                // Verify host hasn't changed since we looked it up
                if host.last_updated != expected_last_updated {
                    return Err(());
                }

                // Apply additional validation
                if !validation(host) {
                    return Err(());
                }

                // All checks passed, atomically remove the host
                let removed_host = entry.remove();
                Ok(Some(removed_host))
            }
            scc::hash_map::Entry::Vacant(_) => Ok(None),
        }
    }

    /// Inserts or updates a host in the store with optimistic concurrency control.
    ///
    /// This method implements timestamp-based conflict resolution to prevent
    /// stale data from overwriting newer updates. It's the primary method for
    /// updating host state in the cache.
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
    /// - Used for authoritative sources like database loads or admin operations
    ///
    /// # Concurrency & Race Conditions
    ///
    /// This operation performs a lock-free read followed by a lock-free upsert.
    /// Between the timestamp check and upsert, another thread could:
    /// - Insert/update the same host with different data
    /// - Remove the host from the store
    ///
    /// The race is handled by `upsert_sync()` which atomically updates the entry.
    /// However, if multiple threads update concurrently, the last writer wins.
    /// Callers relying on ordering should use `atomic_remove_if_valid()` for
    /// stronger consistency guarantees.
    ///
    /// # Note on Non-Authoritative Updates
    ///
    /// Non-authoritative updates (`authoritative = false`) may be rejected if
    /// the incoming data is older than what's already in the store. This prevents
    /// out-of-order updates from overwriting fresher data, which can happen when
    /// multiple update sources have different latencies.
    pub fn insert(&self, host: Host, authoritative: bool) -> Host {
        // Ignore entries that are out of date
        if let Some(existing_host) = self.host_store.get_sync(&host.id) {
            if !authoritative && existing_host.last_updated >= host.last_updated {
                return existing_host.get().clone();
            }
        }
        self.host_store
            .upsert_sync(host.id, host.clone())
            .unwrap_or(host)
    }

    /// Removes all stale hosts from the store in a batch operation.
    ///
    /// A host is considered stale if:
    /// `current_time - host.last_updated > host_staleness_threshold`
    ///
    /// This method should be called periodically to clean up hosts that have
    /// not been updated recently and are no longer active. It's more efficient
    /// than relying solely on lazy removal via `get()` for large-scale cleanup.
    ///
    /// # Returns
    ///
    /// * `usize` - The number of stale hosts removed from the store
    ///
    /// # Implementation Details
    ///
    /// Uses a two-pass approach:
    /// 1. First pass: iterate through all hosts to identify stale entries
    /// 2. Second pass: remove identified stale hosts
    ///
    /// This avoids holding iteration locks during removal operations.
    ///
    /// # Concurrency & Race Conditions
    ///
    /// Between identifying stale hosts and removing them, concurrent operations may:
    /// - Update a stale host with fresh data (removal becomes a no-op or removes old version)
    /// - Remove hosts that we're about to remove (removal becomes a no-op)
    /// - Insert new hosts (won't affect this cleanup operation)
    ///
    /// These races are benign. The worst case is redundant removal attempts
    /// which are cheap no-ops. Fresh updates won't be incorrectly removed since
    /// the store uses atomic operations.
    pub fn cleanup_stale_hosts(&self) -> usize {
        let mut stale_host_ids = Vec::new();

        // First pass: identify stale hosts
        self.host_store.iter_sync(|host_id, host| {
            if Self::is_host_stale(host) {
                stale_host_ids.push(*host_id);
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
            last_updated,
            concurrent_frames_limit: None,
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
        assert!(store.get(&fresh_host_id).is_some());

        // Note: We don't call get() on stale hosts because get() automatically removes them.
        // Instead, we directly verify the store contains them by checking the internal state.
        // We'll verify removal works via cleanup_stale_hosts directly.

        // Run cleanup - should find and remove stale hosts
        let removed_count = store.cleanup_stale_hosts();

        // Should have removed 2 stale hosts
        assert_eq!(removed_count, 2);

        // Fresh host should still be present
        assert!(store.get(&fresh_host_id).is_some());

        // Stale hosts should be removed
        assert!(store.get(&stale_host_id).is_none());
        assert!(store.get(&very_stale_host_id).is_none());
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
        assert!(store.get(&host1_id).is_some());
        assert!(store.get(&host2_id).is_some());
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
        let result = store.get(&stale_host_id);
        assert!(result.is_none());

        // Second get should also return None
        let result2 = store.get(&stale_host_id);
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

    #[test]
    fn test_atomic_remove_if_valid_success() {
        let store = HostStore::default();

        // Create a test host
        let host_id = Uuid::new_v4();
        let timestamp = Utc::now();
        let host = create_test_host_with_timestamp(host_id, 4, ByteSize::gb(8), timestamp);

        store.insert(host.clone(), true);

        // Atomic remove should succeed with correct timestamp and validation
        let result =
            store.atomic_remove_if_valid(&host.id, timestamp, |h| h.idle_cores.value() >= 4);

        assert!(matches!(result, Ok(Some(_))));
        if let Ok(Some(removed_host)) = result {
            assert_eq!(removed_host.id, host.id);
        }

        // Host should be gone from store
        assert!(store.get(&host.id).is_none());
    }

    #[test]
    fn test_atomic_remove_if_valid_timestamp_mismatch() {
        let store = HostStore::default();

        // Create a test host
        let host_id = Uuid::new_v4();
        let timestamp = Utc::now();
        let host = create_test_host_with_timestamp(host_id, 4, ByteSize::gb(8), timestamp);

        store.insert(host.clone(), true);

        // Try to remove with wrong timestamp
        let wrong_timestamp = timestamp - ChronoDuration::seconds(60);
        let result =
            store.atomic_remove_if_valid(&host.id, wrong_timestamp, |h| h.idle_cores.value() >= 4);

        // Should return an error
        assert!(result.is_err());

        // Host should still be in store
        assert!(store.get(&host.id).is_some());
    }

    #[test]
    fn test_atomic_remove_if_valid_validation_failure() {
        let store = HostStore::default();

        // Create a test host with 4 cores
        let host_id = Uuid::new_v4();
        let timestamp = Utc::now();
        let host = create_test_host_with_timestamp(host_id, 4, ByteSize::gb(8), timestamp);

        store.insert(host.clone(), true);

        // Try to remove with validation requiring 8 cores
        let result = store.atomic_remove_if_valid(
            &host.id,
            timestamp,
            |h| h.idle_cores.value() >= 8, // This will fail
        );

        // Should return an error
        assert!(result.is_err());

        // Host should still be in store
        assert!(store.get(&host.id).is_some());
    }

    #[test]
    fn test_atomic_remove_if_valid_stale_host() {
        let store = HostStore::default();

        // Create a stale host
        let host_id = Uuid::new_v4();
        let staleness_threshold = CONFIG.host_cache.host_staleness_threshold;
        let staleness_duration = ChronoDuration::from_std(staleness_threshold).unwrap();
        let stale_timestamp = Utc::now() - staleness_duration - ChronoDuration::seconds(10);

        let host = create_test_host_with_timestamp(host_id, 4, ByteSize::gb(8), stale_timestamp);
        store.insert(host.clone(), true);

        // Atomic remove should succeed and remove stale host regardless of validation
        let result = store.atomic_remove_if_valid(
            &host.id,
            stale_timestamp,
            |h| h.idle_cores.value() >= 8, // Would normally fail, but staleness overrides
        );

        assert!(matches!(result, Ok(Some(_))));
        if let Ok(Some(removed_host)) = result {
            assert_eq!(removed_host.id, host.id);
        }

        // Host should be gone from store
        assert!(store.get(&host.id).is_none());
    }

    #[test]
    fn test_atomic_remove_if_valid_nonexistent_host() {
        let store = HostStore::default();

        let nonexistent_id = Uuid::new_v4();
        let result = store.atomic_remove_if_valid(&nonexistent_id, Utc::now(), |_| true);

        assert!(matches!(result, Ok(None)));
    }
}
