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

use std::cmp::Ordering;
use std::collections::BTreeSet;

use miette::{bail, Result};
use opencue_proto::host::{
    self as pb, HardwareStateSeq, Host, HostDeleteRequest, HostLockRequest,
    HostRebootWhenIdleRequest, HostSearchCriteria, HostSetAllocationRequest,
    HostSetHardwareStateRequest, HostSetThreadModeRequest, HostUnlockRequest,
};
use tracing::{debug, warn};

use super::Context;
use crate::cli::{HardwareState, HostCommand, HostSelection, LockState, ThreadMode};
use crate::client::rpc_error;
use crate::output;

/// Runs a `host` subcommand.
pub async fn run(ctx: &Context, cmd: HostCommand) -> Result<()> {
    let cuebot = &ctx.cuebot;
    match cmd {
        HostCommand::List {
            matches,
            state,
            alloc,
            lock_state,
            sort_idle,
        } => {
            let criteria = HostSearchCriteria {
                substr: matches,
                allocs: alloc,
                states: (!state.is_empty()).then(|| HardwareStateSeq {
                    state: state
                        .into_iter()
                        .map(|s| hardware_state(s) as i32)
                        .collect(),
                }),
                ..Default::default()
            };
            let mut hosts = cuebot.get_hosts(criteria).await?;
            if let Some(lock_state) = lock_state {
                let wanted = self::lock_state(lock_state) as i32;
                hosts.retain(|h| h.lock_state == wanted);
            }
            sort_hosts(&mut hosts, sort_idle);
            print!("{}", output::hosts(&hosts, now()));
        }
        HostCommand::Lock(selection) => {
            for host in resolve(ctx, &selection).await? {
                debug!("locking host {}", host.name);
                let name = host.name.clone();
                cuebot
                    .host()
                    .lock(HostLockRequest { host: Some(host) })
                    .await
                    .map_err(rpc_error(format!("locking '{name}'")))?;
            }
        }
        HostCommand::Unlock(selection) => {
            for host in resolve(ctx, &selection).await? {
                debug!("unlocking host {}", host.name);
                let name = host.name.clone();
                cuebot
                    .host()
                    .unlock(HostUnlockRequest { host: Some(host) })
                    .await
                    .map_err(rpc_error(format!("unlocking '{name}'")))?;
            }
        }
        HostCommand::Move { alloc, selection } => {
            let hosts = resolve(ctx, &selection).await?;
            let dst = cuebot.find_allocation(&alloc).await?;
            if !ctx.confirm(&format!("Move {} hosts to {alloc}", hosts.len()))? {
                return Ok(());
            }
            for host in hosts {
                debug!("moving {} to {alloc}", host.name);
                let name = host.name.clone();
                cuebot
                    .host()
                    .set_allocation(HostSetAllocationRequest {
                        host: Some(host),
                        allocation_id: dst.id.clone(),
                    })
                    .await
                    .map_err(rpc_error(format!("moving '{name}' to '{alloc}'")))?;
            }
        }
        HostCommand::Delete(selection) => {
            let hosts = resolve(ctx, &selection).await?;
            if !ctx.confirm(&format!("Delete {} hosts", hosts.len()))? {
                return Ok(());
            }
            for host in hosts {
                debug!("deleting host {}", host.name);
                let name = host.name.clone();
                cuebot
                    .host()
                    .delete(HostDeleteRequest { host: Some(host) })
                    .await
                    .map_err(rpc_error(format!("deleting '{name}'")))?;
            }
        }
        HostCommand::SafeReboot(selection) => {
            let hosts = resolve(ctx, &selection).await?;
            if !ctx.confirm(&format!("Lock and reboot {} hosts when idle", hosts.len()))? {
                return Ok(());
            }
            for host in hosts {
                debug!("locking {} and rebooting when idle", host.name);
                let name = host.name.clone();
                cuebot
                    .host()
                    .reboot_when_idle(HostRebootWhenIdleRequest { host: Some(host) })
                    .await
                    .map_err(rpc_error(format!("rebooting '{name}'")))?;
            }
        }
        HostCommand::Repair(selection) => {
            set_hardware_state(ctx, &selection, pb::HardwareState::Repair).await?
        }
        HostCommand::Up(selection) => {
            set_hardware_state(ctx, &selection, pb::HardwareState::Up).await?
        }
        HostCommand::ThreadMode { mode, selection } => {
            let hosts = resolve(ctx, &selection).await?;
            let mode = thread_mode(mode);
            if !ctx.confirm(&format!(
                "Set {} hosts to thread mode {}",
                hosts.len(),
                mode.as_str_name()
            ))? {
                return Ok(());
            }
            for host in hosts {
                debug!(
                    "setting {} to thread mode {}",
                    host.name,
                    mode.as_str_name()
                );
                let name = host.name.clone();
                cuebot
                    .host()
                    .set_thread_mode(HostSetThreadModeRequest {
                        host: Some(host),
                        mode: mode as i32,
                    })
                    .await
                    .map_err(rpc_error(format!("setting thread mode of '{name}'")))?;
            }
        }
    }
    Ok(())
}

