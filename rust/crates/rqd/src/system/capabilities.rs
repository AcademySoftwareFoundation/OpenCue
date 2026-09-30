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

//! Startup capability preflight.
//!
//! When `runner.run_as_user` is set, RQD switches the uid/gid of every frame process
//! (`CAP_SETUID`/`CAP_SETGID`) and chowns artist-owned log directories it does not own
//! (`CAP_CHOWN` plus `CAP_DAC_OVERRIDE`/`CAP_FOWNER` to write into them). If those
//! effective capabilities are missing, every frame fails at launch with an opaque error.
//! This module verifies them up front so a mis-provisioned node fails fast and loudly at
//! startup instead of silently failing every frame.

use crate::config::RunnerConfig;
use miette::Result;

#[cfg(target_os = "linux")]
mod imp {
    use super::*;
    use miette::miette;

    /// `(name, bit)` of the capabilities required when `run_as_user` is enabled.
    /// Bit numbers per `<linux/capability.h>`.
    const REQUIRED_CAPS: &[(&str, u8)] = &[
        ("CAP_CHOWN", 0),
        ("CAP_DAC_OVERRIDE", 1),
        ("CAP_FOWNER", 3),
        ("CAP_SETGID", 6),
        ("CAP_SETUID", 7),
    ];

    /// Reads the effective capability bitmask (`CapEff`) of the current process from
    /// `/proc/self/status`. Returns `None` if it can't be read or parsed.
    fn effective_caps() -> Option<u64> {
        let status = std::fs::read_to_string("/proc/self/status").ok()?;
        for line in status.lines() {
            if let Some(hex) = line.strip_prefix("CapEff:") {
                return u64::from_str_radix(hex.trim(), 16).ok();
            }
        }
        None
    }

    pub fn preflight(config: &RunnerConfig) -> Result<()> {
        if !config.run_as_user {
            return Ok(());
        }

        // Validate the effective set even when running as root: in containers and user
        // namespaces a uid-0 process can have a reduced CapEff and would otherwise fail
        // at frame launch instead of here.
        let caps = effective_caps().ok_or_else(|| {
            miette!(
                "runner.run_as_user is enabled but RQD could not read its effective \
                 capabilities from /proc/self/status to verify it can switch frame users"
            )
        })?;

        let missing: Vec<&str> = REQUIRED_CAPS
            .iter()
            .filter(|(_, bit)| (caps & (1u64 << *bit)) == 0)
            .map(|(name, _)| *name)
            .collect();

        if missing.is_empty() {
            return Ok(());
        }

        Err(miette!(
            "runner.run_as_user is enabled but RQD is missing required Linux capabilities: {}. \
             Without them every frame fails when switching to the artist's uid/gid or writing its \
             log. Grant them to the binary (e.g. `setcap \
             cap_setuid,cap_setgid,cap_chown,cap_dac_override,cap_fowner=ep /usr/bin/openrqd`) or \
             run RQD as root.",
            missing.join(", ")
        ))
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn test_preflight_noop_when_run_as_user_disabled() {
            let mut config = RunnerConfig::default();
            config.run_as_user = false;
            assert!(preflight(&config).is_ok());
        }

        #[test]
        fn test_required_caps_bit_decoding() {
            // A mask with only CAP_CHOWN(0) and CAP_SETUID(7) set.
            let caps: u64 = (1 << 0) | (1 << 7);
            let missing: Vec<&str> = REQUIRED_CAPS
                .iter()
                .filter(|(_, bit)| (caps & (1u64 << *bit)) == 0)
                .map(|(name, _)| *name)
                .collect();
            assert_eq!(
                missing,
                vec!["CAP_DAC_OVERRIDE", "CAP_FOWNER", "CAP_SETGID"]
            );
        }
    }
}

#[cfg(target_os = "linux")]
pub use imp::preflight;

/// Capabilities are a Linux concept; nothing to verify on other platforms.
#[cfg(not(target_os = "linux"))]
pub fn preflight(_config: &RunnerConfig) -> Result<()> {
    Ok(())
}
