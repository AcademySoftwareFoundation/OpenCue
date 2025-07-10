pub mod error;

use crate::config::error::JobQueueConfigError;
use config::{Config as ConfigBase, Environment, File};
use serde::Deserialize;
use std::{env, time::Duration};

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
pub struct QueueConfig {
    #[serde(with = "humantime_serde")]
    pub monitor_interval: Duration,
}

impl Default for QueueConfig {
    fn default() -> QueueConfig {
        QueueConfig {
            monitor_interval: Duration::from_secs(5),
        }
    }
}

//===Config Loader===

#[derive(Debug, Deserialize, Default, Clone)]
#[serde(default)]
pub struct Config {
    pub logging: LoggingConfig,
    pub queue: QueueConfig,
}

impl Config {
    // load the current config from the system config and environment variables
    pub fn load() -> Result<Self, JobQueueConfigError> {
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
