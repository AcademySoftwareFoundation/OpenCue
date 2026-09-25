"""MEMSTRAND workload: cores stranded by memory must show on the dashboard.

Production: a flood of memory-heavy threadable frames, capped at 4 cores by
the layer's max cores, used up host memory and left most idle cores
unusable, yet the stranded-cores gauge read near zero: it counted a host's
whole idle as sellable as soon as any waiting layer fit one frame there.

Small farm, one allocation:

  flood   JOBS jobs of FRAMES threadable frames, 4 cores / 50 GB each (the
          fake RQD reports 50 GB rss via SIM_RSS_PIN), layer max cores 4.
          They fill every host's memory long before its cores.
  light   one 1-core / 1 GB layer that stays waiting: its limit has no seat,
          so it never runs, but it fits every stranded host.

usage: inject_memstrand.py [duration_s]
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
JOBS = int(os.environ.get("SIM_MEMSTRAND_JOBS", "4"))
FRAMES = int(os.environ.get("SIM_MEMSTRAND_FRAMES", "300"))
FLOOD_CORES = 4
FLOOD_MEM_MB = 50 * 1024
TOKEN = "simmemstrand"
LIMIT = "simmemstrandlic"
PSQL = spec.psql_cmd()


def sql(q):
    return subprocess.run(PSQL + ["-c", q], capture_output=True, text=True,
                          timeout=20).stdout.strip()


def head():
    return ('<?xml version="1.0"?>\n'
            '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
            '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
            '  <user>sim</user>\n  <uid>9862</uid>\n')


def job(name, frames, cores, threadable, mem_mb, limit=None):
    # DTD order: cmd,range,chunk,cores,threadable,memory,...,tags,limits,...,services
    lim = f'<limits><limit>{limit}</limit></limits>' if limit else ''
    layer = (f'      <layer name="{name.split("-")[-2]}" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{cores * 100}</cores><threadable>{threadable}</threadable>'
             f'<memory>{mem_mb}mb</memory><tags>{spec.TAG}</tags>{lim}'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused><priority>100</priority>'
            f'<maxcores>80000</maxcores>\n    <layers>\n{layer}\n    </layers>\n  </job>\n')


def main():
    sql(f"DELETE FROM layer_limit WHERE pk_limit_record IN (SELECT pk_limit_record FROM "
        f"limit_record WHERE str_name='{LIMIT}'); DELETE FROM limit_record WHERE "
        f"str_name='{LIMIT}'; INSERT INTO limit_record (pk_limit_record, str_name, "
        f"int_max_value) VALUES (CAST(gen_random_uuid() AS VARCHAR), '{LIMIT}', 0);")
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    t0 = time.time()
    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(
        spec=head() + job(f"sim-test-{TOKEN}-light-00001", 2000, 1, 0, 1024, LIMIT)
        + "</spec>\n"))
    for n in range(1, JOBS + 1):
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(
            spec=head() + job(f"sim-test-{TOKEN}-durlong-flood-{n:05d}", FRAMES, FLOOD_CORES,
                              1, FLOOD_MEM_MB) + "</spec>\n"))
    print(f"MEMSTRAND: {JOBS} flood jobs x {FRAMES} frames ({FLOOD_CORES} cores, "
          f"{FLOOD_MEM_MB // 1024} GB, max {FLOOD_CORES} cores) and one light layer held by a "
          f"0-seat limit", flush=True)
    # The user capped these layers at 4 cores. Launch is asynchronous, so the cap is
    # applied as the jobs appear, and held for the whole run.
    capped = 0
    while time.time() - t0 < DURATION:
        n = sql(f"UPDATE layer SET int_cores_max = {FLOOD_CORES * 100} WHERE pk_job IN (SELECT"
                f" pk_job FROM job WHERE str_name ILIKE '%{TOKEN}%flood%') AND int_cores_max <>"
                f" {FLOOD_CORES * 100} RETURNING pk_layer;")
        capped += len([r for r in n.splitlines() if r.strip() and not r.startswith("UPDATE")])
        time.sleep(2)
    print(f"MEMSTRAND: capped {capped} flood layers at {FLOOD_CORES} cores", flush=True)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
