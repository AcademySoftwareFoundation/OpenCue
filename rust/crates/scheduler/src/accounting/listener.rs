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

//! PostgreSQL `LISTEN/NOTIFY` listener: the live, cross-process feed that keeps the
//! in-memory [`Store`] fresh between recompute passes. See
//! `docs/_docs/developer-guide/scheduler-accounting.md`.
//!
//! Cuebot emits two channels, each in the same transaction as the PG write it describes
//! (so a notification is delivered iff that write commits):
//! - `acct_release`: a per-proc release delta on `unbookProc` for scheduler-managed
//!   shows. Cores/gpus are signed deltas (negative for a release).
//! - `acct_limit_change`: an enforced cap change from a cueadmin operation.
//!
//! Both are best-effort optimisations: a dropped notification (listener reconnecting)
//! only leaves the store reading high → under-book → healed by the next recompute /
//! limit reseed. Nothing here can over-book a hard cap.

use std::sync::Arc;
use std::time::Duration;

use serde::Deserialize;
use sqlx::postgres::PgListener;
use tracing::{debug, info, warn};
use uuid::Uuid;

use crate::accounting::booking_delta::BookingDelta;
use crate::accounting::store::{LimitChange, Store};
use crate::config::CONFIG;

const RELEASE_CHANNEL: &str = "acct_release";
const LIMIT_CHANGE_CHANNEL: &str = "acct_limit_change";
const RECONNECT_BACKOFF: Duration = Duration::from_secs(5);

/// Release delta payload on `acct_release`. Cores/gpus are signed deltas to apply
/// directly to the store (negative for a release). Cuebot also includes `layer`/`dept`
/// for symmetry/debuggability; serde ignores those extra fields (the store only enforces
/// subscription/folder/job).
#[derive(Debug, Deserialize)]
struct ReleasePayload {
    show: Uuid,
    alloc: Uuid,
    folder: Uuid,
    job: Uuid,
    cores: i64,
    gpus: i32,
    /// Slots released (defaults to 0 for regular procs / older Cuebot payloads).
    #[serde(default)]
    slots: i64,
}

/// Cap change payload on `acct_limit_change`. Values are in cores (`-1` = unlimited),
/// GPUs pass through. Exactly one optional field is set per message.
#[derive(Debug, Deserialize)]
#[serde(tag = "vertex")]
enum LimitChangePayload {
    #[serde(rename = "sub")]
    Sub {
        show: Uuid,
        alloc: Uuid,
        #[serde(default)]
        burst: Option<i64>,
        #[serde(default)]
        max_slots: Option<i64>,
    },
    #[serde(rename = "folder")]
    Folder {
        id: Uuid,
        #[serde(default)]
        max_cores: Option<i64>,
        #[serde(default)]
        max_gpus: Option<i64>,
        #[serde(default)]
        max_slots: Option<i64>,
    },
    #[serde(rename = "job")]
    Job {
        id: Uuid,
        #[serde(default)]
        max_cores: Option<i64>,
        #[serde(default)]
        max_gpus: Option<i64>,
        #[serde(default)]
        max_slots: Option<i64>,
    },
}

/// Spawns the listen loop. Reconnects with a fixed backoff on any failure; the recompute
/// and limit-reseed loops are the correctness backstop for whatever it misses.
pub fn spawn_loop(store: Arc<Store>) {
    tokio::spawn(async move {
        loop {
            if let Err(err) = run(&store).await {
                warn!(
                    "Accounting NOTIFY listener disconnected: {err}; reconnecting in {:?} \
                     (recompute heals the gap)",
                    RECONNECT_BACKOFF
                );
            }
            tokio::time::sleep(RECONNECT_BACKOFF).await;
        }
    });
}

async fn run(store: &Store) -> Result<(), sqlx::Error> {
    let mut listener = PgListener::connect(&CONFIG.database.connection_url()).await?;
    listener
        .listen_all([RELEASE_CHANNEL, LIMIT_CHANGE_CHANNEL])
        .await?;
    info!("Accounting NOTIFY listener connected ({RELEASE_CHANNEL}, {LIMIT_CHANGE_CHANNEL})");
    loop {
        // `recv` errors when the connection drops; bubble up so `spawn_loop` reconnects.
        let notification = listener.recv().await?;
        match notification.channel() {
            RELEASE_CHANNEL => handle_release(store, notification.payload()),
            LIMIT_CHANGE_CHANNEL => handle_limit_change(store, notification.payload()),
            other => debug!("Ignoring NOTIFY on unexpected channel {other}"),
        }
    }
}

