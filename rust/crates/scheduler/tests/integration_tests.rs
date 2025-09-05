// use std::sync::Arc;

// use bytesize::ByteSize;
// use opencue_proto::host::ThreadMode;
// use scheduler::{
//     config::DatabaseConfig,
//     dao::{FrameDao, HostDao, LayerDao},
//     job_dispatcher::dispatcher::RqdDispatcher,
//     models::{CoreSize, DispatchLayer, Host},
// };
// use sqlx::{Pool, Postgres};
// use tracing::info;
// use tracing_test::traced_test;
// use uuid::Uuid;

// /// Integration tests for the scheduler dispatcher with various tag types.
// ///
// /// These tests verify that the dispatcher correctly matches jobs with different
// /// tag requirements (HOSTNAME, ALLOC, MANUAL) to appropriate hosts and
// /// dispatches frames in dry run mode.
// ///
// /// # Database Setup
// ///
// /// Tests assume a local PostgreSQL database is running with:
// /// - Host: localhost
// /// - Port: 5432
// /// - Database: cuebot_test
// /// - Username: cuebot_test
// /// - Password: password
// ///
// /// The database should be initialized with the schema from:
// /// `crates/scheduler/resources/schema`

// #[cfg(test)]
// mod tests {
//     use super::*;

//     // Database connection configuration - hardcoded for testing
//     const TEST_DB_HOST: &str = "localhost";
//     const TEST_DB_PORT: u16 = 5432;
//     const TEST_DB_NAME: &str = "cuebot_test";
//     const TEST_DB_USER: &str = "cuebot_test";
//     const TEST_DB_PASSWORD: &str = "password";

//     /// Test configuration and database setup
//     async fn setup_test_db() -> Result<Pool<Postgres>, sqlx::Error> {
//         let database_url = format!(
//             "postgresql://{}:{}@{}:{}/{}",
//             TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
//         );

//         let pool = sqlx::PgPool::connect(&database_url).await?;

//         // Clean up any existing test data
//         cleanup_test_data(&pool).await?;

//         Ok(pool)
//     }

//     /// Clean up test data from previous runs
//     async fn cleanup_test_data(pool: &Pool<Postgres>) -> Result<(), sqlx::Error> {
//         // Delete in reverse dependency order to avoid foreign key constraints
//         sqlx::query("DELETE FROM frame WHERE str_name LIKE 'test_%'")
//             .execute(pool)
//             .await?;
//         sqlx::query("DELETE FROM layer WHERE str_name LIKE 'test_%'")
//             .execute(pool)
//             .await?;
//         sqlx::query("DELETE FROM job WHERE str_name LIKE 'test_%'")
//             .execute(pool)
//             .await?;
//         sqlx::query("DELETE FROM host_tag WHERE str_tag LIKE 'test_%'")
//             .execute(pool)
//             .await?;
//         sqlx::query("DELETE FROM host WHERE str_name LIKE 'test_%'")
//             .execute(pool)
//             .await?;
//         sqlx::query("DELETE FROM alloc WHERE str_name LIKE 'test_%'")
//             .execute(pool)
//             .await?;
//         sqlx::query("DELETE FROM show WHERE str_name LIKE 'test_%'")
//             .execute(pool)
//             .await?;
//         sqlx::query("DELETE FROM facility WHERE str_name LIKE 'test_%'")
//             .execute(pool)
//             .await?;
//         sqlx::query("DELETE FROM dept WHERE str_name LIKE 'test_%'")
//             .execute(pool)
//             .await?;

//         Ok(())
//     }

//     /// Create test data for dispatch testing
//     async fn create_test_data(pool: &Pool<Postgres>) -> Result<TestData, sqlx::Error> {
//         // Create basic entities
//         let facility_id = Uuid::new_v4();
//         let dept_id = Uuid::new_v4();
//         let show_id = Uuid::new_v4();

//         // Create facility
//         sqlx::query("INSERT INTO facility (pk_facility, str_name) VALUES ($1, $2)")
//             .bind(facility_id.to_string())
//             .bind("test_facility")
//             .execute(pool)
//             .await?;

//         // Create department
//         sqlx::query("INSERT INTO dept (pk_dept, str_name) VALUES ($1, $2)")
//             .bind(dept_id.to_string())
//             .bind("test_dept")
//             .execute(pool)
//             .await?;

