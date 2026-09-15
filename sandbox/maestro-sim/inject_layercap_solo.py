"""LAYERCAP_SOLO workload: the one huge layer that could use the whole farm.

The flip side of LAYERCAP. There, the flood competes with other work and the
per-host layer cap must hold. Here the flood is the ONLY work on the farm,
and a cap that still binds is just the scheduler stranding its own cores: a
25% cap turns a farm-sized layer into a 25% farm. The cap is for contention;
with nobody else waiting, the layer must be allowed to blanket every machine
(the relax pass grants rss-proven layers over-cap commits when capacity
would otherwise idle).

One job, one non-threadable 1-core layer, nothing else. Non-threadable means
rss-proven from the first tick, so the relax pass applies immediately and
the probe gate stays out of the picture.

usage: inject_layercap_solo.py [duration_s]
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
FRAMES = int(os.environ.get("SIM_LAYERCAP_SOLO_FRAMES", "20000"))
TOKEN = "simlayercapsolo"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def make_job():
    layer = (f'      <layer name="flood" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{FRAMES}</range><chunk>1</chunk>'
             f'<cores>{sim_model.CORE_POINTS}</cores>'
             f'<threadable>0</threadable><memory>512mb</memory>'
             f'<tags>{spec.TAG}</tags>'
             f'<services><service>shell</service></services></layer>')
    # "durlong" in the job name pins each frame to 120s in fake_rqd: churn per
    # host per tick then matches production shape (well under one frame), so
    # the verdict measures the scheduler, not the sim's compressed durations.
    return (f'  <job name="sim-test-{TOKEN}-durlong-00001"><paused>false</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{layer}\n    </layers>\n  </job>\n')


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    xml = SPEC_HEAD + make_job() + "</spec>\n"
    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"LAYERCAP_SOLO: one layer, {FRAMES} 1-core frames, alone on the "
          f"farm, staying up {DURATION}s.", flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
