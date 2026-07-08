"""One command to run the OpenCue scheduler simulation from a clean slate.

It ALWAYS starts fresh: it tears down any previous run (cuebot + fake RQD +
pinger + feeders), then RECREATES the Postgres cluster from scratch -- stops the
old one, deletes its data dir, re-initdbs and re-applies every migration -- so
each run begins from a byte-for-byte clean database with no table bloat,
autovacuum backlog, or warm cache carried over from a prior run (that state
quietly skews benchmark comparisons). It then brings the whole stack back up and
starts a workload. Long-running processes (cuebot, fake_rqd, pinger) are left
running so you can observe them; re-running simulate.py cleans them up again.

It does NOT modify cuebot. Scheduler behaviour is selected only via the
documented properties (scheduler.enabled / scheduler.reservations_enabled).

Examples:
  # fresh NEW scheduler, hold a 40k-frame backlog for 240s, print metrics
  python simulate.py --mode new --feed 240 --metrics 220

  # fresh OLD (legacy) scheduler, same workload
  python simulate.py --mode old --feed 240 --metrics 220

  # fresh NEW, submit a fixed 30-job backlog and just leave it running
  python simulate.py --mode new --jobs 30

  # fresh RUST scheduler: the standalone cue-scheduler binary plans+books while
  # cuebot runs with booking off as the completion engine (needs Redis + a built
  # rust/ cue-scheduler; see "Rust scheduler mode" in README.md)
  python simulate.py --mode rust --feed 240 --stats 220

Run metrics any time against the live run:  python metrics.py 120
"""
import argparse
import atexit
import getpass
import os
import resource
import signal
import shutil
import socket
import subprocess
import sys
import time

# The user the sim runs as. Postgres and cuebot both REFUSE to run as root, so
# if invoked as root we re-exec the whole script as a non-root user (see
# reexec_as_nonroot_if_needed). When invoked by a normal user this never fires
# and the sim simply runs as them: no sudo, no privilege drop, nothing keyed to
# a specific account. The drop target (root case ONLY) resolves, in order, to
# SIM_RUN_USER, else the user who sudo'd in (SUDO_USER), else the owner of this
# checkout, so there is never a baked-in username like "ubuntu".
def _default_run_user():
    import pwd
    return (os.environ.get("SIM_RUN_USER")
            or os.environ.get("SUDO_USER")
            or pwd.getpwuid(os.stat(os.path.abspath(__file__)).st_uid).pw_name)


RUN_USER = _default_run_user()

# ---------------------------------------------------------------- paths
# Every path below has a sensible default and an env override, so the sim runs
# from a plain checkout with no edits. Defaults are derived from this script's
# own location: FARM is the dir holding the helper scripts (this file's dir),
# CUEBOT_DIR is its parent (scheduler-sim lives inside cuebot/). Override any of
# them with the SIM_* env vars when your layout differs (e.g. a detached copy).
SIM_DIR = os.path.dirname(os.path.abspath(__file__))
FARM = os.environ.get("SIM_FARM", SIM_DIR)
CUEBOT_DIR = os.environ.get("SIM_CUEBOT_DIR", os.path.dirname(SIM_DIR))
# Python that runs the helper scripts. Default: the same interpreter running
# simulate.py — so `path/to/venv/bin/python simulate.py` just works. Override
# with SIM_VENV_PY to point at a different venv.
VENV_PY = os.environ.get("SIM_VENV_PY", sys.executable)
# JDK home for gradle. Empty/missing => let gradle use the ambient JAVA_HOME.
JDK17 = os.environ.get("SIM_JDK_HOME", "/tmp/jdk-17.0.2")
# Gradle user home, per-user so two users on the same box don't clash.
GHOME = os.environ.get("SIM_GRADLE_HOME", f"/tmp/ghome-{getpass.getuser()}")
PGBIN = os.environ.get("SIM_PG_BIN", "/usr/lib/postgresql/16/bin")
PGDATA = os.environ.get("SIM_PGDATA", "/tmp/pgdata")
PG_PORT = int(os.environ.get("SIM_PG_PORT", "5433"))
GRPC_PORT = 8443
SHOW = "10000000-0000-0000-0000-000000000003"
TOTAL_HOSTS = 1553   # full farm; overridden by --hosts (small-farm debug mode)
CUEBOT_LOG = os.environ.get("SIM_CUEBOT_LOG", "/tmp/cuebot.log")
# Per-JVM hosts file. cuebot dials each RQD at <hostname>:8444, so every farm
# name must resolve to 127.0.0.1 (where fake_rqd listens). Rather than touch the
# system /etc/hosts (needs root), we point cuebot's JVM at its OWN hosts file via
# -Djdk.net.hosts.file=... (JDK 9+). No root, no system-wide changes.
SIM_HOSTS_FILE = f"{FARM}/sim_hosts"
RQD_LOG = f"{FARM}/rqd.log"
PINGER_LOG = f"{FARM}/pinger.log"
FEED_LOG = f"{FARM}/feed.log"

# --- Rust scheduler (--mode rust) ----------------------------------------
# The standalone cue-scheduler binary (rust/crates/scheduler) can drive the sim
# instead of cuebot's planner. It books straight into Postgres and uses Redis for
# accounting. By default it runs dry-run (no RQD launch; rqd_complete.py drives
# completion) -- the practical mode. --rust-real-launch flips it to launch on
# fake_rqd like --mode new (see start_rust_scheduler / ensure_resolver_shim), but
# it's launch-latency-bound and much slower. Build with `cargo build -p scheduler`
# in rust/; override the path with SIM_SCHEDULER_BIN.
REPO_ROOT = os.path.dirname(CUEBOT_DIR)
SCHEDULER_BIN = os.environ.get(
    "SIM_SCHEDULER_BIN",
    os.path.join(REPO_ROOT, "rust", "target", "debug", "cue-scheduler"))
SCHEDULER_YAML = os.path.join(FARM, "scheduler_sim.yaml")
SCHEDULER_LOG = os.environ.get("SIM_SCHEDULER_LOG", "/tmp/cue-scheduler.log")
RUST_COMPLETE_LOG = f"{FARM}/rqd_complete.log"
REDIS_PORT = int(os.environ.get("SIM_REDIS_PORT", "6379"))

PSQL = [f"{PGBIN}/psql", "-h", "127.0.0.1",
        "-p", str(PG_PORT), "-U", "cue", "-d", "cuebot", "-A", "-t"]


