"""FOLDERTRIG test injector: a folder cap enforced by a site trigger, lowered under load.

Reproduces the 2026-10-13 production stall. Prod enforces folder caps twice: Maestro
plans against folder_resource.int_cores, and a PL/pgSQL trigger on frame raises on a
WAITING -> RUNNING update once the frame's folder has int_cores > int_max_cores. When
the two disagreed, one rejected frame rolled back a whole 500-booking commit chunk
every tick and farm-wide booking froze.

This injector installs that trigger (the 2021 function, fired on the RUNNING
transition only, with an uncapped folder treated as not over cap), creates a second
folder "foldertrig" under the sim show with a core cap, and floods 1-core work into
BOTH folders: half the jobs are moved into the capped folder, the rest stay in the
show's default (uncapped) folder. The companion foldertrig_watch.py lowers the capped
folder's int_max_cores BELOW its live usage mid-run, repeatedly, so the folder is over
its cap while the trigger is armed. A correct Maestro keeps booking the uncapped
folder on every tick, never books the capped folder while it is over, and any booking
the trigger does reject costs only its own host's bookings.

Units are core-points (100 = 1 core); SIM_FOLDERTRIG_MAX is given in CORES.

usage: inject_foldertrig.py [duration_s]
"""
import os, sys, time, random, subprocess, uuid
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180

FOLDER_NAME = "foldertrig"
FOLDER_MAX = int(os.environ.get("SIM_FOLDERTRIG_MAX", "30"))   # cap in CORES
CP = sim_model.CORE_POINTS
TARGET = int(os.environ.get("SIM_FOLDERTRIG_TARGET", "4000"))  # waiting frames per folder
WAVE = 4
LAYERS_MIN, LAYERS_MAX = 2, 4
FRAMES_MIN, FRAMES_MAX = 60, 120
PSQL = spec.psql_cmd()
TOKEN_CAPPED = "simftcap"
TOKEN_FREE = "simftfree"
TRIGGER = "sim_foldertrig_folder_cap"

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')

# The 2021 folder-cap function (commit c2e0406f3), as a site that runs it must have
# amended it: an uncapped folder (int_max_cores = -1) is not over its cap, and the
# check fires only on the start transition, so completions of an over-cap folder
# still land.
TRIGGER_SQL = f"""
CREATE OR REPLACE FUNCTION trigger__update_frame_int_cores() RETURNS TRIGGER AS $body$
DECLARE
    v_int_cores INT;
    v_int_max_cores INT;
    v_pk_folder VARCHAR;
BEGIN
    SELECT pk_folder INTO v_pk_folder FROM job WHERE pk_job = OLD.pk_job;
    SELECT int_cores, int_max_cores INTO v_int_cores, v_int_max_cores
      FROM folder_resource WHERE pk_folder = v_pk_folder;
    IF v_int_max_cores >= 0 AND v_int_cores > v_int_max_cores THEN
        RAISE EXCEPTION 'Job exceeded max folder resources';
    END IF;
    RETURN NEW;
END;
$body$ LANGUAGE PLPGSQL;
DROP TRIGGER IF EXISTS {TRIGGER} ON frame;
CREATE TRIGGER {TRIGGER} BEFORE UPDATE ON frame FOR EACH ROW
    WHEN (OLD.str_state = 'WAITING' AND NEW.str_state = 'RUNNING')
    EXECUTE PROCEDURE trigger__update_frame_int_cores();
"""


def _psql(sql):
    return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True, timeout=30)


def _psql1(sql, cast=str, default=None):
    try:
        out = _psql(sql).stdout.strip()
        return cast(out) if out else default
    except Exception:
        return default


