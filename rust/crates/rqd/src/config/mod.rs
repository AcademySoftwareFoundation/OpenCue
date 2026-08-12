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

use crate::config::error::RqdConfigError;
use bytesize::ByteSize;
use config::{Config as ConfigBase, Environment, File};
use lazy_static::lazy_static;
use regex::Regex;
use serde::{Deserialize, Deserializer, Serialize};
use std::{
    collections::HashMap,
    env, fs,
    path::Path,
    sync::{Arc, RwLock},
    time::Duration,
};
use tracing::{info, warn};

static DEFAULT_CONFIG_FILE: &str = "~/.local/share/rqd.yaml";

lazy_static! {
    pub static ref CONFIG: Config = Config::load().expect("Failed to load config file");
}
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

/// Deserializes a value that can be either a single comma-separated string or a sequence of strings.
fn string_or_vec<'de, D>(deserializer: D) -> Result<Vec<String>, D::Error>
where
    D: Deserializer<'de>,
{
    #[derive(Deserialize)]
    #[serde(untagged)]
    enum StringOrVec {
        String(String),
        Vec(Vec<String>),
    }

    match StringOrVec::deserialize(deserializer)? {
        StringOrVec::String(s) => Ok(s.split(',').map(|item| item.trim().to_string()).collect()),
        StringOrVec::Vec(v) => Ok(v),
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct GrpcConfig {
    pub rqd_port: u16,
    pub rqd_interface: Option<String>,
    #[serde(deserialize_with = "string_or_vec")]
    pub cuebot_endpoints: Vec<String>,
    #[serde(with = "humantime_serde")]
    pub connection_expires_after: Duration,
    #[serde(with = "humantime_serde")]
    pub backoff_delay_min: Duration,
    #[serde(with = "humantime_serde")]
    pub backoff_delay_max: Duration,
    pub backoff_jitter_percentage: f64,
    pub backoff_retry_attempts: usize,
}

impl Default for GrpcConfig {
    fn default() -> GrpcConfig {
        GrpcConfig {
            rqd_port: 8444,
            rqd_interface: None,
            cuebot_endpoints: vec!["localhost:8443".to_string()],
            connection_expires_after: Duration::from_secs(3600), // 1h. from_hour is experimental
            backoff_delay_min: Duration::from_millis(10),
            backoff_delay_max: Duration::from_secs(60),
            backoff_jitter_percentage: 10.0,
            backoff_retry_attempts: 20,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct MachineConfig {
    #[serde(with = "humantime_serde")]
    pub monitor_interval: Duration,
    /// Retry heartbeat of the dedicated frame-completion delivery task. First delivery attempts are
    /// triggered immediately via a Notify signal; this interval only paces retries of entries that
    /// failed or timed out on a previous pass.
    #[serde(with = "humantime_serde")]
    pub frame_complete_delivery_interval: Duration,
    /// Per-report deadline when sending a FrameCompleteReport to Cuebot. Generous by design: it
    /// exists only to abandon a genuinely hung send (no transport-level deadline is set on the
    /// channel), never to cut short one that is making progress. A timed-out entry is retained and
    /// retried on a later pass.
    #[serde(with = "humantime_serde")]
    pub frame_complete_send_timeout: Duration,
    pub use_ip_as_hostname: bool,
    pub override_real_values: Option<OverrideConfig>,
    pub custom_tags: Vec<String>,
    pub nimby_mode: bool,
    pub nimby_lock_by_default: bool,
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
    pub memory_oom_margin_percentage: u32,
}

impl Default for MachineConfig {
    fn default() -> MachineConfig {
        MachineConfig {
            monitor_interval: Duration::from_secs(5),
            frame_complete_delivery_interval: Duration::from_secs(5),
            frame_complete_send_timeout: Duration::from_secs(30),
            use_ip_as_hostname: false,
            override_real_values: None,
            custom_tags: vec![],
            nimby_mode: false,
            nimby_lock_by_default: false,
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
            memory_oom_margin_percentage: 96,
        }
    }
}

#[cfg(test)]
mod tests {
    use std::io::Write;

    use tempfile::Builder;

    use super::{Config, MachineConfig};

    #[test]
    fn machine_config_defaults_to_unlocked_nimby_startup() {
        assert!(!MachineConfig::default().nimby_lock_by_default);
    }

    #[test]
    fn load_file_reads_nimby_lock_by_default() {
        let mut config_file = Builder::new()
            .suffix(".yaml")
            .tempfile()
            .expect("temp config file");
        writeln!(
            config_file,
            "machine:\n  nimby_mode: true\n  nimby_lock_by_default: true"
        )
        .expect("write config");

        let config = Config::load_file(
            config_file
                .path()
                .to_str()
                .expect("config path should be valid UTF-8"),
        )
        .expect("config should load");

        assert!(config.machine.nimby_mode);
        assert!(config.machine.nimby_lock_by_default);
    }

    #[test]
    fn compiled_exit_status_rules_seed_lazily_from_raw_fields() {
        let mut config = super::RunnerConfig::default();
        config.log_scan_last_lines = 25;
        config.log_exit_status_rules = vec![super::LogExitStatusRule {
            name: "LICENSE".to_string(),
            regex: "all in use".to_string(),
            exit_status: 330,
        }];

        let rule_set = config.compiled_exit_status_rules();
        assert_eq!(rule_set.scan_last_lines, 25);
        assert_eq!(rule_set.rules.len(), 1);
        assert_eq!(rule_set.rules[0].name, "LICENSE");
    }

    #[test]
    fn reload_exit_status_rules_reaches_previously_made_clones() {
        // A clone taken before the reload (as every RunningFrame holds) must observe the new
        // rules — the compiled-rules cell is shared across clones, not copied.
        let config = super::RunnerConfig::default();
        let clone_before_reload = config.clone();
        // Seed the cell from the (empty) raw fields first, as startup does.
        assert!(clone_before_reload
            .compiled_exit_status_rules()
            .rules
            .is_empty());

        config.reload_exit_status_rules(
            10,
            &[super::LogExitStatusRule {
                name: "NEW_RULE".to_string(),
                regex: "added later".to_string(),
                exit_status: 331,
            }],
        );

        let rule_set = clone_before_reload.compiled_exit_status_rules();
        assert_eq!(rule_set.scan_last_lines, 10);
        assert_eq!(rule_set.rules.len(), 1);
        assert_eq!(rule_set.rules[0].name, "NEW_RULE");
    }

    #[test]
    fn reload_exit_status_rules_skips_invalid_regex() {
        let config = super::RunnerConfig::default();
        config.reload_exit_status_rules(
            50,
            &[
                super::LogExitStatusRule {
                    name: "BAD".to_string(),
                    regex: "(unclosed".to_string(),
                    exit_status: 1,
                },
                super::LogExitStatusRule {
                    name: "GOOD".to_string(),
                    regex: "valid".to_string(),
                    exit_status: 2,
                },
            ],
        );

        let rule_set = config.compiled_exit_status_rules();
        assert_eq!(rule_set.rules.len(), 1);
        assert_eq!(rule_set.rules[0].name, "GOOD");
    }
}

/// A rule that reclassifies a failed frame's exit status based on its log output.
///
/// When a frame finishes with a non-zero exit code, RQD scans the tail of its log (see
/// [`RunnerConfig::log_scan_last_lines`]). The first rule whose `regex` matches causes the
/// frame to report `exit_status` to Cuebot instead of the process's real exit code. This lets
/// operators single out failures that deserve special dispatcher handling, e.g. a Houdini
/// license shortage that should be retried differently without the render wrapper needing to
/// translate the error into an exit code itself.
#[derive(Debug, Serialize, Deserialize, Clone, PartialEq, Eq)]
pub struct LogExitStatusRule {
    /// Human-readable identifier, used only in log messages (e.g. "HOUDINI_LICENSE_ERROR").
    #[serde(default)]
    pub name: String,
    /// Regular expression tested against the scanned log tail. Invalid patterns are skipped
    /// (with a warning) at startup so a single typo can't disable the whole feature.
    pub regex: String,
    /// Exit status reported to Cuebot when `regex` matches.
    pub exit_status: i32,
}

/// A [`LogExitStatusRule`] with its regex compiled, ready for matching.
#[derive(Debug, Clone)]
pub struct CompiledExitStatusRule {
    pub name: String,
    pub regex: Regex,
    pub exit_status: i32,
}

/// A compiled snapshot of the exit-status scanning knobs: the rules together with the scan
/// depth they were configured with. Handed out as one `Arc` so a frame completing mid-reload
/// sees a consistent pair instead of new rules with an old scan depth.
#[derive(Debug)]
pub struct ExitStatusRuleSet {
    /// Number of trailing log lines to scan (`log_scan_last_lines`); 0 disables scanning.
    pub scan_last_lines: usize,
    pub rules: Vec<CompiledExitStatusRule>,
}

/// Compiles the configured rules, skipping (with a warning) any whose regex is invalid so a
/// single bad pattern can neither disable the whole feature nor fail frame completion.
pub(crate) fn compile_exit_status_rules(
    rules: &[LogExitStatusRule],
) -> Vec<CompiledExitStatusRule> {
    rules
        .iter()
        .filter_map(|rule| match Regex::new(&rule.regex) {
            Ok(regex) => Some(CompiledExitStatusRule {
                name: rule.name.clone(),
                regex,
                exit_status: rule.exit_status,
            }),
            Err(err) => {
                warn!(
                    "Ignoring invalid log_exit_status_rule '{}' (regex {:?}): {}",
                    rule.name, rule.regex, err
                );
                None
            }
        })
        .collect()
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(default)]
pub struct RunnerConfig {
    pub run_on_docker: bool,
    pub default_uid: u32,
    pub default_gid: u32,
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
    /// Number of trailing log lines scanned against `log_exit_status_rules` when a frame
    /// fails. Set to 0, or leave `log_exit_status_rules` empty, to disable log scanning.
    pub log_scan_last_lines: usize,
    /// Ordered list of regex→exit-status rules applied to failed frames' logs. The first
    /// matching rule wins. Empty by default, which disables the feature.
    pub log_exit_status_rules: Vec<LogExitStatusRule>,
    /// How often the watcher re-reads the config file to pick up changes to
    /// `log_exit_status_rules`/`log_scan_last_lines` without a restart (restarting RQD kills
    /// running frames on Linux, where recover mode is not available). Set to 0 to disable
    /// live reloading. Only these two keys are live-reloaded; every other config change still
    /// requires a restart.
    #[serde(with = "humantime_serde")]
    pub log_exit_status_rules_reload_interval: Duration,
    /// Compiled form of `log_exit_status_rules`, seeded lazily on first access (forced at
    /// startup, see `async_main`) and replaced live by the config watcher on reload.
    ///
    /// The outer `Arc` is shared by every clone of this config — each `RunningFrame` holds a
    /// clone frozen at frame creation, so this cell is what lets a reload reach frames that
    /// were already running. Not part of the serialized config: a frame recovered from a
    /// snapshot gets the live cell back when its config is replaced in `from_snapshot`.
    #[serde(skip)]
    compiled_exit_status_rules: Arc<RwLock<Option<Arc<ExitStatusRuleSet>>>>,
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
        let shell_path = if cfg!(target_os = "windows") {
            "cmd.exe".to_string()
        } else {
            "/bin/bash".to_string()
        };
        let home_dir = std::env::var("HOME")
            .or_else(|_| std::env::var("USERPROFILE"))
            .unwrap_or("/tmp".to_string());

        Self {
            run_on_docker: false,
            default_uid: 1000,
            default_gid: 20,
            prepend_timestamp: true,
            use_host_path_env_var: false,
            desktop_mode: false,
            run_as_user: false,
            temp_path: std::env::temp_dir().to_str().unwrap_or("/tmp").to_string(),
            shell_path,
            snapshots_path: format!("{}/.rqd/snapshots", home_dir),
            kill_monitor_interval: Duration::from_secs(120),
            kill_monitor_timeout: Duration::from_secs(1200),
            force_kill_after_timeout: false,
            docker_mounts: Vec::new(),
            docker_default_image: "ubuntu:latest".to_string(),
            docker_images: HashMap::new(),
            log_scan_last_lines: 50,
            log_exit_status_rules: Vec::new(),
            log_exit_status_rules_reload_interval: Duration::from_secs(300), // 5 min
            compiled_exit_status_rules: Arc::new(RwLock::new(None)),
        }
    }
}

impl RunnerConfig {
    /// Returns the current compiled `log_exit_status_rules`, seeding the shared cell from this
    /// config's raw fields on first call.
    ///
    /// Because compilation happens once per rule set (forced at startup, see `async_main`, and
    /// again only when the watcher applies a reload), the warning for an invalid pattern is
    /// emitted once per load rather than repeating on every failed frame, and no frame pays the
    /// cost of recompiling every regex when it fails.
    pub fn compiled_exit_status_rules(&self) -> Arc<ExitStatusRuleSet> {
        let guard = self
            .compiled_exit_status_rules
            .read()
            .unwrap_or_else(|err| err.into_inner());
        if let Some(rule_set) = guard.as_ref() {
            return Arc::clone(rule_set);
        }
        drop(guard);

        let mut guard = self
            .compiled_exit_status_rules
            .write()
            .unwrap_or_else(|err| err.into_inner());
        // Another thread may have seeded the cell between the read and write locks.
        if let Some(rule_set) = guard.as_ref() {
            return Arc::clone(rule_set);
        }
        let rule_set = Arc::new(ExitStatusRuleSet {
            scan_last_lines: self.log_scan_last_lines,
            rules: compile_exit_status_rules(&self.log_exit_status_rules),
        });
        *guard = Some(Arc::clone(&rule_set));
        rule_set
    }

    /// Compiles `rules` and swaps them into the shared cell, making them the set every frame —
    /// including frames launched before this call — scans on failure from now on. Rules with
    /// invalid regexes are skipped with a warning, same as at startup.
    pub fn reload_exit_status_rules(&self, scan_last_lines: usize, rules: &[LogExitStatusRule]) {
        let rule_set = Arc::new(ExitStatusRuleSet {
            scan_last_lines,
            rules: compile_exit_status_rules(rules),
        });
        *self
            .compiled_exit_status_rules
            .write()
            .unwrap_or_else(|err| err.into_inner()) = Some(rule_set);
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
    /// Returns the config file path and whether its presence is required (it is when the
    /// operator pointed at it explicitly via `OPENCUE_RQD_CONFIG`).
    fn config_file_source() -> (String, bool) {
        match env::var("OPENCUE_RQD_CONFIG") {
            Ok(v) => (v, true),
            Err(_) => (DEFAULT_CONFIG_FILE.to_string(), false),
        }
    }

    /// Reads and deserializes the config from its sources (config file + `OPENRQD` environment
    /// variables) without performing any filesystem setup. Used both by the initial [`load`]
    /// and by the watcher re-reading the file at runtime.
    fn read_sources() -> Result<Self, RqdConfigError> {
        let (config_file, required) = Self::config_file_source();

        let config = ConfigBase::builder()
            .add_source(File::with_name(&config_file).required(required))
            .add_source(
                Environment::with_prefix("OPENRQD")
                    .separator("__")
                    .list_separator(","),
            )
            .build()
            .map_err(|err| {
                RqdConfigError::LoadConfigError(format!(
                    "{:?} config could not be loaded. {}",
                    &config_file, err
                ))
            })?;

        Config::deserialize(config).map_err(|err| {
            RqdConfigError::LoadConfigError(format!(
                "{:?} config could not be deserialized. {}",
                &config_file, err
            ))
        })
    }

    // load the current config from the system config and environment variables
    fn load() -> Result<Self, RqdConfigError> {
        let (config_file, _) = Self::config_file_source();
        println!(" INFO Config::load: using config file: {:?}", config_file);

        let deserialized_config = Self::read_sources()?;

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
        // Ensure machine temp path exists. read_temp_storage calls statvfs
        // directly on this path, which fails with ENOENT if missing; frame
        // launch also uses temp_path as its working dir. create_dir_all is
        // a no-op when the directory already exists, so the only path it
        // surfaces an error for is the genuinely-broken case (parent missing,
        // permission denied, etc.).
        let temp_path = Path::new(&self.machine.temp_path);
        fs::create_dir_all(temp_path).map_err(|err| {
            RqdConfigError::InvalidPath(format!(
                "Failed to create machine temp dir at {:?}: {err}",
                temp_path
            ))
        })?;
        if !temp_path.is_dir() {
            return Err(RqdConfigError::InvalidPath(format!(
                "Machine temp path is not a directory: {:?}",
                temp_path
            )));
        }
        Ok(())
    }
}

/// Periodically re-reads the config sources and applies changes to `log_exit_status_rules` and
/// `log_scan_last_lines` to the live rule set, so operators can register new license-error
/// patterns without restarting RQD.
///
/// Only those two keys are live-reloaded; changes to anything else in the file are ignored
/// until the next restart. A file that is missing, unreadable, or fails to parse leaves the
/// current rules untouched (with a warning), so a half-written edit can never wipe the rules
/// out from under running frames.
///
/// Runs forever; spawn it as a background task. Returns immediately when
/// `log_exit_status_rules_reload_interval` is 0.
pub async fn watch_exit_status_rules() {
    let interval = CONFIG.runner.log_exit_status_rules_reload_interval;
    if interval.is_zero() {
        info!("log_exit_status_rules live reload is disabled (reload interval = 0)");
        return;
    }

    let mut last_applied = (
        CONFIG.runner.log_scan_last_lines,
        CONFIG.runner.log_exit_status_rules.clone(),
    );
    let mut ticker = tokio::time::interval(interval);
    ticker.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);
    // The first tick of a tokio interval fires immediately; skip it, startup already
    // compiled the initial rules.
    ticker.tick().await;

    loop {
        ticker.tick().await;

        let new_config = match Config::read_sources() {
            Ok(config) => config,
            Err(err) => {
                warn!("Skipping log_exit_status_rules reload, config re-read failed: {err}");
                continue;
            }
        };

        let candidate = (
            new_config.runner.log_scan_last_lines,
            new_config.runner.log_exit_status_rules,
        );
        if candidate == last_applied {
            continue;
        }

        CONFIG
            .runner
            .reload_exit_status_rules(candidate.0, &candidate.1);
        info!(
            "Reloaded log_exit_status_rules: {} rule(s) [{}], log_scan_last_lines={}",
            candidate.1.len(),
            candidate
                .1
                .iter()
                .map(|rule| rule.name.as_str())
                .collect::<Vec<_>>()
                .join(", "),
            candidate.0,
        );
        last_applied = candidate;
    }
}
