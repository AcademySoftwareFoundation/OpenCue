pub mod error;

use crate::config::error::JobQueueConfigError;
use bytesize::ByteSize;
use config::{Config as ConfigBase, Environment, File};
use lazy_static::lazy_static;
use once_cell::sync::OnceCell;
use serde::Deserialize;
use std::{env, fs, path::PathBuf, time::Duration};

static DEFAULT_CONFIG_FILE: &str = "~/.local/share/rqd.yaml";

pub static OVERRIDE_CONFIG: OnceCell<Config> = OnceCell::new();

lazy_static! {
    pub static ref CONFIG: Config = OVERRIDE_CONFIG
        .get()
        .cloned()
        .unwrap_or_else(|| Config::load().expect("Failed to load config file"));
}

//===Config Types===

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(default)]
pub struct Config {
    pub logging: LoggingConfig,
    pub queue: QueueConfig,
    pub database: DatabaseConfig,
    pub kafka: KafkaConfig,
    pub rqd: RqdConfig,
    pub host_cache: HostCacheConfig,
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct LoggingConfig {
    // Logging level: debug|info|warning|error
    pub level: String,
    // Path to the log file if `file_appender` is enabled
    pub path: String,
    // Log to stdout if file_appender is False
    pub file_appender: bool,
}

impl Default for LoggingConfig {
    fn default() -> Self {
        Self {
            level: "debug".to_string(),
            path: "/opt/rqd/logs/scheduler.log".to_string(),
            file_appender: false,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct QueueConfig {
    #[serde(with = "humantime_serde")]
    pub monitor_interval: Duration,
    pub worker_threads: usize,
    pub dispatch_frames_per_layer_limit: usize,
    pub core_multiplier: u32,
    pub memory_stranded_threshold: ByteSize,
    #[serde(with = "humantime_serde")]
    pub job_back_off_duration: Duration,
    pub stream: StreamConfig,
    pub manual_tags_chunk_size: usize,
    pub hostname_tags_chunk_size: usize,
    pub host_candidate_attemps_per_layer: usize,
}

impl Default for QueueConfig {
    fn default() -> QueueConfig {
        QueueConfig {
            monitor_interval: Duration::from_secs(5),
            worker_threads: 4,
            dispatch_frames_per_layer_limit: 20,
            core_multiplier: 100,
            memory_stranded_threshold: ByteSize::gib(2),
            job_back_off_duration: Duration::from_secs(300),
            stream: StreamConfig::default(),
            manual_tags_chunk_size: 100,
            hostname_tags_chunk_size: 300,
            host_candidate_attemps_per_layer: 10,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct StreamConfig {
    pub cluster_buffer_size: usize,
    pub layer_buffer_size: usize,
}

impl Default for StreamConfig {
    fn default() -> Self {
        Self {
            cluster_buffer_size: 3,
            layer_buffer_size: 10,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct DatabaseConfig {
    pub pool_size: u32,
    pub connection_url: String,
    pub core_multiplier: u32,
}

impl Default for DatabaseConfig {
    fn default() -> DatabaseConfig {
        DatabaseConfig {
            pool_size: 10,
            connection_url: "postgres://postgres:password@localhost/test".to_string(),
            core_multiplier: 100,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct KafkaConfig {
    pub bootstrap_servers: String,
    #[serde(with = "humantime_serde")]
    pub timeout: Duration,
    pub general_jobs_topic: TopicConfig,
}

impl Default for KafkaConfig {
    fn default() -> KafkaConfig {
        KafkaConfig {
            bootstrap_servers: "localhost:9092".to_string(),
            timeout: Duration::from_secs(5),
            general_jobs_topic: TopicConfig::default(),
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct TopicConfig {
    pub topic_name: String,
    pub num_partitions: i32,
    pub replication_factor: i32,
    #[serde(with = "humantime_serde")]
    pub retention: Duration,
}

impl Default for TopicConfig {
    fn default() -> TopicConfig {
        TopicConfig {
            topic_name: "general_job_queue".to_string(),
            num_partitions: 12,
            replication_factor: 3,
            retention: Duration::from_secs(300),
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct RqdConfig {
    pub grpc_port: u32,
    pub dry_run_mode: bool,
}

impl Default for RqdConfig {
    fn default() -> RqdConfig {
        RqdConfig {
            grpc_port: 8444,
            dry_run_mode: false,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct HostCacheConfig {
    pub concurrent_groups: usize,
    pub memory_key_divisor: ByteSize,
    #[serde(with = "humantime_serde")]
    pub checkout_timeout: Duration,
    #[serde(with = "humantime_serde")]
    pub monitoring_interval: Duration,
    #[serde(with = "humantime_serde")]
    pub group_idle_timeout: Duration,
}

impl Default for HostCacheConfig {
    fn default() -> HostCacheConfig {
        HostCacheConfig {
            concurrent_groups: 3,
            memory_key_divisor: ByteSize::gib(2),
            checkout_timeout: Duration::from_secs(12),
            monitoring_interval: Duration::from_secs(1),
            group_idle_timeout: Duration::from_secs(3 * 60 * 60),
        }
    }
}

//===Config Loader===

impl Config {
    // load the current config from the system config and environment variables
    pub fn load() -> Result<Self, JobQueueConfigError> {
        let mut required = false;
        let config_file = match env::var("OPENCUE_SCHEDULER_CONFIG") {
            Ok(v) => {
                println!(
                    " INFO Config: {}",
                    fs::canonicalize(&v)
                        .unwrap_or(PathBuf::from("Invalid path"))
                        .to_string_lossy()
                );
                required = true;
                v
            }
            Err(_) => DEFAULT_CONFIG_FILE.to_string(),
        };

        println!(" INFO Config::load: using config file: {:?}", config_file);

        let config = ConfigBase::builder()
            .add_source(File::with_name(&config_file).required(required))
            .add_source(Environment::with_prefix("OPENSCHEDULER").separator("_"))
            .build()
            .map_err(|err| {
                JobQueueConfigError::LoadConfigError(format!(
                    "{:?} config could not be loaded. {}",
                    &config_file, err
                ))
            })?;

        let deserialized_config = Config::deserialize(config).map_err(|err| {
            JobQueueConfigError::LoadConfigError(format!(
                "{:?} config could not be deserialized. {}",
                &config_file, err
            ))
        })?;

        Ok(deserialized_config)
    }

    #[allow(dead_code)]
    pub fn load_file_and_env<P: AsRef<str>>(path: P) -> Result<Self, JobQueueConfigError> {
        let config = ConfigBase::builder()
            .add_source(File::with_name(path.as_ref()))
            .add_source(Environment::with_prefix("RQD").separator("_"))
            .build();

        config
            .map(|c| Config::deserialize(c).unwrap())
            .map_err(|err| {
                JobQueueConfigError::LoadConfigError(format!(
                    "{:?} config could not be loaded. {}",
                    path.as_ref(),
                    err
                ))
            })
    }

    #[allow(dead_code)]
    pub fn load_file<P: AsRef<str>>(path: P) -> Result<Self, JobQueueConfigError> {
        let config = ConfigBase::builder()
            .add_source(File::with_name(path.as_ref()))
            .build();

        config
            .map(|c| Config::deserialize(c).unwrap())
            .map_err(|err| {
                JobQueueConfigError::LoadConfigError(format!(
                    "{:?} config could not be loaded. {}",
                    path.as_ref(),
                    err
                ))
            })
    }
}