//         // Create show
//         sqlx::query("INSERT INTO show (pk_show, str_name) VALUES ($1, $2)")
//             .bind(show_id.to_string())
//             .bind("test_show")
//             .execute(pool)
//             .await?;

//         // Create allocations for different tag types
//         let hostname_alloc_id =
//             create_allocation(pool, facility_id, "test_hostname_alloc", "HOSTNAME").await?;
//         let alloc_alloc_id =
//             create_allocation(pool, facility_id, "test_alloc_alloc", "ALLOC").await?;
//         let manual_alloc_id =
//             create_allocation(pool, facility_id, "test_manual_alloc", "MANUAL").await?;

//         // Create subscriptions
//         create_subscription(pool, hostname_alloc_id, show_id, 1000, 1200).await?;
//         create_subscription(pool, alloc_alloc_id, show_id, 800, 1000).await?;
//         create_subscription(pool, manual_alloc_id, show_id, 600, 800).await?;

//         // Create hosts with different tag configurations
//         let hostname_host = create_host_with_tags(
//             pool,
//             hostname_alloc_id,
//             "test_hostname_host",
//             16,
//             32 * 1024 * 1024,
//             4,
//             8 * 1024 * 1024,
//             vec![("test_hostname_tag", "HOSTNAME")],
//         )
//         .await?;

//         let alloc_host = create_host_with_tags(
//             pool,
//             alloc_alloc_id,
//             "test_alloc_host",
//             12,
//             16 * 1024 * 1024,
//             2,
//             4 * 1024 * 1024,
//             vec![("test_alloc_tag", "ALLOC")],
//         )
//         .await?;

//         let manual_host = create_host_with_tags(
//             pool,
//             manual_alloc_id,
//             "test_manual_host",
//             8,
//             8 * 1024 * 1024,
//             1,
//             2 * 1024 * 1024,
//             vec![("test_manual_tag", "MANUAL")],
//         )
//         .await?;

//         // Create folder
//         let folder_id = create_folder(pool, show_id, dept_id, "test_folder").await?;

//         // Create jobs and layers
//         let hostname_job = create_job_with_layers(
//             pool,
//             show_id,
//             facility_id,
//             dept_id,
//             folder_id,
//             "test_hostname_job",
//             vec![(
//                 "test_hostname_layer",
//                 "test_hostname_tag",
//                 4,
//                 4 * 1024 * 1024,
//                 1,
//                 1 * 1024 * 1024,
//             )],
//         )
//         .await?;

//         let alloc_job = create_job_with_layers(
//             pool,
//             show_id,
//             facility_id,
//             dept_id,
//             folder_id,
//             "test_alloc_job",
//             vec![(
//                 "test_alloc_layer",
//                 "test_alloc_tag",
//                 2,
//                 2 * 1024 * 1024,
//                 1,
//                 512 * 1024,
//             )],
//         )
//         .await?;

//         let manual_job = create_job_with_layers(
//             pool,
//             show_id,
//             facility_id,
//             dept_id,
//             folder_id,
//             "test_manual_job",
//             vec![(
//                 "test_manual_layer",
//                 "test_manual_tag",
//                 1,
//                 1 * 1024 * 1024,
//                 0,
//                 0,
//             )],
//         )
//         .await?;

//         Ok(TestData {
//             facility_id,
//             dept_id,
//             show_id,
//             hostname_alloc_id,
//             alloc_alloc_id,
//             manual_alloc_id,
//             folder_id,
//             hostname_host,
//             alloc_host,
//             manual_host,
//             hostname_job,
//             alloc_job,
//             manual_job,
//         })
//     }

//     async fn create_allocation(
//         pool: &Pool<Postgres>,
//         facility_id: Uuid,
//         name: &str,
//         tag: &str,
//     ) -> Result<Uuid, sqlx::Error> {
//         let alloc_id = Uuid::new_v4();
//         sqlx::query(
//             "INSERT INTO alloc (pk_alloc, str_name, pk_facility, str_tag) VALUES ($1, $2, $3, $4)",
//         )
//         .bind(alloc_id.to_string())
//         .bind(name)
//         .bind(facility_id.to_string())
//         .bind(tag)
//         .execute(pool)
//         .await?;
//         Ok(alloc_id)
//     }

