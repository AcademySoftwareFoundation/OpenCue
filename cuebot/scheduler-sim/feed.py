"""Paced job feeder: keep a sustained backlog so the farm stays oversubscribed.

Submits waves of work to hold ~TARGET runnable frames, backing off on launch-
queue rejection. Realistic mix from sim_model. By default each submission is a
DEPENDENCY TREE of jobs (VFX work is rarely standalone) linked by JOB_ON_JOB
depends; only the root is runnable at submit and descendants unblock as parents
finish (SIM_DEP_TREE_DEPTH, default 3; 1 = independent jobs). Run alongside
stats.py to measure steady-state utilization.

usage: feed.py [duration_s] [target_runnable]
"""
import os, sys, time, random, subprocess
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import sim_model
import farm_spec as spec

CUEBOT = spec.GRPC
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
TARGET = int(sys.argv[2]) if len(sys.argv) > 2 else 40000
WAVE = 6                      # specs per submit burst (launch queue is pool=1/q=100)
LAYERS_MIN, LAYERS_MAX = 2, 10
FRAMES_MIN, FRAMES_MAX = 48, 96
PSQL = spec.psql_cmd()

# Job dependency trees. VFX work is almost never standalone -- a comp waits on a
# render that waits on a sim -- so by default every submission is a TREE of jobs
# linked by JOB_ON_JOB depends DECLARED IN THE SPEC. We only choose the tree
# shape here; cuebot does all the actual dependency work (creates the depend
# records, holds descendant frames in DEPEND, and unblocks them when their parent
# finishes). SIM_DEP_TREE_DEPTH is the max depth (1 = old independent-job
# behaviour); trees are unbalanced (random branching, one spine guarantees depth).
DEP_DEPTH = int(os.environ.get("SIM_DEP_TREE_DEPTH", "3"))
DEP_MAX_BRANCH = int(os.environ.get("SIM_DEP_MAX_BRANCH", "3"))
# Soft ceiling on the backlog (WAITING+DEPEND) so a deep tree pipeline can't grow
# the DB without bound. With deps the *runnable* count is gated by tree structure
# and usually sits well below TARGET, so this pending() check -- not the runnable
# gate -- is what throttles submission. It is soft: cuebot's async launch queue
# is already full of trees when we re-check, so the materialised pile settles
# somewhat above the cap (e.g. ~210k DEPEND on the full farm at 3x40k).
PENDING_CAP = TARGET * 3

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')

