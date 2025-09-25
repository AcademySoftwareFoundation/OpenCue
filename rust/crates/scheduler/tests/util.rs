use miette::Result;
use rand::{
    Rng,
    seq::{IteratorRandom, SliceRandom},
    thread_rng,
};
use scheduler::{
    cluster::Cluster,
    cluster_key::{ClusterKey, Tag, TagType},
    config::{Config, DatabaseConfig, LoggingConfig, QueueConfig, RqdConfig},
};
use std::time::Duration;
use tracing::Level;
use uuid::Uuid;

use std::sync::Arc;

use sqlx::{Pool, Postgres, Transaction, postgres::PgPoolOptions};
use tokio::sync::OnceCell;

// Database connection configuration - hardcoded for testing
const TEST_DB_HOST: &str = "localhost";
const TEST_DB_PORT: u16 = 5432;
const TEST_DB_NAME: &str = "cuebot";
const TEST_DB_USER: &str = "cuebot";
const TEST_DB_PASSWORD: &str = "cuebot_password";

static TEST_CONNECTION_POOL: OnceCell<Arc<Pool<Postgres>>> = OnceCell::const_new();

pub async fn test_connection_pool() -> Result<Arc<Pool<Postgres>>, sqlx::Error> {
    let database_url = format!(
        "postgresql://{}:{}@{}:{}/{}",
        TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
    );
    TEST_CONNECTION_POOL
        .get_or_try_init(|| async {
            let pool = PgPoolOptions::new()
                .max_connections(2)
                // .idle_timeout(Some(Duration::from_secs(1)))
                // .acquire_timeout(Duration::from_secs(30))
                .connect(&database_url)
                .await?;
            Ok(Arc::new(pool))
        })
        .await
        .map(Arc::clone)
}