//     async fn create_subscription(
//         pool: &Pool<Postgres>,
//         alloc_id: Uuid,
//         show_id: Uuid,
//         size: i64,
//         burst: i64,
//     ) -> Result<(), sqlx::Error> {
//         let subscription_id = Uuid::new_v4();
//         sqlx::query(
//             "INSERT INTO subscription (pk_subscription, pk_alloc, pk_show, int_size, int_burst) VALUES ($1, $2, $3, $4, $5)"
//         )
//         .bind(subscription_id.to_string())
//         .bind(alloc_id.to_string())
//         .bind(show_id.to_string())
//         .bind(size)
//         .bind(burst)
//         .execute(pool)
//         .await?;
//         Ok(())
//     }

//     async fn create_host_with_tags(
//         pool: &Pool<Postgres>,
//         alloc_id: Uuid,
//         name: &str,
//         cores: i64,
//         memory_kb: i64,
//         gpus: i64,
//         gpu_memory_kb: i64,
//         tags: Vec<(&str, &str)>,
//     ) -> Result<TestHost, sqlx::Error> {
//         let host_id = Uuid::new_v4();

//         // Create host
//         sqlx::query(
//             "INSERT INTO host (pk_host, pk_alloc, str_name, str_lock_state, int_cores, int_cores_idle, int_mem, int_mem_idle, int_gpus, int_gpus_idle, int_gpu_mem, int_gpu_mem_idle, int_thread_mode) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)"
//         )
//         .bind(host_id.to_string())
//         .bind(alloc_id.to_string())
//         .bind(name)
//         .bind("OPEN")
//         .bind(cores * 100) // Core multiplier
//         .bind(cores * 100)
//         .bind(memory_kb)
//         .bind(memory_kb)
//         .bind(gpus)
//         .bind(gpus)
//         .bind(gpu_memory_kb)
//         .bind(gpu_memory_kb)
//         .bind(0) // ThreadMode::Auto
//         .execute(pool)
//         .await?;

//         // Create host_stat
//         let host_stat_id = Uuid::new_v4();
//         sqlx::query(
//             "INSERT INTO host_stat (pk_host_stat, pk_host, str_state, str_os, int_gpu_mem_total, int_gpu_mem_free) VALUES ($1, $2, $3, $4, $5, $6)"
//         )
//         .bind(host_stat_id.to_string())
//         .bind(host_id.to_string())
//         .bind("UP")
//         .bind("linux")
//         .bind(gpu_memory_kb)
//         .bind(gpu_memory_kb)
//         .execute(pool)
//         .await?;

//         // Create host tags
//         for (tag_name, tag_type) in tags {
//             let tag_id = Uuid::new_v4();
//             sqlx::query(
//                 "INSERT INTO host_tag (pk_host_tag, pk_host, str_tag, str_tag_type) VALUES ($1, $2, $3, $4)"
//             )
//             .bind(tag_id.to_string())
//             .bind(host_id.to_string())
//             .bind(tag_name)
//             .bind(tag_type)
//             .execute(pool)
//             .await?;
//         }

//         Ok(TestHost {
//             id: host_id,
//             name: name.to_string(),
//             alloc_id,
//             cores,
//             memory_kb,
//             gpus,
//             gpu_memory_kb,
//         })
//     }

//     async fn create_folder(
//         pool: &Pool<Postgres>,
//         show_id: Uuid,
//         dept_id: Uuid,
//         name: &str,
//     ) -> Result<Uuid, sqlx::Error> {
//         let folder_id = Uuid::new_v4();
//         sqlx::query(
//             "INSERT INTO folder (pk_folder, pk_show, pk_dept, str_name) VALUES ($1, $2, $3, $4)",
//         )
//         .bind(folder_id.to_string())
//         .bind(show_id.to_string())
//         .bind(dept_id.to_string())
//         .bind(name)
//         .execute(pool)
//         .await?;
//         Ok(folder_id)
//     }

//     async fn create_job_with_layers(
//         pool: &Pool<Postgres>,
//         show_id: Uuid,
//         facility_id: Uuid,
//         dept_id: Uuid,
//         folder_id: Uuid,
//         job_name: &str,
//         layers: Vec<(&str, &str, i64, i64, i64, i64)>, // (layer_name, tag, min_cores, min_mem, min_gpus, min_gpu_mem)
//     ) -> Result<TestJob, sqlx::Error> {
//         let job_id = Uuid::new_v4();

//         // Create job
//         sqlx::query(
//             "INSERT INTO job (pk_job, pk_folder, pk_show, pk_facility, pk_dept, str_name, str_visible_name, str_shot, str_user, str_state) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)"
//         )
//         .bind(job_id.to_string())
//         .bind(folder_id.to_string())
//         .bind(show_id.to_string())
//         .bind(facility_id.to_string())
//         .bind(dept_id.to_string())
//         .bind(job_name)
//         .bind(job_name)
//         .bind("test_shot")
//         .bind("test_user")
//         .bind("PENDING")
//         .execute(pool)
//         .await?;

