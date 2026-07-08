# Scheduler (Planner)

A whole-farm scheduler for OpenCue, gated behind `scheduler.enabled`
(default **off**). It is an alternative to the legacy per-host dispatcher.
When enabled it owns dispatch and the legacy `BookingQueue` path is
suppressed. Placement decisions are made single-threaded over an in-memory
snapshot; only the per-host plan reads run in parallel (see section 4).

The keystone of the design is that the planner is **stateless between ticks**:
each tick re-derives its entire picture from a fresh database snapshot and keeps
no booking state across ticks — the database is the single source of truth.
Fire-and-forget launches, instant failover, and self-healing after a crash all
fall out of that one decision (see the keystone note in section 2, and section 4).

This document explains what it does, how it works, the concurrency model
that keeps it correct, how to configure it, and what is planned next.

---

## 1. Background: dispatcher vs scheduler

The legacy path is a **dispatcher**. When a host reports in, it runs
`findDispatchJobs(host)` (a heavy multi-table join) and books the first
frame that fits, in priority order, one host at a time. It never sees more
than one host at once, so it cannot reason across the farm: it cannot hold
a big machine open for a wide job that is queued, or steer a small frame
onto a small machine instead of wasting a big one.

In practice that gap has been filled outside Cuebot, by people: operators
hand-tune each layer's core request and tags ahead of time so the naive
dispatcher behaves. That works, but it means humans do most of the real
scheduling, following a hand-maintained, per-show rulebook.

A **scheduler** makes those decisions itself. It takes a snapshot of the
whole farm each cycle, scores every candidate placement by how much
capacity it would strand, holds reservations for work that would otherwise
starve, and books accordingly. That is what this component does.

---

## 2. Architecture: the tick loop

The scheduler runs a periodic tick (`runTick` → `doTick`). Each tick:

1. **Snapshot**: read all bookable hosts in one query (`readBookableHosts`,
   `SELECT_BOOKABLE_HOSTS`). Hosts that are UP, OPEN, and have at least the
   minimum bookable cores.
2. **Group**: bucket hosts by spec key `(alloc, normalized_tags, os,
   has_gpu)` (`groupByHostSpec`). On a homogeneous farm this is a handful of
   groups, which is what collapses the per-host query storm into a few
   queries per tick.
3. **For each group:**
   1. **Candidate query**: one query per group
      (`readLayerCandidatesForGroup`, `SELECT_CANDIDATES_FOR_GROUP`) for the
      dispatchable layers that match the group, ranked by a **priority-weighted
      lottery** (§3.5), not a strict priority sort.
   2. **Dispatch** (`dispatchGroupWithScoring`): for each candidate in that
      lottery order, score every fitting host, pick the lowest score, record the
      placement, and decrement the in-memory snapshot. A candidate that stays
      blocked long enough and is wide enough records a reservation *request*.
4. **Grant reservations**: after all groups, process the requests
   highest-priority-then-widest and reconcile each grantee's reservation count
   under the per-class and max-grantees caps (section 3.2).
5. **Commit**: read each recorded placement's frames in parallel by host
   (`planHost`, read-only), write them all in one batched transaction
   (`startFramesAndProcsBatch`), then fire the RQD launches fire-and-forget.
6. **Sweep**: drop reservations whose layer no longer appears in any
   candidate set.

Steps 1-4 run single-threaded, so the decisions never race. The only
parallelism is in step 5's plan-phase reads (one task per host); the write is a
single batched commit and the launches fire afterward fire-and-forget.

### The keystone: stateless between ticks

The planner holds **no durable booking state**. Each tick rebuilds its world from
the fresh host snapshot (step 1) and the per-group candidate queries (step 3); the
only thing carried across ticks is the soft reservation map, and even that is just
a hint the planner rebuilds from the database within a tick or two. **The database
is the single source of truth.** Three properties fall out of that one decision —
and they are why the rest of the design stays simple:

- **Fire-and-forget launches.** The launch outcome never feeds back into planning
  state, so the tick never waits on RQD. A dropped or lost launch leaves a frame
  RUNNING in the DB that RQD never received; the orphaned-proc reaper resets it and
  the *next* snapshot re-reads the corrected state. Launch latency never gates
  booking (sections 4 and 7).