def log(msg):
    print(f"[simulate {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def read_text(path):
    """Read a log file tolerantly. gRPC/JVM can emit non-UTF-8 bytes, so decode
    with errors ignored rather than crashing the orchestrator on a stray byte."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def ensure_proto_stubs():
    """Auto-generate opencue_proto/ if it's missing, so a fresh checkout works
    without a separate build step. Stubs come from the repo's proto sources
    (CUEBOT_DIR/../proto/src). Idempotent: skips if already present."""
    proto_pkg = os.path.join(FARM, "opencue_proto")
    if os.path.exists(os.path.join(proto_pkg, "report_pb2.py")):
        return
    proto_src = os.path.join(os.path.dirname(CUEBOT_DIR), "proto", "src")
    if not os.path.isdir(proto_src):
        log(f"WARNING: opencue_proto/ missing and proto sources not at {proto_src}; "
            f"run setup.sh or set SIM_FARM to a dir that has opencue_proto/")
        return
    log(f"opencue_proto/ missing — generating from {proto_src} ...")
    os.makedirs(proto_pkg, exist_ok=True)
    import glob
    r = sh([VENV_PY, "-m", "grpc_tools.protoc", f"-I{proto_src}",
            f"--python_out={proto_pkg}", f"--grpc_python_out={proto_pkg}"]
           + sorted(glob.glob(os.path.join(proto_src, "*.proto"))))
    if r.returncode != 0:
        log(f"  proto generation failed: {r.stderr.strip()[-300:]}")
        sys.exit(1)
    open(os.path.join(proto_pkg, "__init__.py"), "a").close()
    log(f"  generated {len(glob.glob(os.path.join(proto_pkg, '*_pb2.py')))} proto modules")


def ensure_buildable():
    """Fail early with a clear message if CUEBOT_DIR has no gradlew (the usual
    cause is running a detached copy of the scripts outside the repo)."""
    if not os.path.exists(os.path.join(CUEBOT_DIR, "gradlew")):
        log(f"ERROR: no gradlew in CUEBOT_DIR={CUEBOT_DIR}. The sim must reach "
            f"cuebot's gradlew. Run from cuebot/scheduler-sim/, or set "
            f"SIM_CUEBOT_DIR to the cuebot dir that contains gradlew.")
        sys.exit(1)


def _interp_has_grpc(py):
    """True if interpreter `py` can import grpc (i.e. the sim's helpers --
    feed.py, fake_rqd.py, gen_jobs.py -- will run under it)."""
    try:
        return subprocess.run([py, "-c", "import grpc"],
                              capture_output=True, timeout=30).returncode == 0
    except Exception:
        return False


def ensure_grpc_interpreter():
    """Make `python3 simulate.py` work no matter which interpreter launched it.

    Every helper the sim spawns (feed.py, fake_rqd.py, gen_jobs.py, ...) is run
    with this script's own interpreter and imports grpc. If we were started by a
    python WITHOUT grpcio, those helpers die silently at import -- no fake RQD,
    no feeder, and the run reports 0% utilization with no obvious cause. Rather
    than make the user remember to activate a venv, we self-heal:

      1. If our interpreter already has grpc, do nothing.
      2. Else find the sim's own venv (SIM_DIR/venv, or $SIM_VENV_PY). Build it
         via setup.sh if it's missing or also lacks grpc (idempotent).
      3. Re-exec this script under that venv interpreter so every child inherits
         it. SIM_GRPC_REEXECED guards against a re-exec loop.

    Runs AFTER the root drop so the venv is created/owned by the run user.
    """
    if _interp_has_grpc(sys.executable):
        return
    if os.environ.get("SIM_GRPC_REEXECED") == "1":
        sys.exit("ERROR: venv interpreter still cannot import grpc after "
                 "setup.sh; check scheduler-sim/setup.sh output.")
    venv_py = os.environ.get("SIM_VENV_PY") or os.path.join(SIM_DIR, "venv", "bin", "python")
    if not (os.path.exists(venv_py) and _interp_has_grpc(venv_py)):
        setup = os.path.join(SIM_DIR, "setup.sh")
        log(f"this interpreter ({sys.executable}) has no grpc; "
            f"building the sim venv via {setup} ...")
        r = subprocess.run(["bash", setup])
        if r.returncode != 0:
            sys.exit(f"ERROR: setup.sh failed (rc={r.returncode}); cannot build "
                     f"a venv with grpcio. Run scheduler-sim/setup.sh by hand.")
        venv_py = os.path.join(SIM_DIR, "venv", "bin", "python")
    if not (os.path.exists(venv_py) and _interp_has_grpc(venv_py)):
        sys.exit(f"ERROR: no usable venv with grpcio at {venv_py}. "
                 f"Run scheduler-sim/setup.sh by hand.")
    log(f"re-exec under sim venv interpreter {venv_py}")
    os.environ["SIM_GRPC_REEXECED"] = "1"
    os.execv(venv_py, [venv_py, os.path.abspath(__file__)] + sys.argv[1:])


def reexec_as_nonroot_if_needed():
    """If running as root, re-exec the whole script as a non-root user.

    Postgres and cuebot refuse to run as root, so the sim can't run as root
    directly. Instead of sprinkling `sudo -u <user>` through every command, we
    drop privileges once, here, and run everything else plainly as that user.
    When the sim is invoked by a normal user this is a no-op — nothing uses
    sudo at all, so it works for any user out of the box.
    """
    if os.geteuid() != 0:
        return  # already non-root: run everything directly, no sudo
    if os.environ.get("SIM_REEXECED") == "1":
        sys.exit("re-exec as non-root did not drop privileges (SIM_RUN_USER "
                 f"resolved to '{RUN_USER}', still root); set SIM_RUN_USER to a "
                 "non-root account and retry")
    log(f"running as root; postgres/cuebot refuse root, re-exec as '{RUN_USER}'")
    # sudo strips the environment, so forward the sim's own config across the
    # drop: every SIM_* override plus a few pass-throughs. -H sets HOME to
    # RUN_USER's home; SIM_REEXECED guards against a re-exec loop.
    forward = {k: v for k, v in os.environ.items()
               if k.startswith("SIM_") or k in ("JAVA_TOOL_OPTIONS", "PATH")}
    forward["SIM_REEXECED"] = "1"
    env_args = [f"{k}={v}" for k, v in forward.items()]
    os.execvp("sudo", ["sudo", "-H", "-u", RUN_USER, "env"] + env_args
              + [sys.executable, os.path.abspath(__file__)] + sys.argv[1:])


def set_fd_limit():
    """Raise this process's open-file limit, inherited by every child we spawn
    (cuebot, fake_rqd, samplers). cuebot caches one gRPC channel per RQD host
    (grpc.rqd_cache_size=2000), and at full-farm scale it keeps a socket open to
    ~every host at once. Under the default 1024 soft limit it dials the farm fine
    for a few minutes, then hits EMFILE ("Too many open files"): every LaunchFrame
    throws, the planner books then unbooks each frame, and the farm freezes at
    high utilization with ZERO throughput (util looks great, nothing completes).
    A 1553-host farm needs >1553 fds, so the default is far too low.

    Target is SIM_NOFILE (default: as high as the kernel allows), clamped to the
    hard cap. Tests set SIM_NOFILE low on purpose to reproduce the FD wall, or
    high to show raising it removes the stall. Best-effort: lifts the hard cap too
    when we have the privilege (root + CAP_SYS_RESOURCE), else rides the existing
    cap (e.g. a container that pins hard=4096, still 4x the 1024 default)."""
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target = int(os.environ.get("SIM_NOFILE", str(1 << 20)))
    new_hard = hard
    for h in (target, 262144, 65536):   # try to raise the hard cap toward target
        if h <= hard:
            break
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (min(target, h), h))
            new_hard = h
            break
        except (ValueError, OSError):
            continue
    new_soft = min(target, new_hard)
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, new_hard))
    except (ValueError, OSError):
        pass
    now = resource.getrlimit(resource.RLIMIT_NOFILE)
    log(f"open-file limit (RLIMIT_NOFILE) set to soft={now[0]} hard={now[1]} "
        f"(was soft={soft} hard={hard}, target {target})")


def psql(sql, timeout=60):
    return sh(PSQL + ["-c", sql], timeout=timeout)


def db_stats(sample_s=5):
    """Print a short Postgres health summary: transaction/tuple RATES (sampled
    over sample_s), cache hit ratio, connection states, and the busiest tables.
    Called by default at the end of every run so each sim reports DB load."""
    cols = ("xact_commit, xact_rollback, blks_hit, blks_read, tup_returned, "
            "tup_fetched, tup_inserted, tup_updated, tup_deleted")
    snap = f"SELECT {cols} FROM pg_stat_database WHERE datname='cuebot'"
    try:
        a = [int(x) for x in psql(snap).stdout.strip().split("|")]
        t0 = time.time()
        time.sleep(sample_s)
        b = [int(x) for x in psql(snap).stdout.strip().split("|")]
        dt = time.time() - t0
    except (ValueError, IndexError):
        log("DB stats: unavailable")
        return
    names = ["commits", "rollbacks", "blks_hit", "blks_read", "tup_returned",
             "tup_fetched", "tup_inserted", "tup_updated", "tup_deleted"]
    log(f"==== DB STATS (rates over {dt:.0f}s) ====")
    for n, va, vb in zip(names, a, b):
        log(f"  {n:13s} {(vb - va) / dt:10.0f}/s")
    hit, rd = b[2], b[3]
    if hit + rd:
        log(f"  cache_hit      {100 * hit / (hit + rd):9.2f}%")
    conns = psql("SELECT state, count(*) FROM pg_stat_activity "
                 "WHERE datname='cuebot' GROUP BY state").stdout.strip()
    log("  connections:   " + "; ".join(conns.split("\n")))
    tbls = psql("SELECT relname, n_tup_ins, n_tup_upd, n_tup_del "
                "FROM pg_stat_user_tables ORDER BY "
                "(n_tup_ins+n_tup_upd+n_tup_del) DESC LIMIT 5").stdout.strip()
    log("  busiest tables (ins/upd/del):")
    for row in tbls.split("\n"):
        if row:
            p = row.split("|")
            log(f"    {p[0]:16s} {p[1]:>10}/{p[2]:>10}/{p[3]:>10}")


def port_open(port):
    s = socket.socket()
    s.settimeout(1)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def pkill(pattern):
    """Kill processes whose command line matches pattern (best effort)."""
    out = sh(["pgrep", "-f", pattern]).stdout.split()
    me = str(os.getpid())
    killed = 0
    for pid in out:
        if pid == me:
            continue
        try:
            os.kill(int(pid), signal.SIGKILL)
            killed += 1
        except (ProcessLookupError, ValueError, PermissionError):
            pass
    return killed


def _match_pids(patterns):
    """PIDs (excluding ourselves) whose command line matches any of `patterns`."""
    me = os.getpid()
    pids = set()
    for pat in patterns:
        for pid in sh(["pgrep", "-f", pat]).stdout.split():
            try:
                p = int(pid)
            except ValueError:
                continue
            if p != me:
                pids.add(p)
    return pids


def kill_until_gone(patterns, what="processes", tries=6):
    """SIGKILL everything matching `patterns`, then VERIFY it is gone, retrying a
    few times. Returns True if the slate is clean.

    A single pkill is not enough to guarantee a clean run: if the previous run was
    SIGKILLed (so its own cleanup never ran), its cuebot/fake-RQD children -- spawned
    with start_new_session=True -- are re-parented to init and keep running. An
    orphan that is mid-reconnect to the fresh Postgres can be missed by a one-shot
    kill, then come back and book against this run's DB (multiple schedulers on one
    DB -> overcommit, corrupt reservations). Re-checking and re-killing closes that
    race, so a new run never starts on top of a previous one."""
    for _ in range(tries):
        pids = _match_pids(patterns)
        if not pids:
            return True
        for p in pids:
            try:
                os.kill(p, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                log(f"  WARN cannot kill {what} pid {p} (permission)")
        time.sleep(0.5)
    survivors = _match_pids(patterns)
    if survivors:
        log(f"  WARN {what} still alive after teardown: pids {sorted(survivors)}")
        return False
    return True


# cuebot + fake-RQD command-line patterns. A run must never start while any of
# these from a previous run survive, so teardown verifies they are gone and the
# SIGTERM/SIGINT/atexit handlers kill the ones this harness started.
SCHED_PATTERNS = ["build/libs/cuebot.jar", "CuebotApplication", "gradlew bootRun",
                  "cue-scheduler", "fake_rqd.py", "rqd_report.py", "rqd_complete.py"]

# Workload + helper scripts this harness starts (everything EXCEPT cuebot/RQD,
# which are SCHED_PATTERNS). Killed on teardown and on the way out.
WORKLOAD_PATTERNS = ["feed.py", "inject_big.py", "inject_priority_starve.py",
                     "inject_priority_spread.py", "strand_watch.py",
                     "strand_dur_watch.py", "priority_starve_watch.py",
                     "priority_spread_watch.py", "inject_limit.py",
                     "limit_watch.py", "inject_folder.py", "folder_watch.py",
                     "live_stats.py",
                     "gen_jobs.py", "drain_test.py", "metrics.py", "stats.py",
                     "status_pinger", "db_sampler.py", "util_sampler.py"]


# ---------------------------------------------------------------- teardown
def teardown():
    log("tearing down any previous run ...")
    # Kill workload + helpers first (best effort), then VERIFY cuebot/RQD are gone
    # (kill_until_gone re-checks and retries): a previous run's detached
    # (start_new_session) cuebot/RQD orphan -- re-parented to init and possibly
    # mid-reconnect to the fresh DB -- can slip past a one-shot pkill and then book
    # against THIS run's DB. Verifying closes that race.
    for pat in WORKLOAD_PATTERNS:
        pkill(pat)
    kill_until_gone(SCHED_PATTERNS, "cuebot/RQD")
    # Wait for the gRPC port to actually free up.
    for _ in range(30):
        if not port_open(GRPC_PORT):
            break
        time.sleep(1)
    log("  previous run stopped")


# ---------------------------------------------------------------- exit cleanup
# Every child is spawned start_new_session=True (detached) so it OUTLIVES this
# launcher unless explicitly reaped. Without this, a normal exit, a crash, a
# Ctrl-C, or a SIGTERM leaves cuebot/RQD orphans (re-parented to init) that
# reconnect to the next run's DB -> two schedulers on one DB (overcommit, corrupt
# reservations). So we reap this run's children on the way out: a SIGTERM/SIGINT
# handler for signal deaths (ALWAYS), and atexit for a normal return of a run that
# OWNS the stack (a watched run). A non-watch bring-up intentionally leaves the
# stack up for manual inspection; the next run's teardown() reaps it.
_cleanup_done = False
_cleanup_armed = False


def cleanup_children():
    """SIGKILL every child this harness started (cuebot, RQD, workload, samplers)
    and verify they are gone. Idempotent, so the signal and atexit paths can both
    fire without double-killing."""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True
    kill_until_gone(WORKLOAD_PATTERNS + SCHED_PATTERNS, "sim children")


def arm_cleanup():
    """Have a normal exit tear the stack down too (a watched run owns the stack)."""
    global _cleanup_armed
    _cleanup_armed = True


def _atexit_cleanup():
    if _cleanup_armed:
        cleanup_children()


def _signal_cleanup(signum, _frame):
    # A stop signal ALWAYS tears down (armed or not): if the run is interrupted we
    # never want to leave orphans, whatever mode it was in.
    log(f"received signal {signum}; cleaning up sim children ...")
    cleanup_children()
    # 128+signum is the conventional exit code for a signal death. SystemExit
    # re-runs atexit, but cleanup_children is idempotent so nothing double-fires.
    sys.exit(128 + signum)


def install_cleanup_handlers():
    """Arm the exit/signal reapers. Call once, AFTER any re-exec (execv replaces
    the image and wipes handlers) and BEFORE the first child is started."""
    atexit.register(_atexit_cleanup)
    signal.signal(signal.SIGTERM, _signal_cleanup)
    signal.signal(signal.SIGINT, _signal_cleanup)


# ---------------------------------------------------------------- postgres
# Schema + base seed live in the cuebot tree; sim_seed.sql lives beside us.
DDL_DIR = os.path.join(CUEBOT_DIR, "src", "main", "resources", "conf", "ddl", "postgres")


def _maint_psql(sql, db="postgres", timeout=120):
    """psql as the cluster superuser (the OS user initdb created) on a
    maintenance DB -- used to create the cue role / cuebot DB before they exist."""
    return sh([f"{PGBIN}/psql", "-h", "127.0.0.1", "-p", str(PG_PORT),
               "-U", getpass.getuser(), "-d", db, "-Atqc", sql], timeout=timeout)


def _psql_file(path, db="cuebot", user="cue", timeout=600):
    return sh([f"{PGBIN}/psql", "-h", "127.0.0.1", "-p", str(PG_PORT),
               "-U", user, "-d", db, "-v", "ON_ERROR_STOP=1", "-q", "-f", path],
              timeout=timeout)


def ensure_database():
    """Make a FRESH cluster usable with zero manual steps: create the cue role
    and cuebot DB, apply the cuebot schema (Flyway migrations in version order --
    cuebot bundles Flyway as a TEST-only dep and never migrates at runtime, so the
    schema must be pre-applied), then the base seed (seed_data.sql) and the sim
    entities (sim_seed.sql). Every step is guarded on a cheap existence check, so
    on an already-initialised cluster this is just a few SELECTs."""
    if _maint_psql("SELECT 1 FROM pg_roles WHERE rolname='cue'").stdout.strip() != "1":
        log("  creating role 'cue' ...")
        _maint_psql("CREATE ROLE cue LOGIN SUPERUSER")
    if _maint_psql("SELECT 1 FROM pg_database WHERE datname='cuebot'").stdout.strip() != "1":
        log("  creating database 'cuebot' ...")
        _maint_psql("CREATE DATABASE cuebot OWNER cue")
    import glob
    migs = sorted(glob.glob(os.path.join(DDL_DIR, "migrations", "V*.sql")),
                  key=lambda p: int(os.path.basename(p).split("__", 1)[0][1:]))
    have_show = bool(
        _maint_psql("SELECT to_regclass('public.show')", db="cuebot").stdout.strip())
    have_tracking = bool(_maint_psql(
        "SELECT to_regclass('public.sim_schema_migrations')", db="cuebot").stdout.strip())
    if have_show and not have_tracking:
        # Legacy cluster from before migration tracking: we cannot tell which
        # migrations it already has, so rebuild the DB from scratch to guarantee
        # it matches the current migration set. The data is wiped every run
        # anyway; this triggers once, on the first run after this change or after
        # the migration set grows under a cluster that predates tracking.
        log("  schema predates migration tracking; rebuilding cuebot DB ...")
        _maint_psql("DROP DATABASE cuebot WITH (FORCE)")
        _maint_psql("CREATE DATABASE cuebot OWNER cue")
    # Track applied migrations so a cluster that survives across runs still picks
    # up migrations added upstream since it was created (only the data, not the
    # schema, was previously refreshed each run).
    _maint_psql("CREATE TABLE IF NOT EXISTS sim_schema_migrations "
                "(filename text PRIMARY KEY, applied_at timestamptz DEFAULT now())",
                db="cuebot")
    applied = set(_maint_psql(
        "SELECT filename FROM sim_schema_migrations", db="cuebot").stdout.split())
    pending = [m for m in migs if os.path.basename(m) not in applied]
    if pending:
        log(f"  applying {len(pending)} cuebot schema migrations "
            f"({len(applied)} already applied) ...")
        for m in pending:
            r = _psql_file(m)
            if r.returncode != 0:
                sys.exit(f"schema migration {os.path.basename(m)} failed:\n"
                         f"{(r.stderr or r.stdout)[-800:]}")
            _maint_psql("INSERT INTO sim_schema_migrations(filename) VALUES ('"
                        + os.path.basename(m) + "')", db="cuebot")
    if _maint_psql(f"SELECT 1 FROM show WHERE pk_show='{SHOW}'",
                   db="cuebot").stdout.strip() != "1":
        log("  seeding base data (seed_data.sql + sim_seed.sql) ...")
        # Migrations V35/V38 already seed two task_lock rows that seed_data.sql
        # also inserts; clear the table first so seed_data.sql owns the full set
        # and does not collide on those PKs.
        _maint_psql("DELETE FROM task_lock", db="cuebot")
        for f in (os.path.join(DDL_DIR, "seed_data.sql"),
                  os.path.join(FARM, "sim_seed.sql")):
            r = _psql_file(f)
            if r.returncode != 0:
                sys.exit(f"seed {os.path.basename(f)} failed:\n"
                         f"{(r.stderr or r.stdout)[-800:]}")


def ensure_postgres():
    # ALWAYS start fresh. Stop any cluster left by a previous run and delete its
    # data dir, so every run re-initdbs a byte-for-byte clean cluster. Reusing a
    # cluster (the old behaviour: just DELETE the rows) silently carried table
    # bloat, autovacuum backlog and a warm shared_buffers/page cache across runs,
    # which skews A/B benchmark comparisons -- the second run inherits the first
    # run's DB state. A clean initdb each time removes that confound. The cost is
    # ~40s/run to re-apply migrations (ensure_database); that is the price of a
    # trustworthy baseline.
    if os.path.exists(os.path.join(PGDATA, "PG_VERSION")):
        log("stopping previous Postgres cluster (always-fresh) ...")
        sh([f"{PGBIN}/pg_ctl", "-D", PGDATA, "-m", "immediate", "-w", "stop"],
           timeout=60)
    shutil.rmtree(PGDATA, ignore_errors=True)
    shutil.rmtree("/tmp/pgrun", ignore_errors=True)

    # initdb with trust auth on loopback (postgres refuses root; the sim already
    # runs as a non-root user).
    log(f"initialising a fresh Postgres cluster at {PGDATA} ...")
    r = sh([f"{PGBIN}/initdb", "-D", PGDATA, "-A", "trust",
            "-E", "UTF8", "--no-sync"], timeout=180)
    if r.returncode != 0:
        sys.exit(f"initdb failed:\n{(r.stderr or r.stdout)[-800:]}")
    log("starting postgres ...")
    os.makedirs("/tmp/pgrun", exist_ok=True)
    sh([f"{PGBIN}/pg_ctl", "-D", PGDATA,
        "-o", (f"-p {PG_PORT} -k /tmp/pgrun -c listen_addresses=127.0.0.1"
               " -c synchronous_commit=off"),
        "-l", "/tmp/pg.log", "start"], timeout=60)
    for _ in range(30):
        if port_open(PG_PORT):
            log("  postgres up (fresh)")
            break
        time.sleep(1)
    else:
        sys.exit("postgres failed to start; see /tmp/pg.log")
    # Create role/db, apply every migration in order, load base + sim seed.
    ensure_database()


# ---------------------------------------------------------------- reset
RESET_SQL = (
    "DELETE FROM proc;"
    f" DELETE FROM frame f USING job j WHERE f.pk_job=j.pk_job AND j.pk_show='{SHOW}';"
    f" DELETE FROM layer l USING job j WHERE l.pk_job=j.pk_job AND j.pk_show='{SHOW}';"
    f" DELETE FROM job WHERE pk_show='{SHOW}';"
    " UPDATE host SET int_cores_idle=int_cores, int_mem_idle=int_mem,"
    " int_gpus_idle=int_gpus, int_gpu_mem_idle=int_gpu_mem;"
    " UPDATE subscription SET int_cores=0, int_gpus=0;")


# When shrinking the farm we must physically remove the extra hosts (locking
# doesn't hold: HostReportHandler.changeLockState auto-unlocks on report).
WIPE_HOSTS_SQL = (
    "DELETE FROM proc;"
    " DELETE FROM comments WHERE pk_host IS NOT NULL;"
    " DELETE FROM host_local; DELETE FROM job_local; DELETE FROM deed;"
    " DELETE FROM host_stat; DELETE FROM host;")


def reset_db(wipe_hosts=True):
    """Wipe the sim show AND all hosts. Cuebot must be DOWN (no contention).

    Always removes ALL hosts so they are re-created fresh by register_hosts every
    run: nothing is preserved between runs (the project rule), and host hardware
    set only at creation -- GPUs (int_gpus / int_gpu_mem), tags, cores -- always
    reflects the current farm_spec. (cuebot only refreshes GPU from a report when
    the host is fully idle, which never holds once NEW fills it, so re-creating is
    the reliable path.)
    """
    log("resetting DB to a clean slate (sim show + all hosts wiped) ...")
    r = psql(RESET_SQL)
    if "ERROR" in (r.stdout + r.stderr):
        log("  WARN reset hit: " + (r.stdout + r.stderr).strip().splitlines()[-1])
    if wipe_hosts:
        rh = psql(WIPE_HOSTS_SQL)
        if "ERROR" in (rh.stdout + rh.stderr):
            log("  WARN host wipe hit: " + (rh.stdout + rh.stderr).strip().splitlines()[-1])
    chk = psql(
        f"SELECT (SELECT count(*) FROM proc), "
        f"(SELECT count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job "
        f"WHERE j.pk_show='{SHOW}'), (SELECT count(*) FROM host);")
    procs, frames, hosts = chk.stdout.strip().split("|")
    log(f"  procs={procs} simFrames={frames} hosts={hosts}")
    if int(procs) or int(frames):
        sys.exit("reset failed (procs/frames remain) -- is cuebot still up?")
    return int(hosts)


# ---------------------------------------------------------------- cuebot
def ensure_cuebot_built():
    """Warm the gradle build (wrapper dist + deps + compile) with NORMAL name
    resolution. start_cuebot runs bootRun under -Djdk.net.hosts.file=sim_hosts so
    the cuebot APP resolves farm hostnames to fake_rqd -- but that file becomes the
    JVM's ONLY name source, so a COLD build under it cannot reach
    services.gradle.org / Maven Central and dies with UnknownHostException.
    Building here first (no hosts file) makes the later bootRun build-cache-only,
    leaving the hosts file to govern only the app's RQD dials. A no-op once warm."""
    log("building cuebot (gradle assemble; warms the cache for bootRun) ...")
    cmd = ["./gradlew", "assemble", "-g", GHOME, "--no-daemon", "--console=plain"]
    if JDK17 and os.path.isdir(JDK17):
        cmd.append(f"-Dorg.gradle.java.home={JDK17}")
    env = dict(os.environ)
    env.pop("JAVA_TOOL_OPTIONS", None)   # NO private hosts file during the build

    def _assemble(extra):
        return subprocess.run(cmd + extra, cwd=CUEBOT_DIR, env=env,
                              capture_output=True, text=True, timeout=1800)

    # Build --offline first. cuebot's build resolves the Spring Boot / Spotless
    # plugins through repo.spring.io/plugins-snapshot, a repo that is now
    # decommissioned (401/503) -- an online build re-HEADs it every time and dies
    # even though every artifact is already cached, aborting the scenario before
    # cuebot starts. Offline uses the warm cache and never touches it. Fall back to
    # an online build only to populate a genuinely cold cache.
    r = _assemble(["--offline"])
    if r.returncode != 0:
        log("  offline build failed (cold cache?); retrying online ...")
        r = _assemble([])
    if r.returncode != 0:
        sys.exit(f"cuebot build (assemble) failed:\n{(r.stderr or r.stdout)[-1500:]}")
    log("  cuebot build ready (cache warm)")


