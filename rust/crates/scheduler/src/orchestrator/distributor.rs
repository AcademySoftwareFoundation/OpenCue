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

use std::collections::HashMap;
use std::time::{Duration, Instant};

use rand::Rng;

use miette::{IntoDiagnostic, Result};
use tracing::{debug, info, warn};
use uuid::Uuid;

use crate::cluster::{Cluster, ClusterFeed};
use crate::config::CONFIG;

use super::dao::{InstanceRow, OrchestratorDao};

/// Snapshot of an instance's jobs_queried value at a point in time,
/// used to compute the rate between distribution cycles.
struct RateSnapshot {
    jobs_queried: f64,
    timestamp: Instant,
}

/// Resolved facility binding for an instance.
/// Captures both the configured facility name and its resolved UUID from the facility table.
struct InstanceFacility {
    /// Facility name as configured on the instance (e.g. "spi"). `None` means unscoped.
    name: Option<String>,
    /// UUID resolved via the facility table. `None` when unscoped or when the name didn't resolve.
    id: Option<Uuid>,
}

/// The distributor runs on the leader instance. It loads all clusters from the database,
/// reads live instances, computes load rates, and assigns clusters to instances.
pub struct Distributor {
    /// Previous snapshots of each instance's jobs_queried counter, keyed by instance ID.
    previous_snapshots: HashMap<Uuid, RateSnapshot>,
    /// Tracks when each cluster assignment was created or last renewed, keyed by cluster ID.
    /// Used for TTL-based expiration to enable redistribution when new instances join.
    assignment_ages: HashMap<String, Instant>,
}

impl Distributor {
    /// Creates a new distributor with empty rate snapshots.
    ///
    /// The first distribution cycle will use count-based balancing since no
    /// previous rate data is available.
    pub fn new() -> Self {
        Distributor {
            previous_snapshots: HashMap::new(),
            assignment_ages: HashMap::new(),
        }
    }

    /// Seeds assignment ages from existing database assignments.
    ///
    /// Called on leader promotion to give existing assignments a jittered age
    /// spread across the TTL window. This prevents a thundering-herd redistribution
    /// when a new leader takes over by staggering expiration times.
    pub fn seed_ages(&mut self, current_assignments: &HashMap<String, Uuid>) {
        let now = Instant::now();
        let ttl = CONFIG.orchestrator.assignment_ttl;
        let mut rng = rand::thread_rng();
        self.assignment_ages = current_assignments
            .keys()
            .map(|cluster_id| {
                let random_age =
                    Duration::from_secs_f64(rng.gen_range(0.0..ttl.as_secs_f64()));
                (cluster_id.clone(), now - random_age)
            })
            .collect();
    }

    /// Filters out assignments whose age exceeds the configured TTL.
    ///
    /// Expired assignments appear "unassigned" to `compute_assignments`, causing them
    /// to go through the load-balanced second pass. Assignments with no tracked age
    /// (e.g. pre-existing before the TTL feature) are preserved.
    fn filter_expired_assignments(
        &self,
        current_assignments: &HashMap<String, Uuid>,
        now: Instant,
    ) -> HashMap<String, Uuid> {
        let assignment_ttl = CONFIG.orchestrator.assignment_ttl;
        current_assignments
            .iter()
            .filter(
                |(cluster_id, _)| match self.assignment_ages.get(*cluster_id) {
                    Some(created_at) => {
                        let age = now.duration_since(*created_at);
                        if age >= assignment_ttl {
                            debug!(
                                "Assignment for cluster {} expired (age: {:.1}s, ttl: {:.1}s)",
                                cluster_id,
                                age.as_secs_f64(),
                                assignment_ttl.as_secs_f64()
                            );
                            false
                        } else {
                            true
                        }
                    }
                    // Assignments with no birth date live forever
                    None => true,
                },
            )
            .map(|(k, v)| (k.clone(), *v))
            .collect()
    }

