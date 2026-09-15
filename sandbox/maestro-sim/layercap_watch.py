"""LAYERCAP verdict: can one layer blanket a busy machine, or does the cap hold?

Companion to inject_layercap.py (one deep 1-core layer against a saturated
farm; the cap is a contention rule, and background jobs supply the
contention -- the idle-farm case where the cap must YIELD is LAYERCAP_SOLO). Samples every host
running the flood layer and compares its frame count against the reference
cap: max(FLOOR_FRAMES, frac * host cores / layer cores). The reference frac is
fixed by the scenario (SIM_LAYERCAP_REF, default 0.25) regardless of what the
scheduler was configured with, so a run with the cap OFF measures against the
same yardstick and fails, which is the reproduction of the production pile-up.

  - PASS: the flood ramped, no host ever exceeded its reference cap, and the
    layer spread across several hosts.
  - FAIL: any host exceeded its cap on any sample.
  - INCONCLUSIVE: the flood never ramped enough to threaten the cap.

usage: layercap_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
PSQL = spec.psql_cmd()
TOKEN = "simlayercap"
REF_FRAC = float(os.environ.get("SIM_LAYERCAP_REF", "0.25"))
FLOOR_FRAMES = 8
MIN_PEAK = 60           # flood must reach this many running frames to count


def rows(sql):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return [ln.split("|") for ln in out.splitlines() if ln]
    except Exception:
        return []


def main():
    print(f"watching LAYERCAP for {DURATION}s: one 1-core layer floods the "
          f"farm; no host may hold more than max({FLOOR_FRAMES}, "
          f"{int(REF_FRAC*100)}% of its cores) frames of it.\n", flush=True)
    t0 = time.time()
    peak_running = 0
    peak_hosts = 0
    peak_bg = 0
    cap_pinned = 0
    worst_over = 0
    worst_line = ""
    violations = 0
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        r = rows(f"SELECT h.str_name, h.int_cores, count(*) FROM proc p "
                 f"JOIN job j ON j.pk_job = p.pk_job "
                 f"JOIN host h ON h.pk_host = p.pk_host "
                 f"WHERE j.str_name LIKE '%{TOKEN}%' "
                 f"GROUP BY 1, 2 ORDER BY 3 DESC;")
        total = sum(int(x[2]) for x in r)
        peak_running = max(peak_running, total)
        peak_hosts = max(peak_hosts, len(r))
        bg = rows("SELECT count(*) FROM proc p JOIN job j ON j.pk_job = "
                  "p.pk_job WHERE j.str_name LIKE '%simcapbg%';")
        peak_bg = max(peak_bg, int(bg[0][0]) if bg else 0)
        top = ""
        pinned = False
        for name, cores_cp, n in r:
            cores = int(cores_cp) // 100
            cap = max(FLOOR_FRAMES, int(REF_FRAC * cores))
            n = int(n)
            if n == cap:
                pinned = True
            if not top:
                top = f"top {name} {n}/{cap}"
            if n > cap:
                violations += 1
                if n - cap > worst_over:
                    worst_over = n - cap
                    worst_line = f"{name} held {n} frames vs cap {cap}"
        if pinned:
            cap_pinned += 1
        print(f"t={t:5.0f} | running {total:5d} on {len(r):3d} hosts | {top}"
              f"{'  <-- OVER CAP' if top and violations else ''}", flush=True)
        time.sleep(INTERVAL)

    print("\n==== LAYERCAP VERDICT ====", flush=True)
    print(f"peak running {peak_running} frames across {peak_hosts} hosts; "
          f"cap violations {violations}; worst overage {worst_over} frames"
          f"{' (' + worst_line + ')' if worst_line else ''}; "
          f"background peak {peak_bg}; cap pinned {cap_pinned} samples",
          flush=True)
    if peak_bg < 300:
        print(f"INCONCLUSIVE: background work peaked at {peak_bg} running "
              f"frames; the farm was never contended, so the cap holding "
              f"proves nothing (that is LAYERCAP_SOLO's premise).",
              flush=True)
    elif peak_running < MIN_PEAK or cap_pinned < 10:
        print(f"INCONCLUSIVE: flood peak {peak_running} (need {MIN_PEAK}) "
              f"with the cap pinned on only {cap_pinned} samples (need 10); "
              f"the cap was never really pressed.", flush=True)
    elif violations > 0:
        print(f"FAIL: a host exceeded its per-layer share ({worst_line}); "
              f"one layer can still blanket a machine.", flush=True)
    elif peak_hosts < 3:
        print(f"INCONCLUSIVE: the flood only touched {peak_hosts} host(s); "
              f"spread cannot be judged.", flush=True)
    else:
        print(f"PASS: no host ever exceeded its share of the layer and the "
              f"flood spread across {peak_hosts} hosts.", flush=True)


if __name__ == "__main__":
    main()
