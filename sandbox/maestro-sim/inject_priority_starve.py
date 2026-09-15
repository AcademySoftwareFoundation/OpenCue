"""Priority-fairness STARVATION test: does low-priority work starve under
sustained high-priority load?

Two paced streams of statistically identical jobs differing ONLY in priority --
a HIGH class (SIM_PRI_HI, default 300) and a LOW class (SIM_PRI_LO, default 100).
For the test to be valid the farm must be SATURATED first: only when every core
is contested does priority actually decide who runs. While there are spare cores
BOTH priorities book and nobody starves -- that is not a priority test. So the
injector runs in two phases, like the reservation test's saturation gate:

  Phase 1 -- pre-saturate with HIGH only: submit HIGH jobs (paced) until the farm
    is pinned (utilization >= SIM_PRI_SAT_UTIL, default 95%). LOW is held back so
    it can't grab the empty-farm cold-start cores.

  Phase 2 -- contend: keep HIGH's backlog deep (so every freed core always has
    HIGH work waiting) AND start feeding LOW. Now the only way LOW runs is if the
    scheduler chooses it over waiting HIGH work:
      - strict priority (today): HIGH wins every freed core, LOW starves (FAIL).
      - stochastic priority: LOW gets ~LO/(LO+HI) of the farm (PASS).

Jobs are multi-layer with a realistic narrow core mix (never wide enough to need
reservations) and LIGHT memory (so memory never binds) -- purely a booking-
priority test. Submission is paced in waves of WAVE with backoff because cuebot's
job-launch executor is single-threaded (pool=1, bounded queue): bursting overflows
it and specs get rejected. priority_starve_watch.py samples the two classes and renders
the verdict.

usage: inject_priority_starve.py [duration_s] [ignored]
"""
import os, sys, time, random, subprocess
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300

PRI_HI = int(os.environ.get("SIM_PRI_HI", "300"))
PRI_LO = int(os.environ.get("SIM_PRI_LO", "100"))
# Keep this many depend-free WAITING frames per class so each stream always has
# runnable work; HIGH is held deep enough to fill the farm many times over.
HI_TARGET = int(os.environ.get("SIM_PRI_HI_TARGET", "30000"))
LO_TARGET = int(os.environ.get("SIM_PRI_LO_TARGET", "20000"))
SAT_UTIL = float(os.environ.get("SIM_PRI_SAT_UTIL", "95"))       # phase-1 gate (%)
SAT_TIMEOUT = int(os.environ.get("SIM_PRI_SAT_TIMEOUT", "180"))  # s before giving up
WAVE = 6                          # specs per burst (launch queue is pool=1, bounded)
LAYERS_MIN, LAYERS_MAX = 2, 5
FRAMES_MIN, FRAMES_MAX = 50, 90
MAX_CORES = 8                     # cap layer width: narrow (booking, not reservations)
PSQL = spec.psql_cmd()

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def make_job(name, pri, rng):
    n = rng.randint(LAYERS_MIN, LAYERS_MAX)
    layers = []
    for li in range(n):
        nf = rng.randint(FRAMES_MIN, FRAMES_MAX)
        cores = min(MAX_CORES, sim_model.sample_layer_cores())   # realistic narrow mix
        mem_mb = cores * 1024                                    # LIGHT (1 GB/core): never binds
        layers.append(f'      <layer name="lyr{li}_c{cores}" type="Render">'
            f'<cmd>/bin/true</cmd><range>1-{nf}</range><chunk>1</chunk>'
            f'<cores>{cores*sim_model.CORE_POINTS}</cores>'
            f'<threadable>{sim_model.THREADABLE}</threadable><memory>{mem_mb}mb</memory>'
            f'<tags>{spec.TAG}</tags><services><service>shell</service></services></layer>')
    # priority right after paused per the cjsl DTD; maxcores generous so only
    # priority -- never a per-job cap -- decides who books.
    return (f'  <job name="{name}"><paused>false</paused><priority>{pri}</priority>'
            f'<maxcores>80000</maxcores>\n'
            '    <layers>\n' + "\n".join(layers) + "\n    </layers>\n  </job>\n")