async fn set_hardware_state(
    ctx: &Context,
    selection: &HostSelection,
    state: pb::HardwareState,
) -> Result<()> {
    let hosts = resolve(ctx, selection).await?;
    if !ctx.confirm(&format!(
        "Set {} hosts into the {} state",
        hosts.len(),
        state.as_str_name()
    ))? {
        return Ok(());
    }
    for host in hosts {
        debug!(
            "setting {} into the {} state",
            host.name,
            state.as_str_name()
        );
        let name = host.name.clone();
        ctx.cuebot
            .host()
            .set_hardware_state(HostSetHardwareStateRequest {
                host: Some(host),
                state: state as i32,
            })
            .await
            .map_err(rpc_error(format!("setting state of '{name}'")))?;
    }
    Ok(())
}

/// Looks up the selected hosts, warning about names that matched nothing.
async fn resolve(ctx: &Context, selection: &HostSelection) -> Result<Vec<Host>> {
    let hosts = ctx.cuebot.get_hosts(selection_criteria(selection)?).await?;
    if hosts.is_empty() {
        bail!("no hosts matched the selection");
    }
    let missing = missing_names(&selection.hosts, &hosts);
    if !missing.is_empty() {
        warn!(
            "these hosts were not found and will be skipped: {}",
            missing.join(", ")
        );
    }
    debug!("selected {} hosts", hosts.len());
    Ok(hosts)
}

/// Builds the search for a host selection. Blank names and substrings are dropped, since an
/// empty substring would match every host on the farm.
fn selection_criteria(selection: &HostSelection) -> Result<HostSearchCriteria> {
    let non_blank = |values: &[String]| -> Vec<String> {
        values
            .iter()
            .map(|v| v.trim())
            .filter(|v| !v.is_empty())
            .map(str::to_string)
            .collect()
    };
    let criteria = if selection.hosts.is_empty() {
        HostSearchCriteria {
            substr: non_blank(&selection.matches),
            ..Default::default()
        }
    } else {
        HostSearchCriteria {
            hosts: non_blank(&selection.hosts),
            ..Default::default()
        }
    };
    if criteria.substr.is_empty() && criteria.hosts.is_empty() {
        bail!("the host selection is empty; give host names or a non-empty --match");
    }
    Ok(criteria)
}

fn missing_names<'a>(requested: &'a [String], found: &[Host]) -> Vec<&'a str> {
    let found: BTreeSet<&str> = found.iter().map(|h| h.name.as_str()).collect();
    requested
        .iter()
        .map(String::as_str)
        .filter(|name| !found.contains(name))
        .collect()
}

fn sort_hosts(hosts: &mut [Host], by_idle: bool) {
    if by_idle {
        hosts.sort_by(|a, b| {
            b.idle_cores
                .partial_cmp(&a.idle_cores)
                .unwrap_or(Ordering::Equal)
                .then(b.idle_memory.cmp(&a.idle_memory))
        });
    } else {
        hosts.sort_by(|a, b| a.name.cmp(&b.name));
    }
}

fn now() -> i64 {
    chrono::Utc::now().timestamp()
}

fn hardware_state(state: HardwareState) -> pb::HardwareState {
    match state {
        HardwareState::Up => pb::HardwareState::Up,
        HardwareState::Down => pb::HardwareState::Down,
        HardwareState::Rebooting => pb::HardwareState::Rebooting,
        HardwareState::RebootWhenIdle => pb::HardwareState::RebootWhenIdle,
        HardwareState::Repair => pb::HardwareState::Repair,
    }
}

fn lock_state(state: LockState) -> pb::LockState {
    match state {
        LockState::Open => pb::LockState::Open,
        LockState::Locked => pb::LockState::Locked,
        LockState::NimbyLocked => pb::LockState::NimbyLocked,
    }
}

fn thread_mode(mode: ThreadMode) -> pb::ThreadMode {
    match mode {
        ThreadMode::Auto => pb::ThreadMode::Auto,
        ThreadMode::All => pb::ThreadMode::All,
        ThreadMode::Variable => pb::ThreadMode::Variable,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn host(name: &str, idle_cores: f32, idle_memory: i64) -> Host {
        Host {
            name: name.into(),
            idle_cores,
            idle_memory,
            ..Default::default()
        }
    }

    fn names(hosts: &[Host]) -> Vec<&str> {
        hosts.iter().map(|h| h.name.as_str()).collect()
    }

    #[test]
    fn sorts_by_name_or_idle() {
        let mut hosts = vec![host("b", 1.0, 10), host("a", 4.0, 5), host("c", 4.0, 50)];
        sort_hosts(&mut hosts, false);
        assert_eq!(names(&hosts), ["a", "b", "c"]);
        sort_hosts(&mut hosts, true);
        assert_eq!(names(&hosts), ["c", "a", "b"]);
    }

    #[test]
    fn blank_matches_never_select_every_host() {
        let selection = |hosts: &[&str], matches: &[&str]| HostSelection {
            hosts: hosts.iter().map(|s| s.to_string()).collect(),
            matches: matches.iter().map(|s| s.to_string()).collect(),
        };
        let c = selection_criteria(&selection(&[], &["vrack", "", " "])).unwrap();
        assert_eq!(c.substr, ["vrack"]);
        assert!(selection_criteria(&selection(&[], &["", " "])).is_err());
        assert!(selection_criteria(&selection(&[""], &[])).is_err());
        assert_eq!(
            selection_criteria(&selection(&["h1"], &[])).unwrap().hosts,
            ["h1"]
        );
    }

    #[test]
    fn reports_missing_hosts() {
        let requested = vec!["a".to_string(), "b".to_string()];
        assert_eq!(missing_names(&requested, &[host("a", 0.0, 0)]), ["b"]);
        assert!(missing_names(&[], &[host("a", 0.0, 0)]).is_empty());
    }
}