- **Stateless failover.** The leader keeps only the advisory lock and the in-memory
  reservation hint. If it dies, the next Cuebot takes the lock and reconstructs an
  identical picture from the DB within a tick or two — nothing to persist, migrate,
  or replay.
- **Self-healing.** Any transient inconsistency — a partial commit, a lost launch,
  snapshot drift — is erased by the next snapshot. Failures bias toward
  *under*-booking for one tick, never over-booking or lost work.

The cost is the full host snapshot every tick (the dominant read load, section 5).
That is the deliberate trade: **pay a re-read each tick in order to own no state.**

### Operational footprint

Owning no durable state keeps the planner small and cheap to run. It lives
**inside Cuebot** — no new deploy unit, no separate service to run or fail over,
no new infrastructure, and no schema migrations. It is gated by a single flag
(`scheduler.enabled`) and rolled back by flipping that flag off. The whole thing
is ~3,700 lines, almost all in four new files (the planner, a value type, this
doc, and a test), with ~16 existing files lightly touched. There is nowhere to
keep live state, no process to run it, and nothing to rebuild on failover — the
database it already uses is the only state there is.

---

## 3. Components

### 3.1 Placement score (multi-resource E-PVM)

`placementScore(host, layer)`, lower is better. It is the **marginal cost**
of placing one frame on a host, under a convex potential summed over every
host and every resource dimension:

```
C        = sum_hosts sum_D  e^( used_D / total_D )
score(h) = sum_D  W_D * ( e^(after_D/total_D) - e^(before_D/total_D) )
           before_D = total_D - idle_D        (currently reserved)
           after_D  = before_D + layer.min_D  (with this frame added)
```

We pick the host with the smallest score. Because the exponent is the
**utilization fraction** `used_D/total_D`, the score is dimensionless and
free of host-size bias, and the convex `e^x` makes a dimension that is
already near-full (e.g. a host with idle cores but saturated memory) cost a
great deal more to load further. Default weights: `W_CORES=1`, `W_MEM=1`,
`W_GPUS=4`, `W_GPU_MEM=1`, cores and memory equal; GPUs weighted higher so a
GPU layer strands the least GPU capacity.

This is **E-PVM / opportunity cost** (Amir, Awerbuch, Barak, Borgström &
Keren 2000; multi-resource in Verma et al., Borg, EuroSys 2015). It is a
load-**balancing** heuristic, not bin-packing: the same frame is a smaller
fraction of a larger host, so big hosts are filled first but only until their
fraction catches up. Under a sustained backlog this drives every host toward
the **same utilization percentage**, so a 128-core host carries ~8× the
frames of a 16-core host instead of sitting idle.

**Co-locality.** The score also carries a locality bonus. The legacy reactive
path rebooked the next frame of a job onto the same proc the instant a frame
finished, keeping a job's frames together on a machine (cache coherence:
textures, geometry, KSM-shared pages, warm filesystem cache). The planner
unbooks a completing proc instead, so to preserve that it subtracts
`scheduler.locality_bonus` (default 8.0) from a host's score when the host
already runs at least one frame of the candidate's layer, read once per tick
as a host->layer affinity map (`readHostLayerAffinity`). A freed core is then
preferentially refilled by the same layer on the next tick, so a layer stays
clustered on the hosts it already occupies instead of scattering across the
farm; a multi-frame layer keeps at least one proc on its host between ticks,
so the signal persists without tracking individual completions. The bonus is
sized to outweigh the marginal stranding terms (which are ~e^util, single
digits) but it is applied AFTER fit and reservation filtering, so it can never
place a frame that does not fit or override a reservation. Disable with
`scheduler.locality_enabled=false`.

### 3.2 Reservations (EASY/Maui backfill)

A wide layer can be starved indefinitely by a stream of small frames: every
core that frees is grabbed by a one-core frame before enough cores ever
accumulate on a single host. The classic fix is **reservations with
backfill** (Lifka 1995, the EASY scheduler; Jackson, Snell & Clement 2001,
Maui): give the blocked wide job a future claim on a host, let that host
drain toward it, and let shorter low-priority work run on the draining host
in the meantime as long as it finishes before the host is needed.

The planner implements this with four guards so reservations never freeze the
farm reserved-but-idle (the classic low-utilization failure mode of naive
conservative backfill):

