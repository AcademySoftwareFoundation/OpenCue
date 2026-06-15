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

// TODO: replace single-node URL with Sentinel/Cluster topology when Redis HA lands (design §5).
// TODO: detect Redis FLUSHALL/restart and re-trigger bootstrap reseed without scheduler restart
//       (design §4.3 row 5). Today, on connection failure the booking returns Unavailable and
//       the dispatcher idles; if Redis is restarted empty, the next booking will populate
//       acct:* hashes from zero - limit fields will be missing until the next limit reseed (5 min).

use redis::{aio::ConnectionManager, AsyncCommands, Script};

use crate::accounting::booking_delta::{BookingDelta, SEQ_KEY};
use crate::accounting::error::AccountingError;
use crate::accounting::lua::{BOOK_OR_FORCE, RESEED_CAS};
use crate::config::RedisConfig;

/// One value to write during a reseed: HSET `key` `field` `value`.
#[derive(Debug, Clone)]
pub struct ReseedOp {
    pub key: String,
    pub field: &'static str,
    pub value: i64,
}

/// Outcome of a `BOOK_OR_FORCE` Lua call.
pub enum BookOutcome {
    /// Booking accepted; `acct:seq` was bumped to `new_seq` (currently consumed for
    /// diagnostics by callers that want to log it; the dispatcher path ignores it).
    Applied {
        #[allow(dead_code)]
        new_seq: i64,
    },
    /// Booking rejected because a hard cap would be exceeded.
    LimitExceeded {
        table: String,
        current: i64,
        limit: i64,
    },
}

/// Whether to enforce subscription/folder/job caps in the booking Lua.
#[derive(Debug, Clone, Copy)]
pub enum BookMode {
    /// Hot-path booking: enforce caps; reject the booking if any would be exceeded.
    Enforce,
    /// Force mode: bypass caps. Used for compensation rollbacks (negated deltas) and
    /// any other path that must not be rejected by a stale cap.
    Force,
}

impl BookMode {
    fn as_arg(self) -> &'static str {
        match self {
            BookMode::Enforce => "0",
            BookMode::Force => "1",
        }
    }
}

/// Low-level Redis client for accounting. Holds two `redis::Script` handles which manage
/// their own SHA cache and reload on `NOSCRIPT` automatically (see `Script::invoke_async`).
#[derive(Clone)]
pub struct RedisAccounting {
    conn: ConnectionManager,
    book_script: Script,
    reseed_script: Script,
}

impl RedisAccounting {
    pub async fn connect(cfg: &RedisConfig) -> Result<Self, AccountingError> {
        let client = redis::Client::open(cfg.url())
            .map_err(|e| AccountingError::Unavailable(format!("invalid redis url: {e}")))?;
        let conn = ConnectionManager::new(client).await?;
        Ok(Self {
            conn,
            book_script: Script::new(BOOK_OR_FORCE),
            reseed_script: Script::new(RESEED_CAS),
        })
    }

    /// Runs the booking Lua script over the five hashes referenced by `delta`.
    pub async fn book(
        &self,
        delta: &BookingDelta,
        mode: BookMode,
    ) -> Result<BookOutcome, AccountingError> {
        let mut conn = self.conn.clone();
        let value: redis::Value = self
            .book_script
            .key(delta.sub_key())
            .key(delta.folder_key())
            .key(delta.job_key())
            .key(delta.layer_key())
            .key(delta.point_key())
            .key(SEQ_KEY)
            .arg(delta.core_delta.to_string())
            .arg(delta.gpu_delta.to_string())
            .arg(mode.as_arg())
            .invoke_async(&mut conn)
            .await?;
        parse_book_outcome(value)
    }

    /// Issues a CAS reseed. `seq_before` is the snapshot caller observed; `ops` is the
    /// list of HSETs to apply atomically. Returns `Ok(true)` on success, `Ok(false)` on
    /// CAS miss (caller should resnapshot and retry).
    pub async fn reseed_cas(
        &self,
        seq_before: i64,
        ops: &[ReseedOp],
    ) -> Result<bool, AccountingError> {
        let mut conn = self.conn.clone();
        let mut invocation = self.reseed_script.prepare_invoke();
        invocation.key(SEQ_KEY);
        invocation.arg(seq_before.to_string());
        invocation.arg(ops.len().to_string());
        for op in ops {
            invocation.arg(op.key.as_str());
            invocation.arg(op.field);
            invocation.arg(op.value.to_string());
        }
        let result: i64 = invocation.invoke_async(&mut conn).await?;
        Ok(result == 1)
    }

    /// Reads the current `acct:seq` value (defaults to 0 if missing).
    pub async fn get_seq(&self) -> Result<i64, AccountingError> {
        let mut conn = self.conn.clone();
        let v: Option<i64> = conn.get(SEQ_KEY).await?;
        Ok(v.unwrap_or(0))
    }

