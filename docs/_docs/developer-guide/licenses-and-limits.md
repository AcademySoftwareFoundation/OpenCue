---
title: "Licenses and Limits"
nav_order: 104
parent: "Developer Guide"
layout: default
linkTitle: "Licenses and Limits"
date: 2026-09-02
description: >
  Host-based limits, external license reporting, failure-driven layer discovery, and how the
  dispatcher minimizes the farm's license footprint
---

# Licenses and Limits

## How OpenCue counts, reports and minimizes third-party license usage

---

## Overview

A **limit** is a named cap that a layer can be bound to. Historically OpenCue counted one token per
running frame, which is the right model for a resource consumed by a process — but the wrong model
for the licenses most studios actually care about.

This guide covers the extension of that system into real license management:

- A limit declares **how it counts**: per frame (`FRAME`) or per host (`HOST`).
- An external reporter can feed Cuebot the **license server's own view**, including which hosts hold
  a token, so licenses drawn outside the farm are accounted for.
- The dispatcher actively **minimizes the number of machines** the farm spreads a license across,
  rather than merely staying under a cap.
- Layers that need a license are **discovered from frame failures**, not only from job-spec tags.
- A limit declares whether it is **enforced or advisory**.

Everything is additive. An existing limit migrates to `FRAME` + `ENFORCED` with no reporter, and
behaves exactly as it did before. The one exception is legacy rows with `b_host_limit = true`,
which migrate to `HOST`.

> **Cuebot never talks to a license server and never checks a license out.** It observes and biases.
> Checkout stays where it belongs: in the DCC, at frame start. The license server remains the
> authority.

---

## 1. Why frame counting is wrong for licenses

Two problems, both structural.

**Licensing is usually per host, not per frame.** Houdini/`sesinetd`, Katana, Mari and Clarisse all
issue per-machine licenses: any number of processes on one machine draw a single token. A limit of
`50` against a 50-seat Houdini pool stalls the farm at roughly 50 *frames* while the license server
still has 40+ free seats.

**Cuebot is not the only consumer.** Artists on workstations draw from the same pool. Any purely
internal count is wrong the moment a human opens Houdini — and this is the case that matters most,
because every license the farm takes is one an artist cannot have.

### The economics: under-counting is cheap, over-counting is expensive

If Cuebot books a frame that turns out to have no license, the frame reports a license-shortage exit
status, the layer's booking is postponed for a few minutes, and the frame retries without consuming
a retry or dying. The farm recovers on its own.

If Cuebot *withholds* a booking because its accounting is playing safe, nothing recovers it. The
frame waits, the host idles, and the license sits unused on the server. There is no retry mechanism
for a booking that never happened.

Every judgement call in the counting model below resolves toward under-counting.

---

## 2. The counting model

### 2.1 Settlement, not `max()`

The two sources of truth — Cuebot's own bookings and the license server's report — are not two
opinions about the same quantity. They cover **disjoint time ranges**.

A Houdini frame typically checks a license out for hip load and scene build, then releases it well
before the frame finishes. Counting every running frame as a held license means a host running six
frames that collectively hold zero licenses is counted as holding six. Taking `max(internal,
external)` would guarantee that phantom reservation can never be corrected downward — the server's
smaller, *true* number always loses.

Instead, let `W` be `limit_record.ts_reported`, the moment the license server's view was captured:

```
settled(h)  = tokens the server reported h holding as of W.
              Ground truth. Already reflects releases, artists, everything.

pending(h)  = frames on h, in layers bound to the limit, dispatched after
              (W - settle_window). Bookings the server has not yet had a
              chance to observe.

tokens(h)   = settled(h) + pending(h)     -- additive: disjoint in time

usage(h)    = 1 if type = HOST and tokens(h) > 0
            = tokens(h) if type = FRAME

usage(L)    = Σ usage(h) over every host appearing in either set
```

Walking the cases:

| Situation | settled | pending | counted | Right? |
|---|---|---|---|---|
| Frame booked 10m ago, still holds a license | 1 | 0 | 1 | ✓ |
| Frame booked 10m ago, **released** its license | 0 | 0 | **0** | ✓ — the whole point |
| Frame booked 5s ago, server hasn't polled | 0 | 1 | 1 | ✓ no stampede |
| Artist on a workstation | 1 | 0 | 1 | ✓ |
| Artist logged into a busy render host | 1 | 0 | 1 | ✓ not double counted |
| 6 frames on one host, 1 license held (HOST) | 1 | 0 | 1 | ✓ |

The second row is the entire justification for the model. Under `max()` it counted 1 (HOST) or 6
(FRAME) forever; under settlement it drops to zero the moment the server says so.

A host that appears in *both* sets is counted once: the pending scan excludes hosts the snapshot
already covers, so reaching back cannot double count.

### 2.2 The settle window

`pending` is scanned from `ts_reported - limit.settle_window_seconds`, not from `ts_reported`
itself. The window reaches **backwards from the watermark**, because a checkout takes time to appear
on the license server — a frame dispatched a moment before a snapshot may be visible to neither
side.

