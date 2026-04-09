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
    use std::sync::Arc;
    use std::time::Duration;

    use scheduler::orchestrator::dao::OrchestratorDao;
    use scheduler::orchestrator::instance::InstanceManager;
    use scheduler::orchestrator::leader::LeaderElection;
    use serial_test::serial;
    use tokio::sync::watch;

    use crate::embedded_db::create_test_db;

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
}
