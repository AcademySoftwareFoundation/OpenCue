"""COMPLETIONSTORM workload: complete frames faster than one clerk can file.

When a frame finishes, the batched stop does the urgent work inside the tick
and the slow follow-up work (depend satisfaction, layer and job completion
checks, usage counters) goes to one background worker through a queue. The
Maestro must NEVER do that follow-up work itself: the base states the
invariant in the worker's own comment, because tick time would then multiply
by the completion rate. This scenario manufactures a completion rate above
one worker's filing speed and watches what the tick does about it.

Small farm on purpose (40 small hosts, 640 cores), so the storm comes from
frame DURATION, not from farm size, and the box running the sim is never
starved: 640 procs of two second frames complete ~320 frames per second,
far past one worker at ~5-10 ms per post-op. The disease (a queue that
overflows onto the Maestro thread) shows as tick inflation; the cure (an
unbounded queue plus a retry signal to RQD at the door) shows as a calm
tick, zero dropped completions, and RQD redial traffic instead.

usage: inject_completionstorm.py [duration_s]
"""
import os, sys, time
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 240
JOBS = int(os.environ.get("SIM_STORM_JOBS", "20"))
FRAMES = int(os.environ.get("SIM_STORM_FRAMES", "4000"))
TOKEN = "simstorm"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def one_job(name, frames):
    layer = (f'      <layer name="storm" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{sim_model.CORE_POINTS}</cores>'
             f'<threadable>0</threadable><memory>512mb</memory>'
             f'<tags>{spec.TAG}</tags>'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{layer}\n    </layers>\n  </job>\n')


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    for n in range(1, JOBS + 1):
        xml = SPEC_HEAD + one_job(f"sim-test-{TOKEN}-durlong-{n:05d}", FRAMES) + "</spec>\n"
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"COMPLETIONSTORM: {JOBS} jobs x {FRAMES} one-core frames at "
          f"{os.environ.get('SIM_DUR_LONG_S', '?')}s each, staying up {DURATION}s.",
          flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
