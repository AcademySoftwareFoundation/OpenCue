"""Wide-job DURATION fairness: are short-frame wide jobs starved by long ones?

Companion to inject_big.py's mixed-duration mode (SIM_STRAND_DUR_MIX=1), which
injects identical 64-core wide jobs that differ ONLY in per-frame run time -- a
"durshort" class and a "durlong" class, same cores/memory/priority. Both compete
for the same reservations. This samples the two classes over time (WAITING /
RUNNING / SUCCEEDED + the age of the oldest job still waiting) and ends with a
verdict: the SHORT class must keep completing and its oldest wait must not grow
unbounded while the LONG class holds reserved hosts. If short frames never get
through while long frames run, that is the liveness failure we are testing for.

Each sample and the verdict also report farm utilization, the largest idle-core
block (the saturation signal), small-frame throughput (frames/s), and the
reservation grants pulled from the cuebot log -- so a run shows whether the farm
was saturated and reservations were actually exercised without any by-hand
psql/grep (see sim_metrics.py).

usage: strand_dur_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_metrics

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PSQL = spec.psql_cmd()

# cuebot rewrites '-' -> '_' in job names, so 'sim-test-big-durshort-001' lands
# as '...big_durshort_001'. Match on the stable durshort / durlong tokens.
BIG = "j.str_name LIKE '%durshort%' OR j.str_name LIKE '%durlong%'"
CLS = "CASE WHEN j.str_name LIKE '%durlong%' THEN 'long' ELSE 'short' END"

# Per-class counts of wide-job frames by state.
SQL = f"""
SELECT {CLS} AS cls, f.str_state AS state, count(*) AS n
FROM frame f JOIN job j ON f.pk_job = j.pk_job
WHERE {BIG}
GROUP BY 1, 2 ORDER BY 1, 2;
"""

# Age of the oldest wide job (per class) that still has a WAITING frame.
SQL_AGE = f"""
SELECT cls, max(EXTRACT(EPOCH FROM (now()-ts_started)))::int FROM (
  SELECT DISTINCT j.pk_job, {CLS} AS cls, j.ts_started
  FROM frame f JOIN job j ON f.pk_job = j.pk_job
  WHERE ({BIG}) AND f.str_state='WAITING'
) s GROUP BY cls;
"""

# Small-frame throughput, to confirm the farm stays busy (so any short-class
# stall is starvation by the long class, not an idle farm).
SQL_SMALL_DONE = ("SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                  "WHERE j.str_name LIKE 'sim-test-sim_f%' AND f.str_state='SUCCEEDED';")


def q(sql):
    return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                          timeout=15).stdout.strip()


def snapshot():
    """Return {cls: {state: n}}, {cls: oldest_waiting_age}."""
    counts = {"short": {}, "long": {}}
    age = {"short": 0, "long": 0}
    for line in q(SQL).splitlines():
        p = line.split("|")
        if len(p) == 3:
            counts.setdefault(p[0], {})[p[1]] = int(p[2])
    for line in q(SQL_AGE).splitlines():
        p = line.split("|")
        if len(p) == 2:
            age[p[0]] = int(p[1])
    return counts, age


def small_done():
    try:
        return int(q(SQL_SMALL_DONE) or 0)
    except ValueError:
        return -1


def fmt(c):
    return (f"wait={c.get('WAITING',0):3d} run={c.get('RUNNING',0):3d} "
            f"done={c.get('SUCCEEDED',0):4d}")


def main():
    print(f"watching wide-job DURATION fairness for {DURATION}s "
          f"(short-frame vs long-frame wide jobs); util / frames-s / reservation "
          f"grants are reported inline so nothing needs grepping afterward\n",
          flush=True)
    t0 = time.time()
    base_small = small_done()
    peak_age = {"short": 0, "long": 0}
    peak_run = {"short": 0, "long": 0}
    prev_t, prev_small = t0, base_small
    last = None
    while time.time() - t0 < DURATION:
        counts, age = snapshot()
        sd = small_done()
        util, maxidle = sim_metrics.farm_state()
        ev, gr, held = sim_metrics.resv_grants()
        bf_tot, bf_last = sim_metrics.backfill()
        now = time.time()
        rate = (sd - prev_small) / (now - prev_t) if now > prev_t else 0.0
        prev_t, prev_small = now, sd
        for cls in ("short", "long"):
            peak_age[cls] = max(peak_age[cls], age[cls])
            peak_run[cls] = max(peak_run[cls], counts.get(cls, {}).get("RUNNING", 0))
        print(f"t={now-t0:5.0f} | util {util:5.1f}% idle {maxidle:3d}c | "
              f"small {rate:5.0f}/s done {sd-base_small:5d} | "
              f"resv ev={ev} grant={gr} held={held} bf={bf_tot} | "
              f"SHORT {fmt(counts.get('short', {}))} age {age['short']:4d}s | "
              f"LONG {fmt(counts.get('long', {}))} age {age['long']:4d}s", flush=True)
        last = (counts, age)
        time.sleep(INTERVAL)

    counts, age = last or snapshot()
    s, l = counts.get("short", {}), counts.get("long", {})
    s_done, l_done = s.get("SUCCEEDED", 0), l.get("SUCCEEDED", 0)
    s_run, l_run = s.get("RUNNING", 0), l.get("RUNNING", 0)
    total_small = small_done() - base_small
    util, maxidle = sim_metrics.farm_state()
    ev, gr, held = sim_metrics.resv_grants()
    bf_tot, bf_last = sim_metrics.backfill()
    print("\n==== DURATION-FAIRNESS VERDICT ====", flush=True)
    print(f"farm now: util={util:.1f}%  largest idle block={maxidle}c (the farm is "
          f"saturated for a wide job while this stays below its width, e.g. < 64c)",
          flush=True)
    print(f"reservations granted during run: events={ev} totalGranted={gr} "
          f"held={held}" + ("  <-- NONE: reservations off, or the farm never "
          "saturated enough to need one" if gr == 0 else ""), flush=True)
    print(f"backfill placements onto draining reserved hosts: {bf_tot} (EASY "
          f"backfill -- keeps a reserved host productive while it drains)", flush=True)
    print(f"small-frame throughput: {total_small} frames (~{total_small/DURATION:.0f}"
          f"/s) -- confirms the farm stayed busy, so any short-class stall is "
          f"starvation, not an idle farm", flush=True)
    print(f"  SHORT wide jobs: done={s_done} run={s_run} wait={s.get('WAITING',0)} "
          f"oldest-waiting now={age['short']}s peak={peak_age['short']}s", flush=True)
    print(f"  LONG  wide jobs: done={l_done} run={l_run} wait={l.get('WAITING',0)} "
          f"oldest-waiting now={age['long']}s peak={peak_age['long']}s", flush=True)
    if l_run == 0 and l_done == 0:
        print("INCONCLUSIVE: the LONG class never ran"
              + (f", and NO reservations were granted (grant={gr})" if gr == 0 else "")
              + ", so nothing was holding hosts to starve the SHORT class. Lengthen "
              "the run or raise the small backlog (e.g. --compress) so the farm "
              "stays saturated and the long class gets in.", flush=True)
    elif s_done == 0:
        print("FAIL (starvation): SHORT-frame wide jobs completed ZERO frames while "
              "LONG-frame wide jobs ran. The long class is holding the reserved "
              "hosts and the short class never gets through.", flush=True)
    elif peak_age["short"] >= 0.9 * DURATION and s_run == 0:
        print("WARN (possible tail starvation): SHORT made some progress, but its "
              "oldest job waited ~the whole window and none are running at the end. "
              "Inspect the trajectory above.", flush=True)
    else:
        print(f"PASS: SHORT-frame wide jobs kept completing ({s_done} frames) "
              f"alongside the LONG class, so they are not starved by it.", flush=True)


if __name__ == "__main__":
    main()