def waiting():
    try:
        out = subprocess.run(PSQL+["-c","SELECT count(*) FROM frame WHERE str_state='WAITING' AND int_depend_count=0;"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return int(out)
    except Exception:
        return -1

def make_job(name, rng):
    n = rng.randint(LAYERS_MIN, LAYERS_MAX)
    layers = []
    for li in range(n):
        nf = rng.randint(FRAMES_MIN, FRAMES_MAX)
        if sim_model.is_gpu_layer():
            # GPU layer (honours --gpu): few cores + 1 GPU + gpu_memory; cpu mem
            # = half the gpu mem. Only GPU hosts can run it (cuebot enforces).
            cores, gpu_mem_kb, cpu_mem_kb = sim_model.gpu_layer_kb()
            mem_kb = cpu_mem_kb
            lname = f"l{li}_g{cores}"
            gpu_xml = (f'<gpus>1</gpus>'
                       f'<gpu_memory>{int(round(gpu_mem_kb/1024))}mb</gpu_memory>')
        else:
            cores = sim_model.sample_layer_cores()
            mem_kb = sim_model.reserved_kb_for(cores)   # flat 4 GB/core rule of thumb
            lname = f"l{li}_c{cores}"
            gpu_xml = ""
        mem_mb = int(round(mem_kb/1024))
        # Capability tag: a random feasible pool for this layer (else 'general').
        tag = spec.layer_tag(cores, mem_kb) or spec.TAG
        layers.append(f'      <layer name="{lname}" type="Render">'
            f'<cmd>/bin/true</cmd><range>1-{nf}</range><chunk>1</chunk>'
            f'<cores>{cores*sim_model.CORE_POINTS}</cores><threadable>{sim_model.THREADABLE}</threadable><memory>{mem_mb}mb</memory>'
            f'{gpu_xml}<tags>{tag}</tags><services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused><maxcores>8000</maxcores>\n'
            '    <layers>\n' + "\n".join(layers) + "\n    </layers>\n  </job>\n")

def build_tree(depth, rng):
    """Choose the shape of an unbalanced job tree of max depth `depth`. Returns
    parents[] where parents[i] is the parent index of node i (None for the root,
    node 0). A spine 0->1->...->(depth-1) guarantees the tree actually reaches
    `depth`; each node then gets 0..DEP_MAX_BRANCH random extra children, so
    branches terminate at varying depths (lopsided). This only decides who depends
    on whom -- cuebot does the actual dependency handling."""
    parents, level = [None], [1]
    prev = 0
    for lvl in range(2, depth + 1):          # spine: guarantees max depth
        parents.append(prev); level.append(lvl); prev = len(parents) - 1
    i = 0
    while i < len(parents):                   # hang random extra subtrees off each node
        if level[i] < depth:
            for _ in range(rng.randint(0, DEP_MAX_BRANCH)):
                parents.append(i); level.append(level[i] + 1)
        i += 1
    return parents


def make_tree_spec(base, depth, rng):
    """One spec holding a whole dependency tree: a <job> per node plus a <depends>
    block where every non-root job JOB_ON_JOB-depends on its parent. Submitted
    atomically so the names resolve in-spec; cuebot creates the depends, parks
    descendant frames in DEPEND, and releases them as parents complete."""
    parents = build_tree(depth, rng)
    names = [f"{base}_n{i}" for i in range(len(parents))]
    jobs = "\n".join(make_job(names[i], rng) for i in range(len(parents)))
    deps = "".join(
        f'      <depend type="JOB_ON_JOB"><depjob>{names[i]}</depjob>'
        f'<onjob>{names[p]}</onjob></depend>\n'
        for i, p in enumerate(parents) if p is not None)
    depends_block = f"    <depends>\n{deps}    </depends>\n" if deps else ""
    return SPEC_HEAD + jobs + "\n" + depends_block + "</spec>\n"


def pending():
    """Total backlog frames: runnable (WAITING) + dependency-blocked (DEPEND)."""
    try:
        out = subprocess.run(PSQL+["-c","SELECT count(*) FROM frame WHERE str_state IN ('WAITING','DEPEND');"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return int(out)
    except Exception:
        return -1


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    t0 = time.time(); submitted = 0; seq = 0
    base0 = f"sim-test-sim_f{int(t0)%100000}"
    trees = DEP_DEPTH >= 2
    while time.time()-t0 < DURATION:
        w = waiting()                                   # runnable frames
        p = pending() if trees else w                   # runnable + DEPEND (for the cap)
        if 0 <= w < TARGET and (not trees or p < PENDING_CAP):
            for _ in range(WAVE):
                seq += 1
                name = f"{base0}_{seq:05d}"
                if trees:
                    job_xml = make_tree_spec(name, DEP_DEPTH, random.Random(seq))
                else:
                    job_xml = SPEC_HEAD + make_job(name, random.Random(seq)) + "</spec>\n"
                try:
                    stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=job_xml))
                    submitted += 1
                except grpc.RpcError:
                    time.sleep(2.0)   # launch queue full -> back off
                    break
        extra = f" pending={p}" if trees else ""
        print(f"t={time.time()-t0:5.0f}s waiting={w}{extra} submitted={submitted}", flush=True)
        time.sleep(2.0)
    print(f"feeder done: submitted {submitted} {'trees' if trees else 'jobs'}", flush=True)

if __name__ == "__main__":
    main()