fn handle_release(store: &Store, payload: &str) {
    match serde_json::from_str::<ReleasePayload>(payload) {
        Ok(p) => store.apply_release(&BookingDelta {
            show_id: p.show,
            alloc_id: p.alloc,
            folder_id: p.folder,
            job_id: p.job,
            core_delta: p.cores,
            gpu_delta: p.gpus,
            slot_delta: p.slots,
        }),
        Err(err) => warn!("Dropping malformed acct_release payload ({err}): {payload}"),
    }
}

fn handle_limit_change(store: &Store, payload: &str) {
    let parsed = match serde_json::from_str::<LimitChangePayload>(payload) {
        Ok(p) => p,
        Err(err) => {
            warn!("Dropping malformed acct_limit_change payload ({err}): {payload}");
            return;
        }
    };
    for change in limit_changes(parsed) {
        store.apply_limit_change(&change);
    }
}

/// Expand a payload into the concrete cap changes it carries (a folder/job message may
/// set cores, gpus, or both).
fn limit_changes(p: LimitChangePayload) -> Vec<LimitChange> {
    match p {
        LimitChangePayload::Sub {
            show,
            alloc,
            burst,
            max_slots,
        } => burst
            .map(|b| LimitChange::SubBurst {
                show_id: show,
                alloc_id: alloc,
                burst: b,
            })
            .into_iter()
            .chain(max_slots.map(|s| LimitChange::SubMaxSlots {
                show_id: show,
                alloc_id: alloc,
                max_slots: s,
            }))
            .collect(),
        LimitChangePayload::Folder {
            id,
            max_cores,
            max_gpus,
            max_slots,
        } => max_cores
            .map(|c| LimitChange::FolderMaxCores {
                folder_id: id,
                max_cores: c,
            })
            .into_iter()
            .chain(max_gpus.map(|g| LimitChange::FolderMaxGpus {
                folder_id: id,
                max_gpus: g,
            }))
            .chain(max_slots.map(|s| LimitChange::FolderMaxSlots {
                folder_id: id,
                max_slots: s,
            }))
            .collect(),
        LimitChangePayload::Job {
            id,
            max_cores,
            max_gpus,
            max_slots,
        } => max_cores
            .map(|c| LimitChange::JobMaxCores {
                job_id: id,
                max_cores: c,
            })
            .into_iter()
            .chain(max_gpus.map(|g| LimitChange::JobMaxGpus {
                job_id: id,
                max_gpus: g,
            }))
            .chain(max_slots.map(|s| LimitChange::JobMaxSlots {
                job_id: id,
                max_slots: s,
            }))
            .collect(),
    }
}

// Surface a parse failure loudly in tests if the wire contract drifts from Cuebot's
// `AccountingNotifier`.
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_release_payload() {
        let json = r#"{"show":"00000000-0000-0000-0000-000000000001",
            "alloc":"00000000-0000-0000-0000-000000000002",
            "folder":"00000000-0000-0000-0000-000000000003",
            "job":"00000000-0000-0000-0000-000000000004",
            "layer":"00000000-0000-0000-0000-000000000005",
            "dept":"00000000-0000-0000-0000-000000000006",
            "cores":-10,"gpus":-1}"#;
        let p: ReleasePayload = serde_json::from_str(json).expect("release payload parses");
        assert_eq!(p.cores, -10);
        assert_eq!(p.gpus, -1);
        assert_eq!(p.job, Uuid::parse_str("00000000-0000-0000-0000-000000000004").unwrap());
    }

    #[test]
    fn parses_sub_burst_change() {
        let json = r#"{"vertex":"sub","show":"00000000-0000-0000-0000-000000000001",
            "alloc":"00000000-0000-0000-0000-000000000002","burst":200}"#;
        let changes = limit_changes(serde_json::from_str(json).unwrap());
        assert!(matches!(changes[..], [LimitChange::SubBurst { burst: 200, .. }]));
    }

    #[test]
    fn parses_job_max_cores_change_preserving_unlimited() {
        let json = r#"{"vertex":"job","id":"00000000-0000-0000-0000-000000000004","max_cores":-1}"#;
        let changes = limit_changes(serde_json::from_str(json).unwrap());
        assert!(matches!(
            changes[..],
            [LimitChange::JobMaxCores { max_cores: -1, .. }]
        ));
    }

    #[test]
    fn folder_change_with_both_fields_expands_to_two() {
        let json = r#"{"vertex":"folder","id":"00000000-0000-0000-0000-000000000003",
            "max_cores":20,"max_gpus":4}"#;
        let changes = limit_changes(serde_json::from_str(json).unwrap());
        assert_eq!(changes.len(), 2);
    }
}
