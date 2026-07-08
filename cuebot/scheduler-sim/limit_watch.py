"""LIMIT (license-cap) verdict: did concurrency ever exceed the limit's cap?

Companion to inject_limit.py. Samples, over the run, the number of frames of the
limited layers that are RUNNING at once and tracks the peak. The limit is global
(int_max_value = N), so a correct scheduler holds this at <= N no matter how deep
the backlog is.

  - PASS: peak concurrent running <= N AND the backlog clearly wanted more than N
    (so the cap, not a lack of work, held it down). The scheduler enforces the
    limit.
  - INCONCLUSIVE: the backlog never exceeded N (nothing to cap) -- raise the load.
  - FAIL: peak concurrent running > N -- the scheduler ignored the limit and ran
    more frames than the license cap allows.

usage: limit_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_metrics

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
PSQL = spec.psql_cmd()
LIMIT_NAME = os.environ.get("SIM_LIMIT_NAME", "simlic")
CSV = os.environ.get("SIM_LIMIT_CSV", "")


def _scalar(sql, default=0):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return int(out) if out.lstrip("-").isdigit() else default
    except Exception:
        return default


def cap():
    return _scalar(f"SELECT int_max_value FROM limit_record WHERE str_name='{LIMIT_NAME}';", -1)


def _limited_frames(state):
    """Frames in `state` whose layer carries the limit -- the ground-truth
    concurrency the cap governs (one running frame == one license unit)."""
    return _scalar(
        f"SELECT count(*) FROM frame f "
        f"JOIN layer_limit ll ON ll.pk_layer = f.pk_layer "
        f"JOIN limit_record lr ON lr.pk_limit_record = ll.pk_limit_record "
        f"WHERE lr.str_name='{LIMIT_NAME}' AND f.str_state='{state}';")


def main():
    N = cap()
    print(f"watching LIMIT '{LIMIT_NAME}' (cap {N}) for {DURATION}s: concurrent "
          f"running frames must stay <= cap.\n", flush=True)
    t0 = time.time()
    peak_running = 0
    peak_waiting = 0
    rows = []
    while time.time() - t0 < DURATION:
        c = cap()                    # re-read: the injector may create it just after t=0
        if c >= 0:
            N = c
        run = _limited_frames("RUNNING")
        wait = _limited_frames("WAITING")
        util, _ = sim_metrics.farm_state()
        peak_running = max(peak_running, run)
        peak_waiting = max(peak_waiting, wait)
        t = time.time() - t0
        rows.append((t, run, wait, util))
        flag = "  <-- OVER CAP" if N >= 0 and run > N else ""
        print(f"t={t:5.0f} | util {util:5.1f}% | running {run:5d} / cap {N} "
              f"| waiting {wait:6d}{flag}", flush=True)
        time.sleep(INTERVAL)

    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("t,running,waiting,util,cap\n")
                for (t, run, wait, util) in rows:
                    f.write(f"{t:.0f},{run},{wait},{util:.1f},{N}\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    print("\n==== LIMIT VERDICT ====", flush=True)
    print(f"limit '{LIMIT_NAME}' cap={N}  peak concurrent running={peak_running}  "
          f"peak waiting backlog={peak_waiting}", flush=True)
    if N < 0:
        print("INCONCLUSIVE: no limit_record found -- injector did not create it.", flush=True)
    elif peak_waiting <= N:
        print(f"INCONCLUSIVE: backlog never exceeded the cap (peak waiting "
              f"{peak_waiting} <= {N}); nothing to cap. Raise the load.", flush=True)
    elif peak_running > N:
        print(f"FAIL: concurrent running peaked at {peak_running}, OVER the cap of "
              f"{N} -- the scheduler ignored the limit (ran more than the licenses "
              f"allow).", flush=True)
    else:
        print(f"PASS: concurrent running peaked at {peak_running} <= cap {N} while "
              f"{peak_waiting} frames waited -- the scheduler held the limit.", flush=True)


if __name__ == "__main__":
    main()
