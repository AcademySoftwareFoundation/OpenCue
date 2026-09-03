"""SOLOFILL workload: does a layer's fill rate depend on how many layers there are?

Two jobs of EQUAL total frames land together on an idle farm with room for
both: job A has ONE layer, job B has LAYERS layers. Every frame is the same
shape (non-threadable, 1 core, 512mb, long duration), so nothing but the
layer count differs. The invariant under test: a layer's fill rate is bounded
by its waiting frames and the idle capacity that fits it, never by a per-tick
constant. If Maestro places each layer on one host per tick, job B grows
LAYERS times faster than job A, and the watcher's ratio at the mark shows it.

Non-threadable keeps the probe gate out of the picture (rss-proven from the
first tick), and "durlong" pins each frame to a long runtime so the booked
frames stay running while the ramp is measured.

usage: inject_solofill.py [duration_s]
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
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
FRAMES = int(os.environ.get("SIM_SOLOFILL_FRAMES", "20000"))
LAYERS = int(os.environ.get("SIM_SOLOFILL_LAYERS", "50"))
TOKEN_SOLO = "simsolo"
TOKEN_MANY = "simmany"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def layer_xml(name, frames):
    return (f'      <layer name="{name}" type="Render"><cmd>/bin/true</cmd>'
            f'<range>1-{frames}</range><chunk>1</chunk>'
            f'<cores>{sim_model.CORE_POINTS}</cores>'
            f'<threadable>0</threadable><memory>512mb</memory>'
            f'<tags>{spec.TAG}</tags>'
            f'<services><service>shell</service></services></layer>')


def job_xml(token, layers):
    body = "\n".join(layers)
    return (f'  <job name="sim-test-{token}-durlong-00001"><paused>false</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{body}\n    </layers>\n  </job>\n')


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    per_layer = max(1, FRAMES // LAYERS)
    solo = SPEC_HEAD + job_xml(TOKEN_SOLO, [layer_xml("solo", FRAMES)]) + "</spec>\n"
    many = SPEC_HEAD + job_xml(TOKEN_MANY, [layer_xml(f"many{i + 1:02d}", per_layer)
                                             for i in range(LAYERS)]) + "</spec>\n"
    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=solo))
    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=many))
    print(f"SOLOFILL: job A = 1 layer x {FRAMES} frames; job B = {LAYERS} layers x "
          f"{per_layer} frames; both 1-core non-threadable, launched together on "
          f"the idle farm, staying up {DURATION}s.", flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
