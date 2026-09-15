"""Live consolidated stats heartbeat for a running sim.

Prints one block every INTERVAL seconds so a run can be watched without poking
the DB by hand. Each block reports:
  - real utilization, straight from the host table: (sum(int_cores) -
    sum(int_cores_idle)) / sum(int_cores) -- the DB's own busy/idle accounting
  - throughput rates: frames completing/s and frames entering RUNNING/s (booked)
  - running / waiting frame counts and orphaned (pk_frame IS NULL) procs
  - reservation grants and EASY-backfill placements from the cuebot log
    (resv events/granted/held; bf total/last-window), so "are reservations being
    used, and is backfill keeping drained hosts busy?" is answered inline
  - DB load: commits/s, tuple reads/s, cache-hit ratio, connection states
  - BIG-job breakdown when any are present (injected by inject_big.py): per
    priority class (equal/high) wait/run/done and how many jobs are STRANDED
    (never ran a single frame) plus the oldest waiting job's age.

usage: live_stats.py [duration_s] [interval_s]   (defaults 300, 5)
"""
import os
import sys
import time
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_metrics

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PSQL = spec.psql_cmd(tab=True)

# BIG jobs: cuebot rewrites submitted names, so match the stable big_eq/big_hi
# tokens that inject_big.py uses (see strand_watch.py for the same convention).
BIG = "(j.str_name LIKE '%big_eq%' OR j.str_name LIKE '%big_hi%')"
CLS = "CASE WHEN j.str_name LIKE '%big_hi%' THEN 'high' ELSE 'equal' END"

# One round-trip for the core farm/frame/proc numbers.
CORE_SQL = (
    "SELECT (SELECT sum(int_cores) FROM host), "
    "(SELECT coalesce(sum(int_cores - int_cores_idle),0) FROM host), "
    "(SELECT count(*) FROM proc WHERE pk_frame IS NULL), "
    "(SELECT count(*) FROM frame WHERE str_state='RUNNING'), "
    "(SELECT count(*) FROM frame WHERE str_state='WAITING'), "
    "(SELECT count(*) FROM frame WHERE str_state='SUCCEEDED');"
)

DB_SQL = ("SELECT xact_commit, blks_hit, blks_read, tup_returned "
          "FROM pg_stat_database WHERE datname='cuebot';")

CONN_SQL = ("SELECT state, count(*) FROM pg_stat_activity "
            "WHERE datname='cuebot' GROUP BY state;")

# Per-class big-job rollup: total jobs, jobs that never ran a frame (stranded),
# and the oldest still-waiting job's age in seconds.
BIG_SQL = f"""
SELECT cls,
       sum(CASE WHEN st='WAITING'   THEN n ELSE 0 END) AS waiting,
       sum(CASE WHEN st='RUNNING'   THEN n ELSE 0 END) AS running,
       sum(CASE WHEN st='SUCCEEDED' THEN n ELSE 0 END) AS done
FROM (
  SELECT {CLS} AS cls, f.str_state AS st, count(*) AS n
  FROM frame f JOIN job j ON f.pk_job=j.pk_job
  WHERE {BIG} GROUP BY 1,2
) s GROUP BY cls ORDER BY cls;
"""

BIG_STRAND_SQL = f"""
SELECT cls, count(*) AS jobs,
       sum(CASE WHEN done=0 AND running=0 THEN 1 ELSE 0 END) AS stranded,
       max(wait_age)::int AS oldest_wait
FROM (
  SELECT j.pk_job, {CLS} AS cls,
    sum(CASE WHEN f.str_state='SUCCEEDED' THEN 1 ELSE 0 END) AS done,
    sum(CASE WHEN f.str_state='RUNNING'  THEN 1 ELSE 0 END) AS running,
    max(CASE WHEN f.str_state='WAITING'
             THEN EXTRACT(EPOCH FROM (now()-j.ts_started)) ELSE 0 END) AS wait_age
  FROM frame f JOIN job j ON f.pk_job=j.pk_job
  WHERE {BIG} GROUP BY j.pk_job, 2
) p GROUP BY cls ORDER BY cls;
"""


def q(sql):
    return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                          timeout=20).stdout.strip()


def rows(sql):
    out = q(sql)
    return [line.split("\t") for line in out.split("\n") if line]


def main():
    print(f"[live_stats] every {INTERVAL:.0f}s for {DURATION}s", flush=True)
    t_end = time.time() + DURATION
    prev = None        # (t, succeeded, running, xact_commit, tup_returned)
    while time.time() < t_end:
        t = time.time()
        try:
            farm, wf, nofr, run, wait, done = [int(x) for x in q(CORE_SQL).split("\t")]
            commits, blks_hit, blks_read, tup_ret = [int(x) for x in q(DB_SQL).split("\t")]
        except (ValueError, IndexError):
            time.sleep(INTERVAL)
            continue
        util = 100.0 * wf / farm if farm else 0.0

        line = (f"[{time.strftime('%H:%M:%S')}] util={util:5.1f}%  run={run:6d}  "
                f"wait={wait:6d}  orphan={nofr:5d}")
        if prev:
            dt = t - prev[0]
            done_s = (done - prev[1]) / dt          # frames completing/s
            book_s = (run - prev[2]) / dt + done_s  # frames entering RUNNING/s
            commit_s = (commits - prev[3]) / dt
            line += f"  done/s={done_s:6.1f}  book/s={book_s:6.1f}  commit/s={commit_s:7.0f}"
        prev = (t, done, run, commits, tup_ret)

        cache = 100.0 * blks_hit / (blks_hit + blks_read) if (blks_hit + blks_read) else 0.0
        conns = "/".join(f"{s}:{n}" for s, n in rows(CONN_SQL))
        # Reservation grants + backfill placements from the cuebot log, so "are
        # reservations being used, and is backfill keeping drained hosts busy?"
        # is answered inline -- no tailing the log by hand.
        ev, gr, held = sim_metrics.resv_grants()
        bf_tot, bf_last = sim_metrics.backfill()
        line += (f"  resv[ev={ev} grant={gr} held={held}]  bf[tot={bf_tot} win={bf_last}]"
                 f"  cache={cache:.1f}%  conns[{conns}]")
        print(line, flush=True)

        # BIG-job breakdown, only when big jobs are present.
        big = rows(BIG_SQL)
        if big:
            strand = {r[0]: r[1:] for r in rows(BIG_STRAND_SQL)}
            for r in big:
                cls = r[0]
                jobs, stranded, oldest = strand.get(cls, ("?", "?", "?"))
                print(f"             BIG[{cls:5s}] wait={r[1]:>4} run={r[2]:>4} "
                      f"done={r[3]:>4} | jobs={jobs} STRANDED={stranded} "
                      f"oldest_wait={oldest}s", flush=True)

        time.sleep(max(0, INTERVAL - (time.time() - t)))


if __name__ == "__main__":
    main()
