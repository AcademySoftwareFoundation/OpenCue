use std::{
    cmp,
    collections::{HashMap, HashSet},
    time::{Duration, Instant},
};

use itertools::Itertools;
use miette::Result;
use opencue_proto::report::CoreDetail;
use tracing::warn;
use uuid::Uuid;

use crate::system::{manager::ReservationError, *};

/// Lookup tables representing Physical and Virtual cores and their threads
/// Ids on this structure are used for booking
#[derive(Debug, Clone)]
pub struct ProcessorStructure {
    /// {phys_id}_{core_id} -> [thread_ids]
    threads_by_core_unique_id: HashMap<String, Vec<ThreadId>>,
    /// phys_id -> [core_ids]
    cores_by_phys_id: HashMap<PhysId, Vec<CoreId>>,
    /// thread_id => (phys_id, core_id)
    thread_id_lookup_table: HashMap<ThreadId, (PhysId, CoreId)>,
}

impl ProcessorStructure {
    pub fn init(
        threads_by_core_unique_id: HashMap<String, Vec<ThreadId>>,
        cores_by_phys_id: HashMap<PhysId, Vec<CoreId>>,
        thread_id_lookup_table: HashMap<ThreadId, (PhysId, CoreId)>,
    ) -> Self {
        ProcessorStructure {
            threads_by_core_unique_id,
            cores_by_phys_id,
            thread_id_lookup_table,
        }
    }

    pub fn num_cores(&self) -> u32 {
        self.threads_by_core_unique_id.len() as u32
    }
}

#[derive(Debug, Clone)]
pub struct CoreBooking {
    pub cores: HashSet<(PhysId, CoreId)>,
    // Some kind of reservation expiration could be implemented to make this logic even more reliable
    pub start_time: Instant,
}

impl CoreBooking {
    pub fn new() -> Self {
        CoreBooking {
            cores: HashSet::new(),
            start_time: Instant::now(),
        }
    }

    pub fn insert(&mut self, core_id: (PhysId, CoreId)) -> bool {
        self.cores.insert(core_id)
    }

    pub fn expired(&self, timeout: Duration) -> bool {
        self.start_time.elapsed() > timeout
    }
}

pub struct CoreStateManager {
    // reserved_cores_by_physid: HashMap<u32, CoreBooking>,
    bookings: HashMap<ResourceId, CoreBooking>,
    processor_structure: ProcessorStructure,
    locked_cores: u32,
    reservation_grace_period: Duration,
}

impl CoreStateManager {
    pub fn new(processor_structure: ProcessorStructure) -> Self {
        CoreStateManager {
            bookings: HashMap::default(),
            processor_structure,
            locked_cores: 0,
            reservation_grace_period: Duration::from_secs(60),
        }
    }

    /// Reserves a specified number of CPU cores for a given resource.
    ///
    /// This method attempts to reserve the requested number of cores by selecting from
    /// available cores across all physical processors. It prioritizes physical processors
    /// with more available cores to optimize resource allocation.
    ///
    /// # Arguments
    ///
    /// * `num_cores` - The number of cores to reserve
    /// * `resource_id` - The UUID of the resource requesting the cores
    ///
    /// # Returns
    ///
    /// * `Ok(Vec<ThreadId>)` - A vector of thread IDs associated with the reserved cores.
    ///   Each core typically has multiple threads (e.g., 2 threads per core for hyperthreading).
    /// * `Err(ReservationError::NotEnoughResourcesAvailable)` - If the requested number of
    ///   cores cannot be satisfied due to insufficient available resources.
    ///
    /// # Behavior
    ///
    /// - Cores are selected from available cores across all physical processors
    /// - Physical processors with more available cores are prioritized
    /// - All threads associated with each reserved core are returned
    /// - The reservation is tracked internally and associated with the provided resource ID
    ///
    /// # Examples
    ///
    /// ```
    /// let resource_id = Uuid::new_v4();
    /// let thread_ids = manager.reserve_cores(2, resource_id)?;
    /// println!("Reserved {} thread IDs for 2 cores", thread_ids.len());
    /// ```
    pub fn reserve_cores(
        &mut self,
        num_cores: usize,
        resource_id: ResourceId,
    ) -> Result<Vec<ThreadId>, ReservationError> {
        let mut selected_threads = Vec::with_capacity(num_cores * 2);
        let available_cores = self.calculate_available_cores();
        let mut num_reserved_cores = 0;

        let cores_to_reserve: Vec<(PhysId, CoreId)> = available_cores
            .flat_map(|(phys_id, core_ids)| {
                core_ids.into_iter().map(move |core_id| (phys_id, core_id))
            })
            .take(num_cores)
            .collect();

        for (phys_id, core_id) in cores_to_reserve {
            let core_unique_id = format!("{}_{}", phys_id, core_id);
            if let Some(threads) = self
                .processor_structure
                .threads_by_core_unique_id
                .get(&core_unique_id)
            {
                for thread_id in threads {
                    selected_threads.push((phys_id, core_id, *thread_id));
                }
                num_reserved_cores += 1;
            } else {
                warn!("Failed to find thread for coreid={}", core_id)
            }
        }

        if num_reserved_cores != num_cores {
            Err(ReservationError::NotEnoughResourcesAvailable)?
        }
        for (phys_id, core_id, _thread_id) in selected_threads.clone() {
            self.bookings
                .entry(resource_id)
                .or_insert(CoreBooking::new())
                .insert((phys_id, core_id));
        }

        Ok(selected_threads
            .into_iter()
            .map(|(_, _, thread_id)| thread_id)
            .collect())
    }

