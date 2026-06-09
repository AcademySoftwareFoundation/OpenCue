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

pub mod error;

use crate::config::error::JobQueueConfigError;
use bytesize::ByteSize;
use config::{Config as ConfigBase, Environment, File};
use lazy_static::lazy_static;
use once_cell::sync::OnceCell;
use serde::Deserialize;
use std::{collections::HashSet, env, fs, path::PathBuf, time::Duration};

static DEFAULT_CONFIG_FILE: &str = "~/.local/share/scheduler.yaml";

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
    pub sentry_dsn: Option<String>,
    pub logging: LoggingConfig,
    pub queue: QueueConfig,
    pub database: DatabaseConfig,
    pub rqd: RqdConfig,
    pub host_cache: HostCacheConfig,
    pub scheduler: SchedulerConfig,
    pub accounting: AccountingConfig,
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct AccountingConfig {
    pub redis: RedisConfig,
    /// Cadence at which booked counters are reseeded from `SUM(proc)` to both
    /// the PG accounting tables and Redis (under the `acct:seq` CAS guard).
    #[serde(with = "humantime_serde")]
    pub recompute_interval: Duration,
    /// Cadence at which limit fields (subscription burst, folder/job/point caps)
    /// are reseeded from PG accounting tables to Redis.
    #[serde(with = "humantime_serde")]
    pub limit_reseed_interval: Duration,
    /// TTL of the in-process `b_scheduler_managed=true` show-id cache.
    #[serde(with = "humantime_serde")]
    pub managed_shows_ttl: Duration,
    /// Maximum CAS retries per reseed cycle before giving up and waiting for the
    /// next cycle (per design §2.4).
    pub cas_max_retries: u32,
}

impl Default for AccountingConfig {
    fn default() -> Self {
        Self {
            redis: RedisConfig::default(),
            recompute_interval: Duration::from_secs(120),
            limit_reseed_interval: Duration::from_secs(300),
            managed_shows_ttl: Duration::from_secs(30),
            cas_max_retries: 3,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct RedisConfig {
    pub enabled: bool,
    pub host: String,
    pub port: u16,
    pub pool_size: u32,
}

impl Default for RedisConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            host: "localhost".to_string(),
            port: 6379,
            pool_size: 20,
        }
    }
}

impl RedisConfig {
    pub fn url(&self) -> String {
        format!("redis://{}:{}/", self.host, self.port)
    }
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
    /// Duration a cluster sleeps after a pass returned no dispatchable jobs.
    /// Larger values reduce empty-pass query load on the database.
    #[serde(with = "humantime_serde")]
    pub cluster_empty_sleep: Duration,
    pub stream: StreamConfig,
    /// Maximum number of jobs returned per cluster pass. Caps the per-pass
    /// dispatch cost so a big-show cluster doesn't iterate thousands of jobs
    /// in a single round. Strict `ORDER BY priority DESC` means low-priority
    /// jobs are deferred to subsequent passes when the high-priority backlog
    /// drains.
    pub max_jobs_per_cluster_pass: i64,
    pub manual_tags_chunk_size: usize,
    pub hostname_tags_chunk_size: usize,
    pub host_candidate_attempts_per_layer: usize,
    pub empty_job_cycles_before_quiting: Option<usize>,
    pub mem_reserved_min: ByteSize,
    pub selfish_services: Vec<String>,
    pub host_booking_strategy: HostBookingStrategy,
    pub frame_memory_soft_limit: f64,
    pub frame_memory_hard_limit: f64,
    pub metrics_port: u16,
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
            cluster_empty_sleep: Duration::from_secs(30),
            stream: StreamConfig::default(),
            max_jobs_per_cluster_pass: 20,
            manual_tags_chunk_size: 50,
            hostname_tags_chunk_size: 50,
            host_candidate_attempts_per_layer: 10,
            empty_job_cycles_before_quiting: None,
            mem_reserved_min: ByteSize::mib(250),
            selfish_services: Vec::new(),
            host_booking_strategy: HostBookingStrategy::default(),
            frame_memory_soft_limit: 1.6,
            frame_memory_hard_limit: 2.0,
            metrics_port: 9090,
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

/// Strategy for selecting a host when multiple candidates satisfy a layer's
/// floor requirements.
///
/// `Saturation` is the legacy first-fit strategy: scan the B-tree in a
/// configurable direction (`core_saturation` / `memory_saturation`) and take
/// the first valid host. `Epvm` scores up to `max_candidates` hosts via
/// E-PVM stranding and picks the lowest score. Saturation is the default;
/// Epvm is opt-in.
#[derive(Debug, Deserialize, Clone, Copy)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum HostBookingStrategy {
    Saturation {
        core_saturation: bool,
        memory_saturation: bool,
    },
    Epvm {
        weights: ScoreWeights,
        max_candidates: usize,
    },
}

