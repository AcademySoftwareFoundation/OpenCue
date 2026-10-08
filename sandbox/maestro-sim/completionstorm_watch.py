"""COMPLETIONSTORM watcher: the tick must never do the follow-up filing,
and a completion that reached cuebot is never refused or lost.
The storm pushes the completion rate past one worker's filing speed, so
the post-op queue (postQ on the Maestro stat line) grows; what happens
next is the verdict. If the tick inflates, the filing ran on the Maestro
thread. If the fake RQD counts a lost report, cuebot refused or dropped a
completion past the RQD channel's four attempts, and that frame's proc
stays booked until maintenance reclaims it. If the tick stays calm and
nothing is lost, the queue absorbed the storm and the worker drained it.
Reads the farm through psql (procs, done count), Maestro's own stat lines
through the cuebot log (avgTick, postQ) and the fake RQD's stats line
(lost reports, retries), all beside this scenario on the same machine.
The injector pauses its jobs DRAIN_S before the window ends, so the last
postQ sample is taken after the storm: a worker that kept up shows zero.
PASS      : the tick stayed calm, no report was lost, and the backlog was
            empty at the end, over enough completions for the storm to
            have taken hold.
FAIL      : any window's avgTick over the bar, any lost report, or a
            backlog still there at the end.
INCONCLUSIVE: too few frames completed for the storm to have taken hold.
usage: completionstorm_watch.py [duration_s] [interval_s] [drain_s]
"""
import os, re, subprocess, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 240
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
DRAIN_S = int(sys.argv[3]) if len(sys.argv) > 3 else 45
TOKEN = "simstorm"
CUEBOT_LOG = os.environ.get("SIM_STORM_CUEBOT_LOG", "/tmp/cuebot-new.log")
RQD_LOG = os.environ.get("SIM_STORM_RQD_LOG", os.path.join(_HERE, "rqd.log"))
TICK_MAX_MS = int(os.environ.get("SIM_STORM_TICK_MAX_MS", "5000"))
MIN_DONE = int(os.environ.get("SIM_STORM_MIN_DONE", "20000"))
PSQL = spec.psql_cmd()


def scalar(sql):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return int(out) if out.lstrip("-").isdigit() else 0
    except Exception:
        return 0


def read_rqd_lost():
    """Lost reports from the fake RQD's last stats line: completions refused or
    unreachable past the RQD channel's four attempts, never sent again."""
    try:
        txt = open(RQD_LOG, errors="ignore").read()
    except Exception:
        return 0
    lost = re.findall(r"failed=(\d+)", txt)
    return int(lost[-1]) if lost else 0


def read_cuebot():
    """(last avgTick ms, last postQ, peak avgTick, lost) from the logs."""
    try:
        txt = open(CUEBOT_LOG, errors="ignore").read()
    except Exception:
        return 0, 0, 0, read_rqd_lost()
    ticks = [int(m) for m in re.findall(r"avgTick=(\d+)ms", txt)]
    qs = [int(m) for m in re.findall(r"postQ=(\d+)", txt)]
    return (ticks[-1] if ticks else 0, qs[-1] if qs else 0,
            max(ticks) if ticks else 0, read_rqd_lost())


def main():
    print(f"watching COMPLETIONSTORM for {DURATION}s. PASS needs every window's "
          f"avgTick <= {TICK_MAX_MS}ms, zero lost reports and an empty backlog "
          f"at the end, {DRAIN_S}s after the storm's jobs pause, over at least "
          f"{MIN_DONE} completions.\n",
          flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        procs = scalar("SELECT count(*) FROM proc;")
        done = scalar("SELECT count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job"
                      f" WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='SUCCEEDED';")
        tick, q, tick_pk, drops = read_cuebot()
        print(f"t={t:5.0f} | procs {procs:4d} | done {done:6d} | "
              f"avgTick {tick:6d}ms (peak {tick_pk:6d}) | postQ {q:5d} | "
              f"lost {drops}", flush=True)
        time.sleep(INTERVAL)

    tick, q, tick_pk, drops = read_cuebot()
    done = scalar("SELECT count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job"
                  f" WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='SUCCEEDED';")
    print("\n==== COMPLETIONSTORM VERDICT ====", flush=True)
    print(f"final postQ {q}; peak avgTick {tick_pk}ms; "
          f"lost {drops}; frames done {done}", flush=True)
    if drops > 0:
        print(f"FAIL: the fake RQD lost {drops} completion reports: refused or "
              f"unreachable past the RQD channel's four attempts, so those "
              f"frames' procs stay booked until maintenance reclaims them.",
              flush=True)
    elif tick_pk > TICK_MAX_MS:
        print(f"FAIL: avgTick peaked at {tick_pk}ms (> {TICK_MAX_MS}ms). The "
              f"full post-op queue ran its filing on the Maestro thread: tick "
              f"time multiplied by the completion rate, exactly what the "
              f"worker's own comment forbids.", flush=True)
    elif q > 0:
        print(f"FAIL: the backlog did not drain: postQ still {q} at the end, "
              f"{DRAIN_S}s after the storm's jobs paused; the worker fell "
              f"behind the storm for good.", flush=True)
    elif done >= MIN_DONE:
        print(f"PASS: the tick stayed calm (peak {tick_pk}ms) over {done} "
              f"completions with zero lost reports, and the worker drained "
              f"the backlog to zero.", flush=True)
    else:
        print(f"INCONCLUSIVE: only {done} frames completed (< {MIN_DONE}); "
              f"the storm never took hold, nothing was measured.", flush=True)


if __name__ == "__main__":
    main()
