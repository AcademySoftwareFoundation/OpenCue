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

use uuid::Uuid;

pub mod capabilities;
#[cfg(any(target_os = "linux", all(target_os = "macos", debug_assertions)))]
pub mod linux;
pub mod machine;
#[cfg(feature = "nimby")]
pub mod nimby;
mod oom;
mod reservation;

#[cfg(target_os = "macos")]
pub mod macos;
#[cfg(target_os = "windows")]
pub mod windows;
pub mod manager;

pub type ResourceId = Uuid;
pub type CoreId = u32;
pub type PhysId = u32;
pub type ThreadId = u32;

pub use oom::OOM_REASON_MSG;

/// Maps a kill/killpg result so ESRCH ("no such process") counts as success: the target is
/// already gone, which is exactly the state the signal was meant to reach. Reporting it as a
/// failure makes callers (and Cuebot behind them) treat an already-dead render as an unconfirmed
/// kill. Any other errno is a real failure.
#[cfg(unix)]
pub(crate) fn signal_result_tolerating_esrch(
    result: nix::Result<()>,
    target: u32,
    action: &str,
) -> miette::Result<()> {
    match result {
        Ok(()) => Ok(()),
        Err(nix::errno::Errno::ESRCH) => {
            tracing::info!("{action} {target}: process group already gone (ESRCH), nothing to kill");
            Ok(())
        }
        Err(err) => Err(miette::miette!("Failed to {action} {target}. {err}")),
    }
}

/// Returns whether a process with this pid currently exists (including zombies), probing with
/// kill(pid, 0) -- deliberately independent of any cached /proc scan, so it stays reliable when
/// the scan itself is stalled or incomplete. EPERM means the process exists but belongs to
/// another user, which still counts as alive.
#[cfg(unix)]
pub(crate) fn pid_exists(pid: u32) -> bool {
    match nix::sys::signal::kill(nix::unistd::Pid::from_raw(pid as i32), None) {
        Ok(()) => true,
        Err(nix::errno::Errno::EPERM) => true,
        Err(_) => false,
    }
}

#[cfg(all(test, unix))]
mod pid_exists_tests {
    use super::pid_exists;

    #[test]
    fn own_pid_is_alive() {
        assert!(pid_exists(std::process::id()));
    }

    #[test]
    fn reaped_child_is_gone() {
        let mut child = std::process::Command::new("true")
            .spawn()
            .expect("spawn should work");
        let pid = child.id();
        child.wait().expect("wait should work");
        assert!(!pid_exists(pid));
    }
}

#[cfg(all(test, unix))]
mod signal_result_tests {
    use super::signal_result_tolerating_esrch;

    #[test]
    fn esrch_counts_as_success() {
        assert!(signal_result_tolerating_esrch(Err(nix::errno::Errno::ESRCH), 1234, "kill").is_ok());
    }

    #[test]
    fn other_errnos_stay_failures() {
        assert!(
            signal_result_tolerating_esrch(Err(nix::errno::Errno::EPERM), 1234, "kill").is_err()
        );
    }

    #[test]
    fn ok_passes_through() {
        assert!(signal_result_tolerating_esrch(Ok(()), 1234, "kill").is_ok());
    }
}
