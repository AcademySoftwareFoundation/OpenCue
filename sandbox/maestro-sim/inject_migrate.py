"""MIGRATE workload: one show on Maestro, five shows on the legacy dispatcher.

The rollout topology: three cuebots share one database, one farm and the
host and completion reports, each host pinned to one of them and its
completions with it, as an RQD behind a service registry. Cuebots 0 and 1
run the legacy dispatcher
(maestro.enabled=no). Cuebot 2 runs Maestro in managed mode
(maestro.enabled=managed): it plans the one flagged show on its tick and, on
the reports it receives, still books the five legacy shows like the other
two. The legacy dispatch query excludes flagged shows and Maestro's candidate
query takes only them, so the two dispatchers partition the shows by
construction; this load and its watcher prove that they do, and that both
sides make progress on one farm.

Six seeded shows share the one allocation. Every subscription is set to one
sixth of the farm with the whole farm as burst, so neither dispatcher is held
by a show cap and the split is the dispatchers' own. Every show gets the same
flood: JOBS_PER_SHOW jobs of FRAMES one-core frames at priority 100, token
simmigrate, submitted paused and released with one UPDATE once every job
exists, so arrival order decides nothing. The backlog is far deeper than the
farm for the whole run.

usage: inject_migrate.py [duration_s]
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
MANAGED = os.environ.get("SIM_MIGRATE_SHOW", "showA")
SHOWS = [MANAGED] + [s for s in ("sim", "showA", "showB", "showC", "showD", "showE")
                     if s != MANAGED]
JOBS_PER_SHOW = int(os.environ.get("SIM_MIGRATE_JOBS", "2"))
FRAMES = int(os.environ.get("SIM_MIGRATE_FRAMES", "3000"))
FRAMES_MIN = 500                  # runnable frames per show before the release
TOKEN = "simmigrate"
PSQL = spec.psql_cmd()


def spec_head(show):
    return ('<?xml version="1.0"?>\n'
            '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
            f'<spec>\n  <facility>sim</facility>\n  <show>{show}</show>\n  <shot>test</shot>\n'
            '  <user>sim</user>\n  <uid>9860</uid>\n')


def flood_job(name, frames):
    layer = (f'      <layer name="flood" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{sim_model.CORE_POINTS}</cores>'
             f'<threadable>0</threadable><memory>512mb</memory>'
             f'<tags>{spec.TAG}</tags>'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>true</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{layer}\n    </layers>\n  </job>\n')


def sql(q):
    return subprocess.run(PSQL + ["-c", q], capture_output=True, text=True,
                          timeout=20).stdout.strip()


def jobs():
    out = sql(f"SELECT count(*) FROM job WHERE str_name LIKE '%{TOKEN}%';")
    return int(out) if out.isdigit() else 0


def waiting(show):
    out = sql("SELECT count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job"
              " JOIN show s ON s.pk_show=j.pk_show"
              f" WHERE s.str_name='{show}' AND j.str_name LIKE '%{TOKEN}%'"
              " AND f.str_state='WAITING';")
    return int(out) if out.isdigit() else 0


def main():
    farm = int(sql("SELECT COALESCE(sum(int_cores),0) FROM host;") or 0)
    size = farm // len(SHOWS)
    for show in SHOWS:
        sql(f"UPDATE subscription SET int_size={size}, int_burst={farm}"
            f" WHERE pk_show=(SELECT pk_show FROM show WHERE str_name='{show}');")
    flagged = sql("SELECT string_agg(str_name, ',') FROM show WHERE b_scheduler_managed;")
    print(f"MIGRATE: {len(SHOWS)} shows, size {size // 100} cores each, burst {farm // 100};"
          f" managed (Maestro): {flagged or 'NONE'}; legacy: "
          + ",".join(SHOWS[1:]), flush=True)

    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    for show in SHOWS:
        for n in range(1, JOBS_PER_SHOW + 1):
            xml = (spec_head(show)
                   + flood_job(f"sim-test-{TOKEN}-{show}-{n:05d}", FRAMES)
                   + "</spec>\n")
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"MIGRATE: {JOBS_PER_SHOW} jobs x {FRAMES} frames per show submitted paused",
          flush=True)

    t0 = time.time()
    deadline = time.time() + 90
    while time.time() < deadline and (jobs() < JOBS_PER_SHOW * len(SHOWS)
                                      or any(waiting(s) < FRAMES_MIN for s in SHOWS)):
        time.sleep(2)
    sql(f"UPDATE job SET b_paused=false WHERE str_name LIKE '%{TOKEN}%' AND b_paused=true;")
    print(f"MIGRATE: released all shows together after {time.time() - t0:.0f}s "
          f"({jobs()} jobs)", flush=True)

    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
