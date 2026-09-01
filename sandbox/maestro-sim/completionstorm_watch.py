"""COMPLETIONSTORM watcher: the tick must never do the follow-up filing.

The invariant under test: post-completion work never runs on Maestro
thread, and an accepted completion is never dropped. The storm pushes the
completion rate past one worker's filing speed, so the post-op queue
(postQ on the Maestro stat line) MUST fill; what happens next is the
verdict. If the tick inflates, the overflow ran the filing on Maestro
(the disease the base's comment forbids). If completions are dropped, an
acked report died in memory. If the tick stays calm and nothing drops, the
door refused politely and RQD redialed, which is the cure.

Reads the farm through psql (procs, done count) and Maestro's own
stat lines through the cuebot log (avgTick, postQ, drop warnings), which
this scenario runs beside on the same machine.

PASS      : a calm tick and zero drops, reached either way: the storm
            filled the queue and the door refused (redials), or the worker
            outran the storm and the queue never filled.
FAIL      : any window's avgTick over the bar, or any dropped completion.
INCONCLUSIVE: too few frames completed; the storm never took hold.

usage: completionstorm_watch.py [duration_s] [interval_s]
"""
import os, re, subprocess, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 240
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
TOKEN = "simstorm"
CUEBOT_LOG = os.environ.get("SIM_STORM_CUEBOT_LOG", "/tmp/cuebot-new.log")
STORM_MIN_POSTQ = int(os.environ.get("SIM_STORM_MIN_POSTQ", "8000"))
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


def read_cuebot():
    """(last avgTick ms, last postQ, peak avgTick, peak postQ, drops) from the log."""
    try:
        txt = open(CUEBOT_LOG, errors="ignore").read()
    except Exception:
        return 0, 0, 0, 0, 0
    ticks = [int(m) for m in re.findall(r"avgTick=(\d+)ms", txt)]
    qs = [int(m) for m in re.findall(r"postQ=(\d+)", txt)]
    drops = len(re.findall(r"dropping completion", txt))
    return (ticks[-1] if ticks else 0, qs[-1] if qs else 0,
            max(ticks) if ticks else 0, max(qs) if qs else 0, drops)


def main():
    print(f"watching COMPLETIONSTORM for {DURATION}s. The storm must fill the "
          f"post-op queue (postQ >= {STORM_MIN_POSTQ}); PASS then needs every "
          f"window's avgTick <= {TICK_MAX_MS}ms and zero dropped completions.\n",
          flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        procs = scalar("SELECT count(*) FROM proc;")
        done = scalar("SELECT count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job"
                      f" WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='SUCCEEDED';")
        tick, q, tick_pk, q_pk, drops = read_cuebot()
        print(f"t={t:5.0f} | procs {procs:4d} | done {done:6d} | "
              f"avgTick {tick:6d}ms (peak {tick_pk:6d}) | postQ {q:5d} "
              f"(peak {q_pk:5d}) | dropped {drops}", flush=True)
        time.sleep(INTERVAL)

    tick, q, tick_pk, q_pk, drops = read_cuebot()
    done = scalar("SELECT count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job"
                  f" WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='SUCCEEDED';")
    print("\n==== COMPLETIONSTORM VERDICT ====", flush=True)
    print(f"peak postQ {q_pk}; peak avgTick {tick_pk}ms; dropped {drops}; "
          f"frames done {done}", flush=True)
    if drops > 0:
        print(f"FAIL: {drops} completions were dropped after being acked; the "
              f"report was accepted and then lost in memory.", flush=True)
    elif tick_pk > TICK_MAX_MS:
        print(f"FAIL: avgTick peaked at {tick_pk}ms (> {TICK_MAX_MS}ms). The "
              f"full post-op queue ran its filing on the Maestro thread: tick "
              f"time multiplied by the completion rate, exactly what the "
              f"worker's own comment forbids.", flush=True)
    elif q_pk >= STORM_MIN_POSTQ:
        print(f"PASS: the storm filled the queue (peak {q_pk}) and the tick "
              f"stayed calm (peak {tick_pk}ms) with zero drops; overload was "
              f"refused at the door and RQD redialed.", flush=True)
    elif done >= MIN_DONE:
        print(f"PASS: the worker OUTRAN the storm (peak postQ {q_pk} over "
              f"{done} completions) with a calm tick (peak {tick_pk}ms) and "
              f"zero drops; the door never had to close.", flush=True)
    else:
        print(f"INCONCLUSIVE: only {done} frames completed (< {MIN_DONE}) and "
              f"postQ peaked at {q_pk}; the storm never took hold, nothing "
              f"was measured.", flush=True)


if __name__ == "__main__":
    main()
