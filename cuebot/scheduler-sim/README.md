# Scheduler farm simulator

A DB-backed integration harness for the cuebot `Scheduler`. It is not a model of
cuebot, it **is** cuebot: a **real cuebot + Postgres** driven over gRPC by a
**fake render farm**, so every booking goes through the exact production path
(the real `Scheduler`, the real SQL, the real frame-complete handler) — no
database writes from the driver. Hosts register like RQD, jobs are submitted like
a client, and a fake RQD runs/completes frames. It is the integration test unit
tests cannot be, and the place to observe behaviour that only shows up under
load: utilization, co-locality, throughput, reservations, dependency handling,
and big-job placement.

This exercises the *real* booking path end to end and has already surfaced
several bugs.

## Pieces
| file | role |
|------|------|
| **`simulate.py`** | **one command: tears down, resets DB, brings the whole stack up fresh, starts a workload** |
| `farm_spec.py` | the farm: 246 large/128c, 303 medium/32c, 1004 small/16c; mem 4 GB/core |
| `sim_model.py` | frame cores/mem/duration distribution (from real-farm CSVs); `SIM_COMPRESS` env scales durations |
| `sim_seed.sql` | one-time base data: facility/alloc/show/subscription |
| `register_hosts.py` | register all hosts via RQD ReportRqdStartup |
| `rqd_report.py [int]` | faithful host **+ running-frame** status heartbeat; refreshes `proc.ts_ping` so the 300s orphan sweep behaves like prod |
| `status_pinger.py` / `status_pinger_fast.py` | older empty-frame heartbeat (kept; superseded by `rqd_report.py`) |
| `fake_rqd.py [threads]` | fake RQD gRPC server on :8444; runs+completes frames. Used by new, old, and `rust --rust-real-launch`. `threads`=completion-report concurrency (1=serial, 64=concurrent RQDs) |
| `rqd_complete.py [int] [memfail]` | default `--mode rust`: polls the proc table for frames the Rust scheduler booked (dry-run) and reports them complete to cuebot after their `sim_model` run-time — the DB-poll analogue of `fake_rqd.py` |
| `gen_jobs.py` | submit a realistic job mix via LaunchSpec |
| `feed.py [dur] [target]` | paced feeder: hold a sustained backlog of ~`target` waiting frames |
| `drain_test.py <label> <njobs> <seed>` | submit a fixed backlog, time to drain (NEW vs OLD races) |
| `metrics.py [secs]` | poll DB read-only: util, co-locality, big-frame progress |
| `stats.py [secs]` | per-host-type util + honest live-util + **zombie/orphan proc counter** |
| `kill_all_jobs.py` | kill all sim jobs (reset) |

## One command (simulate.py)

### Start here — `--verify`
The one command that proves the scheduler still works, end to end, with nothing
to get wrong:
```
python simulate.py --verify
```
It runs six scenarios back-to-back — each a fresh, fully torn-down sim that
writes its own graphs — then prints a PASS/FAIL summary (nonzero exit if any
scenario fails):

| scenario | asserts |
|---|---|
| **OOM** | memory failures bump the layer's memory per-frame (no legacy ratchet) and frames retry |
| **PRIORITY** | completion share is *ordered by priority* across 10 classes (Spearman rho) |
| **PRIORITY_STARVING** | a low-priority stream survives a high-priority flood (stays above a 3% floor) |
| **RESERVATIONS** | stranded wide jobs are rescued by reservations + backfill and actually run |
| **LIMIT** | a global license cap (`limit_record.int_max_value`) holds concurrent running frames at the cap under a deep backlog |
| **FOLDER** | a folder/group core ceiling (`folder_resource.int_max_cores`) holds the folder's running cores at the cap under a deep backlog |

**Run it exactly as `python simulate.py --verify` — do not add or change flags.**
Each scenario is tuned (farm size, oversubscription, frame length) so its verdict
is meaningful; changing the options on a `--verify` run is unsupported and easily
misleads. For example, PRIORITY only shows proportional shares because it runs on
a deliberately small, ~9×-oversubscribed farm — run the same injector on the full
farm (~1×) and priority *looks* absent even though the scheduler is correct. Tune
only `SIM_VERIFY_SECONDS` (default `180`, per-scenario length); each scenario's
graphs land under `SIM_GRAPH_DIR/verify/<scenario>`.

### What one run does
A single command brings the whole stack up from nothing and tears it down again.
Each run, from a clean slate:
- initdb's a fresh Postgres, applies the cuebot schema migrations, and seeds the
  base data (facility, allocation, show, subscription);
- builds cuebot and starts it, pointing its JVM at a private hosts file so every
  farm hostname resolves to the local fake RQD (no root, no `/etc/hosts` edit);
