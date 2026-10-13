"""BACKLOG workload: a few deep layers so the plan reads face a huge waiting list.

The plan read of a (host, layer) slice used to number every WAITING frame of the
layer with ROW_NUMBER() once per host the layer landed on, so a layer of
90k waiting frames placed on 150 hosts cost 150 sorts of 90k rows per tick.
This injects JOBS jobs of one layer each, FRAMES one-core frames per layer
(JobSpec caps a job at 100k), long frames ("durlong") so the backlog stays
deep for the whole run. The watcher measures the tick from Prometheus.

usage: inject_backlog.py [duration_s]
"""
import os
import sys
import threading
import time

import grpc

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 600
JOBS = int(os.environ.get("SIM_BACKLOG_JOBS", "4"))
FRAMES = int(os.environ.get("SIM_BACKLOG_FRAMES", "90000"))
TOKEN = "simbacklog"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def job(name, frames):
    layer = (f'      <layer name="deep" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{sim_model.CORE_POINTS}</cores>'
             f'<threadable>0</threadable><memory>512mb</memory>'
             f'<tags>{spec.TAG}</tags>'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{layer}\n    </layers>\n  </job>\n')


def launch(stub, index, launched):
    name = f"sim-test-{TOKEN}-durlong-{index:05d}"
    xml = SPEC_HEAD + job(name, FRAMES) + "</spec>\n"
    t0 = time.time()
    try:
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml), timeout=1800)
    except grpc.RpcError as e:
        print(f"BACKLOG: {name} launch failed: {e.code()} {e.details()}", flush=True)
        return
    launched.append(name)
    print(f"BACKLOG: {name} launched ({FRAMES} frames) in {time.time() - t0:.0f}s",
          flush=True)


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    # Launches are serial inserts inside cuebot; run them concurrently so the
    # backlog is up in minutes, not tens of minutes.
    launched = []
    threads = [threading.Thread(target=launch, args=(stub, i + 1, launched))
               for i in range(JOBS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"BACKLOG: {len(launched)} of {JOBS} jobs x {FRAMES} one-core long frames "
          f"submitted, staying up {DURATION}s.", flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
