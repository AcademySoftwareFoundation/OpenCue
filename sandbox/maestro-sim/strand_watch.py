"""Report stranding of the BIG jobs injected by inject_big.py.

Samples the big jobs' frames over time and prints, per priority class
(equal / high), how many big frames are WAITING vs RUNNING vs SUCCEEDED and the
age of the oldest big job still holding a waiting frame ("stranded for Ns").
Ends with a verdict: if big frames never run while small frames keep completing,
that is the head-of-line starvation reservations are meant to fix.

usage: strand_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PSQL = spec.psql_cmd()

# cuebot rewrites the submitted job name (show-shot-user prefix, '-' -> '_'), so
# 'sim-test-big-eq-001' lands as 'sim-test-sim_sim_test_big_eq_001'. Match on the
# stable 'big_eq' / 'big_hi' tokens. ('_' is a LIKE wildcard but only our big
# jobs contain 'big', so the match is unambiguous.)
BIG = "j.str_name LIKE '%big_eq%' OR j.str_name LIKE '%big_hi%'"
CLS = "CASE WHEN j.str_name LIKE '%big_hi%' THEN 'high' ELSE 'equal' END"

# Per-class (equal/high) counts of big frames by state.
SQL = f"""
SELECT {CLS} AS cls, f.str_state AS state, count(*) AS n
FROM frame f JOIN job j ON f.pk_job = j.pk_job
WHERE {BIG}
GROUP BY 1, 2 ORDER BY 1, 2;
"""

# Age of the oldest big job (per class) that still has a WAITING frame.
SQL_AGE = f"""
SELECT cls, max(EXTRACT(EPOCH FROM (now()-ts_started)))::int FROM (
  SELECT DISTINCT j.pk_job, {CLS} AS cls, j.ts_started
  FROM frame f JOIN job j ON f.pk_job = j.pk_job
  WHERE ({BIG}) AND f.str_state='WAITING'
) s GROUP BY cls;
"""

# Per-job rollup for the final verdict: how many big jobs never ran a single
# frame ("stranded"), per priority class.
SQL_PERJOB = f"""
SELECT cls,
       count(*) AS jobs,
       sum(CASE WHEN done=0 AND running=0 THEN 1 ELSE 0 END) AS stranded,
       max(wait_age) AS oldest_wait
FROM (
  SELECT j.pk_job, {CLS} AS cls,
    sum(CASE WHEN f.str_state='SUCCEEDED' THEN 1 ELSE 0 END) AS done,
    sum(CASE WHEN f.str_state='RUNNING'  THEN 1 ELSE 0 END) AS running,
    max(CASE WHEN f.str_state='WAITING'
             THEN EXTRACT(EPOCH FROM (now()-j.ts_started)) ELSE 0 END)::int AS wait_age
  FROM frame f JOIN job j ON f.pk_job = j.pk_job
  WHERE {BIG}
  GROUP BY j.pk_job, 2
) p GROUP BY cls ORDER BY cls;
"""

# Small-frame throughput, to show the farm is busy while big work starves.
SQL_SMALL_DONE = ("SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                  "WHERE j.str_name LIKE 'sim-test-sim_f%' AND f.str_state='SUCCEEDED';")


def q(sql):
    return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                          timeout=15).stdout.strip()


def snapshot():
    """Return {cls: {state: n}}, {cls: max_wait_age}."""
    counts = {"equal": {}, "high": {}}
    age = {"equal": 0, "high": 0}
    for line in q(SQL).splitlines():
        parts = line.split("|")
        if len(parts) != 3:
            continue
        cls, state, n = parts
        counts.setdefault(cls, {})[state] = int(n)
    for line in q(SQL_AGE).splitlines():
        parts = line.split("|")
        if len(parts) != 2:
            continue
        cls, a = parts
        age[cls] = int(a)
    return counts, age


def small_done():
    try:
        return int(q(SQL_SMALL_DONE) or 0)
    except ValueError:
        return -1


def fmt(c):
    return (f"wait={c.get('WAITING',0):3d} run={c.get('RUNNING',0):3d} "
            f"done={c.get('SUCCEEDED',0):3d}")


def main():
    print(f"watching BIG-job stranding for {DURATION}s "
          f"(equal vs high priority)\n", flush=True)
    print(f"{'t':>4}  {'small_done':>10}  | "
          f"{'EQUAL':>28}  stuck | {'HIGH':>28}  stuck", flush=True)
    t0 = time.time()
    peak_run = {"equal": 0, "high": 0}
    base_small = small_done()
    last = None
    while time.time() - t0 < DURATION:
        counts, age = snapshot()
        sd = small_done()
        for cls in ("equal", "high"):
            peak_run[cls] = max(peak_run[cls], counts.get(cls, {}).get("RUNNING", 0))
        print(f"{time.time()-t0:4.0f}  {sd-base_small:10d}  | "
              f"{fmt(counts.get('equal', {})):>28}  {age['equal']:4d}s | "
              f"{fmt(counts.get('high', {})):>28}  {age['high']:4d}s", flush=True)
        last = (counts, age)
        time.sleep(INTERVAL)

    counts, age = last or snapshot()
    print("\n==== STRAND VERDICT ====", flush=True)
    print(f"small frames completed during window: {small_done()-base_small}", flush=True)
    perjob = {}
    for line in q(SQL_PERJOB).splitlines():
        p = line.split("|")
        if len(p) == 4:
            perjob[p[0]] = (int(p[1]), int(p[2]), int(p[3]))  # jobs, stranded, oldest
    for cls in ("equal", "high"):
        c = counts.get(cls, {})
        jobs, stranded, oldest = perjob.get(cls, (0, 0, 0))
        print(f"  {cls:5s} priority: {jobs} big jobs injected, "
              f"{stranded} NEVER ran a single frame (stranded); "
              f"oldest waiting {oldest}s; frames now "
              f"wait={c.get('WAITING',0)} run={c.get('RUNNING',0)} "
              f"done={c.get('SUCCEEDED',0)}", flush=True)
    print("\nWithout reservations, big jobs strand: large stays packed with "
          "small frames and never frees enough cores at once. With reservations "
          "on, blocked big jobs hold draining hosts and get placed.", flush=True)


if __name__ == "__main__":
    main()