- registers the farm: **1553 hosts / ~57k cores** across three real host classes
  (large 128c, medium 32c, small 16c), with realistic per-host usable memory;
- starts a **fake RQD** (`LaunchFrame` → completes each frame after a duration
  sampled from real-farm distributions) and a continuous host-status reporter;
- feeds a workload, streams live stats, and renders utilization + DB-load graphs;
- tears everything down on the next invocation, so **every run starts fresh**.

Runs are reproducible (seeded RNG). Default ports: Postgres **5433**, cuebot gRPC
**8443**, fake RQD **8444**.

### Exploratory runs
Beyond the self-test, drive the stack directly to study behaviour under load
(still **always starts fresh** — kills any prior run, resets the DB, restarts
cuebot, brings up fake RQD + the reporter, then feeds the workload):
```
# sustained-load utilization, NEW scheduler, realistic concurrency:
python simulate.py --mode new --reporter-threads 64 --compress 8 --feed 240 --metrics 220

# same on the legacy/old booking path (the control):
python simulate.py --mode old --reporter-threads 64 --compress 8 --feed 240 --metrics 220

# fixed-backlog drain, NEW:
python simulate.py --mode new --jobs 30 --seed 9000
```
Run `python metrics.py 120` against a live run anytime.

> Note: `simulate.py` selects scheduler behaviour only via documented
> properties; it never modifies cuebot code.

### Flags

#### Mode & scale
| Flag | Default | What it does |
|---|---|---|
| `--mode new\|old\|rust` | `new` | `new` = the E-PVM planner (`Scheduler.java`); `old` = the legacy report-driven dispatcher; `rust` = the standalone Rust scheduler (see below). |
| `--cuebots N` | `2` | Cuebot instances against one Postgres. All race the advisory lock so one plans per tick, exercising leader election / HA. Use `1` for a single instance. |
| `--hosts j,r,e` | full farm | Shrink the farm to these large,medium,small counts (e.g. `2,3,5`) for legible, watchable debugging. |

#### Workload
| Flag | Default | What it does |
|---|---|---|
| `--feed SECONDS` | `0` | Run the paced feeder for SECONDS, holding a sustained backlog. |
| `--feed-target N` | `40000` | Target number of runnable frames the feeder keeps queued. |
| `--jobs N` | `0` | Submit N fixed deterministic jobs at start (instead of a sustained feed). |
| `--dep-tree-depth D` | `3` | Submit each unit of work as an unbalanced dependency tree of max depth D (VFX work is rarely standalone). `1` = independent jobs, no depends. |
| `--seed N` | `9000` | RNG seed, for reproducible runs. |
| `--compress F` | `0.27` | Frame-duration scale (real-minutes → sim-seconds). Higher = longer frames = lower lifecycle rate; keep `hosts/avg_duration` under cuebot's ~120 lifecycle/s ceiling so the farm fills. |
| `--priority-spread SECS` | `0` | PRIORITY test: 10 classes at pri 10..100 contend with equal backlog; normally driven by `--verify` (pair with a small `--hosts` so it is oversubscribed). |
| `--priority-starve SECS` | `0` | PRIORITY_STARVING test: a deep high-priority flood; the low stream must stay above a 3% floor. Normally driven by `--verify`. |
| `--limit-test SECS` | `0` | LIMIT test: attach one global license cap (`SIM_LIMIT_MAX`, default 50) to a deep flood of 1-core frames and assert concurrent running never exceeds it. Normally driven by `--verify`. |
| `--folder-test SECS` | `0` | FOLDER test: cap the sim folder (`SIM_FOLDER_MAX` cores, default 50), flood narrow work into it, and assert the folder's running cores never exceed the cap. Normally driven by `--verify`. |

#### Farm realism / placement stress
| Flag | Default | What it does |
|---|---|---|
| `--tags [N]` | off (N=8) | Scatter N random capability tags across the farm; each job requests one, confining it to a ~1/N slice. Stresses placement under tag fragmentation. |
| `--gpu F` | `0` | Make fraction F of the farm GPU-capable and fraction F of layers GPU layers (placed only on GPU hosts). |
| `--mem-heavy [GB]` | off (GB=24) | Flood the farm with small, single-threaded, memory-hungry jobs so RAM binds and cores strand (the realistic sub-100% regime). |
| `--mem-heavy-max-cores N` | `4` | Core cap for the `--mem-heavy` jobs. |
| `--mem-failure-rate F` | `0` | Fraction of frame completions that report an OOM exit, so cuebot bumps the layer's memory and requeues the frame. |