    /// Reads the subscription hash's booked cores + burst in one round-trip from
    /// `acct:sub:{show_id}:{alloc_id}` (fields `int_cores`, `burst`, both in
    /// cores — the centicore→core conversion happens once at the reseed write
    /// boundary, see the `lua.rs` unit invariant). Missing keys/fields are
    /// treated as `(0, 0)`. Non-authoritative:
    /// the dispatcher's Lua `BOOK_OR_FORCE` call remains the source of truth for
    /// the booking decision; this is a snapshot suitable for optimistic pre-filters
    /// and scoring inputs.
    pub async fn read_sub_counters(
        &self,
        show_id: uuid::Uuid,
        alloc_id: uuid::Uuid,
    ) -> Result<(i64, i64), AccountingError> {
        let mut conn = self.conn.clone();
        let key = format!("acct:sub:{}:{}", show_id, alloc_id);
        let values: Vec<Option<i64>> = conn.hget(&key, &["int_cores", "burst"]).await?;
        let booked = values.first().copied().flatten().unwrap_or(0);
        let burst = values.get(1).copied().flatten().unwrap_or(0);
        Ok((booked, burst))
    }

    /// Reads `acct:job:{job_id}` `int_cores` (live booked cores, in cores — see
    /// the `lua.rs` unit invariant; Redis accounting counters are never stored
    /// in centicores). Returns 0 when the key/field is missing. Used by the E-PVM placement
    /// snapshot in `MatchingService::process_layer` (design Branch 2a).
    pub async fn read_job_cores_in_use(
        &self,
        job_id: uuid::Uuid,
    ) -> Result<i64, AccountingError> {
        let mut conn = self.conn.clone();
        let key = format!("acct:job:{}", job_id);
        let v: Option<i64> = conn.hget(&key, "int_cores").await?;
        Ok(v.unwrap_or(0))
    }
}

/// Parses the raw `redis::Value` returned by the `BOOK_OR_FORCE` Lua script (see
/// `accounting::lua`) into a typed `BookOutcome`.
///
/// # Wire format
///
/// Lua's `return {...}` produces a multi-bulk reply, which `redis-rs` decodes as
/// `Value::Array`. Two shapes are possible:
///
/// ```text
/// Applied (status=1):       Array[Int(1), Int(new_seq)]
/// LimitExceeded (status=0): Array[Int(0), Str(table_name), Int(current), Int(limit)]
/// ```
///
/// `redis::Value` element types:
/// - `Int(i64)`     — Lua numbers (`return {1, ...}`, `INCR`-returned counters).
/// - `BulkString(Vec<u8>)` on RESP2 / `SimpleString(String)` on RESP3 — Lua string
///   literals (`"subscription"`, `"folder"`, `"job"`). Both forms must be accepted
///   because the connection's protocol version is not pinned here.
///
/// # Error handling
///
/// Anything outside the two shapes above means the Lua source and this parser are
/// out of sync — a programmer error, not a transient infra fault. We surface it as
/// `AccountingError::Unexpected`, which the dispatcher routes to the new
/// `DispatchVirtualProcError::AccountingUnexpected` arm so ops can alert on it
/// separately from `Unavailable`. Each match arm carries the position it failed at
/// (status / new_seq / table / current / limit) so a `{other:?}` log line is enough
/// to localize the protocol drift.
fn parse_book_outcome(value: redis::Value) -> Result<BookOutcome, AccountingError> {
    use redis::Value;

    // Top-level: must be the multi-bulk reply produced by Lua's `return {...}`.
    let array = match value {
        Value::Array(items) => items,
        other => {
            return Err(AccountingError::Unexpected(format!(
                "expected Lua array, got {other:?}"
            )))
        }
    };

    // array[0] = status discriminator. 1 = booking applied, 0 = cap rejected.
    let status = match array.first() {
        Some(Value::Int(n)) => *n,
        other => {
            return Err(AccountingError::Unexpected(format!(
                "expected int status as first element, got {other:?}"
            )))
        }
    };

    if status == 1 {
        // Applied shape: [Int(1), Int(new_seq)]. new_seq is `INCR acct:seq`.
        let new_seq = match array.get(1) {
            Some(Value::Int(n)) => *n,
            other => {
                return Err(AccountingError::Unexpected(format!(
                    "expected int new_seq, got {other:?}"
                )))
            }
        };
        Ok(BookOutcome::Applied { new_seq })
    } else {
        // LimitExceeded shape: [Int(0), Str(table), Int(current), Int(limit)].
        // `table` is one of "subscription" / "folder" / "job" / "folder_gpus" /
        // "job_gpus" — see lua.rs cap checks. Accept both BulkString (RESP2) and
        // SimpleString (RESP3) since either is valid for a Lua string literal
        // across redis-rs versions.
        let table = match array.get(1) {
            Some(Value::BulkString(s)) => String::from_utf8_lossy(s).into_owned(),
            Some(Value::SimpleString(s)) => s.clone(),
            other => {
                return Err(AccountingError::Unexpected(format!(
                    "expected table name string, got {other:?}"
                )))
            }
        };
        // `current` is the pre-increment counter value the Lua observed via HGET;
        // useful for log lines / `LimitExceeded` error messages so operators see
        // exactly where the cap fired.
        let current = match array.get(2) {
            Some(Value::Int(n)) => *n,
            other => {
                return Err(AccountingError::Unexpected(format!(
                    "expected int current, got {other:?}"
                )))
            }
        };
        // `limit` is the cap that was exceeded (subscription burst, folder/job
        // int_max_cores, or folder/job int_max_gpus). Same source: HGET inside
        // the Lua.
        let limit = match array.get(3) {
            Some(Value::Int(n)) => *n,
            other => {
                return Err(AccountingError::Unexpected(format!(
                    "expected int limit, got {other:?}"
                )))
            }
        };
        Ok(BookOutcome::LimitExceeded {
            table,
            current,
            limit,
        })
    }
}
