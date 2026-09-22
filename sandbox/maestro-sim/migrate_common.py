"""Shared helpers for the MIGRATE-topology watchers (migrate_watch, forward_watch).

Both scenarios run inject_migrate.py's flood -- one managed show, five legacy,
three cuebots -- and judge the same ground truth: per-show frame counts, stray
run identities, farm utilization, Maestro's per-show dispatch counter and
fake_rqd's DOUBLE LAUNCH line. One copy here, so a change to the flood's job
naming or to the strays/proc queries can never leave one nightly gate judging
stale SQL.
"""
import re, subprocess, urllib.request
import farm_spec as spec

TOKEN = "simmigrate"
PSQL = spec.psql_cmd()


def q(sql):
    """Result lines, [] for an empty result, None when the query FAILED --
    callers judging absence (strays) must not mistake a sampling failure for
    an empty farm."""
    try:
        r = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                           timeout=15)
        if r.returncode != 0:
            return None
        return r.stdout.strip().splitlines()
    except Exception:
        return None


def counts_by_show():
    """{show: [running, succeeded, dead, waiting]} for the flood jobs."""
    out = {}
    for r in (q("SELECT s.str_name,"
               " sum(CASE WHEN f.str_state='RUNNING' THEN 1 ELSE 0 END),"
               " sum(CASE WHEN f.str_state='SUCCEEDED' THEN 1 ELSE 0 END),"
               " sum(CASE WHEN f.str_state='DEAD' THEN 1 ELSE 0 END),"
               " sum(CASE WHEN f.str_state='WAITING' THEN 1 ELSE 0 END)"
               " FROM frame f JOIN job j ON j.pk_job=f.pk_job"
               " JOIN show s ON s.pk_show=j.pk_show"
                f" WHERE j.str_name LIKE '%{TOKEN}%' GROUP BY s.str_name;") or []):
        name, running, done, dead, wait = r.split("|")
        out[name] = [int(running), int(done), int(dead), int(wait)]
    return out


def strays():
    """Run identities out of step: the pk of every proc whose frame is gone or
    not RUNNING, and of every RUNNING flood frame that has no proc. None when
    sampling failed (the watchers keep their existing ages rather than
    restarting every stray's orphan clock on an empty answer)."""
    procs = q("SELECT p.pk_proc FROM proc p LEFT JOIN frame f ON f.pk_frame=p.pk_frame"
              " WHERE f.pk_frame IS NULL OR f.str_state<>'RUNNING';")
    frames = q("SELECT f.pk_frame FROM frame f JOIN job j ON j.pk_job=f.pk_job"
               " LEFT JOIN proc p ON p.pk_frame=f.pk_frame"
               f" WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='RUNNING'"
               " AND p.pk_proc IS NULL;")
    if procs is None or frames is None:
        return None
    return set(procs) | set(frames)


def util():
    rows = q("SELECT round(100.0 * sum(int_cores - int_cores_idle) / sum(int_cores), 1)"
             " FROM host;") or []
    return float(rows[0]) if rows and rows[0].strip() else 0.0


def parse_show_counter(body, counter):
    """{show: n} summed from a Prometheus counter family with a show label."""
    out = {}
    if body:
        for m in re.finditer(
                counter + r'\{[^}]*show="([^"]+)"[^}]*\}\s+([0-9.eE+]+)', body):
            out[m.group(1)] = out.get(m.group(1), 0) + int(float(m.group(2)))
    return out


def maestro_booked_from(url):
    """{show: frames} from Maestro's own dispatch counter at url; {} while it
    is not up."""
    try:
        body = urllib.request.urlopen(url, timeout=10).read().decode()
    except Exception:
        return {}
    return parse_show_counter(body, "cue_maestro_frames_dispatched_total")


def double_launches(rqd_log):
    if not rqd_log:
        return 0
    try:
        return sum(1 for l in open(rqd_log, errors="ignore") if "DOUBLE LAUNCH" in l)
    except Exception:
        return 0