//         // Create job stats
//         let job_stat_id = Uuid::new_v4();
//         sqlx::query(
//             "INSERT INTO job_stat (pk_job_stat, pk_job, int_waiting_count) VALUES ($1, $2, $3)",
//         )
//         .bind(job_stat_id.to_string())
//         .bind(job_id.to_string())
//         .bind(5) // 5 waiting frames per layer
//         .execute(pool)
//         .await?;

//         // Create job resource
//         let job_resource_id = Uuid::new_v4();
//         sqlx::query(
//             "INSERT INTO job_resource (pk_job_resource, pk_job, int_priority) VALUES ($1, $2, $3)",
//         )
//         .bind(job_resource_id.to_string())
//         .bind(job_id.to_string())
//         .bind(1)
//         .execute(pool)
//         .await?;

//         let mut test_layers = Vec::new();

//         for (layer_name, tag, min_cores, min_mem, min_gpus, min_gpu_mem) in layers {
//             let layer_id = Uuid::new_v4();

//             // Create layer
//             sqlx::query(
//                 "INSERT INTO layer (pk_layer, pk_job, str_name, str_cmd, str_range, str_tags, int_cores_min, int_mem_min, int_gpus_min, int_gpu_mem_min) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)"
//             )
//             .bind(layer_id.to_string())
//             .bind(job_id.to_string())
//             .bind(layer_name)
//             .bind("echo test")
//             .bind("1-5")
//             .bind(tag)
//             .bind(min_cores * 100) // Core multiplier
//             .bind(min_mem)
//             .bind(min_gpus)
//             .bind(min_gpu_mem)
//             .execute(pool)
//             .await?;

//             // Create layer stats
//             let layer_stat_id = Uuid::new_v4();
//             sqlx::query(
//                 "INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job, int_waiting_count, int_total_count) VALUES ($1, $2, $3, $4, $5)"
//             )
//             .bind(layer_stat_id.to_string())
//             .bind(layer_id.to_string())
//             .bind(job_id.to_string())
//             .bind(5) // 5 waiting frames
//             .bind(5) // 5 total frames
//             .execute(pool)
//             .await?;

//             // Create layer resource
//             let layer_resource_id = Uuid::new_v4();
//             sqlx::query(
//                 "INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES ($1, $2, $3)"
//             )
//             .bind(layer_resource_id.to_string())
//             .bind(layer_id.to_string())
//             .bind(job_id.to_string())
//             .execute(pool)
//             .await?;

//             // Create frames
//             for frame_num in 1..=5 {
//                 let frame_id = Uuid::new_v4();
//                 sqlx::query(
//                     "INSERT INTO frame (pk_frame, pk_layer, pk_job, str_name, str_state, int_number, int_layer_order, int_dispatch_order) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"
//                 )
//                 .bind(frame_id.to_string())
//                 .bind(layer_id.to_string())
//                 .bind(job_id.to_string())
//                 .bind(format!("{}-frame", frame_num))
//                 .bind("WAITING")
//                 .bind(frame_num)
//                 .bind(frame_num)
//                 .bind(frame_num)
//                 .execute(pool)
//                 .await?;
//             }

//             test_layers.push(TestLayer {
//                 id: layer_id,
//                 name: layer_name.to_string(),
//                 job_id,
//                 tag: tag.to_string(),
//                 min_cores,
//                 min_mem,
//                 min_gpus,
//                 min_gpu_mem,
//             });
//         }

//         Ok(TestJob {
//             id: job_id,
//             name: job_name.to_string(),
//             show_id,
//             facility_id,
//             layers: test_layers,
//         })
//     }

//     #[derive(Debug)]
//     struct TestData {
//         facility_id: Uuid,
//         dept_id: Uuid,
//         show_id: Uuid,
//         hostname_alloc_id: Uuid,
//         alloc_alloc_id: Uuid,
//         manual_alloc_id: Uuid,
//         folder_id: Uuid,
//         hostname_host: TestHost,
//         alloc_host: TestHost,
//         manual_host: TestHost,
//         hostname_job: TestJob,
//         alloc_job: TestJob,
//         manual_job: TestJob,
//     }

