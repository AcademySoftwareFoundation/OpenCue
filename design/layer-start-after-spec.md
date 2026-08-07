# Spec: `layer.ts_start_after` — deferred layer booking

**Status:** implemented on this branch (see §8 checklist; item 16's tracking issue is drafted in
`layer-start-after-tracking-issue.md`, to be filed after the PR lands)
**Branch:** `cuebot_licence_error_code`
**Depends on:** [#2501](https://github.com/AcademySoftwareFoundation/OpenCue/pull/2501) (RQD log-based exit-status rules)
**Related:** [#1246](https://github.com/AcademySoftwareFoundation/OpenCue/pull/1246) (frame state display overrides — considered and not used, see Decision log)

---

## 1. Summary

Add a nullable timestamp to the `layer` table meaning **"do not book frames of this layer before
this time."** Two writers use it:

1. **Automatic backoff.** When a frame reports an operator-configured exit status (e.g. `330`, the
   Houdini license shortage that #2501 teaches RQD to emit), Cuebot pushes the layer's
   `ts_start_after` a few minutes into the future instead of letting the frame retry immediately or
   die. Frames retry indefinitely without ever consuming a retry.
2. **Operators and tools,** via a new `SetStartAfter` RPC, a CueGUI right-click action, and a pycue
   wrapper method — which also delivers a general-purpose "start this layer at 18:00" capability.

The gate is enforced entirely by the existing frame-selection SQL in both dispatchers. No new frame
state, no reaper, no Quartz job, no scheduled service.

## 2. Motivation

A license shortage is not a property of the frame that hit it. Today Cuebot cannot tell one from a
generic crash, so a farm at license cap produces a wave of dead frames that someone has to clean up
by hand, every single time. Retrying immediately is pointless — the license is still gone — and
`maxRetries` is typically low enough that the frames die within seconds of each other.

#2501 gives RQD the ability to recognise the failure from the frame log and report a substitute exit
status. This spec is the Cuebot half: react to that status by pausing the *layer* for a few minutes
rather than killing its frames.

Pausing the layer rather than individual frames is correct here because **every frame in a layer
depends on the same license.** One failure is enough to establish that the license pool is
exhausted; there is no reason to burn one frame per free host to rediscover it.

## 3. Non-goals

- **No cap, deadline, or eventual kill.** Frames retry indefinitely. Backoff is minutes, not hours,
  so the machinery a budget would require (streak accounting, breach behaviour, reset triggers) is
  not worth its weight. Observability replaces it (§4.9).
- **No new frame state.** `FrameState` is derived into `int_<state>_count` column names by
  `trigger__update_frame_status_counts` (`V1__Initial_schema.sql:2883-2904`), so a new state means
  new columns on three stat tables plus every count query.
- **No frame-level `start_after`** in this pass. Documented as an extension point (§7).
- **No exponential backoff.** Fixed per-status durations.

## 4. Design

### 4.1 Schema

`V47__Add_layer_start_after.sql`:

```sql
ALTER TABLE layer
    ADD COLUMN ts_start_after TIMESTAMP (6) WITH TIME ZONE DEFAULT NULL,
    ADD COLUMN str_start_after_reason VARCHAR(255) DEFAULT NULL;

-- Almost every row is NULL, so the partial index is tiny. It serves the
-- cuebot_layers_delayed gauge and any "which layers are delayed" query.
CREATE INDEX i_layer_start_after ON layer (ts_start_after)
    WHERE ts_start_after IS NOT NULL;
```

No backfill (NULL is the correct value for every existing layer). No triggers.

`str_start_after_reason` is **free text displayed verbatim** — the backoff writes
`"Automatic backoff: exit status 330"`, the RPC writes `"Set by dtavares"`, and a future pipeline
tool can write `"Scheduled by shotgun_submit"` without a schema change or an enum to extend.

### 4.2 Semantics and write rules

`ts_start_after` NULL or in the past ⇒ the layer is bookable. In the future ⇒ no frame of the layer
may start.

| Writer | Rule | SQL shape |
| --- | --- | --- |
| Automatic backoff | **Conditional monotonic** — write only if it moves the time later | `SET ts_start_after = now() + d WHERE pk_layer = ? AND (ts_start_after IS NULL OR ts_start_after < now() + d)` |
| `SetStartAfter` RPC | **Authoritative** — any value, including earlier, or NULL | `SET ts_start_after = ? WHERE pk_layer = ?` |

The conditional form does three jobs at once:

- **Preserves operator intent.** An operator sets 18:00; a `330` lands at 10:00; the `WHERE` fails
  and 18:00 survives.
- **Absorbs the in-flight burst.** During an outage dozens of already-running frames on the same
  layer report within seconds. The first report writes; the rest are no-ops that never take the row
  lock. 50 reports ⇒ 1 write.
- **Lets a longer rule extend a shorter active delay.** `330:5` is active, `332:60` arrives, the
  delay extends to 60 minutes.

### 4.3 Dispatch gate

The gate lives in two tiers. **The reservation `UPDATE` is authoritative; the `SELECT`s are advisory
churn-avoidance.** A `SELECT` that misses the predicate costs one wasted reservation attempt, never
an incorrect booking.

**Tier 1 — authoritative (2 sites, fail-closed):**

| File | Constant | Change |
| --- | --- | --- |
| `cuebot/.../dao/postgres/FrameDaoJdbc.java:159` | `UPDATE_FRAME_STARTED` | Fold into the **existing** `frame.pk_layer IN (SELECT layer.pk_layer FROM layer LEFT JOIN layer_limit ...)` guard at lines 175–191 |
| `rust/crates/rqd/../scheduler/src/dao/frame_dao.rs:159` | `UPDATE_FRAME_STARTED` | Add a layer `EXISTS` guard (currently state + version only) |

Cuebot's reservation update already carries a layer-level subquery for `layer_limit`, so this is one
extra clause inside an existing guard of exactly the right shape. `updateFrameStarted` already
raises `FrameReservationException` when the update matches zero rows
(`FrameDaoJdbc.java:212-215`), on a path the dispatcher expects — the existing comment at line 217
names limit exhaustion as the normal cause. Log a delayed-layer rejection at debug so it does not
read as an error.

**Tier 2 — advisory (9 sites, one line each):**

```sql
AND (layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp)
```

| File | Query | `str_state='WAITING'` line |
| --- | --- | --- |
| `DispatchQuery.java` | `FIND_DISPATCH_FRAME_BY_JOB_AND_PROC` (:547) | 603 |
| `DispatchQuery.java` | `FIND_DISPATCH_FRAME_BY_JOB_AND_HOST` (:637) | 695 |
| `DispatchQuery.java` | `FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC` (:728) | 780 |
| `DispatchQuery.java` | `FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST` (:812) | 864 |
| `DispatchQuery.java` | `FIND_DISPATCH_FRAME_BY_LAYER_AND_PROC` (:899) | 955 |
| `DispatchQuery.java` | `FIND_DISPATCH_FRAME_BY_LAYER_AND_HOST` (:989) | 1047 |
| `DispatchQuery.java` | `FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC` (:1080) | 1132 |
| `DispatchQuery.java` | `FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST` (:1164) | 1216 |
| `rust/crates/.../scheduler/src/dao/layer_dao.rs` | pending-frames CTE | 221 |

All nine already join `layer`, so no join is added.

**Local dispatch honours the delay.** No exemption: `UPDATE_FRAME_STARTED` is a single static SQL
string shared by the normal, local and scheduler paths, so gating it gates everything — including
`LocalDispatcher.java:78`, which books a directly-named frame without touching `DispatchQuery` at
all and is therefore reachable *only* through the reservation update.

### 4.4 Automatic backoff

**Configuration** (`cuebot.properties`):

```properties
# Comma-separated exit_status:minutes pairs. Empty (default) disables the feature.
# Must agree with rqd.yaml `runner.log_exit_status_rules`.
dispatcher.layer_delay.rules=
```

Example: `dispatcher.layer_delay.rules=330:5,332:60`.

Parsed once at startup into `Map<Integer, Duration>`. Malformed entries are skipped with a `WARN`
rather than failing startup, mirroring RQD's typo-tolerance for invalid regexes. **Default empty**
so upgrades change no behaviour — a site whose renderer already exits `330` for unrelated reasons
must not silently switch from "dies after maxRetries" to "retries forever".

**Frame state.** In `FrameCompleteHandler.determineFrameState` (`:782`), insert **after** the
`job.autoEat` branch (`:807-809`) and **before** the LLU timeout check (`:812`):

```java
if (delayRules.containsKey(resolveExitStatus(report, frameDetail))) {
    return FrameState.WAITING;
}
```

Resulting order: stale-state guards → exit 0 → `SKIP_RETRY` → `FAILED_LAUNCH` → NIMBY →
**`autoEat`** → **delay rule** → LLU timeout → layer timeout → `FRAME_TIME_NO_RETRY` → `maxRetries`.

Two consequences of that position, both deliberate:

- **Auto-eat wins.** On an auto-eat job a license failure is `EATEN`, not retried. Auto-eat means
  eat everything.
- **Timeouts do not apply.** A delayed-rule frame is immune to LLU and layer timeouts. In practice
  moot — a license failure exits in seconds.

Use `resolveExitStatus(report, frameDetail)` (`:752`), not `report.getExitStatus()`, so the status
that drives the decision is the same one stored on the frame.

**The delay write** lives in `handlePostFrameCompleteOperations` (`:278`) and
`handleOrphanedPostFrameComplete` (`:670`) — the orphan path has its own post-complete method, so
both must call the shared helper or orphaned reports produce an unexplainable gap:

```java
if (newFrameState != FrameState.EATEN
        && delayRules.containsKey(exitStatus)) {
    layerDao.delayLayerForBackoff(frame, delayRules.get(exitStatus), reason);
}
```

The `EATEN` guard follows from auto-eat winning: nothing is going to retry, so delaying would only
stretch the eating across hours and stop the job reaching `FINISHED`.

This runs on the dispatch threadpool, so a queue rejection can drop the write. That is acceptable
and self-healing: the condition persists, the layer re-books, the next matching report writes the
delay. Worst case is one extra round of frame launches.

### 4.5 Retry accounting

Add the configured statuses to the exclusion list in `UPDATE_FRAME_RETRIES` (`FrameDaoJdbc.java:195`,
applied at `:229-232`), alongside `SKIP_RETRY`, `FAILED_LAUNCH`, `FRAME_CLEARED`, `FRAME_ORPHAN`,
`FAILED_KILL` and `DOWN_HOST`. Delayed frames therefore keep their full retry budget for genuine
failures later.

The list is currently a static string with seven positional binds. Since the set is now
configuration-driven, change the predicate to `int_exit_status <> ALL(?)` with an int array bind
rather than rebuilding SQL per configuration.

Note this increment happens at *frame start* using the exit status stored from the *previous* run
(`updateFrameStarted`), which is why exclusion is sufficient — no separate suppression is needed on
the failure side.

### 4.6 API

`proto/src/job.proto`. Next free field in `message Layer` (`:702-728`) is **26**:

```protobuf
message Layer {
    // ...
    int32 eligible_time = 23;
    int32 start_time = 24;
    int32 stop_time = 25;
    int32 start_after = 26;             // epoch seconds; 0 = not set
    string start_after_reason = 27;     // free text, display verbatim
}

service LayerInterface {
    // ...
    rpc SetStartAfter(LayerSetStartAfterRequest) returns (LayerSetStartAfterResponse);
}

message LayerSetStartAfterRequest {
    Layer layer = 1;
    int32 start_after = 2;   // epoch seconds; 0 clears the delay
    string username = 3;     // for the reason string
}
message LayerSetStartAfterResponse {} // Empty
```

`int32` epoch seconds matches `eligible_time` / `start_time` / `stop_time`. Single-layer request
matches all 13 existing `LayerSetX` RPCs; CueGUI loops for multi-selection exactly as it does for
`SetTags`. `0` clears — no separate `Clear` RPC. `username` follows the provenance convention
already used at `ManageLayer.java:199` (`new Source(request.toString(), request.getUsername(), ...)`).

**Servant** (`ManageLayer.java`): `start_after == 0` writes both columns NULL; otherwise writes the
timestamp and `"Set by <username>"` (`"Set by unknown"` when the username is empty).

**DAO** (`LayerDao` / `LayerDaoJdbc`):

- `updateStartAfter(LayerInterface, Timestamp orNull, String reason)` — authoritative.
- `delayLayerForBackoff(LayerInterface, Duration, String reason)` — conditional monotonic; returns
  whether a row was written, so the metric only counts real delays.

**Read path:** add both columns to `GET_LAYER_DETAIL` and `LAYER_DETAIL_MAPPER`
(`LayerDaoJdbc.java:202`) so `LayerDetail` carries `startAfter` / `startAfterReason`; and to
`GET_LAYER` (`WhiteboardDaoJdbc.java:1989`), `GET_LAYER_WITH_LIMITS` (`:2033`) and `LAYER_MAPPER`
(`:1181`) for the proto.

### 4.7 pycue

`pycue/opencue/wrappers/layer.py`:

- `startAfter(format=None)` — epoch seconds, or formatted, mirroring `eligibleTime()` (`:624`).
- `startAfterReason()`
- `setStartAfter(epochSeconds)`
- `clearStartAfter()` — sugar for `setStartAfter(0)`

### 4.8 CueGUI

`cuegui/cuegui/LayerMonitorTree.py`:

**Column** "Start After", modelled on the existing Eligible column (`:167`): rendered with
`cuegui.Utils.dateToMMDDHHMM`, blank when `start_after == 0`, sorted on the raw epoch (not the
formatted string). Tooltip is `start_after_reason` verbatim.

**Row treatment:** a distinct foreground/background while `start_after > now()`, so a delayed layer
is visible without the column being enabled. Clears itself once the deadline passes.

**Context menu:** "Set Start After…" → modal dialog.

```
+-- Set Start After ------------------+
| 3 layers selected                   |
|                                     |
| [ 2026-08-07 14:32 ]   (local time) |
|                                     |
| [+15m] [+1h] [+4h] [Tonight 18:00]  |
|                                     |
| current: 10:05                      |
| Automatic backoff: exit status 330  |
|                                     |
|      [Clear]   [Cancel]   [Set]     |
+-------------------------------------+
```

- `QDateTimeEdit` seeded with the layer's current value, or now when unset.
- Presets compute a datetime and fill the picker; they are not a separate input mode.
- Displays local time; sends UTC epoch seconds.
- `Clear` sends `0`.
- Multi-selection: one RPC per layer; show the first layer's current value.
- The dialog notes that a layer may be delayed again automatically while the underlying failure
  condition persists, so a `Clear` during an outage that immediately re-delays does not read as a
  bug.

### 4.9 Metrics

Replaces the cap as the mechanism that keeps a broken license server from being silent. No DB state,
nothing to reset.

| Metric | Type | Source |
| --- | --- | --- |
| `cuebot_layer_delays_total{exit_status}` | counter | +1 per **real** delay write (`delayLayerForBackoff` returned true) |
| `cuebot_layers_delayed` | gauge | `SELECT count(*) FROM layer WHERE ts_start_after > current_timestamp`, served by the partial index |

The gauge is collected by the existing `collectPrometheusMetrics` Quartz trigger (60s, defined in
`applicationContext-service.xml`). A layer stuck re-delaying for hours shows as a flat non-zero
gauge with a climbing counter — alert on `cuebot_layers_delayed > 0` sustained.

## 5. Behaviour walkthroughs

**License outage.** Host finishes a frame; RQD matches the log rule and reports `330`.
`determineFrameState` returns `WAITING`; `stopFrame` records `int_exit_status = 330`;
`handlePostFrameCompleteOperations` writes `ts_start_after = now() + 5min`,
`str_start_after_reason = "Automatic backoff: exit status 330"`, and unbooks the proc (the existing
`newFrameState`-based branch at `:325-330` already unbooks anything that is not WAITING/SUCCEEDED —
note WAITING *does* rebook, so the layer's own gate is what stops the proc taking another frame of
it). Other in-flight frames on the layer report `330` over the next few seconds; their writes are
no-ops. Both dispatchers skip the layer. Five minutes later it becomes bookable again; if the
license is still gone, one more report re-delays it. No frame consumed a retry; no frame died.

**Scheduled start.** An operator selects a layer, picks 18:00, and hits Set. `ts_start_after` =
18:00, reason `"Set by dtavares"`. The row is tinted and the column shows `08/07 18:00`. A `330`
arriving at 10:00 cannot pull it earlier (conditional monotonic). At 18:00 it books normally.

**Auto-eat job.** `job.autoEat` is checked first, so the frame is `EATEN` and no delay is written.
The job completes promptly, exactly as it does today.

## 6. Known characteristics and accepted trade-offs

- **Probe burst on expiry.** When the delay lifts, every waiting frame of the layer is bookable at
  once, so as many frames launch as there are free hosts; they fail, the first report re-delays, the
  rest are no-ops. Cost is one round of short-lived frame launches per backoff period. The knob is
  backoff length. Bounding it more tightly would require frame-level state, which this design
  deliberately avoids.
- **No jitter.** At layer granularity each layer's deadline derives from its own failure time, so
  delays are naturally staggered across layers; a jitter knob would earn nothing.
- **Two configurations must agree.** The exit status is an arbitrary number chosen in `rqd.yaml`
  and repeated in `cuebot.properties`. Document `330` as the conventional license-shortage code.
  Note it sits inside Cuebot's reserved 3xx band (299/301/302/399) without colliding.
- **Auto-eat jobs do not benefit.** By design (§4.4).
- **A dropped delay write self-heals** on the next matching report (§4.4).
- **Provenance is advisory.** `str_start_after_reason` is free text with no enforced vocabulary.

## 7. Deferred

- **CueWeb** — read-only column, and eventually set/clear parity. CueWeb already carries
  `frameStateDisplayOverride` in `app/frames/frame-columns.tsx:49`, so it tracks CueGUI closely and
  should not diverge on this. **Tracking issue to be filed.**
- **`rest_gateway` registration** of `SetStartAfter` — note `LayerInterface` registration there is
  already incomplete. Same tracking issue.
- **Frame-level `frame.ts_start_after`**, for "start this one frame at T". Every dispatch query
  already selects from `frame`, so the predicate becomes
  `GREATEST(layer.ts_start_after, frame.ts_start_after)` — a one-line extension of each site added
  here, not a new mechanism.
- **Exponential backoff**, if fixed durations prove insufficient. Would need an attempt counter.

## 8. Implementation checklist

1. `V47__Add_layer_start_after.sql` — two columns + partial index.
2. `LayerDetail`: `startAfter`, `startAfterReason` fields.
3. `LayerDao` / `LayerDaoJdbc`: `updateStartAfter`, `delayLayerForBackoff`; extend
   `GET_LAYER_DETAIL` + `LAYER_DETAIL_MAPPER` (`:202`).
4. `FrameDaoJdbc`: layer clause inside the `UPDATE_FRAME_STARTED` guard (`:159`, subquery
   `:175-191`); `UPDATE_FRAME_RETRIES` (`:195`) to `<> ALL(?)`.
5. `DispatchQuery.java`: predicate in all 8 queries (table in §4.3).
6. Config parsing: `dispatcher.layer_delay.rules` → `Map<Integer, Duration>`, WARN on malformed.
7. `FrameCompleteHandler`: `determineFrameState` insert after `:809`; delay-write helper called from
   `handlePostFrameCompleteOperations` (`:278`) and `handleOrphanedPostFrameComplete` (`:670`).
8. Metrics: counter + gauge.
9. `proto/src/job.proto`: fields 26/27, RPC, request/response messages.
10. `ManageLayer.java`: `setStartAfter` servant.
11. `WhiteboardDaoJdbc`: `GET_LAYER` (`:1989`), `GET_LAYER_WITH_LIMITS` (`:2033`), `LAYER_MAPPER`
    (`:1181`).
12. `rust/.../scheduler/src/dao/layer_dao.rs:221` predicate; `frame_dao.rs:159` reservation guard.
13. `pycue/opencue/wrappers/layer.py` accessors.
14. `cuegui/cuegui/LayerMonitorTree.py`: column, row tint, context action, dialog.
15. Docs: reference section + `docs/news/` post, following the #2501 precedent.
16. File the CueWeb / `rest_gateway` tracking issue.

## 9. Testing

- **Unit, no DB:** rule-map parser (valid, malformed, empty); `determineFrameState` ordering —
  auto-eat precedence, timeout immunity, `resolveExitStatus` interaction, and that an unconfigured
  status is unaffected.
- **DAO / servant:** conditional-monotonic write (operator value survives a backoff write; longer
  rule extends a shorter delay; no-op when already covered); reservation update refuses a delayed
  layer. Cuebot DAO tests hang locally on this machine during Flyway bootstrap, so these run in CI —
  local verification is `compileJava` + `spotlessJavaCheck` on JDK 11.
- **Rust:** scheduler pending-frames query excludes a delayed layer; reservation guard refuses one.
- **Manual:** set a delay via CueGUI on a live layer, confirm no booking until it expires; confirm
  `Clear` books immediately; confirm the tooltip distinguishes automatic from manual.

## 10. Decision log

Recorded because several of these were contested during design and the reasoning is not recoverable
from the code.

| # | Decision | Rationale |
| --- | --- | --- |
| 1 | Gate on a layer timestamp, not a new frame state | `FrameState` is string-interpolated into `int_<state>_count` columns by `trigger__update_frame_status_counts`; a new state means new columns on three stat tables plus every count query |
| 2 | Layer granularity, not per-frame | Every frame in a layer needs the same license, so one failure establishes the shortage; per-frame would burn one frame per free host to rediscover it |
| 3 | Considered and rejected: borrow `DEPEND` + `frame_state_display_overrides` (#1246) | Was the plan while the pause was per-frame. Superseded by #2: a layer has no state to relabel, and a timestamp gate needs no reaper |
| 4 | Considered and rejected: dynamic `limit_record` throttle | Both dispatchers already skip limit-exhausted layers, so it needed no new schema — but frames would sit as plain `WAITING` with no signal, failing the visibility requirement, and it reopens the licensing-on-`limit_record` fusion decided against on 2026-08-04 |
| 5 | Reservation `UPDATE` authoritative, `SELECT`s advisory | The `UPDATE` is the only atomic choke point and the only gate reachable by `LocalDispatcher:78`. A missed `SELECT` costs a wasted attempt, not a bad booking |
| 6 | Name `start_after`, not `delayed_until` | Reads correctly for both a backoff hold and a deliberately scheduled start |
| 7 | One column, conditional monotonic for automatic writes | Preserves operator intent, absorbs the in-flight report burst, and lets a longer rule extend a shorter delay — all in one `WHERE` clause |
| 8 | Local dispatch honours the delay | Keeps `UPDATE_FRAME_STARTED` a single static string; an exemption would need a second parameterised variant to keep in sync forever |
| 9 | No cap / no eventual kill | Backoff is minutes, not hours. A budget needed streak accounting, breach behaviour and three reset triggers, and — because retries are not incremented — a bespoke kill path, since `retries >= maxRetries` can never fire |
| 10 | Auto-eat wins over the delay rule | Auto-eat means eat everything; delaying an auto-eat layer would stretch the eating across hours and stop the job finishing |
| 11 | Skip the delay write when the frame was `EATEN` | Follows from #10 — nothing is going to retry |
| 12 | Delay write on the dispatch queue, not inline | Has `newFrameState` available (needed for #11); a dropped write self-heals on the next matching report |
| 13 | Free-text reason column, not a source enum | Renders both "delayed automatically (exit 330)" and "set by dtavares" with no parsing, and future writers extend it without a migration |
| 14 | `rules` default empty | A site whose renderer already exits `330` for its own reasons must not silently gain infinite retries on upgrade |
| 15 | Metrics replace the cap as the loudness mechanism | Counter + gauge need no schema and nothing to reset |