def setup():
    """Install the trigger and create the capped folder beside the show's default one.
    Both folders start clean (reset_db does not touch folder_resource)."""
    r = _psql(TRIGGER_SQL)
    if "ERROR" in (r.stdout + r.stderr):
        print("ERROR installing the folder-cap trigger: "
              + (r.stdout + r.stderr).strip().splitlines()[-1], flush=True)
        return None
    print(f"folder-cap trigger {TRIGGER} installed on frame (WAITING -> RUNNING)", flush=True)
    show = _psql1("SELECT pk_show FROM show WHERE str_name='sim';")
    root, dept = _psql1(f"SELECT pk_folder || '|' || pk_dept FROM folder "
                        f"WHERE b_default=true AND pk_show='{show}';").split("|")
    _psql(f"UPDATE folder_resource SET int_max_cores=-1, int_cores=0, int_gpus=0 "
          f"WHERE pk_folder='{root}';")
    pk = _psql1(f"SELECT pk_folder FROM folder WHERE str_name='{FOLDER_NAME}' "
                f"AND pk_show='{show}';")
    if not pk:
        pk = str(uuid.uuid4())
        _psql(f"INSERT INTO folder (pk_folder, pk_parent_folder, pk_show, str_name, pk_dept) "
              f"VALUES ('{pk}', '{root}', '{show}', '{FOLDER_NAME}', '{dept}');")
    _psql(f"UPDATE folder_resource SET int_max_cores={FOLDER_MAX * CP}, int_cores=0, "
          f"int_gpus=0 WHERE pk_folder='{pk}';")
    got = _psql1(f"SELECT int_max_cores FROM folder_resource WHERE pk_folder='{pk}';")
    print(f"folder {FOLDER_NAME} {pk[:8]} cap set to int_max_cores={got} "
          f"({FOLDER_MAX} cores); default folder {root[:8]} uncapped", flush=True)
    return pk


def make_job(name, rng, paused=False):
    n = rng.randint(LAYERS_MIN, LAYERS_MAX)
    layers = []
    for li in range(n):
        nf = rng.randint(FRAMES_MIN, FRAMES_MAX)
        layers.append(
            f'      <layer name="lyr{li}" type="Render"><cmd>/bin/true</cmd>'
            f'<range>1-{nf}</range><chunk>1</chunk>'
            f'<cores>{CP}</cores>'
            f'<threadable>0</threadable><memory>512mb</memory>'
            f'<tags>{spec.TAG}</tags>'
            f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>{"true" if paused else "false"}</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n    <layers>\n'
            + "\n".join(layers) + "\n    </layers>\n  </job>\n")


def jobs_in(folder_pk):
    return _psql1(f"SELECT count(*) FROM job WHERE pk_folder='{folder_pk}';", int, -1)


def waiting(token):
    return _psql1(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                  f"WHERE j.str_name LIKE '%{token}%' AND f.str_state='WAITING' "
                  f"AND f.int_depend_count=0;", int, -1)


def util_pct():
    return _psql1("SELECT COALESCE(100.0*(sum(int_cores)-sum(int_cores_idle))"
                  "/NULLIF(sum(int_cores),0),0) FROM host;", float, -1.0)


def submit_wave(stub, token, seq, folder_pk):
    """Submit WAVE jobs under token. A job bound for the capped folder is submitted paused,
    moved, then unpaused, so no tick ever plans it from the wrong folder (the candidate
    read skips paused jobs). Cuebot stores the job as show-shot-user_<name with hyphens
    turned to underscores>, so the move matches on the token_sequence suffix."""
    for _ in range(WAVE):
        seq += 1
        name = f"sim-test-{token}-{seq:05d}"
        stored_suffix = f"{token}_{seq:05d}"
        xml = SPEC_HEAD + make_job(name, random.Random(seq * 17 + len(token)),
                                   paused=bool(folder_pk)) + "</spec>\n"
        try:
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
        except grpc.RpcError:
            time.sleep(2.0)
            break
        if folder_pk:
            moved = _psql(f"UPDATE job SET pk_folder='{folder_pk}', b_paused=false "
                          f"WHERE str_name LIKE '%{stored_suffix}';")
            if "UPDATE 1" not in moved.stdout + moved.stderr:
                print(f"WARN: job {name} was not moved into the capped folder: "
                      f"{(moved.stdout + moved.stderr).strip()}", flush=True)
    return seq


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    capped = setup()
    if not capped:
        return
    print(f"FOLDERTRIG test: flood the capped folder ({FOLDER_MAX} cores) and the "
          f"uncapped default folder, {TARGET} waiting each, for {DURATION}s.", flush=True)
    t0 = time.time()
    seq_cap = seq_free = 0
    while time.time() - t0 < DURATION:
        wc = waiting(TOKEN_CAPPED)
        wf = waiting(TOKEN_FREE)
        if 0 <= wc < TARGET:
            seq_cap = submit_wave(stub, TOKEN_CAPPED, seq_cap, capped)
        if 0 <= wf < TARGET:
            seq_free = submit_wave(stub, TOKEN_FREE, seq_free, None)
        print(f"t={time.time()-t0:5.0f}s util={util_pct():5.1f}% waiting capped={wc} "
              f"free={wf} submitted capped={seq_cap} (in folder {jobs_in(capped)}) "
              f"free={seq_free}", flush=True)
        time.sleep(2.0)
    print(f"injector done: submitted {seq_cap} capped + {seq_free} free jobs", flush=True)


if __name__ == "__main__":
    main()
