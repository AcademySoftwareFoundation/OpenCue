"""CAPDROP test injector: reproduce a user lowering a job's max cores under load.

Floods the farm with a few DEEP 1-core jobs (generous max cores, no limits), so the
planner books one job wide across the farm. The companion capdrop_watch.py then
lowers the busiest job's int_max_cores BELOW its live usage, exactly what a user
does in production with "set max cores" on a running job. The planner's next
accounting flush for that job arrives over the new cap, and the legacy
verify_job_resources trigger rejects it; the watcher asserts the accounting mirror
(job_resource.int_cores) still tracks the truth (SUM of the job's procs).

usage: inject_capdrop.py [duration_s]
"""
import os, sys, time, random
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180

# A few deep jobs, not a stream: the watcher targets ONE busy job and lowers its
# cap, so each job must be wide enough to occupy a large slice of the small farm.
NJOBS = int(os.environ.get("SIM_CAPDROP_JOBS", "3"))
LAYERS = 4
FRAMES = int(os.environ.get("SIM_CAPDROP_FRAMES", "400"))   # per layer, deep backlog

TOKEN = "simcapdrop"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def make_job(name, rng):
    layers = []
    for li in range(LAYERS):
        layers.append(
            f'      <layer name="lyr{li}" type="Render"><cmd>/bin/true</cmd>'
            f'<range>1-{FRAMES}</range><chunk>1</chunk>'
            f'<cores>{sim_model.CORE_POINTS}</cores>'
            f'<threadable>0</threadable><memory>512mb</memory>'
            f'<tags>{spec.TAG}</tags>'
            f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused><priority>100</priority>'
            f'<maxcores>80000</maxcores>\n    <layers>\n'
            + "\n".join(layers) + "\n    </layers>\n  </job>\n")


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    print(f"CAPDROP test: submit {NJOBS} deep jobs ({LAYERS}x{FRAMES} 1-core frames "
          f"each, generous max cores); the watcher drops one cap mid-run.", flush=True)
    for i in range(NJOBS):
        xml = SPEC_HEAD + make_job(f"sim-test-{TOKEN}-{i:03d}",
                                   random.Random(i * 17)) + "</spec>\n"
        try:
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
            print(f"submitted {TOKEN}-{i:03d}", flush=True)
        except grpc.RpcError as e:
            print(f"launch failed for job {i}: {e}", flush=True)
        time.sleep(1.0)
    # Stay alive for the window so the harness's process accounting stays simple.
    t0 = time.time()
    while time.time() - t0 < DURATION:
        time.sleep(5.0)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
