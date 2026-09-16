---
layout: default
title: "September 15, 2026: Retiring the Distributed Scheduler"
---

# Retiring the Distributed Scheduler

### Why the standalone Rust scheduler is being removed, and why OpenCue Maestro replaces it

#### September 15, 2026

---

The **Distributed Scheduler** — the standalone Rust service announced in December 2025
(`rust/crates/scheduler/`, the `cue-scheduler` binary) — **has been removed from OpenCue.** It never
ran a production farm, and after a head-to-head evaluation against
[OpenCue Maestro](/docs/developer-guide/maestro/) we concluded it was not the design worth carrying
forward.

This post explains that decision honestly: what the Rust scheduler got right, where the two designs
genuinely diverged, and what the removal means if you were evaluating it.

## Two answers to the same problem

Both projects started from the same diagnosis, and it was the right one. Cuebot's legacy dispatcher
is **reactive and per-host**: every host report runs a heavy multi-table candidate query and books
one frame. Heavy database query load therefore scales with the number of hosts and the report rate,
and every booking is its own transaction taking row locks on the same handful of hot accounting
rows. The database, not the scheduler, is the ceiling.

From that shared premise the two designs diverged philosophically.

The **Distributed Scheduler** answered it as an *engineering* problem: make dispatch fast. A
standalone Rust service runs a continuous per-cluster loop, matches frames to hosts out of an
in-memory B-tree cache (O(log n) lookup), and moves resource-limit enforcement off Postgres locks
entirely into an in-process accounting store fed by `LISTEN/NOTIFY`. Host selection is pluggable:
a default first-fit saturation strategy, plus an opt-in E-PVM scorer that picks the host stranding
the least capacity.

**Maestro** answered it as a *scheduling* problem: decide better. It lives inside Cuebot and runs a
periodic tick — snapshot the whole farm, bucket hosts into a few spec groups, score every candidate
placement with a multi-resource E-PVM cost function, grant reservations with backfill for starving
wide jobs, draw candidates from a priority-weighted lottery, and land every booking for the tick in
one batched transaction.

Both credibly relieve the database. Only one of them changes what the farm actually decides.

## Why Maestro won

### 1. It solves the problem operators actually have

This is the heaviest point, and it is the one that is easy to miss.

Scoring picks a good host for **one frame**. Planning shapes the **whole farm**. The Rust
scheduler — under either strategy, including its E-PVM path — processes layers sequentially in
cluster round-robin against strict priority-ordered job queries. It has no reservations or backfill,
no anti-starvation guarantee, and no locality bonus. A 64-core frame sitting in a stream of 1-core
frames starves exactly as it does today: no mechanism ever drains a host toward it. Per-placement
scoring, however good, cannot hold a machine open for a wide job.

That gap is not academic — it is precisely the gap studios currently fill *with people*. Operators
hand-tune each layer's core request and tags ahead of time so the naive dispatcher behaves, and
reserve big machines for big jobs by convention. Maestro's reservations, backfill, priority lottery
and cache-locality machinery exist to retire that human rulebook. The Rust scheduler would have made
dispatch faster while leaving the rulebook exactly where it was.

### 2. Correctness by construction, not by repair loop

Maestro's keystone is that it holds **no durable state between ticks**. Each tick rebuilds its
entire picture from a fresh database snapshot; the database is the single source of truth. Failover,
self-healing and fire-and-forget launches all fall out of that one decision, and the worst failure
mode is one tick of *under*-booking — the direction you want to fail in production.

The Rust scheduler caches aggressively — host cache, accounting store, managed-shows cache, cluster
set — and each cache needs machinery to stay honest: an optimistic-timestamp checkout protocol, a
NOTIFY listener with reconnect handling, a periodic recompute loop with pending-delta carry-forward,
a limit reseed, a blocking bootstrap reseed, layer permits, cache expiry. Each mechanism is
individually sound. Collectively they are a large correctness surface that exists only because state
lives outside the database. Several of them are named *backstops for missed events*: the design
anticipates its own drift.

### 3. "Distributed" was a roadmap item, not a property

The in-memory accounting store is explicitly single-instance: a second instance booking the same
show would enforce caps against a separate copy of the counters and the two would jointly over-book.
There is no leader election, and a restart requires a blocking bootstrap reseed. The control module
that would coordinate multiple instances was always future work.

Maestro, meanwhile, runs on **every** Cuebot, with one elected leader per tick via a Postgres
advisory lock that Postgres releases the instant the holder's session dies. Failover is automatic
within a tick or two, with nothing to persist, migrate or replay.

As shipped, the Distributed Scheduler was the *less* distributed of the two.

### 4. Sustainable cost

The removal deletes roughly **20,000 lines of Rust** (~16,000 of source across 49 files, ~4,200 of
tests), a deploy unit, a Dockerfile, a CI stress pipeline, a Prometheus endpoint, ~15 tuning knobs,
a ~40-crate dependency tree, and a cross-repo contract in which Cuebot's Java release path and the
Rust accounting store had to stay semantically in sync — meaning every future change to booking or
release logic had to be reasoned about in two codebases and two languages.

