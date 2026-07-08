"""Drain race: submit a FIXED backlog, time until all frames finish.

usage: drain_test.py <label> <njobs> [seedbase]
Submits njobs (deterministic), then polls until waiting+running == 0.
Prints submitted frames and total drain seconds. Same backlog for NEW vs OLD.
"""
import os, sys, time, random, subprocess
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import gen_jobs
import farm_spec as spec

LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"
NJOBS = int(sys.argv[2]) if len(sys.argv) > 2 else 40
SEED  = int(sys.argv[3]) if len(sys.argv) > 3 else 9000
PSQL = spec.psql_cmd()
SHOW = "10000000-0000-0000-0000-000000000003"

def q(sql):
    return subprocess.run(PSQL+["-c",sql], capture_output=True, text=True, timeout=20).stdout.strip()

def main():
    chan = grpc.insecure_channel(spec.GRPC)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    t0 = time.time()
    nframes = 0
    for i in range(NJOBS):
        random.seed(SEED + i)
        spec = gen_jobs.SPEC_HEAD + gen_jobs.make_job(i) + "</spec>\n"
        for line in spec.splitlines():
            ls = line.strip()
            if ls.startswith("<range>1-"):
                nframes += int(ls[len("<range>1-"):ls.index("</range>")])
        try:
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=spec))
        except grpc.RpcError:
            time.sleep(1.0)
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=spec))
    print(f"[{LABEL}] submitted {NJOBS} jobs / ~{nframes} frames", flush=True)
    # poll until drained
    peak_run = 0
    while True:
        s = q(f"SELECT COALESCE(SUM(CASE WHEN f.str_state='WAITING' THEN 1 ELSE 0 END),0), "
              f"COALESCE(SUM(CASE WHEN f.str_state='RUNNING' THEN 1 ELSE 0 END),0), "
              f"COALESCE(SUM(CASE WHEN f.str_state='SUCCEEDED' THEN 1 ELSE 0 END),0) "
              f"FROM frame f JOIN job j ON j.pk_job=f.pk_job WHERE j.pk_show='{SHOW}'")
        try:
            w,r,d = [int(x) for x in s.split("|")]
        except Exception:
            w,r,d = -1,-1,-1
        peak_run = max(peak_run, r)
        el = time.time()-t0
        print(f"[{LABEL}] t={el:6.1f}s waiting={w} running={r} done={d} peakRun={peak_run}", flush=True)
        if d >= nframes and w == 0 and r == 0:
            print(f"[{LABEL}] DRAINED in {el:.1f}s  ({nframes} frames, peak concurrent {peak_run})", flush=True)
            break
        if el > 1200:
            print(f"[{LABEL}] TIMEOUT at {el:.0f}s (done={d}/{nframes})", flush=True)
            break
        time.sleep(2.0)

if __name__ == "__main__":
    main()
