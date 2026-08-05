"""P2: bootstrap base data + register the farm hosts with cuebot over gRPC.

Talks to cuebot exactly like cueadmin (facility/alloc/show) and like RQD
(ReportRqdStartup) would in real life. No database access.
"""
import os
import sys
import grpc

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)

import facility_pb2, facility_pb2_grpc
import show_pb2, show_pb2_grpc
import report_pb2, report_pb2_grpc
import host_pb2

import farm_spec as spec

CUEBOT = spec.GRPC


def bootstrap(chan):
    """Create facility, default allocation, show and a subscription.

    Idempotent: ignores ALREADY_EXISTS so it can be re-run.
    """
    fac_stub = facility_pb2_grpc.FacilityInterfaceStub(chan)
    alloc_stub = facility_pb2_grpc.AllocationInterfaceStub(chan)
    show_stub = show_pb2_grpc.ShowInterfaceStub(chan)

    def ok(fn, *a, **k):
        try:
            return fn(*a, **k)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.ALREADY_EXISTS:
                return None
            raise

    ok(fac_stub.Create, facility_pb2.FacilityCreateRequest(name=spec.FACILITY))
    facility = fac_stub.Get(
        facility_pb2.FacilityGetRequest(name=spec.FACILITY)).facility

    ok(alloc_stub.Create, facility_pb2.AllocCreateRequest(
        name=spec.ALLOC, tag=spec.TAG, facility=facility))
    alloc = alloc_stub.Find(facility_pb2.AllocFindRequest(
        name=f"{spec.FACILITY}.{spec.ALLOC}")).allocation
    ok(alloc_stub.SetDefault, facility_pb2.AllocSetDefaultRequest(allocation=alloc))

    ok(show_stub.CreateShow, show_pb2.ShowCreateShowRequest(name=spec.SHOW))
    show = show_stub.FindShow(
        show_pb2.ShowFindShowRequest(name=spec.SHOW)).show

    # Huge burst so the show is never the bottleneck (we're testing the
    # scheduler under host contention, not subscription caps).
    ok(show_stub.CreateSubscription, show_pb2.ShowCreateSubscriptionRequest(
        show=show, allocation_id=alloc.id,
        size=float(spec.total_cores()), burst=1e9))

    print(f"  facility={spec.FACILITY} alloc={spec.FACILITY}.{spec.ALLOC} "
          f"(default) show={spec.SHOW} subscription=size/burst={spec.total_cores()} cores")


def register_hosts(chan):
    rqd = report_pb2_grpc.RqdReportInterfaceStub(chan)
    n = 0
    for name, cores, mem_kb in spec.all_hosts():
        core_points = cores * spec.CORES_PER_PROC
        num_gpus, gpu_mem_kb = spec.host_gpu(name, cores, mem_kb)
        render_host = report_pb2.RenderHost(
            name=name,
            facility=spec.FACILITY,
            num_procs=cores,
            cores_per_proc=spec.CORES_PER_PROC,
            total_mem=mem_kb,
            free_mem=mem_kb,
            total_swap=8 * spec.GB_KB,
            free_swap=8 * spec.GB_KB,
            total_mcp=100 * spec.GB_KB,
            free_mcp=100 * spec.GB_KB,
            num_gpus=num_gpus,
            total_gpu_mem=gpu_mem_kb,
            free_gpu_mem=gpu_mem_kb,
            load=0,
            boot_time=1,
            nimby_enabled=False,
            state=host_pb2.UP,
            tags=spec.host_tags(name),
        )
        core_detail = report_pb2.CoreDetail(
            total_cores=core_points, idle_cores=core_points,
            locked_cores=0, booked_cores=0)
        rqd.ReportRqdStartup(report_pb2.RqdReportRqdStartupRequest(
            boot_report=report_pb2.BootReport(host=render_host, core_info=core_detail)))
        n += 1
        if n % 250 == 0:
            print(f"  registered {n}/{spec.total_hosts()} ...")
    print(f"  sent {n} ReportRqdStartup calls")


if __name__ == "__main__":
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=10)
    print("connected to cuebot", CUEBOT)
    # Base entities (facility/alloc/show/subscription) are seeded once via
    # sim_seed.sql (install data). Hosts -- the farm -- register over gRPC.
    print(f"registering {spec.total_hosts()} hosts "
          f"({spec.total_cores()} core-points total):")
    register_hosts(chan)
    print("done.")