impl Default for HostBookingStrategy {
    fn default() -> Self {
        Self::Saturation {
            core_saturation: true,
            memory_saturation: false,
        }
    }
}

/// Weights for the E-PVM placement score.
///
/// For each resource dimension (cores, memory, GPUs, GPU memory), E-PVM
/// computes how much of that resource will be "stranded" on a host — left
/// idle because some other dimension ran out first. The weights here scale
/// each dimension's stranding before they're summed into a single score.
/// The cache picks the host with the lowest score.
///
/// # Units and range
///
/// All weights are dimensionless `f64`. Because stranding terms are themselves
/// normalized (divided by the layer's per-dim minimum), a weight of `1.0`
/// means "1 stranded layer-frame on this dimension contributes 1 score unit".
///
/// Practical range: **`0.0` to ~`10.0`**.
/// * `0.0` — disables this dimension's contribution to the score.
/// * `1.0` — baseline; this dimension counts at par with other unit-weighted dims.
/// * `>1.0` — emphasizes the dimension (e.g. set `gpus: 4.0` to make GPU
///   stranding hurt 4× as much as core stranding).
/// * Values much higher than ~10.0 risk single-dimension dominance —
///   placements become driven by one resource, ignoring everything else.
/// * Negative values are not meaningful (would reward stranding); the gate
///   does not enforce non-negativity, but operators should keep weights `>= 0`.
///
/// See `rust/config/scheduler.yaml` for annotated example configurations
/// (baseline, GPU-scarce, memory-tight, cores-only) and the
/// `gpu_reservation` semantics.
#[derive(Debug, Deserialize, Clone, Copy)]
#[serde(default)]
pub struct ScoreWeights {
    /// Penalty per fractional stranded core-layer-frame. Default `1.0`.
    pub cores: f64,
    /// Penalty per fractional stranded mem-layer-frame. Default `1.0`.
    pub mem: f64,
    /// Penalty per fractional stranded GPU-layer-frame (GPU layers only).
    /// Default `2.0` — GPU jobs are rarer, so wasting GPU capacity hurts more.
    pub gpus: f64,
    /// Penalty per fractional stranded GPU-memory-layer-frame (GPU layers only).
    /// Default `1.0`.
    pub gpu_mem: f64,
    /// Soft-reservation penalty for non-GPU layers on GPU hosts. Scales the
    /// host's idle GPU capacity (count + GB). Default `2.0`. See risk #3 — this
    /// is the weight most likely to need adjustment after a production rollout.
    pub gpu_reservation: f64,
}

impl Default for ScoreWeights {
    fn default() -> Self {
        Self {
            cores: 1.0,
            mem: 1.0,
            gpus: 2.0,
            gpu_mem: 1.0,
            gpu_reservation: 2.0,
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
            "postgresql://{}:{}@{}:{}/{}?options=-c%20timezone%3DUTC",
            encoded_user, encoded_pass, self.db_host, self.db_port, self.db_name
        )
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
            monitoring_interval: Duration::from_secs(10),
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
    pub entire_shows: Vec<String>,
    pub alloc_tags: Vec<AllocTag>,
    pub manual_tags: Vec<ManualTags>,
    pub ignore_tags: Vec<String>,
}

impl SchedulerConfig {
    pub fn show_names(&self) -> Option<Vec<String>> {
        let mut show_names: HashSet<String> = HashSet::from_iter(self.entire_shows.iter().cloned());
        for tag in &self.alloc_tags {
            show_names.insert(tag.show.clone());
        }
        if show_names.is_empty() {
            None
        } else {
            Some(show_names.into_iter().collect())
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
pub struct AllocTag {
    pub show: String,
    pub tag: String,
}

#[derive(Debug, Deserialize, Clone)]
pub struct ManualTags {
    pub show: String,
    pub tags: Vec<String>,
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