`limit.settle_window_seconds` is a global property, default `120`. Set it to roughly twice the
reporter's poll interval.

A reporter that stops therefore grows `pending` toward "every running proc of a bound layer", which
is the fail-closed direction, and it is already bounded: past `int_report_ttl` the limit stops
blocking altogether (below).

### 2.3 Never-reported limits

A limit with `ts_reported IS NULL` has no ground truth, so `settled` is empty and `pending` covers
every running proc of a bound layer, unbounded by the settle window. That is exactly today's
counting, which is what makes the migration a no-op for existing limits.

### 2.4 Staleness

A limit is **stale** when `now() - ts_reported > int_report_ttl` (default `900` seconds; `0`
disables staleness for an internal-only limit).

**A stale limit stops enforcing and behaves as advisory**, flagged in the API, the GUI and the
metrics. This follows directly from the economics: the license server is still enforcing for real,
so gating the farm on data we know is wrong buys nothing and costs idle time. Frames that lose the
race fail with the license-shortage status and ride the backoff path.

There is deliberately no `stale_policy` knob. A site that wants a stale snapshot to keep gating for
longer raises `report_ttl`.

### 2.5 The asymmetry principle

Two different questions get two deliberately different answers, and both biases push toward using
fewer licenses:

- **"How much is in use?"** → optimistic. Settled + pending only, so released licenses stop counting
  and the farm keeps booking.
- **"Does this host already hold one?"** → generous. Any running frame of a bound layer, or any
  reported hold, counts as holding. A host that *might* still have the license is treated as though
  it does, so work packs onto it rather than lighting up a new machine.

---

## 3. Minimizing the license footprint

A cap is not the goal. The pool is shared with artists, so every host the farm lights up is a
license a person cannot have. Three mechanisms concentrate licensed work onto as few machines as
possible, well before any threshold is in sight.

### 3.1 `max_value` means machines, for a HOST limit

For a `HOST` limit, `int_max_value` is **not** "maximum licenses" — it is the maximum number of
distinct machines the farm may spread this license across. A studio with a 50-seat Houdini pool that
wants 20 seats kept free for artists sets the limit to 30, and the farm packs into 30 machines.

This is the primary footprint control, and the GUI states it in exactly these words, because "max
value" invites the wrong mental model.

### 3.2 Proc reuse (pre-existing)

`FrameCompleteHandler.handlePostFrameCompleteOperations` already keeps a proc on the same job after
a frame completes. On the steady-state path host affinity is therefore free — a host that acquires a
Houdini license keeps feeding itself Houdini frames. The leak is in *initial* booking and cross-layer
moves, which is what the next two mechanisms cover.

### 3.3 Layer ordering bias

OpenCue dispatch is host-driven: RQD reports in and Cuebot asks "what should this host run?" We
cannot pick a host for a frame, but we can pick the right work for a host. When a host reports in
and already holds tokens for some limits, layers bound to those limits are offered first.

`DispatchQuery.AFFINITY_ORDER_SQL` prepends a sort key to the existing
`frame.int_dispatch_order, frame.int_layer_order`:

*Work this host can do without acquiring a new license comes first.*

Layers with no license limits and layers whose licenses this host already holds are
indistinguishable at position 0, so unlicensed work is never penalized. Two guards:

- The bias applies **within a job only**. Job and priority selection are untouched.
- It is gated behind `dispatcher.limit.affinity_ordering_enabled` (default `false`): the sort key is
  evaluated per candidate frame, so every job pays a small dispatch cost whether or not it uses
  license limits, and it sits ahead of `int_dispatch_order`, reordering frames a user may be
  watching. Sites using HOST limits should turn it on to get the packing behavior described here.

The ordering bias applies to **ADVISORY limits too** — it never blocks anything, it only chooses
among work already eligible. That composition is the point of advisory mode: a site can run every
license limit advisory, never stall a frame, and still get the packing benefit.

### 3.4 The soft spread threshold

Ordering is a preference and can be overridden by circumstance. The hard control is a second, lower
threshold above which the farm stops lighting up new machines: `limit_record.int_soft_value`,
default `-1` meaning "same as `int_max_value`".

```
type = FRAME:  usage < max_value

type = HOST:   usage < soft_value
               OR host_holds(limit, host)
```

- **Below `soft_value`** — any host may take the work. The farm is allowed to grow.
- **At or above `soft_value`** — only hosts that already hold a token. The farm packs instead of
  spreading.

A host that already holds a token may always book, even at `max_value`: all frames on that machine
share the token, so the booking consumes nothing new. This is the core new behavior of a `HOST`
limit, and it is why `max_value` reads as "machines".

Setting `soft_value = max_value` (the default) gives the plain rule. Setting `soft_value = 0` gives
"never light up a new machine for this license" — an emergency lever when the report shows artists
are starved.

`host_holds` is the generous test from §2.5: any row in `limit_host` for that hostname, **or** any
running proc on that host in a layer bound to the limit.

