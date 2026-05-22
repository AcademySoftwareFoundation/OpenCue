---
title: "Redis-Backed Accounting Reference"
nav_order: 101
parent: Reference
layout: default
linkTitle: "Redis-Backed Accounting"
date: 2026-05-22
description: >
  Technical reference for the Redis-backed accounting subsystem shared by Cuebot and the Rust scheduler
---

# Redis-Backed Accounting Reference

### How Cuebot and the Rust scheduler coordinate per-show resource accounting through Redis

---

## Overview

The accounting subsystem tracks how much of each resource pool (subscription,
folder, job, layer, department point) is currently booked. Every dispatch
decision the [Rust scheduler](/docs/developer-guide/scheduler/) makes is gated
on these counters - if a job is already at its `int_max_cores`, the scheduler
must not book another frame against it.

Historically these counters lived only in PostgreSQL: Cuebot's dispatcher
updated five accounting tables transactionally on every booking and every
release. As the Rust scheduler took over dispatch, two problems emerged:

1. **Postgres lock contention.** The scheduler's hot path was hammering the
   same accounting rows Cuebot's `HostReportHandler` writes to. Lock waits on
   `subscription`, `folder_resource`, and `job_resource` started limiting
   throughput.
2. **Horizontal scaling.** An earlier in-process accounting cache (a
   `HashMap<K, V>` inside the scheduler) cannot be shared across N scheduler
   instances. Any path to multi-scheduler deployment needs a shared store.

This subsystem replaces both with a Redis-backed accounting layer that both
Cuebot and the Rust scheduler write through on the hot path. PostgreSQL
remains the durable system of record; Redis is the live operational view.

Source: `rust/crates/scheduler/src/accounting/` and
`cuebot/src/main/java/com/imageworks/spcue/service/AccountingRedisPublisher.java`.

---

## Source-of-truth model

This is the load-bearing design choice; everything else falls out of it.

| Component | Hot path | Slow path |
|---|---|---|
| Rust scheduler (booking) | Atomic Lua against Redis (`check + 5×HINCRBY + INCR acct:seq`), then `INSERT proc` in PG transactionally | Periodic recompute (every 2 min) writes PG accounting tables for scheduler-managed shows from `SUM(proc)` |
| Cuebot release path (`ProcDaoJdbc.unbookProc`) | For scheduler-managed shows: only `DELETE proc` transactionally, then `afterCommit` publishes the release delta to Redis. For Cuebot-managed shows: unchanged transactional UPDATEs against accounting tables | - |
| Cuebot admin paths (size/burst/min/max changes) | Unchanged transactional UPDATEs against accounting tables; **no Redis publish** | - |
| CueGUI | Reads PG accounting tables (unchanged) | - |

Three properties hold:

- **`proc` is canonical for bookings.** Both sides write `proc` transactionally.
  Anything else can be reconstructed from `SELECT SUM(int_cores_reserved) FROM
  proc GROUP BY pk_show, pk_alloc`.
- **PG accounting tables are derived.** For scheduler-managed shows they are
  refreshed by the recompute loop. For Cuebot-managed shows they are written
  transactionally by Cuebot's dispatcher (unchanged from before).
- **Redis is the live operational view.** Both sides feed it on the hot path;
  it is rebuilt from `proc` and from the PG accounting tables on a schedule.

### Why a hybrid, not Redis-only or PG-only

Three alternatives were considered and rejected:

- **Redis as a derived index of Postgres** (Cuebot writes PG transactionally;
  `afterCommit` copies the delta to Redis; the scheduler reads Redis on the hot
  path but writes PG transactionally). This is conservative and safe under a
  Redis outage, but it leaves the scheduler's hot path holding PG locks - which
  is most of the lock-contention pressure we were trying to relieve.
- **Both sides write Redis only; an async drainer persists to Postgres.**
  Maximally decoupled, but Redis loss becomes data loss unless AOF and
  replication are bulletproof, and the drainer becomes a new SPOF. Too far
  ahead of where we trust Redis in this stack today.