    /// Get a list of all cores booked for this phys_id
    fn get_bookings(&self, phys_id: &PhysId) -> impl Iterator<Item = CoreId> {
        self.bookings.values().flat_map(|booking| {
            let cores: Vec<CoreId> = booking
                .cores
                .iter()
                .filter(|&(phys_id_all, _)| *phys_id == *phys_id_all)
                .map(|(_, core_id)| *core_id)
                .collect();
            cores
        })
    }

    fn calculate_available_cores(&self) -> impl Iterator<Item = (PhysId, Vec<CoreId>)> {
        self.processor_structure
            .cores_by_phys_id
            .iter()
            .map(|(phys_id, all_cores)| {
                let bookings_for_physid: Vec<CoreId> = self.get_bookings(phys_id).collect();
                let available_cores: Vec<CoreId> = all_cores
                    .iter()
                    .filter(|core_id| !bookings_for_physid.contains(core_id))
                    .cloned()
                    .collect();
                // Subtract all_cores by booked_cores for this physid

                (*phys_id, available_cores)
            })
            // Sort sockets with more available cores first
            .sorted_by(|a, b| Ord::cmp(&b.1.len(), &a.1.len()))
    }

    // TODO: Experimental. This solution allows double booking and should only be used at
    // recovery mode, when there are no frames running.
    #[deprecated(
        note = "This function is only safe when used before the booking loop gets activated. \
        Its usage is reserved to the recovery logic"
    )]
    pub fn reserve_cores_by_id(
        &mut self,
        thread_ids: Vec<ThreadId>,
        resource_id: ResourceId,
    ) -> Result<Vec<ThreadId>, ReservationError> {
        // First collect unmatched thread IDs to avoid borrowing issues
        let unmatched_thread_ids: Vec<ThreadId> = thread_ids
            .iter()
            .filter(|thread_id| {
                !self
                    .processor_structure
                    .thread_id_lookup_table
                    .contains_key(thread_id)
            })
            .cloned()
            .collect();

        if !unmatched_thread_ids.is_empty() {
            return Err(ReservationError::CoreNotFoundForThread(
                unmatched_thread_ids,
            ));
        }

        // Now process the reservations after validation
        for thread_id in &thread_ids {
            if let Some((phys_id, core_id)) = self
                .processor_structure
                .thread_id_lookup_table
                .get(thread_id)
            {
                self.bookings
                    .entry(resource_id)
                    .or_insert(CoreBooking::new())
                    .insert((*phys_id, *core_id));
            }
        }

        Ok(thread_ids.to_owned())
    }

    /// Releases all cores associated with a given resource ID.
    ///
    /// This method removes the booking for the specified resource and returns the list of
    /// cores that were previously reserved. Once released, these cores become available
    /// for new reservations.
    ///
    /// # Arguments
    ///
    /// * `resource_id` - The UUID of the resource whose cores should be released
    ///
    /// # Returns
    ///
    /// * `Ok(Vec<(PhysId, CoreId)>)` - A vector of tuples containing the physical processor ID
    ///   and core ID for each core that was released
    /// * `Err(ReservationError::ReservationNotFound)` - If no booking exists for the given resource ID
    ///
    /// # Examples
    ///
    /// ```
    /// let resource_id = Uuid::new_v4();
    /// // ... reserve some cores first ...
    /// let released_cores = manager.release_cores(&resource_id)?;
    /// println!("Released {} cores", released_cores.len());
    /// ```
    pub fn release_cores(
        &mut self,
        resource_id: &Uuid,
    ) -> Result<Vec<(PhysId, CoreId)>, ReservationError> {
        self.bookings
            .remove(resource_id)
            .map(|booking| booking.cores.into_iter().collect())
            .ok_or(ReservationError::ReservationNotFound(*resource_id))
    }

    /// Lock a specified number of cores. If the amount requested is not available, the maximum
    /// available will be locked.
    ///
    /// # Arguments
    ///
    /// * `count` - Number of cores to lock
    ///
    /// # Returns
    ///
    /// * `u32` - The actual number of cores that were locked (may be less than requested if not enough are available)
    pub fn lock_cores(&mut self, count: u32) -> u32 {
        let amount_not_locked = self.processor_structure.num_cores() - self.locked_cores;
        let amount_to_lock = std::cmp::min(amount_not_locked, count);

        if amount_to_lock > 0 {
            self.locked_cores += amount_to_lock;
        }

        amount_to_lock as u32
    }

    /// Lock all cores
    pub fn lock_all_cores(&mut self) {
        self.locked_cores = self.processor_structure.num_cores();
    }

    /// Unlock a specified number of cores that were previously locked.
    ///
    /// # Arguments
    ///
    /// * `count` - Number of cores to unlock
    ///
    /// # Returns
    ///
    /// * `u32` - The actual number of cores that were unlocked (may be less than requested if fewer cores are locked)
    pub fn unlock_cores(&mut self, count: u32) -> u32 {
        let previously_locked = self.locked_cores;
        self.locked_cores = self.locked_cores.saturating_sub(count);

        cmp::min(count, previously_locked)
    }

    /// Unlock all cores
    pub fn unlock_all_cores(&mut self) {
        self.locked_cores = 0;
    }

    /// Generates a detailed report of core usage statistics.
    ///
    /// This method calculates and returns comprehensive information about the current state
    /// of CPU cores, including total, idle, locked, and booked cores. The values are
    /// multiplied by the provided core multiplier to account for hyperthreading or other
    /// virtualization scenarios.
    ///
    /// # Arguments
    ///
    /// * `core_multiplier` - A multiplier applied to all core counts (typically 2 for hyperthreading)
    ///
    /// # Returns
    ///
    /// A `CoreDetail` struct containing:
    /// - `total_cores`: Total number of cores available (physical cores × multiplier)
    /// - `idle_cores`: Number of cores that are neither booked nor locked (minimum of non-booked and unlocked cores × multiplier)
    /// - `locked_cores`: Number of cores that have been administratively locked (locked cores × multiplier)
    /// - `booked_cores`: Number of cores that have been reserved for active jobs (booked cores × multiplier)
    /// - `reserved_cores`: HashMap of reserved cores by category (currently empty)
    ///
    /// # Examples
    ///
    /// ```
    /// let report = manager.get_core_info_report(2); // 2x for hyperthreading
    /// println!("Total cores: {}", report.total_cores);
    /// println!("Available cores: {}", report.idle_cores);
    /// ```
    pub fn get_core_info_report(&self, core_multiplier: u32) -> CoreDetail {
        let total_cores = self.processor_structure.num_cores() as i32;
        let locked_cores = self.locked_cores as i32;

        // Idle cores needs to take both cores that are booked and locked.
        // At the end, the number of idle cores is the min between non_booked and unlocked cores
        let available_cores = self.calculate_available_cores();
        let non_booked_cores = available_cores
            .map(|(_, cores)| cores.len() as u32)
            .sum::<u32>() as i32;
        let unlocked_cores = total_cores - locked_cores;
        let idle_cores = cmp::min(non_booked_cores, unlocked_cores) as i32;

        let booked_cores = self
            .bookings
            .values()
            .map(|booking| booking.cores.len() as i32)
            .sum::<i32>();

        CoreDetail {
            total_cores: total_cores * core_multiplier as i32,
            idle_cores: idle_cores * core_multiplier as i32,
            locked_cores: locked_cores * core_multiplier as i32,
            booked_cores: booked_cores * core_multiplier as i32,
            reserved_cores: HashMap::default(),
        }
    }

    /// Removes reservations that are no longer active or have expired.
    ///
    /// This method cleans up the bookings by retaining only those reservations that either:
    /// - Have a resource ID that is still active (present in `active_resource_ids`)
    /// - Have not yet expired based on the configured reservation grace period
    ///
    /// # Arguments
    ///
    /// * `active_resource_ids` - A vector of resource IDs that are currently active
    pub fn sanitize_reservations(&mut self, active_resource_ids: &[ResourceId]) {
        self.bookings.retain(|resource_id, booking| {
            let retain = active_resource_ids.contains(resource_id)
                || !booking.expired(self.reservation_grace_period);
            if !retain {
                warn!("Cleaning up dangling reservation for {}", resource_id);
            }
            retain
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use uuid::Uuid;

    fn create_test_processor_structure() -> ProcessorStructure {
        let mut threads_by_core_unique_id = HashMap::new();
        let mut cores_by_phys_id = HashMap::new();
        let mut thread_id_lookup_table = HashMap::new();

        // Physical processor 0 with 2 cores, each with 2 threads
        threads_by_core_unique_id.insert("0_0".to_string(), vec![0, 1]);
        threads_by_core_unique_id.insert("0_1".to_string(), vec![2, 3]);
        cores_by_phys_id.insert(0, vec![0, 1]);
        thread_id_lookup_table.insert(0, (0, 0));
        thread_id_lookup_table.insert(1, (0, 0));
        thread_id_lookup_table.insert(2, (0, 1));
        thread_id_lookup_table.insert(3, (0, 1));

        // Physical processor 1 with 2 cores, each with 2 threads
        threads_by_core_unique_id.insert("1_0".to_string(), vec![4, 5]);
        threads_by_core_unique_id.insert("1_1".to_string(), vec![6, 7]);
        cores_by_phys_id.insert(1, vec![0, 1]);
        thread_id_lookup_table.insert(4, (1, 0));
        thread_id_lookup_table.insert(5, (1, 0));
        thread_id_lookup_table.insert(6, (1, 1));
        thread_id_lookup_table.insert(7, (1, 1));

        ProcessorStructure::init(
            threads_by_core_unique_id,
            cores_by_phys_id,
            thread_id_lookup_table,
        )
    }

    #[test]
    fn test_processor_structure_init() {
        let processor_structure = create_test_processor_structure();
        assert_eq!(processor_structure.num_cores(), 4);
        assert_eq!(processor_structure.threads_by_core_unique_id.len(), 4);
        assert_eq!(processor_structure.cores_by_phys_id.len(), 2);
        assert_eq!(processor_structure.thread_id_lookup_table.len(), 8);
    }

    #[test]
    fn test_processor_structure_num_cores() {
        let processor_structure = create_test_processor_structure();
        assert_eq!(processor_structure.num_cores(), 4);
    }

    #[test]
    fn test_core_booking_new() {
        let booking = CoreBooking::new();
        assert!(booking.cores.is_empty());
    }

    #[test]
    fn test_core_booking_insert() {
        let mut booking = CoreBooking::new();
        let core_id = (0, 0);

        // First insert should return true
        assert!(booking.insert(core_id));
        assert_eq!(booking.cores.len(), 1);
        assert!(booking.cores.contains(&core_id));

        // Second insert of same core should return false
        assert!(!booking.insert(core_id));
        assert_eq!(booking.cores.len(), 1);
    }

    #[test]
    fn test_core_state_manager_new() {
        let processor_structure = create_test_processor_structure();
        let manager = CoreStateManager::new(processor_structure);
        assert_eq!(manager.bookings.len(), 0);
        assert_eq!(manager.locked_cores, 0);
    }

    #[test]
    fn test_reserve_cores_success() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        let result = manager.reserve_cores(2, resource_id);
        assert!(result.is_ok());

        let thread_ids = result.unwrap();
        assert_eq!(thread_ids.len(), 4); // 2 cores * 2 threads per core
        assert!(manager.bookings.contains_key(&resource_id));
        assert_eq!(manager.bookings[&resource_id].cores.len(), 2);
    }

    #[test]
    fn test_reserve_cores_not_enough_available() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        // Try to reserve more cores than available
        let result = manager.reserve_cores(10, resource_id);
        assert!(result.is_err());
        assert!(matches!(
            result.unwrap_err(),
            ReservationError::NotEnoughResourcesAvailable
        ));
    }

    #[test]
    fn test_reserve_cores_multiple_reservations() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id1 = Uuid::new_v4();
        let resource_id2 = Uuid::new_v4();

        // Reserve 2 cores for first resource
        let result1 = manager.reserve_cores(2, resource_id1);
        assert!(result1.is_ok());

        // Reserve 2 cores for second resource
        let result2 = manager.reserve_cores(2, resource_id2);
        assert!(result2.is_ok());

        assert_eq!(manager.bookings.len(), 2);

        // Try to reserve more cores - should fail as all are taken
        let resource_id3 = Uuid::new_v4();
        let result3 = manager.reserve_cores(1, resource_id3);
        assert!(result3.is_err());
    }

    #[test]
    fn test_reserve_cores_by_id_success() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();
        let thread_ids = vec![0, 1, 2, 3];

        #[allow(deprecated)]
        let result = manager.reserve_cores_by_id(thread_ids.clone(), resource_id);
        assert!(result.is_ok());

        let returned_thread_ids = result.unwrap();
        assert_eq!(returned_thread_ids, thread_ids);
        assert!(manager.bookings.contains_key(&resource_id));
        assert_eq!(manager.bookings[&resource_id].cores.len(), 2); // 2 cores covered by the threads
    }

    #[test]
    fn test_reserve_cores_by_id_invalid_thread() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();
        let thread_ids = vec![0, 1, 99]; // 99 doesn't exist

        #[allow(deprecated)]
        let result = manager.reserve_cores_by_id(thread_ids, resource_id);
        assert!(result.is_err());
        assert!(matches!(
            result.unwrap_err(),
            ReservationError::CoreNotFoundForThread(_)
        ));
    }

    #[test]
    fn test_release_cores_success() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        // Reserve cores first
        let _result = manager.reserve_cores(2, resource_id);
        assert!(manager.bookings.contains_key(&resource_id));

        // Release cores
        let release_result = manager.release_cores(&resource_id);
        assert!(release_result.is_ok());

        let released_cores = release_result.unwrap();
        assert_eq!(released_cores.len(), 2);
        assert!(!manager.bookings.contains_key(&resource_id));
    }

    #[test]
    fn test_release_cores_not_found() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        let result = manager.release_cores(&resource_id);
        assert!(result.is_err());
        assert!(matches!(
            result.unwrap_err(),
            ReservationError::ReservationNotFound(_)
        ));
    }

    #[test]
    fn test_lock_cores() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);

        // Lock 2 cores
        let locked = manager.lock_cores(2);
        assert_eq!(locked, 2);
        assert_eq!(manager.locked_cores, 2);

        // Lock 1 more core
        let locked = manager.lock_cores(1);
        assert_eq!(locked, 1);
        assert_eq!(manager.locked_cores, 3);

        // Try to lock more cores than available
        let locked = manager.lock_cores(5);
        assert_eq!(locked, 1); // Only 1 core left
        assert_eq!(manager.locked_cores, 4);
    }

    #[test]
    fn test_lock_all_cores() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);

        manager.lock_all_cores();
        assert_eq!(manager.locked_cores, 4);
    }

    #[test]
    fn test_unlock_cores() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);

        // Lock some cores first
        manager.lock_cores(3);
        assert_eq!(manager.locked_cores, 3);

        // Unlock 2 cores
        let unlocked = manager.unlock_cores(2);
        assert_eq!(unlocked, 2);
        assert_eq!(manager.locked_cores, 1);

        // Try to unlock more cores than are locked
        let unlocked = manager.unlock_cores(5);
        assert_eq!(unlocked, 1); // Only 1 core was locked
        assert_eq!(manager.locked_cores, 0);
    }

    #[test]
    fn test_unlock_all_cores() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);

        manager.lock_cores(3);
        assert_eq!(manager.locked_cores, 3);

        manager.unlock_all_cores();
        assert_eq!(manager.locked_cores, 0);
    }

    #[test]
    fn test_get_core_info_report() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        // Initial state - all cores available
        let report = manager.get_core_info_report(2); // core_multiplier = 2
        assert_eq!(report.total_cores, 8); // 4 cores * 2 multiplier
        assert_eq!(report.idle_cores, 8);
        assert_eq!(report.locked_cores, 0);
        assert_eq!(report.booked_cores, 0);

        // Reserve 2 cores
        let _result = manager.reserve_cores(2, resource_id);
        let report = manager.get_core_info_report(2);
        assert_eq!(report.total_cores, 8);
        assert_eq!(report.idle_cores, 4); // 2 cores * 2 multiplier still available
        assert_eq!(report.locked_cores, 0);
        assert_eq!(report.booked_cores, 4); // 2 cores * 2 multiplier booked

        // Lock 1 core
        manager.lock_cores(1);
        let report = manager.get_core_info_report(2);
        assert_eq!(report.total_cores, 8);
        assert_eq!(report.idle_cores, 4); // min(non_booked=2, unlocked=3) = 2, * 2 multiplier = 4
        assert_eq!(report.locked_cores, 2); // 1 core * 2 multiplier
        assert_eq!(report.booked_cores, 4);
    }

    #[test]
    fn test_get_bookings() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        // Reserve some cores
        let _result = manager.reserve_cores(2, resource_id);

        // Get bookings for all physical processors and verify total
        let bookings_0: Vec<CoreId> = manager.get_bookings(&0).collect();
        let bookings_1: Vec<CoreId> = manager.get_bookings(&1).collect();

        // Should have exactly 2 cores booked total across both processors
        assert_eq!(bookings_0.len() + bookings_1.len(), 2);

        // At least one processor should have book
        assert!(!bookings_0.is_empty() || !bookings_1.is_empty());
    }

    #[test]
    fn test_calculate_available_cores() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        // Initially all cores should be available
        let available: Vec<(PhysId, Vec<CoreId>)> = manager.calculate_available_cores().collect();
        assert_eq!(available.len(), 2); // 2 physical processors

        let total_available: usize = available.iter().map(|(_, cores)| cores.len()).sum();
        assert_eq!(total_available, 4); // 4 cores total

        // Reserve 2 cores
        let _result = manager.reserve_cores(2, resource_id);

        // Check available cores after reservation
        let available: Vec<(PhysId, Vec<CoreId>)> = manager.calculate_available_cores().collect();
        let total_available: usize = available.iter().map(|(_, cores)| cores.len()).sum();
        assert_eq!(total_available, 2); // 2 cores still available
    }

    #[test]
    fn test_core_allocation_strategy() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        // Reserve 1 core and check that it prioritizes the socket with more available cores
        let result = manager.reserve_cores(1, resource_id);
        assert!(result.is_ok());

        let thread_ids = result.unwrap();
        assert_eq!(thread_ids.len(), 2); // 1 core * 2 threads per core

        // Verify that the booking was made
        assert!(manager.bookings.contains_key(&resource_id));
        assert_eq!(manager.bookings[&resource_id].cores.len(), 1);
    }

    #[test]
    fn test_locked_cores_affect_idle_calculation() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);

        // Lock 2 cores
        manager.lock_cores(2);

        let report = manager.get_core_info_report(1);
        assert_eq!(report.total_cores, 4);
        assert_eq!(report.locked_cores, 2);
        assert_eq!(report.idle_cores, 2); // min(non_booked=4, unlocked=2) = 2
        assert_eq!(report.booked_cores, 0);
    }

    #[test]
    fn test_mixed_locked_and_booked_cores() {
        let processor_structure = create_test_processor_structure();
        let mut manager = CoreStateManager::new(processor_structure);
        let resource_id = Uuid::new_v4();

        // Lock 1 core and book 2 cores
        manager.lock_cores(1);
        let _result = manager.reserve_cores(2, resource_id);

        let report = manager.get_core_info_report(1);
        assert_eq!(report.total_cores, 4);
        assert_eq!(report.locked_cores, 1);
        assert_eq!(report.booked_cores, 2);
        // Idle cores should be min(non_booked=2, unlocked=3) = 2
        assert_eq!(report.idle_cores, 2);
    }
}