<div class="mermaid">
flowchart TD
    A["Host reports in"] --> B["Order candidate layers:<br/>no new license needed, first"]
    B --> C{"Layer bound to<br/>an active limit?"}
    C -- no --> OK["Book"]
    C -- yes --> D{"Enforcement<br/>= ENFORCED?"}
    D -- "ADVISORY / DISABLED / stale" --> OK
    D -- yes --> E{"usage &lt; soft_value?"}
    E -- yes --> OK
    E -- no --> F{"Host already<br/>holds a token?"}
    F -- yes --> OK
    F -- no --> SKIP["Skip layer"]
</div>

> **Local dispatch caveat.** The local (workstation) dispatch queries gate on `max_value` alone, so
> a workstation already holding a token can be refused work the farm dispatcher would allow. This is
> a deliberate simplification — those queries have no `host` table in scope — not a structural
> limit. Revisit if artists hit it on saturated `HOST` limits.

---

## 4. Enforcement modes

`limit_record.str_enforcement ∈ {ENFORCED, ADVISORY, DISABLED}`.

| Mode | Blocks booking | Affinity bias | Soft threshold | Usage shown |
|---|---|---|---|---|
| `ENFORCED` | yes | yes | yes | yes |
| `ADVISORY` | **no** | **yes** | no | yes |
| `DISABLED` | no | no | no | yes |

**`ADVISORY` is the mode this feature was really missing.** The license server already enforces —
authoritatively, and for artists as well as the farm. A site can therefore let Cuebot never block a
frame, let shortages surface as license-shortage exit statuses handled by the layer backoff, and
still get the whole footprint benefit, because the ordering bias is independent of the gate. That is
the recommended configuration for a farm whose licensing is genuinely enforced upstream.

`DISABLED` exists so an operator can neutralize a misbehaving limit without deleting it. Deleting a
`limit_record` throws away its `layer_limit` bindings, which nobody can reconstruct from memory at
2am.

The schema default is `ENFORCED`, so every existing limit keeps today's semantics exactly. A **stale**
limit is treated as `ADVISORY` regardless of its configured mode.

---

## 5. Learning which layers need a license

Everything above assumes `layer_limit` is populated — that submitters declare
`<limits>houdini</limits>` in the job spec. In practice that coverage is poor, and **a limit only
constrains what is tagged**. An untagged Houdini layer consumes real licenses while contributing
nothing to `pending`, so the farm's own usage is under-reported and the whole model degrades.

Waiting for every submitter to tag correctly is not a plan. The failures themselves are the signal:
a frame that exits with the license-shortage status has *proved* it needs that license.

### 5.1 The failure rule lives on the limit

Three fields on `limit_record`, set together through `SetFailureRule`:

| Field | Meaning |
|---|---|
| `int_exit_status` | The frame exit status meaning "this license was unavailable". `NULL` = no rule. |
| `int_delay_minutes` | How long to postpone the layer when a frame reports it. `0` = don't delay. |
| `b_auto_tag` | Whether to bind the failing frame's layer to this limit. Default `true`. |

They are three fields and not one because the combinations are all meaningful:

- `delay = 5, auto_tag = true` — the normal license configuration.
- `delay = 0, auto_tag = true` — **pure discovery**. Learn coverage without changing dispatch at all.
- `delay = 5, auto_tag = false` — a status that isn't really a license.

Because the rules live in the database rather than a property file, they are **live-editable**: a
change takes effect on the next `LimitRuleCache` refresh instead of a Cuebot restart.

The status must agree with what RQD is configured to emit via `rqd.yaml
runner.log_exit_status_rules`. `330` is the conventional license-shortage code.

### 5.2 Auto-tagging

`FrameCompleteHandler.applyLimitRule` runs on the frame-complete path:

1. Skip if the frame was `EATEN` — auto-eat wins, and nothing retries an eaten frame.
2. Look up the limit claiming this exit status in `LimitRuleCache`.
3. If `auto_tag`, bind the layer with source `AUTO`. `LayerDao.addLimit` is idempotent and returns
   whether a row was actually inserted, so a burst of failing frames logs and counts **once**, not
   five hundred times.
4. Write the layer backoff via the existing conditional-monotonic `ts_start_after` update.

**Tag first, delay second.** If anything throws, keeping the discovery and losing the backoff is the
better trade. Discovery is best-effort throughout: it must never fail a frame-complete.

The delay applies whether or not the layer was already bound — the first failure is precisely the
case where the layer is not yet tagged.

### 5.3 Binding provenance

`layer_limit.str_source ∈ {SPEC, AUTO, MANUAL}`, plus `ts_created`:

- **`SPEC`** — declared in the job spec at launch. Never touched by automation.
- **`AUTO`** — inferred from a frame failure.
- **`MANUAL`** — added by an operator through the API or GUI.

One small column buys three things: the GUI marks inferred bindings, a mis-set exit status is
reversible with a single provenance-scoped delete, and discovery rate becomes measurable.

### 5.4 Rails against a mis-set exit status

Claiming a generic status would bind most of the farm to one limit. Four guards:

1. **Statuses 0 and 1 cannot be claimed.** 0 is success and is repurposed as the clear value; 1 is
   the conventional catch-all failure and is rejected at the API and by a `CHECK` constraint,
   because claiming it would tag nearly every failing layer on the farm.
2. **One limit per status**, enforced by a partial unique index. `SetFailureRule` returns
   `ALREADY_EXISTS` naming the other limit.
3. **Bulk undo** — `ClearBindings` / *Remove Auto-Tagged Layers…* in the GUI. One statement,
   provenance-scoped, `SPEC` bindings never touched.
4. **Visibility** — every first-time binding logs at INFO and increments
   `cuebot_limit_auto_tag_total{limit}`.

Clearing the rule (`exit_status = 0`) leaves existing `AUTO` bindings in place. Turning a rule off is
not the same as declaring everything it learned to be wrong; removing them is a separate, explicit
call.

### 5.5 Why discovery pairs with ADVISORY

As coverage grows, more running frames count toward the limit, so **measured usage rises even though
actual license consumption has not changed**. On an `ENFORCED` limit that looks like sudden
saturation and the farm stops booking — punishing the site for improving its own data.

So the sequence is:

1. Create the limit `ADVISORY`, with `auto_tag = true` and `delay_minutes` set. Nothing is gated.
   The affinity bias already applies, so the farm starts packing immediately.
2. Watch `cuebot_limit_auto_tag_total` and the tagged-layer count plateau. That is coverage
   converging.
3. Compare `settled_usage` against the license server's own numbers. When they track, the model is
   working.
4. Only then consider `ENFORCED` — and quite possibly decide it adds nothing, since the license
   server enforces anyway.

Each step is observable and reversible, and a site can stop at step 3 permanently.

### 5.6 Known limitation: coverage does not survive job launch

`layer_limit` is per *layer*, and layers belong to jobs. Every relaunch of the same scene creates new
layers that start untagged and must fail once to be rediscovered — costing one frame failure plus one
`delay_minutes` stall per new job.

Mitigations, in order of effort:

- **Keep `delay_minutes` low (1–2) for license limits.** The backoff exists to stop a hot loop, not
  to be a penalty box, and the affinity bias means retries land preferentially on hosts that already
  hold the license.
- **Promote discoveries to the service.** `layer.str_services` already carries `houdini`, and the
  `service` table is where per-service defaults live. A `service_limit` table applied at launch would
  make coverage durable across jobs. This is the natural next extension and is deliberately out of
  scope: it changes what a job gets at launch, which deserves its own design and its own opt-in.
- **Surface the pattern for a human.** The bindings dialog groups recent `AUTO` bindings by service,
  so a promotion candidate becomes obvious without anyone running a query.

---

## 6. Database schema

Migration: `V49__Add_limit_types_and_host_holds.sql`.

### `limit_record`

```sql
str_type          VARCHAR(16)  DEFAULT 'FRAME'    NOT NULL  -- FRAME | HOST
str_enforcement   VARCHAR(16)  DEFAULT 'ENFORCED' NOT NULL  -- ENFORCED | ADVISORY | DISABLED
int_soft_value    INT          DEFAULT -1         NOT NULL
ts_reported       TIMESTAMP(6) WITH TIME ZONE               -- the settlement watermark
str_report_source VARCHAR(255)
int_report_ttl    INT          DEFAULT 900        NOT NULL
int_exit_status   INT                                       -- CHECK (IS NULL OR > 1)
int_delay_minutes INT     DEFAULT 0    NOT NULL              -- CHECK (>= 0)
b_auto_tag        BOOLEAN DEFAULT true NOT NULL
```

The dead `b_host_limit` flag from `V2__Add_limit_table.sql` — never read by any code in any language
— is migrated to `str_type = 'HOST'`. The column itself is kept, not dropped: the migration is
purely additive so an older Cuebot can still run against a migrated database. `str_type` is
authoritative from here on, and nothing keeps `b_host_limit` in sync.

The migration also adds the primary key and the name uniqueness constraint that `limit_record` never
had, plus a partial unique index on `int_exit_status`.

> **Deployment gate.** The name uniqueness constraint fails loudly on a database that already has
> duplicate limit names. Precheck before upgrading:
> ```sql
> SELECT str_name, COUNT(*) FROM limit_record GROUP BY str_name HAVING COUNT(*) > 1;
> ```
> Resolve duplicates (rename or delete, repointing `layer_limit`) first.

### `layer_limit`

```sql
str_source VARCHAR(16) DEFAULT 'SPEC' NOT NULL   -- SPEC | AUTO | MANUAL
ts_created TIMESTAMP(6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL
```

plus a primary key and `UNIQUE (pk_layer, pk_limit_record)`.

**The unique constraint is load-bearing, not tidying.** `layer_limit` had no uniqueness and
`LayerDaoJdbc.addLimit` was an unguarded `INSERT`. Every aggregate joining `layer_limit` counts a
proc once per matching row, so a duplicate silently doubles that layer's usage contribution.
Auto-tagging calls `addLimit` on every failing frame, which would turn a latent bug into a live one
within minutes. The migration collapses pre-existing duplicates automatically — unlike a name
collision, those rows are provably redundant.