- **Blocked-debt gate (when may a layer reserve).** Each layer carries a
  leaky bucket of net blocked time (`blockedDebtMs`): it grows while the
  layer is blocked (waiting frames, dispatched nothing this tick) and decays
  1:1 while it places. A layer qualifies to reserve only once its debt
  reaches `reservationBlockMs` (default 5 min). Using net debt rather than a
  "continuously blocked" timer means a job that only *crawls*, winning the
  odd gap that would reset a continuous timer, still earns a reservation.
- **Width gate (which layers may reserve), always on.** A reservation exists
  to drain a host for a frame too wide to fit otherwise. A layer may reserve
  only if its per-frame core request is at least
  `RESERVATION_MIN_HOST_FRACTION` (0.5) of the **largest** host in its group.
  Without this gate the narrow small-frame stream, which never actually
  needed a reservation because it runs the instant any core frees, floods the
  reservation budget and locks out the wide jobs the budget was meant for.
  This gate is not configurable.
- **Capacity cap.** Reservations may hold at most `reservationMaxFraction`
  (default 0.5) of the hosts that can fit the layer, and at most
  `scheduler.reservation_max_grantees` (default 8) distinct layers may hold
  reservations farm-wide. So a class of machines can never be fully reserved,
  and the farm cannot deadlock on reservations. Granting is priority-first
  (then widest-job-first), so high-priority blocked work gets first claim on
  the limited budget.
- **Drain guard.** A reserved host that has not yet drained enough cores for
  its owner (`idle < owner.coresMin`) refuses all backfill, even work that
  would finish in time. Otherwise backfill keeps refilling the gap the host
  is trying to open and the owner never gets in.

Backfill itself (`backfillAllows` / `backfillFits`) is the EASY no-delay
test: a strictly-lower-priority frame may borrow a draining host's free cores
only if its runtime estimate (from `layer_usage`) shows it finishing before
the host is needed; a frame with no runtime history is refused, since its
finish time cannot be bounded. Borrowing never takes ownership.

Supporting machinery: `reservationAllows` decides whether a reservation lets
a layer through (no reservation, owns it, or the existing one is strictly
lower priority and gets overridden on successful dispatch);
`reconcileReservationsForLayer` brings a qualified layer's reservation count
toward its pending frame count under the caps; `pickReservationTarget`
chooses the host likely to free soonest (fewest running procs) among hosts
that fit the layer when fully idle.

The reservation map persists across ticks. The invariant: a host's
reservation belongs to the highest-priority layer that has claimed it. The
end-of-tick sweep drops reservations (and blocked-debt) for layers that left
the dispatchable set.

This is the mechanism that retires the human-driven "save this machine for
the big job" practice.

### 3.3 Plan reads and batched commit

The planner never writes bookings during placement; it just records the
`(host, layer)` pairings it chose. After all groups, `doTick` reads each
pairing's frames in parallel by host (`planHost`, read-only, on a small read
pool), then writes every booking for the tick in one batched transaction
(`startFramesAndProcsBatch`: batched frame UPDATE + proc INSERT + host UPDATE).
Frames lost to a `frame.int_version` race are dropped from the batch and retried
next tick. The RQD launches fire afterward fire-and-forget on a launch pool, so
a slow RQD never stalls the tick. Each frame reserves exactly the layer's requested cores: `planHost` builds
procs with the dispatcher's thread-mode idle-core expansion (grab-idle) turned
off, so the cores committed match the cores the planner scored and decremented.
Grab-idle would silently reserve more than planned and corrupt the snapshot;
the planner fills hosts by planning several placements, not by one frame
ballooning to consume the box.

This keeps the *decisions* on one thread (no races) while parallelizing the part
that dominates tick time as the farm fills: the per-host reads. The writes stay
one batched, atomic commit.

### 3.4 Leader election

Only one Cuebot may plan at a time. `runTick` takes a Postgres advisory lock
(`pg_try_advisory_lock`); a Cuebot that does not hold it returns
immediately. The lock is released at the end of each tick and is released
automatically by Postgres if the leader's session drops, so failover is
automatic. A new leader starts with an empty reservation map and no
persistent state to migrate; placement resumes immediately. One caveat: the
block-time bucket is in-memory too, so after a failover reservations re-arm
only as blocked layers re-accrue `reservation_block_seconds` — over that
window, not a tick or two.

