"""SLICE workload: one wide layer on a few large hosts.

A placement slot books a slice of one layer on one host. Maestro sizes
the slice (frame_query_max at most, the per-host layer share, the backlog),
charges the host and every cap for it, and hands the plan read that size.
The plan read must deliver the slice Maestro accounted, or the host
carries phantom reservation for the rest of the tick and the frames past
the delivered count wait a tick for nothing.

Three large hosts (128 cores, share cap 32 frames per layer) and one job
with one layer of one-core frames, long enough that nothing completes
while the first ticks are read. Every first slice on such a host should be
frame_query_max (20) frames.

usage: inject_slice.py [duration_s]
"""
import os, subprocess, sys, time
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 120
FRAMES = int(os.environ.get("SIM_SLICE_FRAMES", "2000"))
TOKEN = "simslice"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def job(name, frames):
    layer = (f'      <layer name="wide" type="Render"><cmd>/bin/true</cmd>'
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
    xml = SPEC_HEAD + job(f"sim-test-{TOKEN}-durlong-00001", FRAMES) + "</spec>\n"
    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"SLICE: one layer of {FRAMES} one-core frames submitted", flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