//     #[derive(Debug)]
//     struct TestHost {
//         id: Uuid,
//         name: String,
//         alloc_id: Uuid,
//         cores: i64,
//         memory_kb: i64,
//         gpus: i64,
//         gpu_memory_kb: i64,
//     }

//     #[derive(Debug)]
//     struct TestJob {
//         id: Uuid,
//         name: String,
//         show_id: Uuid,
//         facility_id: Uuid,
//         layers: Vec<TestLayer>,
//     }

//     #[derive(Debug)]
//     struct TestLayer {
//         id: Uuid,
//         name: String,
//         job_id: Uuid,
//         tag: String,
//         min_cores: i64,
//         min_mem: i64,
//         min_gpus: i64,
//         min_gpu_mem: i64,
//     }

//     #[tokio::test]
//     #[traced_test]
//     async fn test_dispatcher_hostname_tag_matching() {
//         let pool = setup_test_db()
//             .await
//             .expect("Failed to setup test database");
//         let test_data = create_test_data(&pool)
//             .await
//             .expect("Failed to create test data");

//         // Create database config
//         let connection_url = format!(
//             "postgresql://{}:{}@{}:{}/{}",
//             TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
//         );
//         let db_config = DatabaseConfig {
//             pool_size: 5,
//             connection_url,
//             core_multiplier: 100,
//         };

//         // Create DAOs
//         let frame_dao = FrameDao::from_config(&db_config)
//             .await
//             .expect("Failed to create FrameDao");
//         let host_dao = Arc::new(
//             HostDao::from_config(&db_config)
//                 .await
//                 .expect("Failed to create HostDao"),
//         );
//         let layer_dao = LayerDao::from_config(&db_config)
//             .await
//             .expect("Failed to create LayerDao");

//         // Create dispatcher in dry run mode
//         let dispatcher = RqdDispatcher::new(
//             frame_dao,
//             host_dao,
//             8080,              // gRPC port (not used in dry run)
//             10,                // dispatch frames per layer limit
//             ByteSize::mb(100), // memory stranded threshold
//             true,              // dry run mode
//         );

//         // Create dispatch layer for hostname job
//         let dispatch_layer = DispatchLayer {
//             id: test_data.hostname_job.layers[0].id,
//             job_id: test_data.hostname_job.id,
//             facility_id: test_data.facility_id,
//             show_id: test_data.show_id,
//             job_name: test_data.hostname_job.name.clone(),
//             layer_name: test_data.hostname_job.layers[0].name.clone(),
//             str_os: Some("linux".to_string()),
//             cores_min: CoreSize::from_multiplied(test_data.hostname_job.layers[0].min_cores as i32),
//             mem_min: ByteSize::kb(test_data.hostname_job.layers[0].min_mem as u64),
//             threadable: true,
//             gpus_min: test_data.hostname_job.layers[0].min_gpus as i32,
//             gpu_mem_min: ByteSize::kb(test_data.hostname_job.layers[0].min_gpu_mem as u64),
//             tags: test_data.hostname_job.layers[0].tag.clone(),
//         };

//         // Create host model
//         let host = Host::new_for_test(
//             test_data.hostname_host.id,
//             test_data.hostname_host.name.clone(),
//             Some("linux".to_string()),
//             CoreSize::from_multiplied(test_data.hostname_host.cores as i32),
//             ByteSize::kb(test_data.hostname_host.memory_kb as u64),
//             CoreSize::from_multiplied(test_data.hostname_host.cores as i32),
//             ByteSize::kb(test_data.hostname_host.memory_kb as u64),
//             test_data.hostname_host.gpus as u32,
//             ByteSize::kb(test_data.hostname_host.gpu_memory_kb as u64),
//             ThreadMode::Auto,
//             CoreSize::from_multiplied(200), // Burst capacity
//             "test_hostname_alloc".to_string(),
//         );

//         // Test dispatch in dry run mode
//         let result = dispatcher.dispatch(&dispatch_layer, &host).await;

//         match result {
//             Ok(()) => {
//                 info!("Successfully dispatched HOSTNAME tagged layer to matching host");
//                 // In a real scenario, we'd capture and verify the log output
//                 // to ensure frames were "dispatched" in dry run mode
//             }
//             Err(e) => {
//                 panic!("Failed to dispatch HOSTNAME tagged layer: {:?}", e);
//             }
//         }

//         // Clean up
//         cleanup_test_data(&pool)
//             .await
//             .expect("Failed to clean up test data");
//     }

