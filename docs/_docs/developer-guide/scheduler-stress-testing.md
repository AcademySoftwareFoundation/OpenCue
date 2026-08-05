---
title: "Scheduler Stress Testing"
nav_order: 102
parent: Reference
layout: default
linkTitle: "Scheduler Stress Testing"
date: 2026-06-12
description: >
  How to run, tune, and interpret the Rust scheduler's booking and accounting
  stress suite, locally and in CI
---

# Scheduler Stress Testing

## Running and interpreting the booking + accounting stress suite

---

## Overview

The stress suite (`rust/crates/scheduler/tests/stress_tests.rs`) exercises the
[Rust scheduler](/docs/developer-guide/scheduler/)'s full production dispatch
path at scale — `pipeline::run` end to end: in-memory accounting bootstrap →
cluster feed → pending-job query → host matching → dispatch (proc insert, host
ledger decrement, frame start) — against a deterministic, bulk-seeded farm.

It is both a **correctness gate** and a **benchmark harness**:

- **Correctness**: after each phase an audit cross-checks the scheduler's
  in-memory accounting counters against `SUM(proc)` in Postgres (the canonical
  record — see the [Scheduler Accounting Reference](/docs/developer-guide/scheduler-accounting/)),
  and verifies cap enforcement and ledger invariants.
- **Benchmark**: it reports booking throughput (frames/s over the active
  booking window), host-matching efficiency (wasted attempt %), host-cache hit
  ratio, and booking/rollback op counts.

The suite runs two phases in one process:

| Phase | Shape | What it proves |
|---|---|---|
| **drain** | Farm capacity comfortably exceeds demand (default: 1,200 hosts, 6,000 frames) | ≥90% of frames book; throughput measured; accounting stays exact under concurrency, including the force-rollback compensation path |
| **saturation** | Demand vastly exceeds tight subscription bursts and per-job core caps (default: 400 hosts, 3,000 frames, 150-core bursts) | The in-memory cap check is the binding constraint: bookings stop exactly at burst, caps are never breached, rejections flow through the hot path |

### Invariants the audit asserts

1. The in-memory counter for every enforced vertex (subscription, folder, job)
   the run touched matches `SUM(proc.int_cores_reserved)/100` cores and
   `SUM(proc.int_gpus_reserved)` GPUs for its grouping — the same grouping and
   centicore→core conversion the recompute loop uses. The suite pushes the
   recompute and limit-reseed loops out to a long interval, so agreement here
   proves the *dispatch hot path alone* (book + force-rollback) kept the store
   exact — reconciliation never got a chance to paper over drift.
2. Jobs with no bookings have no leaked counters.
3. Per-(show, alloc) booked cores never exceed the subscription burst.
4. Per-job booked cores never exceed `job_resource.int_max_cores`.
5. Host ledger: `int_cores - int_cores_idle == SUM(proc)` per host, never negative.
6. One `RUNNING` frame per proc row.
7. Trigger-maintained `job_stat.int_waiting_count` matches the frame table.
8. After teardown, zero `stress_%` rows remain in any table the suite touches.

### Load-bearing perturbation tests

Beyond the two throughput phases, the suite drives the failure modes the
in-memory design must survive:

- **Recompute straddle** — stall the recompute `SUM(proc)` query, fire a booking
  into the snapshot-straddle window, and assert the counter never ends below
  truth (the pending carry-forward invariant; the one way an absolute overwrite
  could under-count and over-book a hard cap).
- **Injected NOTIFY drops** — drop `acct_release` notifications under load and
  assert no hard cap is ever exceeded and counters converge to `SUM(proc)` once
  load stops (a missed release only ever reads high → under-book → heals).
- **Mid-load managed-flip** — flip a show scheduler-managed during saturation and
  assert the blocking caps seed prevents any over-book on the freshly-flipped
  show.

## Running locally

### Prerequisites

- A migrated Postgres on `localhost:5432` (`cuebot` / `cuebot_password`).
  From the repo root: `docker compose up -d flyway` (brings up `db` and applies
  migrations). If the Flyway image won't build in your environment (e.g.
  SSL-inspecting proxies break its package mirrors), apply the migrations
  directly — they are plain SQL:

  ```bash
  cd cuebot/src/main/resources/conf/ddl/postgres/migrations
  for f in $(ls V*.sql | sort -t V -k2 -n); do
    docker exec -i opencue-db-1 psql -q -v ON_ERROR_STOP=1 -U cuebot -d cuebot < "$f"
  done
  ```

The accounting store is in-process, so no external store (and no Docker daemon
for one) is required — a migrated Postgres is the only dependency.

### Run

```bash
cd rust
cargo test -p scheduler --features stress-tests --test stress_tests -- --nocapture
```

For meaningful benchmark numbers, use a release build:

```bash
cargo test -p scheduler --release --features stress-tests --test stress_tests -- --nocapture
```

### Tuning

