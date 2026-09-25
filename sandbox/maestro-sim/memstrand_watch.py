"""MEMSTRAND watcher: the dashboard reports the cores memory strands.

Each sample reads the truth from the database, the idle cores each host's
idle memory cannot feed at the farm's memory-per-core, and the one stranded
gauge cuebot publishes on /metrics, cue_farm_health_stranded_cores, by cause:

  memory   idle cores no memory is left to feed, whatever is waiting
  fit      the rest no waiting frame fits (here: none expected)

The verdict reads the last WINDOW_S seconds, once the flood filled memory.

PASS      : the gauge's total and its memory cause are within TOLERANCE of
            the truth (a light layer waits that fits every host, which the old
            count took for proof the whole host was usable).
FAIL      : the gauge is missing, unsplit, or reads far from the truth.
INCONCLUSIVE: the flood never stranded MIN_TRUTH cores.

usage: memstrand_watch.py [duration_s] [interval_s]
"""
import os, re, subprocess, sys, time, urllib.request
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 240
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
METRICS = os.environ.get("SIM_METRICS_URL", "http://localhost:8080/metrics")
WINDOW_S = 60.0
TOLERANCE = 0.10
MIN_TRUTH = 100
PSQL = spec.psql_cmd()


def rows(sql):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True, timeout=15)
        return [r.split("|") for r in out.stdout.strip().splitlines() if r]
    except Exception:
        return []


def truth():
    hosts = [(int(c), int(m), int(ci), int(mi)) for c, m, ci, mi in
             rows("SELECT int_cores, int_mem, int_cores_idle, int_mem_idle FROM host;")]
    whole = sum(c for c, _, _, _ in hosts) // 100
    per_core = sum(m for _, m, _, _ in hosts) // whole if whole else 0
    if not per_core:
        return 0
    return sum(max(0, ci // 100 - mi // per_core) for _, _, ci, mi in hosts if ci >= 10)


def gauge(text, name, cause=None):
    sel = rf'[^}}]*cause="{cause}"[^}}]*' if cause else r"[^}]*"
    m = re.findall(rf"^{name}\{{{sel}\}} ([0-9.eE+-]+)", text, re.M)
    return sum(float(v) for v in m) if m else None


def main():
    print(f"watching MEMSTRAND for {DURATION}s.\n", flush=True)
    t0 = time.time()
    samples = []                      # (t, truth, memory gauge, demand gauge)
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        try:
            text = urllib.request.urlopen(METRICS, timeout=5).read().decode()
        except Exception:
            text = ""
        tr = truth()
        mg = gauge(text, "cue_farm_health_stranded_cores", "memory")
        dg = gauge(text, "cue_farm_health_stranded_cores")
        samples.append((t, tr, mg, dg))
        print(f"t={t:5.0f} | truth {tr:5d} | gauge total {dg if dg is not None else '-':>6} | "
              f"memory {mg if mg is not None else '-':>6}", flush=True)
        time.sleep(INTERVAL)

    win = [s for s in samples if s[0] >= DURATION - WINDOW_S]
    print("\n==== MEMSTRAND VERDICT ====", flush=True)
    if not win or max(s[1] for s in win) < MIN_TRUTH:
        print(f"INCONCLUSIVE: the flood never stranded {MIN_TRUTH} cores.", flush=True)
        return
    tr = sum(s[1] for s in win) / len(win)
    mg = [s[2] for s in win if s[2] is not None]
    dg = [s[3] for s in win if s[3] is not None]
    mgm = sum(mg) / len(mg) if mg else None
    dgm = sum(dg) / len(dg) if dg else None
    err = abs(dgm - tr) / tr if dgm is not None else None
    print(f"last {WINDOW_S:.0f}s: truth {tr:.0f} cores, gauge total "
          f"{'missing' if dgm is None else f'{dgm:.0f}'} (memory "
          f"{'missing' if mgm is None else f'{mgm:.0f}'}); error "
          f"{'-' if err is None else f'{err:.0%}'}", flush=True)
    fails = []
    if dgm is None or err > TOLERANCE:
        fails.append(f"the stranded gauge reads {dgm if dgm is not None else 'nothing'} while "
                     f"{tr:.0f} cores are stranded: a host counts as sellable when any waiting "
                     f"layer fits one frame")
    if mgm is None or abs(mgm - tr) / tr > TOLERANCE:
        fails.append("the gauge does not attribute the stranding to memory")
    for f in fails:
        print("FAIL: " + f, flush=True)
    if not fails:
        print(f"PASS: the stranded gauge reports {dgm:.0f} of {tr:.0f} cores, "
              f"{mgm:.0f} of them by memory.", flush=True)


if __name__ == "__main__":
    main()
