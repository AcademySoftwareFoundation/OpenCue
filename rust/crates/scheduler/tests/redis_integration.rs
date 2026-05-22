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

//! Integration tests for the Redis-backed accounting layer. Spawns a real Redis 7
//! container per test via `testcontainers`. Exercises the Lua scripts directly
//! against a live Redis to ensure behavior matches the design contracts in §2.3/§2.4.
//!
//! Gated behind `--features redis-tests` (requires Docker daemon).

#![cfg(feature = "redis-tests")]

use std::time::Duration;

use redis::aio::ConnectionManager;
use redis::{AsyncCommands, Client, Script};
use scheduler::accounting::booking_delta::{BookingDelta, SEQ_KEY};
use scheduler::accounting::lua::{BOOK_OR_FORCE, RESEED_CAS};
use scheduler::accounting::redis_client::ReseedOp;
use testcontainers::runners::AsyncRunner;
use testcontainers::ContainerAsync;
use testcontainers_modules::redis::Redis;
use tokio::time::sleep;
use uuid::Uuid;

struct RedisHarness {
    _container: ContainerAsync<Redis>,
    conn: ConnectionManager,
    book_script: Script,
    reseed_script: Script,
}

impl RedisHarness {
    async fn new() -> Self {
        let container = Redis::default().start().await.expect("start redis");
        let port = container
            .get_host_port_ipv4(6379)
            .await
            .expect("redis port");
        let url = format!("redis://127.0.0.1:{port}/");
        let client = Client::open(url).expect("open client");
        let conn = ConnectionManager::new(client).await.expect("manager");
        RedisHarness {
            _container: container,
            conn,
            book_script: Script::new(BOOK_OR_FORCE),
            reseed_script: Script::new(RESEED_CAS),
        }
    }

    fn delta(show: Uuid, alloc: Uuid, cores: i64, gpus: i32) -> BookingDelta {
        BookingDelta {
            show_id: show,
            alloc_id: alloc,
            folder_id: Uuid::nil(),
            job_id: Uuid::nil(),
            layer_id: Uuid::nil(),
            dept_id: Uuid::nil(),
            core_delta: cores,
            gpu_delta: gpus,
        }
    }

    async fn book(&self, delta: &BookingDelta, force: &str) -> redis::Value {
        let mut conn = self.conn.clone();
        self.book_script
            .key(delta.sub_key())
            .key(delta.folder_key())
            .key(delta.job_key())
            .key(delta.layer_key())
            .key(delta.point_key())
            .key(SEQ_KEY)
            .arg(delta.core_delta.to_string())
            .arg(delta.gpu_delta.to_string())
            .arg(force)
            .invoke_async(&mut conn)
            .await
            .expect("EVALSHA")
    }

    async fn reseed(&self, seq_before: i64, ops: &[ReseedOp]) -> i64 {
        let mut conn = self.conn.clone();
        let mut inv = self.reseed_script.prepare_invoke();
        inv.key(SEQ_KEY)
            .arg(seq_before.to_string())
            .arg(ops.len().to_string());
        for op in ops {
            inv.arg(op.key.as_str())
                .arg(op.field)
                .arg(op.value.to_string());
        }
        inv.invoke_async(&mut conn).await.expect("RESEED_CAS")
    }

    async fn hget_i64(&self, key: &str, field: &str) -> Option<i64> {
        let mut conn = self.conn.clone();
        conn.hget(key, field).await.expect("HGET")
    }

    async fn get_seq(&self) -> i64 {
        let mut conn = self.conn.clone();
        let v: Option<i64> = conn.get(SEQ_KEY).await.expect("GET seq");
        v.unwrap_or(0)
    }

    async fn set_burst(&self, key: &str, burst: i64) {
        let mut conn = self.conn.clone();
        let _: () = conn.hset(key, "burst", burst).await.expect("HSET burst");
    }

    async fn set_field(&self, key: &str, field: &str, value: i64) {
        let mut conn = self.conn.clone();
        let _: () = conn.hset(key, field, value).await.expect("HSET field");
    }
}

fn ok_seq(value: &redis::Value) -> Option<i64> {
    if let redis::Value::Array(items) = value {
        if let (Some(redis::Value::Int(1)), Some(redis::Value::Int(seq))) =
            (items.first(), items.get(1))
        {
            return Some(*seq);
        }
    }
    None
}

fn limit_exceeded(value: &redis::Value) -> Option<(String, i64, i64)> {
    if let redis::Value::Array(items) = value {
        if matches!(items.first(), Some(redis::Value::Int(0))) {
            let table = match items.get(1)? {
                redis::Value::BulkString(s) => String::from_utf8_lossy(s).into_owned(),
                redis::Value::SimpleString(s) => s.clone(),
                _ => return None,
            };
            let current = match items.get(2)? {
                redis::Value::Int(n) => *n,
                _ => return None,
            };
            let limit = match items.get(3)? {
                redis::Value::Int(n) => *n,
                _ => return None,
            };
            return Some((table, current, limit));
        }
    }
    None
}