    /// Runs one distribution cycle: loads clusters, reads instances, computes assignments.
    ///
    /// Cleans up dead instances, loads all clusters from the database, reads live
    /// instances, computes job query rates, determines optimal cluster-to-instance
    /// assignments, and applies changes to the database.
    ///
    /// # Arguments
    ///
    /// * `dao` - Database access for reading instances and writing assignments
    /// * `ignore_tags` - Allocation tags to exclude from cluster loading
    /// * `failure_threshold` - Duration after which an instance without a heartbeat is considered dead
    ///
    /// # Returns
    ///
    /// * `Ok(())` - Distribution cycle completed successfully
    /// * `Err(miette::Error)` - Database error during distribution
    pub async fn distribute(
        &mut self,
        dao: &OrchestratorDao,
        ignore_tags: &[String],
        failure_threshold: Duration,
    ) -> Result<()> {
        // Clean up dead instances (cascade deletes their assignments)
        let dead = dao
            .delete_dead_instances(failure_threshold)
            .await
            .into_diagnostic()?;
        if !dead.is_empty() {
            info!("Removed {} dead instance(s): {:?}", dead.len(), dead);
            // Clean snapshots for dead instances
            for id in &dead {
                self.previous_snapshots.remove(id);
            }
        }

        // Load all clusters from the database
        let all_clusters = ClusterFeed::load_clusters(None, ignore_tags, None).await?;

        if all_clusters.is_empty() {
            debug!("No clusters found in database");
            return Ok(());
        }

        // Read live instances
        let instances = dao
            .get_live_instances(failure_threshold)
            .await
            .into_diagnostic()?;

        if instances.is_empty() {
            warn!("No live instances available for cluster distribution");
            return Ok(());
        }

        // Read current assignments, expired included (cluster_id -> instance_id)
        let current_assignments = dao.get_all_assignments().await.into_diagnostic()?;

        // Compute job query rates per instance (enriches instances with their rate)
        let rated_instances = self.compute_rates(instances);

        let now = Instant::now();
        let active_assignments = self.filter_expired_assignments(&current_assignments, now);

        // Compute new assignments using filtered (non-expired) assignments
        let new_assignments =
            Self::compute_assignments(&all_clusters, &rated_instances, &active_assignments);

        // Update assignment ages:
        // - New or changed assignments get a fresh timestamp
        // - Unchanged assignments keep their existing age
        // - Removed clusters get cleaned up
        let valid_cluster_ids: std::collections::HashSet<&String> =
            new_assignments.keys().collect();
        self.assignment_ages
            .retain(|cluster_id, _| valid_cluster_ids.contains(cluster_id));
        for (cluster_id, &new_instance) in &new_assignments {
            let is_new_or_changed = match active_assignments.get(cluster_id) {
                Some(&prev_instance) => prev_instance != new_instance,
                None => true,
            };
            if is_new_or_changed {
                self.assignment_ages.insert(cluster_id.clone(), now);
            }
        }

        // Apply assignment changes to the database (uses original current_assignments
        // to detect what actually changed in the DB)
        self.apply_assignments(dao, &all_clusters, &new_assignments, &current_assignments)
            .await?;

        // Update metrics
        crate::metrics::set_orchestrator_instances_alive(rated_instances.len());
        crate::metrics::increment_orchestrator_rebalance();

        debug!(
            "Distribution complete: {} clusters across {} instances",
            all_clusters.len(),
            rated_instances.len()
        );

        Ok(())
    }

    /// Computes the job query rate for each instance based on the delta from previous snapshots.
    /// Returns a map of instance_id -> (InstanceRow, rate) where rate is jobs/second.
    /// If no previous snapshot exists (bootstrap), rate is 0.0.
    fn compute_rates(
        &mut self,
        instances: HashMap<Uuid, InstanceRow>,
    ) -> HashMap<Uuid, (InstanceRow, f64)> {
        let now = Instant::now();
        let mut rated_instances = HashMap::new();

        for (id, instance) in instances {
            let rate = if let Some(prev) = self.previous_snapshots.get(&id) {
                let delta_jobs = instance.float_jobs_queried - prev.jobs_queried;
                let delta_secs = now.duration_since(prev.timestamp).as_secs_f64();
                if delta_secs > 0.0 && delta_jobs >= 0.0 {
                    delta_jobs / delta_secs
                } else {
                    0.0
                }
            } else {
                // No previous snapshot — bootstrap with rate 0
                0.0
            };

            // Update snapshots for next cycle
            self.previous_snapshots.insert(
                id,
                RateSnapshot {
                    jobs_queried: instance.float_jobs_queried,
                    timestamp: Instant::now(),
                },
            );
            rated_instances.insert(id, (instance, rate));
        }

        rated_instances
    }

