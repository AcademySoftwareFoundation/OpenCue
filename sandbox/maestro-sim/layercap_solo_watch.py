"""LAYERCAP_SOLO verdict: does a lone farm-sized layer get the farm?

Companion to inject_layercap_solo.py. One 1-core layer floods an otherwise
idle farm. The per-host layer cap exists for contention; with nothing else
waiting it must yield, or the scheduler strands the cores it is supposed to
sell (a 25% cap caps the whole farm at ~25%).

  - PASS: the flood ramped past the reference cap on real hosts (proof the
    relax engaged) and peak core utilisation reached the floor.
  - FAIL: utilisation plateaued at the cap: the farm idled while one layer
    had thousands of waiting frames (the strand).
  - INCONCLUSIVE: the flood never ramped enough to judge.

usage: layercap_solo_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 240
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PSQL = spec.psql_cmd()
TOKEN = "simlayercapsolo"
REF_FRAC = float(os.environ.get("SIM_LAYERCAP_REF", "0.25"))
FLOOR_FRAMES = 8
MIN_PEAK = 100          # flood must reach this many running frames to judge
MIN_UTIL = 85.0         # % of farm cores busy at peak; the cap strands ~31%


def rows(sql):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return [ln.split("|") for ln in out.splitlines() if ln]
    except Exception:
        return []


def main():
    print(f"watching LAYERCAP_SOLO for {DURATION}s: one 1-core layer alone "
          f"on the farm must blow past the {int(REF_FRAC * 100)}% per-host "
          f"cap and reach {MIN_UTIL:.0f}% core utilisation instead of "
          f"stranding the farm.\n", flush=True)
    t0 = time.time()
    peak_util = 0.0
    peak_running = 0
    peak_hosts = 0
    over_cap_hosts = 0
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        u = rows("SELECT sum(int_cores), sum(int_cores - int_cores_idle) "
                 "FROM host;")
        util = 0.0
        if u and int(u[0][0] or 0) > 0:
            util = 100.0 * int(u[0][1] or 0) / int(u[0][0])
        peak_util = max(peak_util, util)
        r = rows(f"SELECT h.str_name, h.int_cores, count(*) FROM proc p "
                 f"JOIN job j ON j.pk_job = p.pk_job "
                 f"JOIN host h ON h.pk_host = p.pk_host "
                 f"WHERE j.str_name LIKE '%{TOKEN}%' "
                 f"GROUP BY 1, 2 ORDER BY 3 DESC;")
        total = sum(int(x[2]) for x in r)
        peak_running = max(peak_running, total)
        peak_hosts = max(peak_hosts, len(r))
        over = 0
        for name, cores_cp, n in r:
            cap = max(FLOOR_FRAMES, int(REF_FRAC * (int(cores_cp) // 100)))
            if int(n) > cap:
                over += 1
        over_cap_hosts = max(over_cap_hosts, over)
        top = f"top {r[0][0]} x{r[0][2]}" if r else "none"
        print(f"t={t:5.0f} | util {util:5.1f}% | running {total:5d} on "
              f"{len(r):3d} hosts ({over} over cap) | {top}", flush=True)
        time.sleep(INTERVAL)

    print("\n==== LAYERCAP_SOLO VERDICT ====", flush=True)
    print(f"peak util {peak_util:.1f}%; peak running {peak_running} frames "
          f"across {peak_hosts} hosts; hosts over the {int(REF_FRAC * 100)}% "
          f"cap at peak {over_cap_hosts}", flush=True)
    if peak_running < MIN_PEAK:
        print(f"INCONCLUSIVE: the flood only reached {peak_running} running "
              f"frames (under {MIN_PEAK}); nothing to judge.", flush=True)
    elif peak_util >= MIN_UTIL and over_cap_hosts > 0:
        print(f"PASS: alone on the farm, the layer blew past the per-host "
              f"cap ({over_cap_hosts} hosts over) and used the cores (peak "
              f"util {peak_util:.1f}%).", flush=True)
    else:
        print(f"FAIL: the cap stranded the farm; peak util {peak_util:.1f}% "
              f"(floor {MIN_UTIL:.0f}%) with {over_cap_hosts} hosts ever "
              f"over cap while thousands of frames waited.", flush=True)


if __name__ == "__main__":
    main()
