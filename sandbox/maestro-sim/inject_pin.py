"""PIN workload: layers pinned to machine lists beside a general flood.

A layer whose tags are host names runs only on those hosts: cuebot tags
every host with its own name at creation, and a layer matches a host when
one of its tags is in the host's tags. That is how a task is sent to a list
of machines, and how a local render is sent to one workstation. Five pinned
jobs of one layer each are submitted at priority 200 against a general flood
at 100 that keeps the farm full, so a pinned layer must win the free cores
of its own hosts:

  one    one small host (a local render)
  pair   two hosts of one capability tag (one host spec)
  span   four hosts across two capability tags (two host specs)
  mixed  one real host and one name that exists nowhere
  dead   two names that exist nowhere, so nothing may ever run

The host lists come from the host table once every host has registered,
and the watcher reads them back from the layers' tags. Pinned frames are
short (durshort), so placement, not run time, decides how many complete.

usage: inject_pin.py [duration_s]
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
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
PIN_FRAMES = int(os.environ.get("SIM_PIN_FRAMES", "30"))
BG_JOBS = int(os.environ.get("SIM_PIN_BG_JOBS", "3"))
BG_FRAMES = int(os.environ.get("SIM_PIN_BG_FRAMES", "3000"))
SATURATE_UTIL = 85.0
SATURATE_WAIT_S = 90
TOKEN = "simpin"
BG_TOKEN = "simpinbg"
PSQL = spec.psql_cmd()

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def one_layer_job(name, frames, tags, priority):
    layer = (f'      <layer name="render" type="Render"><cmd>/bin/true</cmd>'
             f'<range>1-{frames}</range><chunk>1</chunk>'
             f'<cores>{sim_model.CORE_POINTS}</cores>'
             f'<threadable>0</threadable><memory>512mb</memory>'
             f'<tags>{tags}</tags>'
             f'<services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused>'
            f'<priority>{priority}</priority><maxcores>80000</maxcores>\n'
            f'    <layers>\n{layer}\n    </layers>\n  </job>\n')


def q(sql):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip().splitlines()
    except Exception:
        return []


def util_pct():
    rows = q("SELECT sum(int_cores), sum(int_cores - int_cores_idle) FROM host;")
    try:
        total, busy = rows[0].split("|")
        return 100.0 * int(busy or 0) / max(1, int(total or 0))
    except Exception:
        return 0.0


def hosts_by_cap():
    """{cap tag: [host names]} once every farm host has registered."""
    want = spec.total_hosts()
    while True:
        rows = q("SELECT str_name, str_tags FROM host ORDER BY str_name;")
        if len(rows) >= want:
            break
        time.sleep(3)
    out = {}
    for r in rows:
        name, tags = r.split("|", 1)
        cap = next((t for t in tags.split() if t.startswith("cap")), "none")
        out.setdefault(cap, []).append(name)
    return out


def pin_lists(by_cap):
    """Disjoint host lists for the five pinned jobs; see the module doc."""
    caps = sorted(by_cap, key=lambda c: -len(by_cap[c]))
    pool = {c: list(by_cap[c]) for c in caps}
    def take(cap, n, prefer=""):
        names = [h for h in pool[cap] if h.startswith(prefer)] or pool[cap]
        picked = names[:n]
        for h in picked:
            pool[cap].remove(h)
        return picked
    span = take(caps[0], 2) + take(caps[1], 2)
    pair = take(caps[2], 2) if len(caps) > 2 else take(caps[0], 2)
    one = take(caps[-1], 1, prefer="small")
    mixed = take(caps[0], 1) + ["nosuchhost01"]
    dead = ["nosuchhost02", "nosuchhost03"]
    return {"one": one, "pair": pair, "span": span, "mixed": mixed, "dead": dead}


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    lists = pin_lists(hosts_by_cap())
    for i in range(BG_JOBS):
        xml = SPEC_HEAD + one_layer_job(f"sim-test-{BG_TOKEN}{i + 1:02d}-00001", BG_FRAMES,
                                        spec.TAG, 100) + "</spec>\n"
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
    print(f"PIN: {BG_JOBS} background jobs x {BG_FRAMES} general frames submitted; "
          f"waiting for the farm to saturate before the pinned jobs.", flush=True)
    t0 = time.time()
    while time.time() - t0 < SATURATE_WAIT_S and util_pct() < SATURATE_UTIL:
        time.sleep(3)
    print(f"farm at {util_pct():.0f}% util; submitting the pinned jobs.", flush=True)
    for kind, names in lists.items():
        xml = SPEC_HEAD + one_layer_job(f"sim-test-{TOKEN}-{kind}-durshort-00001", PIN_FRAMES,
                                        " | ".join(names), 200) + "</spec>\n"
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
        print(f"PIN {kind}: {PIN_FRAMES} frames pinned to {names}", flush=True)
    while time.time() - t0 < DURATION:
        time.sleep(5)
    print("injector done", flush=True)


if __name__ == "__main__":
    main()