#### Reservations & backfill
| Flag | Default | What it does |
|---|---|---|
| `--reservations` | off | Enable the planner's host reservations for blocked layers (EASY/Maui: time gate + per-class cap). |
| `--reservation-block-seconds S` | `60` | How long a layer must stay blocked before it may reserve. |
| `--reservation-max-fraction F` | `0.5` | Max fraction of a layer's fitting hosts that reservations may hold. |
| `--reservation-max-grantees K` | `8` | Max new reservation grants per tick. |
| `--no-backfill` | backfill on | Disable EASY backfill (reserved hosts freeze idle until they drain). |
| `--strand SECS` | `0` | Starvation test: inject wide (`--strand-cores`) big jobs every `--strand-interval` for SECS and watch them strand or get rescued by reservations + backfill. Use with `--feed`. |
| `--strand-interval SECS` | `30` | Seconds between big-job injections. |
| `--strand-cores N` | `64` | Per-frame width of the big jobs. `128` = a whole large, which cannot fit in a memory-bound farm's residual idle cores, so it *must* trigger a reservation; values >64 also raise cuebot's `dispatcher.frame_cores_max` clamp so the frame keeps its full width. |

#### Completion reporting
| Flag | Default | What it does |
|---|---|---|
| `--reporter-threads N` | `64` | Fake-RQD completion-report concurrency. A real farm has thousands of RQDs reporting in parallel; a serial reporter caps completion throughput. |
| `--heartbeat-interval S` | `5` (new), `0.1` (old) | Seconds the host-status reporter sleeps between full report rounds. |

#### Measurement
| Flag | Default | What it does |
|---|---|---|
| `--metrics SECONDS` | `0` | Run the metrics view (reserved-utilization) for SECONDS. |
| `--stats SECONDS` | `0` | Run the live-stats view for SECONDS: honest live utilization, running/waiting counts, frames completing and booking per second, DB load, and steady-state averages. |

Any run with `--feed`, `--strand`, `--stats`, or `--metrics` also auto-records
utilization and DB load and renders graphs at the end (under `/tmp`, override
with `SIM_GRAPH_DIR`).

## Rust scheduler mode (`--mode rust`)
`--mode rust` drives the **standalone Rust scheduler** (`rust/crates/scheduler`,
the `cue-scheduler` binary) instead of cuebot's in-process planner. Like
`--mode new` (and unlike the legacy report-driven booker) it is a **pull/poll
planner**: a feed loop queries Postgres for pending work, reads host
availability from its own DB-backed cache, scores with E-PVM, and books — it is
not triggered by RQD reports.

How the stack is wired in this mode:
- a throwaway **Redis** is started for the scheduler's accounting;
- the sim show is flagged `show.b_scheduler_managed=true` (migration V45 makes
  cuebot's own dispatch skip it); non-rust runs force it back to false;
- **one cuebot** runs with `scheduler.enabled=false` + `dispatcher.turn_off_booking=true`:
  it never plans or books, it only handles RQD reports/completions and maintains
  frame/layer/job stats;
- `scheduler_sim.yaml` is generated (Postgres + Redis coords, E-PVM) and
  `cue-scheduler` is launched against the sim DB;
- **by default it runs dry-run:** the scheduler books straight into Postgres (no
  real RQD launch) and **`rqd_complete.py`** polls the proc table and reports each
  booked frame complete to cuebot after its `sim_model` run-time. This is the
  practical mode — fast enough to fill the farm.

> `--rust-real-launch` flips the scheduler to call `LaunchFrame` on `fake_rqd`
> like `--mode new` (an equal-footing comparison: both pay the launch cost).
> Because `cue-scheduler` is a native binary, the JVM hosts file cuebot uses
> can't redirect its per-host RQD dials (`http://<host.name>:8444`) to fake_rqd,
> so the sim compiles `resolve_local.c` into a `getaddrinfo` `LD_PRELOAD` shim
> (the native analog of the JVM hosts file; needs `gcc`) and preloads it onto the
> scheduler. **Caveat:** the Rust scheduler awaits each launch inline through a
> single dispatcher actor, so real-launch is launch-latency-bound and far slower
> than dry-run — useful to observe the launch cost, not for throughput.

Prereqs: `redis-server` on PATH and a built binary (`cd ../../rust && cargo build
-p scheduler`; override the path with `SIM_SCHEDULER_BIN`); plus `gcc` for
`--rust-real-launch`. Example:
```
python simulate.py --mode rust --feed 240 --stats 220
```

## Prereqs (one-time)
**Automatic:** run `./setup.sh` from this directory. It creates `venv/`, installs
the gRPC deps, generates `opencue_proto/` from `../../proto/src`, and checks for a
usable JDK 17. Then run the sim with `./venv/bin/python simulate.py ...`.
(`simulate.py` also self-generates `opencue_proto/` on first run if it's missing,
so the proto step self-heals.)

The manual equivalent, if you'd rather do it by hand:
1. **Postgres** reachable; apply cuebot Flyway migrations to a `cuebot` DB, then
   the base seed: dept/services/config from `../src/main/resources/conf/ddl/postgres/seed_data.sql`
   plus `sim_seed.sql`.
2. **Python deps**: `python -m venv venv && venv/bin/pip install grpcio grpcio-tools protobuf`.
3. **Proto stubs**: compile the OpenCue protos into `opencue_proto/` (scripts add
   it to `sys.path`):
   `venv/bin/python -m grpc_tools.protoc -I../../proto/src --python_out=opencue_proto --grpc_python_out=opencue_proto ../../proto/src/*.proto && touch opencue_proto/__init__.py`
4. **Host name resolution (no root needed)**: cuebot dials `<hostname>:8444`
   for every host via the RQD gRPC client, so every farm name must resolve to
   127.0.0.1 (where `fake_rqd.py` listens). **`simulate.py` handles this with
   zero privileges**: it writes a private hosts file (`sim_hosts`) and points
   cuebot's JVM at it with `-Djdk.net.hosts.file=...` (a per-process name source,
   JDK 9+). No `/etc/hosts` edit, no `sudo`. If you drive the older scripts by
   hand, launch cuebot the same way:
   ```bash
   python -c "
   import sys; sys.path.insert(0,'.')
   import farm_spec
   print('127.0.0.1 localhost')
   for name,_,_ in farm_spec.all_hosts(): print(f'127.0.0.1 {name}')
   " > sim_hosts
   # then start cuebot with: JAVA_TOOL_OPTIONS=-Djdk.net.hosts.file=$PWD/sim_hosts
   ```
   Without name resolution, cuebot logs `UnknownHostException: elk0001` for every
   launch attempt and utilization stays at ~0% (all frames fail with
   `RqdClientException: failed to launch frame`). Note `jdk.net.hosts.file` makes
   that file the JVM's **only** name source, so it must also contain `localhost`
   (and the local machine name) — `simulate.py` adds these automatically.