#[tokio::test]
async fn book_happy_path_increments_counters_and_bumps_seq() {
    // The Lua enforces `cur + delta > burst` unconditionally, matching Cuebot's
    // semantics - `burst = 0` (the schema default) means "no bookings allowed".
    // Pre-seed burst so this test models the production flow where the bootstrap
    // limit reseed has already populated the subscription cap.
    let h = RedisHarness::new().await;
    let show = Uuid::new_v4();
    let alloc = Uuid::new_v4();
    let delta = RedisHarness::delta(show, alloc, 100, 1);
    h.set_burst(&delta.sub_key(), 1000).await;

    let result = h.book(&delta, "0").await;
    assert_eq!(
        ok_seq(&result),
        Some(1),
        "expected {{1, 1}}, got {result:?}"
    );

    assert_eq!(h.hget_i64(&delta.sub_key(), "int_cores").await, Some(100));
    assert_eq!(h.hget_i64(&delta.folder_key(), "int_gpus").await, Some(1));
    assert_eq!(h.hget_i64(&delta.job_key(), "int_cores").await, Some(100));
    assert_eq!(h.hget_i64(&delta.layer_key(), "int_cores").await, Some(100));
    assert_eq!(h.hget_i64(&delta.point_key(), "int_cores").await, Some(100));
    assert_eq!(h.get_seq().await, 1);
}

#[tokio::test]
async fn book_rejects_when_burst_is_zero() {
    // Matches Cuebot's behavior: a subscription with no burst configured (or
    // pre-bootstrap Redis state) rejects every booking. Verifies we no longer
    // silently widen permissions for unconfigured subscriptions.
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 1, 0);

    let r = h.book(&delta, "0").await;
    let (table, current, limit) =
        limit_exceeded(&r).unwrap_or_else(|| panic!("expected limit-exceeded, got {r:?}"));
    assert_eq!(table, "subscription");
    assert_eq!(current, 0);
    assert_eq!(limit, 0);

    // No counters were written.
    assert_eq!(h.hget_i64(&delta.sub_key(), "int_cores").await, None);
    assert_eq!(h.get_seq().await, 0);
}

#[tokio::test]
async fn force_mode_books_even_when_burst_is_zero() {
    // Force-mode (rollback path) must succeed regardless of burst state, since the
    // caller has already committed the booking elsewhere and we need to undo it.
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 50, 0);

    let result = h.book(&delta, "1").await;
    assert_eq!(ok_seq(&result), Some(1));
    assert_eq!(h.hget_i64(&delta.sub_key(), "int_cores").await, Some(50));
}

#[tokio::test]
async fn book_over_burst_returns_structured_limit_exceeded() {
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 150, 0);

    // Pre-seed subscription burst so the cap is non-zero (a 0/missing burst means
    // "unlimited" per the Lua's `burst > 0 and ...` gate).
    h.set_burst(&delta.sub_key(), 200).await;

    // First booking puts us at 100 - under the 200 cap.
    let first_delta = RedisHarness::delta(delta.show_id, delta.alloc_id, 100, 0);
    let r1 = h.book(&first_delta, "0").await;
    assert_eq!(ok_seq(&r1), Some(1));

    // Second booking of 150 would push us to 250 - over the 200 cap.
    let r2 = h.book(&delta, "0").await;
    let (table, current, limit) =
        limit_exceeded(&r2).unwrap_or_else(|| panic!("expected limit-exceeded, got {r2:?}"));
    assert_eq!(table, "subscription");
    assert_eq!(current, 100);
    assert_eq!(limit, 200);

    // Counters should be unchanged after a rejected booking.
    assert_eq!(h.hget_i64(&delta.sub_key(), "int_cores").await, Some(100));
    assert_eq!(h.get_seq().await, 1);
}

#[tokio::test]
async fn force_mode_bypasses_limit_check() {
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 500, 0);
    h.set_burst(&delta.sub_key(), 100).await;

    // 500 would be over the 100 burst - but force=1 bypasses the check.
    let result = h.book(&delta, "1").await;
    assert_eq!(ok_seq(&result), Some(1));
    assert_eq!(h.hget_i64(&delta.sub_key(), "int_cores").await, Some(500));
}

