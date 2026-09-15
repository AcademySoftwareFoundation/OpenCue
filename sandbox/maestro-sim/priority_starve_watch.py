"""Priority-fairness STARVATION verdict: is low-priority work starved by high?

Companion to inject_priority_starve.py, which floods the farm with two identical narrow-
job streams differing ONLY in priority -- HIGH (SIM_PRI_HI, default 300) and LOW
(SIM_PRI_LO, default 100), the high stream deep enough to fill the farm alone.
This samples both classes over time (WAITING / RUNNING / SUCCEEDED + each class's
frames/s) and ends with a verdict:

  - FAIL (starvation): LOW completes ~0 frames while HIGH runs -- strict priority
    gives every core to HIGH and LOW never books. This is what today's scheduler
    does, so this test is EXPECTED TO FAIL until priority is made stochastic.
  - PASS: LOW keeps completing a share of frames roughly proportional to its
    priority (~LO/(LO+HI)), so it is not starved.

Throughput (frames/s) per class is the verdict metric; farm util, reservations
and backfill are shown inline (sim_metrics) so saturation is visible -- a LOW
stall only means starvation if the farm is actually full.

usage: priority_starve_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_metrics

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PSQL = spec.psql_cmd()
PRI_HI = int(os.environ.get("SIM_PRI_HI", "300"))
PRI_LO = int(os.environ.get("SIM_PRI_LO", "100"))
EXPECT_LO = PRI_LO / float(PRI_LO + PRI_HI)   # ideal proportional share for LOW

# cuebot rewrites '-' -> '_', so 'sim-test-prihi-001' lands as '...prihi_001'.
# Match on the stable prihi / prilo tokens.
SEL = "j.str_name LIKE '%prihi%' OR j.str_name LIKE '%prilo%'"
CLS = "CASE WHEN j.str_name LIKE '%prihi%' THEN 'hi' ELSE 'lo' END"

SQL = f"""
SELECT {CLS} AS cls, f.str_state AS state, count(*) AS n
FROM frame f JOIN job j ON f.pk_job = j.pk_job
WHERE ({SEL})
GROUP BY 1, 2 ORDER BY 1, 2;
"""

SQL_AGE = f"""
SELECT cls, max(EXTRACT(EPOCH FROM (now()-ts_started)))::int FROM (
  SELECT DISTINCT j.pk_job, {CLS} AS cls, j.ts_started
  FROM frame f JOIN job j ON f.pk_job = j.pk_job
  WHERE ({SEL}) AND f.str_state='WAITING'
) s GROUP BY cls;
"""


def q(sql):
    return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                          timeout=15).stdout.strip()


def snapshot():
    counts = {"hi": {}, "lo": {}}
    age = {"hi": 0, "lo": 0}
    for line in q(SQL).splitlines():
        p = line.split("|")
        if len(p) == 3:
            counts.setdefault(p[0], {})[p[1]] = int(p[2])
    for line in q(SQL_AGE).splitlines():
        p = line.split("|")
        if len(p) == 2:
            age[p[0]] = int(p[1])
    return counts, age


def done(c):
    return c.get("SUCCEEDED", 0)


def main():
    print(f"watching PRIORITY fairness for {DURATION}s: HI=pri{PRI_HI} vs "
          f"LO=pri{PRI_LO} (ideal LO share ~{EXPECT_LO*100:.0f}%). Per-class "
          f"frames/s is the verdict; util / resv / backfill shown inline.\n",
          flush=True)
    t0 = time.time()
    prev_t = t0
    prev = {"hi": 0, "lo": 0}
    peak_age = {"hi": 0, "lo": 0}
    last = None
    while time.time() - t0 < DURATION:
        counts, age = snapshot()
        util, maxidle = sim_metrics.farm_state()
        ev, gr, held = sim_metrics.resv_grants()
        bf_tot, _ = sim_metrics.backfill()
        now = time.time()
        dt = (now - prev_t) or 1.0
        hi_d, lo_d = done(counts.get("hi", {})), done(counts.get("lo", {}))
        hi_s = (hi_d - prev["hi"]) / dt
        lo_s = (lo_d - prev["lo"]) / dt
        prev_t = now
        prev = {"hi": hi_d, "lo": lo_d}
        for c in ("hi", "lo"):
            peak_age[c] = max(peak_age[c], age[c])
        h, l = counts.get("hi", {}), counts.get("lo", {})
        print(f"t={now-t0:5.0f} | util {util:5.1f}% idle {maxidle:4d}c "
              f"resv={gr} bf={bf_tot} | "
              f"HI pri{PRI_HI} {hi_s:6.1f}/s run={h.get('RUNNING',0):5d} "
              f"wait={h.get('WAITING',0):6d} done={hi_d:6d} | "
              f"LO pri{PRI_LO} {lo_s:6.1f}/s run={l.get('RUNNING',0):5d} "
              f"wait={l.get('WAITING',0):6d} done={lo_d:6d}", flush=True)
        last = counts
        time.sleep(INTERVAL)

    counts = last or snapshot()
    h, l = counts.get("hi", {}), counts.get("lo", {})
    hi_d, lo_d = done(h), done(l)
    tot = hi_d + lo_d
    share = (lo_d / tot) if tot else 0.0
    util, maxidle = sim_metrics.farm_state()
    print("\n==== PRIORITY-FAIRNESS VERDICT ====", flush=True)
    print(f"farm now: util={util:.1f}%  largest idle block={maxidle}c", flush=True)
    print(f"HI (pri{PRI_HI}): done={hi_d} run={h.get('RUNNING',0)} "
          f"wait={h.get('WAITING',0)}", flush=True)
    print(f"LO (pri{PRI_LO}): done={lo_d} run={l.get('RUNNING',0)} "
          f"wait={l.get('WAITING',0)} peak-wait={peak_age['lo']}s", flush=True)
    print(f"LO share of completed frames: {share*100:.1f}%  "
          f"(ideal proportional share ~{EXPECT_LO*100:.0f}%)", flush=True)
    if hi_d == 0 and h.get('RUNNING', 0) == 0:
        print("INCONCLUSIVE: the HI stream never ran -- there was no contention to "
              "starve LO. Raise the load / saturate the farm (HI alone must fill "
              "it) and rerun.", flush=True)
    elif lo_d == 0 or share < 0.03:
        print(f"FAIL (starvation): LO (pri{PRI_LO}) completed {lo_d} frames "
              f"({share*100:.1f}%) while HI completed {hi_d}. Strict priority gives "
              f"every core to HI, so LO is starved. This is the bug the test "
              f"documents -- it should flip to PASS once priority is stochastic.",
              flush=True)
    elif share >= 0.5 * EXPECT_LO:
        print(f"PASS: LO kept completing ({lo_d} frames, {share*100:.1f}% of total "
              f"-- ~its proportional share of ~{EXPECT_LO*100:.0f}%), so it is not "
              f"starved by HI.", flush=True)
    else:
        print(f"WARN: LO made some progress ({lo_d} frames, {share*100:.1f}%) but "
              f"well below its proportional share (~{EXPECT_LO*100:.0f}%). Inspect "
              f"the trajectory above.", flush=True)


if __name__ == "__main__":
    main()
