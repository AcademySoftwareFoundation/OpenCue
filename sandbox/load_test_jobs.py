#!/usr/bin/env python3

#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
Load-test runner that submits OpenCue jobs in a variety of shapes so you can
stress Monitor Jobs, Monitor Job Details, dependency views and the REST
gateway with realistic patterns. Replaces the simple "N basic jobs" loader
with a subcommand-driven CLI.

Subcommands
-----------
  simple    N independent jobs, one layer each. Default scenario.
  wide      Job(s) with many layers (default 10) and a small frame range.
  deep      Job(s) with one layer but a large frame range (default 200).
  chain     Linear dependency chain: job_0 <- job_1 <- ... <- job_N-1.
            Each job depends on the previous one, so frames flow through
            DEPEND -> WAITING -> RUNNING in order.
  fan-out   One blocker; N dependents all wait on it.
  fan-in    N blockers; one dependent waits on every blocker.
  diamond   Diamond DAG: A blocks B and C; B and C both block D.
  mixed     A realistic mixed load: simple + wide + deep + a chain.

Shared options (applies to every subcommand unless overridden):
  --show, --shot, --prefix     Job-name segments.
  --command                    Override the default `/bin/sleep <N>`. The
                               string is split with shlex; use --command
                               "/bin/echo hello world" for a custom layer.
  --sleep-seconds              Range for the default sleep command.
                               Pass a single int (constant) or "MIN-MAX"
                               (each frame picks a value cyclically).
  --frame-range                Frame range expression, e.g. "1-10" or
                               "1-100x5" (every-5th). Defaults vary by
                               subcommand.
  --paused                     Submit jobs paused (CueGUI parity for
                               dependency testing - frames stay put until
                               you unpause).
  --batch-size, --batch-pause  Throttle submission so you don't overwhelm
                               Cuebot. Default 10 jobs per batch, 1.0s pause.
  --dry-run                    Print what would be submitted without actually
                               talking to Cuebot. Useful for sanity-checking
                               long invocations.
  --print-names                Echo each submitted short job name (one per
                               line, prefixed with '+ ') and a final clean
                               list of names. Useful for piping into
                               `xargs cueadmin -kill` or saving for later.
  --unique                     Append a unix-timestamp suffix to every
                               generated short name. Re-runs never collide
                               with still-pending jobs from a previous run
                               (most useful for the dependency subcommands
                               which submit paused).

Examples
--------
  # Backward-compatible default: 100 basic jobs in batches of 10.
  python load_test_jobs.py simple

  # 200 simple jobs, all paused, sleeping 1-10s per frame.
  python load_test_jobs.py simple -n 200 --paused --sleep-seconds 1-10

  # One job with 25 layers, each running 5 frames.
  python load_test_jobs.py wide --layers-per-job 25 --frame-range 1-5

  # 10 jobs with 500 frames each.
  python load_test_jobs.py deep -n 10 --frames-per-layer 500

  # A 12-deep dependency chain. --unique avoids name collisions on re-run.
  python load_test_jobs.py chain --chain-length 12 --unique

  # One blocker and 20 dependents (fan-out).
  python load_test_jobs.py fan-out --dependents 20 --unique

  # 9 blockers and 1 dependent (drop-in replacement for
  # dep_test_eligible_time.py with NUM_BLOCKERS=9).
  python load_test_jobs.py fan-in --blockers 9 --unique

  # Diamond DAG (A -> B, A -> C, B+C -> D). --unique stamps a timestamp
  # suffix onto every name so back-to-back runs never collide with the
  # previous (still-paused) diamond.
  python load_test_jobs.py diamond --unique

  # Realistic mixed load.
  python load_test_jobs.py mixed --total 50 --unique