def start_cuebot(mode, reservations=False, block_seconds=60, max_fraction=0.5,
                 max_grantees=8, backfill=True, booking_off=False, frame_cores_max=0):
    # scheduler.enabled is a tri-state rollout switch: no | facility | managed
    # (back-compat true=facility/false=no). Default new->facility, else->no;
    # override with SIM_SCHEDULER_ENABLED (e.g. "managed" for per-show testing).
    enabled = os.environ.get("SIM_SCHEDULER_ENABLED") or ("facility" if mode == "new" else "no")
    resv = "true" if reservations else "false"
    bf = "true" if backfill else "false"
    log(f"starting cuebot (mode={mode}, scheduler.enabled={enabled}, "
        f"reservations={resv}, block={block_seconds}s, max_frac={max_fraction}, "
        f"max_grantees={max_grantees}, backfill={bf}, "
        f"booking_off={booking_off}) ...")
    # Point cuebot's JVM at our private hosts file so every farm name resolves
    # to 127.0.0.1 (where fake_rqd listens) without touching /etc/hosts. The
    # forked bootRun application JVM inherits JAVA_TOOL_OPTIONS from this env, so
    # the property is in effect before InetAddress initialises.
    # cuebot in the sim only talks to LOCAL services: postgres on 127.0.0.1, and
    # fake_rqd (the hosts file above maps every farm hostname to 127.0.0.1). But
    # it dials RQD BY HOSTNAME (e.g. jaime0001), and if the environment set a JVM
    # HTTP proxy in JAVA_TOOL_OPTIONS (-Dhttps.proxyHost=..., as sandboxes do),
    # gRPC routes those launches THROUGH the proxy (the farm names are not in
    # nonProxyHosts), which mangles the HTTP/2 stream ("INTERNAL: http2
    # exception"), so every LaunchFrame fails and the planner books then unbooks
    # and nothing runs (NEW looks busy but completes 0 frames). cuebot needs no
    # proxy at runtime, so bypass it for every host. This -D is appended LAST so
    # it overrides any nonProxyHosts inherited from JAVA_TOOL_OPTIONS.
    java_tool_opts = f"-Djdk.net.hosts.file={SIM_HOSTS_FILE} -Dhttp.nonProxyHosts=*"
    if os.environ.get("JAVA_TOOL_OPTIONS"):
        java_tool_opts = os.environ["JAVA_TOOL_OPTIONS"] + " " + java_tool_opts
    env = dict(os.environ)
    env.update({
        "JAVA_TOOL_OPTIONS": java_tool_opts,
        "CUEBOT_DB_URL": f"jdbc:postgresql://127.0.0.1:{PG_PORT}/cuebot",
        "CUEBOT_DB_USER": "cue", "CUEBOT_DB_PASSWORD": "",
        "SCHEDULER_ENABLED": enabled,
        "SCHEDULER_INTERVAL_MS": os.environ.get("SIM_TICK_MS", "3000"),
        "SCHEDULER_RESERVATIONS_ENABLED": resv,
        "SCHEDULER_RESERVATION_BLOCK_SECONDS": str(block_seconds),
        "SCHEDULER_RESERVATION_MAX_FRACTION": str(max_fraction),
        "SCHEDULER_RESERVATION_MAX_GRANTEES": str(max_grantees),
        "SCHEDULER_BACKFILL_ENABLED": bf,
        # Periodic "Scheduler stat:" summary (carries backfilled=N) fires every
        # this many seconds -- lowered from the 300s default so the live tail's
        # bf[] backfill counter updates often (override with SIM_STAT_INTERVAL_SECONDS).
        "SCHEDULER_STAT_INTERVAL_SECONDS": os.environ.get("SIM_STAT_INTERVAL_SECONDS", "30"),
        # --mode rust: scheduler.enabled=false AND booking off, so cuebot only
        # handles RQD reports/completions (frame + layer/job stat bookkeeping)
        # and never dispatches -- the Rust scheduler owns all booking.
        "DISPATCHER_TURN_OFF_BOOKING": "true" if booking_off else "false",
    })
    # Raise the per-frame core clamp (core-points) so whole-host wide jobs are
    # not capped back to 64; only when asked (0 keeps cuebot's default).
    if frame_cores_max > 0:
        env["DISPATCHER_FRAME_CORES_MAX"] = str(frame_cores_max)
    # Launch instance 0 from the prebuilt jar (NOT `gradlew bootRun`). A long-
    # running bootRun keeps a Gradle launcher alive for cuebot's entire lifetime,
    # and Gradle tees the app's (high-volume) stdout into its daemon log under
    # GHOME -- which balloons to tens of GB over a session and fills the disk.
    # `java -jar` removes Gradle from runtime entirely; the private hosts file
    # still applies via JAVA_TOOL_OPTIONS (exactly how the extra cuebots launch).
    # Runs as the current (non-root) user -- no sudo.
    jar = os.path.join(CUEBOT_DIR, "build", "libs", "cuebot.jar")
    if not os.path.exists(jar):
        sys.exit(f"cuebot jar not found at {jar} (ensure_cuebot_built should have built it)")
    java = os.path.join(JDK17, "bin", "java") if (JDK17 and os.path.isdir(JDK17)) else "java"
    logf = open(CUEBOT_LOG, "w")
    subprocess.Popen([java, "-jar", jar], cwd=CUEBOT_DIR, stdout=logf,
                     stderr=subprocess.STDOUT, start_new_session=True, env=env)
    # Wait for ready.
    for i in range(180):
        if "Started CuebotApplication" in read_text(CUEBOT_LOG) and port_open(GRPC_PORT):
            log(f"  cuebot ready after ~{i}s (gRPC :{GRPC_PORT})")
            return
        time.sleep(1)
    sys.exit(f"cuebot did not become ready; see {CUEBOT_LOG}")


