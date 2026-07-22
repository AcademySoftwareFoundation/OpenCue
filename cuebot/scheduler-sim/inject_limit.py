"""LIMIT (license-cap) test: does the scheduler cap concurrent frames of a limit?

OpenCue's Limits feature (limit_record.int_max_value + layer_limit) caps how many
frames of layers sharing a limit may RUN at once -- the classic "we only have N
licenses" constraint. This injector attaches ONE limit (default `simlic`, cap N)
to every layer it submits and then floods the farm with far more runnable frames
than N, so a scheduler that honors the limit must hold concurrency at <= N while a
scheduler that ignores it will run as many as the cores allow.

The limit is GLOBAL (b_host_limit=false): at most N frames across the whole farm,
regardless of host count. limit_watch.py samples the peak concurrent running count
for the limit and checks it never exceeds N.

usage: inject_limit.py [duration_s]
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

LIMIT_NAME = os.environ.get("SIM_LIMIT_NAME", "simlic")
LIMIT_MAX = int(os.environ.get("SIM_LIMIT_MAX", "50"))   # N: the license cap
# Hold a deep backlog of limited frames -- MANY more than N want to run -- so the
# cap is the only thing that can hold concurrency down. Narrow 1-core layers: each
# running frame is one license unit, and cores never bind before the limit does.
TARGET = int(os.environ.get("SIM_LIMIT_TARGET", "6000"))
WAVE = 6                             # specs per burst (launch queue is pool=1, bounded)
LAYERS_MIN, LAYERS_MAX = 3, 6
FRAMES_MIN, FRAMES_MAX = 60, 120     # long-ish so concurrency accumulates
PSQL = spec.psql_cmd()

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')

TOKEN = "simlimit"


def ensure_limit():
    """Create the limit_record the layers reference (cuebot resolves <limit> by
    NAME at submit, so it must exist first). Idempotent: drop any stale copy and
    its links, then insert a fresh cap=LIMIT_MAX global limit."""
    sql = (f"DELETE FROM layer_limit WHERE pk_limit_record IN "
           f"(SELECT pk_limit_record FROM limit_record WHERE str_name='{LIMIT_NAME}');"
           f"DELETE FROM limit_record WHERE str_name='{LIMIT_NAME}';"
           f"INSERT INTO limit_record (pk_limit_record, str_name, int_max_value, b_host_limit) "
           f"VALUES (CAST(gen_random_uuid() AS VARCHAR), '{LIMIT_NAME}', {LIMIT_MAX}, false);")
    subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True, timeout=15)
    out = subprocess.run(PSQL + ["-c", f"SELECT int_max_value FROM limit_record "
                                       f"WHERE str_name='{LIMIT_NAME}';"],
                         capture_output=True, text=True, timeout=10).stdout.strip()
    print(f"limit '{LIMIT_NAME}' cap={out} (global)", flush=True)


def make_job(name, rng):
    n = rng.randint(LAYERS_MIN, LAYERS_MAX)
    layers = []
    for li in range(n):
        nf = rng.randint(FRAMES_MIN, FRAMES_MAX)
        # DTD order: cmd,range,chunk,cores,threadable,memory,...,tags,limits,...,services
        layers.append(
            f'      <layer name="lyr{li}" type="Render"><cmd>/bin/true</cmd>'
            f'<range>1-{nf}</range><chunk>1</chunk>'
            f'<cores>{sim_model.CORE_POINTS}</cores>'            # 1 core = 1 license unit
            f'<threadable>0</threadable><memory>512mb</memory>'
            f'<tags>{spec.TAG}</tags>'
            f'<limits><limit>{LIMIT_NAME}</limit></limits>'
            f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused><priority>100</priority>'
            f'<maxcores>80000</maxcores>\n    <layers>\n'
            + "\n".join(layers) + "\n    </layers>\n  </job>\n")


def _scalar(sql, cast, default):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=10).stdout.strip()
        return cast(out)
    except Exception:
        return default


def waiting():
    """Depend-free WAITING frames of the limited layers (the live runnable backlog)."""
    return _scalar(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                   f"WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='WAITING' "
                   f"AND f.int_depend_count=0;", int, -1)


def util_pct():
    return _scalar("SELECT COALESCE(100.0*(sum(int_cores)-sum(int_cores_idle))"
                   "/NULLIF(sum(int_cores),0),0) FROM host;", float, -1.0)


def submit_wave(stub, prefix, seq):
    for _ in range(WAVE):
        seq += 1
        xml = SPEC_HEAD + make_job(f"{prefix}-{seq:05d}", random.Random(seq * 13)) + "</spec>\n"
        try:
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
        except grpc.RpcError:
            time.sleep(2.0)            # launch queue full -> back off, retry next tick
            break
    return seq


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    ensure_limit()
    print(f"LIMIT test: flood the farm with '{LIMIT_NAME}'-limited frames "
          f"(cap {LIMIT_MAX}), hold {TARGET} waiting, for {DURATION}s.", flush=True)
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