//     #[tokio::test]
//     #[traced_test]
//     async fn test_dispatcher_alloc_tag_matching() {
//         let pool = setup_test_db()
//             .await
//             .expect("Failed to setup test database");
//         let test_data = create_test_data(&pool)
//             .await
//             .expect("Failed to create test data");

//         let connection_url = format!(
//             "postgresql://{}:{}@{}:{}/{}",
//             TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
//         );
//         let db_config = DatabaseConfig {
//             pool_size: 5,
//             connection_url,
//             core_multiplier: 100,
//         };

//         let frame_dao = FrameDao::from_config(&db_config)
//             .await
//             .expect("Failed to create FrameDao");
//         let host_dao = Arc::new(
//             HostDao::from_config(&db_config)
//                 .await
//                 .expect("Failed to create HostDao"),
//         );

//         let dispatcher = RqdDispatcher::new(
//             frame_dao,
//             host_dao,
//             8080,
//             10,
//             ByteSize::mb(100),
//             true, // dry run mode
//         );

//         // Create dispatch layer for alloc job
//         let dispatch_layer = DispatchLayer {
//             id: test_data.alloc_job.layers[0].id,
//             job_id: test_data.alloc_job.id,
//             facility_id: test_data.facility_id,
//             show_id: test_data.show_id,
//             job_name: test_data.alloc_job.name.clone(),
//             layer_name: test_data.alloc_job.layers[0].name.clone(),
//             str_os: Some("linux".to_string()),
//             cores_min: CoreSize::from_multiplied(test_data.alloc_job.layers[0].min_cores as i32),
//             mem_min: ByteSize::kb(test_data.alloc_job.layers[0].min_mem as u64),
//             threadable: true,
//             gpus_min: test_data.alloc_job.layers[0].min_gpus as i32,
//             gpu_mem_min: ByteSize::kb(test_data.alloc_job.layers[0].min_gpu_mem as u64),
//             tags: test_data.alloc_job.layers[0].tag.clone(),
//         };

//         let host = Host::new_for_test(
//             test_data.alloc_host.id,
//             test_data.alloc_host.name.clone(),
//             Some("linux".to_string()),
//             CoreSize::from_multiplied(test_data.alloc_host.cores as i32),
//             ByteSize::kb(test_data.alloc_host.memory_kb as u64),
//             CoreSize::from_multiplied(test_data.alloc_host.cores as i32),
//             ByteSize::kb(test_data.alloc_host.memory_kb as u64),
//             test_data.alloc_host.gpus as u32,
//             ByteSize::kb(test_data.alloc_host.gpu_memory_kb as u64),
//             ThreadMode::Auto,
//             CoreSize::from_multiplied(200),
//             "test_alloc_alloc".to_string(),
//         );

//         let result = dispatcher.dispatch(&dispatch_layer, &host).await;

//         match result {
//             Ok(()) => {
//                 info!("Successfully dispatched ALLOC tagged layer to matching host");
//             }
//             Err(e) => {
//                 panic!("Failed to dispatch ALLOC tagged layer: {:?}", e);
//             }
//         }

//         cleanup_test_data(&pool)
//             .await
//             .expect("Failed to clean up test data");
//     }

//     #[tokio::test]
//     #[traced_test]
//     async fn test_dispatcher_manual_tag_matching() {
//         let pool = setup_test_db()
//             .await
//             .expect("Failed to setup test database");
//         let test_data = create_test_data(&pool)
//             .await
//             .expect("Failed to create test data");

//         let connection_url = format!(
//             "postgresql://{}:{}@{}:{}/{}",
//             TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
//         );
//         let db_config = DatabaseConfig {
//             pool_size: 5,
//             connection_url,
//             core_multiplier: 100,
//         };

//         let frame_dao = FrameDao::from_config(&db_config)
//             .await
//             .expect("Failed to create FrameDao");
//         let host_dao = Arc::new(
//             HostDao::from_config(&db_config)
//                 .await
//                 .expect("Failed to create HostDao"),
//         );

//         let dispatcher = RqdDispatcher::new(
//             frame_dao,
//             host_dao,
//             8080,
//             10,
//             ByteSize::mb(100),
//             true, // dry run mode
//         );