### 3.5 Priority: a weighted lottery (rate, not rank)

The candidate query does **not** order strictly by priority. It draws a
**priority-weighted lottery** — Efraimidis-Spirakis weighted reservoir sampling:
each eligible layer gets a random key `power(random(), 1.0 / GREATEST(priority, 1))`
and the top `layer_candidates_per_group_max` by that key are taken
(`ORDER BY power(random(), 1.0/…) DESC LIMIT …` in `SELECT_CANDIDATES_FOR_GROUP`).
A layer's expected selection rate is proportional to its priority, so **priority
is a rate, not a rank.** This is the single most operator-visible change from the
legacy dispatcher, which sorted strictly by `priority DESC` and so gave every free
core to the highest-priority work until it drained — starving everything below it
while a high-priority backlog stayed full.

**What this means for operators.** Priority now buys a *share*, not dominance. A
show at priority 120 vs one at 100 wins roughly `120/(120+100) ≈ 55%` of the
contested selections, not 100%. Two consequences:

- **Re-spread clustered values.** If your priority numbers were calibrated for
  rank semantics they often cluster in a narrow band (e.g. 90–110). Under the
  lottery that band barely differentiates — 110 vs 90 is only a `≈1.22×` rate
  edge. To get meaningful separation, spread the values (e.g. 50 / 100 / 400).
- **It is a rate, not a guarantee.** The *realized* share of completed frames also
  depends on backlog composition: a stream with far more waiting layers is
  over-represented in the candidate pool, so it lands more selections than its
  bare priority ratio suggests, and a thin low-priority stream lands fewer. The
  firm guarantee the lottery provides is **anti-starvation** — any eligible layer
  keeps a nonzero, priority-weighted chance every tick and never waits behind a
  saturating higher-priority backlog forever. `GREATEST(priority, 1)` floors the
  weight so priority 0 or negative still draws the minimum nonzero share.

**Reservations are the exception.** Reservation *granting* stays strict
priority-first (the requests are re-sorted by priority before the per-class caps
fill; §3.2), so the lottery changes only booking *order*, never which wide job
gets rescued first.

---

## 4. Concurrency model

The planner reasons over an in-memory snapshot while commits and external
events change the database in the background. This is safe by design.

**Single-booker invariant.** Three guards ensure nothing competes to
*consume* capacity behind the planner's back:

1. `tickInFlight` compare-and-set, one Cuebot never overlaps its own ticks.
2. Leader advisory lock, only one Cuebot plans across the deployment.
3. In `facility` mode `scheduler.enabled` suppresses the legacy `BookingQueue`
   enqueue in `HostReportHandler`; in `managed` mode the legacy dispatcher keeps
   running but its query excludes `b_scheduler_managed` shows, so the two never
   book the same show.

So the only things that can change host state during a tick are:

- **The planner's own commits**: already accounted for, because the planner
  decrements its in-memory snapshot for each decision as it makes it.
- **External frame completions**: these only *free* cores, i.e. the
  snapshot is conservative (it under-counts free capacity). Safe.

**Snapshot drift is a quality issue, not a correctness one.** The commit
treats the database as the source of truth, not the snapshot:
`startFramesAndProcsBatch` books against real current state, with two hard
guards underneath:
- the atomic host update
  `UPDATE host SET int_cores_idle = int_cores_idle - ? WHERE ... >= ?`,
  which makes physical over-booking impossible, and
- the `frame.int_version` optimistic lock, which rejects any overlapping
  frame grab. A frame that loses the version race is dropped from the batch
  (comparing affected-row counts) and stays WAITING for the next tick.

If the batch books fewer frames than the planner estimated (a host had less
room than the snapshot, or a frame lost its version race), the planner merely
over-decremented its in-memory copy and leaves that host slightly
under-packed for the rest of the tick. The next tick's fresh snapshot
corrects it. Failures bias toward **under-booking** (waste a little capacity
for one tick), never over-booking.

**Drift is bounded to a single tick** because the batched commit is
synchronous on the planner thread: when it returns, the database fully
reflects this tick's bookings, so the next snapshot re-grounds on reality.
Only the RQD launches run afterward, fire-and-forget on the launch pool, so a
slow or sluggish RQD never stalls the next tick. There is no commit worker
pool and no drain barrier to wait on; the single transaction is the
synchronization point.