### `limit_host`

The license server's view of who holds a token.

```sql
CREATE TABLE limit_host (
    pk_limit_host     VARCHAR(36)  NOT NULL,
    pk_limit_record   VARCHAR(36)  NOT NULL,
    str_host_name     VARCHAR(256) NOT NULL,   -- normalized: short name, lowercased
    str_reported_name VARCHAR(256) NOT NULL,   -- as the server reported it, for display
    int_tokens        INT DEFAULT 1 NOT NULL,  -- CHECK (> 0)
    str_user          VARCHAR(64),
    ts_reported       TIMESTAMP(6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    ...
);
```

Keyed on **hostname, not `pk_host`**: most holders are artist workstations with no `host` row, and a
decommissioned-then-re-registered render host gets a new `pk_host` while keeping its name. `pk_host`
is resolved at read time by joining `host.str_name`, so a workstation that later joins the farm
starts matching automatically.

The table is set to `fillfactor = 70` with aggressive autovacuum: reports rewrite a handful of rows
every few seconds, so the updates should stay HOT and the table should never bloat.

### `limit_usage`

A precomputed summary — settled totals, settled host counts, watermark — so the dispatch gate reads
one row per limit instead of aggregating the farm on every dispatch query. Refreshed by the
`LOCK_LIMIT_USAGE_RECALCULATION` maintenance task every `limit.usage_refresh_seconds`, and
synchronously by the report path for the limits a report touches.

---

## 7. Configuration

`opencue.properties`:

```properties
# How long a license checkout may take to appear on the license server. The pending scan reaches
# back this far before a limit's report watermark. Set to roughly twice the reporter's poll
# interval. Default = 120.
limit.settle_window_seconds=120

# How often the limit_usage summary table is recomputed, in seconds. The report path also
# refreshes its own limit synchronously. Default = 5.
limit.usage_refresh_seconds=5

# Minimum seconds between accepted reports for the same limit. A faster report leaves that limit
# untouched and names it in the response's skipped_limits; the rest of the batch still applies.
# Default = 5.
limit.min_report_interval_seconds=5

# Whether dispatch orders layers a host can run without acquiring a new license ahead of layers
# that would light up a new one. Off by default so jobs without license limits pay no sort cost;
# turn on when using HOST limits. Default = false.
dispatcher.limit.affinity_ordering_enabled=false

# DEPRECATED. Superseded by the failure rule on the limit itself. Statuses claimed by a limit take
# precedence; any left here and unclaimed still work, with a one-time WARN at startup.
dispatcher.layer_delay.rules=
```

`limit.usage_refresh_seconds` also drives the `LimitRuleCache` refresh interval. Caching failure
rules in-process is safe where caching usage counters would not be: rules are read-only operator
configuration changed by hand a few times a year, so a few seconds of staleness after an edit is
invisible and every Cuebot instance converges on the next tick.

### Migrating from `dispatcher.layer_delay.rules`

The property still works for statuses no limit claims, and Cuebot logs a WARN at startup naming each
entry. Move each one onto the limit it belongs to:

```python
limit.setFailureRule(exitStatus=330, delayMinutes=5, autoTag=True)
```

A limit claiming a status **overrides** any property entry for it — including a limit with
`delay_minutes = 0`, which deliberately turns the delay off while keeping discovery on.

---

## 8. API

### Proto — `proto/src/limit.proto`

Enums: `LimitType` (`FRAME`, `HOST`), `LimitEnforcement` (`ENFORCED`, `ADVISORY`, `DISABLED`),
`LimitHoldSource` (`CUE`, `EXTERNAL`, `BOTH`), `LimitBindSource` (`SPEC`, `AUTO`, `MANUAL`).

The `Limit` message gained the configuration fields above plus the usage split that an operator
actually needs to read:

| Field | Meaning |
|---|---|
| `current_usage` | Merged usage: settled + pending. What the dispatcher gates on. |
| `settled_usage` | Reported by the license server as of `last_report_time`. |
| `pending_usage` | Booked since, not yet visible to the server. **Persistently high means the reporter is behind, not that the farm is busy.** |
| `host_count` | Distinct hosts holding at least one token. |
| `report_stale` | The last report is older than the TTL. |
| `blocking_disabled` | The limit is not currently blocking, for any reason. Saves clients recomputing the rule. |
| `spec_layer_count` / `auto_layer_count` | Coverage, split by how it was acquired. |

`current_running` (field 4) is retained as a deprecated alias of `current_usage` for wire
compatibility.

New RPCs on `LimitInterface`:

| RPC | Purpose |
|---|---|
| `SetType` | Switch between `FRAME` and `HOST` counting. |
| `SetEnforcement` | `ENFORCED` / `ADVISORY` / `DISABLED`. |
| `SetSoftValue` | The spread threshold. `0` or `-1` means "same as max". |
| `SetReportTtl` | Staleness threshold in seconds; `0` disables. |
| `SetFailureRule` | Exit status, backoff and auto-tag in one call — they are only meaningful together. |
| `GetBindings` | Layers bound to a limit, filterable by origin and by layer id. |
| `ClearBindings` | Remove bindings scoped by origin. `SPEC` is never removable this way. |
| `ReportUsage` | Feed Cuebot the license server's view. |
| `GetHolds` | Current token holders, filterable by limit and by host. |

### `ReportUsage` semantics

- **Per-limit full snapshot**, applied in one transaction, advancing that limit's watermark. Deltas
  would be unrecoverable if one were lost.
- **Limits absent from the request are untouched.** A Houdini reporter must not affect the Nuke
  limit.
- **An empty `hosts` list is meaningful**: it clears the hold set. That is the correct way to say
  "nothing is checked out", and it is distinct from not mentioning the limit at all.
- **Unknown limit names are returned, not thrown**, in `unknown_limits`. A license server reports
  every product the vendor sells; the farm has limits for three of them.
- **Skips are returned, not thrown**, in `skipped_limits` with a reason:
  - `RATE_LIMITED` — another reporter posted inside `limit.min_report_interval_seconds`.
  - `OUT_OF_ORDER` — the snapshot is older than the limit's current watermark. The reporter's clock
    is behind, or a queued snapshot was replayed out of order; applying it would move the watermark
    backwards and read as stale immediately.

  Either way the rest of the batch still applies. Validation of the report contents happens in a
  **pre-flight pass over every report**, so a bad row rejects the request with nothing written rather
  than rolling back a partially-applied batch.
- **Hostname normalization is Cuebot-side**: strip domain, lowercase, trim. Reporters should not need
  to know Cue's naming conventions. The raw string is retained for display.

`capture_time` matters more than it looks. The watermark decides which bookings count as pending; if
a reporter takes 20 seconds to run, stamping receipt time silently discards 20 seconds of bookings
from the pending set. **Reporters should send the time they polled the server, not the time they
finished.**

### `SetFailureRule` validation

- `exit_status` must be `0` (clear) or `> 1`. Status 1 and negative values return
  `INVALID_ARGUMENT`.
- `exit_status` must not be claimed by another limit → `ALREADY_EXISTS`, naming the other limit.
- `delay_minutes >= 0`. Zero is valid and means "tag but never delay".

### pycue

```python
import opencue
from opencue_proto import limit_pb2

# Create a discovery-mode license limit.
limit = opencue.api.createLimit('houdini', 30,
                                limitType=limit_pb2.HOST,
                                enforcement=limit_pb2.ADVISORY,
                                exitStatus=330, delayMinutes=2)

# Configuration
limit.setLimitType(limit_pb2.HOST)
limit.setEnforcement(limit_pb2.ADVISORY)
limit.setSoftValue(25)
limit.setReportTtl(900)
limit.setFailureRule(exitStatus=330, delayMinutes=2, autoTag=True)

# Inspection
limit.currentUsage()      # merged: what gates
limit.settledUsage()      # the license server's number
limit.pendingUsage()      # booked since the last report
limit.hostCount()         # distinct holders
limit.isReportStale()     # report older than the TTL
limit.isBlocking()        # False for ADVISORY, DISABLED, and stale ENFORCED
limit.specLayerCount(), limit.autoLayerCount()

limit.holds()                                     # who holds a token
limit.bindings(sources=[limit_pb2.AUTO])          # what Cue thinks needs it
limit.clearBindings([limit_pb2.AUTO])             # the undo for a mis-set exit status

# Module-level equivalents
opencue.api.getLimitHolds(limitName=None, hostName=None)
opencue.api.getLimitBindings('houdini', sources=None, layerIds=None)
opencue.api.clearLimitBindings('houdini', [limit_pb2.AUTO])
```

Reporting:

```python
report = opencue.api.buildLimitReport(
    'houdini',
    {'render0142': 1, 'ws-dtavares': 1},
    capture_time=captured_at)        # stamp BEFORE polling the server

response = opencue.api.reportLimitUsage([report], source='sesictrl@lic01')
response.unknown_limits   # names with no matching limit; not an error
response.skipped_limits   # rate-limited or out-of-order; not an error
```

### rest_gateway

`main.go` already registers `gw.RegisterLimitInterfaceHandlerFromEndpoint`, which generates a route
per RPC from the proto. The new RPCs are exposed over REST with no gateway change — a useful path for
reporters not written in Python.

---

## 9. CueGUI

### Limits plugin

The tree gained columns for Type, Mode, Soft, the three-way usage split, Hosts, Free, Last Report,
Source, Error Code, Backoff and Layers. State is encoded in form as well as number:

- **Mode** shows `Advisory (stale)` when the report has aged out, so an operator never has to work
  out from three columns whether a limit is actually gating.
- **Last Report** turns red past the TTL. A dead cron is otherwise invisible.
- **Layers** reads `120 (+38 auto)`. While the auto count climbs, coverage is still converging and
  the limit is not ready to be Enforced.