pub fn create_test_config() -> Config {
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
            // Won't influence tests as it's only read by main,
            //for test use #[tokio::test(flavor = "multi_thread", worker_threads = 8)]
            worker_threads: 2,
            dispatch_frames_per_layer_limit: 8, // Small limit for testing
            core_multiplier: 100,
            memory_stranded_threshold: bytesize::ByteSize::mb(100),
            job_back_off_duration: Duration::from_secs(10),
            stream: scheduler::config::StreamConfig {
                cluster_buffer_size: 1,
                job_buffer_size: 2,
            },
            manual_tags_chunk_size: 10,
            hostname_tags_chunk_size: 20,
            host_candidate_attemps_per_layer: 5,
            empty_job_cycles_before_quiting: Some(20),
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

#[derive(Debug)]
pub struct TestData {
    pub test_prefix: String,
    pub clusters: Vec<Cluster>,
    pub jobs: Vec<TestJob>,
    pub hosts: Vec<TestHost>,
}

#[derive(Debug)]
struct TestHost {
    id: Uuid,
    name: String,
    alloc_id: Uuid,
}

#[derive(Debug)]
struct TestJob {
    id: Uuid,
    name: String,
    layers: Vec<TestLayer>,
    frames_by_layer: usize,
}

#[derive(Debug)]
struct TestLayer {
    id: Uuid,
    name: String,
    tag: Vec<String>,
}

pub async fn clean_up_test_data(test_prefix: &str) -> Result<(), sqlx::Error> {
    // let pool = test_connection_pool().await?;
    // let mut tx = pool.begin().await?;

    // // Delete proc (references frames)
    // sqlx::query(
    //     "DELETE FROM proc WHERE pk_frame IN (
    //         SELECT f.pk_frame FROM frame f
    //         JOIN layer l ON f.pk_layer = l.pk_layer
    //         JOIN job j ON f.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete frame_history (references frames)
    // sqlx::query(
    //     "DELETE FROM frame_history WHERE pk_frame IN (
    //         SELECT f.pk_frame FROM frame f
    //         JOIN layer l ON f.pk_layer = l.pk_layer
    //         JOIN job j ON f.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete frames (references layers)
    // sqlx::query(
    //     "DELETE FROM frame WHERE pk_frame IN (
    //         SELECT f.pk_frame FROM frame f
    //         JOIN layer l ON f.pk_layer = l.pk_layer
    //         JOIN job j ON f.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete layer_output (references layers)
    // sqlx::query(
    //     "DELETE FROM layer_output WHERE pk_layer IN (
    //         SELECT l.pk_layer FROM layer l
    //         JOIN job j ON l.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete layer_env (references layers)
    // sqlx::query(
    //     "DELETE FROM layer_env WHERE pk_layer IN (
    //         SELECT l.pk_layer FROM layer l
    //         JOIN job j ON l.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete layer_mem (references layers)
    // sqlx::query(
    //     "DELETE FROM layer_mem WHERE pk_layer IN (
    //         SELECT l.pk_layer FROM layer l
    //         JOIN job j ON l.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete layer_usage (references layers)
    // sqlx::query(
    //     "DELETE FROM layer_usage WHERE pk_layer IN (
    //         SELECT l.pk_layer FROM layer l
    //         JOIN job j ON l.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete layer_stat (references layers)
    // sqlx::query(
    //     "DELETE FROM layer_stat WHERE pk_layer IN (
    //         SELECT l.pk_layer FROM layer l
    //         JOIN job j ON l.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete layer_resource (references layers)
    // sqlx::query(
    //     "DELETE FROM layer_resource WHERE pk_layer IN (
    //         SELECT l.pk_layer FROM layer l
    //         JOIN job j ON l.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete layer_history (references layers)
    // sqlx::query(
    //     "DELETE FROM layer_history WHERE pk_layer IN (
    //         SELECT l.pk_layer FROM layer l
    //         JOIN job j ON l.pk_job = j.pk_job
    //         WHERE j.str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete layers (references jobs)
    // sqlx::query(
    //     "DELETE FROM layer WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete job_local (references jobs and hosts)
    // sqlx::query(
    //     "DELETE FROM job_local WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete job_env (references jobs)
    // sqlx::query(
    //     "DELETE FROM job_env WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete job_mem (references jobs)
    // sqlx::query(
    //     "DELETE FROM job_mem WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete job_usage (references jobs)
    // sqlx::query(
    //     "DELETE FROM job_usage WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete job_stat (references jobs)
    // sqlx::query(
    //     "DELETE FROM job_stat WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete job_resource (references jobs)
    // sqlx::query(
    //     "DELETE FROM job_resource WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete job_post (references jobs)
    // sqlx::query(
    //     "DELETE FROM job_post WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete job_history (references jobs)
    // sqlx::query(
    //     "DELETE FROM job_history WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete depend (references jobs)
    // sqlx::query(
    //     "DELETE FROM depend WHERE pk_job_depend_on IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     ) OR pk_job_depend_er IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete comments (references jobs)
    // sqlx::query(
    //     "DELETE FROM comments WHERE pk_job IN (
    //         SELECT pk_job FROM job WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete jobs (references folders/shows/facilities/depts)
    // sqlx::query("DELETE FROM job WHERE str_name LIKE $1")
    //     .bind(format!("{}%", test_prefix))
    //     .execute(&mut *tx)
    //     .await?;

    // // Delete host_local (references hosts)
    // sqlx::query(
    //     "DELETE FROM host_local WHERE pk_host IN (
    //         SELECT pk_host FROM host WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete host_tag (references hosts)
    // sqlx::query(
    //     "DELETE FROM host_tag WHERE pk_host IN (
    //         SELECT pk_host FROM host WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete host_stat (references hosts)
    // sqlx::query(
    //     "DELETE FROM host_stat WHERE pk_host IN (
    //         SELECT pk_host FROM host WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete deed (references hosts and owners)
    // sqlx::query(
    //     "DELETE FROM deed WHERE pk_host IN (
    //         SELECT pk_host FROM host WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete hosts (references allocations)
    // sqlx::query("DELETE FROM host WHERE str_name LIKE $1")
    //     .bind(format!("{}%", test_prefix))
    //     .execute(&mut *tx)
    //     .await?;

    // // Delete owner (references shows)
    // sqlx::query(
    //     "DELETE FROM owner WHERE pk_show IN (
    //         SELECT pk_show FROM show WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete folder_resource (references folders)
    // sqlx::query(
    //     "DELETE FROM folder_resource WHERE pk_folder IN (
    //         SELECT pk_folder FROM folder WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete folders (references shows and depts)
    // sqlx::query("DELETE FROM folder WHERE str_name LIKE $1")
    //     .bind(format!("{}%", test_prefix))
    //     .execute(&mut *tx)
    //     .await?;

    // // Delete subscriptions (references allocations and shows)
    // sqlx::query(
    //     "DELETE FROM subscription WHERE pk_alloc IN (
    //         SELECT pk_alloc FROM alloc WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete allocations (references facilities)
    // sqlx::query("DELETE FROM alloc WHERE str_name LIKE $1")
    //     .bind(format!("{}%", test_prefix))
    //     .execute(&mut *tx)
    //     .await?;

    // // Delete show_service (references shows)
    // sqlx::query(
    //     "DELETE FROM show_service WHERE pk_show IN (
    //         SELECT pk_show FROM show WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete show_alias (references shows)
    // sqlx::query(
    //     "DELETE FROM show_alias WHERE pk_show IN (
    //         SELECT pk_show FROM show WHERE str_name LIKE $1
    //     )",
    // )
    // .bind(format!("{}%", test_prefix))
    // .execute(&mut *tx)
    // .await?;

    // // Delete shows
    // sqlx::query("DELETE FROM show WHERE str_name LIKE $1")
    //     .bind(format!("{}%", test_prefix))
    //     .execute(&mut *tx)
    //     .await?;

    // // Delete departments
    // sqlx::query("DELETE FROM dept WHERE str_name LIKE $1")
    //     .bind(format!("{}%", test_prefix))
    //     .execute(&mut *tx)
    //     .await?;

    // // Delete facilities
    // sqlx::query("DELETE FROM facility WHERE str_name LIKE $1")
    //     .bind(format!("{}%", test_prefix))
    //     .execute(&mut *tx)
    //     .await?;

    // tx.commit().await?;
    Ok(())
}

pub async fn create_test_data(
    test_name: &str,
    test_id: &str,
    job_count: usize,
    host_count: usize,
    layer_count: usize,
    frames_per_layer_count: usize,
    tag_count: usize,
) -> Result<TestData, sqlx::Error> {
    assert!(tag_count >= 4, "Minimum tag_count is 4");

    // Create basic entities
    let facility_id = Uuid::new_v4();
    let dept_id = Uuid::new_v4();
    let show_id = Uuid::new_v4();
    let pool = test_connection_pool().await?;
    let test_prefix = format!("{}_{}", test_name, test_id);

    let mut tx = pool.begin().await?;

    // Create facility
    sqlx::query("INSERT INTO facility (pk_facility, str_name) VALUES ($1, $2)")
        .bind(facility_id.to_string())
        .bind(format!("{}_facility", test_prefix))
        .execute(&mut *tx)
        .await?;

    // Create department
    sqlx::query("INSERT INTO dept (pk_dept, str_name) VALUES ($1, $2)")
        .bind(dept_id.to_string())
        .bind(format!("{}_dept", test_prefix))
        .execute(&mut *tx)
        .await?;

    // Create show
    sqlx::query("INSERT INTO show (pk_show, str_name) VALUES ($1, $2)")
        .bind(show_id.to_string())
        .bind(format!("{}_show", test_prefix))
        .execute(&mut *tx)
        .await?;

    // Manual Tags
    let mut tags = Vec::new();
    for i in 1..=tag_count {
        tags.push(format!("{}_{}", test_prefix, i));
    }

    // Create allocations for different tag types
    let allocs = [
        create_allocation(&mut tx, facility_id, &format!("{}_a1", test_prefix)).await?,
        create_allocation(&mut tx, facility_id, &format!("{}_a2", test_prefix)).await?,
        create_allocation(&mut tx, facility_id, &format!("{}_a3", test_prefix)).await?,
    ];

    // Clusters. Chunk manual tags in approximatelly 4 groups
    let mut clusters = Vec::new();
    for chunk in tags.chunks(tags.len() / 4) {
        let cluster = Cluster::TagsKey(
            chunk
                .iter()
                .map(|tag_name| Tag {
                    name: tag_name.clone(),
                    ttype: TagType::Manual,
                })
                .collect(),
        );
        clusters.push(cluster);
    }
    for (alloc_id, alloc_name) in allocs.iter() {
        let cluster = Cluster::ComposedKey(ClusterKey {
            facility_id: facility_id.to_string(),
            show_id: show_id.to_string(),
            tag: Tag {
                name: alloc_name.clone(),
                ttype: TagType::Alloc,
            },
        });
        clusters.push(cluster);
        create_subscription(&mut tx, *alloc_id, show_id, 1000 * 100, 1200 * 100).await?;
    }

    // Create folder
    let folder_id = create_folder(
        &mut tx,
        show_id,
        dept_id,
        &format!("{}_folder", test_prefix),
    )
    .await?;

    tx.commit().await?;

    let mut rng = thread_rng();

    // Chunck tags to the number of hosts
    let tags_per_chunk = tags.len().div_ceil(host_count);
    let tag_chunks: Vec<Vec<(String, &str)>> = tags
        .chunks(tags_per_chunk)
        .map(|chunk| {
            chunk
                .into_iter()
                .map(|tag| (tag.clone(), "MANUAL"))
                .collect()
        })
        .collect();
    // Create hosts
    let mut hosts = Vec::new();
    for i in 0..host_count {
        let (curr_alloc_id, curr_alloc_tag) = allocs.choose(&mut rng).unwrap();

        let mut host_tags: Vec<_> = {
            // Ensure each tag exist in at least one host
            if i < tag_chunks.len() {
                tag_chunks[i].clone()
            } else {
                // The following hosts shall have 0-3 randomly selected manual tags
                let num_custom_tags = rng.gen_range(0..3);
                tags.iter()
                    .choose_multiple(&mut rng, num_custom_tags)
                    .into_iter()
                    .map(|tag| (tag.clone(), "MANUAL"))
                    .collect()
            }
        };
        // Each host shall have a single ALLOC tag
        host_tags.push((curr_alloc_tag.clone(), "ALLOC"));

        let cores_range: Vec<_> = (16..=512).step_by(8).collect();
        let cores = *cores_range.choose(&mut rng).unwrap();
        let memory = rng.gen_range(30..=200);

        let host = create_host(
            *curr_alloc_id,
            &format!("{}_host{}", test_prefix, i),
            cores,
            memory * 1024 * 1024,
            4,
            8 * 1024 * 1024,
            host_tags,
        )
        .await?;
        hosts.push(host);
    }

    // Create Jobs
    let mut jobs = Vec::new();
    for i in 0..job_count {
        let job = create_job_scenario(
            &format!("{}_{}", test_prefix, i),
            show_id,
            facility_id,
            dept_id,
            folder_id,
            layer_count,
            frames_per_layer_count,
            &tags,
        )
        .await?;
        jobs.push(job);
    }

    Ok(TestData {
        test_prefix: test_prefix.to_string(),
        clusters,
        jobs,
        hosts,
    })
}

async fn create_allocation(
    pool: &mut Transaction<'static, Postgres>,
    facility_id: Uuid,
    name: &str,
) -> Result<(Uuid, String), sqlx::Error> {
    let alloc_id = Uuid::new_v4();

    sqlx::query(
        "INSERT INTO alloc (pk_alloc, str_name, pk_facility, str_tag) VALUES ($1, $2, $3, $4)",
    )
    .bind(alloc_id.to_string())
    .bind(name)
    .bind(facility_id.to_string())
    .bind(name)
    .execute(&mut **pool)
    .await?;
    Ok((alloc_id, name.to_string()))
}

async fn create_subscription(
    pool: &mut Transaction<'static, Postgres>,
    alloc_id: Uuid,
    show_id: Uuid,
    size: i64,
    burst: i64,
) -> Result<(), sqlx::Error> {
    let subscription_id = Uuid::new_v4();
    sqlx::query(
        "INSERT INTO subscription \
        (pk_subscription, pk_alloc, pk_show, int_size, int_burst) \
        VALUES ($1, $2, $3, $4, $5)",
    )
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
    alloc_id: Uuid,
    name: &str,
    cores: i64,
    memory_kb: i64,
    gpus: i64,
    gpu_memory_kb: i64,
    tags: Vec<(String, &str)>,
) -> Result<TestHost, sqlx::Error> {
    let pool = test_connection_pool().await?;
    let host_id = Uuid::new_v4();

    // Create host
    sqlx::query(
        "INSERT INTO host \
        (pk_host, pk_alloc, str_name, str_lock_state, int_cores, int_cores_idle, int_mem, int_mem_idle, int_gpus, int_gpus_idle, int_gpu_mem, int_gpu_mem_idle, int_thread_mode) \
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)"
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
    .execute(&*pool)
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
    .execute(&*pool)
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
        .execute(&*pool)
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
    job_prefix: &str,
    show_id: Uuid,
    facility_id: Uuid,
    dept_id: Uuid,
    folder_id: Uuid,
    layer_count: usize,
    frames_per_layer_count: usize,
    tags: &[String],
) -> Result<TestJob, sqlx::Error> {
    let pool = test_connection_pool().await?;
    let mut tx = pool.begin().await?;
    let job_id = Uuid::new_v4();
    let job_name = format!("{}_job", job_prefix);

    // Create job
    sqlx::query(
            "INSERT INTO job (pk_job, pk_folder, pk_show, pk_facility, pk_dept, str_name, str_visible_name, str_shot, str_user, str_state) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)"
        )
        .bind(job_id.to_string())
        .bind(folder_id.to_string())
        .bind(show_id.to_string())
        .bind(facility_id.to_string())
        .bind(dept_id.to_string())
        .bind(&job_name)
        .bind(&job_name)
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

    let total_waiting_frames = layer_count * frames_per_layer_count;
    if existing_job_stat == 0 {
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
            "INSERT INTO job_resource (pk_job_resource, pk_job, int_priority, int_max_cores) VALUES ($1, $2, $3, $4)",
        )
        .bind(Uuid::new_v4().to_string())
        .bind(job_id.to_string())
        .bind(1)
        .bind(-1)
        .execute(&mut *tx)
        .await?;
    } else {
        // Update existing job_resource
        sqlx::query(
            "UPDATE job_resource SET int_priority = $1, int_max_cores = $2 WHERE pk_job = $3",
        )
        .bind(1)
        .bind(-1)
        .bind(job_id.to_string())
        .execute(&mut *tx)
        .await?;
    }

    let mut rng = thread_rng();
    let mut test_layers = Vec::new();

    for layer_index in 0..layer_count {
        let layer_id = Uuid::new_v4();
        let layer_name = &format!("{}_layer-{}", job_prefix, layer_index);

        let num_tags = rng.gen_range(1..=3);
        let layer_tags: Vec<_> = tags.choose_multiple(&mut rng, num_tags).cloned().collect();
        let cores_range: Vec<usize> = (8..=128).step_by(4).collect();
        let min_cores: usize = *cores_range.choose(&mut rng).unwrap();
        let memory = rng.gen_range(4..=64);

        // &format!("integ_test_mixed_hostname_{}", test_suffix),
        // &format!("integ_test_hostname_tag_{}", test_suffix),
        // 1,
        // 1024 * 1024,
        // 0,
        // 0,
        // Create layer
        sqlx::query(
                "INSERT INTO layer \
                (pk_layer, pk_job, str_name, str_cmd, str_range, str_tags, str_type, int_cores_min, int_mem_min, int_gpus_min, int_gpu_mem_min) \
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)"
            )
            .bind(layer_id.to_string())
            .bind(job_id.to_string())
            .bind(layer_name)
            .bind("echo 'Integration test frame'")
            .bind(format!("1-{}", frames_per_layer_count))
            .bind(layer_tags.join(" | "))
            .bind("PRE") // Default layer type
            .bind(min_cores as i64 * 100) // Core multiplier
            .bind(memory * 1024 * 1024)
            .bind(0)
            .bind(0)
            .execute(&mut *tx)
            .await?;

        // Create layer stats
        sqlx::query(
                "INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job, int_waiting_count, int_total_count) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (pk_layer) DO UPDATE SET int_waiting_count = EXCLUDED.int_waiting_count, int_total_count = EXCLUDED.int_total_count"
            )
            .bind(Uuid::new_v4().to_string())
            .bind(layer_id.to_string())
            .bind(job_id.to_string())
            .bind(frames_per_layer_count as i64)
            .bind(frames_per_layer_count as i64)
            .execute(&mut *tx)
            .await?;

        // Create layer resource
        // Check if layer_resource already exists for this layer (might be created by triggers)
        let existing_layer_resource =
            sqlx::query_scalar::<_, i64>("SELECT COUNT(*) FROM layer_resource WHERE pk_layer = $1")
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
        for frame_num in 1..=frames_per_layer_count as i32 {
            let frame_id = Uuid::new_v4();
            sqlx::query(
                    "INSERT INTO frame (pk_frame, pk_layer, pk_job, str_name, str_state, int_number, int_layer_order, int_dispatch_order) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)"
                )
                .bind(frame_id.to_string())
                .bind(layer_id.to_string())
                .bind(job_id.to_string())
                .bind(format!("{}-{}", frame_num, layer_name))
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
            tag: layer_tags,
        });
    }
    tx.commit().await?;

    Ok(TestJob {
        id: job_id,
        name: job_name.to_string(),
        layers: test_layers,
        frames_by_layer: frames_per_layer_count,
    })
}

