"""Generate and submit a realistic job mix over gRPC.

~N jobs, each 2-10 layers; each layer's cores/mem sampled from the real
distribution (sim_model), with a frame range of a VFX "shot" (48-96 frames).
Total demand intentionally oversubscribes the farm so it fills and keeps a
backlog -- exercising placement and reservations under contention.
"""
import os
import sys
import random
import grpc

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
BATCH = sys.argv[1] + "_" if len(sys.argv) > 1 else ""
NUM_JOBS = 50
LAYERS_MIN, LAYERS_MAX = 2, 10
FRAMES_MIN, FRAMES_MAX = 48, 96

SPEC_HEAD = """<?xml version="1.0"?>
<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">
<spec>
  <facility>sim</facility>
  <show>sim</show>
  <shot>test</shot>
  <user>sim</user>
  <uid>9860</uid>
"""


def make_job(idx):
    nlayers = random.randint(LAYERS_MIN, LAYERS_MAX)
    layers = []
    for li in range(nlayers):
        nframes = random.randint(FRAMES_MIN, FRAMES_MAX)
        if sim_model.is_gpu_layer():
            # GPU layer: few cores + 1 GPU + gpu_memory; cpu memory = half the
            # gpu memory. Only GPU-capable hosts can run it (cuebot enforces).
            cores, gpu_mem_kb, cpu_mem_kb = sim_model.gpu_layer_kb()
            mem_kb = cpu_mem_kb
            lname = f"layer{li}_g{cores}"
            gpu_xml = (f"\n        <gpus>1</gpus>"
                       f"\n        <gpu_memory>{int(round(gpu_mem_kb / 1024))}mb</gpu_memory>")
        else:
            cores = sim_model.sample_layer_cores()
            mem_kb = sim_model.reserved_kb_for(cores)   # flat 4 GB/core rule of thumb
            lname = f"layer{li}_c{cores}"
            gpu_xml = ""
        mem_mb = int(round(mem_kb / 1024))
        # Capability tag: a random feasible pool for this layer (else 'general').
        tag = spec.layer_tag(cores, mem_kb) or spec.TAG
        layers.append(f"""      <layer name="{lname}" type="Render">
        <cmd>/bin/true</cmd>
        <range>1-{nframes}</range>
        <chunk>1</chunk>
        <cores>{cores * sim_model.CORE_POINTS}</cores>
        <threadable>{sim_model.THREADABLE}</threadable>
        <memory>{mem_mb}mb</memory>{gpu_xml}
        <tags>{tag}</tags>
        <services><service>shell</service></services>
      </layer>""")
    # Lift the per-job core cap (default 100 cores) so jobs aren't the
    # bottleneck and the farm can actually fill -- we're testing the
    # scheduler, not the default cap.
    return (f'  <job name="sim-test-sim_{BATCH}job{idx:03d}">\n'
            f'    <paused>false</paused>\n    <maxcores>4000</maxcores>\n    <layers>\n'
            + "\n".join(layers) + "\n    </layers>\n  </job>\n")


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=10)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    total_layers = total_frames = total_core_demand = 0
    for i in range(NUM_JOBS):
        random.seed(1000 + i)
        spec = SPEC_HEAD + make_job(i) + "</spec>\n"
        resp = stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=spec))
        # tally demand from the spec we just built
        for line in spec.splitlines():
            line = line.strip()
            if line.startswith("<cores>"):
                cp = int(line[len("<cores>"):-len("</cores>")])
                total_core_demand += cp
            if line.startswith("<range>1-"):
                total_frames += int(line[len("<range>1-"):-len("</range>")])
                total_layers += 1
    print(f"submitted {NUM_JOBS} jobs, {total_layers} layers, {total_frames} frames")
    print(f"core demand: {total_core_demand} cp ({total_core_demand//100} cores) "
          f"vs farm 57248 cores -> {total_core_demand/100/57248:.1f}x")


if __name__ == "__main__":
    main()
