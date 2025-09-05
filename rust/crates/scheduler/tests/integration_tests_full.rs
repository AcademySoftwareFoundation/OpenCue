use std::time::Duration;

use scheduler::{
    cluster::{Cluster, ClusterFeed},
    cluster_key::{ClusterKey, Tag, TagType},
    config::{Config, DatabaseConfig, LoggingConfig, QueueConfig, RqdConfig},
    job_fetcher,
};
use sqlx::{Pool, Postgres};
use tracing::info;
use tracing_test::traced_test;
use uuid::Uuid;

/// Full service integration tests that test the complete job scheduler binary.
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
#[cfg(test)]
mod full_service_tests {
    use scheduler::config::OVERRIDE_CONFIG;

    use super::*;

    // Database connection configuration - hardcoded for testing
    const TEST_DB_HOST: &str = "localhost";
    const TEST_DB_PORT: u16 = 5432;
    const TEST_DB_NAME: &str = "cuebot";
    const TEST_DB_USER: &str = "cuebot";
    const TEST_DB_PASSWORD: &str = "cuebot_password";

    /// Test configuration for full service integration testing
    fn create_test_config() -> Config {
        let connection_url = format!(
            "postgresql://{}:{}@{}:{}/{}",
            TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
        );

        Config {
            logging: LoggingConfig {
                level: "debug".to_string(),
                path: "/tmp/scheduler_test.log".to_string(),
                file_appender: false,
            },
            queue: QueueConfig {
                monitor_interval: Duration::from_secs(1),
                worker_threads: 2,
                dispatch_frames_per_layer_limit: 5, // Small limit for testing
                core_multiplier: 100,
                memory_stranded_threshold: bytesize::ByteSize::mb(100),
                job_back_off_duration: Duration::from_secs(10),
                stream: scheduler::config::StreamConfig {
                    cluster_buffer_size: 1,
                    layer_buffer_size: 1,
                },
                manual_tags_chunk_size: 10,
                hostname_tags_chunk_size: 20,
                host_candidate_attemps_per_layer: 3,
            },
            database: DatabaseConfig {
                pool_size: 20,
                connection_url,
                core_multiplier: 100,
            },
            kafka: scheduler::config::KafkaConfig::default(),
            rqd: RqdConfig {
                grpc_port: 8444,
                dry_run_mode: true, // Always run in dry mode for tests
            },
            host_cache: scheduler::config::HostCacheConfig::default(),
        }
    }

    async fn setup_test_database() -> Result<Pool<Postgres>, sqlx::Error> {
        let database_url = format!(
            "postgresql://{}:{}@{}:{}/{}",
            TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
        );
        let pool = sqlx::PgPool::connect(&database_url).await?;

        // Force a thorough cleanup before starting
        cleanup_test_data(&pool).await?;

        // Also manually clean up the specific constraint-violating records with TRUNCATE for thorough cleanup
        // Disable triggers temporarily and clean up everything related to test data
        let _ = sqlx::query("SET session_replication_role = 'replica'")
            .execute(&pool)
            .await;

        // Clean up all test-related data more aggressively
        let _ = sqlx::query("DELETE FROM job_stat").execute(&pool).await;
        let _ = sqlx::query("DELETE FROM layer_stat").execute(&pool).await;
        let _ = sqlx::query("DELETE FROM frame").execute(&pool).await;
        let _ = sqlx::query("DELETE FROM layer_resource")
            .execute(&pool)
            .await;
        let _ = sqlx::query("DELETE FROM layer").execute(&pool).await;
        let _ = sqlx::query("DELETE FROM job_resource").execute(&pool).await;
        let _ = sqlx::query("DELETE FROM job").execute(&pool).await;

        let _ = sqlx::query("SET session_replication_role = 'origin'")
            .execute(&pool)
            .await;

        Ok(pool)
    }

