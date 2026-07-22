"""Host heartbeat: periodically send ReportStatus for every farm host.

Real RQD pings cuebot every ~60s; without it cuebot's monitor ages hosts to
DOWN. We send an empty-frame status report per host on an interval, which
refreshes ts_ping and keeps str_state=UP. Missing frames are never killed by
the handler (it only memory/timeout-checks frames present in a report), so this
is safe for booked frames.
"""
import os
import sys
import time
import grpc

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import report_pb2, report_pb2_grpc
import host_pb2
import farm_spec as spec

CUEBOT = spec.GRPC
INTERVAL = 5.0  # seconds between full ping rounds


def render_host(name, cores, mem_kb):
    return report_pb2.RenderHost(
        name=name, facility=spec.FACILITY,
        num_procs=cores, cores_per_proc=spec.CORES_PER_PROC,
        total_mem=mem_kb, free_mem=mem_kb,
        total_swap=8 * spec.GB_KB, free_swap=8 * spec.GB_KB,
        total_mcp=100 * spec.GB_KB, free_mcp=100 * spec.GB_KB,
        load=0, boot_time=1, nimby_enabled=False,
        state=host_pb2.UP, tags=[spec.TAG])


def ping_round(stub, hosts):
    failed = 0
    for name, cores, mem_kb in hosts:
        cp = cores * spec.CORES_PER_PROC
        report = report_pb2.HostReport(
            host=render_host(name, cores, mem_kb),
            frames=[],   # handler does not kill frames absent from a report
            core_info=report_pb2.CoreDetail(
                total_cores=cp, idle_cores=cp, locked_cores=0, booked_cores=0))
        try:
            stub.ReportStatus(report_pb2.RqdReportStatusRequest(host_report=report))
        except grpc.RpcError:
            failed += 1   # cuebot restarting / transient; keep heartbeating
    return failed


if __name__ == "__main__":
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=10)
    stub = report_pb2_grpc.RqdReportInterfaceStub(chan)
    hosts = list(spec.all_hosts())
    rounds = 0
    while True:
        t0 = time.time()
        failed = ping_round(stub, hosts)
        rounds += 1
        print(f"ping round {rounds}: {len(hosts)} hosts in {time.time()-t0:.1f}s"
              f"{f' ({failed} failed)' if failed else ''}", flush=True)
        time.sleep(INTERVAL)
