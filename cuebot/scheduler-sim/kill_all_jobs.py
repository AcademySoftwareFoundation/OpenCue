"""Kill all jobs in the sim show (resets the farm: frees procs, host cores)."""
import os
import sys
import grpc

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import farm_spec as spec

chan = grpc.insecure_channel(spec.GRPC)
grpc.channel_ready_future(chan).result(timeout=10)
stub = job_pb2_grpc.JobInterfaceStub(chan)

jobs = stub.GetJobs(job_pb2.JobGetJobsRequest(
    r=job_pb2.JobSearchCriteria(shows=["sim"]))).jobs.jobs
print(f"killing {len(jobs)} jobs ...")
for j in jobs:
    try:
        stub.Kill(job_pb2.JobKillRequest(job=j, username="sim", reason="reset"))
    except grpc.RpcError as e:
        print("  kill failed:", e.code())
print("done")