---

## 5. Performance

The planner is built to take load off the database, the scaling bottleneck of
the legacy path, and to fill capacity the instant it exists.

**It fills the farm immediately.** Because the planner places across the whole
farm in a single tick, rather than booking one host at a time as each host
reports, it saturates idle capacity in one pass instead of waiting for a report
from every host. From a cold start in the DB-backed simulator it drove 1553
hosts (~57k cores) from idle to ~100% utilization in about 40 seconds, booking
on the order of hundreds of frames per second, and holds a steady backlog at
full utilization thereafter. The legacy report-driven path can only book a host
when that host next reports, so a cold farm fills at the report rate.

**One batched commit instead of a transaction per frame.** The legacy path
books each frame in its own `@Transactional` call, so booking N frames is N
transactions, every one taking row locks on the same few hot accounting rows
(subscription, folder_resource, point, layer_stat, job_stat). Under load those
transactions serialize on the shared rows and per-transaction BEGIN/COMMIT
overhead dominates. The planner lands every booking for a tick in a single
transaction (`startFramesAndProcsBatch`, section 3.3): a batched frame UPDATE (a
VALUES join keyed on `(pk_frame, int_version)`), a multi-row proc INSERT, one
summed `UPDATE host` per host, and the resource-counter deltas accumulated in
memory and flushed as one UPDATE per hot row instead of one per proc. Thousands
of contended per-proc writes collapse into a few dozen, and a deadlock-free lock
order (layer_stat then job_stat, both sorted; `lockStatRowsForBatch`) keeps the
batch from ever deadlocking against a concurrent frame completion. The effect is
a dramatic drop in row-lock contention on exactly the rows every booking and
every completion must touch.

**Query count scales with host-spec groups, not hosts.** The legacy dispatcher
is reactive and per-host: every host report runs `findDispatchJobs(host)`, a
heavy multi-table join, so the count of heavy candidate queries grows with the
host count and the report rate, a per-host "query storm" that worsens as the
farm grows. The planner is proactive and farm-wide: one host-snapshot query per
tick, hosts bucketed into a few static spec groups, then one candidate-layer
query per group. On a homogeneous farm that is O(G) heavy queries per tick
(G = distinct host specs, a small constant) instead of O(H) per report cycle
(H = hosts), so heavy DB query load stops scaling with farm size. The only
per-host work left is the read-only plan phase, which is light and runs in
parallel; placement scoring is O(candidates x hosts), but that is in-memory
arithmetic over the snapshot, not database work.

**Roughly 10x less DB traffic overall.** Together these move the design from "a
transaction per booking decision plus a heavy join per host report" to
"in-memory planning with one batched commit per tick." In the DB-backed
simulator that is about an order of magnitude less database traffic in steady
state, and more than that on the worst-case per-frame row-fetch: the legacy path
fetched on the order of ~75,000 rows per completed frame, the planner ~1,000.
The database is still the remaining ceiling, not the planner, but the planner
already takes most of the load off it.

---

## 6. Configuration

| Property | Default | Meaning |
|---|---|---|
| `scheduler.enabled` | `no` | Rollout switch: `no` (off, legacy owns every show), `facility` (planner owns all shows, legacy BookingQueue globally suppressed), or `managed` (planner owns only shows flagged `b_scheduler_managed=true` -- set per show via the show API -- legacy keeps the rest). Back-compat: `true`=facility, `false`=no. |
| `scheduler.read_pool_size` | = launch pool size | Threads for the parallel per-host plan reads (read-only, DB-bound). |
| `scheduler.launch_pool_size` | `8` | Threads for the fire-and-forget RQD launches after the batched commit. |
| `scheduler.launch_queue_size` | `16384` | Bound on queued launches; on overflow a launch is dropped and recovered by RQD report reconciliation. |
| `scheduler.layer_candidates_per_group_max` | `2000` | Cap on candidate layers fetched per group per tick. |
| `scheduler.reservations_enabled` | `true` | Enable reservations and backfill. When off, pure placement scoring. |
| `scheduler.reservation_block_seconds` | `300` | Net blocked time a layer must accrue before it may reserve. |
| `scheduler.reservation_max_fraction` | `0.5` | Max fraction of a layer's fitting hosts that reservations may hold. |
| `scheduler.reservation_max_grantees` | `8` | Max distinct layers holding reservations farm-wide. |
| `scheduler.backfill_enabled` | `true` | Allow lower-priority frames to backfill draining reserved hosts. |
| `scheduler.locality_enabled` | `true` | Prefer hosts already running the layer (co-locality / cache coherence). |
| `scheduler.locality_bonus` | `8.0` | Score bonus for a co-located host. Applied after fit/reservation filtering, so it never overrides them. |
| `scheduler.stat_interval_seconds` | `300` | Cadence of the consolidated INFO `Scheduler stat:` line (planner health, farm fill, throughput, reservations). Lower it for live debugging. |
| `dispatcher.job_frame_dispatch_max` | `8` | Max frames of one job booked onto a host per tick. |
| `dispatcher.host_frame_dispatch_max` | `12` | Max frames booked onto a host per tick. |