#[tokio::test]
async fn reseed_cas_applies_when_seq_unchanged() {
    let h = RedisHarness::new().await;
    let key = format!("acct:sub:{}:{}", Uuid::new_v4(), Uuid::new_v4());

    let seq_before = h.get_seq().await;
    let ops = vec![
        ReseedOp {
            key: key.clone(),
            field: "int_cores",
            value: 42,
        },
        ReseedOp {
            key: key.clone(),
            field: "burst",
            value: 200,
        },
    ];
    let applied = h.reseed(seq_before, &ops).await;
    assert_eq!(applied, 1, "CAS should succeed when seq is unchanged");
    assert_eq!(h.hget_i64(&key, "int_cores").await, Some(42));
    assert_eq!(h.hget_i64(&key, "burst").await, Some(200));

    // RESEED_CAS must NOT bump acct:seq (it's reconciliation, not mutation).
    assert_eq!(h.get_seq().await, seq_before);
}

#[tokio::test]
async fn reseed_cas_misses_when_booking_bumped_seq_concurrently() {
    let h = RedisHarness::new().await;
    let show = Uuid::new_v4();
    let alloc = Uuid::new_v4();
    let delta = RedisHarness::delta(show, alloc, 50, 0);
    h.set_burst(&delta.sub_key(), 1000).await;

    let seq_before = h.get_seq().await;

    // Concurrent booking bumps `acct:seq` between the caller's GET and the CAS attempt.
    let _ = h.book(&delta, "0").await;
    assert!(h.get_seq().await > seq_before);

    // CAS attempt with the stale seq_before should return 0 (miss).
    let ops = vec![ReseedOp {
        key: delta.sub_key(),
        field: "int_cores",
        value: 999,
    }];
    let applied = h.reseed(seq_before, &ops).await;
    assert_eq!(applied, 0, "CAS should miss with stale seq_before");

    // The hot-path-written value must survive the failed reseed (i.e. no clobber).
    assert_eq!(h.hget_i64(&delta.sub_key(), "int_cores").await, Some(50));
}

#[tokio::test]
async fn cas_guard_prevents_silent_loss_under_concurrent_booking() {
    // Mirrors the trace in design §2.4: reseed reads SUM=50, booking runs (counter→60,
    // seq bumped), reseed CAS detects miss and retries; the booking is preserved.
    let h = RedisHarness::new().await;
    let show = Uuid::new_v4();
    let alloc = Uuid::new_v4();

    // Initial state: counter at 50, burst at 1000 (so the booking is under cap), seq=0.
    let key = format!("acct:sub:{}:{}", show, alloc);
    {
        let mut conn = h.conn.clone();
        let _: () = conn.hset(&key, "int_cores", 50).await.unwrap();
    }
    h.set_burst(&key, 1000).await;

    // (t1) Reseed reads seq_before.
    let seq_before = h.get_seq().await;

    // (t2) Concurrent booking bumps the counter to 60 and increments seq.
    let booking = RedisHarness::delta(show, alloc, 10, 0);
    // The booking writes to its own (sub, folder, job, layer, point) hashes; the sub key
    // is the same one our reseed will target.
    let _ = h.book(&booking, "0").await;
    let post_book = h.hget_i64(&key, "int_cores").await;
    assert_eq!(post_book, Some(60), "booking applied: 50 + 10");

    // (t3) Reseed tries to CAS-write 50 (its in-memory snapshot) - must miss.
    let ops = vec![ReseedOp {
        key: key.clone(),
        field: "int_cores",
        value: 50,
    }];
    let applied = h.reseed(seq_before, &ops).await;
    assert_eq!(applied, 0, "reseed must miss to protect concurrent booking");

    // The booking is preserved - no silent loss.
    assert_eq!(h.hget_i64(&key, "int_cores").await, Some(60));

    // (t4) Reseed re-snapshots: seq_before = current seq, recompute ops with 60.
    let seq_before_retry = h.get_seq().await;
    let ops_retry = vec![ReseedOp {
        key: key.clone(),
        field: "int_cores",
        value: 60,
    }];
    let applied_retry = h.reseed(seq_before_retry, &ops_retry).await;
    assert_eq!(applied_retry, 1, "retry succeeds with fresh snapshot");
    assert_eq!(h.hget_i64(&key, "int_cores").await, Some(60));
}

#[tokio::test]
async fn book_over_job_gpu_max_returns_structured_limit_exceeded() {
    // Mirrors the Java `DispatchQuery.FIND_JOBS_BY_SHOW_PRIORITY_MODE` predicate
    // `job_resource.int_gpus + layer.int_gpus_min < job_resource.int_max_gpus`
    // that lived in PG before accounting moved to Redis.
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 100, 3);
    h.set_burst(&delta.sub_key(), 10_000).await;
    h.set_field(&delta.job_key(), "int_max_gpus", 4).await;

    // First booking puts the job at 2 GPUs - under the 4 cap.
    let first = RedisHarness::delta(delta.show_id, delta.alloc_id, 100, 2);
    let r1 = h.book(&first, "0").await;
    assert_eq!(ok_seq(&r1), Some(1));

    // Second booking would push GPUs to 5 - over the 4 cap.
    let r2 = h.book(&delta, "0").await;
    let (table, current, limit) =
        limit_exceeded(&r2).unwrap_or_else(|| panic!("expected limit-exceeded, got {r2:?}"));
    assert_eq!(table, "job_gpus");
    assert_eq!(current, 2);
    assert_eq!(limit, 4);

    // Counters should be unchanged after a rejected booking.
    assert_eq!(h.hget_i64(&delta.job_key(), "int_gpus").await, Some(2));
}

