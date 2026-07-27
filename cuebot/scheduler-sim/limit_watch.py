"""LIMIT (license-cap) verdict: did concurrency ever exceed the limit's cap?

Companion to inject_limit.py. Two modes, selected by SIM_LIMIT_HOST (must match
the injector's):

GLOBAL (default): samples the number of frames of the limited layers RUNNING at
once and tracks the peak; a correct scheduler holds it at <= N (int_max_value).
  - PASS: peak concurrent running <= N AND the backlog clearly wanted more than N.
  - INCONCLUSIVE: the backlog never exceeded N (nothing to cap) -- raise the load.
  - FAIL: peak concurrent running > N.

PER-HOST / floating license (SIM_LIMIT_HOST=1, b_host_limit=true): N counts
DISTINCT HOSTS ("seats"), every frame on a seated host shares its seat. Samples
distinct hosts running the limit's layers AND the running-frame count:
  - PASS: peak distinct hosts <= N AND peak running >= 10*N (seats really are
    shared -- frames blow past the seat count) AND a deep backlog waited.
  - INCONCLUSIVE: backlog too shallow to prove anything -- raise the load.
  - FAIL: peak distinct hosts > N (seat cap violated), OR running never cleared
    10*N under a deep backlog (seats not shared: the gate is over-strict).

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
HOST_MODE = os.environ.get("SIM_LIMIT_HOST", "0") == "1"


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


def _limited_hosts():
    """Distinct hosts holding a seat: >=1 proc of the limit's layers. Counted
    from proc, the same view the scheduler's seat accounting uses, so the
    verdict measures exactly what the enforcement enforces."""
    return _scalar(
        f"SELECT count(DISTINCT p.pk_host) FROM proc p "
        f"JOIN layer_limit ll ON ll.pk_layer = p.pk_layer "
        f"JOIN limit_record lr ON lr.pk_limit_record = ll.pk_limit_record "
        f"WHERE lr.str_name='{LIMIT_NAME}';")


def main():
    N = cap()
    what = ("distinct hosts (seats) must stay <= cap while frames share seats"
            if HOST_MODE else "concurrent running frames must stay <= cap")
    print(f"watching LIMIT '{LIMIT_NAME}' (cap {N}"
          f"{' hosts' if HOST_MODE else ''}) for {DURATION}s: {what}.\n", flush=True)
    t0 = time.time()
    peak_running = 0
    peak_waiting = 0
    peak_hosts = 0
    rows = []
    while time.time() - t0 < DURATION:
        c = cap()                    # re-read: the injector may create it just after t=0
        if c >= 0:
            N = c
        run = _limited_frames("RUNNING")
        wait = _limited_frames("WAITING")
        hosts = _limited_hosts() if HOST_MODE else 0
        util, _ = sim_metrics.farm_state()
        peak_running = max(peak_running, run)
        peak_waiting = max(peak_waiting, wait)
        peak_hosts = max(peak_hosts, hosts)
        t = time.time() - t0
        rows.append((t, run, wait, util, hosts))
        if HOST_MODE:
            flag = "  <-- OVER CAP" if N >= 0 and hosts > N else ""
            print(f"t={t:5.0f} | util {util:5.1f}% | hosts {hosts:3d} / cap {N} "
                  f"| running {run:5d} | waiting {wait:6d}{flag}", flush=True)
        else:
            flag = "  <-- OVER CAP" if N >= 0 and run > N else ""
            print(f"t={t:5.0f} | util {util:5.1f}% | running {run:5d} / cap {N} "
                  f"| waiting {wait:6d}{flag}", flush=True)
        time.sleep(INTERVAL)

    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("t,running,waiting,util,cap,hosts\n")
                for (t, run, wait, util, hosts) in rows:
                    f.write(f"{t:.0f},{run},{wait},{util:.1f},{N},{hosts}\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    print("\n==== LIMIT VERDICT ====", flush=True)
    if HOST_MODE:
        print(f"limit '{LIMIT_NAME}' host-cap={N}  peak distinct hosts={peak_hosts}  "
              f"peak concurrent running={peak_running}  "
              f"peak waiting backlog={peak_waiting}", flush=True)
        if N < 0:
            print("INCONCLUSIVE: no limit_record found -- injector did not create it.",
                  flush=True)
        elif peak_waiting < 1000:
            print(f"INCONCLUSIVE: backlog too shallow (peak waiting {peak_waiting} "
                  f"< 1000) to prove the cap or seat sharing. Raise the load.", flush=True)
        elif peak_hosts > N:
            print(f"FAIL: distinct hosts peaked at {peak_hosts}, OVER the cap of {N} "
                  f"-- the scheduler opened more seats than the floating licenses "
                  f"allow.", flush=True)
        elif peak_running < 10 * N:
            print(f"FAIL: running frames peaked at only {peak_running} (< 10x cap "
                  f"{N}) under a deep backlog -- seats are not being shared (the "
                  f"per-host gate is over-strict or seated hosts are not filling).",
                  flush=True)
        else:
            print(f"PASS: distinct hosts peaked at {peak_hosts} <= cap {N} while "
                  f"running peaked at {peak_running} (>= 10x cap, seats shared) and "
                  f"{peak_waiting} frames waited -- the scheduler held the per-host "
                  f"limit.", flush=True)
        return

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
