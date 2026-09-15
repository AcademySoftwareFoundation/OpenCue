"""PRODENV workload: the limited, tagged, multi-show stream the chaos test stirs.

The standard feeder (started alongside by --feed) keeps the full farm saturated.
This injector adds only what that feeder lacks: layers that carry LIMITS (so the
chaos driver's limit churn binds something) and layers with explicit capability
tags, spread across every show (so subscription and folder churn touch live
work in each of them). Narrow 1-core frames: each running frame is one limit
unit, and cores never bind before the limits do.

Creates three limit_record rows (prodlimA/B/C) up front, the way inject_limit
does, then holds a deep depend-free WAITING backlog of limited frames for the
whole window. prodenv_watch.py mutates the caps; this process only feeds.

usage: inject_prodenv.py [duration_s]
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
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300

LIMITS = {"prodlimA": 150, "prodlimB": 90, "prodlimC": 60}
TARGET = int(os.environ.get("SIM_PRODENV_TARGET", "4000"))
WAVE = 4
LAYERS_MIN, LAYERS_MAX = 3, 5
FRAMES_MIN, FRAMES_MAX = 60, 120
NTAGS = int(os.environ.get("SIM_NTAGS", "8"))
PSQL = spec.psql_cmd()

TOKEN = "simprodenv"
SHOWS = spec.SHOWS or [spec.SHOW]


def spec_head(show):
    return ('<?xml version="1.0"?>\n'
            '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
            f'<spec>\n  <facility>sim</facility>\n  <show>{show}</show>\n'
            '  <shot>test</shot>\n  <user>sim</user>\n  <uid>9860</uid>\n')


def ensure_limits():
    """Create the limit_record rows the layers reference (cuebot resolves
    <limit> by NAME at submit). Idempotent: drop stale copies first."""
    for name, cap in LIMITS.items():
        sql = (f"DELETE FROM layer_limit WHERE pk_limit_record IN "
               f"(SELECT pk_limit_record FROM limit_record WHERE str_name='{name}');"
               f"DELETE FROM limit_record WHERE str_name='{name}';"
               f"INSERT INTO limit_record (pk_limit_record, str_name, int_max_value) "
               f"VALUES (CAST(gen_random_uuid() AS VARCHAR), '{name}', {cap});")
        subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True, timeout=15)
    out = subprocess.run(PSQL + ["-c", "SELECT str_name, int_max_value FROM "
                                       "limit_record WHERE str_name LIKE 'prodlim%';"],
                         capture_output=True, text=True, timeout=10).stdout.strip()
    print(f"limits seeded: {out}", flush=True)


def make_job(name, rng):
    n = rng.randint(LAYERS_MIN, LAYERS_MAX)
    names = list(LIMITS)
    layers = []
    for li in range(n):
        nf = rng.randint(FRAMES_MIN, FRAMES_MAX)
        lim = names[rng.randrange(len(names))]
        tag = f"cap{rng.randrange(NTAGS)}" if rng.random() < 0.5 else spec.TAG
        # DTD order: cmd,range,chunk,cores,threadable,memory,...,tags,limits,...,services
        layers.append(
            f'      <layer name="lyr{li}" type="Render"><cmd>/bin/true</cmd>'
            f'<range>1-{nf}</range><chunk>1</chunk>'
            f'<cores>{sim_model.CORE_POINTS}</cores>'
            f'<threadable>0</threadable><memory>512mb</memory>'
            f'<tags>{tag}</tags>'
            f'<limits><limit>{lim}</limit></limits>'
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
    """Depend-free WAITING frames of the limited layers (live runnable backlog)."""
    return _scalar(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                   f"WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='WAITING' "
                   f"AND f.int_depend_count=0;", int, -1)


def util_pct():
    return _scalar("SELECT COALESCE(100.0*(sum(int_cores)-sum(int_cores_idle))"
                   "/NULLIF(sum(int_cores),0),0) FROM host;", float, -1.0)


def submit_wave(stub, seq):
    for _ in range(WAVE):
        seq += 1
        show = SHOWS[seq % len(SHOWS)]
        xml = (spec_head(show)
               + make_job(f"sim-test-{TOKEN}-{seq:05d}", random.Random(seq * 17))
               + "</spec>\n")
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
    ensure_limits()
    print(f"PRODENV stream: limited+tagged 1-core frames across {len(SHOWS)} shows, "
          f"hold {TARGET} waiting, for {DURATION}s.", flush=True)
    t0 = time.time()
    seq = 0
    while time.time() - t0 < DURATION:
        w = waiting()
        if 0 <= w < TARGET:
            seq = submit_wave(stub, seq)
        print(f"t={time.time()-t0:5.0f}s util={util_pct():5.1f}% waiting={w} "
              f"submitted={seq}", flush=True)
        time.sleep(2.0)
    print(f"injector done: submitted {seq} jobs", flush=True)


if __name__ == "__main__":
    main()