- **Cuebot writes both Postgres and Redis inline in the same code path with no
  transaction coordination.** Partial failures silently diverge with no recovery
  story. Anti-pattern, rejected outright.

The chosen design sits between the first two: Redis is the live operational
view both sides write through; Postgres is durably correct via Cuebot's
transactional writes (for Cuebot-managed shows) or the scheduler's periodic
recompute (for scheduler-managed shows).

---

## Show ownership: the per-show partition

Within a single show, exactly one of Cuebot or Rust owns the accounting write
path. There is no double-write and no per-key arbitration. The flag lives on
the `show` table:

```sql
ALTER TABLE show ADD COLUMN b_scheduler_managed BOOLEAN NOT NULL DEFAULT false;
```

- `b_scheduler_managed = false` (default): the show is Cuebot-managed.
  Cuebot's dispatcher books and releases against PG accounting tables
  transactionally, exactly as before. Redis is not consulted.
- `b_scheduler_managed = true`: the show is scheduler-managed. The Rust
  scheduler books against Redis on the hot path; Cuebot's release path only
  deletes the `proc` row and publishes the release delta to Redis via
  `afterCommit`. PG accounting tables for this show are refreshed by the
  scheduler's 2-min recompute loop.

The flag is **per-show, not per-allocation.** A show is either
scheduler-managed or it isn't; mixed-mode shows would force per-row arbitration
in both Cuebot and the scheduler, and the simplification was worth more than
the flexibility.

