---
title: "Scheduler Accounting Reference"
nav_order: 101
parent: Reference
layout: default
linkTitle: "Scheduler Accounting"
date: 2026-06-26
description: >
  Technical reference for the in-memory accounting subsystem in the Rust scheduler and the
  PostgreSQL LISTEN/NOTIFY feed from Cuebot
---

# Scheduler Accounting Reference

## How the Rust scheduler enforces per-show resource limits with in-memory counters and a PostgreSQL NOTIFY feed from Cuebot

---

## Overview

The accounting subsystem tracks how much of each resource pool is currently
booked so that every dispatch decision the [Rust scheduler](/docs/developer-guide/scheduler/)
makes can be gated on a hard cap. If a job is already at its `int_max_cores`,
the scheduler must not book another frame against it.

The single source of truth for a scheduler-managed show's booked counters is an
**in-memory `Store` inside the scheduler process**. PostgreSQL remains the
durable system of record for the `proc` rows the counters are derived from, and
Cuebot keeps the PG accounting tables fresh for CueGUI, but no external store
sits on the booking hot path. A booking is a lock-guarded, in-process atomic
check-and-increment.

This replaces an earlier Redis-backed design. Redis was introduced to let the
counters be shared across N scheduler instances, but the scheduler is and will
remain **single-instance (N=1)**. At N=1, Redis's only unique benefit (splitting
one show across instances) is unreachable, while it manufactured an entire class
of accounting-drift bugs (limit-seeding fail-closed, mass dispatch rejection,
double-booking, CAS starvation). A single in-process counter makes that bug
class *structurally impossible*: there is exactly one writer and one reader of
the booked state, and the check and the increment happen under the same lock.

Source:
- `rust/crates/scheduler/src/accounting/` (the store, listener, and backstop loops)
- `cuebot/.../service/AccountingNotifier.java` (the PG `pg_notify` emitter)

---

## Source-of-truth model

This is the load-bearing design choice; everything else falls out of it.