Context menu:

```
Edit Max Value…            Show License Holders…
Edit Soft Threshold…       Show Tagged Layers…
Set Type            ▸      Remove Auto-Tagged Layers…
Set Mode            ▸      ─────────
Set Report Timeout…        Rename
Set Failure Rule…          Delete Limit
```

**`LimitHoldsDialog`** (also opened by double-clicking a limit) lists Host / Tokens / Source / User /
Reported. Render-host rows jump to the host monitor; workstation rows are inert. The footer states
the arithmetic plainly, because the settlement split is the one thing nobody will guess:

> 31 of 50 in use — 28 reported by the license server, 3 booked since. 24 render hosts, 7
> workstations. Packing above 30. Reported by sesictrl@lic01, 14s ago.

**`LimitBindingsDialog`** is the counterpart: holds answer "who is using this license", bindings
answer "what does Cue think needs it". Filterable by origin, with a grouped-by-service footer that
makes a promotion candidate obvious — `38 auto-bound layers, 34 of them service "houdini"` reads as
"make this a service default" without anyone running a query.

**`CreateLimitDialog`** replaces the old bare text prompt that hardcoded `maxValue = 0` — a limit that
blocked everything the moment it was attached. It now walks through type, maximum, soft threshold,
mode, report timeout and the failure rule, with the Host-limit maximum explained inline as *how many
machines*.

**Layer properties** mark auto-bound limits, so a lighting TD looking at a delayed layer can see that
Cue inferred the binding rather than the submitter declaring it — otherwise an auto-tag looks like
someone else's mistake.

### Host monitor

A **Licenses** column shows what each host currently holds, with externally-held names
parenthesized so an artist session on a render host is visible:

```
houdini,(mari)
```

The map is rebuilt in `_getUpdate` from a single farm-wide `getLimitHolds()` call — one extra RPC per
refresh, independent of farm size. A failed call keeps the last good map rather than replacing it, so
a hiccup cannot silently reinterpret "no data" as "nobody holds anything".

The filter bar accepts `license:houdini`, filtered client-side against the same map. No proto change,
and consistent with how the column is populated. `HostAttributes` gains a Licenses group listing each
held limit with tokens, source and report age, closing the navigation loop from a holder row.

---

## 10. Metrics

| Metric | Type | Meaning |
|---|---|---|
| `cuebot_limit_auto_tag_total{limit}` | counter | Layers auto-bound after failing with the limit's exit status. Ticks once per **new** binding, so it measures discovery rate, not failure rate. |
| `cuebot_limit_delays_total{limit,exit_status}` | counter | Automatic layer backoffs written by a failure rule. |
| `cue_limit_bound_layers{limit,source}` | gauge | Coverage, split `SPEC` / `AUTO`. |
| `cue_limit_usage{limit,kind}` | gauge | Usage, split `settled` / `pending`. |
| `cue_limit_report_stale{limit}` | gauge | 1 when the external report is older than its TTL. |

What to watch:

- **`cue_limit_report_stale` sustained at 1** — the reporter is dead and the limit has stopped
  blocking. Alert on this.
- **`cue_limit_bound_layers{source="AUTO"}` plateauing** — discovery has converged; the limit is a
  candidate for `ENFORCED`.
- **`cue_limit_bound_layers{source="AUTO"}` climbing by thousands per hour** — a mis-set exit status.
  Clear the rule and run `ClearBindings`.
- **`cue_limit_usage{kind="pending"}` persistently large relative to `settled`** — the reporter is
  behind, not the farm busy. Shorten the poll interval or the settle window.

The gauges are cleared before each collection, so a deleted limit does not linger as a stale series.

---

## 11. External license reporting

A reporter polls the license server and pushes its per-host view into Cuebot via `ReportUsage`.
`samples/licensing/` contains a reference implementation for SideFX `sesinetd` via `sesictrl`:
`sesictrl_report.py`, `sesictrl_limits.yaml` and a README.

The shape any reporter should follow:

```
capture_time = now()          # BEFORE polling, not after
snapshot     = poll license server
reports      = [buildLimitReport(limit, hosts, capture_time=capture_time) for ...]
reportLimitUsage(reports, source='sesictrl@lic01')
```

Requirements that are not obvious:

- **Never post a partial or empty snapshot on failure.** An empty report clears every hold and opens
  the gate wide. Going quiet instead lets Cuebot's staleness handling degrade the limit to advisory,
  which is the designed response. The sample script deliberately posts nothing on any error —
  `sesictrl` failure, parse failure, anything.
- **Do not let runs overlap.** Two runs posting different snapshots would flap the dispatch gate. Use
  `flock` under cron, or `Type=oneshot` under a systemd timer.
- **Keep `limit.settle_window_seconds` at roughly twice the poll interval**, and each limit's
  `report_ttl` comfortably above it, so a brief outage does not flap the stale flag.
- **A limit in `skipped_limits` is normal**, not an error. Another reporter won the race inside
  `limit.min_report_interval_seconds`; every other limit in the batch still applied. Log it and exit
  zero.
