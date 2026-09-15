"""DOUBLERENDER workload: reproduce the stale-release double render.

The release-path defect (found by audit, verified against the code): a stale
lostProc call — maintenance walking a minutes-old proc list, or any caller
holding a stale VirtualProc — stops a frame that has ALREADY been released
and rebooked. The stop is unfenced: it re-fetches the frame fresh, so the
version guard passes against the NEW run. The frame flips to WAITING while
its new host still renders; the scheduler's orphan sweep then deletes the
new proc WITHOUT any RQD kill, and the next tick books the frame on yet
another host. Two hosts render the same frame.

NO cuebot code is modified to induce this. The stale lostProc's entire
effect on the world is one SQL statement (UPDATE_FRAME_STOPPED_NORSS with a
passing guard); this injector performs exactly that statement against a
handful of RUNNING frames. Everything downstream — the kill-less sweep, the
rebook, the second launch — is real, unmodified cuebot behavior. fake_rqd
detects the crime: one server receives every host's launches, so a launch
for a frame whose first copy is still alive prints DOUBLE LAUNCH.

The job name carries "durlong" so fake_rqd runs each frame 120s: long
enough that the first copy is guaranteed alive when the relaunch arrives.

usage: inject_doublerender.py [duration_s]
"""
import os, subprocess, sys, time
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 240
FRAMES = int(os.environ.get("SIM_DOUBLERENDER_FRAMES", "240"))
FLIPS = int(os.environ.get("SIM_DOUBLERENDER_FLIPS", "5"))
# The sweep takes procs booked >10s ago whose frame is not RUNNING; only flip
# frames comfortably past that so the corpse is sweep-eligible immediately.
MIN_PROC_AGE_S = 15
TOKEN = "simdoublerender"
PSQL = spec.psql_cmd()

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def rows(sql):
    out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                         timeout=15).stdout.strip()
    return [ln.split("|") for ln in out.splitlines() if ln]


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    lay = (f'      <layer name="render" type="Render"><cmd>/bin/true</cmd>'
           f'<range>1-{FRAMES}</range><chunk>1</chunk><cores>100</cores>'
           f'<threadable>0</threadable><memory>2048mb</memory>'
           f'<tags>{spec.TAG}</tags>'
           f'<services><service>shell</service></services></layer>')
    body = (f'  <job name="sim-test-{TOKEN}-durlong-00001">'
            f'<paused>false</paused><priority>100</priority>'
            f'<maxcores>80000</maxcores>\n'
            f'    <layers>\n{lay}\n    </layers>\n  </job>\n')
    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=SPEC_HEAD + body
                                                 + "</spec>\n"))
    print(f"DOUBLERENDER: {FRAMES} long (120s) frames submitted; will flip "
          f"{FLIPS} RUNNING frames to WAITING with the exact unfenced-stop "
          f"statement once their procs are {MIN_PROC_AGE_S}s old.", flush=True)

    t0 = time.time()
    flipped = 0
    while time.time() - t0 < DURATION:
        if flipped < FLIPS:
            picks = rows(
                f"SELECT f.pk_frame, p.pk_proc, h.str_name FROM frame f "
                f"JOIN proc p ON p.pk_frame = f.pk_frame "
                f"JOIN host h ON h.pk_host = p.pk_host "
                f"JOIN job j ON j.pk_job = f.pk_job "
                f"WHERE j.str_name LIKE '%{TOKEN}%' "
                f"AND f.str_state = 'RUNNING' "
                f"AND p.ts_booked < now() - interval '{MIN_PROC_AGE_S} "
                f"seconds' LIMIT {FLIPS - flipped};")
            for pk_frame, pk_proc, host in picks:
                # The stale lostProc's stop, verbatim in effect: state flip +
                # version bump, guard on RUNNING. The proc row is left behind
                # exactly as the unfenced caller leaves it (its delete no-ops
                # on the stale handle; this proc is the NEW run's).
                r = rows(f"UPDATE frame SET str_state = 'WAITING', "
                         f"ts_stopped = current_timestamp, "
                         f"ts_updated = current_timestamp, "
                         f"int_exit_status = 1, "
                         f"int_version = int_version + 1 "
                         f"WHERE pk_frame = '{pk_frame}' "
                         f"AND str_state = 'RUNNING' RETURNING pk_frame;")
                if r:
                    flipped += 1
                    print(f"FLIPPED frame={pk_frame} proc={pk_proc} "
                          f"host={host}", flush=True)
        time.sleep(3)
    print(f"injector done ({flipped} flips)", flush=True)


if __name__ == "__main__":
    main()
