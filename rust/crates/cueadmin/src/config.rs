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

//! Cuebot connection settings, read from the same YAML file pycue uses.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::Duration;

use miette::{bail, miette, IntoDiagnostic, Result, WrapErr};
use tracing::debug;
use yaml_rust2::{Yaml, YamlLoader};

const CONFIG_FILE_ENV_VARS: [&str; 2] = ["OPENCUE_CONFIG_FILE", "OPENCUE_CONF"];

/// Connection settings for reaching a Cuebot.
#[derive(Debug, Clone, PartialEq)]
pub struct Config {
    /// Port used for addresses that don't name one.
    pub grpc_port: u16,
    /// Deadline for each RPC.
    pub timeout: Duration,
    /// Largest gRPC message accepted or sent.
    pub max_message_bytes: usize,
    /// Facility used when none is requested.
    pub facility_default: String,
    /// Cuebot addresses per facility.
    pub facilities: BTreeMap<String, Vec<String>>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            grpc_port: 8443,
            timeout: Duration::from_millis(10_000),
            max_message_bytes: 104_857_600,
            facility_default: "local".to_string(),
            facilities: BTreeMap::from([("local".to_string(), vec!["localhost:8443".to_string()])]),
        }
    }
}

impl Config {
    /// Loads the user's pycue config file, if any, on top of the defaults.
    ///
    /// The file is the first of `$OPENCUE_CONFIG_FILE`, `$OPENCUE_CONF` and
    /// `~/.config/opencue/opencue.yaml` that exists.
    pub fn load() -> Result<Self> {
        match find_config_file() {
            Some(path) => {
                debug!("loading opencue config from {}", path.display());
                let text = std::fs::read_to_string(&path)
                    .into_diagnostic()
                    .wrap_err_with(|| format!("reading {}", path.display()))?;
                Self::from_yaml(&text).wrap_err_with(|| format!("parsing {}", path.display()))
            }
            None => Ok(Self::default()),
        }
    }

    /// Parses a pycue YAML config, falling back to defaults for missing keys.
    ///
    /// pycue uses flat, dotted keys such as `cuebot.facility_default`.
    pub fn from_yaml(text: &str) -> Result<Self> {
        let mut config = Self::default();
        let docs = YamlLoader::load_from_str(text).into_diagnostic()?;
        let Some(doc) = docs.first() else {
            return Ok(config);
        };
        if doc.is_null() {
            return Ok(config);
        }
        if doc.as_hash().is_none() {
            bail!("expected a mapping at the top level");
        }

        if let Some(port) = int(doc, "cuebot.grpc_port")? {
            config.grpc_port = u16::try_from(port)
                .map_err(|_| miette!("cuebot.grpc_port {port} is not a valid port"))?;
        }
        if let Some(ms) = int(doc, "cuebot.timeout")? {
            config.timeout = Duration::from_millis(ms.max(0) as u64);
        }
        if let Some(bytes) = int(doc, "cuebot.max_message_bytes")? {
            config.max_message_bytes = bytes.max(0) as usize;
        }
        match &doc["cuebot.facility_default"] {
            Yaml::BadValue => {}
            Yaml::String(s) => config.facility_default = s.clone(),
            _ => return Err(miette!("cuebot.facility_default must be a string")),
        }
        match &doc["cuebot.facility"] {
            Yaml::BadValue => {}
            Yaml::Hash(map) => {
                config.facilities = map
                    .iter()
                    .map(|(name, hosts)| {
                        let name = name
                            .as_str()
                            .ok_or_else(|| miette!("cuebot.facility keys must be strings"))?;
                        Ok((name.to_string(), host_list(hosts)?))
                    })
                    .collect::<Result<_>>()?;
            }
            _ => {
                return Err(miette!(
                    "cuebot.facility must map facility names to host lists"
                ))
            }
        }
        Ok(config)
    }

    /// Picks the Cuebot addresses to try, in order of precedence: `--server`, `--facility`,
    /// `$CUEBOT_HOSTS`, then `$CUEBOT_FACILITY` or the default facility.
    ///
    /// Addresses without a port get [`Config::grpc_port`].
    pub fn resolve_hosts(
        &self,
        server: &[String],
        facility: Option<&str>,
        env_hosts: Option<&str>,
        env_facility: Option<&str>,
    ) -> Result<Vec<String>> {
        let hosts: Vec<String> = if !server.is_empty() {
            server.to_vec()
        } else if let Some(facility) = facility {
            self.facility_hosts(facility)?
        } else if let Some(env_hosts) = env_hosts.filter(|h| !h.trim().is_empty()) {
            env_hosts.split(',').map(str::to_string).collect()
        } else {
            self.facility_hosts(env_facility.unwrap_or(&self.facility_default))?
        };

        let hosts: Vec<String> = hosts
            .iter()
            .map(|h| h.trim())
            .filter(|h| !h.is_empty())
            .map(|h| self.with_port(h))
            .collect();
        if hosts.is_empty() {
            bail!("no Cuebot host configured; use --server or set CUEBOT_HOSTS");
        }
        Ok(hosts)
    }

