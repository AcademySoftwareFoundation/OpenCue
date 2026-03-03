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

use miette::{IntoDiagnostic, Result};
use tracing::{debug, info, warn};
use uuid::Uuid;

use crate::cluster::{Cluster, ClusterFeed};
use crate::dao::helpers::parse_uuid;

use super::dao::{InstanceRow, OrchestratorDao};

/// Snapshot of an instance's jobs_queried value at a point in time,
/// used to compute the rate between distribution cycles.
struct RateSnapshot {
    jobs_queried: f64,
    timestamp: Instant,
}

/// The distributor runs on the leader instance. It loads all clusters from the database,
/// reads live instances, computes load rates, and assigns clusters to instances.
pub struct Distributor {
    /// Previous snapshots of each instance's jobs_queried counter, keyed by instance ID.
    previous_snapshots: HashMap<Uuid, RateSnapshot>,
}

impl Distributor {
    /// Creates a new distributor with empty rate snapshots.
    ///
    /// The first distribution cycle will use count-based balancing since no
    /// previous rate data is available.
    pub fn new() -> Self {
        Distributor {
            previous_snapshots: HashMap::new(),
        }
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
        // 1. Clean up dead instances (cascade deletes their assignments)
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

        // 2. Load all clusters from the database
        let all_clusters = ClusterFeed::load_clusters(None, ignore_tags, None).await?;
        let all_clusters = ClusterFeed::filter_clusters(all_clusters, ignore_tags);

        if all_clusters.is_empty() {
            debug!("No clusters found in database");
            return Ok(());
        }

        // 3. Read live instances
        let instances = dao
            .get_live_instances(failure_threshold)
            .await
            .into_diagnostic()?;

        if instances.is_empty() {
            warn!("No live instances available for cluster distribution");
            return Ok(());
        }

        // 4. Read current assignments
        let current_assignments = dao.get_all_assignments().await.into_diagnostic()?;

        // Build a map: cluster_json -> currently assigned instance_id
        let mut current_map: HashMap<String, Uuid> = HashMap::new();
        for assignment in &current_assignments {
            current_map.insert(
                assignment.str_cluster.clone(),
                parse_uuid(&assignment.pk_instance),
            );
        }

        // Build set of live instance IDs for quick lookup
        let live_ids: std::collections::HashSet<Uuid> = instances
            .iter()
            .map(|i| parse_uuid(&i.pk_instance))
            .collect();

        // 5. Compute job query rates per instance
        let now = Instant::now();
        let rates = self.compute_rates(&instances, now);

        // 6. Compute new assignments
        let new_assignments =
            Self::compute_assignments(&all_clusters, &instances, &current_map, &live_ids, &rates);

        // 7. Apply assignment changes to the database
        self.apply_assignments(dao, &all_clusters, &new_assignments, &current_map)
            .await?;

        // 8. Update snapshots for next cycle
        for instance in &instances {
            self.previous_snapshots.insert(
                parse_uuid(&instance.pk_instance),
                RateSnapshot {
                    jobs_queried: instance.float_jobs_queried,
                    timestamp: now,
                },
            );
        }

        // 9. Update metrics
        crate::metrics::set_orchestrator_instances_alive(instances.len());
        crate::metrics::increment_orchestrator_rebalance();

        debug!(
            "Distribution complete: {} clusters across {} instances",
            all_clusters.len(),
            instances.len()
        );

        Ok(())
    }

    /// Computes the job query rate for each instance based on the delta from previous snapshots.
    /// Returns a map of instance_id -> rate (jobs/second).
    /// If no previous snapshot exists (bootstrap), rate is 0.0.
    fn compute_rates(&self, instances: &[InstanceRow], now: Instant) -> HashMap<Uuid, f64> {
        let mut rates = HashMap::new();

        for instance in instances {
            let id = parse_uuid(&instance.pk_instance);
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

            rates.insert(id, rate);
        }

        rates
    }

