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
    pub rqd: RqdConfig,
    pub host_cache: HostCacheConfig,
    pub scheduler: SchedulerConfig,
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
            level: "debug:sqlx=info".to_string(),
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
    pub empty_job_cycles_before_quiting: Option<usize>,
    pub mem_reserved_min: ByteSize,
    #[serde(with = "humantime_serde")]
    pub allocation_refresh_interval: Duration,
    pub selfish_services: Vec<String>,
    pub host_booking_strategy: HostBookingStrategy,
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
            empty_job_cycles_before_quiting: None,
            mem_reserved_min: ByteSize::mib(250),
            allocation_refresh_interval: Duration::from_secs(3),
            selfish_services: Vec::new(),
            host_booking_strategy: HostBookingStrategy::default(),
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct StreamConfig {
    pub cluster_buffer_size: usize,
    pub job_buffer_size: usize,
}

impl Default for StreamConfig {
    fn default() -> Self {
        Self {
            cluster_buffer_size: 3,
            job_buffer_size: 3,
        }
    }
}

#[derive(Debug, Deserialize, Clone, Copy)]
#[serde(default)]
pub struct HostBookingStrategy {
    pub core_saturation: bool,
    pub memory_saturation: bool,
}

impl Default for HostBookingStrategy {
    fn default() -> Self {
        Self {
            core_saturation: true,
            memory_saturation: false,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct DatabaseConfig {
    pub pool_size: u32,
    pub db_host: String,
    pub db_name: String,
    pub db_user: String,
    pub db_pass: String,
    pub db_port: u16,
    pub core_multiplier: u32,
}

impl Default for DatabaseConfig {
    fn default() -> DatabaseConfig {
        DatabaseConfig {
            pool_size: 20,
            core_multiplier: 100,
            db_host: "localhost".to_string(),
            db_name: "test".to_string(),
            db_user: "postgres".to_string(),
            db_pass: "password".to_string(),
            db_port: 5432,
        }
    }
}

impl DatabaseConfig {
    pub fn connection_url(&self) -> String {
        let encoded_user = urlencoding::encode(&self.db_user);
        let encoded_pass = urlencoding::encode(&self.db_pass);
        format!(
            "postgresql://{}:{}@{}:{}/{}?timezone=UTC",
            encoded_user, encoded_pass, self.db_host, self.db_port, self.db_name
        )
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
    pub clean_up_interval: Duration,
    #[serde(with = "humantime_serde")]
    pub group_idle_timeout: Duration,
    pub concurrent_fetch_permit: usize,
    #[serde(with = "humantime_serde")]
    pub host_staleness_threshold: Duration,
    pub update_stat_on_book: bool,
}

impl Default for HostCacheConfig {
    fn default() -> HostCacheConfig {
        HostCacheConfig {
            concurrent_groups: 3,
            memory_key_divisor: ByteSize::gib(2),
            checkout_timeout: Duration::from_secs(12),
            monitoring_interval: Duration::from_secs(1),
            clean_up_interval: Duration::from_secs(5 * 60),
            group_idle_timeout: Duration::from_secs(3 * 60 * 60),
            concurrent_fetch_permit: 4,
            host_staleness_threshold: Duration::from_secs(2 * 60), // 2 minutes
            update_stat_on_book: false,
        }
    }
}

#[derive(Debug, Deserialize, Clone, Default)]
#[serde(default)]
pub struct SchedulerConfig {
    pub facility: Option<String>,
    pub alloc_tags: Vec<AllocTag>,
    pub manual_tags: Vec<String>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct AllocTag {
    pub show: String,
    pub tag: String,
}

//===Config Loader===

impl Config {
    /// Loads the current configuration from system config file and environment variables.
    ///
    /// Configuration sources are applied in the following order (later sources override earlier):
    /// 1. Default config file: `~/.local/share/rqd.yaml`
    /// 2. Custom config file: specified via `OPENCUE_SCHEDULER_CONFIG` environment variable
    /// 3. Environment variables: prefixed with `OPENSCHEDULER_`, using `_` as separator
    ///
    /// # Returns
    ///
    /// * `Ok(Config)` - Successfully loaded configuration
    /// * `Err(JobQueueConfigError)` - Failed to load or deserialize configuration
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
            .add_source(Environment::with_prefix("OPENSCHEDULER"))
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

    /// Loads configuration from a specified file path with environment variable overrides.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to the configuration file
    ///
    /// # Returns
    ///
    /// * `Ok(Config)` - Successfully loaded configuration
    /// * `Err(JobQueueConfigError)` - Failed to load or deserialize configuration
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

    /// Loads configuration from a specified file path without environment variable overrides.
    ///
    /// # Arguments
    ///
    /// * `path` - Path to the configuration file
    ///
    /// # Returns
    ///
    /// * `Ok(Config)` - Successfully loaded configuration
    /// * `Err(JobQueueConfigError)` - Failed to load or deserialize configuration
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
