pub mod error;

use crate::config::error::RqdConfigError;
use bytesize::ByteSize;
use config::{Config as ConfigBase, Environment, File};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, env, fs, path::Path, time::Duration};

static DEFAULT_CONFIG_FILE: &str = "~/.local/share/rqd.yaml";

//===Config Types===

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
pub struct GrpcConfig {
    pub rqd_port: u16,
    pub cuebot_endpoints: Vec<String>,
    #[serde(with = "humantime_serde")]
    pub connection_expires_after: Duration,
    #[serde(with = "humantime_serde")]
    pub backoff_delay_min: Duration,
    #[serde(with = "humantime_serde")]
    pub backoff_delay_max: Duration,
    pub backoff_jitter_percentage: f64,
}

impl Default for GrpcConfig {
    fn default() -> GrpcConfig {
        GrpcConfig {
            rqd_port: 8444,
            cuebot_endpoints: vec!["localhost:4343".to_string()],
            connection_expires_after: Duration::from_secs(3600), // 1h. from_hour is experimental
            backoff_delay_min: Duration::from_millis(10),
            backoff_delay_max: Duration::from_secs(60),
            backoff_jitter_percentage: 10.0,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct MachineConfig {
    #[serde(with = "humantime_serde")]
    pub monitor_interval: Duration,
    pub use_ip_as_hostname: bool,
    pub override_real_values: Option<OverrideConfig>,
    pub custom_tags: Vec<String>,
    pub nimby_mode: bool,
    pub facility: String,
    pub cpuinfo_path: String,
    pub distro_release_path: String,
    pub proc_stat_path: String,
    pub proc_loadavg_path: String,
    pub temp_path: String,
    pub core_multiplier: u32,
    pub worker_threads: usize,
    #[serde(with = "humantime_serde")]
    pub nimby_idle_threshold: Duration,
    pub nimby_display_file_path: Option<String>,
    #[serde(with = "humantime_serde")]
    pub nimby_start_retry_interval: Duration,
    pub nimby_display_xauthority_path: String,
}

impl Default for MachineConfig {
    fn default() -> MachineConfig {
        MachineConfig {
            monitor_interval: Duration::from_secs(5),
            use_ip_as_hostname: false,
            override_real_values: None,
            custom_tags: vec![],
            nimby_mode: false,
            facility: "cloud".to_string(),
            cpuinfo_path: "/proc/cpuinfo".to_string(),
            distro_release_path: "/etc/os-release".to_string(),
            proc_stat_path: "/proc/stat".to_string(),
            proc_loadavg_path: "/proc/loadavg".to_string(),
            temp_path: "/tmp".to_string(),
            core_multiplier: 100,
            worker_threads: 4,
            nimby_idle_threshold: Duration::from_secs(60 * 15), // 15 min
            nimby_display_file_path: None,
            nimby_start_retry_interval: Duration::from_secs(60 * 5), // 5 min
            nimby_display_xauthority_path: "/home/{username}/Xauthority".to_string(),
        }
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(default)]
pub struct RunnerConfig {
    pub run_on_docker: bool,
    pub default_uid: u32,
    pub default_gid: u32,
    pub logger: LoggerType,
    pub prepend_timestamp: bool,
    pub use_host_path_env_var: bool,
    pub desktop_mode: bool,
    pub run_as_user: bool,
    pub temp_path: String,
    pub shell_path: String,
    pub snapshots_path: String,
    #[serde(with = "humantime_serde")]
    pub kill_monitor_interval: Duration,
    #[serde(with = "humantime_serde")]
    pub kill_monitor_timeout: Duration,
    pub force_kill_after_timeout: bool,
    pub docker_mounts: Vec<DockerMountConfig>,
    pub docker_default_image: String,
    pub docker_images: HashMap<String, String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub enum LoggerType {
    #[serde(rename = "file")]
    File,
    // This is a placeholder for new logging solutions
    // #[serde(rename = "loki")]
    // Loki,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DockerMountConfig {
    pub target: String,
    pub source: String,
    pub typ: String,
    pub bind_propagation: String,
}

impl Default for RunnerConfig {
    fn default() -> Self {
        Self {
            run_on_docker: false,
            default_uid: 1000,
            default_gid: 20,
            logger: LoggerType::File,
            prepend_timestamp: true,
            use_host_path_env_var: false,
            desktop_mode: false,
            run_as_user: false,
            temp_path: std::env::temp_dir().to_str().unwrap_or("/tmp").to_string(),
            shell_path: "/bin/bash".to_string(),
            snapshots_path: format!(
                "{}/.rqd/snapshots",
                std::env::var("HOME").unwrap_or("/tmp".to_string())
            ),
            kill_monitor_interval: Duration::from_secs(120),
            kill_monitor_timeout: Duration::from_secs(1200),
            force_kill_after_timeout: false,
            docker_mounts: Vec::new(),
            docker_default_image: "ubuntu:latest".to_string(),
            docker_images: HashMap::new(),
        }
    }
}

#[cfg(feature = "containerized_frames")]
impl RunnerConfig {
    pub fn get_docker_image(&self, image_key: &str) -> String {
        self.docker_images
            .get(image_key)
            .cloned()
            .unwrap_or(self.docker_default_image.clone())
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
#[derive(Default)]
pub struct OverrideConfig {
    pub cores: Option<u64>,
    pub procs: Option<u64>,
    pub memory_size: Option<ByteSize>,
    pub workstation_mode: Option<bool>,
    pub hostname: Option<String>,
    pub os: Option<String>,
}

//===Config Loader===

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(default)]
pub struct Config {
    pub logging: LoggingConfig,
    pub grpc: GrpcConfig,
    pub machine: MachineConfig,
    pub runner: RunnerConfig,
}

impl Config {
    // load the current config from the system config and environment variables
    pub fn load() -> Result<Self, RqdConfigError> {
        let mut required = false;
        let config_file = match env::var("OPENCUE_RQD_CONFIG") {
            Ok(v) => {
                required = true;
                v
            }
            Err(_) => DEFAULT_CONFIG_FILE.to_string(),
        };

        println!(" INFO Config::load: using config file: {:?}", config_file);

        let config = ConfigBase::builder()
            .add_source(File::with_name(&config_file).required(required))
            .add_source(Environment::with_prefix("OPENRQD").separator("_"))
            .build()
            .map_err(|err| {
                RqdConfigError::LoadConfigError(format!(
                    "{:?} config could not be loaded. {}",
                    &config_file, err
                ))
            })?;

        let deserialized_config = Config::deserialize(config).map_err(|err| {
            RqdConfigError::LoadConfigError(format!(
                "{:?} config could not be deserialized. {}",
                &config_file, err
            ))
        })?;

        Self::setup(&deserialized_config)?;

        Ok(deserialized_config)
    }

    #[allow(dead_code)]
    pub fn load_file_and_env<P: AsRef<str>>(path: P) -> Result<Self, RqdConfigError> {
        let config = ConfigBase::builder()
            .add_source(File::with_name(path.as_ref()))
            .add_source(Environment::with_prefix("RQD").separator("_"))
            .build();

        config
            .map(|c| Config::deserialize(c).unwrap())
            .map_err(|err| {
                RqdConfigError::LoadConfigError(format!(
                    "{:?} config could not be loaded. {}",
                    path.as_ref(),
                    err
                ))
            })
    }

    #[allow(dead_code)]
    pub fn load_file<P: AsRef<str>>(path: P) -> Result<Self, RqdConfigError> {
        let config = ConfigBase::builder()
            .add_source(File::with_name(path.as_ref()))
            .build();

        config
            .map(|c| Config::deserialize(c).unwrap())
            .map_err(|err| {
                RqdConfigError::LoadConfigError(format!(
                    "{:?} config could not be loaded. {}",
                    path.as_ref(),
                    err
                ))
            })
    }

    // TODO: Ensure paths exist and permissions are adequate
    pub fn setup(&self) -> Result<(), RqdConfigError> {
        // Ensure snapshot path exists
        let snapshots_path = Path::new(&self.runner.snapshots_path);
        if !snapshots_path.exists() {
            fs::create_dir_all(snapshots_path).map_err(|err| {
                RqdConfigError::InvalidPath(format!(
                    "Failed to create snapshot dir at {:?}: {err}",
                    snapshots_path
                ))
            })?;
        }
        Ok(())
    }
}