def start_extra_cuebot(instance, mode, reservations=False, block_seconds=60,
                       max_fraction=0.5, max_grantees=8, backfill=True, frame_cores_max=0):
    """Launch an ADDITIONAL cuebot (instance >= 1) from the built jar, on offset
    ports, against the SAME Postgres with scheduler.enabled. All instances race
    for the Postgres advisory lock each tick, so exactly one plans at a time:
    this is how the sim exercises leader election / HA (Scheduler.md section 4).

    Only instance 0 (start_cuebot, via bootRun) is reached by the farm, fake RQD
    and feeder; the extras just join to plan from the shared DB and fire their
    RQD launches through the same hosts file. Using the prebuilt jar (not a second
    `gradlew bootRun`) avoids two Gradle builds fighting over the build dir."""
    cue = GRPC_PORT + 10 * instance     # this extra's OWN grpc port: 8453, 8463, ...
    # RQD dial port: there is exactly ONE fake_rqd (started by instance 0 on
    # GRPC_PORT+1 = 8444), so EVERY cuebot must dial RQD there. The old cue+1
    # (8454, 8464, ...) pointed each extra at a dead port, so when an extra won
    # the planner lock all its launches failed and its frames were booked then
    # unbooked, so the farm looked busy but completed nothing.
    rqd = GRPC_PORT + 1                 # 8444, the single fake_rqd for all instances
    web = 8080 + instance               # embedded Tomcat (metrics); 8081, 8082, ...
    logpath = CUEBOT_LOG.replace(".log", f"-{instance}.log")
    jar = os.path.join(CUEBOT_DIR, "build", "libs", "cuebot.jar")
    if not os.path.exists(jar):
        sys.exit(f"cuebot jar not found at {jar} (ensure_cuebot_built should have built it)")
    enabled = os.environ.get("SIM_SCHEDULER_ENABLED") or ("facility" if mode == "new" else "no")
    # cuebot in the sim only talks to LOCAL services: postgres on 127.0.0.1, and
    # fake_rqd (the hosts file above maps every farm hostname to 127.0.0.1). But
    # it dials RQD BY HOSTNAME (e.g. jaime0001), and if the environment set a JVM
    # HTTP proxy in JAVA_TOOL_OPTIONS (-Dhttps.proxyHost=..., as sandboxes do),
    # gRPC routes those launches THROUGH the proxy (the farm names are not in
    # nonProxyHosts), which mangles the HTTP/2 stream ("INTERNAL: http2
    # exception"), so every LaunchFrame fails and the planner books then unbooks
    # and nothing runs (NEW looks busy but completes 0 frames). cuebot needs no
    # proxy at runtime, so bypass it for every host. This -D is appended LAST so
    # it overrides any nonProxyHosts inherited from JAVA_TOOL_OPTIONS.
    java_tool_opts = f"-Djdk.net.hosts.file={SIM_HOSTS_FILE} -Dhttp.nonProxyHosts=*"
    if os.environ.get("JAVA_TOOL_OPTIONS"):
        java_tool_opts = os.environ["JAVA_TOOL_OPTIONS"] + " " + java_tool_opts
    env = dict(os.environ)
    env.update({
        "JAVA_TOOL_OPTIONS": java_tool_opts,
        "CUEBOT_DB_URL": f"jdbc:postgresql://127.0.0.1:{PG_PORT}/cuebot",
        "CUEBOT_DB_USER": "cue", "CUEBOT_DB_PASSWORD": "",
        "SCHEDULER_ENABLED": enabled,
        "SCHEDULER_INTERVAL_MS": os.environ.get("SIM_TICK_MS", "3000"),
        "SCHEDULER_RESERVATIONS_ENABLED": "true" if reservations else "false",
        "SCHEDULER_RESERVATION_BLOCK_SECONDS": str(block_seconds),
        "SCHEDULER_RESERVATION_MAX_FRACTION": str(max_fraction),
        "SCHEDULER_RESERVATION_MAX_GRANTEES": str(max_grantees),
        "SCHEDULER_BACKFILL_ENABLED": "true" if backfill else "false",
        "SCHEDULER_STAT_INTERVAL_SECONDS": os.environ.get("SIM_STAT_INTERVAL_SECONDS", "30"),
        # Offset every listener so the extra never collides with instance 0.
        "CUEBOT_GRPC_CUE_PORT": str(cue),
        "CUEBOT_GRPC_RQD_SERVER_PORT": str(rqd),
        "SERVER_PORT": str(web),
    })
    if frame_cores_max > 0:
        env["DISPATCHER_FRAME_CORES_MAX"] = str(frame_cores_max)
    java = os.path.join(JDK17, "bin", "java") if (JDK17 and os.path.isdir(JDK17)) else "java"
    log(f"starting cuebot #{instance} (jar, gRPC :{cue}, web :{web}, "
        f"scheduler.enabled={enabled}) ...")
    logf = open(logpath, "w")
    subprocess.Popen([java, "-jar", jar], cwd=CUEBOT_DIR, stdout=logf,
                     stderr=subprocess.STDOUT, start_new_session=True, env=env)
    for i in range(180):
        if "Started CuebotApplication" in read_text(logpath) and port_open(cue):
            log(f"  cuebot #{instance} ready after ~{i}s (gRPC :{cue})")
            return
        time.sleep(1)
    sys.exit(f"cuebot #{instance} did not become ready; see {logpath}")


