"""Inject BIG (wide) jobs into a farm the small feeder keeps saturated, as a
*guaranteed* test of reservations: with reservations OFF these jobs can never
run; with reservations ON they do.

Why it's guaranteed. A work-conserving planner fills any idle core with ready
small work. With a deep 1-2 core backlog, cores free a few at a time and are
refilled within a tick, so a wide block of idle cores never accumulates on a
single host. A wide frame needs BIG_CORES idle cores at once on one host -- which
never happens while small work is waiting. The only escape is the cold-start
transient (an empty farm has whole idle hosts), so we WAIT until the farm is
saturated -- no host has a BIG_CORES idle block -- before ACTIVATING a big job.
After that, the only way BIG_CORES contiguous cores can ever open is the scheduler
reserving a host and draining it (the drain guard stops small work from refilling
it). So:

  - reservations OFF  -> big frames strand forever (run=0).
  - reservations ON   -> the blocked layer reserves a large, it drains, big runs.

Width comes from SIM_STRAND_CORES (whole cores per frame; default 64). At >= 0.5
of the largest host in the group a big layer qualifies for a reservation; the
--verify RESERVATIONS scenario uses 128 (a whole large) so the job can ONLY run
by reserving and draining a full host -- the memory optimiser can't slot it into
the memory-stranded idle cores of a partially loaded host the way it can a
half-host 64-core job.

Big frames request LOW memory (16 GB), trivially satisfiable, so the ONLY reason
a big frame can't run is core fragmentation -- never memory. Jobs are injected at
the SAME priority as the small stream: classic head-of-line starvation, where the
continuously-fed narrow work always wins the transient gaps, so the wide frame
never accumulates its cores. (Equal priority is what makes the starvation
guaranteed: a HIGHER-priority big job is NOT guaranteed to strand -- under fast
churn it can opportunistically grab a transient gap before the small work refills
it. So we inject at equal priority.)

Injection avoids a cuebot launch-queue trap. cuebot's job-launch executor is a
single thread with a 100-deep queue (applicationContext-service.xml, bean
launchQueue); the feeder keeps it saturated with dependency-tree submissions, so
a big job's LaunchSpec is ACCEPTED yet its DispatchLaunchJob can starve in the
backlog and the job silently never materialises -- leaving the reservation test
empty (it then "passes" only on incidental feed-mix luck). So injection is split
in two: a PRECREATE phase stages the big jobs PAUSED before the feeder starts
(idle queue -> they land at once; paused jobs are excluded from scheduling, the
candidate query filters b_paused=false), then the ACTIVATE phase waits for
saturation and RESUMES them on the interval schedule so each strands and can only
run via a reservation.

usage:
  inject_big.py precreate [duration_s] [interval_s]   # stage paused (run pre-feeder)
  inject_big.py [duration_s] [interval_s]             # activate: resume on schedule
"""
import os, sys, time, subprocess
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
# CLI: "precreate [dur] [interval]" stages paused jobs then exits; "[dur] [interval]"
# activates (resumes) them. Both derive the same round count from dur/interval so
# the names line up between the phases.
MODE_PRECREATE = len(sys.argv) > 1 and sys.argv[1] == "precreate"
_args = sys.argv[2:] if MODE_PRECREATE else sys.argv[1:]
DURATION = int(_args[0]) if len(_args) > 0 else 300
INTERVAL = int(_args[1]) if len(_args) > 1 else 30

BIG_CORES  = int(os.environ.get("SIM_STRAND_CORES", "64"))  # whole cores per frame
BIG_MEM_MB = 16 * 1024                # low: memory is never the binding reason
BIG_FRAMES = int(os.environ.get("SIM_STRAND_FRAMES", "24"))   # frames per big job
PRI = 1                               # SAME priority as the small feeder jobs
SATURATE_TIMEOUT = 240                # s to wait for the farm to fill before giving up

# Fairness test (SIM_STRAND_DUR_MIX=1): inject TWO identical wide jobs per round
# that differ ONLY in per-frame run time -- a "durshort" and a "durlong" (fake_rqd
# reads the token and runs them short/long). Same cores, memory and priority, so
# the only difference is processing time. This checks that short wide jobs aren't
# starved out by long ones holding their reserved hosts.
DUR_MIX = os.environ.get("SIM_STRAND_DUR_MIX") == "1"

