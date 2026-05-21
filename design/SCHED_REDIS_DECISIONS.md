# Redis-Backed Accounting - Decision Record

Outcome of the design session on 2026-05-13. Defines how the Rust scheduler and Cuebot coordinate accounting state (`subscription`, `folder_resource`, `job_resource`, `layer_resource`, `point`) via Redis, in preparation for horizontal scaling of the scheduler.

This document records *what* was decided and *why*. Implementation details (signatures, exact SQL, file paths) will be ported to a follow-up implementation plan.

---

## 0. Starting point

**Performance targets.** `time_to_book < 30s` and `cluster round-trip < 5s` under multiple concurrent large shows. The shared resource being protected is Postgres CPU - the Rust scheduler must coexist with Cuebot on the same database without degrading Cuebot's host-report throughput.

**Already shipped on this branch (perf "Phase 1").** Four independent quick wins: empty-cluster sleep raised 3s → 30s (configurable), `LIMIT N` on `QUERY_PENDING_BY_SHOW_FACILITY_TAG`, EXISTS-rewrite + new indexes + facility case-sensitivity fix, host-cache refresh overlap guard. Net effect: ~10× drop in `QUERY_PENDING` rate and ~3–5× per-call cost reduction. These reduce baseline DB load so accounting becomes the next bottleneck to address; they do not interact with the accounting design.

**Replaces an earlier in-process accounting design.** Before Redis, the team designed an in-process accounting cache: a generic `AccountingCache<T: AccountingTable>` backed by `Arc<RwLock<HashMap<K, V>>>`, populated by a 20s "tier-1" reseed from `SUM(proc)` and persisted to Postgres by a 3-min "tier-2" UPDATE for Cuegui visibility. Concrete deliverables (trait shapes, SQL queries, an `AtomicU64` sequence-number guard, a 5-cache compensation rollback at `pipeline/dispatcher/actor.rs:527`) had already been spec'd. **This document replaces that plan.** The in-process cache could not be shared across scheduler instances, and the reseed-as-primary-sync model concentrated drift in failure modes. Redis is the chosen shared store; hook-fed deltas replace reseed-as-primary; the cache moves out-of-process.

**Redis-consistency variants considered and rejected.**

- **Redis as a derived index of Postgres** (Cuebot writes Postgres transactionally; afterCommit copies the delta to Redis; the scheduler reads Redis on the hot path). Conservative and safe under a Redis outage, but the win in Postgres lock contention from the scheduler's hot path was small relative to what a Redis-authoritative path delivers.
- **Both sides write Redis only; a drainer persists to Postgres asynchronously.** Maximally decoupled, but Redis loss = data loss unless AOF/replica is bulletproof, and the drainer becomes a new SPOF. Too far ahead of where we trust Redis in this stack today.
- **Cuebot writes both Postgres and Redis inline in the same code path.** No transaction guarantees between the two stores - partial failures diverge with no recovery story. Anti-pattern.

The chosen design (see §2) sits between the first two: Redis is the live operational view both sides write through; Postgres is durably correct via either Cuebot's transactional writes (for Cuebot-managed shows) or the scheduler's periodic recompute from `proc` (for scheduler-managed shows). `proc` is the canonical record of bookings.

**Cuebot accounting write surface today.** Three categories: the release path (`ProcDaoJdbc.unbookProc`, ~5 transactional UPDATEs per frame completion), low-volume admin DAOs (`SubscriptionDaoJdbc`, `GroupDaoJdbc`, `PointDaoJdbc`), and rare lifecycle DAOs (folder/subscription/show create/delete). The release path is the only one this design hooks; admin and lifecycle drift heals via the limit reseed. Booking-increment writes from Cuebot become dead code once the Rust scheduler owns dispatch for scheduler-managed shows.

---

## 1. Driver

**Horizontal scaling of the Rust scheduler in the next ~6 months.** The prior in-process accounting cache (§0) cannot be shared across scheduler instances; any path that grows to N schedulers either needs a shared store or a complex cross-process reconciliation. Redis is the chosen shared store. The reseed-as-primary-sync mechanism in that earlier design was also "starting to look like a recipe for drift" - hook-fed deltas are a more reliable convergence model than a periodic reseed loop.