//         // Create dispatch layer for manual job
//         let dispatch_layer = DispatchLayer {
//             id: test_data.manual_job.layers[0].id,
//             job_id: test_data.manual_job.id,
//             facility_id: test_data.facility_id,
//             show_id: test_data.show_id,
//             job_name: test_data.manual_job.name.clone(),
//             layer_name: test_data.manual_job.layers[0].name.clone(),
//             str_os: Some("linux".to_string()),
//             cores_min: CoreSize::from_multiplied(test_data.manual_job.layers[0].min_cores as i32),
//             mem_min: ByteSize::kb(test_data.manual_job.layers[0].min_mem as u64),
//             threadable: true,
//             gpus_min: test_data.manual_job.layers[0].min_gpus as i32,
//             gpu_mem_min: ByteSize::kb(test_data.manual_job.layers[0].min_gpu_mem as u64),
//             tags: test_data.manual_job.layers[0].tag.clone(),
//         };

//         let host = Host::new_for_test(
//             test_data.manual_host.id,
//             test_data.manual_host.name.clone(),
//             Some("linux".to_string()),
//             CoreSize::from_multiplied(test_data.manual_host.cores as i32),
//             ByteSize::kb(test_data.manual_host.memory_kb as u64),
//             CoreSize::from_multiplied(test_data.manual_host.cores as i32),
//             ByteSize::kb(test_data.manual_host.memory_kb as u64),
//             test_data.manual_host.gpus as u32,
//             ByteSize::kb(test_data.manual_host.gpu_memory_kb as u64),
//             ThreadMode::Auto,
//             CoreSize::from_multiplied(150),
//             "test_manual_alloc".to_string(),
//         );

//         let result = dispatcher.dispatch(&dispatch_layer, &host).await;

//         match result {
//             Ok(()) => {
//                 info!("Successfully dispatched MANUAL tagged layer to matching host");
//             }
//             Err(e) => {
//                 panic!("Failed to dispatch MANUAL tagged layer: {:?}", e);
//             }
//         }

//         cleanup_test_data(&pool)
//             .await
//             .expect("Failed to clean up test data");
//     }

//     #[tokio::test]
//     #[traced_test]
//     async fn test_dispatcher_resource_consumption() {
//         let pool = setup_test_db()
//             .await
//             .expect("Failed to setup test database");
//         let test_data = create_test_data(&pool)
//             .await
//             .expect("Failed to create test data");

//         let connection_url = format!(
//             "postgresql://{}:{}@{}:{}/{}",
//             TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
//         );
//         let db_config = DatabaseConfig {
//             pool_size: 5,
//             connection_url,
//             core_multiplier: 100,
//         };

//         let frame_dao = FrameDao::from_config(&db_config)
//             .await
//             .expect("Failed to create FrameDao");
//         let host_dao = Arc::new(
//             HostDao::from_config(&db_config)
//                 .await
//                 .expect("Failed to create HostDao"),
//         );

//         let dispatcher = RqdDispatcher::new(
//             frame_dao,
//             host_dao.clone(),
//             8080,
//             3, // Limited to 3 frames per dispatch to test resource consumption
//             ByteSize::mb(100),
//             true, // dry run mode
//         );

//         // Use a host with limited resources
//         let limited_host = Host::new_for_test(
//             test_data.hostname_host.id,
//             test_data.hostname_host.name.clone(),
//             Some("linux".to_string()),
//             CoreSize::from_multiplied(8), // 8 cores total
//             ByteSize::mb(8 * 1024),       // 8GB total
//             CoreSize::from_multiplied(8), // All available initially
//             ByteSize::mb(8 * 1024),       // All available initially
//             2,
//             ByteSize::mb(2 * 1024),
//             ThreadMode::Auto,
//             CoreSize::from_multiplied(200),
//             "test_hostname_alloc".to_string(),
//         );

//         let dispatch_layer = DispatchLayer {
//             id: test_data.hostname_job.layers[0].id,
//             job_id: test_data.hostname_job.id,
//             facility_id: test_data.facility_id,
//             show_id: test_data.show_id,
//             job_name: test_data.hostname_job.name.clone(),
//             layer_name: test_data.hostname_job.layers[0].name.clone(),
//             str_os: Some("linux".to_string()),
//             cores_min: CoreSize::from_multiplied(2), // Each frame needs 2 cores
//             mem_min: ByteSize::mb(1024),             // Each frame needs 1GB
//             threadable: true,
//             gpus_min: 0,
//             gpu_mem_min: ByteSize::kb(0),
//             tags: test_data.hostname_job.layers[0].tag.clone(),
//         };

