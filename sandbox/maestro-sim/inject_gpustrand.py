"""GPUSTRAND workload: CPU-only work buries the GPUs it cannot use.

A GPU is reachable only through a core and some memory. Fill a GPU host with
CPU-only frames and its GPUs go dark: the hardware is idle, but no GPU frame
can start beside it. Stock OpenCue holds a hole open for exactly this. When
the legacy dispatcher visits a GPU host and finds no GPU work waiting, it
hides one GPU frame's worth of the host (1 core, 4G of memory, 1 GPU, 4G of
GPU memory) from the CPU-only pass that follows, and restores it after. The
Maestro scores the whole farm at once, so it has no pass to hide capacity
from, and a CPU-only frame pays nothing for a GPU. An empty GPU host is then
the CHEAPEST machine on the farm for CPU work.

Small farm with GPU machines (SIM_GPU sizes the hosts, SIM_GPU_LAYERS=0 keeps
the background feed CPU-only). Two arms:

  flood  sim-test-simgpustrand-*     1-core CPU-only frames, thousands of
                                     them, run anywhere: saturates the farm
                                     including every GPU host.
  gpu    sim-test-simgpustrandgpu-*  submitted only AFTER the flood saturates,
                                     asks for 1 GPU and 2 cores (threadable, so
                                     the booking is the ask; a non-threadable
                                     frame always books one core): must start,
                                     because idle GPUs are worthless while GPU
                                     work waits. Two cores per GPU is half of a
                                     GPU host, so the other half stays open to
                                     CPU work even while GPU frames wait.

The flood arrives first on purpose. A GPU job that is already running when
the farm fills proves nothing; the disease is a GPU frame that arrives to a
farm whose GPUs are idle and unreachable.

usage: inject_gpustrand.py [duration_s]
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
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
FLOOD_JOBS = int(os.environ.get("SIM_GPUSTRAND_JOBS", "12"))
FLOOD_FRAMES = int(os.environ.get("SIM_GPUSTRAND_FRAMES", "4000"))
GPU_FRAMES = int(os.environ.get("SIM_GPUSTRAND_GPU_FRAMES", "400"))
SATURATE_UTIL = float(os.environ.get("SIM_GPUSTRAND_SATURATE_UTIL", "90"))
SATURATE_WAIT_S = int(os.environ.get("SIM_GPUSTRAND_SATURATE_WAIT", "75"))
TOKEN = "simgpustrand"
PSQL = spec.psql_cmd()

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def cpu_job(name, frames):
    layer = (f'      <layer name="flood" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{sim_model.CORE_POINTS}</cores>'
             f'<threadable>0</threadable><memory>512mb</memory>'
             f'<tags>{spec.TAG}</tags>'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{layer}\n    </layers>\n  </job>\n')


def gpu_job(name, frames):
    layer = (f'      <layer name="render" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{2 * sim_model.CORE_POINTS}</cores>'
             f'<threadable>1</threadable><memory>2048mb</memory>'
             f'<gpus>1</gpus><gpu_memory>4096mb</gpu_memory>'
             f'<tags>{spec.TAG}</tags>'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
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


def gpu_hosts():
    try:
        out = subprocess.run(PSQL + ["-c", "SELECT count(*) FROM host WHERE int_gpus > 0;"],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        return int(out) if out.isdigit() else 0
    except Exception:
        return 0


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    print(f"GPUSTRAND: farm has {gpu_hosts()} GPU hosts. Flooding with "
          f"{FLOOD_JOBS} CPU-only jobs, then the GPU job once the farm is full.",
          flush=True)
    for n in range(1, FLOOD_JOBS + 1):
        xml = SPEC_HEAD + cpu_job(f"sim-test-{TOKEN}-durlong-{n:05d}", FLOOD_FRAMES) + "</spec>\n"
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))

    t0 = time.time()
    while time.time() - t0 < SATURATE_WAIT_S:
        u = util_pct()
        if u >= SATURATE_UTIL:
            break
        time.sleep(3)
    print(f"GPUSTRAND: farm at {util_pct():.1f}% after {time.time() - t0:.0f}s; "
          f"submitting the GPU job now.", flush=True)

    xml = SPEC_HEAD + gpu_job(f"sim-test-{TOKEN}gpu-durlong-00001", GPU_FRAMES) + "</spec>\n"
    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))

    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
