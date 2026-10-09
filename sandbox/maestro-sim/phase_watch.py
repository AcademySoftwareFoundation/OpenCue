"""Phase watcher: one tick phase must stay bounded under load.

Companion to the BACKLOG and PLACE scenarios. Once the farm is loaded (waiting
frames at or above MIN_WAITING, or the load timeout), samples the leader's
Prometheus endpoint every INTERVAL seconds and, at the end, derives the tick
duration quantiles from the cue_maestro_tick_duration_seconds histogram over
the measured window (buckets are cumulative, so the window is the delta
between the first and last scrape). The watched phase comes from
cue_maestro_tick_phase_seconds{phase=PHASE} where the build exports it, else
from the "PHASE=NNNms" field of the cuebot log's tick breakdown lines, which
every build logs for any tick over one second.

Verdict, on the watched phase alone (the tick's other phases are reported
beside it):
  - PASS: the phase at or under BOUND_MS: its p95 from the histogram, else
    the max of the logged slow ticks.
  - FAIL: the phase grew with the load.
  - INCONCLUSIVE: the load never arrived or no tick was observed.

usage: phase_watch.py PHASE BOUND_MS MIN_WAITING [duration_s] [interval_s]
"""
import os
import re
import subprocess
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

WATCHED = sys.argv[1]
BOUND_MS = float(sys.argv[2])
MIN_WAITING = int(sys.argv[3])
DURATION = int(sys.argv[4]) if len(sys.argv) > 4 else 600
INTERVAL = int(sys.argv[5]) if len(sys.argv) > 5 else 5
METRICS_URL = "http://localhost:8080/metrics"
CUEBOT_LOG = "/tmp/cuebot-new.log"
PSQL = spec.psql_cmd()
LOAD_TIMEOUT_S = int(os.environ.get("SIM_PHASE_LOAD_TIMEOUT_S", "420"))

TICK = "cue_maestro_tick_duration_seconds"
PHASE = "cue_maestro_tick_phase_seconds"
LINE = re.compile(r"^(\w+)\{([^}]*)\}\s+([0-9.eE+-]+|NaN|\+Inf)$")
LABEL = re.compile(r'(\w+)="([^"]*)"')
BREAKDOWN = re.compile(r"Maestro tick breakdown: .*?" + WATCHED + r"=(\d+)ms")


def scalar(sql, default=0):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=20).stdout.strip()
        return int(out.splitlines()[0]) if out else default
    except Exception:
        return default


def scrape():
    """{(metric, le_or_phase_key): value} for the two tick histograms."""
    out = {}
    try:
        body = urllib.request.urlopen(METRICS_URL, timeout=10).read().decode()
    except Exception:
        return out
    for ln in body.splitlines():
        m = LINE.match(ln)
        if not m:
            continue
        name = m.group(1)
        if not (name.startswith(TICK) or name.startswith(PHASE)):
            continue
        labels = dict(LABEL.findall(m.group(2)))
        if name.startswith(PHASE) and labels.get("phase") != WATCHED:
            continue
        out[(name, labels.get("le", ""))] = float(m.group(3))
    return out


def quantiles(first, last, metric):
    """(p50, p95, p99, count, mean) in ms from the cumulative bucket deltas."""
    buckets = []
    for (name, le), value in last.items():
        if name == metric + "_bucket" and le:
            buckets.append((float(le), value - first.get((name, le), 0.0)))
    buckets.sort()
    count = last.get((metric + "_count", ""), 0.0) - first.get((metric + "_count", ""), 0.0)
    total = last.get((metric + "_sum", ""), 0.0) - first.get((metric + "_sum", ""), 0.0)
    if count <= 0 or not buckets:
        return None

    def q(p):
        # The bucket whose cumulative share first reaches p; its upper bound is
        # the quantile's upper estimate, the histogram's own resolution.
        target = p * count
        for le, cum in buckets:
            if cum >= target:
                return le * 1000.0
        return buckets[-1][0] * 1000.0

    return q(0.5), q(0.95), q(0.99), int(count), 1000.0 * total / count


def log_phase(since_pos):
    """Max and count of the watched phase's field of breakdown lines past since_pos."""
    try:
        with open(CUEBOT_LOG, errors="ignore") as f:
            f.seek(since_pos)
            vals = [int(m.group(1)) for m in BREAKDOWN.finditer(f.read())]
    except Exception:
        vals = []
    return (max(vals) if vals else 0), len(vals)


def main():
    print(f"watching the {WATCHED} phase for {DURATION}s: it must stay at or under "
          f"{BOUND_MS:.0f} ms with {MIN_WAITING}+ frames waiting.\n", flush=True)
    t0 = time.time()
    waiting = 0
    while time.time() - t0 < min(LOAD_TIMEOUT_S, DURATION):
        waiting = scalar("SELECT COALESCE(sum(int_waiting_count), 0) FROM layer_stat;")
        print(f"t={time.time() - t0:5.0f} | loading | waiting {waiting}", flush=True)
        if waiting >= MIN_WAITING:
            break
        time.sleep(INTERVAL)
    loaded = waiting >= MIN_WAITING
    if not loaded:
        print(f"INCONCLUSIVE: only {waiting} frames waiting after "
              f"{LOAD_TIMEOUT_S}s (need {MIN_WAITING}).", flush=True)
        return
    try:
        log_pos = os.path.getsize(CUEBOT_LOG)
    except Exception:
        log_pos = 0
    first = scrape()
    t_measure = time.time()
    last = first
    while time.time() - t0 < DURATION:
        time.sleep(INTERVAL)
        last = scrape()
        waiting = scalar("SELECT COALESCE(sum(int_waiting_count), 0) FROM layer_stat;")
        running = scalar("SELECT count(*) FROM proc;")
        tq = quantiles(first, last, TICK)
        tick = (f"tick p50 {tq[0]:.0f} p95 {tq[1]:.0f} p99 {tq[2]:.0f} ms "
                f"over {tq[3]} ticks" if tq else "tick: no sample yet")
        print(f"t={time.time() - t0:5.0f} | waiting {waiting} running {running} | {tick}",
              flush=True)

    tq = quantiles(first, last, TICK)
    rq = quantiles(first, last, PHASE)
    read_max, read_n = log_phase(log_pos)
    window = time.time() - t_measure
    print(f"\n==== {WATCHED.upper()} PHASE VERDICT ====", flush=True)
    if not tq:
        print("INCONCLUSIVE: no tick observed in the measured window.", flush=True)
        return
    read_ms = rq[1] if rq else float(read_max)
    read = (f"{WATCHED} p95 {rq[1]:.0f} ms (histogram)" if rq
            else f"{WATCHED} max {read_max} ms over {read_n} logged slow ticks")
    print(f"tick p50 {tq[0]:.0f} p95 {tq[1]:.0f} p99 {tq[2]:.0f} mean {tq[4]:.0f} ms "
          f"over {tq[3]} ticks in {window:.0f}s; {read}; waiting {waiting} at the end",
          flush=True)
    if read_ms <= BOUND_MS:
        print(f"PASS: {WATCHED} phase {read_ms:.0f} ms at or under {BOUND_MS:.0f} ms with "
              f"{waiting} frames waiting.", flush=True)
    else:
        print(f"FAIL: {WATCHED} phase {read_ms:.0f} ms over {BOUND_MS:.0f} ms with {waiting} "
              f"frames waiting; it grows with the load.", flush=True)


if __name__ == "__main__":
    main()