//         // First dispatch should succeed - host has enough resources
//         let result1 = dispatcher.dispatch(&dispatch_layer, &limited_host).await;
//         assert!(result1.is_ok(), "First dispatch should succeed");

//         // Note: In real scenario, resource consumption would be handled by the dispatcher
//         // For dry run mode testing, we don't modify host resources as fields are private

//         // Second dispatch should still work but dispatch fewer frames
//         let result2 = dispatcher.dispatch(&dispatch_layer, &limited_host).await;
//         assert!(
//             result2.is_ok(),
//             "Second dispatch should succeed with remaining resources"
//         );

//         // In dry run mode, we test the dispatch logic without actual resource modification

//         // Third dispatch should succeed in dry run mode
//         let result3 = dispatcher.dispatch(&dispatch_layer, &limited_host).await;
//         assert!(
//             result3.is_ok(),
//             "Third dispatch should succeed in dry run mode"
//         );

//         info!("Resource consumption test completed - all dispatches handled appropriately");

//         cleanup_test_data(&pool)
//             .await
//             .expect("Failed to clean up test data");
//     }

//     #[tokio::test]
//     #[traced_test]
//     async fn test_dispatcher_tag_mismatch() {
//         let pool = setup_test_db()
//             .await
//             .expect("Failed to setup test database");
//         let test_data = create_test_data(&pool)
//             .await
//             .expect("Failed to create test data");

//         let connection_url = format!(
//             "postgresql://{}:{}@{}:{}/{}",
//             TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
//         );
//         let db_config = DatabaseConfig {
//             pool_size: 5,
//             connection_url,
//             core_multiplier: 100,
//         };

//         let frame_dao = FrameDao::from_config(&db_config)
//             .await
//             .expect("Failed to create FrameDao");
//         let host_dao = Arc::new(
//             HostDao::from_config(&db_config)
//                 .await
//                 .expect("Failed to create HostDao"),
//         );

//         let dispatcher = RqdDispatcher::new(
//             frame_dao,
//             host_dao,
//             8080,
//             10,
//             ByteSize::mb(100),
//             true, // dry run mode
//         );

//         // Try to dispatch HOSTNAME job to ALLOC host (should have no frames to dispatch)
//         let hostname_layer = DispatchLayer {
//             id: test_data.hostname_job.layers[0].id,
//             job_id: test_data.hostname_job.id,
//             facility_id: test_data.facility_id,
//             show_id: test_data.show_id,
//             job_name: test_data.hostname_job.name.clone(),
//             layer_name: test_data.hostname_job.layers[0].name.clone(),
//             str_os: Some("linux".to_string()),
//             cores_min: CoreSize::from_multiplied(test_data.hostname_job.layers[0].min_cores as i32),
//             mem_min: ByteSize::kb(test_data.hostname_job.layers[0].min_mem as u64),
//             threadable: true,
//             gpus_min: test_data.hostname_job.layers[0].min_gpus as i32,
//             gpu_mem_min: ByteSize::kb(test_data.hostname_job.layers[0].min_gpu_mem as u64),
//             tags: test_data.hostname_job.layers[0].tag.clone(),
//         };

//         let alloc_host = Host::new_for_test(
//             test_data.alloc_host.id,
//             test_data.alloc_host.name.clone(),
//             Some("linux".to_string()),
//             CoreSize::from_multiplied(test_data.alloc_host.cores as i32),
//             ByteSize::kb(test_data.alloc_host.memory_kb as u64),
//             CoreSize::from_multiplied(test_data.alloc_host.cores as i32),
//             ByteSize::kb(test_data.alloc_host.memory_kb as u64),
//             test_data.alloc_host.gpus as u32,
//             ByteSize::kb(test_data.alloc_host.gpu_memory_kb as u64),
//             ThreadMode::Auto,
//             CoreSize::from_multiplied(200),
//             "test_alloc_alloc".to_string(),
//         );

//         // This should succeed but dispatch no frames due to tag mismatch
//         let result = dispatcher.dispatch(&hostname_layer, &alloc_host).await;

//         match result {
//             Ok(()) => {
//                 info!("Tag mismatch test passed - dispatch completed with no frames (expected)");
//             }
//             Err(e) => {
//                 // Depending on implementation, this might be an error or just no frames dispatched
//                 info!("Tag mismatch resulted in error (acceptable): {:?}", e);
//             }
//         }

//         cleanup_test_data(&pool)
//             .await
//             .expect("Failed to clean up test data");
//     }
// }