    /// Pure function that computes the optimal cluster-to-instance assignment.
    ///
    /// Strategy:
    /// 1. Preserve stable assignments (cluster stays on same live instance).
    /// 2. Assign unassigned clusters to the instance with the lowest load ratio.
    pub fn compute_assignments(
        all_clusters: &[Cluster],
        rated_instances: &HashMap<Uuid, (InstanceRow, f64)>,
        active_assignments: &HashMap<String, Uuid>,
    ) -> HashMap<String, Uuid> {
        let mut assignments: HashMap<String, Uuid> = HashMap::new();

        // Collect instance IDs
        let instance_ids: Vec<Uuid> = rated_instances.keys().copied().collect();

        // Track load per instance (weighted by rate / capacity)
        let mut instance_load_count_capacity: HashMap<Uuid, (f64, usize, f64)> = instance_ids
            .iter()
            .map(|id| {
                let (inst, rate) = rated_instances.get(id).unwrap();
                (*id, (*rate, 0, inst.int_capacity as f64))
            })
            .collect();

        let all_rates_zero = rated_instances.values().all(|(_, rate)| *rate == 0.0);

        // Build facility map for affinity filtering
        let instance_facilities: HashMap<Uuid, InstanceFacility> = rated_instances
            .iter()
            .map(|(&id, (inst, _))| {
                (id, InstanceFacility {
                    name: inst.str_facility.clone(),
                    id: inst.str_facility_id,
                })
            })
            .collect();

        // First pass: preserve stable assignments where the instance is still alive
        for cluster in all_clusters {
            if let Some(&current_instance) = active_assignments.get(&cluster.id) {
                if rated_instances.contains_key(&current_instance) {
                    assignments.insert(cluster.id.clone(), current_instance);
                    if let Some((_rate, count, _capacity)) =
                        instance_load_count_capacity.get_mut(&current_instance)
                    {
                        *count += 1;
                    }
                }
            }
        }

        // Second pass: assign unassigned clusters
        for cluster in all_clusters {
            if assignments.contains_key(&cluster.id) {
                continue; // Already assigned in first pass
            }

            // Find eligible instances for this cluster's facility
            let eligible: Vec<Uuid> = instance_ids
                .iter()
                .filter(|id| Self::is_facility_eligible(cluster, &instance_facilities, **id))
                .copied()
                .collect();

            if eligible.is_empty() {
                warn!(
                    "No eligible instance for cluster {} (facility_id={})",
                    cluster, cluster.facility_id
                );
                continue;
            }

            let best = *eligible
                .iter()
                .min_by(|a, b| {
                    let (load_a, count_a, capacity_a) = *instance_load_count_capacity
                        .get(a)
                        .unwrap_or(&(0.0, 0, 1.0));
                    let (load_b, count_b, capacity_b) = *instance_load_count_capacity
                        .get(b)
                        .unwrap_or(&(0.0, 0, 1.0));

                    // If all rates are 0, use count based comparison
                    let (ratio_a, ratio_b) = if all_rates_zero {
                        (count_a as f64 / capacity_a, count_b as f64 / capacity_b)
                    } else {
                        (load_a / capacity_a, load_b / capacity_b)
                    };
                    ratio_a
                        .partial_cmp(&ratio_b)
                        .unwrap_or(std::cmp::Ordering::Equal)
                })
                .unwrap();

            assignments.insert(cluster.id.clone(), best);
            if let Some((load, count, _)) = instance_load_count_capacity.get_mut(&best) {
                *count += 1;

                // For rate-based distribution, slightly increase load estimate for
                // subsequent assignments within the same cycle.
                // Without this bump, if instance B has the lowest rate, it would win *every*
                // assignment in the loop, piling all unassigned clusters onto one instance.
                // By adding `1.0` to load after each assignment, the loop simulates the expected
                // increase in workload, so subsequent iterations see instance B as slightly
                // busier and may pick a different instance instead.
                // 1.0 is an arbitrary unit, but it's enough to spread clusters across instances
                // rather than dumping them all on the least-loaded one.
                *load += 1.0;
            }
        }

        assignments
    }

    /// Checks whether a cluster is eligible to run on a given instance based on facility.
    fn is_facility_eligible(
        cluster: &Cluster,
        instance_facilities: &HashMap<Uuid, InstanceFacility>,
        instance_id: Uuid,
    ) -> bool {
        match instance_facilities.get(&instance_id) {
            Some(InstanceFacility { name: Some(_), id: Some(facility_id) }) => {
                // Instance is scoped to a resolved facility — cluster must match
                cluster.facility_id == *facility_id
            }
            Some(InstanceFacility { name: Some(name), id: None }) => {
                // Instance has a facility name that didn't resolve — no cluster can match
                warn!(
                    "Instance {} has unresolved facility name '{}'",
                    instance_id, name
                );
                false
            }
            _ => {
                // Instance has no facility scope — accepts all clusters
                true
            }
        }
    }