- **Validate the parser against a captured sample before going live.** SideFX does not publish the
  `sesictrl` JSON schema and it varies between Houdini versions. The sample script isolates all of it
  in one function, `parse_sesictrl_json()`, and supports `--from-file` plus `--dry-run`.

A systemd timer is preferred over cron: real logging, a restart policy, no `flock` needed, and it can
poll faster than cron's one-minute floor.

---

## 12. Rollout

The implementation lands in four independently shippable phases.

**Phase 1 — schema and API.** V49, proto, DAO, `limit_usage` + maintenance task, servant, pycue.
`str_type` defaults to `FRAME`, `str_enforcement` to `ENFORCED`, `int_exit_status` to `NULL`,
`limit_host` starts empty, and with no reports the pending scan reproduces today's counting. The
`layer_limit` dedupe and unique constraint land here, ahead of anything that writes bindings. **No
behavior change for any existing limit.**

**Phase 2 — dispatch.** The enforcement/soft-threshold predicate and the affinity ordering across all
copies of the frame dispatch queries. This is where measurement happens: `EXPLAIN (ANALYZE, BUFFERS)`
against a production-sized snapshot.

**Phase 3 — failure rules and discovery.** `LimitRuleCache`, `applyLimitRule`, idempotent `addLimit`
with provenance, the property deprecation shim, discovery metrics. Safe to ship before phase 2 —
discovery with no gate changes nothing about booking.

**Phase 4 — GUI and reporter.** Limits widget, dialogs, host monitor column, `samples/licensing/`.

Then, per limit: create it `ADVISORY` with `auto_tag` on, watch coverage plateau, compare
`settled_usage` against the license server, and only then consider `ENFORCED`.

### Backwards compatibility

| Surface | Guarantee |
|---|---|
| `Limit.current_running` (field 4) | retained, populated with merged usage |
| `Limit.max_value`, `id`, `name` | unchanged |
| `createLimit(name, maxValue)` | unchanged signature; ENFORCED FRAME limit |
| Existing limits | FRAME + ENFORCED; identical behavior |
| `b_host_limit = true` rows | migrated to `str_type = 'HOST'`; column retained, unused |
| Older Cuebot ↔ migrated database | works; the migration adds only columns, tables and constraints |
| CueGUI ↔ older Cuebot | new columns render `0` / `--`; no crash |
| Older CueGUI ↔ new Cuebot | unaware of new fields; works unchanged |
| `rest_gateway` | no change; new RPCs exposed automatically |
| `layer_limit` rows | all become `SPEC`; duplicates collapsed by the migration |
| `LayerDao.addLimit(layer, id)` | retained as a deprecated overload defaulting to `SPEC` |
| `dispatcher.layer_delay.rules` | still honored for unclaimed statuses; WARN at startup |

Two hard gates: `limit_record` name uniqueness (fails loudly — resolve by hand) and the `layer_limit`
duplicate collapse (repaired automatically, because the rows are provably redundant).

---

## 13. Troubleshooting

**The farm stalled the moment I set a limit to `ENFORCED`.**
Coverage was still converging. Every new `AUTO` binding raises measured usage without changing actual
license consumption. Set it back to `ADVISORY`, wait for `cue_limit_bound_layers{source="AUTO"}` to
plateau, and compare `settled_usage` against the license server before trying again.

**A limit shows `Advisory (stale)` but I configured it Enforced.**
The reporter has not posted within `report_ttl`. Check the reporter's logs and its timer. A stale
limit deliberately stops blocking.

**`Pending` is always large and `Settled` is always small.**
The reporter is behind, not the farm busy. Either it polls too slowly for `limit.settle_window_seconds`,
or it is stamping `capture_time` after the poll instead of before.

**Thousands of layers suddenly got auto-bound.**
A mis-set exit status. Clear the rule with `setFailureRule(exitStatus=0)`, then
`clearBindings([limit_pb2.AUTO])`. `SPEC` bindings are untouched.

**Every relaunch of a job stalls once on the same layer.**
Expected: coverage is per-layer and does not survive job launch (§5.6). Lower `delay_minutes` to 1–2,
and consider declaring the limit in the job spec for that service.

**Two limits want the same exit status.**
`SetFailureRule` returns `ALREADY_EXISTS` naming the other limit. One status, one limit — there is no
sensible resolution for two.

**A host is refused work it should be able to take, on a local (workstation) booking.**
Local dispatch gates on `max_value` alone and does not run the holder test. See the caveat in §3.4.

---

## Related documentation

- [Adding or removing limits](/docs/user-guides/adding-removing-limits/) — the operator-facing guide
- [Deferred Layer Booking with Start After](/news/2026-08-07-layer-start-after-deferred-booking/) —
  the `ts_start_after` gate the failure rule writes to
- [RQD log-based exit-status rules](/news/2026-08-06-rqd-log-exit-status-rules/) — how RQD recognises
  a license shortage from the frame log and reports a substitute exit status
- [Monitoring development guide](/docs/developer-guide/monitoring-development/) — Prometheus setup