    fn facility_hosts(&self, facility: &str) -> Result<Vec<String>> {
        self.facilities.get(facility).cloned().ok_or_else(|| {
            let known: Vec<&str> = self.facilities.keys().map(String::as_str).collect();
            miette!(
                "unknown facility '{facility}'; configured facilities: {}",
                known.join(", ")
            )
        })
    }

    /// Normalizes an address to `host:port`: drops an `http://` prefix, brackets bare IPv6
    /// literals and appends [`Config::grpc_port`] when no port is given.
    fn with_port(&self, host: &str) -> String {
        let host = host.strip_prefix("http://").unwrap_or(host);
        let port = self.grpc_port;
        if host.starts_with('[') {
            if host.contains("]:") {
                host.to_string()
            } else {
                format!("{host}:{port}")
            }
        } else if host.matches(':').count() > 1 {
            format!("[{host}]:{port}")
        } else if host.contains(':') {
            host.to_string()
        } else {
            format!("{host}:{port}")
        }
    }
}

fn int(doc: &Yaml, key: &str) -> Result<Option<i64>> {
    match &doc[key] {
        Yaml::BadValue => Ok(None),
        Yaml::Integer(i) => Ok(Some(*i)),
        _ => Err(miette!("{key} must be an integer")),
    }
}

fn host_list(value: &Yaml) -> Result<Vec<String>> {
    match value {
        Yaml::String(s) => Ok(vec![s.clone()]),
        Yaml::Array(items) => items
            .iter()
            .map(|item| {
                item.as_str()
                    .map(str::to_string)
                    .ok_or_else(|| miette!("facility hosts must be strings"))
            })
            .collect(),
        _ => Err(miette!("facility hosts must be a list of strings")),
    }
}

fn find_config_file() -> Option<PathBuf> {
    CONFIG_FILE_ENV_VARS
        .iter()
        .filter_map(std::env::var_os)
        .map(PathBuf::from)
        .chain(config_base_directory().map(|dir| dir.join("opencue.yaml")))
        .find(|path| Path::is_file(path))
}

fn config_base_directory() -> Option<PathBuf> {
    if cfg!(windows) {
        std::env::var_os("APPDATA").map(|dir| PathBuf::from(dir).join("opencue"))
    } else {
        std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".config").join("opencue"))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = r#"
cuebot.grpc_port: 9000
cuebot.timeout: 2500
cuebot.facility_default: dev
cuebot.facility:
    dev:
        - cuebot-dev1
        - cuebot-dev2:8443
    prod: cuebot-prod
"#;

    #[test]
    fn parses_pycue_config() {
        let config = Config::from_yaml(SAMPLE).unwrap();
        assert_eq!(config.grpc_port, 9000);
        assert_eq!(config.timeout, Duration::from_millis(2500));
        assert_eq!(config.max_message_bytes, 104_857_600);
        assert_eq!(config.facility_default, "dev");
        assert_eq!(
            config.facilities["dev"],
            ["cuebot-dev1", "cuebot-dev2:8443"]
        );
        assert_eq!(config.facilities["prod"], ["cuebot-prod"]);
    }

    #[test]
    fn empty_config_is_default() {
        assert_eq!(Config::from_yaml("").unwrap(), Config::default());
        assert_eq!(Config::from_yaml("# nothing\n").unwrap(), Config::default());
    }

    #[test]
    fn rejects_bad_values() {
        assert!(Config::from_yaml("cuebot.grpc_port: lots").is_err());
        assert!(Config::from_yaml("cuebot.facility: [a, b]").is_err());
        assert!(Config::from_yaml("- a\n- b").is_err());
    }

    #[test]
    fn host_precedence() {
        let config = Config::from_yaml(SAMPLE).unwrap();
        let server = vec!["explicit".to_string()];

        let resolve = |server: &[String], facility, env_hosts, env_facility| {
            config
                .resolve_hosts(server, facility, env_hosts, env_facility)
                .unwrap()
        };

        assert_eq!(
            resolve(&server, Some("prod"), Some("env"), None),
            ["explicit:9000"]
        );
        assert_eq!(
            resolve(&[], Some("prod"), Some("env"), None),
            ["cuebot-prod:9000"]
        );
        assert_eq!(
            resolve(&[], None, Some("e1, e2:1"), Some("prod")),
            ["e1:9000", "e2:1"]
        );
        assert_eq!(resolve(&[], None, None, Some("prod")), ["cuebot-prod:9000"]);
        assert_eq!(
            resolve(&[], None, Some(""), None),
            ["cuebot-dev1:9000", "cuebot-dev2:8443"]
        );
    }

    #[test]
    fn normalizes_addresses() {
        let config = Config::default();
        assert_eq!(config.with_port("cuebot"), "cuebot:8443");
        assert_eq!(config.with_port("cuebot:9000"), "cuebot:9000");
        assert_eq!(config.with_port("http://cuebot:9000"), "cuebot:9000");
        assert_eq!(config.with_port("::1"), "[::1]:8443");
        assert_eq!(config.with_port("[::1]"), "[::1]:8443");
        assert_eq!(config.with_port("[::1]:9000"), "[::1]:9000");
    }

    #[test]
    fn unknown_facility_is_an_error() {
        let config = Config::default();
        let err = config
            .resolve_hosts(&[], Some("mars"), None, None)
            .unwrap_err();
        assert!(err.to_string().contains("unknown facility 'mars'"));
    }
}
