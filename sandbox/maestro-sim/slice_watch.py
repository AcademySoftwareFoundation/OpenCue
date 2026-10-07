"""SLICE watcher: a slice delivers what Maestro accounted.

Samples the running frames per large host twice a second and records each
host's first delivery: the running count right after its first placement
tick. Maestro sizes a first slice on an idle 128-core host at
frame_query_max (20) frames for a one-core layer with a deep backlog (the
per-host share is 32), and charges the host for 20. The invariant: the
delivered slice equals the accounted slice, so the first delivery on every
large host is 20 frames.

PASS      : every large host's first delivery is at least SLICE frames.
FAIL      : the disease. A first delivery below SLICE on a host that had the
            room: the plan read cut the slice Maestro accounted, so the
            host carries phantom reservation and the rest waits a tick.
INCONCLUSIVE: no large host booked anything.

usage: slice_watch.py [duration_s]
"""
import os, subprocess, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 60
SLICE = int(os.environ.get("SIM_SLICE_EXPECT", "20"))
TOKEN = "simslice"
PSQL = spec.psql_cmd()


def q(sql):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip().splitlines()
    except Exception:
        return []


def running_by_host():
    out = {}
    for r in q("SELECT h.str_name, count(p.pk_proc) FROM host h LEFT JOIN proc p"
               " ON p.pk_host=h.pk_host WHERE h.str_name LIKE 'large%' GROUP BY 1 ORDER BY 1;"):
        name, n = r.split("|")
        out[name] = int(n)
    return out


def main():
    print(f"watching SLICE for {DURATION}s: the first delivery on every large host must be "
          f"at least {SLICE} frames (frame_query_max), the slice Maestro accounted.\n",
          flush=True)
    t0 = time.time()
    first = {}
    last = {}
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        now = running_by_host()
        for h, n in now.items():
            if n > 0 and h not in first:
                first[h] = n
                print(f"t={t:5.1f} | {h}: first delivery {n} frames", flush=True)
            elif n != last.get(h):
                print(f"t={t:5.1f} | {h}: running {n}", flush=True)
        last = now
        time.sleep(0.5)

    print("\n==== SLICE VERDICT ====", flush=True)
    print("first deliveries: " + ", ".join(f"{h} {n}" for h, n in sorted(first.items())),
          flush=True)
    if not first:
        print("INCONCLUSIVE: no large host booked anything.", flush=True)
        return
    short = {h: n for h, n in first.items() if n < SLICE}
    if short:
        print(f"FAIL: {len(short)} of {len(first)} large hosts got a first slice below "
              f"{SLICE} frames (" + ", ".join(f"{h} {n}" for h, n in sorted(short.items()))
              + "). The plan read cut the slice Maestro accounted.", flush=True)
    else:
        print(f"PASS: every large host's first slice delivered at least {SLICE} frames, "
              f"the size Maestro accounted.", flush=True)


if __name__ == "__main__":
    main()
