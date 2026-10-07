"""STRANDGROW workload: memory-heavy 1-core layers that strand host cores.

The production shape: a layer whose frames really hold 18G asks 1 core. A
few frames exhaust a host's memory and the rest of its cores sit idle but
unbookable. The scheduler books those frames at round(memory / the group's
memory-per-core) cores (18G -> 5 cores) instead of 1, so the cores work
instead of stranding. The rss is pinned by the fake RQD (SIM_RSS_PIN).

Three jobs, one group (same tag):
  - flood:  deep threadable 1-core layer that UNDER-declares (2G). The
            patient: only rss evidence can size it, after a probe.
  - honest: threadable 1-core layer that declares its real 18G. Sized from
            its declaration on frame one, no probe.
  - ctrl:   NON-threadable 18G. Must never get more than 1 core.

threadable is hardcoded per layer on purpose: SIM_THREADABLE flips with
other knobs and would silently change the premise.

usage: inject_strandgrow.py [duration_s]
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
FLOOD_FRAMES = int(os.environ.get("SIM_STRANDGROW_FRAMES", "4000"))
CTRL_FRAMES = int(os.environ.get("SIM_STRANDGROW_CTRL_FRAMES", "25"))
HONEST_FRAMES = int(os.environ.get("SIM_STRANDGROW_HONEST_FRAMES", "60"))
MEM_MB = int(os.environ.get("SIM_STRANDGROW_MEM_MB", "18432"))
DECLARED_MB = int(os.environ.get("SIM_STRANDGROW_DECLARED_MB", "2048"))
TOKEN = "simstrandgrow"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def job_xml(job, layer, frames, threadable, mem_mb):
    lay = (f'      <layer name="{layer}" type="Render"><cmd>/bin/true</cmd>'
           f'<range>1-{frames}</range><chunk>1</chunk>'
           f'<cores>{sim_model.CORE_POINTS}</cores>'
           f'<threadable>{threadable}</threadable><memory>{mem_mb}mb</memory>'
           f'<tags>{spec.TAG}</tags>'
           f'<services><service>shell</service></services></layer>')
    return (f'  <job name="sim-test-{TOKEN}_{job}-00001"><paused>false</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{lay}\n    </layers>\n  </job>\n')


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    for body in (job_xml("flood", "hog", FLOOD_FRAMES, 1, DECLARED_MB),
                 job_xml("honest", "hogdeclared", HONEST_FRAMES, 1, MEM_MB),
                 job_xml("ctrl", "hognothread", CTRL_FRAMES, 0, MEM_MB)):
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=SPEC_HEAD + body
                                                     + "</spec>\n"))
    print(f"STRANDGROW: flood {FLOOD_FRAMES} threadable 1-core frames "
          f"declaring {DECLARED_MB}mb + {HONEST_FRAMES} declaring {MEM_MB}mb "
          f"+ {CTRL_FRAMES} non-threadable controls, staying up {DURATION}s.",
          flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