    /// Pure function that computes the optimal cluster-to-instance assignment.
    ///
    /// Strategy:
    /// 1. Preserve stable assignments (cluster stays on same live instance if eligible).
    /// 2. Assign unassigned clusters to the instance with the lowest load ratio.
    fn compute_assignments(
        all_clusters: &[Cluster],
        instances: &[InstanceRow],
        current_map: &HashMap<String, Uuid>,
        live_ids: &std::collections::HashSet<Uuid>,
        rates: &HashMap<Uuid, f64>,
    ) -> HashMap<String, Uuid> {
        let mut assignments: HashMap<String, Uuid> = HashMap::new();

        // Parse instance IDs once
        let instance_ids: Vec<Uuid> = instances
            .iter()
            .map(|i| parse_uuid(&i.pk_instance))
            .collect();

        // Track load per instance (weighted by rate / capacity)
        let mut instance_load: HashMap<Uuid, f64> = instance_ids
            .iter()
            .map(|id| (*id, *rates.get(id).unwrap_or(&0.0)))
            .collect();

        // Track assignment count per instance for bootstrap (when all rates are 0)
        let mut instance_count: HashMap<Uuid, usize> =
            instance_ids.iter().map(|id| (*id, 0)).collect();

        let all_rates_zero = rates.values().all(|r| *r == 0.0);

        // Build instance capacity map
        let capacity_map: HashMap<Uuid, f64> = instances
            .iter()
            .zip(instance_ids.iter())
            .map(|(i, id)| (*id, i.int_capacity as f64))
            .collect();

        // Build facility map for affinity filtering
        let instance_facilities: HashMap<Uuid, Option<String>> = instances
            .iter()
            .zip(instance_ids.iter())
            .map(|(i, id)| (*id, i.str_facility.clone()))
            .collect();

        // First pass: preserve stable assignments
        for cluster in all_clusters {
            let cluster_json = serde_json::to_string(cluster).expect("Failed to serialize Cluster");

            if let Some(&current_instance) = current_map.get(&cluster_json) {
                if live_ids.contains(&current_instance)
                    && Self::is_facility_eligible(cluster, &instance_facilities, current_instance)
                {
                    assignments.insert(cluster_json, current_instance);
                    if let Some(count) = instance_count.get_mut(&current_instance) {
                        *count += 1;
                    }
                }
            }
        }

        // Second pass: assign unassigned clusters
        for cluster in all_clusters {
            let cluster_json = serde_json::to_string(cluster).expect("Failed to serialize Cluster");

            if assignments.contains_key(&cluster_json) {
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

            // Pick the instance with the lowest load
            let best = if all_rates_zero {
                // Bootstrap: distribute by count / capacity
                *eligible
                    .iter()
                    .min_by(|a, b| {
                        let ratio_a = *instance_count.get(a).unwrap_or(&0) as f64
                            / capacity_map.get(a).unwrap_or(&1.0);
                        let ratio_b = *instance_count.get(b).unwrap_or(&0) as f64
                            / capacity_map.get(b).unwrap_or(&1.0);
                        ratio_a
                            .partial_cmp(&ratio_b)
                            .unwrap_or(std::cmp::Ordering::Equal)
                    })
                    .unwrap()
            } else {
                // Rate-based: pick instance with lowest rate/capacity ratio
                *eligible
                    .iter()
                    .min_by(|a, b| {
                        let ratio_a = instance_load.get(a).unwrap_or(&0.0)
                            / capacity_map.get(a).unwrap_or(&1.0);
                        let ratio_b = instance_load.get(b).unwrap_or(&0.0)
                            / capacity_map.get(b).unwrap_or(&1.0);
                        ratio_a
                            .partial_cmp(&ratio_b)
                            .unwrap_or(std::cmp::Ordering::Equal)
                    })
                    .unwrap()
            };

            assignments.insert(cluster_json, best);
            if let Some(count) = instance_count.get_mut(&best) {
                *count += 1;
            }
            // For rate-based distribution, slightly increase load estimate for
            // subsequent assignments within the same cycle
            if let Some(load) = instance_load.get_mut(&best) {
                *load += 1.0;
            }
        }

        assignments
    }

    /// Checks whether a cluster is eligible to run on a given instance based on facility.
    fn is_facility_eligible(
        cluster: &Cluster,
        instance_facilities: &HashMap<Uuid, Option<String>>,
        instance_id: Uuid,
    ) -> bool {
        match instance_facilities.get(&instance_id) {
            Some(Some(facility)) => {
                // Instance is scoped to a facility — cluster must match
                cluster.facility_id.to_string().to_lowercase() == facility.to_lowercase()
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
            let cluster_json = serde_json::to_string(cluster).expect("Failed to serialize Cluster");

            if let Some(&new_instance) = new_assignments.get(&cluster_json) {
                let needs_upsert = match current_map.get(&cluster_json) {
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

        // Delete assignments for clusters that no longer exist in the database
        for cluster_json in current_map.keys() {
            if !new_assignments.contains_key(cluster_json) {
                // This cluster no longer exists — try to parse and delete
                if let Ok(cluster) = serde_json::from_str::<Cluster>(cluster_json) {
                    dao.delete_assignment_by_cluster(&cluster)
                        .await
                        .into_diagnostic()?;
                    debug!("Removed stale assignment for cluster {}", cluster);
                }
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use std::collections::{HashMap, HashSet};

    use uuid::Uuid;

    use crate::cluster::Cluster;
    use crate::cluster_key::{Tag, TagType};
    use crate::dao::helpers::parse_uuid;

    use super::{Distributor, InstanceRow};

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

    fn make_instance(id: Uuid, facility: Option<&str>, capacity: i32) -> InstanceRow {
        InstanceRow {
            pk_instance: id.to_string(),
            str_name: format!("test:{}", id),
            str_facility: facility.map(String::from),
            int_capacity: capacity,
            float_jobs_queried: 0.0,
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
        let instances = vec![
            make_instance(inst_a, None, 100),
            make_instance(inst_b, None, 100),
        ];

        let live_ids: HashSet<Uuid> = instances
            .iter()
            .map(|i| parse_uuid(&i.pk_instance))
            .collect();
        let rates: HashMap<Uuid, f64> = instances
            .iter()
            .map(|i| (parse_uuid(&i.pk_instance), 0.0))
            .collect();
        let current_map = HashMap::new();

        let assignments = Distributor::compute_assignments(
            &clusters,
            &instances,
            &current_map,
            &live_ids,
            &rates,
        );

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
        let instances = vec![
            make_instance(inst_a, None, 100),
            make_instance(inst_b, None, 100),
        ];

        let live_ids: HashSet<Uuid> = instances
            .iter()
            .map(|i| parse_uuid(&i.pk_instance))
            .collect();
        let rates: HashMap<Uuid, f64> = vec![(inst_a, 100.0), (inst_b, 50.0)].into_iter().collect();

        // Pre-assign all clusters to inst_a
        let current_map: HashMap<String, Uuid> = clusters
            .iter()
            .map(|c| (serde_json::to_string(c).unwrap(), inst_a))
            .collect();

        let assignments = Distributor::compute_assignments(
            &clusters,
            &instances,
            &current_map,
            &live_ids,
            &rates,
        );

        // All clusters should stay with inst_a (stability)
        for (_, instance) in &assignments {
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
        let instances = vec![
            make_instance(inst_a, Some(&facility_a.to_string()), 100),
            make_instance(inst_b, Some(&facility_b.to_string()), 100),
        ];

        let live_ids: HashSet<Uuid> = instances
            .iter()
            .map(|i| parse_uuid(&i.pk_instance))
            .collect();
        let rates: HashMap<Uuid, f64> = instances
            .iter()
            .map(|i| (parse_uuid(&i.pk_instance), 0.0))
            .collect();
        let current_map = HashMap::new();

        let assignments = Distributor::compute_assignments(
            &clusters,
            &instances,
            &current_map,
            &live_ids,
            &rates,
        );

        let cluster_a_json = serde_json::to_string(&cluster_a).unwrap();
        let cluster_b_json = serde_json::to_string(&cluster_b).unwrap();

        assert_eq!(assignments[&cluster_a_json], inst_a);
        assert_eq!(assignments[&cluster_b_json], inst_b);
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
        let instances = vec![
            make_instance(inst_a, None, 200), // 2x capacity
            make_instance(inst_b, None, 100),
        ];

        let live_ids: HashSet<Uuid> = instances
            .iter()
            .map(|i| parse_uuid(&i.pk_instance))
            .collect();
        let rates: HashMap<Uuid, f64> = instances
            .iter()
            .map(|i| (parse_uuid(&i.pk_instance), 0.0))
            .collect();
        let current_map = HashMap::new();

        let assignments = Distributor::compute_assignments(
            &clusters,
            &instances,
            &current_map,
            &live_ids,
            &rates,
        );

        let count_a = assignments.values().filter(|&&v| v == inst_a).count();
        let count_b = assignments.values().filter(|&&v| v == inst_b).count();

        // inst_a should get ~6, inst_b should get ~3 (2:1 ratio)
        assert_eq!(count_a, 6);
        assert_eq!(count_b, 3);
    }
}
