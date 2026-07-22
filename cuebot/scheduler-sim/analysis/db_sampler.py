import time, subprocess, sys, os
OUT = sys.argv[1]
_PORT = os.environ.get("SIM_PG_PORT", "5433")
_HOST = os.environ.get("SIM_PG_HOST", "127.0.0.1")
PSQL = ["psql","-tA","-h",_HOST,"-p",_PORT,"-U","cue","-d","cuebot","-c"]
def q(sql): return subprocess.run(PSQL+[sql], capture_output=True, text=True).stdout.strip()
with open(OUT,"w") as f:
    f.write("ts,commits,rollbacks,tup_ret,tup_fetch,ins,upd,del,deadlocks,"
            "blks_read,blks_hit,active,lockwait\n"); f.flush()
    while True:
        db = q("SELECT xact_commit||','||xact_rollback||','||tup_returned||','||tup_fetched"
               "||','||tup_inserted||','||tup_updated||','||tup_deleted||','||deadlocks"
               "||','||blks_read||','||blks_hit "
               "FROM pg_stat_database WHERE datname='cuebot'")
        act = q("SELECT count(*) FILTER (WHERE state='active')||','||"
                "count(*) FILTER (WHERE wait_event_type='Lock') "
                "FROM pg_stat_activity WHERE datname='cuebot' AND pid<>pg_backend_pid()")
        if db and act:
            f.write(f"{time.strftime('%H:%M:%S')},{db},{act}\n"); f.flush()
        time.sleep(2)