# ---------------------------------------------------------------- helpers
def write_sim_hosts_file():
    """Write a private JVM hosts file mapping every farm host → 127.0.0.1.

    cuebot resolves each host name to dial its RQD; we point cuebot's JVM at
    THIS file via -Djdk.net.hosts.file (see start_cuebot) so no root / no
    /etc/hosts edit is needed. Writes the active farm set (honors --hosts /
    SIM_HOST_COUNTS — exactly the hosts that get registered and dialed).
    localhost and the local machine name are included because this file becomes
    the JVM's ONLY name source.
    """
    sys.path.insert(0, FARM)
    import farm_spec
    import importlib
    importlib.reload(farm_spec)  # honor SIM_HOST_COUNTS if set
    names = sorted({n for n, _, _ in farm_spec.all_hosts()})
    lines = ["127.0.0.1 localhost", "::1 localhost"]
    try:
        lines.append(f"127.0.0.1 {socket.gethostname()}")
    except Exception:
        pass
    lines += [f"127.0.0.1 {n}" for n in names]
    with open(SIM_HOSTS_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(SIM_HOSTS_FILE, 0o644)  # plain readable; cuebot runs as this same user
    log(f"  wrote JVM hosts file {SIM_HOSTS_FILE} ({len(names)} farm hosts → 127.0.0.1)")


def spawn(script_args, logpath, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    logf = open(logpath, "w")
    return subprocess.Popen([VENV_PY] + script_args, cwd=FARM,
                            stdout=logf, stderr=subprocess.STDOUT,
                            start_new_session=True, env=env)


# --- automatic graphs (util% + DB load) ----------------------------------
# Every watched run records utilization (util_sampler) and DB load (db_sampler)
# to an auto-named scratch dir and renders two PNGs at the end, so a run always
# leaves graphs behind without any manual sampling step. Override the directory
# with SIM_GRAPH_DIR; the default is /tmp/scheduler-sim/<mode>-<timestamp>.
def graph_dir_for(mode):
    base = os.environ.get("SIM_GRAPH_DIR")
    if base:
        return base
    return os.path.join("/tmp", "scheduler-sim",
                        f"{mode}-{time.strftime('%Y%m%d-%H%M%S')}")


def start_samplers(graph_dir, tag="run"):
    """Spawn db_sampler + util_sampler writing CSVs into graph_dir. Returns the
    Popen handles so they can be stopped before plotting."""
    os.makedirs(graph_dir, exist_ok=True)
    # Record the invocation so every graph traces back to its config; plot_run.py
    # stamps this along the bottom of each PNG.
    try:
        import shlex
        with open(os.path.join(graph_dir, f"{tag}_cmd.txt"), "w") as _cf:
            _cf.write("simulate.py " + shlex.join(sys.argv[1:]) + "\n")
    except Exception:
        pass
    procs = [
        spawn(["analysis/db_sampler.py", os.path.join(graph_dir, f"{tag}_dbstat.csv")],
              os.path.join(graph_dir, "db_sampler.log")),
        spawn(["analysis/util_sampler.py", os.path.join(graph_dir, f"{tag}_util.csv")],
              os.path.join(graph_dir, "util_sampler.log")),
    ]
    log(f"  sampling util%/DB load -> {graph_dir}")
    return procs


def generate_graphs(graph_dir, sampler_procs, tag="run"):
    """Stop the samplers and render the run's PNGs (utilization, throughput,
    reservation subsystem, DB load). Best-effort: a plotting failure warns but
    never fails the run."""
    for p in sampler_procs:
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(1)   # let the final CSV line flush
    r = sh([VENV_PY, "analysis/plot_run.py", graph_dir, tag], cwd=FARM, timeout=300)
    pngs = [os.path.join(graph_dir, f"{tag}_util.png"),
            os.path.join(graph_dir, f"{tag}_throughput.png"),
            os.path.join(graph_dir, f"{tag}_membound.png"),
            os.path.join(graph_dir, f"{tag}_reservations.png"),
            os.path.join(graph_dir, f"{tag}_dbstats.png")]
    made = [p for p in pngs if os.path.exists(p)]
    if made:
        log("GRAPHS written:")
        for p in made:
            log(f"    {p}")
    else:
        log(f"  WARN graph generation produced no PNGs: "
            f"{(r.stderr or r.stdout or '').strip()[-300:]}")


def ensure_hosts(nhosts, expected):
    if nhosts >= expected:
        log(f"hosts present ({nhosts})")
        return
    log(f"have {nhosts}/{expected} hosts; registering the farm ...")
    r = sh([VENV_PY, "register_hosts.py"], cwd=FARM, timeout=300)
    log("  " + (r.stdout.strip().splitlines() or ["registered"])[-1])


def start_fake_rqd(threads, mem_failure_rate=0.0):
    log(f"starting fake RQD (reporter threads={threads}"
        + (f", mem_failure_rate={mem_failure_rate:.0%}" if mem_failure_rate > 0 else "")
        + ") ...")
    spawn(["fake_rqd.py", str(threads), str(mem_failure_rate)], RQD_LOG)
    for _ in range(30):
        log_txt = read_text(RQD_LOG)
        if "listening" in log_txt:
            log("  fake RQD up")
            return
        if "Address already in use" in log_txt:
            log("  WARN fake RQD: port 8444 already in use (stale process?); "
                "see rqd.log")
            return
        time.sleep(1)
    log("  WARN fake RQD startup not confirmed (see rqd.log)")


def start_pinger(interval, expected):
    log(f"starting host+frame status reporter (rqd_report, interval={interval}s) ...")
    spawn(["rqd_report.py", str(interval)], PINGER_LOG)
    for _ in range(20):
        up = psql("SELECT count(*) FROM host_stat WHERE ts_ping > now() - interval '15 seconds';")
        try:
            if int(up.stdout.strip() or 0) >= expected:
                log(f"  {expected} hosts UP")
                return
        except ValueError:
            pass
        time.sleep(2)
    log("  WARN not all hosts confirmed UP yet (pinger keeps trying)")


# ---------------------------------------------------------------- workload
def submit_jobs(njobs, seed):
    log(f"submitting {njobs} deterministic jobs (seed base {seed}) ...")
    code = (
        f"import sys,random; sys.path.insert(0,{FARM + '/opencue_proto'!r});"
        f"sys.path.insert(0,{FARM!r});"
        "import grpc,job_pb2,job_pb2_grpc,gen_jobs,farm_spec;"
        "ch=grpc.insecure_channel(farm_spec.GRPC);"
        "grpc.channel_ready_future(ch).result(timeout=15);"
        "st=job_pb2_grpc.JobInterfaceStub(ch);"
        f"[ (random.seed({seed}+i), st.LaunchSpec(job_pb2.JobLaunchSpecRequest("
        "spec=gen_jobs.SPEC_HEAD+gen_jobs.make_job(i)+'</spec>\\n'))) "
        f"for i in range({njobs}) ];"
        "print('submitted')")
    r = sh([VENV_PY, "-c", code], cwd=FARM, timeout=300)
    log("  " + (r.stdout.strip() or r.stderr.strip()[-200:] or "done"))


def start_feeder(duration, target):
    dep = int(os.environ.get("SIM_DEP_TREE_DEPTH", "3"))
    kind = f"dependency trees, depth {dep}" if dep >= 2 else "independent jobs"
    log(f"starting paced feeder (hold ~{target} runnable frames for {duration}s; {kind}) ...")
    spawn(["feed.py", str(duration), str(target)], FEED_LOG)


def _strand_env(cores, dur_mix):
    env_extra = {"SIM_STRAND_CORES": str(cores)}
    if dur_mix:
        env_extra["SIM_STRAND_DUR_MIX"] = "1"
    return env_extra


def precreate_big(duration, interval, cores=64, dur_mix=False):
    """Stage the wide jobs PAUSED before the feeder starts. cuebot's job-launch
    queue is one thread / 100 deep (applicationContext-service.xml); once the
    feeder floods it with dependency-tree submissions a big job's launch can starve
    and the job silently never exists -- leaving the reservation test empty. Creating
    them paused on an idle queue guarantees they materialise; start_big_injector
    resumes them after saturation. Synchronous so it finishes before the feeder runs."""
    log(f"pre-creating paused {cores}-core wide jobs (idle launch queue) ...")
    r = sh([VENV_PY, "inject_big.py", "precreate", str(duration), str(interval)],
           cwd=FARM, env=dict(os.environ, **_strand_env(cores, dur_mix)), timeout=180)
    log("  " + ((r.stdout.strip() or r.stderr.strip())[-200:] or "staged"))


def start_big_injector(duration, interval, cores=64, dur_mix=False):
    shape = ("two duration classes (short vs long per-frame time)" if dur_mix
             else "mixed equal/high priority")
    log(f"starting BIG-job injector (resume {cores}-core paused jobs every "
        f"{interval}s for {duration}s, {shape}) ...")
    spawn(["inject_big.py", str(duration), str(interval)], f"{FARM}/inject_big.log",
          env_extra=_strand_env(cores, dur_mix))


def start_priority_starve_injector(duration, interval):
    log(f"starting PRIORITY_STARVING injector (two paced streams: "
        f"pri{os.environ.get('SIM_PRI_HI','300')} HIGH vs "
        f"pri{os.environ.get('SIM_PRI_LO','100')} LOW; phase 1 saturates with HIGH, "
        f"then LOW contends, for {duration}s) ...")
    spawn(["inject_priority_starve.py", str(duration), str(interval)],
          f"{FARM}/inject_priority_starve.log")


def start_priority_spread_injector(duration):
    log(f"starting PRIORITY spread injector ({len(os.environ.get('SIM_SPREAD_PRIS','10,20,30,40,50,60,70,80,90,100').split(','))} "
        f"priority classes, no prefill, all contend from t=0, for {duration}s) ...")
    spawn(["inject_priority_spread.py", str(duration)],
          f"{FARM}/inject_priority_spread.log")


def start_limit_injector(duration):
    log(f"starting LIMIT injector (flood '{os.environ.get('SIM_LIMIT_NAME','simlic')}'"
        f"-limited frames, cap {os.environ.get('SIM_LIMIT_MAX','50')}, for {duration}s) ...")
    spawn(["inject_limit.py", str(duration)], f"{FARM}/inject_limit.log")


def start_folder_injector(duration):
    log(f"starting FOLDER injector (flood the sim folder, cap "
        f"{os.environ.get('SIM_FOLDER_MAX','50')} cores, for {duration}s) ...")
    spawn(["inject_folder.py", str(duration)], f"{FARM}/inject_folder.log")


# ------------------------------------------------------- Rust scheduler (rust)
def start_redis():
    """Start a throwaway Redis for the Rust scheduler's accounting (no
    persistence). Reused if one is already up; the scheduler force-reseeds Redis
    from Postgres on startup, so a stale instance is harmless."""
    if port_open(REDIS_PORT):
        log(f"redis already up on :{REDIS_PORT}")
        return
    log(f"starting redis on :{REDIS_PORT} (ephemeral, no persistence) ...")
    logf = open("/tmp/redis-sim.log", "w")
    subprocess.Popen(
        ["redis-server", "--port", str(REDIS_PORT), "--save", "",
         "--appendonly", "no", "--dir", "/tmp"],
        stdout=logf, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(30):
        if port_open(REDIS_PORT):
            log("  redis up")
            return
        time.sleep(1)
    sys.exit("redis failed to start; see /tmp/redis-sim.log")


def set_scheduler_managed(managed):
    """Flip the sim show's b_scheduler_managed flag. true hands the show to the
    Rust scheduler (and, via migration V45, makes cuebot's own dispatch skip it);
    false restores it to cuebot, so a later --mode new/old run is never left
    stranded by a previous --mode rust run."""
    val = "true" if managed else "false"
    psql(f"UPDATE show SET b_scheduler_managed={val} WHERE pk_show='{SHOW}';")
    log(f"  show b_scheduler_managed={val}")


def write_scheduler_yaml(tick_ms, facility, dry_run=True):
    """Write the cue-scheduler config: point it at the sim's Postgres and Redis,
    E-PVM placement (the same family the --mode new planner uses). dry_run=True
    (default) books in the DB without a real RQD launch (rqd_complete.py drives
    completion) -- the practical mode. dry_run=False (--rust-real-launch) makes the
    scheduler call LaunchFrame on fake_rqd, the same path --mode new uses, for an
    equal-footing comparison; it's launch-latency-bound and much slower."""
    interval_s = max(1, tick_ms // 1000)
    cfg = f"""logging:
  level: info,sqlx=warn
database:
  db_host: 127.0.0.1
  db_port: {PG_PORT}
  db_name: cuebot
  db_user: cue
  db_pass: ""
rqd:
  dry_run_mode: {str(dry_run).lower()}
queue:
  monitor_interval: {interval_s}s
  # Sim-tuned for responsiveness (production uses longer to cut idle DB load):
  # empty_sleep = how long a cluster naps after a pass with no work; reload =
  # how often the managed-show cluster set is re-derived from live host tags
  # (so a farm registered just before startup, or grown mid-run, is picked up).
  cluster_empty_sleep: 5s
  cluster_reload_interval: 30s
  # Dispatch fan-out. Defaults are 3/3; with a real RQD launch awaited inline in
  # the dispatch path, low concurrency means booking is launch-latency-bound. Bump
  # both so many jobs/clusters dispatch (and launch) concurrently.
  stream:
    cluster_buffer_size: 8
    job_buffer_size: 64
  host_booking_strategy:
    type: epvm
    max_candidates: 500
    weights: {{ cores: 1.0, mem: 1.0, gpus: 2.0, gpu_mem: 1.0, gpu_count_reservation: 2.0, gpu_mem_reservation: 2.0 }}
accounting:
  redis:
    host: 127.0.0.1
    port: {REDIS_PORT}
scheduler:
  facility: {facility}
"""
    with open(SCHEDULER_YAML, "w") as f:
        f.write(cfg)
    log(f"  wrote scheduler config {SCHEDULER_YAML}")


def ensure_resolver_shim():
    """Compile (once) the getaddrinfo LD_PRELOAD shim (resolve_local.c) and return
    the .so path. The Rust scheduler is a native binary, so the JVM hosts file
    (-Djdk.net.hosts.file) cuebot uses can't redirect its per-host RQD dials
    (http://<host.name>:8444) to fake_rqd. The shim is the native analog: glibc
    getaddrinfo is intercepted and every named lookup sent to loopback (every sim
    target -- Postgres, Redis, each farm host's RQD -- is local). Only needed for
    --rust-real-launch. The .c source is committed; the .so is a build artifact."""
    src = os.path.join(SIM_DIR, "resolve_local.c")
    so = os.path.join(FARM, "resolve_local.so")
    if not os.path.exists(so):
        r = subprocess.run(["gcc", "-shared", "-fPIC", "-o", so, src, "-ldl"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"failed to build resolver shim from {src}:\n{r.stderr}")
        log(f"  built RQD resolver shim {so}")
    return so


def start_rust_scheduler(facility, ld_preload=None):
    """Launch the real cue-scheduler binary against the sim's Postgres + Redis.
    With ld_preload set (non-dry-run), the scheduler's per-host RQD dials resolve
    to fake_rqd via the getaddrinfo shim."""
    if not os.path.exists(SCHEDULER_BIN):
        sys.exit(
            f"cue-scheduler binary not found at {SCHEDULER_BIN}.\n"
            f"  Build it:  (cd {os.path.join(REPO_ROOT, 'rust')} && "
            f"cargo build -p scheduler)\n"
            f"  or set SIM_SCHEDULER_BIN to its path.")
    log(f"starting Rust scheduler (cue-scheduler, facility={facility}, E-PVM, "
        f"{'real-launch' if ld_preload else 'dry-run'}) ...")
    env = dict(os.environ)
    env["OPENCUE_SCHEDULER_CONFIG"] = SCHEDULER_YAML
    if ld_preload:
        env["LD_PRELOAD"] = (ld_preload + " " + env["LD_PRELOAD"]) \
            if env.get("LD_PRELOAD") else ld_preload
    logf = open(SCHEDULER_LOG, "w")
    subprocess.Popen([SCHEDULER_BIN, "--facility", facility], cwd=FARM,
                     stdout=logf, stderr=subprocess.STDOUT,
                     start_new_session=True, env=env)
    for i in range(60):
        txt = read_text(SCHEDULER_LOG)
        if "Starting scheduler feed" in txt:
            log(f"  Rust scheduler up after ~{i}s (metrics :9090)")
            return
        if "panicked" in txt or "Failed to load config" in txt or "Error:" in txt:
            sys.exit(f"cue-scheduler failed to start; see {SCHEDULER_LOG}")
        time.sleep(1)
    log(f"  WARN Rust scheduler start not confirmed; see {SCHEDULER_LOG}")


def start_rust_completer(mem_failure_rate=0.0):
    """Start the DB-poll completion driver (rqd_complete.py): it finds frames the
    Rust scheduler booked (dry-run) and reports them complete to cuebot after their
    modeled run-time -- the dry-run analogue of fake_rqd."""
    log("starting Rust-scheduler completion driver (rqd_complete, DB-poll) ...")
    spawn(["rqd_complete.py", "0.5", str(mem_failure_rate)], RUST_COMPLETE_LOG)
    for _ in range(30):
        if "polling proc table" in read_text(RUST_COMPLETE_LOG):
            log("  completion driver up")
            return
        time.sleep(1)
    log(f"  WARN completion driver start not confirmed; see {RUST_COMPLETE_LOG}")


# ---------------------------------------------------------------- main
def _verify_peak_util(gdir):
    """Peak util_pct (%) from a scenario's util CSV, or 0 if unreadable."""
    import csv
    try:
        rows = list(csv.DictReader(open(os.path.join(gdir, "run_util.csv"))))
        return max((float(r["util_pct"]) for r in rows), default=0.0)
    except Exception:
        return 0.0


def _verify_check(name, gdir, logp, cblog):
    """Return (passed, detail) for one verify scenario, read from its cuebot log
    (OOM / reservations) or its stdout log (priority)."""
    import re
    try:
        cb = open(cblog, errors="ignore").read()
    except Exception:
        cb = ""
    if name == "OOM":
        # The per-frame OOM path must handle the kills and the legacy
        # whole-layer ratchet must never fire, while the farm still fills.
        bumps = cb.count("per-frame mem bump to:")
        legacy = cb.count("Increased mem usage to:")
        util = _verify_peak_util(gdir)
        ok = legacy == 0 and bumps > 0 and util >= 40
        return ok, f"{bumps} per-frame bumps, {legacy} legacy ratchets, peak util {util:.0f}%"
    if name == "PRIORITY_STARVING":
        # Gate on priority_starve_watch.py's OWN verdict, not share>0. It prints
        # "FAIL (starvation)" when LOW's completed-frame share falls below its 3%
        # floor (or LOW completes nothing) -- exactly the strict-ordering regression
        # the lottery must prevent; a >0 gate would pass a ~1% leak. We gate at that
        # starvation floor rather than the watcher's ~proportional PASS band
        # (0.5*EXPECT_LO = 12.5% for the 100-vs-300 mix): the lottery's guarantee is
        # anti-starvation (a priority-weighted rate), and reaching full proportional
        # share needs a longer window than the self-test runs, so a WARN (progress,
        # below the band) still passes.
        try:
            txt = open(logp, errors="ignore").read()
        except Exception:
            txt = ""
        m = re.search(r"LO share of completed frames:\s*([\d.]+)%", txt)
        share = float(m.group(1)) if m else 0.0
        ok = bool(m) and "FAIL (starvation)" not in txt
        return ok, f"low-priority share {share:.1f}% (starved/FAIL if <3%)"
    if name == "PRIORITY":
        # PRIORITY (spread): completion share must be ORDERED by priority across the
        # class spectrum -- the everyday proportional-rate case. Gate on
        # priority_spread_watch.py's verdict (Spearman rho >= its threshold), read
        # from the scenario stdout log. Exact proportions are NOT required (the
        # lowest classes run a little over their strict share, the top a little
        # under -- see priority_spread_watch.py).
        try:
            txt = open(logp, errors="ignore").read()
        except Exception:
            txt = ""
        m = re.search(r"Spearman rho\(priority, share\) = ([\-\d.]+)", txt)
        rho = float(m.group(1)) if m else 0.0
        ok = bool(re.search(r"(?m)^PASS:", txt))
        return ok, f"share ordered by priority (Spearman rho={rho:.2f})"
    if name == "RESERVATIONS":
        # A reservation only counts if it RESCUES the stranded wide job -- its
        # frames must actually run. reservedCores>0 alone is hollow: a drain that
        # never finishes leaves the job stranded forever, which IS the failure this
        # scenario must catch. Query the DB for big-job frames that ran; require >0.
        try:
            out = psql("SELECT COALESCE(sum((SELECT count(*) FROM frame f "
                       "WHERE f.pk_layer=l.pk_layer AND f.str_state IN "
                       "('RUNNING','SUCCEEDED'))),0) FROM layer l "
                       "JOIN job j ON j.pk_job=l.pk_job "
                       "WHERE j.str_name LIKE '%big%'").stdout.strip()
            ran = int(out or "0")
        except Exception:
            ran = 0
        peak = max([int(x) for x in re.findall(r"reservedCores=(\d+)", cb)] or [0])
        ok = ran > 0
        return ok, f"{ran} stranded big frames rescued+ran (peak reservedCores {peak})"
    if name == "LIMIT":
        # The scheduler must never run more than the limit's cap concurrently.
        # Gate on limit_watch.py's verdict (PASS only if peak running <= cap AND the
        # backlog wanted more), read from the scenario stdout log.
        try:
            txt = open(logp, errors="ignore").read()
        except Exception:
            txt = ""
        cm = re.search(r"cap=(\d+)", txt)
        pm = re.search(r"peak concurrent running=(\d+)", txt)
        cap = int(cm.group(1)) if cm else -1
        peak = int(pm.group(1)) if pm else -1
        ok = bool(re.search(r"(?m)^PASS:", txt))
        return ok, f"peak concurrent running {peak} vs cap {cap}"
    if name == "FOLDER":
        # The scheduler must never run more than the folder's core cap. Gate on
        # folder_watch.py's verdict, read from the scenario stdout log.
        try:
            txt = open(logp, errors="ignore").read()
        except Exception:
            txt = ""
        cm = re.search(r"cap=(\-?\d+) cores", txt)
        pm = re.search(r"peak running=(\d+) cores", txt)
        cap = int(cm.group(1)) if cm else -1
        peak = int(pm.group(1)) if pm else -1
        ok = bool(re.search(r"(?m)^PASS:", txt))
        return ok, f"peak folder running {peak} vs cap {cap} cores"
    return False, "unknown scenario"


def run_verify():
    """Run the OOM, priority and reservation scenarios back-to-back. Each is a
    separate simulate.py subprocess, so it does its own full teardown + fresh
    Postgres on startup (never contaminating the next) and writes its own graph
    set. Prints a PASS/FAIL summary; returns a process exit code (0 = all pass).
    Per-scenario duration from SIM_VERIFY_SECONDS (default 180)."""
    D = int(os.environ.get("SIM_VERIFY_SECONDS", "180"))
    base = [VENV_PY, os.path.abspath(__file__), "--mode", "new", "--compress", "8"]
    cblog = "/tmp/cuebot-new.log"   # every scenario runs --mode new
    scenarios = [
        ("OOM", ["--feed", str(D), "--mem-failure-rate", "0.1"]),
        # PRIORITY: 10 priority classes contend; share of completions must rise
        # with priority (Spearman rho). Run on a SMALL farm (~10% = 5760 cores) so
        # the injector's fixed backlog (2000 waiting/class x ~2.5 cores x 10 =
        # ~50k core-demand) HEAVILY oversubscribes it (~9x). That heavy
        # oversubscription is the whole point: only then does the lottery cut the
        # low-priority tail each tick and shares track priority (rho ~0.98,
        # near-proportional). On the FULL farm the same backlog is only ~1.05x
        # oversubscribed -- nearly every candidate books every tick, so shares
        # flatten to ~1/N and priority looks absent (rho ~0.67). --compress 4 so
        # frames complete fast enough to accumulate a meaningful per-class tally.
        ("PRIORITY", ["--hosts", "25,30,100", "--compress", "4",
                      "--priority-spread", str(D)]),
        # PRIORITY_STARVING: the adversarial edge -- a deep HIGH flood; LOW must
        # merely survive above the 3% starvation floor.
        ("PRIORITY_STARVING", ["--priority-starve", str(D)]),
        # RESERVATIONS: 64-core wide jobs (half a large -- matches the scheduler's
        # 64-core reservation clamp) on a TINY farm with SHORT frames. Rationale:
        #  - tiny farm: the feeder saturates it to ~100%, so the wide jobs genuinely
        #    cannot fit and must strand (the full farm caps near ~88% util, leaving
        #    open jaimes the wide job grabs opportunistically -- flaky, no reserve);
        #  - short frames (--compress 4): a reserved host DRAINS in ~one frame-time,
        #    so the reservation finishes and the job actually RUNS within the run.
        #    128-core whole-host jobs with long frames never finished draining, so
        #    they stranded forever -- reservation "requested" but the job never ran.
        # The check asserts the stranded big jobs RAN (were rescued), not the hollow
        # reservedCores>0. Fixed durations (a tiny farm needs far less than D).
        ("RESERVATIONS", ["--hosts", "10,12,40", "--compress", "4",
                          "--reservations", "--reservation-block-seconds", "15",
                          "--feed", "200", "--strand", "140"]),
        # LIMIT: a global license cap (limit_record.int_max_value). Attach one
        # limit (cap SIM_LIMIT_MAX=50) to a deep flood of 1-core frames on a small
        # farm (672 cores) that could otherwise run hundreds at once, and assert
        # concurrent running never exceeds the cap. Inherits --compress 8 so frames
        # run long enough for concurrency to accumulate.
        ("LIMIT", ["--hosts", "3,4,10", "--limit-test", str(D)]),
        # FOLDER: a folder/group core cap (folder_resource.int_max_cores). Cap the
        # sim folder at 50 cores and flood narrow work into it on a small farm that
        # could run far more, and assert folder running cores never exceed the cap.
        ("FOLDER", ["--hosts", "3,4,10", "--folder-test", str(D)]),
    ]
    results = []
    for name, flags in scenarios:
        gdir = os.path.join("/tmp/scheduler-sim/verify", name.lower())
        logp = gdir + ".log"
        os.makedirs(gdir, exist_ok=True)
        log(f"[verify] === {name}: fresh sim (teardown + reinit) for {D}s ===")
        env = dict(os.environ, SIM_GRAPH_DIR=gdir)
        with open(logp, "w") as lf:
            subprocess.run(base + flags, env=env, stdout=lf,
                           stderr=subprocess.STDOUT, cwd=FARM)
        ok, detail = _verify_check(name, gdir, logp, cblog)
        results.append((name, ok, detail, gdir))
        log(f"[verify] {name}: {'PASS' if ok else 'FAIL'} ({detail})")

    print("\n=== SIM VERIFY ===")
    for name, ok, detail, gdir in results:
        print(f"{name:<13}: {'PASS' if ok else 'FAIL'}    {detail}")
        print(f"{'':13}  graphs -> {gdir}")
    allok = all(ok for _, ok, _, _ in results)
    print("\n" + ("ALL PASS" if allok else "SOME FAILED"))
    return 0 if allok else 1


def main():
    # If we're root, drop to a non-root user and re-run (postgres/cuebot refuse
    # root). For a normal user this is a no-op and nothing uses sudo.
    reexec_as_nonroot_if_needed()
    # Raise the open-file limit now (we're the final, non-root process): every
    # cuebot/fake_rqd/sampler we spawn inherits it. The default 1024 starves
    # cuebot's per-host RQD channel cache at farm scale (see set_fd_limit).
    set_fd_limit()
    # Make sure we're under an interpreter that has grpc (re-exec under the
    # sim's venv if not), so the helpers we spawn never die at `import grpc`.
    ensure_grpc_interpreter()
    ensure_buildable()
    ensure_proto_stubs()
    ap = argparse.ArgumentParser(description="One-command fresh scheduler sim")
    ap.add_argument("--mode", choices=["new", "old", "rust"], default="new",
                    help="new=cuebot's E-PVM planner; old=legacy cuebot booking; "
                         "rust=the standalone cue-scheduler binary "
                         "(rust/crates/scheduler) plans+books while cuebot runs "
                         "with booking off as the completion engine. rust mode "
                         "needs Redis and a built cue-scheduler binary.")
    ap.add_argument("--cuebots", type=int, default=2, metavar="N",
                    help="number of cuebot instances to run against the same "
                         "Postgres (default 2). All race the advisory lock so one "
                         "plans per tick: this exercises leader election / HA. Set "
                         "1 for a single-cuebot run. Instance 0 runs via bootRun and "
                         "owns the gRPC/RQD/feeder traffic; extras run from the jar "
                         "on offset ports and only join to plan.")
    ap.add_argument("--jobs", type=int, default=0,
                    help="submit N fixed deterministic jobs at start")
    ap.add_argument("--seed", type=int, default=9000)
    ap.add_argument("--feed", type=int, default=0,
                    help="run paced feeder for SECONDS (sustained backlog)")
    ap.add_argument("--feed-target", type=int, default=40000)
    ap.add_argument("--dep-tree-depth", type=int, default=3, metavar="D",
        help="job dependency tree depth (VFX work is rarely standalone). Each "
             "feeder submission is an UNBALANCED tree of JOB_ON_JOB-linked jobs of "
             "max depth D, declared in the spec; cuebot creates the depends, parks "
             "descendants in DEPEND, and unblocks them as parents finish. Only the "
             "root is runnable at submit. 1 = independent jobs (no depends). Default 3.")
    ap.add_argument("--reporter-threads", type=int, default=64,
                    help="fake_rqd completion-report concurrency (default 64). A "
                         "real farm has thousands of RQDs reporting in parallel; "
                         "a serial reporter instead caps completion throughput at "
                         "1/ack-latency (~18 frames/s at 54ms/report) and lets "
                         "finished frames pile up unreported, so the farm looks "
                         "fully utilized (cores still booked) while almost nothing "
                         "completes. 64 keeps reporting off the critical path at "
                         "full-farm scale so throughput reflects the scheduler.")
    ap.add_argument("--rust-real-launch", action="store_true",
                    help="--mode rust ONLY: run the Rust scheduler non-dry-run so it "
                         "actually calls LaunchFrame on fake_rqd (same RQD path as "
                         "--mode new), instead of the default dry-run + rqd_complete.py "
                         "DB-poll. Resolves farm host names to fake_rqd via the "
                         "resolve_local.c LD_PRELOAD getaddrinfo shim (needs gcc). "
                         "NOTE: the Rust scheduler awaits each launch inline through a "
                         "single dispatcher actor, so this is launch-latency-bound and "
                         "far slower than dry-run -- useful to observe the launch cost, "
                         "not for throughput. Dry-run is the practical default.")
    ap.add_argument("--compress", type=float, default=None,
                    help="sim duration compression (SIM_COMPRESS); higher=longer "
                         "frames=lower lifecycle rate. Default uses sim_model's 0.27")
    ap.add_argument("--metrics", type=int, default=0,
                    help="run metrics.py for SECONDS (reserved-util view)")
    ap.add_argument("--stats", type=int, default=0,
                    help="run stats.py for SECONDS: honest LIVE util (cores "
                         "backing RUNNING frames), zombie-proc leak detector, "
                         "per-type breakdown, steady-state averages")
    ap.add_argument("--heartbeat-interval", type=float, default=None,
                    help="seconds the reporter SLEEPS between full report rounds. "
                         "Mode-aware default (override to pin any value): 5.0 for "
                         "NEW, 0.1 for OLD and rust. OLD's report-driven booker only "
                         "books a host WHEN it reports, so it needs the fast "
                         "heartbeat or the farm never fills. NEW (the planner) is "
                         "the opposite: its cuebot books AND processes reports, so a "
                         "0.1s flood from 1553 hosts (~10 reports/host/s, ~100x a "
                         "real farm) overruns the host-report handler (~200ms DB "
                         "work each), completions back up, frames pile up in RUNNING "
                         "holding cores, util pegs at 100% and throughput collapses; "
                         "5s keeps it ahead. rust's cuebot has booking OFF (it only "
                         "drains completions via rqd_complete through the same "
                         "handler), so it absorbs the 0.1s cadence fine and that is "
                         "what it was validated under. Also keeps proc.ts_ping fresh "
                         "for the 300s orphan sweep.")
    ap.add_argument("--hosts", type=str, default=None,
                    help="SMALL-FARM debug mode: 'large,medium,small' counts, e.g. "
                         "'2,3,5'. Shrinks the farm (removes all other hosts and "
                         "re-registers just this set) so booking dynamics are easy "
                         "to watch. Default: full 1553-host farm.")
    ap.add_argument("--tags", type=int, nargs="?", const=8, default=0, metavar="N",
                    help="scatter N RANDOM capability tags across the farm (no "
                         "value => 8): each host gets one random tag, each job "
                         "requests one random feasible tag, so EVERY job is "
                         "confined to a random ~1/N scattered slice of the farm. "
                         "Unlike clean size-class tags this fragments placement "
                         "(idle cores in one pool can't absorb another's waiting "
                         "work) and stresses the scheduler. 0/absent = off.")
    ap.add_argument("--gpu", type=float, default=0.0, metavar="F",
                    help="GPU pools: fraction F of the farm is GPU-capable (drawn "
                         "only from medium/small hosts) and fraction F of layers are GPU "
                         "layers (4 cores + 1 GPU + gpu_memory, cpu mem = half the "
                         "gpu mem). GPU layers place only on GPU hosts (enforced by "
                         "cuebot). Default 0 (no GPU). Typical: 0.1.")
    ap.add_argument("--reservations", action="store_true",
                    help="enable the planner's host reservations for blocked "
                         "layers (EASY/Maui-style: time gate + per-class cap). "
                         "Default off. Use with --strand to show big jobs no "
                         "longer starve.")
    ap.add_argument("--reservation-block-seconds", type=int, default=60,
                    metavar="SECS",
                    help="how long a layer must be continuously blocked before "
                         "it may reserve (default 60 for the sim; production "
                         "default is 300 = 5 min).")
    ap.add_argument("--reservation-max-fraction", type=float, default=0.5,
                    metavar="F",
                    help="reservations may hold at most this fraction of the "
                         "hosts that can fit a layer (default 0.5), so a host "
                         "class is never fully reserved.")
    ap.add_argument("--reservation-max-grantees", type=int, default=8,
                    metavar="K",
                    help="maximum new reservation grants per tick (default 8). "
                         "Caps O(layers x hosts) work at full-farm scale; "
                         "existing holders always reconcile regardless of K.")
    ap.add_argument("--no-backfill", dest="backfill", action="store_false",
                    help="disable EASY backfill (Lifka 1995). By default a "
                         "reserved host lets short lower-priority frames run on "
                         "its free cores while it drains, as long as they finish "
                         "before the reserved (wide) job needs it. Disabling "
                         "freezes reserved hosts idle until they drain.")
    ap.set_defaults(backfill=True)
    ap.add_argument("--priority-starve", type=int, default=0, metavar="SECS",
                    help="PRIORITY_STARVING test: flood the farm with two identical "
                         "narrow-job streams differing ONLY in priority "
                         "(SIM_PRI_HI=300 vs SIM_PRI_LO=100), the high stream deep "
                         "enough to fill the farm alone, and watch each stream's "
                         "frames/s for SECS. Strict priority starves the low stream "
                         "(FAIL); stochastic priority keeps it alive above the 3%% "
                         "floor (PASS). The adversarial anti-starvation case.")
    ap.add_argument("--priority-spread", type=int, default=0, metavar="SECS",
                    help="PRIORITY test: contend the farm with N (default 10) narrow-"
                         "job streams at priorities 10,20,...,100 (SIM_SPREAD_PRIS), "
                         "moderate backlog each, NO prefill, for SECS. Checks that "
                         "completion share is ORDERED by priority (Spearman rho); the "
                         "everyday proportional-rate case, not the starvation edge.")
    ap.add_argument("--limit-test", type=int, default=0, metavar="SECS",
                    help="LIMIT test: attach a global limit (SIM_LIMIT_NAME=simlic, "
                         "cap SIM_LIMIT_MAX=50) to a flood of frames and check the "
                         "scheduler never runs more than the cap concurrently -- the "
                         "license-cap constraint. FAILs if concurrency exceeds the cap.")
    ap.add_argument("--folder-test", type=int, default=0, metavar="SECS",
                    help="FOLDER test: cap the sim folder at SIM_FOLDER_MAX=50 cores "
                         "(folder_resource.int_max_cores) and flood work into it; "
                         "check the scheduler never runs more than the cap. FAILs if "
                         "folder running cores exceed the cap (dept/group core ceiling).")
    ap.add_argument("--priority-interval", type=int, default=20, metavar="SECS",
                    help="seconds between PRIORITY_STARVING top-up submissions "
                         "(default 20)")
    ap.add_argument("--strand", type=int, default=0, metavar="SECS",
                    help="STARVATION TEST: alongside the small feeder, inject "
                         "64-core BIG jobs every --strand-interval seconds "
                         "(mixed equal/high priority) and watch them for SECS. "
                         "Without reservations the big jobs strand: large stays "
                         "packed with small frames and never frees 64 cores at "
                         "once. Needs --feed for the small backlog.")
    ap.add_argument("--strand-interval", type=int, default=30, metavar="SECS",
                    help="seconds between BIG-job injections (default 30, "
                         "'once in a while' like a real facility)")
    ap.add_argument("--strand-cores", type=int, default=64, metavar="N",
                    help="per-frame core width of the BIG jobs (default 64). Use "
                         "128 for whole-large jobs that cannot fit in the "
                         "memory-stranded idle cores of a memory-bound farm, "
                         "forcing a reservation. Values >64 also raise cuebot's "
                         "dispatcher.frame_cores_max clamp so the frame keeps its "
                         "full width.")
    ap.add_argument("--verify", action="store_true",
                    help="SELF-TEST: run the OOM, priority and reservation "
                         "scenarios back-to-back -- each a fresh, fully-torn-down "
                         "sim that also writes its own graphs -- and print a "
                         "PASS/FAIL summary. Per-scenario seconds from "
                         "SIM_VERIFY_SECONDS (default 180); exits nonzero if any "
                         "scenario fails.")
    ap.add_argument("--strand-duration-mix", action="store_true",
                    help="DURATION-FAIRNESS TEST (use with --strand): inject the "
                         "big jobs as two identical classes that differ ONLY in "
                         "per-frame run time -- a short-frame and a long-frame "
                         "class (same 64 cores, memory, priority). Checks whether "
                         "the short class keeps getting through or is starved by "
                         "the long class holding its reserved hosts. Tunable via "
                         "SIM_DUR_SHORT_S / SIM_DUR_LONG_S (default 12s / 120s).")
    ap.add_argument("--mem-failure-rate", type=float, default=0.0,
                    help="fraction of frame completions that report exit_status=33 "
                         "(memory failure). Cuebot then bumps the layer memory by ~2 GB "
                         "and requeues the frame. Default 0 (no failures). "
                         "Example: 0.1 = 10%% of frames fail once with OOM.")
    ap.add_argument("--mem-heavy", type=float, nargs="?", const=24.0, default=0.0,
                    metavar="GB",
                    help="LOW-UTILIZATION TEST: flood the farm with small, "
                         "memory-hungry jobs. Layers are drawn only from the small "
                         "buckets (<= --mem-heavy-max-cores cores) and made to "
                         "demand GB memory on average (bare flag defaults to 24), "
                         "so memory, not cores, becomes the binding constraint. "
                         "Hosts run ~3.5-3.9 GB/core, so e.g. 32 exhausts host RAM "
                         "with most cores still idle and utilization plateaus well "
                         "below 100%%. Off by default.")
    ap.add_argument("--mem-heavy-max-cores", type=int, default=4, metavar="N",
                    help="with --mem-heavy, the largest core count treated as a "
                         "'small' (memory-heavy) layer (default 4).")
    args = ap.parse_args()

    if args.verify:
        sys.exit(run_verify())

    # Heartbeat default is mode-aware (see --heartbeat-interval): only NEW needs
    # the slow 5s rate, because its cuebot books AND processes reports, so a 0.1s
    # flood (1553 hosts x ~10/s) overruns the report handler and stalls it. OLD
    # needs 0.1s for its report-driven booker; rust's cuebot has booking OFF (it
    # only drains completions via rqd_complete through the same handler), so it
    # absorbs 0.1s fine and was validated there, and stays at 0.1s too.
    if args.heartbeat_interval is None:
        args.heartbeat_interval = 5.0 if args.mode == "new" else 0.1

    # Mode-specific cuebot log, so a later run in a different mode (e.g. rust
    # after new) does not clobber this run's scheduler stats / backfill numbers.
    # Honors an explicit SIM_CUEBOT_LOG override.
    global CUEBOT_LOG
    if not os.environ.get("SIM_CUEBOT_LOG"):
        CUEBOT_LOG = f"/tmp/cuebot-{args.mode}.log"
    # Export the resolved path so the watcher children (live_stats / strand_dur_watch,
    # via sim_metrics) read reservation grants from THIS run's cuebot log.
    os.environ["SIM_CUEBOT_LOG"] = CUEBOT_LOG

    if args.compress is not None:
        os.environ["SIM_COMPRESS"] = str(args.compress)  # inherited by feeder/rqd
    if args.hosts:
        os.environ["SIM_HOST_COUNTS"] = args.hosts  # inherited by all helpers
    if args.tags:
        os.environ["SIM_NTAGS"] = str(args.tags)  # inherited by all helpers
    if args.gpu:
        os.environ["SIM_GPU"] = str(args.gpu)  # inherited by all helpers
    if args.mem_heavy > 0:
        os.environ["SIM_MEM_HEAVY_GB"] = str(args.mem_heavy)  # inherited by feeder
        os.environ["SIM_MEM_HEAVY_MAX_CORES"] = str(args.mem_heavy_max_cores)
        log(f"MEM-HEAVY low-util test: layers <= {args.mem_heavy_max_cores} cores "
            f"average {args.mem_heavy:g} GB (memory-bound; cores will strand)")
    os.environ["SIM_DEP_TREE_DEPTH"] = str(args.dep_tree_depth)  # job dep trees; inherited by feeder

    # Expected host count: small farm honors --hosts, else the full farm.
    sys.path.insert(0, FARM)
    import farm_spec
    import importlib
    importlib.reload(farm_spec)  # pick up SIM_HOST_COUNTS set above
    expected_hosts = farm_spec.total_hosts()
    if args.hosts:
        log(f"SMALL-FARM mode: {expected_hosts} hosts "
            f"({farm_spec.total_cores()} cores) — counts {args.hosts}")
    if args.tags:
        from collections import Counter
        hc = Counter(farm_spec.host_tags(n)[-1] for n, _, _ in farm_spec.all_hosts())
        log(f"RANDOM CAPABILITY TAGS on (N={args.tags}) — hosts per pool: "
            f"{dict(sorted(hc.items()))}. Every job is pinned to one random pool "
            f"(a ~1/N scattered slice of the farm), so idle cores in one pool "
            f"cannot absorb another pool's waiting work — placement is fragmented.")
    if args.gpu:
        gpu_hosts = sum(1 for n, c, m in farm_spec.all_hosts()
                        if farm_spec.host_gpu(n, c, m)[0] > 0)
        gpu_units = sum(farm_spec.host_gpu(n, c, m)[0] for n, c, m in farm_spec.all_hosts())
        log(f"GPU: {args.gpu:.0%} of farm GPU-capable — {gpu_hosts}/{expected_hosts} "
            f"hosts ({gpu_units} GPUs total), {args.gpu:.0%} of layers are GPU layers")

    t0 = time.time()
    install_cleanup_handlers()   # reap this run's children on any exit path
    teardown()
    ensure_postgres()
    rust = (args.mode == "rust")
    if rust:
        start_redis()
    write_sim_hosts_file()
    nhosts = reset_db()
    # Hand the show to whichever scheduler owns it: the standalone Rust scheduler
    # (rust mode), or the Java planner in per-show 'managed' mode. Otherwise force
    # the flag OFF so a leftover true can't make cuebot's own dispatch skip the
    # show (migration V45 filters b_scheduler_managed=false).
    set_scheduler_managed(rust or os.environ.get("SIM_SCHEDULER_ENABLED") == "managed")
    ensure_cuebot_built()
    if rust:
        # One cuebot, scheduler OFF + booking OFF: it neither plans nor books, it
        # only handles RQD reports/completions and maintains frame/layer/job
        # stats. The cue-scheduler binary does all planning and booking.
        start_cuebot("old", booking_off=True)
        # Bring the farm up (registered + reporting UP) BEFORE the scheduler: it
        # derives its cluster set from live host tags at startup and only reloads
        # every queue.cluster_reload_interval, so a scheduler started against an
        # empty farm idles until the first reload. Started last, against a ready
        # farm, it plans from its very first tick -- like production.
        ensure_hosts(nhosts, expected_hosts)
        start_pinger(args.heartbeat_interval, expected_hosts)
        real = args.rust_real_launch
        write_scheduler_yaml(int(os.environ.get("SIM_TICK_MS", "3000")),
                             farm_spec.FACILITY, dry_run=not real)
        if real:
            # --rust-real-launch: fake_rqd is the RQD for rust too -- the scheduler
            # calls LaunchFrame on it (same path as --mode new) and it drives
            # completion. Started before the scheduler so the first launches land.
            # The scheduler dials each host by name (http://<host.name>:8444); the
            # LD_PRELOAD shim resolves those to fake_rqd on loopback (the native
            # analog of cuebot's JVM hosts file).
            start_fake_rqd(args.reporter_threads, args.mem_failure_rate)
            start_rust_scheduler(farm_spec.FACILITY,
                                 ld_preload=ensure_resolver_shim())
        else:
            # Default: dry-run. The scheduler books straight into Postgres (no RQD
            # launch); rqd_complete.py polls the proc table and reports each booked
            # frame complete to cuebot after its sim_model run-time.
            start_rust_scheduler(farm_spec.FACILITY)
            start_rust_completer(args.mem_failure_rate)
    else:
        # Whole-host wide jobs (--strand-cores > 64) need the per-frame clamp
        # raised (core-points) so cuebot does not cap them back to 64.
        frame_cores_max = args.strand_cores * 100 if args.strand_cores > 64 else 0
        start_cuebot(args.mode, args.reservations,
                     args.reservation_block_seconds, args.reservation_max_fraction,
                     args.reservation_max_grantees, args.backfill,
                     frame_cores_max=frame_cores_max)
        for i in range(1, max(1, args.cuebots)):
            start_extra_cuebot(i, args.mode, args.reservations,
                               args.reservation_block_seconds, args.reservation_max_fraction,
                               args.reservation_max_grantees, args.backfill,
                               frame_cores_max=frame_cores_max)
        if args.cuebots > 1:
            log(f"{args.cuebots} cuebots up, sharing the Postgres advisory lock "
                f"(one plans per tick)")
        ensure_hosts(nhosts, expected_hosts)
        start_fake_rqd(args.reporter_threads, args.mem_failure_rate)
        start_pinger(args.heartbeat_interval, expected_hosts)

    if args.jobs:
        submit_jobs(args.jobs, args.seed)
    # Stage wide jobs PAUSED on an idle launch queue BEFORE the feeder floods it,
    # so they reliably materialise; start_big_injector resumes them post-saturation.
    if args.strand:
        precreate_big(args.strand, args.strand_interval,
                      cores=args.strand_cores, dur_mix=args.strand_duration_mix)
    if args.feed:
        start_feeder(args.feed, args.feed_target)
    if args.strand:
        start_big_injector(args.strand, args.strand_interval,
                           cores=args.strand_cores,
                           dur_mix=args.strand_duration_mix)
    if args.priority_starve:
        start_priority_starve_injector(args.priority_starve, args.priority_interval)
    if args.priority_spread:
        start_priority_spread_injector(args.priority_spread)
    if args.limit_test:
        start_limit_injector(args.limit_test)
    if args.folder_test:
        start_folder_injector(args.folder_test)

    log(f"stack is UP and fresh in {time.time()-t0:.0f}s  "
        f"(mode={args.mode}).")
    if rust:
        completer = f"rqd={RQD_LOG}" if real else f"complete={RUST_COMPLETE_LOG}"
        log(f"logs: cuebot={CUEBOT_LOG}  scheduler={SCHEDULER_LOG}  "
            f"{completer}  pinger={PINGER_LOG}"
            + (f"  feed={FEED_LOG}" if args.feed else ""))
    else:
        log(f"logs: cuebot={CUEBOT_LOG}  rqd={RQD_LOG}  pinger={PINGER_LOG}"
            + (f"  feed={FEED_LOG}" if args.feed else ""))

    # Live consolidated stats (util, frames/s, DB, and BIG-job/stranded when
    # big jobs are present) stream by default for the duration of whatever phase
    # is active, so a run can be watched without querying the DB by hand.
    watch = (args.strand or args.priority_starve or args.priority_spread
             or args.limit_test or args.folder_test
             or args.stats or args.metrics or args.feed)
    if watch:
        # This run owns the stack for a bounded, watched lifetime: tear it down on
        # a normal exit too (signals always tear down). A non-watch bring-up is
        # left running on purpose for inspection; the next run's teardown reaps it.
        arm_cleanup()
    # Always record util% + DB load over a watched run and render graphs at the
    # end (auto-named under /tmp; see graph_dir_for). Samplers start now so they
    # capture the farm filling.
    graph_dir = graph_dir_for(args.mode) if watch else None
    samplers = start_samplers(graph_dir) if watch else []
    if args.priority_starve:
        log(f"watching PRIORITY_STARVING (low vs high streams) for {args.priority_starve}s ...")
        subprocess.run([VENV_PY, "priority_starve_watch.py", str(args.priority_starve), "5"],
                       cwd=FARM)
    elif args.priority_spread:
        log(f"watching PRIORITY spread (share-vs-priority across classes) for "
            f"{args.priority_spread}s ...")
        csv = f"{graph_dir}/run_priority_spread.csv" if graph_dir else ""
        subprocess.run([VENV_PY, "priority_spread_watch.py", str(args.priority_spread), "5"],
                       cwd=FARM, env=dict(os.environ, SIM_SPREAD_CSV=csv))
    elif args.limit_test:
        log(f"watching LIMIT (concurrent running vs cap) for {args.limit_test}s ...")
        csv = f"{graph_dir}/run_limit.csv" if graph_dir else ""
        subprocess.run([VENV_PY, "limit_watch.py", str(args.limit_test), "3"],
                       cwd=FARM, env=dict(os.environ, SIM_LIMIT_CSV=csv))
    elif args.folder_test:
        log(f"watching FOLDER (folder running cores vs cap) for {args.folder_test}s ...")
        csv = f"{graph_dir}/run_folder.csv" if graph_dir else ""
        subprocess.run([VENV_PY, "folder_watch.py", str(args.folder_test), "3"],
                       cwd=FARM, env=dict(os.environ, SIM_FOLDER_CSV=csv))
    elif args.strand and args.strand_duration_mix:
        log(f"watching wide-job DURATION fairness (short vs long frames) for "
            f"{args.strand}s ...")
        subprocess.run([VENV_PY, "strand_dur_watch.py", str(args.strand), "5"], cwd=FARM)
    elif args.strand:
        log(f"watching BIG-job stranding + live stats for {args.strand}s "
            f"(small feeder runs alongside) ...")
        subprocess.run([VENV_PY, "live_stats.py", str(args.strand), "5"], cwd=FARM)
    elif watch:
        secs = args.stats or args.metrics or args.feed
        log(f"streaming live stats for {secs}s ...")
        subprocess.run([VENV_PY, "live_stats.py", str(secs), "5"], cwd=FARM)
    else:
        log(f"run live stats any time:  {VENV_PY} {os.path.join(FARM, 'live_stats.py')} 120")

    if watch:
        generate_graphs(graph_dir, samplers)

    # DB load summary by default, after whatever phase ran above.
    db_stats()


if __name__ == "__main__":
    main()
