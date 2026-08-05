"""DB-poll frame completion driver for --mode rust (the Rust scheduler).

The Rust scheduler is run with rqd.dry_run_mode=true: it books frames straight
into Postgres -- flips the frame WAITING->STARTED, inserts a proc, decrements the
host's idle cores -- but, being dry-run, it never calls LaunchFrame on an RQD, so
nothing ever reports the frame finished. Left alone the farm fills once and never
drains. This driver supplies the "frame finished" signal that fake_rqd supplies
for the Java path, but it discovers frames from the DB instead of from LaunchFrame
RPCs:

  1. Poll the proc table for scheduler-booked frames (a STARTED frame + proc) we
     have not seen yet.
  2. Sample a run-time from the SAME sim_model used everywhere else and schedule
     the frame for completion that far in the future (a min-heap, one timer
     thread, so thousands of concurrent frames cost no thread each).
  3. When due, send the exact FrameCompleteReport that fake_rqd sends. cuebot's
     FrameCompleteHandler then frees the proc, restores the host's idle cores,
     marks the frame SUCCEEDED, and updates layer_stat/job_stat -- the counters
     the scheduler's next pending-work query reads.

cuebot runs with booking OFF (scheduler.enabled=false + dispatcher.turn_off_booking
=true), so it never dispatches; it is purely the completion/stat engine. This
reuses production frame/stat bookkeeping without re-implementing it, and needs no
RQD gRPC path -- so no /etc/hosts and fully non-root, like the rest of the sim.

Memory-failure simulation mirrors fake_rqd: SIM_MEM_FAILURE_RATE (env or argv[2])
makes that fraction of completions report exit_status=33, so cuebot bumps the
layer memory and requeues the frame; the scheduler re-dispatches it (a new proc,
rediscovered here).

usage: rqd_complete.py [poll_interval_s] [mem_failure_rate]
"""
import os
import sys
import time
import heapq
import random
import threading
import subprocess
from concurrent import futures

import grpc

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import report_pb2, report_pb2_grpc
import host_pb2
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
POLL_INTERVAL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
# exit_status=33 == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
_EXIT_MEM_FAILURE = 33
_MEM_FAILURE_RATE = float(
    sys.argv[2] if len(sys.argv) > 2 else os.environ.get("SIM_MEM_FAILURE_RATE", "0"))
PSQL = spec.psql_cmd(tab=True)

_report = report_pb2_grpc.RqdReportInterfaceStub(grpc.insecure_channel(CUEBOT))
# cuebot finds the proc to free by the report's frame, not by host (fake_rqd uses
# a single dummy host for every completion too), so one dummy host is fine here.
_DUMMY_HOST = report_pb2.RenderHost(
    name="rust-sched-rqd", nimby_locked=False, free_mem=64 * 1024 * 1024,
    state=host_pb2.UP)

_heap = []            # (due_time, seq, RunningFrameInfo)
_seq = 0
_seen = set()         # pk_proc already scheduled -> never schedule twice
_lock = threading.Lock()
_stats = {"discovered": 0, "completed": 0, "mem_failed": 0, "failed": 0}
_report_pool = futures.ThreadPoolExecutor(max_workers=8)


def poll_new():
    """Discover STARTED frames the scheduler booked that we have not scheduled.

    A proc row with a non-null pk_frame is a live booking. The frame is STARTED;
    we only need it to wind down after its modeled run-time. int_cores_reserved is
    core points (100 == 1 core), exactly what sim_model.duration_seconds wants."""
    sql = ("SELECT p.pk_proc, p.pk_frame, p.pk_job, j.str_name, f.str_name, "
           "p.pk_layer, p.int_cores_reserved, p.int_gpus_reserved "
           "FROM proc p "
           "JOIN job j ON j.pk_job=p.pk_job "
           "JOIN frame f ON f.pk_frame=p.pk_frame "
           "WHERE p.pk_frame IS NOT NULL;")
    out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                         timeout=30).stdout
    now = time.time()
    global _seq
    with _lock:
        for line in out.strip().split("\n"):
            if not line:
                continue
            c = line.split("\t")
            if len(c) < 8:
                continue
            proc_id = c[0]
            if proc_id in _seen:
                continue
            _seen.add(proc_id)
            cores = int(c[6])
            dur = sim_model.duration_seconds(cores)
            frame = report_pb2.RunningFrameInfo(
                resource_id=proc_id, job_id=c[2], job_name=c[3],
                frame_id=c[1], frame_name=c[4], layer_id=c[5],
                num_cores=cores, num_gpus=int(c[7]),
                start_time=int(now), rss=512 * 1024, max_rss=512 * 1024)
            heapq.heappush(_heap, (now + dur, _seq, frame))
            _seq += 1
            _stats["discovered"] += 1


def _send_completion(frame):
    mem_fail = _MEM_FAILURE_RATE > 0 and random.random() < _MEM_FAILURE_RATE
    exit_status = _EXIT_MEM_FAILURE if mem_fail else 0
    report = report_pb2.FrameCompleteReport(
        host=_DUMMY_HOST, frame=frame, exit_status=exit_status, exit_signal=0,
        run_time=1)
    try:
        _report.ReportRunningFrameCompletion(
            report_pb2.RqdReportRunningFrameCompletionRequest(
                frame_complete_report=report))
        with _lock:
            if mem_fail:
                _stats["mem_failed"] += 1
            else:
                _stats["completed"] += 1
            # On OOM cuebot requeues the frame; the scheduler re-dispatches it
            # with a NEW proc (new pk_proc), so this old id never recurs and we
            # need not forget it. A failed RPC, though, leaves the proc STARTED
            # in the DB -> forget it so the next poll retries.
    except grpc.RpcError:
        with _lock:
            _stats["failed"] += 1
            _seen.discard(frame.resource_id)


def _completion_loop():
    while True:
        now = time.time()
        due = []
        with _lock:
            while _heap and _heap[0][0] <= now:
                due.append(heapq.heappop(_heap)[2])
        for frame in due:
            _report_pool.submit(_send_completion, frame)
        time.sleep(0.02)


def _stats_loop():
    while True:
        time.sleep(5)
        with _lock:
            pending = len(_heap)
            s = dict(_stats)
        mem = (f" memFailed={s['mem_failed']}" if _MEM_FAILURE_RATE > 0 else "")
        print(f"  [rqd-complete] discovered={s['discovered']} "
              f"completed={s['completed']}{mem} pending={pending} "
              f"failed={s['failed']}", flush=True)


def main():
    grpc.channel_ready_future(grpc.insecure_channel(CUEBOT)).result(timeout=30)
    threading.Thread(target=_completion_loop, daemon=True).start()
    threading.Thread(target=_stats_loop, daemon=True).start()
    mem = (f", mem_failure_rate={_MEM_FAILURE_RATE:.0%}"
           if _MEM_FAILURE_RATE > 0 else "")
    print(f"rqd_complete: polling proc table every {POLL_INTERVAL}s, reporting "
          f"completions to {CUEBOT}{mem}", flush=True)
    while True:
        try:
            poll_new()
        except Exception as e:                      # keep the driver alive
            print(f"  [rqd-complete] poll error: {e}", flush=True)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
