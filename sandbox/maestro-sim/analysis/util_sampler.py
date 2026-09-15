"""Sample farm utilization over time -> CSV, for plot_run.py.

Every 2s records utilization straight from the host table -- (sum(int_cores) -
sum(int_cores_idle)) / sum(int_cores), the DB's own authoritative accounting of
busy vs idle cores -- plus running/waiting frame counts and a succeeded-frame
counter. That last column is the throughput signal: util alone can't tell a
working scheduler from one that books then unbooks (both look busy), so a run is
judged on how fast succeeded_frames climbs, not on util. Companion to
db_sampler.py; simulate.py starts both automatically for a watched run. Honors
SIM_PG_HOST / SIM_PG_PORT / SIM_PG_BIN.

usage: util_sampler.py <out.csv>
"""
import time, subprocess, sys, os
OUT = sys.argv[1]
_PORT = os.environ.get("SIM_PG_PORT", "5433")
_HOST = os.environ.get("SIM_PG_HOST", "127.0.0.1")
# Full psql path (not bare "psql"): a non-root user invoking the sim may have a
# minimal PATH that lacks the postgres bin dir.
_BIN = os.environ.get("SIM_PG_BIN", "/usr/lib/postgresql/16/bin")
PSQL = [f"{_BIN}/psql", "-tA", "-h", _HOST, "-p", _PORT, "-U", "cue", "-d", "cuebot", "-c"]


def q(sql):
    return subprocess.run(PSQL + [sql], capture_output=True, text=True).stdout.strip()


with open(OUT, "w") as f:
    f.write("ts,util_pct,running_frames,waiting_frames,busy_cores,total_cores,"
            "succeeded_frames,busy_mem_kb,total_mem_kb\n")
    f.flush()
    while True:
        # Utilization straight from the host table's own accounting: busy =
        # total - idle cores (in core-points, so the ratio is unitless). This is
        # the authoritative source -- each booking decrements int_cores_idle -- so
        # no proc join or pk_frame filter is needed.
        #
        # succeeded_frames is the THROUGHPUT signal, recorded next to util on
        # purpose: high utilization only means cores are BOOKED, not that work is
        # getting done (a scheduler that books then unbooks looks fully busy while
        # completing nothing). So judge a run on how fast this count climbs,
        # frames actually finishing, never on util alone.
        # busy_mem/total_mem (kB) come straight from the host table too, so the
        # cores-vs-memory graph can show which resource actually binds the farm.
        row = q("SELECT "
                "(SELECT COALESCE(sum(int_cores - int_cores_idle),0) FROM host),"
                "(SELECT COALESCE(sum(int_cores),0) FROM host),"
                "(SELECT count(*) FROM frame WHERE str_state='RUNNING'),"
                "(SELECT count(*) FROM frame WHERE str_state='WAITING'),"
                "(SELECT count(*) FROM frame WHERE str_state='SUCCEEDED'),"
                "(SELECT COALESCE(sum(int_mem - int_mem_idle),0) FROM host),"
                "(SELECT COALESCE(sum(int_mem),0) FROM host)")
        parts = row.split("|") if row else []
        if len(parts) == 7:
            try:
                busy, tc, run, wait, done, busy_mem, tot_mem = (int(x) for x in parts)
            except ValueError:
                time.sleep(2)
                continue
            util = 100.0 * busy / tc if tc else 0.0
            f.write(f"{time.strftime('%H:%M:%S')},{util:.2f},{run},{wait},"
                    f"{busy},{tc},{done},{busy_mem},{tot_mem}\n")
            f.flush()
        time.sleep(2)
