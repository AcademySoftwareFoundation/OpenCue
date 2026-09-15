"""LAYERCAP workload: one deep single-layer flood against a busy farm.

The pathological shape from production: one layer with thousands of identical
1-core frames and a huge maxcores. The per-host layer cap is a CONTENTION
rule: while other work is waiting, no host may give the flood more than its
share (a quarter of its cores), or one layer starves everyone else machine by
machine. So this scenario builds real contention first: background jobs are
submitted and the farm saturates, THEN the flood arrives. The cap must hold
on every host for the whole run while the background keeps its cores.

The lone-layer case (an idle farm where the cap must YIELD instead of
stranding cores) is LAYERCAP_SOLO's job, not this one.

usage: inject_layercap.py [duration_s]
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
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
FRAMES = int(os.environ.get("SIM_LAYERCAP_FRAMES", "20000"))
BG_JOBS = int(os.environ.get("SIM_LAYERCAP_BG_JOBS", "8"))
BG_FRAMES = int(os.environ.get("SIM_LAYERCAP_BG_FRAMES", "3000"))
SATURATE_UTIL = 85.0
SATURATE_WAIT_S = 90
TOKEN = "simlayercap"
BG_TOKEN = "simcapbg"
PSQL = spec.psql_cmd()

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def one_layer_job(name, frames, priority=100):
    layer = (f'      <layer name="flood" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{sim_model.CORE_POINTS}</cores>'
             f'<threadable>0</threadable><memory>512mb</memory>'
             f'<tags>{spec.TAG}</tags>'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused>'
            f'<priority>{priority}</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{layer}\n    </layers>\n  </job>\n')


def util_pct():
    try:
        out = subprocess.run(
            PSQL + ["-c", "SELECT sum(int_cores), sum(int_cores - int_cores_idle) FROM host;"],
            capture_output=True, text=True, timeout=15).stdout.strip()
        total, busy = out.split("|")
        return 100.0 * int(busy or 0) / max(1, int(total or 0))
    except Exception:
        return 0.0


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    for i in range(BG_JOBS):
        xml = SPEC_HEAD + one_layer_job(f"sim-test-{BG_TOKEN}{i + 1:02d}-00001",
                                        BG_FRAMES) + "</spec>\n"
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"LAYERCAP: {BG_JOBS} background jobs x {BG_FRAMES} frames "
          f"submitted; waiting for the farm to saturate before the flood.",
          flush=True)
    t0 = time.time()
    while time.time() - t0 < SATURATE_WAIT_S:
        u = util_pct()
        if u >= SATURATE_UTIL:
            break
        time.sleep(3)
    print(f"farm at {util_pct():.0f}% util; releasing the flood.", flush=True)
    # Priority 400 vs the background 100: the flood must actually reach its
    # capped share so the cap is tested at its edge, not from below.
    xml = SPEC_HEAD + one_layer_job(f"sim-test-{TOKEN}-00001", FRAMES,
                                    priority=400) + "</spec>\n"
    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"LAYERCAP flood: one layer, {FRAMES} 1-core frames, against a "
          f"busy farm, staying up {DURATION}s.", flush=True)
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