| Component | Hot path | Backstop |
|---|---|---|
| Rust scheduler (booking) | In-process atomic check + increment in `Store` under one lock, then `INSERT proc` in PG transactionally | Recompute (~15 s) overwrites booked counters from `SUM(proc)`, carrying in-flight bookings forward |
| Cuebot release path (`ProcDaoJdbc.procDestroyed`) | For scheduler-managed shows: `DELETE proc` plus a transactional `pg_notify('acct_release', …)` in the **same** transaction. For Cuebot-managed shows: unchanged transactional accounting-table UPDATEs | Recompute heals any missed notification |
| Cuebot admin cap changes (burst / folder & job max cores/gpus) | Transactional accounting-table UPDATE plus a transactional `pg_notify('acct_limit_change', …)` in the same transaction | Limit reseed (~5 min) re-reads the caps from PG |
| CueGUI | Reads PG accounting tables (refreshed by the scheduler's recompute for managed shows; written transactionally by Cuebot for Cuebot-managed shows) | - |

Three properties hold:

- **`proc` is canonical for bookings.** Both sides write `proc`
  transactionally. The booked counters can always be reconstructed from
  `SELECT SUM(int_cores_reserved) FROM proc GROUP BY pk_show, pk_alloc` (and the
  folder/job groupings).
- **The in-memory `Store` is the live enforced state.** It is what the booking
  check reads and increments. It is seeded from PG at startup and kept fresh by
  the NOTIFY feed, reconciled to `SUM(proc)` by the recompute.
- **The PG accounting tables are derived, for display only.** For
  scheduler-managed shows they are refreshed by the recompute loop; for
  Cuebot-managed shows Cuebot writes them transactionally as before. Nothing on
  the scheduler's hot path reads them.

### Why in-memory, not Redis or PG-on-the-hot-path

- **PG-on-the-hot-path** is what the scheduler was built to escape: the
  scheduler's booking rate hammered the same accounting rows Cuebot's
  `HostReportHandler` writes, and lock waits on `subscription`,
  `folder_resource`, and `job_resource` limited throughput.
- **Redis** decoupled the hot path from PG locks and could in principle be
  shared across schedulers, but at N=1 it bought nothing the in-process store
  does not, and every reseed had to defend against a read/write race with live
  hot-path writes (the `acct:seq` compare-and-swap). That race only exists
  because the counter lives in a separate process from the writer. Move the
  counter in-process and the race — and the CAS, and the retry loop, and the
  starvation failure mode — all disappear.

The in-process store keeps the hot path off PG locks (the win Redis gave) while
removing the cross-process coordination Redis required (the cost Redis added).

---

## Show ownership: the per-show partition

Within a single show, exactly one of Cuebot or the scheduler owns the accounting
write path. There is no double-write and no per-key arbitration. The flag lives
on the `show` table (migration `V45__show_scheduler_managed.sql`, unchanged by
this rewrite):

```sql
ALTER TABLE show ADD COLUMN b_scheduler_managed BOOLEAN NOT NULL DEFAULT false;
```

- `b_scheduler_managed = false` (default): the show is **Cuebot-managed**.
  Cuebot books and releases against the PG accounting tables transactionally,
  exactly as before. The scheduler's store is not consulted, and Cuebot emits no
  NOTIFY for it.
- `b_scheduler_managed = true`: the show is **scheduler-managed**. The scheduler
  books against its in-memory store on the hot path; Cuebot's release path only
  deletes the `proc` row and emits an `acct_release` notification. The PG
  accounting tables for this show are refreshed by the scheduler's recompute.

The flag is **per-show, not per-allocation.** A show is either
scheduler-managed or it isn't.

### Looking up the flag

The scheduler caches the set of `b_scheduler_managed = true` show ids in
`ManagedShowsCache`, refreshed on a TTL (`managed_shows_ttl`, default 30 s).
`apply_booking` consults this cache and is a no-op for shows the scheduler does
not currently manage. Cuebot independently caches the flag for its release path.
The brief stale window after a toggle is safe in both directions — see
[Managed-flip seed](#managed-flip-seed) and [Failure modes](#failure-modes-and-drift).

---

## The store

`accounting/store.rs` holds the entire enforced state in process behind a single
`Mutex`:

| Map | Key | Holds |
|---|---|---|
| `sub` | `(show_id, alloc_id)` | booked `cores`/`gpus` + `pending` deltas |
| `folder` | `folder_id` | booked `cores`/`gpus` + `pending` deltas |
| `job` | `job_id` | booked `cores`/`gpus` + `pending` deltas |
| `sub_burst` | `(show_id, alloc_id)` | subscription burst cap, in cores |
| `folder_caps` | `folder_id` | folder `max_cores` / `max_gpus`, in cores |
| `job_caps` | `job_id` | job `max_cores` / `max_gpus`, in cores |

### Only three vertices are enforced

The five accounting tables in PG are subscription, folder, job, layer, and
department point. The scheduler tracks and enforces only **three**: subscription
(burst), folder (`int_max_cores`/`int_max_gpus`), and job
(`int_max_cores`/`int_max_gpus`). The booking Lua this replaces incremented
layer and point counters too, but the booking check never *read* them, so they
are not kept in the store. (Layer/point limits are still visible to CueGUI via
PG, unchanged.)

### One lock, pure in-memory critical sections

A single `Mutex` guards the whole store. Every critical section is pure
in-memory arithmetic — no I/O, no `.await` — so contention is negligible at this
scale and the multi-vertex check-and-increment is trivially atomic. A booking
touches subscription, folder, and job under one lock acquisition; there is no
window in which a concurrent booking could see a half-applied increment.

### The booking hot path

`Store::book(&BookingDelta)` performs, under the lock, an atomic
check-and-increment across the three enforced vertices:

```text
1. If cores delta > 0:
     check subscription burst   -> reject "subscription" if over
     check folder int_max_cores -> reject "folder"       if over
     check job int_max_cores    -> reject "job"          if over
2. If gpus delta > 0:
     check folder int_max_gpus  -> reject "folder_gpus"  if over
     check job int_max_gpus     -> reject "job_gpus"      if over
3. On success: increment all three vertices and record the delta as `pending`.
```

It returns `Applied` or `LimitExceeded { table, current, limit }`, where `table`
names the offending vertex for metrics and operator-facing rejection messages.
The `INSERT proc` happens in PG **outside** the lock, after `book` returns
`Applied`.

#### Cap conventions

A subscription **burst** cap of `0` means "reject all" — a missing burst entry
(before the bootstrap seed) reads as `0` and fails closed, matching Cuebot's
`IS_SHOW_OVER_BURST` convention. A folder/job **max** of `0` or any non-positive
value (notably the `-1` unlimited sentinel) is treated as *unbounded* — the
`> 0` guard skips the comparison. The two conventions are distinct on purpose:
an unseeded subscription must reject (we don't know its real burst yet), whereas
an unset hard cap genuinely means unlimited.

### Confirm and rollback

After `book` returns `Applied`, the dispatcher carries the delta through to the
`proc` transaction's outcome:

- **`confirm`** runs once the `proc` row is committed and RQD has launched the
  frame. It drops the `pending` portion of the delta but keeps the booked
  increment.
- **`rollback`** runs if the `proc` INSERT or RQD launch fails. It undoes both
  the booked increment and the `pending` delta (the in-process equivalent of the
  old force-rollback Lua).

Exactly one of `confirm`/`rollback` runs per successful `book`. Both ignore
current managed status: if `apply_booking` applied a delta, it must be settled
even if the show flipped to Cuebot-managed in between.

If the scheduler crashes between `book` and the `proc` INSERT, the booked
increment is simply lost from memory — but so is the whole store, which the
[bootstrap seed](#bootstrap-blocking-startup-seed) rebuilds from `SUM(proc)` on
restart. There is no durable over-count to clean up.

---

## The two NOTIFY channels

Cuebot is the only writer of `proc` deletions and cap changes, so it is the
source of the two live signals that keep the scheduler's store fresh between
recompute passes. Each notification is emitted with `SELECT pg_notify(channel,
payload)` **in the same transaction** as the PG write it describes.

`pg_notify` is transactional: the notification is delivered if and only if the
enclosing transaction commits, and is discarded on rollback. This is strictly
better than the old Redis `afterCommit` publish, which ran *after* the commit
and so had a partial-failure window (commit succeeds, publish fails). Here there
is no such window — the DELETE and its release signal are atomic.

The scheduler listens on both channels with a dedicated `PgListener`
(`accounting/listener.rs`), separate from the query pool. On any connection
drop it reconnects with a fixed backoff; missed notifications during the gap are
healed by the backstop loops (see [Failure modes](#failure-modes-and-drift)).

### `acct_release`

Emitted per proc on the scheduler-managed branch of `ProcDaoJdbc.procDestroyed`.
The payload carries the show/alloc/folder/job ids and **signed** core/gpu deltas
(negative for a release), in cores:

```json
{
  "show":   "<uuid>",
  "alloc":  "<uuid>",
  "folder": "<uuid>",
  "job":    "<uuid>",
  "layer":  "<uuid>",
  "dept":   "<uuid>",
  "cores":  -10,
  "gpus":   -1
}
```

The scheduler decrements the subscription/folder/job counters by the delta.
`layer` and `dept` are included for symmetry and debuggability; the listener
ignores them (those vertices are not enforced). The decrement is unconditional
and pending-free — a release is always for a long-committed booking.

### `acct_limit_change`

Emitted in the same transaction as a cueadmin cap change. Exactly one vertex per
message; core values are in cores (`-1` = unlimited), GPUs pass through:

```json
{ "vertex": "sub",    "show": "<uuid>", "alloc": "<uuid>", "burst": 200 }
{ "vertex": "folder", "id": "<uuid>", "max_cores": 20, "max_gpus": 4 }
{ "vertex": "job",    "id": "<uuid>", "max_cores": -1 }
```

For `folder` and `job`, `max_cores` and `max_gpus` are each optional; a message
may set one, the other, or both (the listener expands a both-fields message into
two cap changes). Only the **five enforced caps** are wired to emit:
subscription burst, folder max cores/gpus, and job max cores/gpus. Size,
min-cores, priority, layer, and point caps are not enforced by the scheduler and
emit nothing.

Cuebot emits a cap change only for scheduler-managed shows: each cap DAO resolves
the owning show id (the subscription/group/job interfaces all expose it, so no
extra query is needed) and gates the `pg_notify` on `ShowDao.isSchedulerManaged`
(short-circuited by the `accounting.notify.enabled` flag). The scheduler's listener
applies every cap change it receives without re-filtering — correctness comes from
the emit-side gate. Admin cap changes are rare, so this costs nothing in practice.

---

## The recompute backstop and the pending carry-forward

The recompute loop (`accounting/recompute.rs`, every `recompute_interval`,
default **15 s**) is the correctness backstop, not the primary path. Each pass:

1. **PG side (for CueGUI):** the existing `RECOMPUTE_*_FROM_PROC` UPDATEs rewrite
   the PG accounting tables from `SUM(proc)` for scheduler-managed shows, so
   CueGUI's view stays within one interval of reality. (Scoped to managed shows;
   an empty managed set is a no-op, so it never clobbers Cuebot's accounting.)
2. **Store side:** one `SUM(proc)` snapshot, grouped by (show, alloc, folder,
   job), is overlaid on a **zero-baseline** of every enumerable key and written
   **absolutely** into the store — but each key's in-flight `pending` delta is
   carried forward: `counter = SUM(proc) + pending`.

The zero-baseline (every enumerable sub/folder/job key seeded at 0 before the
sums fold in) means a key that drifted stale-high and then drained to zero procs
is reset, rather than wedged at its stale value forever — `SUM(proc)` alone only
returns keys that still have procs.

### Why pending carry-forward is required

The recompute reads `SUM(proc)` (step 2 above) and then overwrites the in-memory
counter. Those two operations are not atomic with respect to the booking hot
path. Consider a booking that lands in the **straddle window** — after the
snapshot's `SELECT` has read the rows but before its `proc` INSERT is visible to
that read:

| t | Event | `proc` visible to snapshot | store `job.cores` |
|---|---|---|---|
| t0 | recompute `SELECT SUM(proc)` for job J reads 0 | 0 | 0 |
| t1 | `book(+8)` for J: store → 8, recorded as `pending` | 0 (INSERT not yet committed/visible) | 8 |
| t2 | recompute overwrites J from snapshot | 0 | **?** |

A naive absolute overwrite would write `0` at t2 and erase the just-booked 8
cores. The counter would then read low, and the *next* booking could push J over
its hard cap — the **one** way an absolute overwrite can over-book.

The carry-forward closes this: at t2 the store writes `SUM(proc) + pending =
0 + 8 = 8`. The booking survives.

### "When in doubt, keep the booking" is always safe

`pending` is cleared by `confirm`/`rollback`, which run only after the dispatcher
knows the `proc` outcome. So a delta is `pending` exactly while its `proc`
visibility is uncertain. If the snapshot happened to *already* include that
proc, the carry-forward double-counts it for one interval — the counter reads
**high**, which can only cause a too-conservative *under*-book, which the next
recompute corrects. The asymmetry is deliberate: over-counting is self-healing
and harmless to a hard cap; under-counting can breach a hard cap. When in doubt,
keep the booking.

This single invariant — `counter = SUM(proc) + Σ(in-flight bookings)` — subsumes
the old `acct:seq` compare-and-swap entirely. There is **no CAS, no retry loop,
no `acct:seq`, and no starvation floor.** The live store is the primary record;
the recompute only reconciles.

---

## The other backstops and seeds

### Limit reseed (cap-change backstop)

`accounting/limit_reseed.rs`, every `limit_reseed_interval` (default 5 min),
re-reads the five enforced caps from PG and writes them into the store. The
`acct_limit_change` NOTIFY propagates cueadmin changes immediately; this loop
heals any notification missed during a listener reconnect, within one interval.
Only the enforced caps are read (subscription burst, folder/job max cores+gpus).

### Bootstrap (blocking startup seed)

`accounting/bootstrap.rs` runs **before the scheduler accepts any work**: it
seeds the enforced caps (limit reseed), then the booked counters (recompute
reseed), from PG. Because the store is the only copy of this state, the gate is
mandatory — dispatching against empty counters would book every hard cap wide
open, and (because an unseeded burst reads as 0 = reject-all) would
simultaneously reject every subscription. The entrypoint runs the bootstrap to
completion before spawning the recompute, limit-reseed, and listener loops.

### Managed-flip seed

When a show becomes scheduler-managed *after* startup, `ManagedShowsCache`
performs a **blocking seed of both its caps and its booked counters before
publishing the show into the cache**. The booked seed is essential: a flipped show
often already has live Cuebot procs, so seeding the booked counters from
`SUM(proc)` first means the hot path enforces against real usage from the very
first booking, not against 0 (which would leave a full burst of headroom free →
over-book a hard cap). The booked seed is a one-shot absolute set per show — it
does not bump the recompute epoch or touch the settled buckets, so it cannot
interfere with the single recompute driver's begin/overwrite sequencing (the show
has no in-flight scheduler bookings yet, since the hot path no-ops for unpublished
shows). Until the seed lands the show is treated as Cuebot-managed (Cuebot keeps
booking it via PG) — strictly safer than flipping the hot path on against unseeded
state. If the seed fails, only that show's cache publish is deferred to the next
refresh; removals (shows that left the managed set) still apply immediately.

---

## Failure modes and drift

Every failure mode is **safe-direction**: a dropped or delayed signal can only
leave a counter reading *high*, which under-books (too conservative) and
self-heals. A hard cap can only be breached if a counter reads *low*, which only
the recompute-erase hole (closed by the [pending carry-forward](#why-pending-carry-forward-is-required))
or an unseeded counter (closed by the [blocking bootstrap and managed-flip
seeds](#the-other-backstops-and-seeds)) could cause.

| Failure | Effect | Recovery |
|---|---|---|
| `acct_release` NOTIFY missed (listener reconnecting) | Store missing a decrement → counter high → under-book | Next recompute (~15 s) overwrites from `SUM(proc)` |
| `acct_limit_change` NOTIFY missed | Store cap stale | Next limit reseed (~5 min) re-reads from PG |
| Scheduler dies between `book` and `proc` INSERT | Booked increment lost on crash (store is in memory) | Bootstrap reseed from `SUM(proc)` on restart |
| `proc` INSERT / RQD launch fails after `book` | `rollback` undoes the increment + pending | Immediate; recompute is a further backstop |
| Recompute snapshot straddles a live booking | Snapshot misses the proc | Carry-forward keeps the booking; never under-counts |
| Cuebot admin cap change | Store stale on that cap until NOTIFY/limit-reseed | `acct_limit_change` NOTIFY (instant) or limit reseed (~5 min) |
| `b_scheduler_managed` toggle mid-flight | Brief window of stale managed-set | Stale-true heals via recompute; stale-false defers to Cuebot (safe); managed-flip seed gates enforcement |
| Cuebot NOTIFY kill-switch off | No live releases/cap-changes → counters high → under-book | Recompute / limit reseed still heal; ops alerted by metric |

### CueGUI staleness

CueGUI reads the PG accounting tables unchanged. For scheduler-managed shows
they lag the live store by at most one recompute interval (~15 s) plus any
bookings since the last recompute. For Cuebot-managed shows they are
transactionally exact as before.

---

## The Cuebot kill-switch

A single property gates whether Cuebot emits the accounting notifications:

```properties
accounting.notify.enabled=true   # default; ${ACCOUNTING_NOTIFY_ENABLED}
```

With the flag **off**, Cuebot still deletes procs and updates caps
transactionally but emits no `pg_notify`. The scheduler's store then stops
receiving live releases and cap changes, so its counters only ever grow (reads
high) → it under-books → the recompute and limit-reseed loops heal it within
their intervals. This is the **safe** direction, so flag-off degrades
gracefully to backstop-only operation; it does not over-book.

Because flag-off is safe, there is **no startup deployment guardrail** that
refuses to run (the old Redis design had one because a disabled Redis publisher
*over*-counted). Instead, when scheduler-managed shows exist and the flag is off,
Cuebot logs a WARN and exposes a `cuebot_accounting_notify_disabled` metric for
ops visibility — utilization will sag (under-booking), but correctness holds.

The per-show `b_scheduler_managed` toggle remains the live operational rollback:
flip a show back to Cuebot-managed to take it off the scheduler entirely.

---

## The unit invariant: cores, not centicores

PostgreSQL stores cores as **centicores** (cores × 100; the `int_*cores*`
columns and `proc.int_cores_reserved`). The in-memory store works in
**unmultiplied cores** (1 = 1 core). Conversion happens only at the PG↔store
boundary:

- The recompute converts `SUM(proc)` centicore sums to cores
  (`centicores_to_cores`, via `CoreSize::from_multiplied`).
- The limit reseed converts caps to cores (`centicores_to_cores_cap`),
  preserving the `-1` unlimited sentinel.
- Cuebot converts to cores before emitting the NOTIFY payloads.

GPU fields are **not** multiplied — they pass through verbatim, including their
`-1` sentinel. Inside the store no centicore arithmetic ever happens; the hot
path is unit-clean.

---

## The N=1 assumption and the revisit trigger for N>1

The in-memory store is **not shared**. It assumes a single scheduler instance:
exactly one process owns the booked counters, so the booking check and increment
can be a single in-process critical section, and the recompute can overwrite
absolutely without coordinating with any peer. This is the assumption that makes
the whole design correct *and* makes the drift bug class go away.

This is a deliberate trade. The Redis design existed to allow N>1 schedulers to
share counters, but at this scale N=1 is expected for the foreseeable future and
the only thing N>1 would buy (splitting one show across instances) is not
needed.

**Revisit trigger:** before ever running more than one scheduler instance that
could book the same show. At that point the in-memory store is no longer a
single source of truth — two processes would each enforce against their own copy
and could jointly over-book a hard cap. Crossing N>1 requires re-introducing a
shared/coordinated counter (a shared store with an atomic check-increment, or a
partitioning scheme that guarantees no two instances ever book the same
subscription/folder/job), plus leader election for the recompute and
limit-reseed loops. None of that is in place today, and the code assumes it is
absent (see `managed_shows.rs` and the entrypoint notes).

---

## Source layout

| Path | Purpose |
|---|---|
| `accounting/mod.rs` | `AccountingService` facade; `apply_booking` / `confirm_booking` / `rollback_booking`; managed-show short-circuit |
| `accounting/store.rs` | In-memory counters + caps; the locked atomic `book`, `confirm`, `rollback`, `apply_release`, `overwrite_counters`, `set_caps`, `apply_limit_change` |
| `accounting/listener.rs` | `PgListener` on `acct_release` + `acct_limit_change`; payload parsing |
| `accounting/recompute.rs` | ~15 s `SUM(proc)` → PG tables (CueGUI) + store overwrite with pending carry-forward |
| `accounting/limit_reseed.rs` | ~5 min caps → store; the cap-change backstop |
| `accounting/bootstrap.rs` | Blocking startup seed (caps then counters) before dispatch |
| `accounting/managed_shows.rs` | Cached `b_scheduler_managed` set + blocking managed-flip seed |
| `accounting/booking_delta.rs` | Per-booking delta carried through the dispatch pipeline |
| `accounting/dao.rs` | PG queries for the snapshot, baseline keys, and cap tables |
| `accounting/error.rs` | `AccountingError::LimitExceeded` (the one hot-path failure mode) |
| `cuebot/.../service/AccountingNotifier.java` | Emits `pg_notify` for releases and cap changes |
| `cuebot/.../dao/postgres/ProcDaoJdbc.java` | Scheduler-managed branch in `procDestroyed`: DELETE proc + transactional release notify |
| `cuebot/.../dao/postgres/ShowDaoJdbc.java` | `b_scheduler_managed` cache + `setSchedulerManaged` |

## Glossary

- **Accounting vertices**: the resource pools a booking touches —
  subscription, folder, job, layer, department point. The scheduler **enforces**
  only subscription, folder, and job.
- **Booked counters**: the live "how much is currently reserved" `cores`/`gpus`
  the cap check reads, as opposed to limit fields (burst, max_cores).
- **Pending delta**: the subset of a counter still in flight — booked in memory
  but whose `proc` row may not yet be visible to the recompute snapshot. Carried
  forward across a recompute so the absolute overwrite cannot erase it.
- **Recompute**: the ~15 s loop that overwrites booked counters from
  `SUM(proc) + pending` and refreshes the PG tables for CueGUI.
- **Limit reseed**: the ~5 min loop that re-reads enforced caps from PG.
- **`acct_release` / `acct_limit_change`**: the two PG NOTIFY channels Cuebot
  emits transactionally for releases and cap changes.
- **Scheduler-managed show**: `b_scheduler_managed = true` — dispatch and
  hot-path accounting are owned by the Rust scheduler's in-memory store.
- **Cuebot-managed show**: `b_scheduler_managed = false` — Cuebot dispatches and
  updates the PG accounting tables transactionally; the scheduler's store is not
  consulted.
</content>
