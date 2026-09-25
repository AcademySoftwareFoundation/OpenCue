"""GPUSTRAND watcher: CPU-only work must not keep an idle GPU unreachable.

Samples the farm while a CPU-only flood saturates it and a GPU job then asks
for one GPU. A GPU is reachable only through a core and some memory, so a
host that holds an idle GPU behind cores and memory that CPU-only work
occupies is STRANDED: the hardware is idle, and no GPU frame can start
beside it. A resource can only be stranded by work that does not use it, so
a host counts as stranded only while a non-GPU proc runs on it. A host whose
cores are all held by GPU frames, with one GPU left over, is not a fault.

No scheduler without preemption can free a stranded host before the CPU
frames on it finish. What the scheduler controls is what happens to the
cores as they free up. The invariant is therefore about the drain, and it is
measured only on samples where GPU frames wait:

  1. the stranded count never rises again after the GPU job is seen (the
     first two ticks after the job arrives are ingestion and are exempt),
     because freed capacity on a host with an idle GPU never goes back to
     CPU-only work while a GPU frame could use it;
  2. the stranded count reaches ZERO inside the run, because every stranded
     host drains into GPU work;
  3. GPU frames run.

The reference shape is the GPU job's own ask (2 software cores, 2G of memory,
1 GPU, 4G of GPU memory), so "unreachable" means exactly what the waiting
frames need, not a nominal frame the farm never sees.

PASS      : the three points above hold.
FAIL      : the disease. Freed cores on a host with an idle GPU went back to
            CPU-only work (the count rose), the stranded hosts never drained
            (the count never reached zero), or no GPU frame ever ran.
INCONCLUSIVE: the flood never saturated the farm, or the GPU job never
            reached the database, so nothing was measured.

usage: gpustrand_watch.py [duration_s] [interval_s]
"""
import os, subprocess, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_model

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
TOKEN = "simgpustrand"
GB_KB = 1024 * 1024
GPU_ASK_CP = 2 * sim_model.CORE_POINTS  # 2 software cores, as inject_gpustrand.gpu_job asks
GPU_ASK_MEM_KB = 2 * GB_KB
GPU_ASK_GPU_MEM_KB = 4 * GB_KB
MIN_UTIL = 85.0                   # below this the flood never took hold
INGEST_GRACE_S = 6.0              # two ticks: Maestro has not seen the job yet
CSV = os.environ.get("SIM_GPUSTRAND_CSV", "")
PSQL = spec.psql_cmd()


def q(sql):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip().splitlines()
    except Exception:
        return []


def scalar(sql):
    rows = q(sql)
    return int(rows[0]) if rows and rows[0].strip().lstrip("-").isdigit() else 0


def sample():
    util = q("SELECT round(100.0 * sum(int_cores - int_cores_idle) / sum(int_cores), 1)"
             " FROM host;")
    u = float(util[0]) if util and util[0].strip() else 0.0
    # Cuebot normalizes hyphens to underscores, so the flood pattern rides the
    # underscored form; the _ wildcard only matches that underscore and never
    # reaches the gpu arm, whose token is a longer prefix.
    flood = scalar("SELECT count(*) FROM proc p JOIN job j ON j.pk_job=p.pk_job"
                   f" WHERE j.str_name LIKE '%{TOKEN}_durlong%';")
    gpu_run = scalar("SELECT count(*) FROM proc p JOIN job j ON j.pk_job=p.pk_job"
                     f" WHERE j.str_name LIKE '%{TOKEN}gpu%';")
    gpu_wait = scalar("SELECT count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job"
                      f" WHERE j.str_name LIKE '%{TOKEN}gpu%' AND f.str_state='WAITING';")
    # Stranded: an idle GPU the waiting frames could use, behind cores or
    # memory below their ask, on a host where non-GPU work holds capacity.
    stranded = scalar(
        "SELECT count(*) FROM host h WHERE h.int_gpus_idle >= 1"
        f" AND h.int_gpu_mem_idle >= {GPU_ASK_GPU_MEM_KB}"
        f" AND (h.int_cores_idle < {GPU_ASK_CP} OR h.int_mem_idle < {GPU_ASK_MEM_KB})"
        " AND EXISTS (SELECT 1 FROM proc p JOIN job j ON j.pk_job=p.pk_job"
        f" WHERE p.pk_host=h.pk_host AND j.str_name NOT LIKE '%{TOKEN}gpu%');")
    idle_gpus = scalar("SELECT COALESCE(sum(int_gpus_idle),0) FROM host;")
    return u, flood, gpu_run, gpu_wait, stranded, idle_gpus


