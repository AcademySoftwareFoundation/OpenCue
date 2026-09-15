"""Priority PROPORTIONALITY test: does completion share track priority across a
spectrum of classes?

Submits N (default 10) statistically identical narrow-job streams that differ
ONLY in priority -- classes at pri 10, 20, ... 100 -- and holds an equal backlog
for each. There is NO pre-fill phase: every class contends from t=0.

CRITICAL: run this against a SMALL farm (simulate.py --hosts, e.g. 25,30,100 =
~5760 cores) so the fixed backlog HEAVILY oversubscribes it (~9x). Heavy
oversubscription is what makes priority visible. The booking loop walks the
candidate layers in lottery (priority-weighted) order and books ~8 frames each
until the scarce free cores run out, so the low-priority TAIL of that ordered list
is cut every tick and shares track priority (Spearman rho ~0.98, near-proportional
to pri/sum(pri)). On the FULL farm the SAME backlog is only ~1.05x oversubscribed:
free cores never run out before the candidate list does, so every class books
every tick and shares flatten to ~1/N (rho ~0.67), making priority look absent.
That flatness is NOT a scheduler bug -- it is what mild oversubscription means.

Under the priority-weighted lottery each class's share of completed frames RISES
with its priority and is near-proportional to pri/sum(pri) through the middle of
the range. It is NOT exactly proportional at the extremes: the lowest classes run
a little OVER their strict share (the lottery floors every class a nonzero
selection chance -- the anti-starvation guarantee) and the highest a little UNDER
(each class holds the SAME backlog, so the top cannot run past its own demand).
priority_spread_watch.py tallies per-class completion share and checks it is
ordered by priority (Spearman rho near 1) -- that is the honest, robust claim.

Jobs are LARGE (many frames) so a job rarely fully completes during the run and
gets archived out of the frame table -- which would bias the per-class SUCCEEDED
counts (high classes complete more, so they would archive more and be undercounted).
Narrow cores + light memory keep it a pure booking-priority test (no reservations,
memory never binds).

Contrast with PRIORITY_STARVING (inject_priority_starve.py): the adversarial
2-class case (a deep HIGH flood) that only asks whether LOW survives.

usage: inject_priority_spread.py [duration_s]
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

# N priority classes, evenly spaced. Default 10 classes at 10,20,...,100.
PRIS = [int(x) for x in
        os.environ.get("SIM_SPREAD_PRIS", "10,20,30,40,50,60,70,80,90,100").split(",")]
# Depend-free WAITING frames held PER CLASS. Against a SMALL farm this fixed
# backlog is a DEEP oversubscription -- 2000 x ~2.5 cores x 10 classes ~= 50k
# core-demand vs a ~5760-core (--hosts 25,30,100) farm => ~9x -- deep enough that
# free cores run out before the lottery-ordered candidate list does, so the
# low-priority tail is cut each tick. That tail-cut is what makes priority visible.
TARGET = int(os.environ.get("SIM_SPREAD_TARGET", "2000"))
WAVE = 4                            # specs per burst (launch queue is pool=1, bounded)
LAYERS_MIN, LAYERS_MAX = 2, 4
FRAMES_MIN, FRAMES_MAX = 150, 300   # LARGE: jobs seldom finish+archive within the run
MAX_CORES = 8                       # narrow (booking, not reservations)
PSQL = spec.psql_cmd()

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>sim</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')


def token(pri):
    """Stable, dash-free per-class token carried in the job name (cuebot turns
    '-' into '_', so keep the class marker separator-free)."""
    return f"prispread{pri:03d}"


def make_job(name, pri, rng):
    n = rng.randint(LAYERS_MIN, LAYERS_MAX)
    layers = []
    for li in range(n):
        nf = rng.randint(FRAMES_MIN, FRAMES_MAX)
        cores = min(MAX_CORES, sim_model.sample_layer_cores())   # realistic narrow mix
        mem_mb = cores * 1024                                    # LIGHT (1 GB/core): never binds
        layers.append(f'      <layer name="lyr{li}_c{cores}" type="Render">'
            f'<cmd>/bin/true</cmd><range>1-{nf}</range><chunk>1</chunk>'
            f'<cores>{cores*sim_model.CORE_POINTS}</cores>'
            f'<threadable>{sim_model.THREADABLE}</threadable><memory>{mem_mb}mb</memory>'
            f'<tags>{spec.TAG}</tags><services><service>shell</service></services></layer>')
    return (f'  <job name="{name}"><paused>false</paused><priority>{pri}</priority>'
            f'<maxcores>80000</maxcores>\n'
            '    <layers>\n' + "\n".join(layers) + "\n    </layers>\n  </job>\n")


def _scalar(sql, cast, default):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=10).stdout.strip()
        return cast(out)
    except Exception:
        return default


def waiting(tok):
    """Depend-free WAITING frames for a class (its live runnable backlog)."""
    return _scalar(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                   f"WHERE j.str_name LIKE '%{tok}%' AND f.str_state='WAITING' "
                   f"AND f.int_depend_count=0;", int, -1)


def util_pct():
    return _scalar("SELECT COALESCE(100.0*(sum(int_cores)-sum(int_cores_idle))"
                   "/NULLIF(sum(int_cores),0),0) FROM host;", float, -1.0)


def submit_wave(stub, prefix, pri, seq):
    """Submit up to WAVE jobs; back off (and stop the wave) on launch-queue reject."""
    for _ in range(WAVE):
        seq += 1
        xml = SPEC_HEAD + make_job(f"{prefix}-{seq:05d}", pri,
                                   random.Random(seq * 7 + pri)) + "</spec>\n"
        try:
            stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(spec=xml))
        except grpc.RpcError:
            time.sleep(2.0)            # launch queue full -> back off, retry next tick
            break
    return seq


def main():
    chan = grpc.insecure_channel(CUEBOT)
    grpc.channel_ready_future(chan).result(timeout=15)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    print(f"PRIORITY-SPREAD test: {len(PRIS)} classes pri={PRIS}, hold {TARGET} "
          f"waiting each (NO prefill -- all contend from t=0), for {DURATION}s.",
          flush=True)
    t0 = time.time()
    seq = {p: 0 for p in PRIS}
    while time.time() - t0 < DURATION:
        for p in PRIS:
            w = waiting(token(p))
            if 0 <= w < TARGET:
                seq[p] = submit_wave(stub, f"sim-test-{token(p)}", p, seq[p])
        print(f"t={time.time()-t0:5.0f}s util={util_pct():5.1f}%  "
              + " ".join(f"p{p}={seq[p]}" for p in PRIS), flush=True)
        time.sleep(2.0)
    print(f"injector done: submitted per class {seq}", flush=True)


if __name__ == "__main__":
    main()
