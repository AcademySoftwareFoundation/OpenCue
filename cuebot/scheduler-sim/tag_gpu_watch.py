"""TAGS_GPU verdict: tag confinement + GPU placement + GPU memory accounting.

Companion to `simulate.py --tag-gpu-test` (normally driven by --verify). The
farm is fragmented two ways at once -- N random capability tags (`--tags`,
farm_spec cap{i} pools) and a GPU slice (`--gpu`: only some hosts have GPUs,
some layers need one) -- and the watcher asserts cuebot never violates either
constraint while the fragmented farm still serves every pool:

  INVARIANTS (sampled continuously; one hit = FAIL):
    - TAG: no proc on a host whose tags don't match its layer's tag pattern
      (the same `host.str_tags ~* '(?x)'||layer.str_tags||'\\y'` predicate
      cuebot's dispatch query uses).
    - GPU HOST: no proc of a GPU layer (int_gpus_min > 0) on a host with no
      GPUs.
    - GPU ACCOUNTING: no host oversubscribed on GPUs or GPU memory
      (SUM(proc.int_gpus_reserved) <= host.int_gpus, same for gpu_mem), and
      no host with negative int_gpus_idle / int_gpu_mem_idle.

  COVERAGE (floors, so the verdict can't pass vacuously):
    - peak concurrent GPU procs >= SIM_TAGGPU_MIN_GPU (default 50);
    - every tag pool ran work: distinct tags seen running >= SIM_NTAGS.

usage: tag_gpu_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
PSQL = spec.psql_cmd()
NTAGS = int(os.environ.get("SIM_NTAGS", "0") or "0")
MIN_GPU = int(os.environ.get("SIM_TAGGPU_MIN_GPU", "50"))
# GPU utilization floor (percent of GPU UNITS on GPU-capable hosts only --
# most of the farm has no GPUs and must not dilute the denominator).
# Calibrated: the full-farm scenario measures ~75% peak.
MIN_UTIL = float(os.environ.get("SIM_TAGGPU_MIN_UTIL", "40"))
CSV = os.environ.get("SIM_TAGGPU_CSV", "")


def _scalar(sql, default=0):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return int(out) if out.lstrip("-").isdigit() else default
    except Exception:
        return default


def tag_violations():
    return _scalar(
        "SELECT count(*) FROM proc p "
        "JOIN layer l ON l.pk_layer = p.pk_layer "
        "JOIN host h ON h.pk_host = p.pk_host "
        "WHERE l.str_tags IS NOT NULL AND l.str_tags <> '' "
        "AND NOT (h.str_tags ~* ('(?x)' || l.str_tags || '\\y'));")


def gpu_host_violations():
    return _scalar(
        "SELECT count(*) FROM proc p "
        "JOIN layer l ON l.pk_layer = p.pk_layer "
        "JOIN host h ON h.pk_host = p.pk_host "
        "WHERE l.int_gpus_min > 0 AND h.int_gpus = 0;")


def gpu_oversub_hosts():
    return _scalar(
        "SELECT count(*) FROM ("
        "  SELECT p.pk_host, SUM(p.int_gpus_reserved) sg, "
        "         SUM(p.int_gpu_mem_reserved) sm, "
        "         max(h.int_gpus) g, max(h.int_gpu_mem) m "
        "  FROM proc p JOIN host h ON h.pk_host = p.pk_host "
        "  GROUP BY p.pk_host) x "
        "WHERE x.sg > x.g OR x.sm > x.m;")


def negative_idle_hosts():
    return _scalar("SELECT count(*) FROM host "
                   "WHERE int_gpus_idle < 0 OR int_gpu_mem_idle < 0;")


def gpu_running():
    return _scalar("SELECT count(*) FROM proc p "
                   "JOIN layer l ON l.pk_layer = p.pk_layer "
                   "WHERE l.int_gpus_min > 0;")


def tags_running():
    return _scalar("SELECT count(DISTINCT l.str_tags) FROM proc p "
                   "JOIN layer l ON l.pk_layer = p.pk_layer "
                   "WHERE l.str_tags LIKE 'cap%';")


def gpu_utilization():
    """(gpu_unit_util_pct, gpu_mem_util_pct) over GPU-CAPABLE hosts only --
    most of the farm has no GPUs and must not dilute the denominator."""
    try:
        out = subprocess.run(PSQL + ["-c",
            "SELECT COALESCE(SUM(int_gpus),0), COALESCE(SUM(int_gpus_idle),0), "
            "COALESCE(SUM(int_gpu_mem),0), COALESCE(SUM(int_gpu_mem_idle),0) "
            "FROM host WHERE int_gpus > 0;"],
            capture_output=True, text=True, timeout=15).stdout.strip()
        g, gi, m, mi = [float(x) for x in out.split("|")]
        return ((100.0 * (g - gi) / g) if g else 0.0,
                (100.0 * (m - mi) / m) if m else 0.0)
    except Exception:
        return (0.0, 0.0)


def main():
    print(f"watching TAGS_GPU for {DURATION}s: tag + GPU placement must never "
          f"violate, GPU mem never oversubscribed; floors gpu>={MIN_GPU}, "
          f"tags=={NTAGS}.\n", flush=True)
    t0 = time.time()
    viol_samples = 0
    peak_gpu = 0
    peak_tags = 0
    peak_util = 0.0
    peak_mem_util = 0.0
    rows_out = []
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        tv = tag_violations()
        gv = gpu_host_violations()
        ov = gpu_oversub_hosts()
        nv = negative_idle_hosts()
        g = gpu_running()
        tr = tags_running()
        gu, gmu = gpu_utilization()
        peak_gpu = max(peak_gpu, g)
        peak_tags = max(peak_tags, tr)
        peak_util = max(peak_util, gu)
        peak_mem_util = max(peak_mem_util, gmu)
        bad = tv + gv + ov + nv
        if bad > 0:
            viol_samples += 1
        flag = "  <-- VIOLATION" if bad > 0 else ""
        print(f"t={t:5.0f} | tagViol {tv:3d} gpuHostViol {gv:3d} overSub {ov:3d} "
              f"negIdle {nv:3d} | gpu running {g:5d} util {gu:5.1f}% mem {gmu:5.1f}% "
              f"| tags active {tr:2d}/{NTAGS}{flag}", flush=True)
        rows_out.append((t, g, gu, gmu, tr))
        time.sleep(INTERVAL)

    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("t,gpu_procs,gpu_util,gpu_mem_util,tags_active\n")
                for (t, g, gu, gmu, tr) in rows_out:
                    f.write(f"{t:.0f},{g},{gu:.1f},{gmu:.1f},{tr}\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    print("\n==== TAGS_GPU VERDICT ====", flush=True)
    print(f"violation samples={viol_samples}  peak gpu procs={peak_gpu}  "
          f"peak gpu util={peak_util:.1f}% mem={peak_mem_util:.1f}%  "
          f"peak tags active={peak_tags} of {NTAGS}", flush=True)
    if viol_samples > 0:
        print(f"FAIL: {viol_samples} samples caught tag/GPU placement or GPU "
              f"accounting violations -- see the flagged lines above.", flush=True)
    elif peak_gpu < MIN_GPU or (NTAGS and peak_tags < NTAGS):
        print(f"INCONCLUSIVE: coverage too thin (peak gpu {peak_gpu} < {MIN_GPU} "
              f"or tags {peak_tags} < {NTAGS}); nothing proven. Raise load/duration.",
              flush=True)
    elif peak_util < MIN_UTIL:
        print(f"FAIL: GPU utilization peaked at only {peak_util:.1f}% of GPU-host "
              f"capacity (< {MIN_UTIL:.0f}%) -- the GPU slice is underused despite "
              f"a deep GPU backlog.", flush=True)
    else:
        print(f"PASS: zero violations while {peak_gpu} GPU procs peaked "
              f"({peak_util:.1f}% of GPU units, {peak_mem_util:.1f}% of GPU memory, "
              f"GPU-capable hosts only) and all {peak_tags} tag pools ran work -- "
              f"tag confinement, GPU placement and GPU memory accounting hold "
              f"under fragmentation.", flush=True)


if __name__ == "__main__":
    main()