"""

import argparse
import glob
import os
import platform
import random
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import outline
import outline.cuerun
from outline.modules.shell import Shell

try:
    import opencue
except ImportError:  # opencue may not be importable in --dry-run-only setups
    opencue = None  # type: ignore[assignment]


# --------------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------------

DEFAULT_SHOW = "testing"
DEFAULT_SHOT = "testshot"
DEFAULT_PREFIX = "load_test"

# Blender preview-render defaults (see the `blender` subcommand). The render
# output is written into the shared RQD logs dir so the CueWeb container (which
# mounts it read-only) can serve the images to the frame preview panel.
DEFAULT_OUTPUT_ROOT = "/tmp/rqd/logs"
DEFAULT_BLENDER_FRAMES = 4


def discover_blender() -> Optional[str]:
    """Locate the Blender executable across macOS, Windows and Linux.

    Order: $BLENDER env var, then PATH (`blender` / `blender.exe`), then the
    usual per-platform install locations (newest version first). Returns None
    when nothing is found, so callers can print a clear hint.
    """
    env = os.environ.get("BLENDER")
    if env and os.path.exists(env):
        return env

    on_path = shutil.which("blender") or shutil.which("blender.exe")
    if on_path:
        return on_path

    system = platform.system()
    candidates: List[str] = []
    if system == "Darwin":
        for root in ("/Applications", os.path.expanduser("~/Applications")):
            candidates += sorted(
                glob.glob(os.path.join(root, "Blender*.app/Contents/MacOS/Blender")),
                reverse=True)
    elif system == "Windows":
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     os.environ.get("LOCALAPPDATA", "")):
            if base:
                candidates += sorted(
                    glob.glob(os.path.join(base, "Blender Foundation", "Blender*", "blender.exe")),
                    reverse=True)
        candidates += sorted(
            glob.glob(r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"),
            reverse=True)
    else:  # Linux (CentOS, Rocky, Ubuntu, etc.) and other Unix
        candidates += [
            "/usr/bin/blender", "/usr/local/bin/blender", "/bin/blender",
            "/snap/bin/blender",  # snap
            "/var/lib/flatpak/exports/bin/org.blender.Blender",  # flatpak (system)
            os.path.expanduser("~/.local/share/flatpak/exports/bin/org.blender.Blender"),
        ]
        for root in ("/opt", os.path.expanduser("~")):
            candidates += sorted(glob.glob(os.path.join(root, "blender*", "blender")), reverse=True)

    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None
DEFAULT_BATCH_SIZE = 10
DEFAULT_BATCH_PAUSE_SEC = 1.0
DEFAULT_NUM_JOBS = 100


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

@dataclass
class CommonOpts:
    """Subset of CLI options that apply to every subcommand."""
    show: str
    shot: str
    prefix: str
    command: Optional[List[str]]   # None -> default to sleep
    sleep_range: Tuple[int, int]   # (min, max) inclusive
    paused: bool
    batch_size: int
    batch_pause: float
    dry_run: bool
    print_names: bool = False
    unique_suffix: str = ""        # appended to every generated short name
    submitted_names: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.submitted_names is None:
            self.submitted_names = []

    def short(self, base: str) -> str:
        """Apply --unique suffix to a generated short name. The suffix lets
        you re-run a subcommand back-to-back without colliding with the
        previous run's still-pending jobs.
        """
        return base + self.unique_suffix


def _parse_sleep_spec(spec: str) -> Tuple[int, int]:
    """`5` -> (5, 5);  `1-10` -> (1, 10)."""
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        lo_i, hi_i = int(lo), int(hi)
        if hi_i < lo_i:
            raise argparse.ArgumentTypeError(
                "--sleep-seconds: max (%d) must be >= min (%d)" % (hi_i, lo_i))
        return lo_i, hi_i
    n = int(spec)
    return n, n


def _layer_command(common: CommonOpts, layer_index: int) -> List[str]:
    """
    Build the argv for a single layer. When --command is set, use it verbatim
    (split with shlex). Otherwise default to `/bin/sleep <N>` where N rotates
    deterministically across the sleep range so the test pattern is
    reproducible but varied.
    """
    if common.command is not None:
        return list(common.command)
    lo, hi = common.sleep_range
    if lo == hi:
        sleep_for = lo
    else:
        span = hi - lo + 1
        sleep_for = lo + (layer_index % span)
    return ["/bin/sleep", str(sleep_for)]


def _print(msg: str) -> None:
    """Single-line stdout flush so progress reads cleanly when piped."""
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def _throttle(submitted_count: int, common: CommonOpts) -> None:
    """Sleep between batches so we don't overwhelm Cuebot."""
    if common.batch_size <= 0 or common.batch_pause <= 0:
        return
    if submitted_count > 0 and submitted_count % common.batch_size == 0:
        _print("  ... batch of %d submitted, pausing %.1fs"
               % (common.batch_size, common.batch_pause))
        time.sleep(common.batch_pause)


def _submit_outline(
    short_name: str,
    common: CommonOpts,
    layer_builders: List[Callable[[int], Shell]],
) -> bool:
    """
    Build + submit a single outline with the provided layer builders. Returns
    True on success. Respects --dry-run and --paused.
    """
    if common.dry_run:
        layer_summary = ", ".join(
            "%s(range=%r, cmd=%s)" % (
                builder(idx).get_name(),
                builder(idx).get_frame_range(),
                builder(idx).get_arg("command"),
            )
            for idx, builder in enumerate(layer_builders)
        )
        _print("  [DRY] %s | %s%s" % (
            short_name, layer_summary, " | paused" if common.paused else ""))
        common.submitted_names.append(short_name)
        if common.print_names:
            _print("  + %s" % short_name)
        return True

    try:
        ol = outline.Outline(short_name, shot=common.shot, show=common.show)
        for idx, builder in enumerate(layer_builders):
            ol.add_layer(builder(idx))
        outline.cuerun.launch(ol, pause=common.paused, use_pycuerun=False)
        common.submitted_names.append(short_name)
        if common.print_names:
            _print("  + %s" % short_name)
        return True
    except Exception as e:
        msg = str(e)
        _print("  ! failed to submit %s: %s" % (short_name, msg))
        # Surface a one-time hint when names collide with a previous run's
        # still-pending jobs (most common after a partial dependency run).
        if "already pending" in msg.lower() and not common.unique_suffix:
            _print("    hint: pass --unique to append a timestamp suffix, "
                   "or kill the existing jobs first (cueadmin -kill ...).")
        return False


def _find_job(short_name: str):
    """Look up the full opencue.Job by trailing short name (`<show>-<shot>-<user>_<short>`).

    Cuebot normalizes job names to lowercase on insert (see JobSpec.java), so
    we search and compare in lowercase. Otherwise a short name like
    'diamond_A' would never match the persisted 'diamond_a'.
    """
    if opencue is None:
        raise RuntimeError("opencue.api not available; cannot wire dependencies")
    needle = short_name.lower()
    for job in opencue.api.getJobs(substr=[needle]):
        if job.name().lower().endswith("_%s" % needle):
            return job
    raise RuntimeError("could not find submitted job: %s" % short_name)


