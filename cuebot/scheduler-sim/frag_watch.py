"""FRAGMENTATION verdict: cue_scheduler_fragmented_cores{reason} straight off the
live scheduler.

Companion to `simulate.py --frag-test` (a standalone scenario, not part of the
--verify battery). The scheduler's fragmentation gauge is scraped from cuebot's
Prometheus /metrics endpoint (embedded Tomcat, port SIM_METRICS_PORT) once per
INTERVAL and recorded as a time series, one column per cause:

    packing  - no host had enough idle cores for one frame (wide layers)
    memory   - cores fit somewhere but not the RAM
    resource - GPU did not (or a fitting host was held)
    cap      - a job/show/limit/folder/license quota

The scenario floods a small, feeder-saturated farm with WIDE frames (--strand)
and reservations OFF, so those frames can never assemble their cores and strand
on core fragmentation every tick -- a guaranteed, continuous `packing` signal.

    COVERAGE (floor, so the verdict can't pass vacuously):
      - peak packing cores >= SIM_FRAG_MIN_PACKING (default 50).

usage: frag_watch.py [duration_s] [interval_s]
"""
import os
import re
import sys
import time
import urllib.request

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
PORT = int(os.environ.get("SIM_METRICS_PORT", "8080"))
URL = f"http://127.0.0.1:{PORT}/metrics"
CSV = os.environ.get("SIM_FRAG_CSV", "")
MIN_PACKING = float(os.environ.get("SIM_FRAG_MIN_PACKING", "50"))
REASONS = ["packing", "memory", "resource", "cap"]

# cuebot resolves farm hostnames via a private hosts file, but this watcher talks
# to 127.0.0.1 directly; bypass any inherited HTTP(S)_PROXY so localhost is local.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_LINE = re.compile(r'cue_scheduler_fragmented_cores\{([^}]*)\}\s+([0-9.eE+-]+)')
_REASON = re.compile(r'reason="([^"]+)"')


def scrape():
    """Return {reason: cores} for the most recent tick, or None if unreachable."""
    try:
        body = _OPENER.open(URL, timeout=5).read().decode("utf-8", "replace")
    except Exception:
        return None
    vals = {r: 0.0 for r in REASONS}
    for m in _LINE.finditer(body):
        rm = _REASON.search(m.group(1))
        if rm and rm.group(1) in vals:
            vals[rm.group(1)] += float(m.group(2))
    return vals


def main():
    rows = []
    peak = {r: 0.0 for r in REASONS}
    t0 = time.time()
    misses = 0
    while time.time() - t0 < DURATION:
        vals = scrape()
        if vals is None:
            misses += 1
        else:
            rows.append((round(time.time() - t0, 1), vals))
            for r in REASONS:
                peak[r] = max(peak[r], vals[r])
        time.sleep(INTERVAL)

    if CSV and rows:
        with open(CSV, "w") as f:
            f.write("t," + ",".join(REASONS) + "\n")
            for t, vals in rows:
                f.write(f"{t}," + ",".join(f"{vals[r]:.1f}" for r in REASONS) + "\n")
        print(f"FRAGMENTATION wrote {len(rows)} samples to {CSV}")

    if misses:
        print(f"FRAGMENTATION note: {misses} scrape misses "
              f"(endpoint not up yet, or metrics.prometheus.collector off)")
    print("FRAGMENTATION peaks (cores): "
          + ", ".join(f"{r}={peak[r]:.0f}" for r in REASONS))
    ok = peak["packing"] >= MIN_PACKING
    print(f"FRAGMENTATION verdict: {'PASS' if ok else 'FAIL'} "
          f"(peak packing {peak['packing']:.0f} >= {MIN_PACKING})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