def _scalar(sql, cast, default):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=10).stdout.strip()
        return cast(out)
    except Exception:
        return default


def waiting(token):
    """Depend-free WAITING frames whose job name carries `token` (HI/LO backlog)."""
    return _scalar(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                   f"WHERE j.str_name LIKE '%{token}%' AND f.str_state='WAITING' "
                   f"AND f.int_depend_count=0;", int, -1)


def util_pct():
    return _scalar("SELECT COALESCE(100.0*(sum(int_cores)-sum(int_cores_idle))"
                   "/NULLIF(sum(int_cores),0),0) FROM host;", float, -1.0)


def max_host_idle():
    return _scalar("SELECT COALESCE(MAX(int_cores_idle),0) FROM host;", int, -1) // \
        sim_model.CORE_POINTS


def submit_wave(stub, prefix, pri, seq):
    """Submit up to WAVE jobs; back off (and stop the wave) on launch-queue reject."""
    for _ in range(WAVE):
        seq += 1
        xml = SPEC_HEAD + make_job(f"{prefix}-{seq:05d}", pri,
                                   random.Random(seq * 7 + pri)) + "</spec>\n"
        try:
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
        except grpc.RpcError:
            time.sleep(2.0)            # launch queue full -> back off, retry next tick
            break
    return seq


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    print(f"PRIORITY test: HI=pri{PRI_HI} (hold {HI_TARGET} waiting) vs "
          f"LO=pri{PRI_LO} (hold {LO_TARGET}); phase1 saturate with HI to "
          f"util>={SAT_UTIL:.0f}%, then contend, for {DURATION}s.", flush=True)
    t0 = time.time()
    hi_seq = lo_seq = 0

    # Phase 1: HIGH only, until the farm is pinned (no cold-start cores for LOW).
    saturated = False
    while time.time() - t0 < min(SAT_TIMEOUT, DURATION):
        u = util_pct()
        if u >= SAT_UTIL:
            print(f"t={time.time()-t0:5.0f}s farm SATURATED (util={u:.1f}%, maxIdle="
                  f"{max_host_idle()}c) -- starting LOW; it now runs ONLY if the "
                  f"scheduler shares cores across priorities", flush=True)
            saturated = True
            break
        w = waiting("prihi")
        if 0 <= w < HI_TARGET:
            hi_seq = submit_wave(stub, "sim-test-prihi", PRI_HI, hi_seq)
        print(f"t={time.time()-t0:5.0f}s [saturating] util={u:5.1f}% HI_waiting={w} "
              f"HI_jobs={hi_seq}", flush=True)
        time.sleep(2.0)
    if not saturated:
        print(f"t={time.time()-t0:5.0f}s WARN farm did not reach {SAT_UTIL:.0f}% within "
              f"{SAT_TIMEOUT}s; starting LOW anyway (verdict may be INCONCLUSIVE)",
              flush=True)

    # Phase 2: keep HIGH deep AND feed LOW; whoever the scheduler picks, wins.
    while time.time() - t0 < DURATION:
        whi, wlo = waiting("prihi"), waiting("prilo")
        if 0 <= whi < HI_TARGET:
            hi_seq = submit_wave(stub, "sim-test-prihi", PRI_HI, hi_seq)
        if 0 <= wlo < LO_TARGET:
            lo_seq = submit_wave(stub, "sim-test-prilo", PRI_LO, lo_seq)
        print(f"t={time.time()-t0:5.0f}s [contend] util={util_pct():5.1f}% "
              f"HI_wait={whi} LO_wait={wlo} HI_jobs={hi_seq} LO_jobs={lo_seq}",
              flush=True)
        time.sleep(2.0)
    print(f"injector done: HI_jobs={hi_seq} LO_jobs={lo_seq}", flush=True)


if __name__ == "__main__":
    main()