| Env var | Default | Meaning |
|---|---|---|
| `STRESS_JOBS` | 300 | drain-phase job count |
| `STRESS_LAYERS` | 4 | drain-phase layers per job |
| `STRESS_FRAMES_PER_LAYER` | 5 | drain-phase frames per layer |
| `STRESS_HOSTS` | 1200 | drain-phase host count |
| `STRESS_TAGS` | 8 | drain-phase manual tag count |
| `STRESS_SAT_JOBS` | 150 | saturation-phase job count |
| `STRESS_SAT_HOSTS` | 400 | saturation-phase host count |
| `STRESS_DRAIN_TARGET` | 0.9 | fraction of drain frames that must book |
| `STRESS_STALL_SECS` | 30 | watchdog: pause jobs after this long without a new booking |
| `STRESS_TIMEOUT_SECS` | 600 | watchdog: per-phase hard timeout |

Seeding is deterministic for a given scale (fixed RNG seed), so consecutive
runs at the same scale book the same workload — diffs in throughput between
runs reflect the code, not the data.

### Reading the report

```text
================ phase: drain ================
frames     : 6000 seeded, 5988 dispatched (99.8%), waiting 6000 -> 12
throughput : 975.1 frames/s over a 6.1s booking window (wall 43.3s)
matching   : 3175 host attempts (41.9% wasted), 39 cluster rounds, host-cache hit 98%
accounting : 7452 booking ops, 5988 dispatches (metrics), 24040 booked cores, rejections [...]
audit      : OK
```

- **throughput** is measured from the first to the last `proc.ts_booked`, so it
  excludes the post-drain shutdown tail of the feed (the `wall` figure includes it).
- **booking ops** above the dispatch count means the compensation path ran:
  each failed dispatch costs one book plus one force-rollback. The audit
  passing alongside a surplus is a *positive* signal — rollbacks netted out.
- In the saturation phase, expect large `subscription=` rejection counts and
  every subscription pinned at exactly `burst/burst` cores.

### Cleanup guarantees

All database rows the suite creates are prefixed `stress_`. The suite sweeps
that prefix **before** seeding (so leftovers from a crashed earlier run never
skew results) and **after** the run, then asserts zero residue. The accounting
state is in-process and dies with the test, so it needs no cleanup. If a run is
killed hard (e.g. SIGKILL mid-phase), the next run's pre-sweep removes the
leftovers.

## CI integration

The suite runs in the
[`scheduler-stress-pipeline.yml`](https://github.com/AcademySoftwareFoundation/OpenCue/blob/master/.github/workflows/scheduler-stress-pipeline.yml)
workflow.

### When it runs

| Trigger | Scale | Purpose |
|---|---|---|
| Pull request touching `rust/crates/scheduler/**`, `rust/crates/opencue-proto/**`, `rust/Cargo.toml`, the Postgres migrations, or the workflow itself | defaults | Gate scheduler changes on booking/accounting correctness |
| Nightly (cron, master) | defaults | Catch drift from changes outside the paths filter; daily throughput data point |
| Manual (`workflow_dispatch`) | custom via inputs | Benchmark a branch at chosen scale |

### When it deliberately does not run

- **PRs that don't touch the scheduler or schema** (Python, CueGUI, OpenCueWeb,
  docs, …). The suite needs a migrated Postgres, a Docker daemon, and several
  minutes of runner time; for those changes it produces zero signal.
- **As a performance gate.** Shared CI runners have noisy CPU/IO, so the
  workflow never asserts on frames/s — throughput is published in the job's
  step summary (and the full log as an artifact) for humans to eyeball trends.
  Benchmark conclusions should come from local release-mode runs on quiet
  hardware.

### What fails the job

Only correctness regressions: accounting drift between the in-memory store and
Postgres, a cap breach, booking liveness failures (drain below target, or a
saturated farm producing no rejections), a phase that never converges
(hard-timeout), or test data left behind after cleanup.

### Launching a manual benchmark run

GitHub → Actions → *OpenCue Scheduler Stress Pipeline* → *Run workflow*, then
optionally override the job/host/frame counts and timeout. Results appear in
the run's step summary; the complete log is attached as the
`scheduler-stress-output` artifact (kept 30 days).

## Scope and limitations

- **RQD is not exercised.** The suite runs in `dry_run_mode`: the full booking
  path executes (in-memory book, proc insert, host ledger, frame start) but no
  gRPC launch is sent. Frame *completion* and the Cuebot release path are out of
  scope — see the [Scheduler Accounting Reference](/docs/developer-guide/scheduler-accounting/)
  for how releases are reconciled. (The injected-NOTIFY-drop test simulates the
  release-feed behaviour without a live Cuebot.)
- **Only scheduler-managed shows** (`show.b_scheduler_managed = true`) are
  covered; Cuebot-managed accounting is Cuebot's test territory.
- The recompute / limit-reseed loops are pushed to a long interval for the two
  throughput phases (see invariant 1) so the hot path is audited in isolation;
  the recompute straddle and managed-flip perturbation tests drive them directly.

## Schema gotchas the suite encodes

These bit during development and are asserted/documented in the test code —
keep them in mind when extending the seeding:

- `alloc.str_tag` is `VARCHAR(24)` and `host.str_name` is `VARCHAR(30)`:
  generated names must stay short.
- The pending-job query `INNER JOIN`s `folder_resource`: a folder without that
  row makes every job in it silently unbookable.
- The `vs_waiting` view requires `job_resource.int_max_cores - int_cores >= 100`
  (centicores): `int_max_cores = 0` does **not** mean "unlimited" on the query
  path — use a large value instead.