The reservation **width gate** (`RESERVATION_MIN_HOST_FRACTION`, 0.5 of the
largest host in a group) is deliberately a fixed constant, not a property:
loosening it reintroduces the small-frame flooding it exists to prevent.

No schema changes. The only new SQL is the host-snapshot query and the
per-group candidate query, both against existing tables and indexes.

**Rollback** is a single flag: set `scheduler.enabled=no` and the legacy
dispatcher resumes. Progressive rollout works the same way in reverse: in
`managed` mode, clearing a show's `b_scheduler_managed` flag hands it straight
back to the legacy dispatcher with no restart.

---

## 7. Failure modes

- **Commit collision** (`frame.int_version` / resource guard): the frame is
  dropped from the batch, stays WAITING, picked up next tick. Logged at debug.
- **Leader loss** (session drop): the advisory lock releases automatically;
  another Cuebot becomes leader on its next tick. Placement resumes at once,
  but reservations re-arm only as blocked layers re-accrue
  `reservation_block_seconds` (the block-time bucket is in-memory).
- **Slow batched commit**: the commit is synchronous, so a slow transaction
  delays the next tick directly (no worker pool hides it). This is the one
  place where DB latency gates the tick rate; the future-work batching and
  row-fetch reductions (sections 8 and 9) target it.
- **Slow RQD launch**: absorbed by the fire-and-forget launch pool; on a full
  launch queue the launch is dropped and recovered by RQD report
  reconciliation, so it never stalls the tick.
- **Empty snapshot** (no bookable hosts): tick is a no-op; reservations are
  left intact.
- **Spec-group explosion**: if the host-spec group count approaches the host
  count (commonly a host name leaking into the tag set), planning degrades to
  one candidate query per host, the very storm grouping avoids. The scheduler
  logs a throttled WARNING (at most once every few minutes) so it is caught
  without flooding the log.
- **Bare-hostname tag pins are not honored**: cuebot auto-adds each host's own
  name as a tag, and `normalizeTags` strips it from the group key (that is what
  prevents the group explosion above). As a result a layer tagged with *only* a
  bare hostname (`layer.tags == "<hostname>"`, the legacy exclusive-pin idiom)
  matches no group and never dispatches under the scheduler — its frames sit
  `WAITING`. The legacy dispatcher honors such pins (it matches the host's raw
  tags), so this is a silent difference for `scheduler.enabled` shows. A layer
  that carries a shared tag alongside the hostname still dispatches on the shared
  tag. If exclusive hostname pinning is needed, keep those shows on the legacy
  dispatcher (or route via a dedicated allocation/tag instead of a host name).

**Observability.** Per-tick detail is DEBUG; INFO carries one consolidated
`Scheduler stat:` line per `scheduler.stat_interval_seconds` (default 5 minutes):

```
Scheduler stat: win=300s ticks=920 skipped=0 lockLost=12 avgTick=556ms maxTick=1840ms
  | farm hosts=1553 idleHosts=9 cores=57088 idleCores=74 util=99.9% groups=5
  | flow committed=98210 planned=104900 raceLost=6690 launchDropped=0
  | resv held=52 granted=31 reqs=11 backfilled=88
```

