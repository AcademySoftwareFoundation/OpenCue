"""Shared metrics so any watcher reports what a by-hand psql/grep would.

The point of the simulator is to run it and SEE everything -- utilization,
throughput, and whether reservations are actually being granted -- without
poking the DB or tailing the cuebot log yourself. These helpers centralize the
two signals that used to need manual digging, so every watcher surfaces them:

  - farm_state(): farm utilization% and the largest idle-core block on any one
    host. That second number is the saturation signal: while it is below a wide
    job's width, no host can fit a wide frame, so one can only run via a
    reservation -- exactly the condition the reservation test needs.
  - resv_grants(): reservations parsed from the cuebot log's
    'Scheduler resv-grant' lines -- how many grant events fired, the total
    reservations newly granted, and the latest count held. (0,0,0) means none
    were granted, which is itself the answer: reservations are off, or the farm
    never saturated enough to need one.

Both live_stats.py and strand_dur_watch.py call these, so a by-hand run prints
util / frames-s / reservations on its own with nothing to grep afterward.
"""
import os
import re
import sys
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_model

# cuebot logs "Scheduler resv-grant: newGrantees=N totalHeld=M" once per tick
# that grants at least one reservation (Scheduler.java logs only on an actual
# grant, to stay off the hot path). Parse those two counters.
_RESV_RE = re.compile(r"resv-grant: newGrantees=(\d+) totalHeld=(\d+)")

# cuebot's periodic "Scheduler stat:" summary line carries "backfilled=N": frames
# placed onto reserved, draining hosts via EASY backfill during that window (it
# resets per window, so we sum across windows for the cumulative total). The
# summary fires every scheduler.stat_interval_seconds; simulate.py lowers that
# for sim runs (SIM_STAT_INTERVAL_SECONDS) so backfill updates the live tail.
_BF_RE = re.compile(r"backfilled=(\d+)")

# One row: total cores, busy cores, largest single-host idle block -- all in
# core-points -- straight from the host table's own busy/idle accounting.
_FARM_SQL = ("SELECT coalesce(sum(int_cores),0), "
             "coalesce(sum(int_cores - int_cores_idle),0), "
             "coalesce(max(int_cores_idle),0) FROM host;")


def farm_state():
    """(util_pct, max_idle_cores) from the host table. util is busy/total cores
    (the DB's own accounting -- each booking decrements int_cores_idle), and
    max_idle_cores is the largest idle block on any one host in whole cores:
    while it is below a wide job's width the farm is saturated, so a wide frame
    can only ever run via a reservation. Returns (0.0, -1) on a query error."""
    try:
        out = subprocess.run(spec.psql_cmd() + ["-c", _FARM_SQL],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        total, busy, max_idle = [int(x) for x in out.split("|")]
    except (ValueError, IndexError, OSError, subprocess.SubprocessError):
        return (0.0, -1)
    util = 100.0 * busy / total if total else 0.0
    return (util, max_idle // sim_model.CORE_POINTS)


# Per-log incremental scan state. The cuebot log grows to 100s of MB on a
# full-farm run, so a watcher that re-read it whole every heartbeat would burn
# gigabytes of I/O; instead each scan reads only the bytes appended since the
# last call and accumulates the counters here, keyed by log path.
_scan_state = {}


def _scan(cuebot_log):
    """Read newly-appended cuebot-log bytes once and fold in reservation grants
    and backfill counts. Advances only past the last COMPLETE line, so a line
    still being written is re-read whole next time. Returns the running state
    dict for this log path. First call on a fresh path reads the whole file
    (correct cumulative); later calls are cheap."""
    st = _scan_state.setdefault(cuebot_log, {"offset": 0, "ev": 0, "gr": 0,
                                             "held": 0, "bf_tot": 0, "bf_last": 0})
    try:
        with open(cuebot_log, "rb") as fh:
            fh.seek(st["offset"])
            chunk = fh.read()
    except OSError:
        return st
    nl = chunk.rfind(b"\n")
    if nl < 0:
        return st                       # no complete new line yet; don't advance
    st["offset"] += nl + 1              # consume up to the last complete line
    text = chunk[:nl + 1].decode("utf-8", "replace")
    for m in _RESV_RE.finditer(text):
        st["ev"] += 1
        st["gr"] += int(m.group(1))
        st["held"] = int(m.group(2))
    for m in _BF_RE.finditer(text):
        st["bf_tot"] += int(m.group(1))
        st["bf_last"] = int(m.group(1))
    return st


def resv_grants(cuebot_log=None):
    """(events, granted, held) from the cuebot log's 'Scheduler resv-grant'
    lines: number of grant events, total reservations newly granted across them,
    and the latest held count. Reads SIM_CUEBOT_LOG when no path is given
    (simulate.py exports the resolved per-run path there). Returns (0,0,0) if the
    log is missing or has no grants -- which is itself the answer when
    reservations are disabled or the farm never needed one."""
    st = _scan(cuebot_log or os.environ.get("SIM_CUEBOT_LOG", "/tmp/cuebot.log"))
    return (st["ev"], st["gr"], st["held"])


def backfill(cuebot_log=None):
    """(total, last) EASY-backfill placements from the scheduler's 'Scheduler
    stat:' summary lines: total frames backfilled onto reserved/draining hosts
    summed across all summary windows, and the most recent window's count.
    Returns (0,0) before the first summary fires (or if the log is missing) --
    which is the answer when backfill is off or no reservation has drained yet."""
    st = _scan(cuebot_log or os.environ.get("SIM_CUEBOT_LOG", "/tmp/cuebot.log"))
    return (st["bf_tot"], st["bf_last"])