Maestro is roughly 4,000 lines of Java in the codebase every Cuebot contributor already navigates,
with **no new deploy unit, no new service, no schema change, and no new on-call surface.** OpenCue's
contributor base is Java and Python; the pool that can confidently debug a lock-ordering bug in a
Rust accounting store is much smaller. Rust brings real benefits, and OpenCue is committed to it for
RQD — but a second language is a permanent maintenance tax that the scheduler did not need to pay.

### 5. The measured evidence

Maestro ships with a DB-backed simulator (`sandbox/maestro-sim/`) that is not a model of Cuebot —
it *is* Cuebot: a real Cuebot process and a real Postgres driven over gRPC by a fake render farm, so
every booking goes through the production path. Against a 1,553-host / ~57k-core farm it drove a
cold farm from idle to ~100% utilization in about 40 seconds, cut steady-state database traffic by
roughly an order of magnitude, and reduced worst-case rows fetched per completed frame from ~75,000
to ~1,000 versus the legacy dispatcher.

The Rust scheduler had smoke and stress suites, but never published a comparable end-to-end
farm-fill or database-load benchmark. That asymmetry mattered: one option's claims were reproducible
on the production code path, the other's were not.

## What we are keeping

Retiring the code is not the same as dismissing the ideas. Three are worth restating:

- **Moving the accounting check-and-increment off Postgres locks** remains the strongest structural
  answer to hot-row contention. Maestro's batched commit attacks the same contention from the other
  side — collapsing thousands of per-proc writes into a few dozen per tick — but the in-memory
  approach is the better long-term idea if the batched commit ever becomes the ceiling.
- **The GPU soft-reservation term** in the Rust E-PVM scorer steers non-GPU work away from GPU
  hosts. Maestro's exponential delta is zero on dimensions a layer does not use, so it does not
  currently protect idle GPU capacity from CPU work. This is worth porting.
- **Horizontal scale-out** is a genuine long-term architecture, and the Rust service was the natural
  chassis for it.

What would reopen the question: a farm, or a multi-facility tenancy shape, that demonstrably
outgrows a single leader's tick budget. Nothing about Maestro forecloses that path — both designs
use the same per-show ownership flag, so the migration story compounds rather than conflicts.

## What this means for you

**If you never deployed the Distributed Scheduler** — the overwhelming majority of deployments —
nothing changes. It was gated behind a separate service you had to run on purpose.

**If you were evaluating or piloting it**, note the following:

- The `cue-scheduler` binary, its crate, its Dockerfile, its sample config and its documentation are
  gone from the repository. The last release containing them is the one this post supersedes.
- Cuebot's side of the integration is gone too: the `LISTEN/NOTIFY` accounting publisher
  (`accounting.notify.enabled`) and the `dispatcher.scheduler_manages_resources` property, which
  told Cuebot to skip its own accounting writes for externally-owned shows. Cuebot now always owns
  its accounting tables.
- **Clear any stale per-show flags.** The `show.b_scheduler_managed` column stays — Maestro's
  per-show `managed` rollout mode uses it — but the legacy dispatch query still excludes flagged
  shows. A show left flagged with no scheduler owning it will simply strand. Run
  `cueadmin -scheduler-managed <show> off` for every show you handed to the Rust scheduler, unless
  you are deliberately handing that show to Maestro instead.
- Database migrations are untouched. `V44` (the scheduler's pending-query indexes) and `V45` (the
  `b_scheduler_managed` column) remain applied; migration history is never rewritten, and both are
  harmless.

**If you are looking for what to run instead**, Maestro is the answer, and it is off by default. It
rolls out per show via `maestro.enabled=managed`, takes the whole facility with
`maestro.enabled=facility`, and rolls back by setting the flag to `no` — no restart, no migration,
no new process. See the [OpenCue Maestro developer guide](/docs/developer-guide/maestro/) for the
design, the full configuration table, the operator-visible semantics change around priority, and the
known failure modes.

## A note on calling it

It is not comfortable to remove a substantial, well-built piece of engineering. The Distributed
Scheduler was carefully written, genuinely fast, and correct in the ways its authors set out to make
it correct. But "we already built it" is not an argument for shipping it, and carrying a second
scheduler in a second language — one that made dispatch faster without making scheduling smarter,
and that needed a coordinator it did not have to be what its name claimed — would have cost the
project more every year than it returned.

We would rather say so plainly than let it linger half-adopted.

---

Questions or disagreement? We would genuinely like to hear it:

- **Slack**: #opencue on [ASWF Slack](https://slack.aswf.io)
- **GitHub Discussions**: [OpenCue Discussions](https://github.com/AcademySoftwareFoundation/OpenCue/discussions)
