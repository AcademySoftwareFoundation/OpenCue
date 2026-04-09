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

mod embedded_db;

#[cfg(all(test, feature = "integration-tests"))]
mod orchestration_tests {
    use std::collections::HashMap;
    use std::sync::Arc;
    use std::time::Duration;

    use scheduler::cluster::Cluster;
    use scheduler::cluster_key::{Tag, TagType};
    use scheduler::orchestrator::dao::{InstanceRow, OrchestratorDao};
    use scheduler::orchestrator::distributor::Distributor;
    use scheduler::orchestrator::instance::InstanceManager;
    use scheduler::orchestrator::leader::LeaderElection;
    use serial_test::serial;
    use tokio::sync::watch;
    use uuid::Uuid;

    use crate::embedded_db::create_test_db;

    /// Creates `count` test clusters sharing the same facility and show.
    fn make_test_clusters(count: usize) -> (Uuid, Uuid, Vec<Cluster>) {
        let facility = Uuid::new_v4();
        let show = Uuid::new_v4();
        let clusters = (0..count)
            .map(|i| {
                Cluster::single_tag(
                    facility,
                    show,
                    Tag {
                        name: format!("tag{}", i),
                        ttype: TagType::Alloc,
                    },
                )
            })
            .collect();
        (facility, show, clusters)
    }

    /// Wraps DAO instance rows into rated instances with rate 0.0 (bootstrap).
    fn rated_instances_from_dao(
        instances: HashMap<Uuid, InstanceRow>,
    ) -> HashMap<Uuid, (InstanceRow, f64)> {
        instances
            .into_iter()
            .map(|(id, row)| (id, (row, 0.0)))
            .collect()
    }

    /// Well-known advisory lock ID for the orchestrator leader (same as production).
    const ORCHESTRATOR_LOCK_ID: i64 = 0x4F70656E437565;

    // ── Test 1: Instance registration and heartbeat ──────────────────────