It groups planner health and HA leadership (ticks won, `skipped` = fired while
the previous tick still ran, `lockLost` = another Cuebot held the lock, avg/max
tick), farm fill (hosts, idle hosts, cores, idle cores, utilization, host-spec
group count), throughput and loss (committed procs, frames planned, `raceLost` =
frames lost to the version race, RQD launches dropped), and reservation/backfill
activity (held, newly granted, requested, backfilled). Every Cuebot emits it,
leader or standby, so a standby that never wins the lock still heartbeats
(`ticks=0`, `lockLost` high), distinguishing a standby from a dead process. The
line is meant to be pasted straight into a bug report.

---

## 8. Simulator (scheduler-sim)

The scheduler ships with a full DB-backed simulator under `scheduler-sim/`. It
is not a model of Cuebot, it *is* Cuebot: a real Cuebot process and a real
Postgres, driven over gRPC by a fake render farm, so every booking goes through
the exact production path (the real Scheduler, the real SQL, the real
frame-complete handler). That makes it the integration test unit tests cannot
be, and the place to measure behaviour that only shows up under load.

One command brings the whole stack up from nothing:

    scheduler-sim/simulate.py --mode new --feed 240 --metrics 220

It initdb's a Postgres cluster, applies the cuebot schema (Flyway migrations,
tracked so a cluster that survives across runs still picks up new ones), seeds
it, builds cuebot, registers the farm, starts a fake RQD plus a continuous
status reporter, feeds a workload, prints live metrics, and tears the run down
on the next invocation. Runs are reproducible (seeded RNG) and need no manual
setup on a fresh box.

What it reproduces faithfully:

  - **A real farm's shape.** 1553 hosts and ~57k cores across three real host
    classes (jaime 128c, ram 32c, elk 16c), with realistic usable-memory cuts
    for the OS, RQD and cache, so memory binds, not just cores.
  - **A production-shaped workload.** Per-layer core counts, memory and frame
    durations are sampled from real-farm CSV distributions, with heavy-tailed
    (lognormal) per-layer memory.
  - **A concurrent driver.** Frame completions and host status are reported in
    parallel, the way thousands of independent RQDs do, so a slow serial
    reporter cannot accidentally flatter a worse scheduler.

What it can simulate (the knobs):

  - `--mode new|old`: A/B the new scheduler against the legacy dispatcher on an
    identical workload.
  - `--feed` / `--jobs`: a sustained saturated backlog or a fixed job set, for
    steady-state utilization and drain time.
  - `--compress`: scale frame durations to find the utilization plateau and the
    cuebot/DB frame-lifecycle ceiling.
  - `--strand`: the starvation test, inject wide 64-core jobs (mixed equal/high
    priority) and watch them strand or get rescued by reservations and backfill.
  - `--reservations`, `--reservation-block-seconds`, `--reservation-max-fraction`,
    `--reservation-max-grantees`, `--no-backfill`: exercise the full EASY/Maui
    reservation and backfill machinery.
  - `--mem-heavy`: the low-utilization test, flood the farm with small,
    single-threaded, memory-hungry jobs so RAM binds and cores strand; the GB
    value dials the plateau (around 16 GB gives ~27% core utilization, 32 GB
    ~17%, while memory pins near 100%).
  - `--tags`: the production capability-routing model (size classes tied to host
    types).
  - `--gpu F`: a fraction of layers become GPU layers (few cores + 1 GPU + GPU
    memory), runnable only on GPU hosts.
  - `--mem-failure-rate`: inject OOM failures so cuebot bumps layer memory and
    requeues, exercising the retry path.
  - `--hosts`: shrink the farm to a few machines for legible, watchable debugging.

What it measures, live (`live_stats`): real core utilization (cores actually
backing a frame), running/waiting/orphaned-proc counts, frames completing and
booking per second, Postgres commits per second, cache-hit ratio and connection
states, per-priority big-job stranding, and a DB-load view (transactions and
rows fetched per completed frame, busiest tables). That is how the numbers in
section 5 was produced.

See `cuebot/scheduler-sim/Scheduler-simulator.md`
for what the simulator does and the full flag reference.

## 9. Testing

An offline simulator that A/B tests the legacy dispatcher and this planner
against a production-shaped workload lives on the `sim` branch under
`benchmarks/sim_cpp/`. It models the workload service
mix, the operator core/tag pre-pass, KSM co-location, and simulated DB time.
Use it for algorithmic experiments; use a real small-facility trial for
production validation.
