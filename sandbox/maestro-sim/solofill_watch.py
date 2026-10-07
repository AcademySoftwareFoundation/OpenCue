"""SOLOFILL verdict: a layer's fill must not depend on the layer count.

Companion to inject_solofill.py. Job A (one layer) and job B (many layers,
equal total frames) start together on an idle farm with room for both. At
the mark (default 120 s) the watcher compares their running frames. The
mark sits well past the first tick of a cold fill, which on a small box
spends tens of seconds committing thousands of frames, and past the
ingestion of the many-layer job, so both jobs have had their turn. Equal shapes, equal priority, equal backlog: the only
difference is how many layers carry the frames, so the ratio A/B measures
how much of a layer's fill rate is a per-tick allowance instead of capacity.

  - PASS: at the mark A holds at least RATIO_MIN of B's running frames (or A
    has no frames left to book).
  - FAIL: A is still holding a backlog while B has run ahead by more than
    1/RATIO_MIN: Maestro hands each layer a per-tick allowance, so a
    job's fill rate scales with its layer count.
  - INCONCLUSIVE: the farm never booked enough of B to judge.

usage: solofill_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
MARK_S = int(os.environ.get("SIM_SOLOFILL_MARK_S", "120"))
RATIO_MIN = float(os.environ.get("SIM_SOLOFILL_RATIO_MIN", "0.5"))
MIN_B = int(os.environ.get("SIM_SOLOFILL_MIN_B", "1000"))
MIN_BACKLOG = 1000
PSQL = spec.psql_cmd()


def scalar(sql):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return int(out) if out.lstrip("-").isdigit() else 0
    except Exception:
        return 0


def running(token):
    return scalar("SELECT count(*) FROM proc p JOIN job j ON j.pk_job = p.pk_job "
                  f"WHERE j.str_name LIKE '%{token}%';")


def hosts(token):
    return scalar("SELECT count(DISTINCT p.pk_host) FROM proc p JOIN job j ON "
                  f"j.pk_job = p.pk_job WHERE j.str_name LIKE '%{token}%';")


def waiting(token):
    return scalar("SELECT count(*) FROM frame f JOIN job j ON j.pk_job = f.pk_job "
                  f"WHERE j.str_name LIKE '%{token}%' AND f.str_state = 'WAITING';")


def main():
    print(f"watching SOLOFILL for {DURATION}s: one-layer job A vs many-layer job B "
          f"of equal frames on an idle farm; at t={MARK_S}s A must hold at least "
          f"{RATIO_MIN:.0%} of B's running frames.\n", flush=True)
    t0 = time.time()
    mark = None
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        a, b = running("simsolo"), running("simmany")
        ha, wa = hosts("simsolo"), waiting("simsolo")
        ratio = (a / b) if b else 0.0
        print(f"t={t:5.0f} | A running {a:6d} on {ha:5d} hosts (waiting {wa:6d}) | "
              f"B running {b:6d} | A/B {ratio:5.2f}", flush=True)
        if mark is None and t >= MARK_S:
            mark = (a, b, wa, ha)
        time.sleep(INTERVAL)

    if mark is None:
        mark = (running("simsolo"), running("simmany"), waiting("simsolo"),
                hosts("simsolo"))
    a, b, wa, ha = mark
    ratio = (a / b) if b else 0.0
    print("\n==== SOLOFILL VERDICT ====", flush=True)
    print(f"at the mark: A {a} running on {ha} hosts with {wa} waiting; B {b} "
          f"running; ratio A/B {ratio:.3f}", flush=True)
    if b < MIN_B:
        print(f"INCONCLUSIVE: B only reached {b} running frames (< {MIN_B}); the "
              f"farm never booked enough to judge.", flush=True)
    elif ratio >= RATIO_MIN or wa < MIN_BACKLOG:
        print(f"PASS: the one-layer job kept pace (A/B {ratio:.2f}); a layer's "
              f"fill is bounded by capacity, not by a per-tick allowance.",
              flush=True)
    else:
        print(f"FAIL: with {wa} frames still waiting, the one-layer job held "
              f"{a} running frames against {b} for the many-layer job (A/B "
              f"{ratio:.2f}); each layer gets a per-tick allowance, so a job's "
              f"fill rate scales with its layer count.", flush=True)


if __name__ == "__main__":
    main()