The flag also replaces the older `dispatcher.exclusion_list` and
`dispatcher.scheduler_manages_resources` properties in `opencue.properties`,
both removed. Migration: any show previously named in `exclusion_list` must be
flipped via cueadmin (see [Operator workflow](#operator-workflow) below).

### Looking up the flag

Cuebot's `ProcDaoJdbc.unbookProc` checks the flag on every release. Hitting PG
on every release would defeat the purpose, so `ShowDao` caches the flag with a
~30 s TTL. After a `setSchedulerManaged` toggle, the new value is visible
across the cluster within ~30 s. The brief stale window is acceptable -
transient drift heals via the next recompute (see [Failure modes](#failure-modes-and-drift-bounds)).

---

## Redis schema

Six key namespaces, one per accounting table plus a global sequence counter:

| Key | Type | Fields |
|---|---|---|
| `acct:sub:{show_id}:{alloc_id}` | HASH | `size, burst, int_cores, int_gpus` |
| `acct:folder:{folder_id}` | HASH | `int_min_cores, int_max_cores, int_min_gpus, int_max_gpus, int_cores, int_gpus, show_id` |
| `acct:job:{job_id}` | HASH | `int_max_cores, int_max_gpus, int_priority, int_cores, int_gpus` |
| `acct:layer:{layer_id}` | HASH | `int_cores, int_gpus` (plus any per-layer caps the scheduler reads) |
| `acct:point:{dept_id}:{show_id}` | HASH | `int_min_cores, int_max_cores, int_cores, int_gpus` |
| `acct:seq` | STRING (INCR) | global mutation sequence number |

`job_resource` and `layer_resource` both carry caps the scheduler enforces on
the hot path - neither can be omitted from Redis without breaking per-job or
per-layer cap enforcement.

### The unit invariant: cores, not centicores

PostgreSQL stores cores as **centicores** (cores × 100; the `int_*cores*`
columns and `proc.int_cores_reserved`). Redis stores cores in **unmultiplied
units** (1 = 1 core). Conversion happens at every PG↔Redis and Cuebot↔Redis
boundary - the limit reseed, the booked-counter recompute, the Cuebot release
publisher, and the Rust booking delta. Inside Redis - and inside the Lua
scripts - no centicore arithmetic ever happens.

Two reasons:

1. Redis is the live operational view. Operators reading `redis-cli HGETALL
   acct:sub:...` should see numbers that match what they typed into cueadmin
   (e.g. `cueadmin -create-subscription -size 100` should show `size = 100`,
   not `10000`).
2. The Rust scheduler's hot-path arithmetic is already in cores
   (`CoreSize`). Pushing the conversion to the PG and Cuebot edges keeps the
   hot path free of unit-juggling.

GPU fields and `int_priority` pass through verbatim - no unit conversion.

The `-1` "unlimited" sentinel on `folder_resource.int_max_cores` and
`job_resource.int_max_cores` is preserved verbatim across the conversion. The
hot-path Lua guard (`> 0`) gates the comparison either way, but passing the
sentinel through unchanged keeps `redis-cli` output faithful to the PG meaning.

---

## The `acct:seq` sequence-number guard

`acct:seq` is a monotonic counter in Redis that protects every reseed from a
silent-loss race against concurrent hot-path writes. It is not optional
machinery added later - it is the reseed contract.

### The race it prevents

A reseed has two operations that cannot be made atomic from the outside:

1. **SQL read**: e.g. `SELECT SUM(int_cores_reserved) FROM proc GROUP BY
   pk_show, pk_alloc`.
2. **Redis write**: write each computed total back to the corresponding
   `acct:*` hash.

Between (1) and (2), live hot-path mutations are still happening on Redis.
Without a guard, the reseed clobbers them:

| t | Event | Redis `acct:sub:S:A.int_cores` | proc rows for (S,A) |
|---|---|---|---|
| t0 | start | 50 | 5 rows × 10 cores |
| t1 | Reseed reads PG → `SUM = 50` | 50 | 5 rows |
| t2 | Rust books a frame: Lua `HINCRBY +10` → `INSERT proc` | 60 | 6 rows |
| t3 | Reseed writes Redis from its in-memory snapshot: `HSET ... 50` | **50** ← booking lost | 6 rows |

At t3, the booking from t2 is silently lost in Redis. `proc` is correct, but
Redis under-counts → the next dispatch over-books. This does **not** self-heal
- every reseed cycle reopens the same window.

### The protocol

Every mutating Lua script (booking, force-rollback, Cuebot release publisher)
increments `acct:seq` as part of the same script. Reseed becomes a
compare-and-swap on the entire state:

1. `GET acct:seq` → store as `seq_before`.
2. `SELECT SUM(...) FROM proc` (or read accounting tables, for the limit
   reseed).
3. Compute the new Redis values in memory.
4. Atomic CAS via Lua: *if `GET acct:seq == seq_before` then write the new
   values, else return RETRY*.
5. On RETRY: loop back to (1). After a bounded number of retries under
   sustained load, skip this reseed cycle. Hot-path writes are keeping Redis
   fresh; a reseed that can't make progress is the wrong tool.

The same trace with the guard:

| t | Event | `acct:seq` | Redis `int_cores` |
|---|---|---|---|
| t0 | start | 100 | 50 |
| t1 | Reseed reads `seq_before=100`, SELECT SUM=50 | 100 | 50 |
| t2 | Booking Lua: HINCRBY +10, INCR seq | **101** | 60 |
| t3 | Reseed CAS: seq is 101 ≠ 100 → RETRY | 101 | 60 |
| t4 | Reseed re-reads `seq_before=101`, SELECT SUM=60 | 101 | 60 |
| t5 | No mutations during window | 101 | 60 |
| t6 | Reseed CAS succeeds: HSET ... 60 | 101 | 60 |

No write is clobbered.

The mechanism is the same as the `AtomicU64` sequence guard from the earlier
in-process design - with the counter moved into Redis so it's visible across
processes. Once N>1 schedulers run, this property generalises directly.

---

## Hot path: atomic booking Lua

The scheduler's per-frame booking is a single Lua script that runs against
Redis, executing five updates atomically:

```
1. Read current state of acct:sub / acct:folder / acct:job / acct:layer / acct:point
2. Check booking would not exceed any limit (size, burst, max_cores, etc.)
3. If OK: 5 × HINCRBY (int_cores, int_gpus) + INCR acct:seq, return {1}
4. If over a limit: return structured failure {0, table_name, current, limit}
5. Then transactionally INSERT proc in Postgres (outside Lua)
```

The Lua script returns a structured shape on failure (`{0, table_name,
current, limit}`) so observability and metrics can attribute the rejection to
the right table without re-reading state.

### Rollback (`force` mode)

The same script supports a `force` flag that skips the limit checks and applies
the delta unconditionally. This is the rollback path: if the PG `INSERT proc`
fails after the Lua succeeded, the scheduler calls the script again with
`force=true` and negated deltas to undo the Redis-side change.

One script, two modes - no separate rollback script to keep in sync.

### No idempotency tokens

The booking script has no dedup mechanism. A network blip that causes the
caller to retry a successful booking will double-count in Redis. This is
accepted because:

- The recompute loop (≤ 2 min) heals double-counts from `proc`.
- Adding idempotency tokens would require a write-once log in Redis with its
  own eviction story.
- In practice the duplicate-booking rate from caller retries is far below the
  threshold where it would affect dispatch correctness.

If observed rates change this calculus, idempotency tokens are listed under
[known limitations](#known-limitations-and-future-work).

---

## Reseed loops

Three loops keep Redis convergent with PG. They are explicitly designed to be
the recovery mechanism - hot-path writes drive correctness in the common case,
reseeds drive correctness after failure.

### Booked-counter recompute (every 2 min)

For every scheduler-managed show, the scheduler runs:

```sql
SELECT pk_show, pk_alloc, SUM(int_cores_reserved), SUM(int_gpus_reserved)
FROM proc
WHERE pk_show IN (<scheduler-managed shows>)
GROUP BY pk_show, pk_alloc;
```

The result is dual-written to:

- **PG accounting tables** - so CueGUI's view stays fresh for scheduler-managed
  shows. CueGUI reads PG unchanged; numbers may lag the actual booking state by
  up to one recompute interval.
- **Redis `int_cores` / `int_gpus`** - guarded by the `acct:seq` CAS described
  above.

The dual write happens under the same SUM query for consistency: both PG and
Redis end up showing the same snapshot.

### Limit reseed (every 5 min)

For every scheduler-managed show, the scheduler reads limit fields (`size`,
`burst`, `int_min_cores`, `int_max_cores`, priorities) from the PG accounting
tables and writes them to Redis. This catches changes from Cuebot admin
operations (size/burst/folder cap changes) that don't go through the
afterCommit hook. Five minutes of staleness on cap changes is the documented
drift bound for this path.

### Bootstrap reseed (blocking at startup)

When the scheduler starts, it runs both reseeds end-to-end before accepting
work. The booking pipeline does not start until Redis is fully populated.

Redis is configured without persistence (single node, AOF off), so a Redis
restart shows as an empty store on reconnect. The scheduler detects empty
Redis and re-runs the bootstrap. This is the recovery path: Redis dies →
scheduler stops dispatching → Redis comes back → scheduler reseeds and
resumes.

### Why recompute, not batched additive deltas

The recompute model was chosen over a batched-additive model (where the
scheduler accumulates per-show deltas in memory and flushes them to PG
periodically) for two reasons:

1. **No lost-batch-on-crash failure mode.** A batched flush that fails after
   the scheduler crashes loses every booking in that batch from the PG view.
   Recompute from `SUM(proc)` cannot lose bookings - `proc` is always correct.
2. **A safety net exists.** Recompute is self-correcting: any drift from any
   cause is bounded by the recompute interval. Additive deltas have no such
   property; once they diverge, they stay diverged.

---

## Cuebot integration

### Release publisher (`AccountingRedisPublisher`)

For scheduler-managed shows, `ProcDaoJdbc.unbookProc` only `DELETE`s the proc
row transactionally; the accounting-table UPDATEs from the legacy code path are
skipped (they would race the recompute loop). On `afterCommit`, the release
delta is published to Redis via the `AccountingRedisPublisher` interface.

Two implementations:

- **`LettuceAccountingRedisPublisher`** - wired in when
  `accounting.redis.enabled=true`. Runs a single Lua script that applies five
  `HINCRBY` decrements and increments `acct:seq` atomically.
- **No-op publisher** - wired in when `accounting.redis.enabled=false`.
  Deployments without Redis use this and the unmodified legacy behavior.

Publish failures (network blip, Redis briefly unavailable) are logged at WARN
and swallowed. The recompute loop heals the missing decrement on the next
cycle.

### `recalculate_subs()` show-awareness

Cuebot's 2-hour periodic task that recomputes subscription aggregates already
existed before this subsystem. It is updated to skip rows where
`b_scheduler_managed = true`, so it doesn't fight the scheduler's recompute
loop on those shows.

### Startup guardrail

The combination "any show has `b_scheduler_managed=true` but at least one
Cuebot has `accounting.redis.enabled=false`" is a silent over-booking trap:
that Cuebot's releases never reach Redis, so the scheduler sees counts that
only ever grow.

At startup, Cuebot queries `SELECT COUNT(*) FROM show WHERE b_scheduler_managed
= true`. If the count is > 0 and `accounting.redis.enabled=false`, Cuebot:

- Logs a loud WARN ("Scheduler-managed shows exist but Redis publishing is
  disabled; bookings will silently over-count.").
- Exposes the `cuebot_redis_publish_misconfigured` metric for deploy-time
  alerting.

Cuebot does **not** refuse to start - a misconfigured Cuebot must still serve
gRPC traffic. The signal is loud enough to catch in deploy validation.

### Operator workflow

Transitioning a show between modes is a single CLI operation:

```
cueadmin -show <name> -setSchedulerManaged true    # move to scheduler
cueadmin -show <name> -setSchedulerManaged false   # move back to Cuebot
```

Backed by a `ShowInterface.setSchedulerManaged(show_id, bool)` gRPC method and
a pycue wrapper. Cuebot flips `show.b_scheduler_managed` in a single UPDATE;
the `ShowDao` cache picks up the change within ~30 s; from that moment,
`unbookProc` and `recalculate_subs()` branch on the new value.

No drain or quiesce step is required:

- In-flight bookings continue executing; their releases flow through whichever
  branch is active at release time.
- Transient PG drift after the flip - possibly transiently negative
  `int_cores` going one way, phantom-positive going the other - heals via the
  next recompute (≤ 2 min).
- Redis state is fed by hot-path writes from both sides regardless of the flag,
  so scheduler decisions stay correct across the transition.

The command is safe to run during production hours.

---

## Failure modes and drift bounds

| Failure | Effect | Recovery |
|---|---|---|
| Cuebot `afterCommit` Redis publish fails | Redis missing a decrement; over-counts by 1 booking | Next recompute (≤ 2 min) reseeds booked counters from `proc` |
| Rust scheduler dies between Lua and `proc` INSERT | Redis over-counted by 1; no proc row | Next recompute (≤ 2 min) reseeds Redis from `proc` |
| Rust scheduler dies after `proc` INSERT, before reply to caller | Caller may retry; no Redis dedup → Redis over-counted by 1 | Same as above |
| Cuebot admin operation (size/burst change) | Redis stale on limit fields | Next limit reseed (≤ 5 min) heals from accounting tables |
| Redis itself dies | Scheduler stops dispatching scheduler-managed shows | On Redis recovery, scheduler detects empty Redis, reseeds, resumes |
| `b_scheduler_managed` toggle mid-flight | PG accounting transiently wrong (possibly negative) for that show | Next recompute (≤ 2 min) reseeds from `proc` |
| Cuebot Redis publish enabled but scheduler off | Redis filled but unused; no harm | n/a |
| Scheduler on, Cuebot Redis publish off on *any* Cuebot | Redis missing decrements progressively → silent over-booking | **Deployment invariant** (below); guarded at Cuebot startup |

### Deployment invariant

If any show has `b_scheduler_managed = true`, every Cuebot in the cluster must
have `accounting.redis.enabled = true`. Cuebot's startup guardrail surfaces
violations as a WARN log and the `cuebot_redis_publish_misconfigured` metric.

### CueGUI staleness

CueGUI reads PG accounting tables unchanged. For scheduler-managed shows,
numbers are stale by at most the recompute interval (2 min) plus any in-flight
bookings since the last recompute. For Cuebot-managed shows, accounting is
updated transactionally as before. Acceptable for the existing CueGUI contract.

---

## Configuration

### Cuebot

Spring properties (typically in `opencue.properties` or environment overrides):

```properties
accounting.redis.enabled=true
accounting.redis.host=redis.internal
accounting.redis.port=6379
```

When `accounting.redis.enabled=false`, the no-op publisher bean is wired and
Cuebot behaves exactly as before this subsystem existed.

### Rust scheduler

YAML config (per the scheduler's standard config format):

```yaml
accounting:
  redis_url: "redis://redis.internal:6379"
  recompute_interval_seconds: 120
  limit_reseed_interval_seconds: 300
  redis_pool_size: 20
```

### Redis topology

Current deployment is **single-node, no persistence**. Redis restart equals
empty store, which the scheduler detects on reconnect and recovers from via
bootstrap reseed. Redis is therefore a new SPOF for scheduler-managed shows;
during a Redis outage, the scheduler stops dispatching those shows. See
[known limitations](#known-limitations-and-future-work).

---

## Design decisions and trade-offs

Where the design picked one path and rejected another, the reasoning is here.
Brief versions; the trade-off matters more than the alternative chosen.

| Question | Decision | Trade-off |
|---|---|---|
| Why Redis at all (vs an in-process cache) | Shared store enables horizontal scaling across N scheduler instances; hook-fed deltas are more reliable than reseed-as-primary for convergence | Operational dependency on Redis; new SPOF until HA lands |
| Where the show-ownership flag lives | New `b_scheduler_managed` column on `show`; replaces `dispatcher.exclusion_list` | One-time migration cost for deployments using the old property |
| Per-show vs per-allocation granularity | Per-show only | Mixed-mode shows not supported |
| How PG accounting tables stay current for scheduler-managed shows | Periodic recompute from `SUM(proc)` | CueGUI lag bounded by recompute interval (2 min) |
| How Cuebot release path stays current in Redis | `afterCommit` publish on the release path only - **no** publish on admin/lifecycle paths | Cuebot admin changes propagate to Redis via the 5-min limit reseed, not instantly |
| Concurrency safety on reseeds | `acct:seq` CAS guard on every reseed | Rare RETRY loop under sustained load; bounded by a max-retries cap |
| Idempotency on the booking Lua | None - trust caller retry semantics | Duplicate bookings double-count in Redis until next recompute heals |
| Bootstrap behavior | Blocking reseed at startup, always | Scheduler startup time increases by the bootstrap reseed duration |
| Redis client choice | `redis-rs` (Rust, async with built-in pooling); Lettuce (Java, composes with Spring DI and `TransactionSynchronization.afterCommit`) | Two clients to maintain awareness of |
| Cuebot rollout shape | No two-phase rollout; ship Cuebot with a no-op-when-disabled switch from the start | Cuebot deployments without Redis must explicitly set `accounting.redis.enabled=false` |
| Cuebot per-release flag lookup cost | `ShowDao` cache with ~30 s TTL | Brief stale window after `setSchedulerManaged` toggle |

### Why the per-show partition is load-bearing

Within a single show, exactly one of Cuebot or Rust owns the accounting write
path. There is no double-write and no per-key arbitration. The transition
between modes is brief and self-heals via the next recompute.

The alternative - per-allocation or per-row arbitration - would force every
write on both sides to check ownership, every recompute to handle partial
state, and every operator toggle to specify which dimension was flipping. The
per-show simplification is the reason the rest of the design fits on one page.

---

## Known limitations and future work

These are documented gaps. Each must be addressed before the situation in the
"becomes load-bearing" column arises.

| Item | Why deferred | When it becomes load-bearing |
|---|---|---|
| Leader election for the recompute and limit-reseed loops | Single scheduler instance for now | Before deploying > 1 scheduler instance - two schedulers running the recompute concurrently would race the CAS guard but waste cycles |
| Multi-scheduler bootstrap race | Single scheduler for now | Same |
| Redis HA (Sentinel or Cluster) | Single-node Redis accepted as new SPOF | If "scheduler stops, reseed on recovery" outage tolerance becomes unacceptable in production |
| Cuebot admin afterCommit hooks (size/burst/folder caps) | Drift heals via 5-min limit reseed | If 5-minute limit drift becomes problematic for operators |
| Idempotency tokens on the booking Lua | Recompute heals double-counts within 2 min | If duplicate-booking rate is observed to materially affect dispatch correctness |
| CueGUI surfacing of `b_scheduler_managed` | cueadmin CLI is enough for now | Whenever operator UX is prioritised |

The recompute and limit-reseed loop entry points in `pipeline/entrypoint.rs`
carry `// TODO: gate behind leader-election when multi-scheduler lands`
comments as a pin against accidentally rolling out > 1 scheduler without
addressing leader election first.

---

## Source layout

| Path | Purpose |
|---|---|
| `rust/crates/scheduler/src/accounting/mod.rs` | Module root; orchestrates booking, recompute, limit reseed, bootstrap |
| `rust/crates/scheduler/src/accounting/redis_client.rs` | Redis connection management, Lua script wiring |
| `rust/crates/scheduler/src/accounting/lua.rs` | Booking + force-rollback Lua sources |
| `rust/crates/scheduler/src/accounting/recompute.rs` | 2-min `SUM(proc)` → PG + Redis dual write |
| `rust/crates/scheduler/src/accounting/limit_reseed.rs` | 5-min accounting tables → Redis |
| `rust/crates/scheduler/src/accounting/bootstrap.rs` | Blocking startup reseed |
| `rust/crates/scheduler/src/accounting/managed_shows.rs` | Cached lookup of `b_scheduler_managed = true` shows |
| `rust/crates/scheduler/src/accounting/booking_delta.rs` | Per-booking delta carried through the dispatch pipeline |
| `rust/crates/scheduler/src/accounting/dao.rs` | PG accounting-table queries used by the reseeds |
| `cuebot/.../service/AccountingRedisPublisher.java` | Java interface for the `afterCommit` release publisher |
| `cuebot/.../service/LettuceAccountingRedisPublisher.java` | Lettuce-backed implementation; the Lua release script lives here |
| `cuebot/.../dao/postgres/ProcDaoJdbc.java` | Hosts the show-aware branch in `unbookProc` |
| `cuebot/.../dao/postgres/ShowDaoJdbc.java` | Hosts the `b_scheduler_managed` lookup + cache and the startup count |

## Glossary

- **Accounting tables**: the five PG tables that track reserved resources at
  each hierarchy level - `subscription`, `folder_resource`, `job_resource`,
  `layer_resource`, `point`.
- **`acct:seq`**: monotonic Redis counter incremented by every mutating Lua
  script; the CAS guard for reseeds.
- **Booked counters**: the `int_cores` / `int_gpus` fields - "how much is
  currently reserved", as opposed to limit fields (size, burst, max_cores).
- **CAS guard**: compare-and-swap on `acct:seq` to detect concurrent mutations
  between a reseed's read and write.
- **Limit fields**: `size`, `burst`, `int_min_cores`, `int_max_cores`,
  `int_priority` - configured by operators, changed by admin paths, not by
  bookings.
- **Recompute**: the 2-min loop that rebuilds booked counters from
  `SUM(proc)`.
- **Limit reseed**: the 5-min loop that copies limit fields from PG to Redis.
- **Scheduler-managed show**: a show with `b_scheduler_managed = true` -
  dispatch is owned by the Rust scheduler, releases go through Redis.
- **Cuebot-managed show**: a show with `b_scheduler_managed = false` - legacy
  behavior, Redis not consulted.