# One round per INTERVAL across DURATION, matching the old submit cadence; the
# precreate and activate phases use the same count so the staged names resolve.
ROUNDS = max(1, DURATION // INTERVAL)

PSQL = spec.psql_cmd()

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def round_names(n):
    """Job name(s) for round n. Use cuebot's own conformed prefix
    '{show}-{shot}-{user}_' = 'sim-test-sim_' with underscores so the name stores
    VERBATIM (conformJobName is a no-op) and FindJob/precreate can match it exactly;
    a dashed name like 'sim-test-big-eq-1' is rewritten to 'sim-test-sim_..._big_eq_1'
    and would defeat exact lookup. The stable 'big_eq'/'big_durshort'/'big_durlong'
    token stays in the name, which is what the watchers LIKE-match on."""
    if DUR_MIX:
        return [f"sim-test-sim_big_durshort_{n:03d}", f"sim-test-sim_big_durlong_{n:03d}"]
    return [f"sim-test-sim_big_eq_{n:03d}"]


def max_host_idle_cores():
    """Largest idle-core block (whole cores) on any single host right now, or -1
    on error. While this is >= BIG_CORES some host could trivially fit a big
    frame, so activating then would not test reservations."""
    try:
        out = subprocess.run(
            PSQL + ["-c", "SELECT COALESCE(MAX(int_cores_idle),0) FROM host;"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        return int(out) // sim_model.CORE_POINTS
    except Exception:
        return -1


def wait_for_saturation():
    """Block until no host has a BIG_CORES idle block (the farm is full of small
    work), so an activated big frame can only ever run via a reservation. Returns
    True if saturation was reached, False if it timed out."""
    t0 = time.time()
    while time.time() - t0 < SATURATE_TIMEOUT:
        m = max_host_idle_cores()
        if 0 <= m < BIG_CORES:
            print(f"t={time.time()-t0:5.0f}s farm SATURATED (max host idle "
                  f"{m} < {BIG_CORES} cores) -- a big frame can now only run via "
                  f"a reservation; activating", flush=True)
            return True
        print(f"t={time.time()-t0:5.0f}s waiting for saturation "
              f"(max host idle = {m} cores, need < {BIG_CORES}) ...", flush=True)
        time.sleep(3)
    print(f"WARN farm did not saturate within {SATURATE_TIMEOUT}s "
          f"(max host idle still >= {BIG_CORES}); the test is NOT guaranteed",
          flush=True)
    return False


def make_big(name, pri, paused):
    cores_pts = BIG_CORES * sim_model.CORE_POINTS
    pflag = "true" if paused else "false"
    layer = (f'      <layer name="big" type="Render">'
        f'<cmd>/bin/true</cmd><range>1-{BIG_FRAMES}</range><chunk>1</chunk>'
        f'<cores>{cores_pts}</cores><threadable>{sim_model.THREADABLE}</threadable>'
        f'<memory>{BIG_MEM_MB}mb</memory>'
        f'<tags>{spec.TAG}</tags><services><service>shell</service></services></layer>')
    # priority comes right after paused per the cjsl DTD; maxcores generous so
    # it is never the reason a frame can't book.
    return (f'  <job name="{name}"><paused>{pflag}</paused><priority>{pri}</priority>'
            f'<maxcores>{cores_pts * BIG_FRAMES}</maxcores>\n'
            '    <layers>\n' + layer + "\n    </layers>\n  </job>\n")


def _landed(name):
    """True once cuebot's launch queue actually created the job. LaunchSpec can
    return OK while the single-thread launch executor is still backlogged, so we
    confirm the row exists rather than trust the RPC."""
    try:
        out = subprocess.run(
            PSQL + ["-c", f"SELECT count(*) FROM job WHERE str_name = '{name}';"],
            capture_output=True, text=True, timeout=10).stdout.strip()
        return out.isdigit() and int(out) > 0
    except Exception:
        return False


def precreate_paused(stub, name):
    """Create one big job PAUSED and confirm it materialised. Run before the feeder,
    so the launch queue is idle and the job lands within a tick."""
    xml = SPEC_HEAD + make_big(name, PRI, paused=True) + "</spec>\n"
    try:
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    except grpc.RpcError as e:
        print(f"precreate FAILED {name}: {e}", flush=True)
        return False
    for _ in range(20):
        if _landed(name):
            print(f"precreated (paused) {name} cores={BIG_CORES} frames={BIG_FRAMES}",
                  flush=True)
            return True
        time.sleep(1)
    print(f"WARN {name} accepted by LaunchSpec but never materialised", flush=True)
    return False


def activate(stub, name):
    """Resume a pre-created paused big job so it becomes schedulable and strands on
    the now-saturated farm. Falls back to a fresh unpaused submit if the job was
    never precreated (script run standalone)."""
    try:
        j = stub.FindJob(job_pb2.JobFindJobRequest(name=name)).job
        stub.Resume(job_pb2.JobResumeRequest(job=j))
        return True
    except grpc.RpcError:
        xml = SPEC_HEAD + make_big(name, PRI, paused=False) + "</spec>\n"
        try:
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
            return True
        except grpc.RpcError as e:
            print(f"activate FAILED {name}: {e}", flush=True)
            return False


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)

    if MODE_PRECREATE:
        # Phase 1: stage every big job PAUSED on an idle launch queue (before the
        # feeder floods it). Paused jobs sit inert -- excluded from scheduling --
        # until Phase 2 resumes them.
        ok = 0
        for n in range(1, ROUNDS + 1):
            for name in round_names(n):
                if precreate_paused(stub, name):
                    ok += 1
        print(f"precreate done: {ok} paused big jobs staged", flush=True)
        return

    # Phase 2: gate on saturation, then RESUME the staged jobs one round per
    # INTERVAL so an activated big frame strands unless a reservation drains a
    # host for it. This is what makes the test guaranteed.
    wait_for_saturation()
    t0 = time.time()
    for n in range(1, ROUNDS + 1):
        for name in round_names(n):
            if activate(stub, name):
                print(f"t={time.time()-t0:5.0f}s activated {name} "
                      f"pri={PRI} cores={BIG_CORES} frames={BIG_FRAMES}", flush=True)
        # Sleep to the next interval without overshooting the duration.
        end = min(t0 + DURATION, time.time() + INTERVAL)
        while time.time() < end:
            time.sleep(min(2.0, end - time.time()))
    print(f"injector done: activated {ROUNDS} rounds", flush=True)


if __name__ == "__main__":
    main()
