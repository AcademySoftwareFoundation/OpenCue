mod util;
use std::time::Duration;

use scheduler::{
    cluster::{Cluster, ClusterFeed},
    cluster_key::{ClusterKey, Tag, TagType},
    pipeline,
};
use tracing::info;
use tracing_test::traced_test;
use uuid::Uuid;

use crate::util::WaitingFrameClause;

/// Smoke tests to exercice some scenarios
///
/// These tests start from the main service entry points and test the complete flow:
/// 1. Service discovers clusters from the database
/// 2. Service queries jobs from each cluster
/// 3. Service processes job layers and finds host candidates
/// 4. Service dispatches frames to matched hosts in dry run mode
/// 5. Service updates database state appropriately
///
/// # Database Setup
///
/// Tests assume a local PostgreSQL database is running with:
/// - Host: localhost
/// - Port: 5432
/// - Database: cuebot_test
/// - Username: cuebot_test
/// - Password: password
///
/// # Running Integration Tests
///
/// These tests are gated behind the `integration-tests` feature flag and are not
/// run by default with `cargo test`. To run them:
///
/// ```bash
/// # Run all tests including integration tests
/// cargo test --features integration-tests
///
/// # Run only integration tests
/// cargo test --features integration-tests integration_tests_full
/// ```
// #[cfg(all(test, feature = "smoke-tests"))]
mod scheduler_smoke_test {
    use std::sync::Arc;

    use scheduler::{config::OVERRIDE_CONFIG, pgpool::connection_pool};
    use serial_test::serial;
    use sqlx::{Pool, Postgres, Transaction};
    use tokio::time::sleep;
    use tokio_test::assert_ok;

    use crate::util::{create_test_config, get_waiting_frames_count, test_connection_pool};

    use super::*;

    async fn setup_test_database() -> Result<Arc<Pool<Postgres>>, sqlx::Error> {
        let pool = test_connection_pool()
            .await
            .map_err(|e| sqlx::Error::Configuration(e.to_string().into()))?;

        // Force a thorough cleanup before starting
        cleanup_test_data(&pool).await?;

        Ok(pool)
    }