Secondary properties Redis buys:
- Survives scheduler restart without a cold reseed.
- Operational visibility via `redis-cli`.
- Decouples Rust's per-booking write rate from Postgres lock contention.

---

## 2. Architecture

### 2.1 Source-of-truth model

Hybrid, deliberately:

| Component | Hot path | Slow path |
|---|---|---|
| Rust scheduler | Atomic Lua against Redis (check + 5×HINCRBY + INCR seq), then INSERT `proc` in PG transactionally | Periodic recompute (every 2 min) writes PG accounting tables for scheduler-managed shows from SUM(proc) |
| Cuebot release path (`ProcDaoJdbc.unbookProc`) | For scheduler-managed shows: only `DELETE proc` transactionally, then afterCommit publish to Redis. For Cuebot-managed shows: today's behavior unchanged | - |
| Cuebot admin paths (size/burst/min/max changes) | Today's behavior unchanged; **no Redis publish hook** | - |
| Cuegui | Reads PG accounting tables (today, unchanged) | - |

**`proc` remains the canonical record of bookings**, written transactionally by both sides. Accounting tables in PG are *derived* from `proc` (via Rust recompute for scheduler-managed shows, via Cuebot's transactional UPDATEs for Cuebot-managed shows). Redis is the live operational view fed by hot-path writes from both sides.

### 2.2 Why this shape

The per-show partition is the load-bearing simplification. Within a single show, exactly one of Cuebot or Rust owns the accounting write path; there is no double-write and no per-key arbitration. The transition between modes is brief and self-heals via the next recompute.

### 2.3 Redis schema

Six key namespaces, one per accounting table plus a global sequence counter:

| Key | Type | Fields |
|---|---|---|
| `acct:sub:{show_id}:{alloc_id}` | HASH | `size, burst, int_cores, int_gpus` |
| `acct:folder:{folder_id}` | HASH | `int_min_cores, int_max_cores, int_min_gpus, int_max_gpus, int_cores, int_gpus, show_id` |
| `acct:job:{job_id}` | HASH | `int_max_cores, int_max_gpus, int_priority, int_cores, int_gpus` |
| `acct:layer:{layer_id}` | HASH | `int_cores, int_gpus` (and any per-layer caps if the scheduler reads them) |
| `acct:point:{dept_id}:{show_id}` | HASH | `int_min_cores, int_max_cores, int_cores, int_gpus` |
| `acct:seq` | STRING (INCR) | global mutation sequence number |

Both `job_resource` and `layer_resource` carry caps the scheduler enforces - they cannot be omitted from Redis without breaking per-job and per-layer cap enforcement on the hot path.

### 2.4 The `acct:seq` sequence-number guard

`acct:seq` is a monotonic counter in Redis that protects every reseed (booked-counter or limit) from a silent-loss race against concurrent hot-path writes.

**The race.** A reseed has two operations that cannot be made atomic from the outside:

1. **SQL read**: e.g. `SELECT SUM(int_cores_reserved) FROM proc GROUP BY pk_show, pk_alloc`.
2. **Redis write**: write each computed total back to the corresponding `acct:*` hash.

Between (1) and (2), live hot-path mutations are still happening on Redis. Without a guard, the reseed clobbers them.

| t | Event | Redis `acct:sub:S:A.int_cores` | proc rows for (S,A) |
|---|---|---|---|
| t0 | start | 50 | 5 rows × 10 cores |
| t1 | Reseed reads PG → `SUM = 50` | 50 | 5 rows |
| t2 | Rust books a frame: Lua `HINCRBY +10` → `INSERT proc` (txn) | 60 | 6 rows |
| t3 | Reseed writes Redis from its in-memory snapshot: `HSET ... 50` | **50** 🚨 | 6 rows |

At t3, the booking from t2 is silently lost in Redis. `proc` is correct, but Redis under-counts → next dispatch over-books. This does **not** self-heal - every reseed cycle re-opens the same window.

**The protocol.** Every mutating Lua script (booking, force-rollback, Cuebot release publisher) increments `acct:seq` as part of the same script. Reseed becomes a compare-and-swap on the entire state:

1. `GET acct:seq` → store as `seq_before`.
2. `SELECT SUM(...) FROM proc` (or read accounting tables for limit reseed).
3. Compute the new Redis values in memory.
4. Atomic CAS via Lua: *if `GET acct:seq == seq_before` then write the new values, else return RETRY*.
5. On RETRY: loop back to (1). After a bounded number of retries under sustained load, skip this reseed cycle - hot-path writes are keeping Redis fresh, and a reseed that can't make progress is the wrong tool.

Re-running the trace with the guard:

| t | Event | `acct:seq` | Redis `int_cores` |
|---|---|---|---|
| t0 | start | 100 | 50 |
| t1 | Reseed reads `seq_before=100`, SELECT SUM=50 | 100 | 50 |
| t2 | Booking Lua: HINCRBY +10, INCR seq | **101** | 60 |
| t3 | Reseed CAS: seq is 101 ≠ 100 → RETRY | 101 | 60 ✓ |
| t4 | Reseed re-reads `seq_before=101`, SELECT SUM=60 | 101 | 60 |
| t5 | No mutations during window | 101 | 60 |
| t6 | Reseed CAS succeeds: HSET ... 60 | 101 | 60 ✓ |

No write was clobbered.

**Why this must land in PR C, not later.** Without the guard, the reseed loop *appears* correct under low-load testing (no concurrent writes during the reseed window → no race fires) but degrades silently in production. By the time over-booking is observed, every scheduler is already running the racy code. The guard is part of the reseed, not a follow-up. The earlier in-process design solved the same race with an `AtomicU64` in the scheduler process; this is the same mechanism with the counter moved into Redis for cross-process visibility.

---

## 3. Decisions log

| # | Question | Decision |
|---|---|---|
| Q1a | Why Redis at all (vs an in-process cache)? | **N-scheduler horizontal scaling within ~6 months.** Secondary: hook-fed cache is more reliable than reseed-fed for convergence. |
| Q1b | Time horizon for multi-scheduler | **6 months.** |
| Q1c | Two-phase rollout (Rust-only Redis first, then hook Cuebot) or skip straight to hooked Cuebot | **Skip the two-phase rollout.** Go straight to hooked Cuebot, with a no-op-when-not-configured switch so non-Redis deployments still work. |
| Q2a | Source of truth (Redis-first / PG-first / Redis-only) | **Hybrid (see §2.1).** Redis is the live operational view; `proc` is canonical for booking facts; PG accounting tables are *derived* via recompute or Cuebot transactional writes depending on show ownership. |
| Q2b | Which tables go into Redis | **All five:** subscription, folder_resource, job_resource, layer_resource, point. |
| Q2c | Cuebot configuration scope | **Global.** All Cuebot instances configured identically; if the scheduler is on, all Cuebots talk to Redis. |
| Q2d | Failure recovery direction | **Reseed heals drift.** A few minutes of drift is acceptable. |
| Q3a | PG accounting writes from Rust | **Periodic recompute from SUM(proc)**, not batched-additive deltas. Avoids the lost-batch-on-crash failure mode and the no-safety-net problem. |
| Q3b | Cuebot afterCommit hook scope | **Release path only** (`ProcDaoJdbc.unbookProc`). Admin/lifecycle paths are out of scope; drift heals via limit reseed. |
| Q3c | Reseed flows | **Two flows.** Booked counters reseed from SUM(proc) → Redis. Limit fields reseed from accounting tables → Redis. |
| Q5a / Q7a / Q8a | Where the partition lives | **New `b_scheduler_managed boolean` column on the `show` table.** Single source of truth; replaces `dispatcher.exclusion_list` entirely. |
| Q7b | Per-show vs per-allocation granularity | **Per-show only.** A show is either scheduler-managed or Cuebot-managed - no per-allocation mixed mode. `exclusion_list` format simplifies to show-name-only (then is removed in favor of the column). |
| Q7c | Behavior at ownership transitions | **Recompute heals.** No special runbook step. Transient PG drift (possibly negative `int_cores`) is acceptable for a few minutes after a flip. |
| Q8b | How operators toggle the flag | **New `cueadmin` operation that transitions a show in either direction** (Cuebot-managed → scheduler-managed and back). Backed by a new `ShowInterface.setSchedulerManaged(show_id, bool)` gRPC method, plus a pycue wrapper. Operator-visible behavior: `cueadmin -show foo -setSchedulerManaged true` flips the column; transient PG drift heals via next recompute (≤2 min). |
| Q8c | Reconcile cadences | **Recompute every 2 min** (PG accounting + Redis booked counters, unified - same SUM query, dual writes). **Limit reseed every 5 min** (separate, reads accounting tables → Redis). |
| Q6c / Q8d | Lua script return shape | **Structured return:** `{0, table_name, current, limit}` on failure for observability. |
| Q8d | Rollback path | **Same script with `force=true` flag** that skips limit checks. One script, two modes. |
| - | Idempotency / dedup | **No dedup.** Trust caller retry semantics; rare double-bookings heal via reseed. |
| Q6d / Q8e | Bootstrap | **Blocking reseed at startup, always.** Single scheduler for now; multi-scheduler race is deferred (see §5). |
| Q6e / Q8f | Redis topology + persistence | **Single node, no persistence.** Redis restart = empty; scheduler detects empty Redis on reconnect and triggers reseed before accepting work. |
| Q9a | Cuebot's `recalculate_subs()` (2-hour task) | **Make show-aware** - skip rows where `b_scheduler_managed = true`. Same pattern as `unbookProc`. |
| Q9b | Cuebot per-release flag lookup | **`ShowDao` cache with ~30s TTL.** Brief stale window after a toggle is acceptable; matches the drift tolerance elsewhere. |
| Q9c | Rust Redis client | **`redis-rs`** (async, with its built-in pooling). Pool size ~20 connections. |
| Q9d | Cuebot Redis client | **Lettuce.** Composes well with `TransactionSynchronization.afterCommit` and Spring DI. Gated by `accounting.redis.enabled` property; no-op publisher bean when disabled. |

---

## 4. Consequences

### 4.1 Cuebot footprint (modest)

- New column `show.b_scheduler_managed` + Flyway migration.
- `ProcDaoJdbc.unbookProc`: branch on flag - for scheduler-managed shows, only `DELETE proc` transactionally; afterCommit publishes 5 HINCRBYs to Redis. For other shows, today's behavior.
- `ShowDao`: cache the flag with ~30s TTL.
- New `ShowInterface.setSchedulerManaged(show_id, bool)` gRPC method, pycue wrapper, and `cueadmin` subcommand. This is the bidirectional transition operation - moving a show from Cuebot-managed to scheduler-managed (and back) is a single-flag operator command; no drain or quiesce step is required.
- New Spring config: `accounting.redis.enabled`, `accounting.redis.host`, `accounting.redis.port`. No-op publisher bean when disabled.
- `recalculate_subs()`: skip scheduler-managed shows.
- **Startup guardrail (§4.3 invariant):** at Cuebot boot, query `SELECT COUNT(*) FROM show WHERE b_scheduler_managed = true`. If the count is > 0 and `accounting.redis.enabled=false`, log `WARN` with a clear message ("Scheduler-managed shows exist but Redis publishing is disabled; bookings will silently over-count.") and a metric `cuebot_redis_publish_misconfigured`. Does not refuse to start - a misconfigured Cuebot must still serve gRPC traffic - but the warning is loud enough to catch in deploy validation.
- Remove `dispatcher.exclusion_list` and `dispatcher.scheduler_manages_resources` properties (and supporting code).

### 4.2 Rust scheduler footprint (large)

- New `crates/scheduler/src/accounting/` module replaces the existing `ResourceAccountingService`.
- `AccountingTable` trait + per-table impls for 5 tables, but the *backing store is Redis*, not an in-process `HashMap`. The trait's role shifts from "abstract over `HashMap<K, V>`" to "abstract over Redis key encoding and Lua script wiring."
- Hot-path Lua script (atomic check-and-modify, structured return, `force` flag).
- Recompute loop (every 2 min) → SUM(proc) → dual write to PG + Redis. Filtered to `b_scheduler_managed = true` shows.
- Limit reseed loop (every 5 min) → accounting tables → Redis.
- Bootstrap: blocking reseed at startup, populates Redis from PG before accepting work.
- New `BookingDelta` carrying `show_id, alloc_name, folder_id, job_id, layer_id, dept_id, core_delta, gpu_delta`. Requires extending `DispatchLayer` (and the underlying `LayerWithFramesModel` / `QUERY_LAYERS_WITH_FRAMES` in `dao/layer_dao.rs`) to carry `folder_id` and `dept_id` - these are constant per-job but not currently propagated to the dispatcher.
- Compensation rollback at `pipeline/dispatcher/actor.rs:527` calls the Lua script in force mode with negated deltas.

### 4.3 Failure modes & drift bounds

| Failure | Effect | Recovery |
|---|---|---|
| Cuebot afterCommit Redis publish fails | Redis missing a decrement; over-counts by 1 booking | Next recompute (≤2 min) reseeds booked counters from `proc` |
| Rust scheduler dies between Lua and `proc` INSERT | Redis over-counted by 1; no proc row | Next recompute (≤2 min) reseeds Redis from `proc` |
| Rust scheduler dies after `proc` INSERT, before reply to caller | Caller may retry; no Redis dedup → Redis over-counted by 1 | Same as above - recompute heals |
| Cuebot admin operation (size/burst change) | Redis stale on limit fields | Next limit reseed (≤5 min) heals from accounting tables |
| Redis itself dies | Scheduler stops dispatching | On Redis recovery, scheduler detects empty Redis, reseeds, resumes |
| `b_scheduler_managed` toggle mid-flight | PG accounting transiently wrong (possibly negative) for that show | Next recompute (≤2 min) reseeds from `proc` |
| Cuebot Redis publish enabled but Rust scheduler off | Redis filled but unused; no harm | n/a |
| Rust scheduler on, Cuebot Redis publish off | Redis missing decrements progressively → silent over-booking | **Deployment invariant: if any show has `b_scheduler_managed=true`, all Cuebots must have `accounting.redis.enabled=true`.** Guarded at Cuebot startup by a `WARN` log + `cuebot_redis_publish_misconfigured` metric (see §4.1). |

### 4.3.1 Operator workflow: moving a show between modes

Transitioning a show from Cuebot-managed to scheduler-managed (or back) is intentionally a single-step operator action:

```
cueadmin -show <name> -setSchedulerManaged true    # move to scheduler
cueadmin -show <name> -setSchedulerManaged false   # move back to Cuebot
```

The command issues `ShowInterface.setSchedulerManaged(show_id, bool)` over gRPC. Cuebot flips `show.b_scheduler_managed` in a single UPDATE; the `ShowDao` cache picks up the change within ~30s (per Q9b); from that moment, `unbookProc` and `recalculate_subs()` branch on the new value.

No drain or quiesce step is required because:

- In-flight bookings on the show continue executing; their releases flow through whichever branch is active at release time.
- Transient PG drift after the flip (possibly transiently-negative `int_cores` going one way, phantom-positive going the other - see Q7c) heals via the next recompute (≤2 min).
- Redis state is fed by hot-path writes from both sides regardless of the flag, so scheduler decisions stay correct across the transition.

The CLI command should be safe to run during production hours.

### 4.4 Cuegui impact

Cuegui reads PG accounting tables unchanged. For scheduler-managed shows, numbers are stale by at most the recompute interval (2 min) plus any in-flight bookings since the last recompute. For Cuebot-managed shows, accounting is updated transactionally as today. Acceptable for the existing Cuegui contract.

### 4.5 Backward compatibility

- Deployments without Redis configured: `accounting.redis.enabled=false`, Cuebot afterCommit publisher is no-op, Rust scheduler not in use. Today's behavior preserved.
- Deployments running the Rust scheduler today with perf Phase 1 (§0) only: unchanged. The earlier in-process accounting cache design is replaced by this one, not layered on top - no migration of in-process cache code needed (none was merged).
- `dispatcher.exclusion_list` removal is a breaking change for existing deployments using it. Migration: any show currently in `exclusion_list` must be updated in the `show` table via cueadmin during the upgrade.

---

## 5. Explicitly deferred

These are known gaps that don't need to be solved now, but must be addressed before the multi-scheduler rollout.

| Item | Why deferred | When it becomes load-bearing |
|---|---|---|
| Leader election for the recompute loop | Single-scheduler-only for now | Before deploying >1 scheduler instance |
| Multi-scheduler bootstrap race | Single-scheduler-only for now | Same |
| Redis HA (Sentinel or Cluster) | Single-node accepted as new SPOF | If outage tolerance of "scheduler stops, reseed on recovery" becomes unacceptable in production |
| Cuebot admin afterCommit hooks (size/burst/folder caps) | Drift heals via limit reseed (≤5 min) | If 5-minute limit drift becomes problematic |
| Idempotency tokens on Lua script | Drift heals via reseed | If duplicate-booking rate is observed to materially affect dispatch correctness |
| CueGUI surfacing of `b_scheduler_managed` | Cueadmin is enough for now | Whenever operator UX is prioritized |

A `// TODO: gate behind leader-election when multi-scheduler lands` comment is required at the recompute and limit-reseed loop entry points in `pipeline/entrypoint.rs` (or wherever they spawn).

**Not deferred** - the `acct:seq` sequence-number guard (see §2.4) must land in PR C alongside the reseed loops. It is part of the reseed contract, not a follow-up.

---

## 6. PR shape

This is one feature, but it spans Cuebot (Java), Rust scheduler, proto, and pycue/cueadmin. Suggested staging:

**PR A - Schema + show-management flag + Cuebot read-side.**
- Flyway migration adding `show.b_scheduler_managed` (default false).
- `ShowInterface.setSchedulerManaged` gRPC method + Cuebot impl + pycue wrapper + cueadmin subcommand.
- `ShowDao` flag lookup with ~30s TTL.
- `recalculate_subs()` skips scheduler-managed shows.
- No Redis dependency or behavior change yet - flag is always false in practice. This PR can land independently of any Redis decisions.
- Change DispatcherDaoJdbc to stop relying on `exclusion_list` and use the new column
- Remove `dispatcher.exclusion_list` + `dispatcher.scheduler_manages_resources` properties and supporting code.
- Remove deprecated config in opencue.properties.

**PR B - Cuebot Redis publisher + show-aware `unbookProc`.**
- Add Lettuce dependency.
- `accounting.redis.enabled` / `accounting.redis.host` / `accounting.redis.port` Spring properties.
- Real Lettuce-backed publisher bean wired in, conditionally active on `accounting.redis.enabled=true`. No-op publisher bean wired when disabled.
- Branch in `ProcDaoJdbc.unbookProc` on the cached flag: scheduler-managed shows get `DELETE proc` + afterCommit Redis publish; other shows keep today's behavior.
- Startup-time `WARN` + `cuebot_redis_publish_misconfigured` metric when any show has `b_scheduler_managed=true` but `accounting.redis.enabled=false` (see §4.1).
- Per the deployment invariant in §4.3, this PR must ship before PR C in production.

**PR C - Rust scheduler accounting module.**
- New `crates/scheduler/src/accounting/` module replacing `ResourceAccountingService`.
- Hot-path Lua script (atomic check-and-modify with `force` flag).
- Recompute loop (every 2 min), filtered to scheduler-managed shows.
- Limit reseed loop (every 5 min).
- Bootstrap reseed (blocking at startup, always).
- `BookingDelta` over 5 tables; `DispatchLayer` schema extended with `folder_id`/`dept_id`.
- Compensation rollback updated to use Lua force mode.
- Sequence-number guard (`acct:seq`) on every reseed - see §2.4. Required in this PR; cannot be a follow-up.
- TODO comments for leader-election gating at the recompute and limit-reseed loop entry points.

**PR D - Cleanup.**
- Remove any earlier in-process accounting cache code paths if they landed before this design (none expected).

PR A is a pure no-op in production. PR B activates the Cuebot publishing surface. PR C is the only point at which production scheduler behavior changes; it requires PR B to be live in production first or Redis state will be wrong. Keep in mind nothing will be put in production until the entire feature is completed. Every PR will be smoke tested on the dev environment manually.