    /// Applies the computed assignments to the database.
    /// Upserts new/changed assignments and deletes removed ones.
    async fn apply_assignments(
        &self,
        dao: &OrchestratorDao,
        all_clusters: &[Cluster],
        new_assignments: &HashMap<String, Uuid>,
        current_map: &HashMap<String, Uuid>,
    ) -> Result<()> {
        // Upsert assignments that are new or changed
        for cluster in all_clusters {
            if let Some(&new_instance) = new_assignments.get(&cluster.id) {
                let needs_upsert = match current_map.get(&cluster.id) {
                    Some(&current_instance) => current_instance != new_instance,
                    None => true,
                };

                if needs_upsert {
                    dao.upsert_assignment(new_instance, cluster)
                        .await
                        .into_diagnostic()?;
                    debug!("Assigned cluster {} to instance {}", cluster, new_instance);
                }
            }
        }

        // Delete assignments for clusters that no longer exist
        for cluster_id in current_map.keys() {
            if !new_assignments.contains_key(cluster_id) {
                dao.delete_assignment_by_cluster_id(cluster_id)
                    .await
                    .into_diagnostic()?;
                debug!("Removed stale assignment for cluster_id {}", cluster_id);
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use std::collections::HashMap;

    use uuid::Uuid;

    use crate::cluster::Cluster;
    use crate::cluster_key::{Tag, TagType};

    use super::{Distributor, InstanceFacility, InstanceRow};

    fn make_cluster(facility_id: Uuid, show_id: Uuid, tag: &str) -> Cluster {
        Cluster::single_tag(
            facility_id,
            show_id,
            Tag {
                name: tag.to_string(),
                ttype: TagType::Alloc,
            },
        )
    }

    fn make_instance(id: Uuid, facility: Option<Uuid>, capacity: i32) -> InstanceRow {
        make_instance_with_jobs(id, facility, capacity, 0.0)
    }

    fn make_instance_with_jobs(
        id: Uuid,
        facility: Option<Uuid>,
        capacity: i32,
        jobs_queried: f64,
    ) -> InstanceRow {
        InstanceRow {
            pk_instance: id,
            str_name: format!("test:{}", id),
            str_facility_id: facility,
            str_facility: facility.map(|f| f.to_string()),
            int_capacity: capacity,
            float_jobs_queried: jobs_queried,
            b_draining: false,
        }
    }

    #[test]
    fn test_even_distribution_bootstrap() {
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();

        let clusters: Vec<Cluster> = (0..6)
            .map(|i| make_cluster(facility, show, &format!("tag{}", i)))
            .collect();

        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (inst_a, (make_instance(inst_a, None, 100), 0.0)),
            (inst_b, (make_instance(inst_b, None, 100), 0.0)),
        ]
        .into();

        let current_map = HashMap::new();

        let assignments =
            Distributor::compute_assignments(&clusters, &rated_instances, &current_map);

        // All clusters should be assigned
        assert_eq!(assignments.len(), 6);

        // Each instance should get 3 clusters
        let count_a = assignments.values().filter(|&&v| v == inst_a).count();
        let count_b = assignments.values().filter(|&&v| v == inst_b).count();
        assert_eq!(count_a, 3);
        assert_eq!(count_b, 3);
    }

    #[test]
    fn test_stable_assignments_preserved() {
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();

        let clusters: Vec<Cluster> = (0..4)
            .map(|i| make_cluster(facility, show, &format!("tag{}", i)))
            .collect();

        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (inst_a, (make_instance(inst_a, None, 100), 100.0)),
            (inst_b, (make_instance(inst_b, None, 100), 50.0)),
        ]
        .into();

        // Pre-assign all clusters to inst_a
        let current_map: HashMap<String, Uuid> =
            clusters.iter().map(|c| (c.id.clone(), inst_a)).collect();

        let assignments =
            Distributor::compute_assignments(&clusters, &rated_instances, &current_map);

        // All clusters should stay with inst_a (stability)
        for instance in assignments.values() {
            assert_eq!(*instance, inst_a);
        }
    }

    #[test]
    fn test_facility_affinity() {
        let facility_a = Uuid::new_v4();
        let facility_b = Uuid::new_v4();
        let show = Uuid::new_v4();

        let cluster_a = make_cluster(facility_a, show, "tag_a");
        let cluster_b = make_cluster(facility_b, show, "tag_b");
        let clusters = vec![cluster_a.clone(), cluster_b.clone()];

        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (
                inst_a,
                (
                    make_instance(inst_a, Some(facility_a), 100),
                    0.0,
                ),
            ),
            (
                inst_b,
                (
                    make_instance(inst_b, Some(facility_b), 100),
                    0.0,
                ),
            ),
        ]
        .into();

        let current_map = HashMap::new();

        let assignments =
            Distributor::compute_assignments(&clusters, &rated_instances, &current_map);

        assert_eq!(assignments[&cluster_a.id], inst_a);
        assert_eq!(assignments[&cluster_b.id], inst_b);
    }