## Paths & environment (all overridable)
`simulate.py` has no hardcoded layout — every path has a default plus a `SIM_*`
env override, so it runs from a plain checkout. Defaults derive from the
script's own location:

| var | default | what it is |
|-----|---------|------------|
| `SIM_FARM` | the dir of `simulate.py` | where the helper scripts + `opencue_proto/` live |
| `SIM_CUEBOT_DIR` | parent of `SIM_FARM` | cuebot project root (has `gradlew`) |
| `SIM_VENV_PY` | the interpreter running `simulate.py` | Python used for the helper scripts |
| `SIM_JDK_HOME` | `/tmp/jdk-17.0.2` | JDK for gradle; if the dir is absent, the ambient `JAVA_HOME` is used |
| `SIM_GRADLE_HOME` | `/tmp/ghome-<user>` | gradle user home (`-g`) |
| `SIM_PG_BIN` | `/usr/lib/postgresql/16/bin` | dir with `psql`/`pg_ctl` |
| `SIM_PGDATA` | `/tmp/pgdata` | Postgres data dir |
| `SIM_PG_PORT` | `5433` | Postgres port |
| `SIM_CUEBOT_LOG` | `/tmp/cuebot.log` | cuebot stdout/stderr log |
| `SIM_RUN_USER` | `$SUDO_USER`, else the checkout owner | non-root user to drop to **iff** invoked as root |

So from a checkout the common case is simply:
```
# scheduler-sim lives in cuebot/, so SIM_CUEBOT_DIR defaults correctly;
# run with the venv that has the deps and FARM/VENV_PY resolve themselves:
path/to/venv/bin/python simulate.py --mode new --hosts 1,1,2 --jobs 3 --stats 30
```
If invoked as **root**, `simulate.py` re-execs itself as `SIM_RUN_USER`
(postgres/cuebot refuse root), forwarding all `SIM_*` vars across the drop. If
invoked by a normal user it runs as them with no `sudo` anywhere.

## Run cuebot with the scheduler on
Set `scheduler.enabled=true` (and optionally `scheduler.interval_ms`,
`scheduler.reservations_enabled`). Point cuebot at the same Postgres.

## Drive it
```
venv/bin/python status_pinger.py &     # heartbeat (keep running)
venv/bin/python fake_rqd.py &          # fake RQD (keep running)
venv/bin/python register_hosts.py      # once, registers 1553 hosts
venv/bin/python gen_jobs.py            # submit the job mix
venv/bin/python metrics.py 70          # observe
```

Notes: postgres and cuebot must run as a non-root user (both refuse root).
`simulate.py` handles this for you: if invoked as root it re-execs itself as a
non-root user (`SIM_RUN_USER`, defaulting to whoever `sudo`'d in, else the owner
of the checkout) and runs the whole stack there; if invoked by a normal user it
just runs as them, with no `sudo` anywhere. So the sim works for any user out of
the box, with no account name hardcoded.
