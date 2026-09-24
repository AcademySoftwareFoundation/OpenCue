"""BUDGET workload: subscription size orders the farm, burst lends.

Production budgets a show as a subscription on an allocation: a SIZE, its
guaranteed share, and a BURST, its ceiling. Two rules must hold together:

  size   under contention, shows split the allocation in proportion to
         their sizes (legacy's tier walk): a show under its size beats one
         over it.
  burst  a ceiling only while someone else needs the cores: a show over its
         burst takes what nobody within burst can use, and gives it back as
         its frames finish once another show arrives.

Small farm, four seeded shows on one allocation, equal priority; sizes and
bursts as a share of the farm:

  showA   size 10%, burst 20%
  showB   size 20%, burst 40%
  showC   size 30%, burst 100%
  showD   size 40%, burst 100%

Three phases, long frames (durlong) so the handover is visible:

  1. showA alone: it should fill the farm, far past its burst.
  2. showB, showC and showD arrive at PHASE2_S with the same flood: the
     split should settle at the sizes, 10/20/30/40.
  3. at PHASE3_S their jobs are capped (job max cores) at 10% of the farm
     each: showA takes the leftover, past its burst, and nothing idles.

usage: inject_budget.py [duration_s]
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
JOBS = int(os.environ.get("SIM_BUDGET_JOBS", "6"))
FRAMES = int(os.environ.get("SIM_BUDGET_FRAMES", "3000"))
PHASE2_S = int(os.environ.get("SIM_BUDGET_PHASE2_S", "70"))
PHASE3_S = int(os.environ.get("SIM_BUDGET_PHASE3_S", "190"))
SUBS = {"showA": (0.10, 0.20), "showB": (0.20, 0.40),     # (size, burst) of the farm
        "showC": (0.30, 1.00), "showD": (0.40, 1.00)}
LATE = ("showB", "showC", "showD")
CAP_FRAC = 0.10                                            # per late show in phase 3
TOKEN = "simbudget"
PSQL = spec.psql_cmd()


def spec_head(show):
    return ('<?xml version="1.0"?>\n'
            '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
            f'<spec>\n  <facility>sim</facility>\n  <show>{show}</show>\n  <shot>test</shot>\n'
            '  <user>sim</user>\n  <uid>9861</uid>\n')


def flood_job(name, frames):
    layer = (f'      <layer name="flood" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{sim_model.CORE_POINTS}</cores>'
             f'<threadable>0</threadable><memory>512mb</memory>'
             f'<tags>{spec.TAG}</tags>'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused>'
            f'<priority>100</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{layer}\n    </layers>\n  </job>\n')


def sql(q):
    return subprocess.run(PSQL + ["-c", q], capture_output=True, text=True,
                          timeout=20).stdout.strip()


def submit(stub, show):
    for n in range(1, JOBS + 1):
        xml = (spec_head(show)
               + flood_job(f"sim-test-{TOKEN}-{show}-durlong-{n:05d}", FRAMES)
               + "</spec>\n")
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"BUDGET: {show} submitted {JOBS} jobs x {FRAMES} frames", flush=True)


def main():
    farm = int(sql("SELECT COALESCE(sum(int_cores),0) FROM host;") or 0)
    for show, (size_f, burst_f) in SUBS.items():
        size, burst = int(round(farm * size_f)), int(round(farm * burst_f))
        sql(f"UPDATE subscription SET int_size={size}, int_burst={burst}"
            f" WHERE pk_show=(SELECT pk_show FROM show WHERE str_name='{show}');")
        print(f"BUDGET: {show} size {size // 100}, burst {burst // 100} cores of "
              f"{farm // 100}", flush=True)

    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    t0 = time.time()
    submit(stub, "showA")
    while time.time() - t0 < PHASE2_S:
        time.sleep(1)
    for show in LATE:
        submit(stub, show)
    while time.time() - t0 < PHASE3_S:
        time.sleep(1)
    per_job = int(farm * CAP_FRAC / JOBS)
    for show in LATE:
        sql(f"UPDATE job_resource SET int_max_cores={per_job} WHERE pk_job IN (SELECT pk_job"
            f" FROM job WHERE str_name ILIKE '%{TOKEN}_{show}%');")
    print(f"BUDGET: {', '.join(LATE)} capped at {CAP_FRAC:.0%} of the farm each", flush=True)
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