    #[test]
    fn test_weighted_capacity() {
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();

        let clusters: Vec<Cluster> = (0..9)
            .map(|i| make_cluster(facility, show, &format!("tag{}", i)))
            .collect();

        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (inst_a, (make_instance(inst_a, None, 200), 0.0)), // 2x capacity
            (inst_b, (make_instance(inst_b, None, 100), 0.0)),
        ]
        .into();

        let current_map = HashMap::new();

        let assignments =
            Distributor::compute_assignments(&clusters, &rated_instances, &current_map);

        let count_a = assignments.values().filter(|&&v| v == inst_a).count();
        let count_b = assignments.values().filter(|&&v| v == inst_b).count();

        // inst_a should get ~6, inst_b should get ~3 (2:1 ratio)
        assert_eq!(count_a, 6);
        assert_eq!(count_b, 3);
    }

    #[test]
    fn test_compute_rates_bootstrap_returns_zero() {
        let mut distributor = Distributor::new();
        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();

        let instances: HashMap<Uuid, InstanceRow> = [
            (inst_a, make_instance_with_jobs(inst_a, None, 100, 50.0)),
            (inst_b, make_instance_with_jobs(inst_b, None, 100, 30.0)),
        ]
        .into();

        let rated = distributor.compute_rates(instances);

        // Bootstrap: no previous snapshots, all rates should be 0.0
        assert_eq!(rated[&inst_a].1, 0.0);
        assert_eq!(rated[&inst_b].1, 0.0);
    }

    #[test]
    fn test_compute_rates_positive_delta() {
        let mut distributor = Distributor::new();
        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();

        // Cycle 1: bootstrap — populates snapshots
        let instances_t0: HashMap<Uuid, InstanceRow> = [
            (inst_a, make_instance_with_jobs(inst_a, None, 100, 100.0)),
            (inst_b, make_instance_with_jobs(inst_b, None, 100, 50.0)),
        ]
        .into();
        let _ = distributor.compute_rates(instances_t0);

        // Small delay to ensure non-zero elapsed time
        std::thread::sleep(std::time::Duration::from_millis(10));

        // Cycle 2: inst_a queried 200 more, inst_b queried 50 more
        let instances_t1: HashMap<Uuid, InstanceRow> = [
            (inst_a, make_instance_with_jobs(inst_a, None, 100, 300.0)),
            (inst_b, make_instance_with_jobs(inst_b, None, 100, 100.0)),
        ]
        .into();
        let rated = distributor.compute_rates(instances_t1);

        assert!(rated[&inst_a].1 > 0.0);
        assert!(rated[&inst_b].1 > 0.0);
        // inst_a delta (200) is 4x inst_b delta (50)
        assert!(rated[&inst_a].1 > rated[&inst_b].1);
    }

    #[test]
    fn test_compute_rates_negative_delta_returns_zero() {
        let mut distributor = Distributor::new();
        let inst_a = Uuid::new_v4();

        // Cycle 1: bootstrap with high value
        let instances_t0: HashMap<Uuid, InstanceRow> =
            [(inst_a, make_instance_with_jobs(inst_a, None, 100, 500.0))].into();
        let _ = distributor.compute_rates(instances_t0);

        std::thread::sleep(std::time::Duration::from_millis(10));

        // Cycle 2: counter decreased (e.g. reset)
        let instances_t1: HashMap<Uuid, InstanceRow> =
            [(inst_a, make_instance_with_jobs(inst_a, None, 100, 100.0))].into();
        let rated = distributor.compute_rates(instances_t1);

        assert_eq!(rated[&inst_a].1, 0.0);
    }

    #[test]
    fn test_compute_rates_feeds_distribution() {
        let mut distributor = Distributor::new();
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();

        let clusters: Vec<Cluster> = (0..6)
            .map(|i| make_cluster(facility, show, &format!("rate_tag{}", i)))
            .collect();

        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();

        // Cycle 1: bootstrap
        let instances_t0: HashMap<Uuid, InstanceRow> = [
            (inst_a, make_instance_with_jobs(inst_a, None, 100, 0.0)),
            (inst_b, make_instance_with_jobs(inst_b, None, 100, 0.0)),
        ]
        .into();
        let _ = distributor.compute_rates(instances_t0);

        std::thread::sleep(std::time::Duration::from_millis(10));

        // Cycle 2: inst_a is much busier than inst_b
        let instances_t1: HashMap<Uuid, InstanceRow> = [
            (inst_a, make_instance_with_jobs(inst_a, None, 100, 1000.0)),
            (inst_b, make_instance_with_jobs(inst_b, None, 100, 100.0)),
        ]
        .into();
        let rated = distributor.compute_rates(instances_t1);

        // Rates should reflect that inst_a is busier
        assert!(rated[&inst_a].1 > rated[&inst_b].1);

        // Use computed rated instances in assignment (no prior assignments)
        let current_map = HashMap::new();
        let assignments = Distributor::compute_assignments(&clusters, &rated, &current_map);

        assert_eq!(assignments.len(), 6);

        let count_a = assignments.values().filter(|&&v| v == inst_a).count();
        let count_b = assignments.values().filter(|&&v| v == inst_b).count();

        // The less busy instance (inst_b) should get more clusters
        assert!(
            count_b > count_a,
            "inst_b (less busy) should get more clusters: count_a={}, count_b={}",
            count_a,
            count_b
        );
    }

    #[test]
    fn test_ttl_expiration_enables_redistribution() {
        use std::time::{Duration, Instant};

        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();

        let clusters: Vec<Cluster> = (0..6)
            .map(|i| make_cluster(facility, show, &format!("ttl_tag{}", i)))
            .collect();

        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();

        // All clusters assigned to inst_a
        let current_map: HashMap<String, Uuid> =
            clusters.iter().map(|c| (c.id.clone(), inst_a)).collect();

        let mut distributor = Distributor::new();

        // Seed ages with a timestamp far in the past (expired)
        let expired_time = Instant::now() - Duration::from_secs(300);
        for cluster in &clusters {
            distributor
                .assignment_ages
                .insert(cluster.id.clone(), expired_time);
        }

        // Filter out expired assignments (simulating what distribute() does)
        let assignment_ttl = Duration::from_secs(120);
        let now = Instant::now();
        let active_assignments: HashMap<String, Uuid> = current_map
            .iter()
            .filter(
                |(cluster_id, _)| match distributor.assignment_ages.get(*cluster_id) {
                    Some(created_at) => now.duration_since(*created_at) < assignment_ttl,
                    None => true,
                },
            )
            .map(|(k, v)| (k.clone(), *v))
            .collect();

        // All assignments should be expired
        assert!(
            active_assignments.is_empty(),
            "All assignments should have expired"
        );

        // Now compute_assignments with both instances and no active assignments
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (inst_a, (make_instance(inst_a, None, 100), 0.0)),
            (inst_b, (make_instance(inst_b, None, 100), 0.0)),
        ]
        .into();

        let assignments =
            Distributor::compute_assignments(&clusters, &rated_instances, &active_assignments);

        assert_eq!(assignments.len(), 6);

        // With no active assignments, clusters should be evenly distributed
        let count_a = assignments.values().filter(|&&v| v == inst_a).count();
        let count_b = assignments.values().filter(|&&v| v == inst_b).count();
        assert_eq!(count_a, 3);
        assert_eq!(count_b, 3);
    }

    #[test]
    fn test_seed_ages_gives_grace_period() {
        use std::time::{Duration, Instant};

        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();

        let clusters: Vec<Cluster> = (0..4)
            .map(|i| make_cluster(facility, show, &format!("seed_tag{}", i)))
            .collect();

        let inst_a = Uuid::new_v4();

        // Simulate existing DB assignments
        let current_assignments: HashMap<String, Uuid> =
            clusters.iter().map(|c| (c.id.clone(), inst_a)).collect();

        let mut distributor = Distributor::new();
        distributor.seed_ages(&current_assignments);

        // Verify all ages were seeded
        assert_eq!(distributor.assignment_ages.len(), clusters.len());

        // Verify none are expired (they should be very recent)
        let assignment_ttl = Duration::from_secs(120);
        let now = Instant::now();
        for (cluster_id, created_at) in &distributor.assignment_ages {
            let age = now.duration_since(*created_at);
            assert!(
                age < assignment_ttl,
                "Seeded assignment for {} should not be expired (age: {:?})",
                cluster_id,
                age
            );
        }

        // Filtering should keep all assignments active
        let active_assignments: HashMap<String, Uuid> = current_assignments
            .iter()
            .filter(
                |(cluster_id, _)| match distributor.assignment_ages.get(*cluster_id) {
                    Some(created_at) => now.duration_since(*created_at) < assignment_ttl,
                    None => true,
                },
            )
            .map(|(k, v)| (k.clone(), *v))
            .collect();

        assert_eq!(
            active_assignments.len(),
            current_assignments.len(),
            "All seeded assignments should remain active"
        );
    }

    #[test]
    fn test_assignment_ages_updated_after_reassignment() {
        use std::time::{Duration, Instant};

        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();

        let clusters: Vec<Cluster> = (0..4)
            .map(|i| make_cluster(facility, show, &format!("age_tag{}", i)))
            .collect();

        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();

        let mut distributor = Distributor::new();

        // Simulate: 2 clusters assigned to inst_a, 2 expired (will go through second pass)
        let expired_time = Instant::now() - Duration::from_secs(300);
        let fresh_time = Instant::now();

        // First 2 clusters are expired, last 2 are fresh
        distributor
            .assignment_ages
            .insert(clusters[0].id.clone(), expired_time);
        distributor
            .assignment_ages
            .insert(clusters[1].id.clone(), expired_time);
        distributor
            .assignment_ages
            .insert(clusters[2].id.clone(), fresh_time);
        distributor
            .assignment_ages
            .insert(clusters[3].id.clone(), fresh_time);

        // All currently assigned to inst_a
        let current_map: HashMap<String, Uuid> =
            clusters.iter().map(|c| (c.id.clone(), inst_a)).collect();

        // Filter expired
        let assignment_ttl = Duration::from_secs(120);
        let now = Instant::now();
        let active_assignments: HashMap<String, Uuid> = current_map
            .iter()
            .filter(
                |(cluster_id, _)| match distributor.assignment_ages.get(*cluster_id) {
                    Some(created_at) => now.duration_since(*created_at) < assignment_ttl,
                    None => true,
                },
            )
            .map(|(k, v)| (k.clone(), *v))
            .collect();

        // Only 2 fresh assignments should remain
        assert_eq!(active_assignments.len(), 2);

        // Compute assignments with 2 instances
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (inst_a, (make_instance(inst_a, None, 100), 0.0)),
            (inst_b, (make_instance(inst_b, None, 100), 0.0)),
        ]
        .into();

        let assignments =
            Distributor::compute_assignments(&clusters, &rated_instances, &active_assignments);

        // All 4 should be assigned
        assert_eq!(assignments.len(), 4);

        // The 2 fresh clusters stay with inst_a, the 2 expired ones get redistributed
        assert_eq!(assignments[&clusters[2].id], inst_a);
        assert_eq!(assignments[&clusters[3].id], inst_a);
    }

    // --- is_facility_eligible unit tests ---

    #[test]
    fn test_facility_eligible_matching_facility() {
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();
        let cluster = make_cluster(facility, show, "tag");
        let instance_id = Uuid::new_v4();

        let facilities = HashMap::from([(instance_id, InstanceFacility {
            name: Some(facility.to_string()),
            id: Some(facility),
        })]);

        assert!(Distributor::is_facility_eligible(&cluster, &facilities, instance_id));
    }

    #[test]
    fn test_facility_eligible_mismatched_facility() {
        let facility_a = Uuid::new_v4();
        let facility_b = Uuid::new_v4();
        let show = Uuid::new_v4();
        let cluster = make_cluster(facility_a, show, "tag");
        let instance_id = Uuid::new_v4();

        let facilities = HashMap::from([(instance_id, InstanceFacility {
            name: Some(facility_b.to_string()),
            id: Some(facility_b),
        })]);

        assert!(!Distributor::is_facility_eligible(&cluster, &facilities, instance_id));
    }

    #[test]
    fn test_facility_eligible_unscoped_instance_accepts_all() {
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();
        let cluster = make_cluster(facility, show, "tag");
        let instance_id = Uuid::new_v4();

        let facilities = HashMap::from([(instance_id, InstanceFacility {
            name: None,
            id: None,
        })]);

        assert!(Distributor::is_facility_eligible(&cluster, &facilities, instance_id));
    }

    #[test]
    fn test_facility_eligible_unresolved_name_rejects() {
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();
        let cluster = make_cluster(facility, show, "tag");
        let instance_id = Uuid::new_v4();

        // Instance has a facility name but it didn't resolve to a UUID
        let facilities = HashMap::from([(instance_id, InstanceFacility {
            name: Some("nonexistent".to_string()),
            id: None,
        })]);

        assert!(!Distributor::is_facility_eligible(&cluster, &facilities, instance_id));
    }

    // --- compute_assignments facility tests ---

    fn make_instance_unresolved_facility(id: Uuid, name: &str, capacity: i32) -> InstanceRow {
        InstanceRow {
            pk_instance: id,
            str_name: format!("test:{}", id),
            str_facility_id: None,
            str_facility: Some(name.to_string()),
            int_capacity: capacity,
            float_jobs_queried: 0.0,
            b_draining: false,
        }
    }

    #[test]
    fn test_facility_scoped_instances_no_cross_assignment() {
        let facility_a = Uuid::new_v4();
        let facility_b = Uuid::new_v4();
        let show = Uuid::new_v4();

        // 3 clusters per facility
        let clusters_a: Vec<Cluster> = (0..3)
            .map(|i| make_cluster(facility_a, show, &format!("a_tag{}", i)))
            .collect();
        let clusters_b: Vec<Cluster> = (0..3)
            .map(|i| make_cluster(facility_b, show, &format!("b_tag{}", i)))
            .collect();
        let all_clusters: Vec<Cluster> = clusters_a.iter().chain(&clusters_b).cloned().collect();

        let inst_a = Uuid::new_v4();
        let inst_b = Uuid::new_v4();
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (inst_a, (make_instance(inst_a, Some(facility_a), 100), 0.0)),
            (inst_b, (make_instance(inst_b, Some(facility_b), 100), 0.0)),
        ]
        .into();

        let assignments =
            Distributor::compute_assignments(&all_clusters, &rated_instances, &HashMap::new());

        assert_eq!(assignments.len(), 6);

        // facility_a clusters must go to inst_a, facility_b clusters to inst_b
        for c in &clusters_a {
            assert_eq!(
                assignments[&c.id], inst_a,
                "Cluster {} (facility_a) should be on inst_a",
                c.id
            );
        }
        for c in &clusters_b {
            assert_eq!(
                assignments[&c.id], inst_b,
                "Cluster {} (facility_b) should be on inst_b",
                c.id
            );
        }
    }

    #[test]
    fn test_unresolved_facility_instance_gets_no_clusters() {
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();

        let clusters: Vec<Cluster> = (0..4)
            .map(|i| make_cluster(facility, show, &format!("tag{}", i)))
            .collect();

        let inst_good = Uuid::new_v4();
        let inst_bad = Uuid::new_v4();
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (inst_good, (make_instance(inst_good, None, 100), 0.0)),
            (
                inst_bad,
                (make_instance_unresolved_facility(inst_bad, "bogus", 100), 0.0),
            ),
        ]
        .into();

        let assignments =
            Distributor::compute_assignments(&clusters, &rated_instances, &HashMap::new());

        // All clusters should go to inst_good; inst_bad has an unresolved facility
        assert_eq!(assignments.len(), 4);
        for id in assignments.values() {
            assert_eq!(*id, inst_good);
        }
    }

    #[test]
    fn test_mixed_scoped_and_unscoped_instances() {
        let facility_a = Uuid::new_v4();
        let facility_b = Uuid::new_v4();
        let show = Uuid::new_v4();

        let cluster_a = make_cluster(facility_a, show, "tag_a");
        let cluster_b = make_cluster(facility_b, show, "tag_b");
        let clusters = vec![cluster_a.clone(), cluster_b.clone()];

        // inst_scoped only handles facility_a, inst_unscoped handles anything
        let inst_scoped = Uuid::new_v4();
        let inst_unscoped = Uuid::new_v4();
        let rated_instances: HashMap<Uuid, (InstanceRow, f64)> = [
            (inst_scoped, (make_instance(inst_scoped, Some(facility_a), 100), 0.0)),
            (inst_unscoped, (make_instance(inst_unscoped, None, 100), 0.0)),
        ]
        .into();

        let assignments =
            Distributor::compute_assignments(&clusters, &rated_instances, &HashMap::new());

        assert_eq!(assignments.len(), 2);
        // cluster_a can go to either (both are eligible), but cluster_b can only go to unscoped
        assert_eq!(assignments[&cluster_b.id], inst_unscoped);
    }
}