#[tokio::test]
async fn book_over_folder_gpu_max_returns_structured_limit_exceeded() {
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 100, 2);
    h.set_burst(&delta.sub_key(), 10_000).await;
    h.set_field(&delta.folder_key(), "int_max_gpus", 3).await;

    // First booking puts the folder at 2 GPUs - under the 3 cap.
    let first = RedisHarness::delta(delta.show_id, delta.alloc_id, 100, 2);
    let r1 = h.book(&first, "0").await;
    assert_eq!(ok_seq(&r1), Some(1));

    // Second booking would push folder GPUs to 4 - over the 3 cap.
    let r2 = h.book(&delta, "0").await;
    let (table, current, limit) =
        limit_exceeded(&r2).unwrap_or_else(|| panic!("expected limit-exceeded, got {r2:?}"));
    assert_eq!(table, "folder_gpus");
    assert_eq!(current, 2);
    assert_eq!(limit, 3);
}

#[tokio::test]
async fn gpu_cap_unlimited_when_negative() {
    // Cuebot's `-1` sentinel = "unlimited" for `int_max_gpus`. The `> 0` guard in
    // the Lua must let bookings through when the cap is unset or -1.
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 100, 99);
    h.set_burst(&delta.sub_key(), 10_000).await;
    h.set_field(&delta.job_key(), "int_max_gpus", -1).await;
    h.set_field(&delta.folder_key(), "int_max_gpus", -1).await;

    let r = h.book(&delta, "0").await;
    assert!(
        ok_seq(&r).is_some(),
        "expected booking accepted with -1 cap, got {r:?}"
    );
    assert_eq!(h.hget_i64(&delta.job_key(), "int_gpus").await, Some(99));
}

#[tokio::test]
async fn gpu_cap_not_checked_when_delta_is_zero() {
    // Cores-only bookings should not be rejected by a tight GPU cap (no GPU
    // demand means there's nothing to check).
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 100, 0);
    h.set_burst(&delta.sub_key(), 10_000).await;
    h.set_field(&delta.job_key(), "int_max_gpus", 1).await;
    h.set_field(&delta.job_key(), "int_gpus", 1).await; // already at the cap

    let r = h.book(&delta, "0").await;
    assert!(
        ok_seq(&r).is_some(),
        "expected booking accepted with gpu_delta=0, got {r:?}"
    );
}

#[tokio::test]
async fn force_mode_bypasses_gpu_cap() {
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 100, 5);
    h.set_burst(&delta.sub_key(), 10_000).await;
    h.set_field(&delta.job_key(), "int_max_gpus", 1).await;

    let result = h.book(&delta, "1").await;
    assert_eq!(ok_seq(&result), Some(1));
    assert_eq!(h.hget_i64(&delta.job_key(), "int_gpus").await, Some(5));
}

#[tokio::test]
async fn force_with_negative_delta_decrements() {
    // Exercises the compensation-rollback path: a successful booking followed by a
    // force-rollback with negated deltas should net to zero.
    let h = RedisHarness::new().await;
    let delta = RedisHarness::delta(Uuid::new_v4(), Uuid::new_v4(), 250, 2);
    h.set_burst(&delta.sub_key(), 1000).await;

    let _ = h.book(&delta, "0").await;
    assert_eq!(h.hget_i64(&delta.sub_key(), "int_cores").await, Some(250));
    assert_eq!(h.hget_i64(&delta.folder_key(), "int_gpus").await, Some(2));

    // Rollback with negated delta in force mode.
    let rollback = BookingDelta {
        core_delta: -delta.core_delta,
        gpu_delta: -delta.gpu_delta,
        ..delta.clone()
    };
    let result = h.book(&rollback, "1").await;
    assert!(ok_seq(&result).is_some(), "force rollback applied");
    assert_eq!(h.hget_i64(&delta.sub_key(), "int_cores").await, Some(0));
    assert_eq!(h.hget_i64(&delta.folder_key(), "int_gpus").await, Some(0));

    // Sanity: brief wait to ensure no race-condition log spam.
    sleep(Duration::from_millis(10)).await;
}