    #[tokio::test]
    async fn test_instance_register_and_heartbeat() {
        let (pool, url) = create_test_db("register").await;

        let dao = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));
        let mgr = InstanceManager::with_dao(dao.clone(), None, 100);
        mgr.register().await.expect("register should succeed");

        // Verify the instance is visible
        let instances = dao
            .get_live_instances(Duration::from_secs(30))
            .await
            .expect("get_live_instances should succeed");
        assert_eq!(instances.len(), 1);
        assert!(instances.contains_key(&mgr.instance_id));

        // Update heartbeat with a counter value
        dao.update_heartbeat(mgr.instance_id, 42.0)
            .await
            .expect("update_heartbeat should succeed");

        let instances = dao
            .get_live_instances(Duration::from_secs(30))
            .await
            .expect("get_live_instances should succeed");
        let row = &instances[&mgr.instance_id];
        assert!((row.float_jobs_queried - 42.0).abs() < f64::EPSILON);
    }

    // ── Test 2: Leader election with advisory locks ──────────────────────

    #[tokio::test]
    #[serial]
    async fn test_leader_election_advisory_locks() {
        let (pool, url) = create_test_db("leader").await;

        // Two DAOs, each with their own dedicated leader connection
        let dao1 = Arc::new(OrchestratorDao::with_pool(pool.clone(), url.clone()));
        let dao2 = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        // Instance 1 acquires the lock
        let acquired = dao1
            .try_acquire_leader_lock(ORCHESTRATOR_LOCK_ID)
            .await
            .expect("lock attempt should not error");
        assert!(acquired, "first instance should acquire the lock");

        // Instance 2 cannot acquire it
        let acquired = dao2
            .try_acquire_leader_lock(ORCHESTRATOR_LOCK_ID)
            .await
            .expect("lock attempt should not error");
        assert!(!acquired, "second instance should NOT acquire the lock");

        // Instance 1 releases the lock
        dao1.release_leader_lock().await;

        // Now instance 2 can acquire it
        let acquired = dao2
            .try_acquire_leader_lock(ORCHESTRATOR_LOCK_ID)
            .await
            .expect("lock attempt should not error");
        assert!(acquired, "second instance should acquire the lock after release");

        dao2.release_leader_lock().await;
    }

    // ── Test 3: Instance deregistration ──────────────────────────────────

    #[tokio::test]
    async fn test_instance_deregistration() {
        let (pool, url) = create_test_db("deregister").await;

        let dao = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));
        let mgr = InstanceManager::with_dao(dao.clone(), Some("test-facility".to_string()), 100);
        mgr.register().await.expect("register should succeed");

        // Verify it exists
        let instances = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert_eq!(instances.len(), 1);

        // Graceful shutdown removes it
        mgr.shutdown().await;

        let instances = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert_eq!(instances.len(), 0);
    }

    // ── Test 4: Multiple instances with different capacities ─────────────

    #[tokio::test]
    async fn test_multiple_instances() {
        let (pool, url) = create_test_db("multi_instance").await;

        let dao = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        let mgr1 = InstanceManager::with_dao(dao.clone(), None, 100);
        let mgr2 = InstanceManager::with_dao(dao.clone(), None, 200);
        let mgr3 = InstanceManager::with_dao(dao.clone(), Some("facility-a".to_string()), 50);

        mgr1.register().await.unwrap();
        mgr2.register().await.unwrap();
        mgr3.register().await.unwrap();

        let instances = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert_eq!(instances.len(), 3);

        // Verify capacities
        assert_eq!(instances[&mgr1.instance_id].int_capacity, 100);
        assert_eq!(instances[&mgr2.instance_id].int_capacity, 200);
        assert_eq!(instances[&mgr3.instance_id].int_capacity, 50);

        // Remove one
        mgr2.shutdown().await;
        let instances = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert_eq!(instances.len(), 2);
        assert!(!instances.contains_key(&mgr2.instance_id));
    }

    // ── Test 5: Leader election loop (live async) ────────────────────────

    #[tokio::test]
    #[serial]
    async fn test_leader_election_loop() {
        let (pool, url) = create_test_db("election_loop").await;

        let dao1 = Arc::new(OrchestratorDao::with_pool(pool.clone(), url.clone()));
        let dao2 = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        let election1 = LeaderElection::new(dao1.clone());
        let election2 = LeaderElection::new(dao2.clone());

        let (_shutdown_tx, shutdown_rx) = watch::channel(false);

        let handle1 = election1.start(vec![], shutdown_rx.clone());
        let handle2 = election2.start(vec![], shutdown_rx.clone());

        // Wait for election to settle — with CONFIG defaults or fast overrides
        tokio::time::sleep(Duration::from_secs(15)).await;

        // Exactly one should be leader
        let leader1 = election1.is_leader();
        let leader2 = election2.is_leader();
        assert!(
            leader1 ^ leader2,
            "Exactly one instance should be leader, got: election1={}, election2={}",
            leader1, leader2
        );

        // Shutdown
        let _ = _shutdown_tx.send(true);
        let _ = tokio::time::timeout(Duration::from_secs(5), handle1).await;
        let _ = tokio::time::timeout(Duration::from_secs(5), handle2).await;
    }

    // ── Test 6: Cluster assignment round-trip ────────────────────────────

    #[tokio::test]
    async fn test_cluster_assignment_round_trip() {
        use scheduler::cluster::Cluster;
        use scheduler::cluster_key::{Tag, TagType};

        let (pool, url) = create_test_db("assignments").await;

        let dao = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        // Register an instance
        let mgr = InstanceManager::with_dao(dao.clone(), None, 100);
        mgr.register().await.unwrap();

        // Create a test cluster
        let cluster = Cluster::single_tag(
            uuid::Uuid::new_v4(),
            uuid::Uuid::new_v4(),
            Tag {
                name: "general".to_string(),
                ttype: TagType::Alloc,
            },
        );

        // Assign cluster to instance
        dao.upsert_assignment(mgr.instance_id, &cluster)
            .await
            .expect("upsert_assignment should succeed");

        // Read back assignments
        let assignments = dao
            .get_assignments_for_instance(mgr.instance_id)
            .await
            .expect("get_assignments should succeed");
        assert_eq!(assignments.len(), 1);
        assert_eq!(assignments[0].str_cluster_id, cluster.id);

        // Read all assignments
        let all = dao.get_all_assignments().await.unwrap();
        assert_eq!(all.len(), 1);
        assert_eq!(all[&cluster.id], mgr.instance_id);

        // Delete assignment
        dao.delete_assignment_by_cluster_id(&cluster.id)
            .await
            .unwrap();
        let all = dao.get_all_assignments().await.unwrap();
        assert!(all.is_empty());
    }

    // ── Test 7: Dead instance cleanup ────────────────────────────────────

    #[tokio::test]
    async fn test_dead_instance_cleanup() {
        let (pool, url) = create_test_db("dead_cleanup").await;
        let dao = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        // Register instance
        let mgr = InstanceManager::with_dao(dao.clone(), None, 100);
        mgr.register().await.unwrap();

        // With a 30s threshold, the just-registered instance should be alive
        let dead = dao.delete_dead_instances(Duration::from_secs(30)).await.unwrap();
        assert!(dead.is_empty());

        // With a 0s threshold, everything is "dead"
        let dead = dao.delete_dead_instances(Duration::from_secs(0)).await.unwrap();
        assert_eq!(dead.len(), 1);
        assert_eq!(dead[0], mgr.instance_id);

        // Instance should be gone now
        let instances = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert!(instances.is_empty());
    }

    // ── Test 8: Cluster redistribution when instance goes offline ────────

    #[tokio::test]
    async fn test_cluster_redistribution_on_instance_offline() {
        let (pool, url) = create_test_db("redistribution").await;
        let dao = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        // Register 3 instances
        let mgr_a = InstanceManager::with_dao(dao.clone(), None, 100);
        let mgr_b = InstanceManager::with_dao(dao.clone(), None, 100);
        let mgr_c = InstanceManager::with_dao(dao.clone(), None, 100);
        mgr_a.register().await.unwrap();
        mgr_b.register().await.unwrap();
        mgr_c.register().await.unwrap();

        // Create 6 clusters and compute initial assignments (2 per instance)
        let (_fac, _show, clusters) = make_test_clusters(6);
        let instances = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        let rated = rated_instances_from_dao(instances);
        let initial_assignments =
            Distributor::compute_assignments(&clusters, &rated, &HashMap::new());

        assert_eq!(initial_assignments.len(), 6);
        let count_a = initial_assignments.values().filter(|&&v| v == mgr_a.instance_id).count();
        let count_b = initial_assignments.values().filter(|&&v| v == mgr_b.instance_id).count();
        let count_c = initial_assignments.values().filter(|&&v| v == mgr_c.instance_id).count();
        assert_eq!(count_a, 2);
        assert_eq!(count_b, 2);
        assert_eq!(count_c, 2);

        // Write assignments to DB
        for cluster in &clusters {
            let inst = initial_assignments[&cluster.id];
            dao.upsert_assignment(inst, cluster).await.unwrap();
        }
        assert_eq!(dao.get_all_assignments().await.unwrap().len(), 6);

        // Simulate instance B going offline (cascade deletes its assignments)
        mgr_b.shutdown().await;

        // Verify: only 4 assignments remain (B's 2 were cascade-deleted)
        let remaining = dao.get_all_assignments().await.unwrap();
        assert_eq!(remaining.len(), 4, "cascade delete should remove B's assignments");
        assert!(
            !remaining.values().any(|&v| v == mgr_b.instance_id),
            "no assignments should reference the dead instance"
        );

        // Re-run distribution with surviving instances
        let surviving = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert_eq!(surviving.len(), 2);
        let rated_surviving = rated_instances_from_dao(surviving);
        let new_assignments =
            Distributor::compute_assignments(&clusters, &rated_surviving, &remaining);

        // All 6 clusters should now be assigned to the 2 surviving instances
        assert_eq!(new_assignments.len(), 6);
        assert!(
            !new_assignments.values().any(|&v| v == mgr_b.instance_id),
            "dead instance should not receive assignments"
        );

        // The 4 stable assignments should remain on their original instances
        for (cluster_id, &original_inst) in &remaining {
            assert_eq!(
                new_assignments[cluster_id], original_inst,
                "stable assignment for {} should not move",
                cluster_id
            );
        }

        // Apply to DB and verify
        for cluster in &clusters {
            let inst = new_assignments[&cluster.id];
            dao.upsert_assignment(inst, cluster).await.unwrap();
        }
        let final_assignments = dao.get_all_assignments().await.unwrap();
        assert_eq!(final_assignments.len(), 6);
    }

    // ── Test 9: Leader reelection when leader goes offline ──────────────

    #[tokio::test]
    #[serial]
    async fn test_leader_reelection_on_leader_offline() {
        let (pool, url) = create_test_db("reelection").await;

        let dao1 = Arc::new(OrchestratorDao::with_pool(pool.clone(), url.clone()));
        let dao2 = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        let election1 = LeaderElection::new(dao1.clone());
        let election2 = LeaderElection::new(dao2.clone());

        let (shutdown_tx, shutdown_rx) = watch::channel(false);

        let handle1 = election1.start(vec![], shutdown_rx.clone());
        let handle2 = election2.start(vec![], shutdown_rx.clone());

        // Wait for initial election to settle
        tokio::time::sleep(Duration::from_secs(15)).await;

        // Exactly one should be leader
        let leader1 = election1.is_leader();
        let leader2 = election2.is_leader();
        assert!(
            leader1 ^ leader2,
            "Exactly one should be leader: e1={}, e2={}",
            leader1, leader2
        );

        // Identify who is leader and simulate their crash by releasing the lock
        let (leader_dao, standby_election) = if leader1 {
            (&dao1, &election2)
        } else {
            (&dao2, &election1)
        };
        leader_dao.release_leader_lock().await;

        // Wait for the standby to detect the free lock and acquire it
        tokio::time::sleep(Duration::from_secs(15)).await;

        assert!(
            standby_election.is_leader(),
            "the standby instance should have become leader after the original leader went offline"
        );

        // Shutdown
        let _ = shutdown_tx.send(true);
        let _ = tokio::time::timeout(Duration::from_secs(5), handle1).await;
        let _ = tokio::time::timeout(Duration::from_secs(5), handle2).await;
    }

    // ── Test 10: Load rebalance when a new instance joins ───────────────

    #[tokio::test]
    async fn test_load_rebalance_on_new_instance_join() {
        let (pool, url) = create_test_db("rebalance_join").await;
        let dao = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        // Start with a single instance holding all clusters
        let mgr_a = InstanceManager::with_dao(dao.clone(), None, 100);
        mgr_a.register().await.unwrap();

        let (_fac, _show, clusters) = make_test_clusters(6);

        // Assign all 6 clusters to instance A
        for cluster in &clusters {
            dao.upsert_assignment(mgr_a.instance_id, cluster).await.unwrap();
        }
        let active_assignments = dao.get_all_assignments().await.unwrap();
        assert_eq!(active_assignments.len(), 6);
        assert!(active_assignments.values().all(|&v| v == mgr_a.instance_id));

        // New instance B joins the cluster
        let mgr_b = InstanceManager::with_dao(dao.clone(), None, 100);
        mgr_b.register().await.unwrap();

        let instances = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert_eq!(instances.len(), 2);
        let rated = rated_instances_from_dao(instances);

        // With active assignments, stability preserves all on A (no migration)
        let stable_assignments =
            Distributor::compute_assignments(&clusters, &rated, &active_assignments);
        assert_eq!(stable_assignments.len(), 6);
        let all_on_a = stable_assignments.values().all(|&v| v == mgr_a.instance_id);
        assert!(
            all_on_a,
            "with active (non-expired) assignments, stability should keep all clusters on A"
        );

        // Simulate TTL expiration: pass empty active_assignments (all expired)
        let after_ttl =
            Distributor::compute_assignments(&clusters, &rated, &HashMap::new());
        assert_eq!(after_ttl.len(), 6);

        let count_a = after_ttl.values().filter(|&&v| v == mgr_a.instance_id).count();
        let count_b = after_ttl.values().filter(|&&v| v == mgr_b.instance_id).count();
        assert_eq!(
            count_a, 3,
            "after TTL expiration, clusters should be evenly distributed (A)"
        );
        assert_eq!(
            count_b, 3,
            "after TTL expiration, clusters should be evenly distributed (B)"
        );

        // Apply the rebalanced assignments to DB
        for cluster in &clusters {
            let inst = after_ttl[&cluster.id];
            dao.upsert_assignment(inst, cluster).await.unwrap();
        }
        let final_assignments = dao.get_all_assignments().await.unwrap();
        assert_eq!(final_assignments.len(), 6);
        let final_a = final_assignments.values().filter(|&&v| v == mgr_a.instance_id).count();
        let final_b = final_assignments.values().filter(|&&v| v == mgr_b.instance_id).count();
        assert_eq!(final_a, 3);
        assert_eq!(final_b, 3);
    }

    // ── Test 11: Fresh start after all nodes become offline ─────────────

    #[tokio::test]
    #[serial]
    async fn test_fresh_start_after_total_failure() {
        let (pool, url) = create_test_db("fresh_start").await;
        let dao = Arc::new(OrchestratorDao::with_pool(pool.clone(), url.clone()));

        // Set up initial cluster: 2 instances with 6 clusters distributed
        let mgr_a = InstanceManager::with_dao(dao.clone(), None, 100);
        let mgr_b = InstanceManager::with_dao(dao.clone(), None, 100);
        mgr_a.register().await.unwrap();
        mgr_b.register().await.unwrap();

        let (_fac, _show, clusters) = make_test_clusters(6);
        let instances = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        let rated = rated_instances_from_dao(instances);
        let initial_assignments =
            Distributor::compute_assignments(&clusters, &rated, &HashMap::new());

        for cluster in &clusters {
            let inst = initial_assignments[&cluster.id];
            dao.upsert_assignment(inst, cluster).await.unwrap();
        }
        assert_eq!(dao.get_all_assignments().await.unwrap().len(), 6);

        // Leader acquires the advisory lock
        let acquired = dao
            .try_acquire_leader_lock(ORCHESTRATOR_LOCK_ID)
            .await
            .expect("lock attempt should not error");
        assert!(acquired, "should acquire leader lock");

        // ── Simulate total failure ──
        // Leader connection drops
        dao.release_leader_lock().await;
        assert!(!dao.is_leader_lock_held().await, "lock should be released");

        // All instances die (0s threshold = everything is dead)
        let dead = dao.delete_dead_instances(Duration::from_secs(0)).await.unwrap();
        assert_eq!(dead.len(), 2, "both instances should be removed");

        // Verify total wipeout
        let live = dao.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert!(live.is_empty(), "no instances should be alive");
        let assignments = dao.get_all_assignments().await.unwrap();
        assert!(assignments.is_empty(), "cascade delete should remove all assignments");

        // ── Fresh start: new instances come online ──
        let dao_new = Arc::new(OrchestratorDao::with_pool(pool.clone(), url));

        // New leader can acquire the lock (it was freed when old leader's connection closed)
        let acquired = dao_new
            .try_acquire_leader_lock(ORCHESTRATOR_LOCK_ID)
            .await
            .expect("lock attempt should not error");
        assert!(acquired, "new instance should acquire the leader lock after total failure");

        // Register fresh instances
        let mgr_c = InstanceManager::with_dao(dao_new.clone(), None, 100);
        let mgr_d = InstanceManager::with_dao(dao_new.clone(), None, 100);
        mgr_c.register().await.unwrap();
        mgr_d.register().await.unwrap();

        let new_instances = dao_new.get_live_instances(Duration::from_secs(30)).await.unwrap();
        assert_eq!(new_instances.len(), 2);

        // Compute fresh assignments from scratch (no prior state)
        let new_rated = rated_instances_from_dao(new_instances);
        let fresh_assignments =
            Distributor::compute_assignments(&clusters, &new_rated, &HashMap::new());

        assert_eq!(fresh_assignments.len(), 6);
        let count_c = fresh_assignments.values().filter(|&&v| v == mgr_c.instance_id).count();
        let count_d = fresh_assignments.values().filter(|&&v| v == mgr_d.instance_id).count();
        assert_eq!(count_c, 3, "fresh distribution should be even (C)");
        assert_eq!(count_d, 3, "fresh distribution should be even (D)");

        // Apply to DB
        for cluster in &clusters {
            let inst = fresh_assignments[&cluster.id];
            dao_new.upsert_assignment(inst, cluster).await.unwrap();
        }
        let final_assignments = dao_new.get_all_assignments().await.unwrap();
        assert_eq!(final_assignments.len(), 6);

        // Cleanup
        dao_new.release_leader_lock().await;
    }
}