    async fn cleanup_test_data(pool: &Pool<Postgres>) -> Result<(), sqlx::Error> {
        // Use a single transaction for all cleanup operations to ensure atomicity
        let mut tx = pool.begin().await?;

        // Temporarily disable triggers to avoid issues during cleanup
        sqlx::query("SET session_replication_role = 'replica'")
            .execute(&mut *tx)
            .await?;

        // Delete in reverse dependency order - most dependent tables first
        // Use consistent naming patterns and ignore errors for non-existent data

        // Delete job_history records for test jobs first
        let _ = sqlx::query("DELETE FROM job_history WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        let _ = sqlx::query("DELETE FROM frame WHERE str_name LIKE '%integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Delete layer stats and resources
        let _ = sqlx::query("DELETE FROM layer_stat WHERE pk_layer IN (SELECT pk_layer FROM layer WHERE str_name LIKE 'integ_test_%')")
            .execute(&mut *tx)
            .await;
        let _ = sqlx::query("DELETE FROM layer_resource WHERE pk_layer IN (SELECT pk_layer FROM layer WHERE str_name LIKE 'integ_test_%')")
            .execute(&mut *tx)
            .await;

        // Delete layers
        let _ = sqlx::query("DELETE FROM layer WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Delete job stats and resources
        let _ = sqlx::query("DELETE FROM job_stat WHERE pk_job IN (SELECT pk_job FROM job WHERE str_name LIKE 'integ_test_%')")
            .execute(&mut *tx)
            .await;
        let _ = sqlx::query("DELETE FROM job_resource WHERE pk_job IN (SELECT pk_job FROM job WHERE str_name LIKE 'integ_test_%')")
            .execute(&mut *tx)
            .await;

        // Delete jobs
        let _ = sqlx::query("DELETE FROM job WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Delete folder
        let _ = sqlx::query("DELETE FROM folder WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Delete host stats and tags
        let _ = sqlx::query("DELETE FROM host_stat WHERE pk_host IN (SELECT pk_host FROM host WHERE str_name LIKE 'integ_test_%')")
            .execute(&mut *tx)
            .await;
        let _ = sqlx::query("DELETE FROM host_tag WHERE str_tag LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Delete hosts
        let _ = sqlx::query("DELETE FROM host WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Delete subscriptions
        let _ = sqlx::query("DELETE FROM subscription WHERE pk_alloc IN (SELECT pk_alloc FROM alloc WHERE str_name LIKE 'integ_test_%')")
            .execute(&mut *tx)
            .await;

        // Delete allocs
        let _ = sqlx::query("DELETE FROM alloc WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Delete shows
        let _ = sqlx::query("DELETE FROM show WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Delete facilities and departments
        let _ = sqlx::query("DELETE FROM facility WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;
        let _ = sqlx::query("DELETE FROM dept WHERE str_name LIKE 'integ_test_%'")
            .execute(&mut *tx)
            .await;

        // Clean up any orphaned records that might cause constraint violations
        let _ = sqlx::query("DELETE FROM job_stat WHERE pk_job NOT IN (SELECT pk_job FROM job)")
            .execute(&mut *tx)
            .await;
        let _ = sqlx::query(
            "DELETE FROM layer_stat WHERE pk_layer NOT IN (SELECT pk_layer FROM layer)",
        )
        .execute(&mut *tx)
        .await;
        let _ = sqlx::query(
            "DELETE FROM layer_resource WHERE pk_layer NOT IN (SELECT pk_layer FROM layer)",
        )
        .execute(&mut *tx)
        .await;
        let _ =
            sqlx::query("DELETE FROM job_resource WHERE pk_job NOT IN (SELECT pk_job FROM job)")
                .execute(&mut *tx)
                .await;

        // Re-enable triggers
        sqlx::query("SET session_replication_role = 'origin'")
            .execute(&mut *tx)
            .await?;

        // Commit the transaction
        tx.commit().await?;

        Ok(())
    }

    /// Creates comprehensive test data for integration testing with multiple scenarios
    async fn create_test_data(pool: &Pool<Postgres>) -> Result<TestData, sqlx::Error> {
        // Create unique suffix for this test run to avoid conflicts when running tests concurrently
        let test_suffix = Uuid::new_v4().to_string()[..8].to_string();
        // Create basic entities
        let facility_id = Uuid::new_v4();
        let dept_id = Uuid::new_v4();
        let show_id = Uuid::new_v4();

        let mut tx = pool.begin().await?;

        // Create facility
        sqlx::query("INSERT INTO facility (pk_facility, str_name) VALUES ($1, $2)")
            .bind(facility_id.to_string())
            .bind(format!("integ_test_facility_{}", test_suffix))
            .execute(&mut *tx)
            .await?;

        // Create department
        sqlx::query("INSERT INTO dept (pk_dept, str_name) VALUES ($1, $2)")
            .bind(dept_id.to_string())
            .bind(format!("integ_test_dept_{}", test_suffix))
            .execute(&mut *tx)
            .await?;

        // Create show
        sqlx::query("INSERT INTO show (pk_show, str_name) VALUES ($1, $2)")
            .bind(show_id.to_string())
            .bind(format!("integ_test_show_{}", test_suffix))
            .execute(&mut *tx)
            .await?;

        // Create allocations for different tag types
        let hostname_alloc = create_allocation(
            &mut tx,
            facility_id,
            &format!("integ_test_hostname_alloc_{}", test_suffix),
            "HOSTNAME",
        )
        .await?;
        let alloc_alloc = create_allocation(
            &mut tx,
            facility_id,
            &format!("integ_test_alloc_alloc_{}", test_suffix),
            "ALLOC",
        )
        .await?;
        let manual_alloc = create_allocation(
            &mut tx,
            facility_id,
            &format!("integ_test_manual_alloc_{}", test_suffix),
            "MANUAL",
        )
        .await?;

        // Create subscriptions with different resource limits
        create_subscription(&mut tx, hostname_alloc, show_id, 1000, 1200).await?;
        create_subscription(&mut tx, alloc_alloc, show_id, 800, 1000).await?;
        create_subscription(&mut tx, manual_alloc, show_id, 600, 800).await?;

        // Create hosts with different tag types and resource configurations
        let hostname_host = create_host(
            &mut tx,
            hostname_alloc,
            &format!("integ_test_hostname_host_{}", test_suffix),
            16,
            32 * 1024 * 1024,
            4,
            8 * 1024 * 1024,
            vec![(
                &format!("integ_test_hostname_tag_{}", test_suffix),
                "HOSTNAME",
            )],
        )
        .await?;

        let alloc_host = create_host(
            &mut tx,
            alloc_alloc,
            &format!("integ_test_alloc_host_{}", test_suffix),
            12,
            16 * 1024 * 1024,
            2,
            4 * 1024 * 1024,
            vec![(&format!("integ_test_alloc_tag_{}", test_suffix), "ALLOC")],
        )
        .await?;

        let manual_host = create_host(
            &mut tx,
            manual_alloc,
            &format!("integ_test_manual_host_{}", test_suffix),
            8,
            8 * 1024 * 1024,
            1,
            2 * 1024 * 1024,
            vec![(&format!("integ_test_manual_tag_{}", test_suffix), "MANUAL")],
        )
        .await?;

        // Create folder
        let folder_id = create_folder(
            &mut tx,
            show_id,
            dept_id,
            &format!("integ_test_folder_{}", test_suffix),
        )
        .await?;

        tx.commit().await?;

        // Create comprehensive job scenarios
        let hostname_job = create_job_scenario(
            pool,
            show_id,
            facility_id,
            dept_id,
            folder_id,
            &format!("integ_test_hostname_job_{}", test_suffix),
            vec![
                (
                    &format!("integ_test_hostname_layer1_{}", test_suffix),
                    &format!("integ_test_hostname_tag_{}", test_suffix),
                    2,
                    2 * 1024 * 1024,
                    1,
                    1024 * 1024,
                ),
                (
                    &format!("integ_test_hostname_layer2_{}", test_suffix),
                    &format!("integ_test_different_tag{}", test_suffix),
                    4,
                    4 * 1024 * 1024,
                    0,
                    0,
                ),
            ],
            3,
        )
        .await?;

        let alloc_job = create_job_scenario(
            pool,
            show_id,
            facility_id,
            dept_id,
            folder_id,
            &format!("integ_test_alloc_job_{}", test_suffix),
            vec![(
                &format!("integ_test_alloc_layer_{}", test_suffix),
                &format!("integ_test_alloc_tag_{}", test_suffix),
                1,
                1024 * 1024,
                1,
                512 * 1024,
            )],
            3,
        )
        .await?;

        let manual_job = create_job_scenario(
            pool,
            show_id,
            facility_id,
            dept_id,
            folder_id,
            &format!("integ_test_manual_job_{}", test_suffix),
            vec![(
                &format!("integ_test_manual_layer_{}", test_suffix),
                &format!("integ_test_manual_tag_{}", test_suffix),
                1,
                1024 * 1024,
                0,
                0,
            )],
            3,
        )
        .await?;

        // Create a mixed-tag job that requires multiple host types
        let mixed_job = create_job_scenario(
            pool,
            show_id,
            facility_id,
            dept_id,
            folder_id,
            &format!("integ_test_mixed_job_{}", test_suffix),
            vec![
                (
                    &format!("integ_test_mixed_hostname_{}", test_suffix),
                    &format!("integ_test_hostname_tag_{}", test_suffix),
                    1,
                    1024 * 1024,
                    0,
                    0,
                ),
                (
                    &format!("integ_test_mixed_alloc_{}", test_suffix),
                    &format!("integ_test_alloc_tag_{}", test_suffix),
                    1,
                    1024 * 1024,
                    0,
                    0,
                ),
                (
                    &format!("integ_test_mixed_manual_{}", test_suffix),
                    &format!("integ_test_manual_tag_{}", test_suffix),
                    1,
                    1024 * 1024,
                    0,
                    0,
                ),
            ],
            3,
        )
        .await?;

        Ok(TestData {
            facility_id,
            show_id,
            dept_id,
            hostname_alloc,
            alloc_alloc,
            manual_alloc,
            hostname_host,
            alloc_host,
            manual_host,
            hostname_job,
            alloc_job,
            manual_job,
            mixed_job,
            test_suffix,
        })
    }

    async fn create_allocation(
        pool: &mut Transaction<'static, Postgres>,
        facility_id: Uuid,
        name: &str,
        tag: &str,
    ) -> Result<Uuid, sqlx::Error> {
        let alloc_id = Uuid::new_v4();
        sqlx::query(
            "INSERT INTO alloc (pk_alloc, str_name, pk_facility, str_tag) VALUES ($1, $2, $3, $4)",
        )
        .bind(alloc_id.to_string())
        .bind(name)
        .bind(facility_id.to_string())
        .bind(tag)
        .execute(&mut **pool)
        .await?;
        Ok(alloc_id)
    }

    async fn create_subscription(
        pool: &mut Transaction<'static, Postgres>,
        alloc_id: Uuid,
        show_id: Uuid,
        size: i64,
        burst: i64,
    ) -> Result<(), sqlx::Error> {
        let subscription_id = Uuid::new_v4();
        sqlx::query("INSERT INTO subscription (pk_subscription, pk_alloc, pk_show, int_size, int_burst) VALUES ($1, $2, $3, $4, $5)")
            .bind(subscription_id.to_string())
            .bind(alloc_id.to_string())
            .bind(show_id.to_string())
            .bind(size)
            .bind(burst)
            .execute(&mut **pool)
            .await?;
        Ok(())
    }

    #[allow(clippy::too_many_arguments)]
    async fn create_host(
        pool: &mut Transaction<'static, Postgres>,
        alloc_id: Uuid,
        name: &str,
        cores: i64,
        memory_kb: i64,
        gpus: i64,
        gpu_memory_kb: i64,
        tags: Vec<(&str, &str)>,
    ) -> Result<TestHost, sqlx::Error> {
        let host_id = Uuid::new_v4();

        // Create host
        sqlx::query(
            "INSERT INTO host (pk_host, pk_alloc, str_name, str_lock_state, int_cores, int_cores_idle, int_mem, int_mem_idle, int_gpus, int_gpus_idle, int_gpu_mem, int_gpu_mem_idle, int_thread_mode) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)"
        )
        .bind(host_id.to_string())
        .bind(alloc_id.to_string())
        .bind(name)
        .bind("OPEN")
        .bind(cores * 100) // Core multiplier
        .bind(cores * 100)
        .bind(memory_kb)
        .bind(memory_kb)
        .bind(gpus)
        .bind(gpus)
        .bind(gpu_memory_kb)
        .bind(gpu_memory_kb)
        .bind(0) // ThreadMode::Auto
        .execute(&mut **pool)
        .await?;

        // Create host_stat
        let host_stat_id = Uuid::new_v4();
        sqlx::query(
            "INSERT INTO host_stat (pk_host_stat, pk_host, str_state, str_os, int_gpu_mem_total, int_gpu_mem_free) VALUES ($1, $2, $3, $4, $5, $6)"
        )
        .bind(host_stat_id.to_string())
        .bind(host_id.to_string())
        .bind("UP")
        .bind("linux")
        .bind(gpu_memory_kb)
        .bind(gpu_memory_kb)
        .execute(&mut **pool)
        .await?;

        // Create host tags
        for (tag_name, tag_type) in tags {
            let tag_id = Uuid::new_v4();
            sqlx::query(
                "INSERT INTO host_tag (pk_host_tag, pk_host, str_tag, str_tag_type) VALUES ($1, $2, $3, $4)"
            )
            .bind(tag_id.to_string())
            .bind(host_id.to_string())
            .bind(tag_name)
            .bind(tag_type)
            .execute(&mut **pool)
            .await?;
        }

        Ok(TestHost {
            id: host_id,
            name: name.to_string(),
            alloc_id,
        })
    }

    async fn create_folder(
        pool: &mut Transaction<'static, Postgres>,
        show_id: Uuid,
        dept_id: Uuid,
        name: &str,
    ) -> Result<Uuid, sqlx::Error> {
        let folder_id = Uuid::new_v4();
        sqlx::query(
            "INSERT INTO folder (pk_folder, pk_show, pk_dept, str_name) VALUES ($1, $2, $3, $4)",
        )
        .bind(folder_id.to_string())
        .bind(show_id.to_string())
        .bind(dept_id.to_string())
        .bind(name)
        .execute(&mut **pool)
        .await?;
        Ok(folder_id)
    }

    #[allow(clippy::too_many_arguments)]
    async fn create_job_scenario(
        pool: &Pool<Postgres>,
        show_id: Uuid,
        facility_id: Uuid,
        dept_id: Uuid,
        folder_id: Uuid,
        job_name: &str,
        layers: Vec<(&str, &str, i64, i64, i64, i64)>, // (layer_name, tag, min_cores, min_mem, min_gpus, min_gpu_mem)
        frames_by_layer: usize,
    ) -> Result<TestJob, sqlx::Error> {
        let mut tx = pool.begin().await?;
        let job_id = Uuid::new_v4();

        // Create job
        sqlx::query(
            "INSERT INTO job (pk_job, pk_folder, pk_show, pk_facility, pk_dept, str_name, str_visible_name, str_shot, str_user, str_state) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)"
        )
        .bind(job_id.to_string())
        .bind(folder_id.to_string())
        .bind(show_id.to_string())
        .bind(facility_id.to_string())
        .bind(dept_id.to_string())
        .bind(job_name)
        .bind(job_name)
        .bind(format!("integ_test_shot_{}", job_name.split('_').next_back().unwrap_or("default")))
        .bind(format!("integ_test_user_{}", job_name.split('_').next_back().unwrap_or("default")))
        .bind("PENDING")
        .execute(&mut *tx)
        .await?;

        // Create job stats with waiting frames
        // First check if job_stat already exists for this job (might be created by triggers)
        let existing_job_stat =
            sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM job_stat WHERE pk_job = $1")
                .bind(job_id.to_string())
                .fetch_one(&mut *tx)
                .await?;

        if existing_job_stat == 0 {
            let total_waiting_frames = layers.len() * 3; // 3 frames per layer
            sqlx::query(
                "INSERT INTO job_stat (pk_job_stat, pk_job, int_waiting_count) VALUES ($1, $2, $3)",
            )
            .bind(Uuid::new_v4().to_string())
            .bind(job_id.to_string())
            .bind(total_waiting_frames as i64)
            .execute(&mut *tx)
            .await?;
        } else {
            // Update existing job_stat
            let total_waiting_frames = layers.len() * 3; // 3 frames per layer
            sqlx::query("UPDATE job_stat SET int_waiting_count = $1 WHERE pk_job = $2")
                .bind(total_waiting_frames as i64)
                .bind(job_id.to_string())
                .execute(&mut *tx)
                .await?;
        }

        // Create job resource
        // First check if job_resource already exists for this job (might be created by triggers)
        let existing_job_resource =
            sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM job_resource WHERE pk_job = $1")
                .bind(job_id.to_string())
                .fetch_one(&mut *tx)
                .await?;

        if existing_job_resource == 0 {
            sqlx::query(
                "INSERT INTO job_resource (pk_job_resource, pk_job, int_priority) VALUES ($1, $2, $3)",
            )
            .bind(Uuid::new_v4().to_string())
            .bind(job_id.to_string())
            .bind(1)
            .execute(&mut *tx)
            .await?;
        } else {
            // Update existing job_resource
            sqlx::query("UPDATE job_resource SET int_priority = $1 WHERE pk_job = $2")
                .bind(1)
                .bind(job_id.to_string())
                .execute(&mut *tx)
                .await?;
        }

        let mut test_layers = Vec::new();

        for (layer_name, tag, min_cores, min_mem, min_gpus, min_gpu_mem) in layers {
            let layer_id = Uuid::new_v4();

            // Create layer
            sqlx::query(
                "INSERT INTO layer (pk_layer, pk_job, str_name, str_cmd, str_range, str_tags, str_type, int_cores_min, int_mem_min, int_gpus_min, int_gpu_mem_min) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)"
            )
            .bind(layer_id.to_string())
            .bind(job_id.to_string())
            .bind(layer_name)
            .bind("echo 'Integration test frame'")
            .bind("1-3")
            .bind(tag)
            .bind("PRE") // Default layer type
            .bind(min_cores * 100) // Core multiplier
            .bind(min_mem)
            .bind(min_gpus)
            .bind(min_gpu_mem)
            .execute(&mut *tx)
            .await?;

            // Create layer stats
            sqlx::query(
                "INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job, int_waiting_count, int_total_count) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (pk_layer) DO UPDATE SET int_waiting_count = EXCLUDED.int_waiting_count, int_total_count = EXCLUDED.int_total_count"
            )
            .bind(Uuid::new_v4().to_string())
            .bind(layer_id.to_string())
            .bind(job_id.to_string())
            .bind(3) // 3 waiting frames
            .bind(3) // 3 total frames
            .execute(&mut *tx)
            .await?;

            // Create layer resource
            // Check if layer_resource already exists for this layer (might be created by triggers)
            let existing_layer_resource = sqlx::query_scalar::<_, i64>(
                "SELECT COUNT(*) FROM layer_resource WHERE pk_layer = $1",
            )
            .bind(layer_id.to_string())
            .fetch_one(&mut *tx)
            .await?;

            if existing_layer_resource == 0 {
                sqlx::query(
                    "INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES ($1, $2, $3)"
                )
                .bind(Uuid::new_v4().to_string())
                .bind(layer_id.to_string())
                .bind(job_id.to_string())
                .execute(&mut *tx)
                .await?;
            }

            // Create frames (1-3)
            for frame_num in 1..=frames_by_layer as i32 {
                let frame_id = Uuid::new_v4();
                sqlx::query(
                    "INSERT INTO frame (pk_frame, pk_layer, pk_job, str_name, str_state, int_number, int_layer_order, int_dispatch_order) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"
                )
                .bind(frame_id.to_string())
                .bind(layer_id.to_string())
                .bind(job_id.to_string())
                .bind(format!("{}-frame{}", frame_num, layer_name))
                .bind("WAITING")
                .bind(frame_num)
                .bind(frame_num)
                .bind(frame_num)
                .execute(&mut *tx)
                .await?;
            }

            test_layers.push(TestLayer {
                id: layer_id,
                name: layer_name.to_string(),
                tag: tag.to_string(),
            });
        }
        tx.commit().await?;

        Ok(TestJob {
            id: job_id,
            name: job_name.to_string(),
            layers: test_layers,
            frames_by_layer,
        })
    }

    #[allow(dead_code)]
    struct TestData {
        facility_id: Uuid,
        show_id: Uuid,
        dept_id: Uuid,
        hostname_alloc: Uuid,
        alloc_alloc: Uuid,
        manual_alloc: Uuid,
        hostname_host: TestHost,
        alloc_host: TestHost,
        manual_host: TestHost,
        hostname_job: TestJob,
        alloc_job: TestJob,
        manual_job: TestJob,
        mixed_job: TestJob,
        test_suffix: String,
    }

    impl TestData {
        fn num_frames(&self) -> usize {
            self.alloc_job.layers.len() * self.alloc_job.frames_by_layer
                + self.mixed_job.layers.len() * self.mixed_job.frames_by_layer
                + self.manual_job.layers.len() * self.manual_job.frames_by_layer
                + self.hostname_job.layers.len() * self.hostname_job.frames_by_layer
        }
    }

    #[derive(Debug)]
    #[allow(dead_code)]
    struct TestHost {
        id: Uuid,
        name: String,
        alloc_id: Uuid,
    }

    #[derive(Debug)]
    #[allow(dead_code)]
    struct TestJob {
        id: Uuid,
        name: String,
        layers: Vec<TestLayer>,
        frames_by_layer: usize,
    }

    #[derive(Debug)]
    #[allow(dead_code)]
    struct TestLayer {
        id: Uuid,
        name: String,
        tag: String,
    }

    /// Helper function to run a test with proper setup and cleanup
    async fn test_wrapper<F, Fut>(
        test_name: &str,
        test_fn: F,
    ) -> Result<(), Box<dyn std::error::Error>>
    where
        F: FnOnce(TestData) -> Fut,
        Fut: std::future::Future<Output = ()>,
    {
        info!("Starting integration test: {}", test_name);

        // Setup database and test data
        let pool = setup_test_database().await?;
        sleep(Duration::from_secs(3)).await;

        // Log pool status
        info!(
            "Pool status - Size: {}, Idle: {}",
            pool.size(),
            pool.num_idle()
        );
        let test_data = create_test_data(&pool).await?;
        // Wait for data transactions to clear
        sleep(Duration::from_secs(1)).await;

        // Set global config
        let _ = OVERRIDE_CONFIG.set(create_test_config());

        // Run the test
        test_fn(test_data).await;

        Ok(())
    }

    #[tokio::test]
    #[traced_test]
    #[serial]
    async fn test_dispatch_hostname_tag_flow() {
        let result = test_wrapper(
            "test_dispatch_hostname_tag_flow",
            test_dispatch_hostname_tag_flow_inner,
        )
        .await;
        assert_ok!(result, "Failure at test wrapper")
    }

    async fn test_dispatch_hostname_tag_flow_inner(test_data: TestData) {
        // Create a specific cluster feed for HOSTNAME tag testing
        let hostname_cluster = Cluster::ComposedKey(ClusterKey {
            facility_id: test_data.facility_id.to_string(),
            show_id: test_data.show_id.to_string(),
            tag: Tag {
                name: format!("integ_test_hostname_tag_{}", test_data.test_suffix),
                ttype: TagType::HostName,
            },
        });

        let cluster_feed = ClusterFeed::load_from_clusters(vec![hostname_cluster]);

        info!("Starting HOSTNAME tag integration test...");

        let waiting_frames_before =
            get_waiting_frames_count(WaitingFrameClause::JobId(test_data.hostname_job.id)).await;
        assert_eq!(waiting_frames_before, 6);
        // Run the job fetcher with our test cluster feed
        // This simulates the main service flow: cluster discovery → job querying → layer processing → dispatching
        let result = pipeline::run(cluster_feed).await;

        match result {
            Ok(()) => {
                info!("✅ HOSTNAME tag integration test completed successfully");

                let waiting_frames =
                    get_waiting_frames_count(WaitingFrameClause::JobId(test_data.hostname_job.id))
                        .await;
                info!(
                    "Job waiting count after processing: {}. Half the frames matched the expected tag",
                    waiting_frames
                );
                assert_eq!(waiting_frames, 3);

                // In dry run mode, frames shouldn't actually be dispatched (state changes)
                // but the service should have processed them without errors
            }
            Err(e) => {
                panic!("❌ HOSTNAME tag integration test failed: {}", e);
            }
        }
    }

    #[tokio::test]
    #[traced_test]
    #[serial]
    async fn test_dispatch_alloc_tag_flow() {
        let result = test_wrapper(
            "test_dispatch_hostname_tag_flow",
            test_dispatch_alloc_tag_flow_inner,
        )
        .await;
        assert_ok!(result, "Failure at test wrapper")
    }

    async fn test_dispatch_alloc_tag_flow_inner(test_data: TestData) {
        // Create a specific cluster feed for ALLOC tag testing
        let alloc_cluster = Cluster::ComposedKey(ClusterKey {
            facility_id: test_data.facility_id.to_string(),
            show_id: test_data.show_id.to_string(),
            tag: Tag {
                name: format!("integ_test_alloc_tag_{}", test_data.test_suffix),
                ttype: TagType::Alloc,
            },
        });

        let cluster_feed = ClusterFeed::load_from_clusters(vec![alloc_cluster]);

        info!("Starting ALLOC tag integration test...");

        let frame_count = test_data.num_frames();
        let waiting_frames_before = get_waiting_frames_count(WaitingFrameClause::All).await;
        assert_eq!(waiting_frames_before, frame_count);

        let result = pipeline::run(cluster_feed).await;

        match result {
            Ok(()) => {
                let waiting_frames_after = get_waiting_frames_count(WaitingFrameClause::All).await;
                let target_frames =
                    test_data.alloc_job.frames_by_layer + test_data.mixed_job.frames_by_layer;
                assert_eq!(waiting_frames_after, frame_count - target_frames);
                info!("✅ ALLOC tag integration test completed successfully");
            }
            Err(e) => {
                panic!("❌ ALLOC tag integration test failed: {}", e);
            }
        }
    }

    #[tokio::test]
    #[traced_test]
    #[serial]
    async fn test_dispatch_manual_tag_flow() {
        let result = test_wrapper(
            "test_dispatch_manual_tag_flow",
            test_dispatch_manual_tag_flow_inner,
        )
        .await;
        assert_ok!(result, "Failure at test wrapper")
    }

    async fn test_dispatch_manual_tag_flow_inner(test_data: TestData) {
        // Create a cluster feed with MANUAL tags (chunked)
        let manual_cluster = Cluster::TagsKey(vec![Tag {
            name: format!("integ_test_manual_tag_{}", test_data.test_suffix),
            ttype: TagType::Manual,
        }]);

        let cluster_feed = ClusterFeed::load_from_clusters(vec![manual_cluster]);

        info!("Starting MANUAL tag integration test...");
        let frame_count = test_data.num_frames();
        let waiting_frames_before = get_waiting_frames_count(WaitingFrameClause::All).await;
        assert_eq!(waiting_frames_before, frame_count);

        let result = pipeline::run(cluster_feed).await;

        match result {
            Ok(()) => {
                let waiting_frames_after = get_waiting_frames_count(WaitingFrameClause::All).await;
                let target_frames =
                    test_data.manual_job.frames_by_layer + test_data.manual_job.frames_by_layer;
                assert_eq!(waiting_frames_after, frame_count - target_frames);
                info!("✅ MANUAL tag integration test completed successfully");
            }
            Err(e) => {
                panic!("❌ MANUAL tag integration test failed: {}", e);
            }
        }
    }

    #[tokio::test]
    #[traced_test]
    #[serial]
    async fn test_dispatch_mixed_job_scenario() {
        let result = test_wrapper(
            "test_dispatch_mixed_job_scenario",
            test_dispatch_mixed_job_scenario_inner,
        )
        .await;
        assert_ok!(result, "Failure at test wrapper")
    }

    async fn test_dispatch_mixed_job_scenario_inner(test_data: TestData) {
        // Create multiple clusters to handle the mixed job with different tag types
        let clusters = vec![
            Cluster::ComposedKey(ClusterKey {
                facility_id: test_data.facility_id.to_string(),
                show_id: test_data.show_id.to_string(),
                tag: Tag {
                    name: format!("integ_test_hostname_tag_{}", test_data.test_suffix),
                    ttype: TagType::HostName,
                },
            }),
            Cluster::ComposedKey(ClusterKey {
                facility_id: test_data.facility_id.to_string(),
                show_id: test_data.show_id.to_string(),
                tag: Tag {
                    name: format!("integ_test_alloc_tag_{}", test_data.test_suffix),
                    ttype: TagType::Alloc,
                },
            }),
            Cluster::TagsKey(vec![Tag {
                name: format!("integ_test_manual_tag_{}", test_data.test_suffix),
                ttype: TagType::Manual,
            }]),
        ];

        let cluster_feed = ClusterFeed::load_from_clusters(clusters);

        info!("Starting mixed job scenario integration test...");

        let result = pipeline::run(cluster_feed).await;
        let pool = assert_ok!(connection_pool().await);

        match result {
            Ok(()) => {
                info!("✅ Mixed job scenario integration test completed successfully");

                // Verify that all layers of the mixed job were processed
                let mixed_job_layers =
                    sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM layer WHERE pk_job = $1")
                        .bind(test_data.mixed_job.id.to_string())
                        .fetch_one(&*pool)
                        .await
                        .expect("Failed to query mixed job layers");

                info!("Mixed job has {} layers", mixed_job_layers);
                assert_eq!(
                    mixed_job_layers, 3,
                    "Mixed job should have 3 layers with different tags"
                );
            }
            Err(e) => {
                panic!("❌ Mixed job scenario integration test failed: {}", e);
            }
        }
    }

    #[tokio::test]
    #[traced_test]
    #[serial]
    async fn test_dispatcher_no_matching_hosts() {
        let result = test_wrapper(
            "test_dispatcher_no_matching_hosts",
            test_dispatcher_no_matching_hosts_inner,
        )
        .await;
        assert_ok!(result, "Failure at test wrapper")
    }

    async fn test_dispatcher_no_matching_hosts_inner(_test_data: TestData) {
        // Create a cluster with a non-existent tag that won't match any hosts
        let non_matching_cluster = Cluster::TagsKey(vec![Tag {
            name: "non_existent_tag".to_string(),
            ttype: TagType::Manual,
        }]);

        let cluster_feed = ClusterFeed::load_from_clusters(vec![non_matching_cluster]);

        info!("Starting no matching hosts integration test...");

        let waiting_frames_before = get_waiting_frames_count(WaitingFrameClause::All).await;
        assert_eq!(waiting_frames_before, 21);

        let result = pipeline::run(cluster_feed).await;

        match result {
            Ok(()) => {
                let waiting_frames_after = get_waiting_frames_count(WaitingFrameClause::All).await;
                assert_eq!(waiting_frames_after, 21);

                info!("✅ No matching hosts integration test completed successfully");
                // The service should handle no matching hosts gracefully
            }
            Err(e) => {
                panic!("❌ No matching hosts integration test failed: {}", e);
            }
        }
    }

    // #[tokio::test]
    // #[traced_test]
    // async fn test_full_service_cluster_discovery() {
    //     let pool = setup_test_database()
    //         .await
    //         .expect("Failed to setup test database");
    //     let _test_data = create_full_integration_test_data(&pool)
    //         .await
    //         .expect("Failed to create test data");
    //     let _ = OVERRIDE_CONFIG.set(create_test_config());

    //     info!("Starting cluster discovery integration test...");

    //     // Test the full cluster discovery process
    //     let cluster_feed = ClusterFeed::load_all(true)
    //         .await
    //         .expect("Failed to load clusters");

    //     info!("Discovered {} clusters", cluster_feed.keys.len());

    //     // Run the job fetcher with discovered clusters
    //     let result = job_fetcher::run(cluster_feed).await;

    //     match result {
    //         Ok(()) => {
    //             info!("✅ Cluster discovery integration test completed successfully");
    //         }
    //         Err(e) => {
    //             panic!("❌ Cluster discovery integration test failed: {}", e);
    //         }
    //     }

    //     cleanup_test_data(&pool)
    //         .await
    //         .expect("Failed to clean up test data");
    // pool.close().await;
    // }
}