pub enum WaitingFrameClause {
    JobId(Uuid),
    All,
    JobPrefix(String),
}

pub async fn get_waiting_frames_count(clause: WaitingFrameClause) -> usize {
    let pool = test_connection_pool().await.unwrap();
    match clause {
        WaitingFrameClause::JobId(job_id) => {
            sqlx::query_scalar::<_, i64>("SELECT int_waiting_count FROM job_stat WHERE pk_job = $1")
                .bind(job_id.to_string())
                .fetch_one(&*pool)
                .await
                .expect("Failed to query job stats") as usize
        }
        WaitingFrameClause::All => {
            sqlx::query_scalar::<_, i32>("SELECT sum(int_waiting_count)::INTEGER FROM job_stat")
                .fetch_one(&*pool)
                .await
                .expect("Failed to query job stats") as usize
        }
        WaitingFrameClause::JobPrefix(prefix) => sqlx::query_scalar::<_, i32>(
            "SELECT sum(job_stat.int_waiting_count)::INTEGER \
                   FROM job_stat JOIN job ON job.pk_job = job_stat.pk_job \
                   WHERE job.str_name LIKE $1",
        )
        .bind(format!("{}%", prefix))
        .fetch_one(&*pool)
        .await
        .expect("Failed to query job stats")
            as usize,
    }
}