def main():
    gpu_hosts = scalar("SELECT count(*) FROM host WHERE int_gpus > 0;")
    print(f"watching GPUSTRAND for {DURATION}s. The farm has {gpu_hosts} GPU hosts. "
          f"A CPU-only flood saturates it, then a GPU job asks for 1 GPU and "
          f"{GPU_ASK_CP // 100} cores. PASS needs GPU frames running, a stranded "
          f"count that never rises while GPU frames wait, and that count at zero "
          f"before the end.\n", flush=True)
    t0 = time.time()
    peak_util = 0.0
    gpu_ran = 0
    gpu_ever_waited = False
    first_wait_t = None
    prev_stranded = None
    stranded_peak = 0
    rises = 0
    rise_t = None
    zero_t = None
    last_stranded = None
    waiting_samples = 0
    rows_out = []
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        util, flood, gpu_run, gpu_wait, stranded, idle_gpus = sample()
        peak_util = max(peak_util, util)
        gpu_ran = max(gpu_ran, gpu_run)
        if gpu_wait > 0:
            gpu_ever_waited = True
            waiting_samples += 1
            if first_wait_t is None:
                first_wait_t = t
            stranded_peak = max(stranded_peak, stranded)
            if (prev_stranded is not None and stranded > prev_stranded
                    and t - first_wait_t > INGEST_GRACE_S):
                rises += 1
                if rise_t is None:
                    rise_t = t
            if stranded == 0 and zero_t is None and t - first_wait_t > INGEST_GRACE_S:
                zero_t = t
            prev_stranded = stranded
            last_stranded = stranded
        print(f"t={t:5.0f} | util {util:5.1f}% | flood {flood:5d} | "
              f"gpu run {gpu_run:3d} wait {gpu_wait:4d} | idle gpus {idle_gpus:3d} | "
              f"stranded hosts {stranded:2d}", flush=True)
        rows_out.append((t, util, flood, gpu_run, gpu_wait, stranded, idle_gpus))
        time.sleep(INTERVAL)

    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("t,util,flood_procs,gpu_running,gpu_waiting,stranded_hosts,idle_gpus\n")
                for r in rows_out:
                    f.write(",".join(str(x) for x in r) + "\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    drained = last_stranded == 0 and zero_t is not None
    print("\n==== GPUSTRAND VERDICT ====", flush=True)
    print(f"peak util {peak_util:.1f}%; gpu frames peak running {gpu_ran}; "
          f"samples with gpu waiting {waiting_samples}; stranded peak {stranded_peak} "
          f"hosts, rises {rises}, zero at "
          f"{'never' if zero_t is None else f'{zero_t:.0f}s'}, "
          f"final {last_stranded if last_stranded is not None else '?'}", flush=True)
    if gpu_hosts == 0:
        print("INCONCLUSIVE: the farm has no GPU hosts; nothing was measured.", flush=True)
    elif peak_util < MIN_UTIL:
        print(f"INCONCLUSIVE: the flood only reached {peak_util:.1f}% "
              f"(< {MIN_UTIL}%); the farm was never full, so nothing was measured.",
              flush=True)
    elif not gpu_ever_waited and gpu_ran == 0:
        print("INCONCLUSIVE: the GPU job never reached the database.", flush=True)
    elif gpu_ran == 0:
        print("FAIL: no GPU frame ever ran.", flush=True)
    elif rises > 0:
        print(f"FAIL: the stranded count rose {rises} times while GPU frames waited "
              f"(first at {rise_t:.0f}s). Freed cores on a host with an idle GPU went "
              f"back to CPU-only work, so the GPU stayed unreachable.", flush=True)
    elif not drained:
        print(f"FAIL: {stranded_peak} hosts held an idle GPU behind CPU-only work while "
              f"GPU frames waited, and the count never reached zero (final "
              f"{last_stranded}). The stranded hosts did not drain into GPU work.",
              flush=True)
    else:
        print(f"PASS: {gpu_ran} GPU frames ran; the stranded count fell from "
              f"{stranded_peak} to zero at {zero_t:.0f}s and never rose while GPU "
              f"frames waited, at {peak_util:.1f}% peak utilization.", flush=True)


if __name__ == "__main__":
    main()
