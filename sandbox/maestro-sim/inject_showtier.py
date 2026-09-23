"""SHOWTIER workload: two shows share one allocation by subscription size.

A subscription gives a show a SIZE (its guaranteed share of an allocation)
and a BURST (its ceiling). The legacy dispatcher walks shows lowest tier
first, tier being cores in use over size, so shows with work share an
allocation in proportion to their sizes and a show under its size always
beats a show over it. Maestro's slot lottery draws by job priority alone,
so two shows of equal priority split the allocation in half whatever their
sizes: the small show runs far over its size while the large one sits under.

Small farm, two seeded shows on the one allocation:

  showA   size one quarter of the farm, burst the whole farm
  showB   size three quarters of the farm, burst the whole farm

Both shows get the same flood: JOBS_PER_SHOW jobs of FRAMES one-core frames
at priority 100, token simshowtier, long frames (durlong) so the split holds
still long enough to read. Four jobs per show, because the per-host layer
share (a quarter of each host per layer) caps one layer at 208 frames on this
farm and the large show must be able to reach its 504-core size. All jobs
are submitted paused and released with one UPDATE once every job exists and
every show holds runnable frames, so arrival order decides nothing.

usage: inject_showtier.py [duration_s]
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
JOBS_PER_SHOW = int(os.environ.get("SIM_SHOWTIER_JOBS", "4"))
FRAMES = int(os.environ.get("SIM_SHOWTIER_FRAMES", "4000"))
FRAMES_MIN = 500                  # runnable frames per show before the release
SIZE_FRAC = {"showA": 0.25, "showB": 0.75}
TOKEN = "simshowtier"
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
    for show, frac in SIZE_FRAC.items():
        size = int(round(farm * frac))
        sql(f"UPDATE subscription SET int_size={size}, int_burst={farm}"
            f" WHERE pk_show=(SELECT pk_show FROM show WHERE str_name='{show}');")
        print(f"SHOWTIER: {show} size {size // 100} cores, burst {farm // 100} cores",
              flush=True)

    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    for show in SIZE_FRAC:
        for n in range(1, JOBS_PER_SHOW + 1):
            xml = (spec_head(show)
                   + flood_job(f"sim-test-{TOKEN}-{show}-durlong-{n:05d}", FRAMES)
                   + "</spec>\n")
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"SHOWTIER: {JOBS_PER_SHOW} jobs x {FRAMES} frames per show submitted paused",
          flush=True)

    t0 = time.time()
    deadline = time.time() + 90
    while time.time() < deadline and (jobs() < JOBS_PER_SHOW * len(SIZE_FRAC)
                                      or any(waiting(s) < FRAMES_MIN for s in SIZE_FRAC)):
        time.sleep(2)
    sql(f"UPDATE job SET b_paused=false WHERE str_name LIKE '%{TOKEN}%' AND b_paused=true;")
    print(f"SHOWTIER: released both shows together after {time.time() - t0:.0f}s "
          f"({jobs()} jobs)", flush=True)

    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