def _wait_for_jobs(short_names: List[str], timeout_sec: float = 30.0) -> List:
    """
    Poll Cuebot until every short_name is resolvable, or `timeout_sec` elapses.
    Returns the resolved Job list in the same order.
    """
    deadline = time.time() + timeout_sec
    resolved = [None] * len(short_names)
    pending = set(range(len(short_names)))
    while pending and time.time() < deadline:
        for idx in list(pending):
            try:
                resolved[idx] = _find_job(short_names[idx])
                pending.discard(idx)
            except RuntimeError:
                continue
        if pending:
            time.sleep(0.5)
    if pending:
        missing = [short_names[i] for i in pending]
        raise RuntimeError("timed out resolving submitted jobs: %s" % missing)
    return resolved


def _summary(label: str, submitted: int, failed: int,
             common: Optional[CommonOpts] = None) -> None:
    _print("-" * 60)
    _print("%s complete" % label)
    _print("  submitted: %d" % submitted)
    _print("  failed   : %d" % failed)
    if common and common.print_names and common.submitted_names:
        _print("submitted job names:")
        for name in common.submitted_names:
            _print(name)


# --------------------------------------------------------------------------
# Subcommand: simple (N independent jobs, one layer each)
# --------------------------------------------------------------------------

def cmd_simple(args, common: CommonOpts) -> int:
    num_jobs = args.num_jobs
    frame_range = args.frame_range
    _print("Submitting %d simple jobs (one layer, frame range %s)%s"
           % (num_jobs, frame_range, " [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    submitted = 0
    failed = 0
    for i in range(num_jobs):
        short_name = common.short("%s_job_%04d" % (common.prefix, i))
        builder = lambda idx, i=i: Shell(
            "test_layer",
            command=_layer_command(common, i),
            range=frame_range,
        )
        if _submit_outline(short_name, common, [builder]):
            submitted += 1
        else:
            failed += 1
        if submitted and submitted % 10 == 0:
            _print("  progress: %d/%d (failed=%d)" % (submitted, num_jobs, failed))
        _throttle(i + 1, common)

    _summary("simple", submitted, failed, common)
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------
# Subcommand: wide (job with many layers)
# --------------------------------------------------------------------------

def cmd_wide(args, common: CommonOpts) -> int:
    num_jobs = args.num_jobs
    layers_per_job = args.layers_per_job
    frame_range = args.frame_range
    _print("Submitting %d wide job(s) (%d layers each, frame range %s)%s"
           % (num_jobs, layers_per_job, frame_range, " [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    submitted = 0
    failed = 0
    for i in range(num_jobs):
        short_name = common.short("%s_wide_%04d" % (common.prefix, i))

        def make_builder(layer_idx: int) -> Callable[[int], Shell]:
            def build(_idx: int) -> Shell:
                return Shell(
                    "wide_layer_%03d" % layer_idx,
                    command=_layer_command(common, layer_idx),
                    range=frame_range,
                )
            return build

        layer_builders = [make_builder(li) for li in range(layers_per_job)]
        if _submit_outline(short_name, common, layer_builders):
            submitted += 1
        else:
            failed += 1
        _throttle(i + 1, common)

    _summary("wide", submitted, failed, common)
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------
# Subcommand: deep (job(s) with many frames)
# --------------------------------------------------------------------------

def cmd_deep(args, common: CommonOpts) -> int:
    num_jobs = args.num_jobs
    frames = args.frames_per_layer
    frame_range = "1-%d" % frames
    _print("Submitting %d deep job(s) (one layer, %d frames each)%s"
           % (num_jobs, frames, " [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    submitted = 0
    failed = 0
    for i in range(num_jobs):
        short_name = common.short("%s_deep_%04d" % (common.prefix, i))
        builder = lambda idx, i=i: Shell(
            "deep_layer",
            command=_layer_command(common, i),
            range=frame_range,
        )
        if _submit_outline(short_name, common, [builder]):
            submitted += 1
        else:
            failed += 1
        _throttle(i + 1, common)

    _summary("deep", submitted, failed, common)
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------
# Dependency-aware subcommands
# --------------------------------------------------------------------------

def _require_opencue_or_dry_run(common: CommonOpts) -> None:
    """Dependency subcommands need opencue.api unless we're only printing."""
    if common.dry_run:
        return
    if opencue is None:
        raise SystemExit(
            "opencue.api is not importable. Install it or pass --dry-run "
            "to validate the submission plan without contacting Cuebot.")


def _submit_dep_jobs(
    common: CommonOpts,
    short_names: List[str],
    frame_range: str,
) -> Tuple[List[str], int]:
    """
    Submit every short_name as a paused single-layer job and return the names
    that were submitted plus the failure count. Dependency wiring is done by
    callers after this returns.
    """
    submitted_names: List[str] = []
    failed = 0
    # Dependency scenarios are paused by default so blockers don't race
    # ahead of the wiring. Override with --no-paused (not yet exposed) if
    # you specifically want a live race.
    paused_common = CommonOpts(**{**common.__dict__, "paused": True})
    for short_name in short_names:
        builder = lambda idx, name=short_name: Shell(
            "test_layer",
            command=_layer_command(common, 0),
            range=frame_range,
        )
        if _submit_outline(short_name, paused_common, [builder]):
            submitted_names.append(short_name)
        else:
            failed += 1
    return submitted_names, failed


def _abort_if_submit_incomplete(label: str, required: List[str],
                                submitted: List[str], failed: int,
                                common: CommonOpts) -> Optional[int]:
    """Return a non-zero exit code (and print a summary) when the submit phase
    didn't land every job the dependency wiring needs. Returns None when it
    is safe to proceed.
    """
    if len(submitted) == len(required):
        return None
    missing = [s for s in required if s not in submitted]
    _print("  ! aborting %s: only %d of %d jobs submitted (missing: %s)"
           % (label, len(submitted), len(required), ", ".join(missing)))
    if not common.unique_suffix:
        _print("    re-run with --unique (or kill the colliding jobs) to "
               "submit a fresh set of names.")
    _summary(label, len(submitted), failed, common)
    return 1


def cmd_chain(args, common: CommonOpts) -> int:
    """Linear chain: each job depends on the previous one (job_0 runs first)."""
    _require_opencue_or_dry_run(common)
    chain_len = args.chain_length
    frame_range = args.frame_range
    _print("Submitting chain of %d jobs (each depends on previous)%s"
           % (chain_len, " [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    short_names = [common.short("%s_chain_%02d" % (common.prefix, i)) for i in range(chain_len)]
    submitted, failed = _submit_dep_jobs(common, short_names, frame_range)
    _print("Submitted %d jobs; resolving handles for dependency wiring..."
           % len(submitted))

    if common.dry_run:
        for i in range(1, chain_len):
            _print("  [DRY] %s depends on %s" % (short_names[i], short_names[i - 1]))
        _summary("chain (dry-run)", len(submitted), failed, common)
        return 0

    rc = _abort_if_submit_incomplete("chain", short_names, submitted, failed, common)
    if rc is not None:
        return rc

    jobs = _wait_for_jobs(submitted)
    for i in range(1, len(jobs)):
        jobs[i].createDependencyOnJob(jobs[i - 1])
        _print("  %s depends on %s" % (jobs[i].name(), jobs[i - 1].name()))

    _summary("chain", len(submitted), failed, common)
    return 0 if failed == 0 else 1


def cmd_fan_out(args, common: CommonOpts) -> int:
    """One blocker, N dependents (all dependents wait on the same blocker)."""
    _require_opencue_or_dry_run(common)
    deps = args.dependents
    frame_range = args.frame_range
    _print("Submitting fan-out: 1 blocker, %d dependents%s"
           % (deps, " [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    blocker_short = common.short("%s_fanout_blocker" % common.prefix)
    dep_shorts = [common.short("%s_fanout_dep_%03d" % (common.prefix, i)) for i in range(deps)]
    submitted, failed = _submit_dep_jobs(
        common, [blocker_short] + dep_shorts, frame_range)

    if common.dry_run:
        for s in dep_shorts:
            _print("  [DRY] %s depends on %s" % (s, blocker_short))
        _summary("fan-out (dry-run)", len(submitted), failed, common)
        return 0

    rc = _abort_if_submit_incomplete(
        "fan-out", [blocker_short] + dep_shorts, submitted, failed, common)
    if rc is not None:
        return rc

    blocker_and_deps = _wait_for_jobs(submitted)
    blocker, dep_jobs = blocker_and_deps[0], blocker_and_deps[1:]
    for d in dep_jobs:
        d.createDependencyOnJob(blocker)
        _print("  %s depends on %s" % (d.name(), blocker.name()))

    _summary("fan-out", len(submitted), failed, common)
    return 0 if failed == 0 else 1


def cmd_fan_in(args, common: CommonOpts) -> int:
    """N blockers, one dependent (the dependent waits on every blocker)."""
    _require_opencue_or_dry_run(common)
    blockers = args.blockers
    frame_range = args.frame_range
    _print("Submitting fan-in: %d blockers, 1 dependent%s"
           % (blockers, " [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    blocker_shorts = [common.short("%s_fanin_blocker_%02d" % (common.prefix, i))
                      for i in range(blockers)]
    dep_short = common.short("%s_fanin_dependent" % common.prefix)
    submitted, failed = _submit_dep_jobs(
        common, blocker_shorts + [dep_short], frame_range)

    if common.dry_run:
        for s in blocker_shorts:
            _print("  [DRY] %s depends on %s" % (dep_short, s))
        _summary("fan-in (dry-run)", len(submitted), failed, common)
        return 0

    rc = _abort_if_submit_incomplete(
        "fan-in", blocker_shorts + [dep_short], submitted, failed, common)
    if rc is not None:
        return rc

    resolved = _wait_for_jobs(submitted)
    blocker_jobs, dependent = resolved[:-1], resolved[-1]
    for b in blocker_jobs:
        dependent.createDependencyOnJob(b)
        _print("  %s depends on %s" % (dependent.name(), b.name()))

    _summary("fan-in", len(submitted), failed, common)
    return 0 if failed == 0 else 1


def cmd_diamond(args, common: CommonOpts) -> int:
    """Diamond DAG: A -> B, A -> C, B+C -> D."""
    _require_opencue_or_dry_run(common)
    frame_range = args.frame_range
    _print("Submitting diamond DAG (A -> B, A -> C, B+C -> D)%s"
           % (" [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    # Use lowercase node ids: Cuebot lowercases job names on insert, so
    # uppercase letters would only make the lookup harder to read.
    shorts = [
        common.short("%s_diamond_a" % common.prefix),
        common.short("%s_diamond_b" % common.prefix),
        common.short("%s_diamond_c" % common.prefix),
        common.short("%s_diamond_d" % common.prefix),
    ]
    submitted, failed = _submit_dep_jobs(common, shorts, frame_range)

    if common.dry_run:
        _print("  [DRY] %s depends on %s" % (shorts[1], shorts[0]))
        _print("  [DRY] %s depends on %s" % (shorts[2], shorts[0]))
        _print("  [DRY] %s depends on %s" % (shorts[3], shorts[1]))
        _print("  [DRY] %s depends on %s" % (shorts[3], shorts[2]))
        _summary("diamond (dry-run)", len(submitted), failed, common)
        return 0

    rc = _abort_if_submit_incomplete("diamond", shorts, submitted, failed, common)
    if rc is not None:
        return rc

    a, b, c, d = _wait_for_jobs(submitted)
    for parent, child in [(a, b), (a, c), (b, d), (c, d)]:
        child.createDependencyOnJob(parent)
        _print("  %s depends on %s" % (child.name(), parent.name()))

    _summary("diamond", len(submitted), failed, common)
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------
# Subcommand: mixed (a realistic blend)
# --------------------------------------------------------------------------

def cmd_mixed(args, common: CommonOpts) -> int:
    """
    Submit a realistic mix. Allocation (default total=50):
       60% simple   (one layer, small range)
       15% wide     (5 layers each)
       15% deep     (50 frames each)
       10% chained  (a short dependency chain)
    """
    total = args.total
    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    counts = {
        "simple": max(1, int(total * 0.60)),
        "wide": max(1, int(total * 0.15)),
        "deep": max(1, int(total * 0.15)),
        "chain": max(2, total - int(total * 0.60) - int(total * 0.15) - int(total * 0.15)),
    }
    _print("Submitting mixed load (total=%d): %s%s"
           % (total, counts, " [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    submitted = 0
    failed = 0

    # Simple
    for i in range(counts["simple"]):
        short_name = common.short("%s_mix_simple_%04d" % (common.prefix, i))
        frame_count = rng.randint(1, 5)
        builder = lambda idx, fc=frame_count, i=i: Shell(
            "test_layer",
            command=_layer_command(common, i),
            range="1-%d" % fc,
        )
        if _submit_outline(short_name, common, [builder]):
            submitted += 1
        else:
            failed += 1
        _throttle(submitted, common)

    # Wide
    for i in range(counts["wide"]):
        short_name = common.short("%s_mix_wide_%03d" % (common.prefix, i))
        layer_count = rng.randint(3, 7)

        def make_builder(li: int) -> Callable[[int], Shell]:
            def build(_idx: int) -> Shell:
                return Shell(
                    "wide_layer_%03d" % li,
                    command=_layer_command(common, li),
                    range="1-%d" % rng.randint(1, 4),
                )
            return build

        builders = [make_builder(li) for li in range(layer_count)]
        if _submit_outline(short_name, common, builders):
            submitted += 1
        else:
            failed += 1
        _throttle(submitted, common)

    # Deep
    for i in range(counts["deep"]):
        short_name = common.short("%s_mix_deep_%03d" % (common.prefix, i))
        frames = rng.randint(20, 80)
        builder = lambda idx, frames=frames, i=i: Shell(
            "deep_layer",
            command=_layer_command(common, i),
            range="1-%d" % frames,
        )
        if _submit_outline(short_name, common, [builder]):
            submitted += 1
        else:
            failed += 1
        _throttle(submitted, common)

    # Short chain (paused, with dependency wiring)
    chain_shorts = [common.short("%s_mix_chain_%02d" % (common.prefix, i))
                    for i in range(counts["chain"])]
    chain_submitted, chain_failed = _submit_dep_jobs(common, chain_shorts, "1-2")
    submitted += len(chain_submitted)
    failed += chain_failed

    if not common.dry_run and chain_submitted:
        chain_jobs = _wait_for_jobs(chain_submitted)
        for i in range(1, len(chain_jobs)):
            chain_jobs[i].createDependencyOnJob(chain_jobs[i - 1])
            _print("  %s depends on %s"
                   % (chain_jobs[i].name(), chain_jobs[i - 1].name()))

    _summary("mixed", submitted, failed, common)
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------
# Subcommand: blender (render a real image sequence for the CueWeb preview)
# --------------------------------------------------------------------------

# Blender scene script: rotate the factory-startup cube over the frame range
# and render each frame with the fast, headless-safe Workbench engine.
_BLENDER_SCRIPT = r"""
import bpy, math, sys
argv = sys.argv[sys.argv.index("--") + 1:]
outbase, nframes = argv[0], int(argv[1])
sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_WORKBENCH'
except Exception:
    pass
sc.render.image_settings.file_format = 'PNG'
sc.render.resolution_x = 320
sc.render.resolution_y = 240
sc.render.resolution_percentage = 100
sc.frame_start = 1
sc.frame_end = nframes
cube = bpy.data.objects.get('Cube')
if cube:
    for f in range(1, nframes + 1):
        cube.rotation_euler = (math.radians(15 * (f - 1)), 0, math.radians(30 * (f - 1)))
        cube.keyframe_insert(data_path='rotation_euler', frame=f)
sc.render.filepath = outbase   # Blender appends <####>.png
bpy.ops.render.render(animation=True)
"""


def _blender_render(blender_bin: str, render_dir: str, nframes: int) -> str:
    """Render `nframes` PNGs (beauty.0001.png ...) into render_dir using the
    host Blender. Returns the OpenCue/CueWeb output spec (with a #### token)."""
    script_path = os.path.join(render_dir, "render_cube.py")
    with open(script_path, "w", encoding="utf-8") as fp:
        fp.write(_BLENDER_SCRIPT)
    out_base = os.path.join(render_dir, "beauty.")
    _print("  rendering %d frame(s) with Blender -> %sXXXX.png" % (nframes, out_base))
    subprocess.run(
        [blender_bin, "-b", "-P", script_path, "--", out_base, str(nframes)],
        check=True,
    )
    return os.path.join(render_dir, "beauty.####.png")


def cmd_blender(args, common: CommonOpts) -> int:
    """Render a short Blender sequence per job and register it as the layer's
    output path so the CueWeb frame preview thumbnail viewer has real images.

    The sandbox RQD runs in a minimal Linux container (no Blender), so the host
    Blender renders the frames straight into the shared RQD logs dir; the
    submitted job's frames are trivial markers. Jobs are launched paused so the
    (instant) marker frames don't finish and drop out of Monitor Jobs before
    you can open them - the rendered images exist regardless of frame state.
    """
    num_jobs = args.num_jobs
    nframes = args.frame_count
    # Fail fast on non-positive values: a frame_count < 1 yields an invalid
    # range (e.g. "1-0") and num_jobs < 1 silently submits nothing.
    if num_jobs < 1:
        _print("  ! --num-jobs must be >= 1")
        return 1
    if nframes < 1:
        _print("  ! --frame-count must be >= 1")
        return 1
    blender_bin = args.blender or discover_blender()
    output_root = args.output_root

    _print("Submitting %d Blender preview job(s), %d frame(s) each%s"
           % (num_jobs, nframes, " [DRY]" if common.dry_run else ""))
    _print("-" * 60)

    if not common.dry_run:
        if opencue is None:
            _print("  ! opencue.api not available; cannot register output paths.")
            return 1
        if not blender_bin or not os.path.exists(blender_bin):
            _print("  ! Blender not found. Install it, add it to PATH, set the "
                   "BLENDER env var, or pass --blender PATH.")
            _print("    macOS:   /Applications/Blender.app/Contents/MacOS/Blender")
            _print("    Windows: C:\\Program Files\\Blender Foundation\\Blender X.Y\\blender.exe")
            _print("    Linux:   /usr/bin/blender (or snap/flatpak)")
            return 1
        _print("  using Blender: %s" % blender_bin)
        os.makedirs(output_root, exist_ok=True)

    submitted = 0
    failed = 0
    for i in range(num_jobs):
        short_name = common.short("%s_blender_%04d" % (common.prefix, i))
        stamp = "%d_%04d" % (time.time_ns(), i)
        render_dir = os.path.join(output_root, "blender_%s" % stamp)
        output_spec = os.path.join(render_dir, "beauty.####.png")

        if common.dry_run:
            _print("  [DRY] %s | beauty(range=1-%d) | render -> %s | paused"
                   % (short_name, nframes, output_spec))
            common.submitted_names.append(short_name)
            if common.print_names:
                _print("  + %s" % short_name)
            submitted += 1
            continue

        try:
            os.makedirs(render_dir, exist_ok=True)
            _blender_render(blender_bin, render_dir, nframes)

            ol = outline.Outline(short_name, shot=common.shot, show=common.show)
            ol.add_layer(Shell(
                "beauty",
                command=["/bin/echo", "rendered", "frame", "#IFRAME#"],
                range="1-%d" % nframes,
            ))
            # Always paused: the marker frames would otherwise finish instantly
            # and the job would leave the active list before you can open it.
            outline.cuerun.launch(ol, pause=True, use_pycuerun=False)

            # Poll for visibility rather than a one-shot lookup: _find_job can
            # race Cuebot right after launch and would skip registerOutputPath.
            job = _wait_for_jobs([short_name])[0]
            layer = next(layer_obj for layer_obj in job.getLayers() if layer_obj.name() == "beauty")
            layer.registerOutputPath(output_spec)

            _print("  + %s  (output: %s)" % (job.name(), output_spec))
            common.submitted_names.append(short_name)
            submitted += 1
        except Exception as e:  # pylint: disable=broad-except
            _print("  ! failed to submit %s: %s" % (short_name, e))
            failed += 1
        _throttle(i + 1, common)

    _summary("blender", submitted, failed, common)
    if submitted and not common.dry_run:
        _print("Open a job in CueWeb -> Frames -> click the Preview (image) "
               "icon on a frame to see the Blender render.")
    return 0 if failed == 0 else 1


# --------------------------------------------------------------------------
# CLI plumbing
# --------------------------------------------------------------------------

def _build_shared_parser() -> argparse.ArgumentParser:
    """Flags shared by every subcommand. Attached via `parents=[...]` to both
    the top-level parser and each subparser, so the user can pass them on
    either side of the subcommand name (e.g. `--paused simple` or
    `simple --paused`).
    """
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--show", default=DEFAULT_SHOW,
                        help="show name (default: %(default)s)")
    shared.add_argument("--shot", default=DEFAULT_SHOT,
                        help="shot name (default: %(default)s)")
    shared.add_argument("--prefix", default=DEFAULT_PREFIX,
                        help="job-name prefix (default: %(default)s)")
    shared.add_argument("--command", default=None,
                        help="override layer command (string; split with shlex). "
                             "When set, --sleep-seconds is ignored.")
    shared.add_argument("--sleep-seconds", default=(1, 5),
                        type=_parse_sleep_spec,
                        help="default sleep command range as 'N' or 'MIN-MAX' "
                             "(default: 1-5)")
    shared.add_argument("--paused", action="store_true",
                        help="submit jobs paused (default: off, except for "
                             "dependency scenarios which always paused-submit)")
    shared.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help="pause briefly after this many submissions "
                             "(default: %(default)s; 0 to disable)")
    shared.add_argument("--batch-pause", type=float,
                        default=DEFAULT_BATCH_PAUSE_SEC,
                        help="seconds to pause between batches "
                             "(default: %(default)s)")
    shared.add_argument("--dry-run", action="store_true",
                        help="print the submission plan without contacting "
                             "Cuebot. opencue.api is not required.")
    shared.add_argument("--print-names", action="store_true",
                        help="print each submitted short job name (one per "
                             "line, prefixed with '+ ') and a final list. "
                             "Useful for piping to xargs / cueadmin.")
    shared.add_argument("--unique", action="store_true",
                        help="append a unix-timestamp suffix to every "
                             "generated short name so re-runs never collide "
                             "with still-pending jobs from a previous run.")
    return shared


def _build_parser() -> argparse.ArgumentParser:
    shared = _build_shared_parser()

    # Shared flags live on the subparsers (via parents=[shared]) and NOT on
    # the top-level parser. Putting them on both makes argparse silently drop
    # a top-level `--flag` because the subparser re-applies its own default
    # after the fact. Argv is normalized in main() so the bare invocation
    # (no subcommand) still works.
    parent = argparse.ArgumentParser(
        prog="load_test_jobs.py",
        description="OpenCue load-test runner (multiple job-shape patterns).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run with `<subcommand> --help` to see per-pattern options.",
    )

    subs = parent.add_subparsers(dest="cmd", required=False)

    # simple
    p_simple = subs.add_parser(
        "simple",
        parents=[shared],
        help="N independent jobs, one layer each (default scenario).",
        description="Submit N independent single-layer jobs. Matches the "
                    "original load_test_jobs.py behavior.")
    p_simple.add_argument("-n", "--num-jobs", type=int, default=DEFAULT_NUM_JOBS,
                          help="job count (default: %(default)s)")
    p_simple.add_argument("--frame-range", default="1-3",
                          help="frame range expression (default: %(default)s)")
    p_simple.set_defaults(func=cmd_simple)

    # wide
    p_wide = subs.add_parser(
        "wide",
        parents=[shared],
        help="Job(s) with many layers.",
        description="Submit job(s) with many layers each. Useful for "
                    "stress-testing the Layers table and the inline "
                    "JobDetails view.")
    p_wide.add_argument("-n", "--num-jobs", type=int, default=1,
                        help="number of wide jobs (default: %(default)s)")
    p_wide.add_argument("--layers-per-job", type=int, default=10,
                        help="layers per job (default: %(default)s)")
    p_wide.add_argument("--frame-range", default="1-2",
                        help="frame range per layer (default: %(default)s)")
    p_wide.set_defaults(func=cmd_wide)

    # deep
    p_deep = subs.add_parser(
        "deep",
        parents=[shared],
        help="Job(s) with many frames in a single layer.",
        description="Submit job(s) with a single layer that has a large "
                    "frame range. Useful for stress-testing the Frames "
                    "table and pagination.")
    p_deep.add_argument("-n", "--num-jobs", type=int, default=1,
                        help="number of deep jobs (default: %(default)s)")
    p_deep.add_argument("--frames-per-layer", type=int, default=200,
                        help="frames per layer (default: %(default)s)")
    p_deep.set_defaults(func=cmd_deep)

    # chain
    p_chain = subs.add_parser(
        "chain",
        parents=[shared],
        help="Linear dependency chain.",
        description="job_0 <- job_1 <- ... <- job_(N-1). Each job is paused "
                    "and depends on its predecessor. Useful for testing the "
                    "View Dependencies and Drop Dependencies UI flows.")
    p_chain.add_argument("--chain-length", type=int, default=5,
                         help="number of jobs in the chain (default: %(default)s)")
    p_chain.add_argument("--frame-range", default="1-2",
                         help="frame range per job (default: %(default)s)")
    p_chain.set_defaults(func=cmd_chain)

    # fan-out
    p_fan_out = subs.add_parser(
        "fan-out",
        parents=[shared],
        help="One blocker; N dependents.",
        description="One paused blocker job; N paused dependent jobs that "
                    "all wait on the blocker. Frames in the dependents "
                    "should sit in DEPEND until the blocker completes.")
    p_fan_out.add_argument("--dependents", type=int, default=5,
                           help="number of dependents (default: %(default)s)")
    p_fan_out.add_argument("--frame-range", default="1-2",
                           help="frame range per job (default: %(default)s)")
    p_fan_out.set_defaults(func=cmd_fan_out)

    # fan-in
    p_fan_in = subs.add_parser(
        "fan-in",
        parents=[shared],
        help="N blockers; one dependent.",
        description="N paused blocker jobs; one paused dependent job that "
                    "waits on every blocker. Useful for validating "
                    "frame.ts_eligible transitions (DEPEND -> WAITING) and "
                    "the Mark-done flow.")
    p_fan_in.add_argument("--blockers", type=int, default=9,
                          help="number of blockers (default: %(default)s)")
    p_fan_in.add_argument("--frame-range", default="1-2",
                          help="frame range per job (default: %(default)s)")
    p_fan_in.set_defaults(func=cmd_fan_in)

    # diamond
    p_diamond = subs.add_parser(
        "diamond",
        parents=[shared],
        help="Diamond DAG: A -> B, A -> C, B+C -> D.",
        description="Four-node diamond: A is the root; B and C both depend "
                    "on A; D depends on both B and C.")
    p_diamond.add_argument("--frame-range", default="1-2",
                           help="frame range per job (default: %(default)s)")
    p_diamond.set_defaults(func=cmd_diamond)

    # mixed
    p_mixed = subs.add_parser(
        "mixed",
        parents=[shared],
        help="Realistic blend (simple + wide + deep + a short chain).",
        description="Submit a realistic mix: 60%% simple, 15%% wide, 15%% "
                    "deep, plus a short paused chain at the end.")
    p_mixed.add_argument("--total", type=int, default=50,
                         help="approximate total job count (default: %(default)s)")
    p_mixed.add_argument("--seed", type=int, default=None,
                         help="random seed for reproducible mixes (default: random)")
    p_mixed.set_defaults(func=cmd_mixed)

    # blender
    p_blender = subs.add_parser(
        "blender",
        parents=[shared],
        help="Render a real Blender image sequence for the CueWeb frame preview.",
        description="Render a short rotating-cube sequence with the host Blender "
                    "into the shared RQD logs dir and register it as the job "
                    "layer's output path, so the CueWeb frame preview thumbnail "
                    "viewer shows real rendered frames. Jobs are launched "
                    "paused so they stay visible in Monitor Jobs.")
    p_blender.add_argument("-n", "--num-jobs", type=int, default=1,
                           help="number of render jobs to submit (default: %(default)s)")
    p_blender.add_argument("--frame-count", type=int, default=DEFAULT_BLENDER_FRAMES,
                           help="frames to render per job (default: %(default)s)")
    p_blender.add_argument("--blender", default=None,
                           help="path to the Blender executable (default: auto-detect "
                                "via $BLENDER, PATH, then common install locations)")
    p_blender.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT,
                           help="shared dir for rendered frames; must be readable "
                                "by the cueweb container (default: %(default)s)")
    p_blender.set_defaults(func=cmd_blender)

    return parent


KNOWN_SUBCOMMANDS = (
    "simple", "wide", "deep", "chain", "fan-out", "fan-in", "diamond", "mixed",
    "blender",
)

# Flags that consume the following argv token as their value. Listed here so
# _normalize_argv can skip those values when scanning for the subcommand;
# otherwise `--prefix chain` would treat the value `chain` as the subcommand
# and silently run the wrong scenario. Keep this in sync with the flags
# declared in `_build_shared_parser` and the per-subcommand parsers below.
_VALUE_BEARING_FLAGS = frozenset({
    # shared
    "--show", "--shot", "--prefix", "--command", "--sleep-seconds",
    "--batch-size", "--batch-pause",
    # simple / wide / deep
    "-n", "--num-jobs", "--frame-range", "--layers-per-job",
    "--frames-per-layer",
    # chain / fan-out / fan-in / mixed
    "--chain-length", "--dependents", "--blockers", "--total", "--seed",
    # blender
    "--frame-count", "--blender", "--output-root",
})


def _normalize_argv(raw: List[str]) -> List[str]:
    """Pull the subcommand (if any) to the front of argv so shared flags work
    whether the user typed them before or after the subcommand name. If no
    subcommand is present, default to 'simple'. Leaves --help / -h alone so
    top-level help still lists all subcommands.

    Only PROMOTES a token to subcommand position when it's a true positional
    (not a flag, not the value of a value-bearing flag). Without this guard,
    `--prefix chain` would treat the second token as the subcommand and
    silently run the wrong scenario. store_true flags (e.g. `--paused`,
    `--dry-run`) do NOT consume the next token, so `--paused simple` still
    correctly promotes `simple`.
    """
    if "--help" in raw or "-h" in raw:
        return list(raw)
    cmd: Optional[str] = None
    rest: List[str] = []
    expecting_value = False
    for token in raw:
        if expecting_value:
            # Previous token was a value-bearing flag; this token is its
            # value, never a subcommand candidate.
            rest.append(token)
            expecting_value = False
            continue
        if token.startswith("-"):
            rest.append(token)
            # `--flag=value` packs the value in the same token; only
            # bare `--flag` / `-n` forms consume the next argv slot.
            if "=" not in token and token in _VALUE_BEARING_FLAGS:
                expecting_value = True
            continue
        if cmd is None and token in KNOWN_SUBCOMMANDS:
            cmd = token
        else:
            rest.append(token)
    if cmd is None:
        cmd = "simple"
    return [cmd] + rest


def main(argv: Optional[List[str]] = None) -> int:
    raw = sys.argv[1:] if argv is None else list(argv)
    parser = _build_parser()
    args = parser.parse_args(_normalize_argv(raw))

    command_argv: Optional[List[str]] = None
    if args.command:
        command_argv = shlex.split(args.command)
        if not command_argv:
            parser.error("--command resolved to an empty argument list")

    common = CommonOpts(
        show=args.show,
        shot=args.shot,
        prefix=args.prefix,
        command=command_argv,
        sleep_range=args.sleep_seconds,
        paused=args.paused,
        batch_size=args.batch_size,
        batch_pause=args.batch_pause,
        dry_run=args.dry_run,
        print_names=args.print_names,
        # Use nanosecond precision so two invocations launched within the
        # same second still get distinct suffixes (int(time.time()) was
        # second-level and could collide).
        unique_suffix=("_t%d" % time.time_ns()) if args.unique else "",
    )

    return args.func(args, common)


if __name__ == "__main__":
    sys.exit(main())
