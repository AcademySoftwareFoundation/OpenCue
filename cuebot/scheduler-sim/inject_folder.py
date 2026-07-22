"""FOLDER (group/dept core-cap) test: does the scheduler cap a folder's
concurrent cores at folder_resource.int_max_cores?

A folder/group can set a max-core ceiling (e.g. "the comp group gets <= 50
cores"). The legacy dispatcher filters on it (folder_resource.int_cores + layer
cores <= folder_resource.int_max_cores); this test checks whether the E-PVM
scheduler does too. It caps the sim show's default folder and floods narrow work
into it (every sim job lands in that folder), so a scheduler that honors the cap
holds the folder's running cores at <= the cap while one that ignores it runs as
many as the farm allows.

Units are core-points (100 = 1 core); the cap SIM_FOLDER_MAX is given in CORES.

usage: inject_folder.py [duration_s]
"""
import os, sys, time, random, subprocess
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180

FOLDER_MAX = int(os.environ.get("SIM_FOLDER_MAX", "50"))    # cap in CORES
CP = sim_model.CORE_POINTS                                  # core-points per core (100)
TARGET = int(os.environ.get("SIM_FOLDER_TARGET", "6000"))
WAVE = 6
LAYERS_MIN, LAYERS_MAX = 3, 6
FRAMES_MIN, FRAMES_MAX = 60, 120
PSQL = spec.psql_cmd()
TOKEN = "simfolder"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def _psql1(sql, cast=str, default=None):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return cast(out) if out else default
    except Exception:
        return default


def setup_folder_cap():
    """Cap the sim show's DEFAULT folder and zero its running count (reset_db does
    not touch folder_resource, so a prior run could leave it stale). Every sim job
    lands in this folder, so the cap governs the whole show's work."""
    pk = _psql1("SELECT pk_folder FROM folder WHERE b_default=true AND pk_show="
                "(SELECT pk_show FROM show WHERE str_name='sim');")
    if not pk:
        print("ERROR: could not find the sim default folder", flush=True)
        return None
    cp = FOLDER_MAX * CP
    subprocess.run(PSQL + ["-c",
        f"UPDATE folder_resource SET int_max_cores={cp}, int_cores=0, int_gpus=0 "
        f"WHERE pk_folder='{pk}';"], capture_output=True, text=True, timeout=15)
    got = _psql1(f"SELECT int_max_cores FROM folder_resource WHERE pk_folder='{pk}';")
    print(f"folder {pk[:8]} cap set to int_max_cores={got} ({FOLDER_MAX} cores)", flush=True)
    return pk


def make_job(name, rng):
    n = rng.randint(LAYERS_MIN, LAYERS_MAX)
    layers = []
    for li in range(n):
        nf = rng.randint(FRAMES_MIN, FRAMES_MAX)
        layers.append(
            f'      <layer name="lyr{li}" type="Render"><cmd>/bin/true</cmd>'
            f'<range>1-{nf}</range><chunk>1</chunk>'
            f'<cores>{CP}</cores>'                            # 1 core/frame
            f'<threadable>0</threadable><memory>512mb</memory>'
            f'<tags>{spec.TAG}</tags>'
            f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused><priority>100</priority>'
            f'<maxcores>80000</maxcores>\n    <layers>\n'
            + "\n".join(layers) + "\n    </layers>\n  </job>\n")


def waiting():
    return _psql1(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                  f"WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='WAITING' "
                  f"AND f.int_depend_count=0;", int, -1)


def util_pct():
    return _psql1("SELECT COALESCE(100.0*(sum(int_cores)-sum(int_cores_idle))"
                  "/NULLIF(sum(int_cores),0),0) FROM host;", float, -1.0)


def submit_wave(stub, prefix, seq):
    for _ in range(WAVE):
        seq += 1
        xml = SPEC_HEAD + make_job(f"{prefix}-{seq:05d}", random.Random(seq * 17)) + "</spec>\n"
        try:
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
        except grpc.RpcError:
            time.sleep(2.0)
            break
    return seq


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    setup_folder_cap()
    print(f"FOLDER test: flood the sim folder (cap {FOLDER_MAX} cores), hold "
          f"{TARGET} waiting, for {DURATION}s.", flush=True)
    t0 = time.time()
    seq = 0
    while time.time() - t0 < DURATION:
        w = waiting()
        if 0 <= w < TARGET:
            seq = submit_wave(stub, f"sim-test-{TOKEN}", seq)
        print(f"t={time.time()-t0:5.0f}s util={util_pct():5.1f}% waiting={w} submitted={seq}",
              flush=True)
        time.sleep(2.0)
    print(f"injector done: submitted {seq} jobs", flush=True)


if __name__ == "__main__":
    main()
