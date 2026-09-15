"""STRANDGROW verdict: do memory-heavy threadable frames get their core share?

Companion to inject_strandgrow.py. The flood layer asks 1 core and its frames
REALLY hold MEM_MB of rss (the fake RQD pins their reported rss; declarations
are not trusted by design). The scheduler must first probe at the ask (no rss
evidence yet: it has to wait for the reports), then grow every later launch to
round(rss / the group's own memory-per-core) cores (3.5-3.875G/core on this
farm, so 18G -> 500 core-points). The non-threadable control holds the same
rss and must stay at exactly 100 points forever.

Live sampling narrates; the verdict is judged on the persistent record
(frame.int_cores survives completion, written at dispatch):
  - PASS: only a small probe of frames booked at the ask (the scheduler must
    not blast an unproven layer across the farm), the late launches book at
    the metric grant, the control never grew, and the farm's cores worked
    (peak core utilisation over the floor instead of stranding).
  - FAIL: the flood stayed at the ask (the production disease), the control
    grew, or cores stayed stranded.
  - INCONCLUSIVE: the flood never ramped enough to judge.

usage: strandgrow_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 240
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PSQL = spec.psql_cmd()
MEM_MB = int(os.environ.get("SIM_STRANDGROW_MEM_MB", "18432"))
# The scheduler derives its metric from each group's own hosts (memory total
# over cores total). All three sim shapes sit at 3.5-3.875G per core, so an
# 18G layer rounds to 5 cores on every one of them.
EXP = 500
MIN_STARTED = 40                         # flood frames needed to judge
MIN_UTIL = 60.0                          # % of farm cores busy at peak
LATE_N = 50                              # last-started frames that must carry the grant
MAX_PROBE = 40                           # ask-sized wave must stay a probe, not a blast


def rows(sql):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return [ln.split("|") for ln in out.splitlines() if ln]
    except Exception:
        return []


def hist(token):
    """{core_points: frames_started} from the persistent frame record."""
    r = rows(f"SELECT f.int_cores, count(*) FROM frame f "
             f"JOIN job j ON j.pk_job = f.pk_job "
             f"WHERE j.str_name LIKE '%{token}%' AND f.ts_started IS NOT NULL "
             f"GROUP BY 1;")
    return {int(a): int(b) for a, b in r}


def late_hist(token, n):
    """Same, over only the n last-started frames (the post-evidence epoch)."""
    r = rows(f"SELECT c, count(*) FROM (SELECT f.int_cores AS c FROM frame f "
             f"JOIN job j ON j.pk_job = f.pk_job "
             f"WHERE j.str_name LIKE '%{token}%' AND f.ts_started IS NOT NULL "
             f"ORDER BY f.ts_started DESC LIMIT {n}) t GROUP BY 1;")
    return {int(a): int(b) for a, b in r}


def median_of(h):
    total = sum(h.values())
    if not total:
        return 0
    seen = 0
    for cores in sorted(h):
        seen += h[cores]
        if seen * 2 >= total:
            return cores
    return 0


def main():
    print(f"watching STRANDGROW for {DURATION}s: frames really holding "
          f"{MEM_MB}mb rss must book at {EXP} core-points (the farm's own "
          f"memory-per-core metric) once the reports have shown the rss; the first wave books "
          f"at the 100-point ask (no evidence yet) and the non-threadable "
          f"control stays at 100 forever.\n", flush=True)
    t0 = time.time()
    peak_util = 0.0
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        u = rows("SELECT sum(int_cores), sum(int_cores - int_cores_idle) "
                 "FROM host;")
        util = 0.0
        if u and int(u[0][0] or 0) > 0:
            util = 100.0 * int(u[0][1] or 0) / int(u[0][0])
        peak_util = max(peak_util, util)
        live = rows("SELECT p.int_cores_reserved, count(*) FROM proc p "
                    "JOIN job j ON j.pk_job = p.pk_job "
                    "WHERE j.str_name LIKE '%simstrandgrow%' GROUP BY 1 "
                    "ORDER BY 1;")
        dist = " ".join(f"{int(a) // 100}c x{b}" for a, b in live) or "none"
        print(f"t={t:5.0f} | util {util:5.1f}% | live procs: {dist}",
              flush=True)
        time.sleep(INTERVAL)

    flood = hist("simstrandgrow_flood")
    ctrl = hist("simstrandgrow_ctrl")
    late = late_hist("simstrandgrow_flood", LATE_N)
    started = sum(flood.values())
    med = median_of(flood)
    waited = flood.get(100, 0)
    at_exp = 100.0 * flood.get(EXP, 0) / started if started else 0.0
    late_n = sum(late.values())
    late_at_exp = 100.0 * late.get(EXP, 0) / late_n if late_n else 0.0
    ctrl_max = max(ctrl) if ctrl else 0

    print("\n==== STRANDGROW VERDICT ====", flush=True)
    print(f"flood median {med} pts, {at_exp:.0f}% at {EXP} pts over {started} "
          f"started frames; ask-first wave {waited}; late {late_n} frames "
          f"{late_at_exp:.0f}% at {EXP}; ctrl max {ctrl_max}; peak core util "
          f"{peak_util:.1f}%", flush=True)
    if started < MIN_STARTED:
        print(f"INCONCLUSIVE: only {started} flood frames ever started "
              f"(under {MIN_STARTED}); nothing to judge.", flush=True)
    elif ctrl and ctrl_max > 100:
        print(f"FAIL: a non-threadable frame was grown to {ctrl_max} "
              f"core-points; the threadable gate leaks.", flush=True)
    elif med <= 100:
        print(f"FAIL: the flood stayed at the ask (median {med} pts) and "
              f"peak core utilisation was {peak_util:.1f}%; memory-heavy "
              f"frames still strand host cores.", flush=True)
    elif waited < 1 or waited > MAX_PROBE or late_at_exp < 80.0 or peak_util < MIN_UTIL:
        print(f"FAIL: the probe-then-grow story is broken (ask-sized probe "
              f"{waited}, allowed 1..{MAX_PROBE}; late share {late_at_exp:.0f}% "
              f"at {EXP}; peak util {peak_util:.1f}%).", flush=True)
    else:
        print(f"PASS: only a probe booked at the ask ({waited} frames while "
              f"the farm gathered rss evidence), later launches booked at the "
              f"{EXP}-point share ({late_at_exp:.0f}% of the last {late_n}), "
              f"the non-threadable control stayed at 100, and the cores "
              f"worked (peak util {peak_util:.1f}%).", flush=True)


if __name__ == "__main__":
    main()