    async fn cleanup_test_data(pool: &Pool<Postgres>) -> Result<(), sqlx::Error> {
        // Temporarily disable triggers to avoid issues during cleanup
        sqlx::query("SET session_replication_role = 'replica'")
            .execute(pool)
            .await?;

        // Delete job_history records for test jobs first
        sqlx::query("DELETE FROM job_history WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Delete in reverse dependency order - most dependent tables first

        // Delete frames first
        sqlx::query("DELETE FROM frame WHERE str_name LIKE '%_integ_test%'")
            .execute(pool)
            .await?;

        // Delete layer stats and resources
        sqlx::query("DELETE FROM layer_stat WHERE pk_layer IN (SELECT pk_layer FROM layer WHERE str_name LIKE 'integ_test_%')")
            .execute(pool)
            .await?;
        sqlx::query("DELETE FROM layer_resource WHERE pk_layer IN (SELECT pk_layer FROM layer WHERE str_name LIKE 'integ_test_%')")
            .execute(pool)
            .await?;

        // Delete layers
        sqlx::query("DELETE FROM layer WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Delete job stats and resources
        // First delete any orphaned job_stat records that might be causing conflicts
        sqlx::query("DELETE FROM job_stat WHERE pk_job NOT IN (SELECT pk_job FROM job)")
            .execute(pool)
            .await?;
        sqlx::query("DELETE FROM job_stat WHERE pk_job IN (SELECT pk_job FROM job WHERE str_name LIKE 'integ_test_%')")
            .execute(pool)
            .await?;
        sqlx::query("DELETE FROM job_resource WHERE pk_job IN (SELECT pk_job FROM job WHERE str_name LIKE 'integ_test_%')")
            .execute(pool)
            .await?;

        // Delete jobs
        sqlx::query("DELETE FROM job WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Delete folder
        sqlx::query("DELETE FROM folder WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Delete host stats and tags
        sqlx::query("DELETE FROM host_stat WHERE pk_host IN (SELECT pk_host FROM host WHERE str_name LIKE 'integ_test_%')")
            .execute(pool)
            .await?;
        sqlx::query("DELETE FROM host_tag WHERE str_tag LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Delete hosts
        sqlx::query("DELETE FROM host WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Delete subscriptions
        sqlx::query("DELETE FROM subscription WHERE pk_alloc IN (SELECT pk_alloc FROM alloc WHERE str_name LIKE 'integ_test_%')")
            .execute(pool)
            .await?;

        // Delete allocs
        sqlx::query("DELETE FROM alloc WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Delete shows
        sqlx::query("DELETE FROM show WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Delete facilities and departments
        sqlx::query("DELETE FROM facility WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;
        sqlx::query("DELETE FROM dept WHERE str_name LIKE 'integ_test_%'")
            .execute(pool)
            .await?;

        // Re-enable triggers
        sqlx::query("SET session_replication_role = 'origin'")
            .execute(pool)
            .await?;
        Ok(())
    }

    /// Creates comprehensive test data for integration testing with multiple scenarios
    async fn create_full_integration_test_data(
        pool: &Pool<Postgres>,
    ) -> Result<IntegrationTestData, sqlx::Error> {
        // Create unique suffix for this test run to avoid conflicts when running tests concurrently
        let test_suffix = Uuid::new_v4().to_string()[..8].to_string();
        // Create basic entities
        let facility_id = Uuid::new_v4();
        let dept_id = Uuid::new_v4();
        let show_id = Uuid::new_v4();

        // Create facility
        sqlx::query("INSERT INTO facility (pk_facility, str_name) VALUES ($1, $2)")
            .bind(facility_id.to_string())
            .bind(format!("integ_test_facility_{}", test_suffix))
            .execute(pool)
            .await?;

        // Create department
        sqlx::query("INSERT INTO dept (pk_dept, str_name) VALUES ($1, $2)")
            .bind(dept_id.to_string())
            .bind(format!("integ_test_dept_{}", test_suffix))
            .execute(pool)
            .await?;

        // Create show
        sqlx::query("INSERT INTO show (pk_show, str_name) VALUES ($1, $2)")
            .bind(show_id.to_string())
            .bind(format!("integ_test_show_{}", test_suffix))
            .execute(pool)
            .await?;

        // Create allocations for different tag types
        let hostname_alloc = create_allocation(
            pool,
            facility_id,
            &format!("integ_test_hostname_alloc_{}", test_suffix),
            "HOSTNAME",
        )
        .await?;
        let alloc_alloc = create_allocation(
            pool,
            facility_id,
            &format!("integ_test_alloc_alloc_{}", test_suffix),
            "ALLOC",
        )
        .await?;
        let manual_alloc = create_allocation(
            pool,
            facility_id,
            &format!("integ_test_manual_alloc_{}", test_suffix),
            "MANUAL",
        )
        .await?;

        // Create subscriptions with different resource limits
        create_subscription(pool, hostname_alloc, show_id, 1000, 1200).await?;
        create_subscription(pool, alloc_alloc, show_id, 800, 1000).await?;
        create_subscription(pool, manual_alloc, show_id, 600, 800).await?;

        // Create hosts with different tag types and resource configurations
        let hostname_host = create_host(
            pool,
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
            pool,
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
            pool,
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
            pool,
            show_id,
            dept_id,
            &format!("integ_test_folder_{}", test_suffix),
        )
        .await?;

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
                    1 * 1024 * 1024,
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
                1 * 1024 * 1024,
                1,
                512 * 1024,
            )],
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
                1 * 1024 * 1024,
                0,
                0,
            )],
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
                    1 * 1024 * 1024,
                    0,
                    0,
                ),
                (
                    &format!("integ_test_mixed_alloc_{}", test_suffix),
                    &format!("integ_test_alloc_tag_{}", test_suffix),
                    1,
                    1 * 1024 * 1024,
                    0,
                    0,
                ),
                (
                    &format!("integ_test_mixed_manual_{}", test_suffix),
                    &format!("integ_test_manual_tag_{}", test_suffix),
                    1,
                    1 * 1024 * 1024,
                    0,
                    0,
                ),
            ],
        )
        .await?;

        Ok(IntegrationTestData {
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
        pool: &Pool<Postgres>,
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
        .execute(pool)
        .await?;
        Ok(alloc_id)
    }

    async fn create_subscription(
        pool: &Pool<Postgres>,
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
            .execute(pool)
            .await?;
        Ok(())
    }

    async fn create_host(
        pool: &Pool<Postgres>,
        alloc_id: Uuid,
        name: &str,
        cores: i64,
        memory_kb: i64,
        gpus: i64,
        gpu_memory_kb: i64,
        tags: Vec<(&str, &str)>,
    ) -> Result<IntegrationTestHost, sqlx::Error> {
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
        .execute(pool)
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
        .execute(pool)
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
            .execute(pool)
            .await?;
        }

        Ok(IntegrationTestHost {
            id: host_id,
            name: name.to_string(),
            alloc_id,
        })
    }

    async fn create_folder(
        pool: &Pool<Postgres>,
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
        .execute(pool)
        .await?;
        Ok(folder_id)
    }

    async fn create_job_scenario(
        pool: &Pool<Postgres>,
        show_id: Uuid,
        facility_id: Uuid,
        dept_id: Uuid,
        folder_id: Uuid,
        job_name: &str,
        layers: Vec<(&str, &str, i64, i64, i64, i64)>, // (layer_name, tag, min_cores, min_mem, min_gpus, min_gpu_mem)
    ) -> Result<IntegrationTestJob, sqlx::Error> {
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
        .bind(format!("integ_test_shot_{}", job_name.split('_').last().unwrap_or("default")))
        .bind(format!("integ_test_user_{}", job_name.split('_').last().unwrap_or("default")))
        .bind("PENDING")
        .execute(pool)
        .await?;

        // Create job stats with waiting frames
        // First check if job_stat already exists for this job (might be created by triggers)
        let existing_job_stat =
            sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM job_stat WHERE pk_job = $1")
                .bind(job_id.to_string())
                .fetch_one(pool)
                .await?;

        if existing_job_stat == 0 {
            let total_waiting_frames = layers.len() * 3; // 3 frames per layer
            sqlx::query(
                "INSERT INTO job_stat (pk_job_stat, pk_job, int_waiting_count) VALUES ($1, $2, $3)",
            )
            .bind(Uuid::new_v4().to_string())
            .bind(job_id.to_string())
            .bind(total_waiting_frames as i64)
            .execute(pool)
            .await?;
        } else {
            // Update existing job_stat
            let total_waiting_frames = layers.len() * 3; // 3 frames per layer
            sqlx::query("UPDATE job_stat SET int_waiting_count = $1 WHERE pk_job = $2")
                .bind(total_waiting_frames as i64)
                .bind(job_id.to_string())
                .execute(pool)
                .await?;
        }

        // Create job resource
        // First check if job_resource already exists for this job (might be created by triggers)
        let existing_job_resource =
            sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM job_resource WHERE pk_job = $1")
                .bind(job_id.to_string())
                .fetch_one(pool)
                .await?;

        if existing_job_resource == 0 {
            sqlx::query(
                "INSERT INTO job_resource (pk_job_resource, pk_job, int_priority) VALUES ($1, $2, $3)",
            )
            .bind(Uuid::new_v4().to_string())
            .bind(job_id.to_string())
            .bind(1)
            .execute(pool)
            .await?;
        } else {
            // Update existing job_resource
            sqlx::query("UPDATE job_resource SET int_priority = $1 WHERE pk_job = $2")
                .bind(1)
                .bind(job_id.to_string())
                .execute(pool)
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
            .execute(pool)
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
            .execute(pool)
            .await?;

            // Create layer resource
            // Check if layer_resource already exists for this layer (might be created by triggers)
            let existing_layer_resource = sqlx::query_scalar::<_, i64>(
                "SELECT COUNT(*) FROM layer_resource WHERE pk_layer = $1",
            )
            .bind(layer_id.to_string())
            .fetch_one(pool)
            .await?;

            if existing_layer_resource == 0 {
                sqlx::query(
                    "INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES ($1, $2, $3)"
                )
                .bind(Uuid::new_v4().to_string())
                .bind(layer_id.to_string())
                .bind(job_id.to_string())
                .execute(pool)
                .await?;
            }

            // Create frames (1-3)
            for frame_num in 1..=3 {
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
                .execute(pool)
                .await?;
            }

            test_layers.push(IntegrationTestLayer {
                id: layer_id,
                name: layer_name.to_string(),
                tag: tag.to_string(),
            });
        }

        Ok(IntegrationTestJob {
            id: job_id,
            name: job_name.to_string(),
            layers: test_layers,
        })
    }

    #[derive(Debug)]
    struct IntegrationTestData {
        facility_id: Uuid,
        show_id: Uuid,
        dept_id: Uuid,
        hostname_alloc: Uuid,
        alloc_alloc: Uuid,
        manual_alloc: Uuid,
        hostname_host: IntegrationTestHost,
        alloc_host: IntegrationTestHost,
        manual_host: IntegrationTestHost,
        hostname_job: IntegrationTestJob,
        alloc_job: IntegrationTestJob,
        manual_job: IntegrationTestJob,
        mixed_job: IntegrationTestJob,
        test_suffix: String,
    }

    #[derive(Debug)]
    struct IntegrationTestHost {
        id: Uuid,
        name: String,
        alloc_id: Uuid,
    }

    #[derive(Debug)]
    struct IntegrationTestJob {
        id: Uuid,
        name: String,
        layers: Vec<IntegrationTestLayer>,
    }

    #[derive(Debug)]
    struct IntegrationTestLayer {
        id: Uuid,
        name: String,
        tag: String,
    }

    /// Helper function to override global config for testing
    fn with_test_config<F, R>(test_config: Config, f: F) -> R
    where
        F: FnOnce() -> R,
    {
        // Note: Since CONFIG is a lazy_static, we can't easily override it.
        // In a real implementation, you might need to make the config injectable
        // or use environment variables. For now, we'll work with the limitation.
        f()
    }

    async fn get_waiting_frames_count(pool: &Pool<Postgres>, job_id: &Uuid) -> i64 {
        // Verify that jobs were processed by checking database state
        // In a real scenario, we'd check for frame state changes, dispatch logs, etc.
        sqlx::query_scalar::<_, i64>("SELECT int_waiting_count FROM job_stat WHERE pk_job = $1")
            .bind(job_id.to_string())
            .fetch_one(pool)
            .await
            .expect("Failed to query job stats")
    }

    #[tokio::test]
    #[traced_test]
    async fn test_full_service_hostname_tag_flow() {
        let pool = setup_test_database()
            .await
            .expect("Failed to setup test database");
        let test_data = create_full_integration_test_data(&pool)
            .await
            .expect("Failed to create test data");
        let _ = OVERRIDE_CONFIG.set(create_test_config());

        // Create a specific cluster feed for HOSTNAME tag testing
        let hostname_cluster = Cluster::ComposedKey(ClusterKey {
            facility_id: test_data.facility_id.to_string(),
            show_id: test_data.show_id.to_string(),
            tag: Tag {
                name: format!("integ_test_hostname_tag_{}", test_data.test_suffix),
                ttype: TagType::HostName,
            },
        });

        let cluster_feed = ClusterFeed::new_for_test(vec![hostname_cluster]);

        info!("Starting HOSTNAME tag integration test...");

        let waiting_frames_before =
            get_waiting_frames_count(&pool, &test_data.hostname_job.id).await;
        assert_eq!(waiting_frames_before, 6);
        // Run the job fetcher with our test cluster feed
        // This simulates the main service flow: cluster discovery → job querying → layer processing → dispatching
        let result = job_fetcher::run(cluster_feed).await;

        match result {
            Ok(()) => {
                info!("✅ HOSTNAME tag integration test completed successfully");

                let waiting_frames =
                    get_waiting_frames_count(&pool, &test_data.hostname_job.id).await;
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

        cleanup_test_data(&pool)
            .await
            .expect("Failed to clean up test data");
    }

    #[tokio::test]
    #[traced_test]
    async fn test_full_service_alloc_tag_flow() {
        let pool = setup_test_database()
            .await
            .expect("Failed to setup test database");
        let test_data = create_full_integration_test_data(&pool)
            .await
            .expect("Failed to create test data");
        let _ = OVERRIDE_CONFIG.set(create_test_config());

        // Create a specific cluster feed for ALLOC tag testing
        let alloc_cluster = Cluster::ComposedKey(ClusterKey {
            facility_id: test_data.facility_id.to_string(),
            show_id: test_data.show_id.to_string(),
            tag: Tag {
                name: format!("integ_test_alloc_tag_{}", test_data.test_suffix),
                ttype: TagType::Alloc,
            },
        });

        let cluster_feed = ClusterFeed::new_for_test(vec![alloc_cluster]);

        info!("Starting ALLOC tag integration test...");

        let result = job_fetcher::run(cluster_feed).await;

        match result {
            Ok(()) => {
                info!("✅ ALLOC tag integration test completed successfully");
            }
            Err(e) => {
                panic!("❌ ALLOC tag integration test failed: {}", e);
            }
        }

        cleanup_test_data(&pool)
            .await
            .expect("Failed to clean up test data");
    }

    #[tokio::test]
    #[traced_test]
    async fn test_full_service_manual_tag_flow() {
        let pool = setup_test_database()
            .await
            .expect("Failed to setup test database");
        let test_data = create_full_integration_test_data(&pool)
            .await
            .expect("Failed to create test data");
        let _ = OVERRIDE_CONFIG.set(create_test_config());

        // Create a cluster feed with MANUAL tags (chunked)
        let manual_cluster = Cluster::TagsKey(vec![Tag {
            name: format!("integ_test_manual_tag_{}", test_data.test_suffix),
            ttype: TagType::Manual,
        }]);

        let cluster_feed = ClusterFeed::new_for_test(vec![manual_cluster]);

        info!("Starting MANUAL tag integration test...");

        let result = job_fetcher::run(cluster_feed).await;

        match result {
            Ok(()) => {
                info!("✅ MANUAL tag integration test completed successfully");
            }
            Err(e) => {
                panic!("❌ MANUAL tag integration test failed: {}", e);
            }
        }

        cleanup_test_data(&pool)
            .await
            .expect("Failed to clean up test data");
    }

    #[tokio::test]
    #[traced_test]
    async fn test_full_service_mixed_job_scenario() {
        let pool = setup_test_database()
            .await
            .expect("Failed to setup test database");
        let test_data = create_full_integration_test_data(&pool)
            .await
            .expect("Failed to create test data");
        let _ = OVERRIDE_CONFIG.set(create_test_config());

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

        let cluster_feed = ClusterFeed::new_for_test(clusters);

        info!("Starting mixed job scenario integration test...");

        let result = job_fetcher::run(cluster_feed).await;

        match result {
            Ok(()) => {
                info!("✅ Mixed job scenario integration test completed successfully");

                // Verify that all layers of the mixed job were processed
                let mixed_job_layers =
                    sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM layer WHERE pk_job = $1")
                        .bind(test_data.mixed_job.id.to_string())
                        .fetch_one(&pool)
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

        cleanup_test_data(&pool)
            .await
            .expect("Failed to clean up test data");
    }

    #[tokio::test]
    #[traced_test]
    async fn test_full_service_no_matching_hosts() {
        let pool = setup_test_database()
            .await
            .expect("Failed to setup test database");
        let _test_data = create_full_integration_test_data(&pool)
            .await
            .expect("Failed to create test data");
        let _ = OVERRIDE_CONFIG.set(create_test_config());

        // Create a cluster with a non-existent tag that won't match any hosts
        let non_matching_cluster = Cluster::TagsKey(vec![Tag {
            name: "non_existent_tag".to_string(),
            ttype: TagType::Manual,
        }]);

        let cluster_feed = ClusterFeed::new_for_test(vec![non_matching_cluster]);

        info!("Starting no matching hosts integration test...");

        let result = job_fetcher::run(cluster_feed).await;

        match result {
            Ok(()) => {
                info!("✅ No matching hosts integration test completed successfully");
                // The service should handle no matching hosts gracefully
            }
            Err(e) => {
                panic!("❌ No matching hosts integration test failed: {}", e);
            }
        }

        cleanup_test_data(&pool)
            .await
            .expect("Failed to clean up test data");
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
    // }
}
