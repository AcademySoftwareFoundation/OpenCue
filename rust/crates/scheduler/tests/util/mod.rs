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

//! Shared helpers for the scheduler integration test binaries (smoke, stress).
//!
//! Stress-specific machinery (bulk seeding, accounting audit, cleanup) lives in
//! [`stress`], gated behind the `stress-tests` feature.

#[cfg(feature = "stress-tests")]
pub mod stress;

use scheduler::config::{
    Config, DatabaseConfig, HostBookingStrategy, HostCacheConfig, LoggingConfig, QueueConfig,
    RqdConfig, SchedulerConfig,
};
use std::time::Duration;

use std::sync::Arc;

use sqlx::{postgres::PgPoolOptions, Pool, Postgres};
use tokio::sync::OnceCell;
use uuid::Uuid;

// Database connection configuration - matches the repo-root `docker compose up -d flyway`
// stack (Postgres 15 + Flyway migrations).
pub const TEST_DB_HOST: &str = "localhost";
pub const TEST_DB_PORT: u16 = 5432;
pub const TEST_DB_NAME: &str = "cuebot";
pub const TEST_DB_USER: &str = "cuebot";
pub const TEST_DB_PASSWORD: &str = "cuebot_password";

static TEST_CONNECTION_POOL: OnceCell<Arc<Pool<Postgres>>> = OnceCell::const_new();

pub async fn test_connection_pool() -> Result<Arc<Pool<Postgres>>, sqlx::Error> {
    let database_url = format!(
        "postgresql://{}:{}@{}:{}/{}",
        TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_HOST, TEST_DB_PORT, TEST_DB_NAME
    );
    TEST_CONNECTION_POOL
        .get_or_try_init(|| async {
            let pool = PgPoolOptions::new()
                .max_connections(4)
                .connect(&database_url)
                .await?;
            Ok(Arc::new(pool))
        })
        .await
        .map(Arc::clone)
}

#[allow(dead_code)]
pub fn create_test_config() -> Config {
    let host_cache_config = HostCacheConfig {
        update_stat_on_book: true,
        ..Default::default()
    };

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
            cluster_empty_sleep: Duration::from_secs(30),
            cluster_reload_interval: Duration::from_secs(120),
            cluster_saturated_sleep: Duration::from_secs(1),
            stream: scheduler::config::StreamConfig {
                cluster_buffer_size: 4,
                job_buffer_size: 8,
            },
            max_jobs_per_cluster_pass: 20,
            manual_tags_chunk_size: 10,
            hostname_tags_chunk_size: 20,
            host_candidate_attempts_per_layer: 5,
            empty_job_cycles_before_quiting: Some(20),
            mem_reserved_min: bytesize::ByteSize::mb(250),
            selfish_services: Vec::new(),
            host_booking_strategy: HostBookingStrategy::Saturation {
                core_saturation: true,
                memory_saturation: false,
            },
            frame_memory_soft_limit: 1.6,
            frame_memory_hard_limit: 2.0,
            metrics_port: 9090,
        },
        database: DatabaseConfig {
            pool_size: 20,
            core_multiplier: 100,
            db_host: TEST_DB_HOST.to_string(),
            db_name: TEST_DB_NAME.to_string(),
            db_user: TEST_DB_USER.to_string(),
            db_pass: TEST_DB_PASSWORD.to_string(),
            db_port: TEST_DB_PORT,
        },
        rqd: RqdConfig {
            grpc_port: 8444,
            dry_run_mode: true, // Always run in dry mode for tests
        },
        host_cache: host_cache_config,
        scheduler: SchedulerConfig::default(),
        accounting: scheduler::config::AccountingConfig::default(),
        sentry_dsn: None,
    }
}

#[allow(dead_code)]
pub enum WaitingFrameClause {
    JobId(Uuid),
    All,
    JobPrefix(String),
}

#[allow(dead_code)]
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
