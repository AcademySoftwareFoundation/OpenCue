"""PARITY test: does the NEW scheduler book exactly what the LEGACY dispatcher books?

The class of bug this hunts: an eligibility gate the two paths implement
DIFFERENTLY, so a job renders under --mode old and silently starves under
--mode new (or the reverse). Host-name tag pinning was one member; the OS
list-vs-exact match and the missing facility gate are two more. Rather than
chase members one at a time, submit a battery of job ARCHETYPES -- each
exercising one gate -- record which of them ever book, and let the verify
layer diff the sets between a --mode old run and a --mode new run. Any
asymmetry, in either direction, fails PARITY_NEW.

Archetypes (1 job = 1 layer, 1-core frames, tiny):
  parity_plain    control: general tags, no os, facility sim. Books everywhere.
  parity_os       <os>rhel9</os> on a farm whose hosts advertise SP_OS
                  "rhel7,rhel9" (SIM_HOST_OS, set by --parity-test): legacy
                  expands host os into str_os IN ('rhel7','rhel9'); an exact
                  string compare books nothing.
  parity_alt      tags "general | util" (the alternation submitters produce
                  for multi-tag layers): must match via 'general' everywhere.
  parity_facother facility 'cloud' while every host sits in facility 'sim'
                  (a cloud.general subscription is ensured so the ONLY
                  differing gate is the facility): legacy refuses it; a
                  scheduler missing the facility gate books it. Asymmetric in
                  the OPPOSITE direction, which parity also fails.

Writes {booked,notbooked} to /tmp/scheduler-sim/parity_booked_<mode>.txt (the
dir outlives per-scenario teardown) and prints one PARITY RESULT line; the
PARITY_OLD/PARITY_NEW verify checks read those.

usage: inject_parity.py [duration_s] [mode]
"""
import os, sys, time, subprocess
import grpc
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "opencue_proto"))
sys.path.insert(0, _HERE)
import job_pb2, job_pb2_grpc
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
MODE = sys.argv[2] if len(sys.argv) > 2 else "unknown"
PSQL = spec.psql_cmd()
OUT_DIR = "/tmp/scheduler-sim"
OUT = f"{OUT_DIR}/parity_booked_{MODE}.txt"

# One os value the multi-OS hosts advertise (SIM_HOST_OS="rhel7,rhel9").
JOB_OS = os.environ.get("SIM_PARITY_JOB_OS", "rhel9")

SPEC_HEAD = ('<?xml version="1.0"?>\n'
  '<!DOCTYPE spec SYSTEM "http://localhost:8080/spcue/dtd/cjsl-1.15.dtd">\n'
  '<spec>\n  <facility>%s</facility>\n  <show>sim</show>\n  <shot>test</shot>\n'
  '  <user>sim</user>\n  <uid>9860</uid>\n')

# (archetype, facility, job-level <os> or None, layer tags)
ARCHETYPES = [
    ("parity_plain",    "sim",   None,   "general"),
    ("parity_os",       "sim",   JOB_OS, "general"),
    ("parity_alt",      "sim",   None,   "general | util"),
    ("parity_facother", "cloud", None,   "general"),
]


def q(sql):
    return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                          timeout=20).stdout.strip()


def ensure_cloud_subscription():
    """Subscribe the sim show to cloud.general so parity_facother's ONLY
    differing gate is the job's facility, not a missing subscription."""
    show = "10000000-0000-0000-0000-000000000003"   # the sim show (sim_seed.sql)
    q("INSERT INTO subscription (pk_subscription, pk_alloc, pk_show, int_size,"
      " int_burst, int_cores, float_tier)"
      f" SELECT CAST(gen_random_uuid() AS VARCHAR), a.pk_alloc, '{show}',"
      "        1000000000, 1000000000, 0, 0"
      " FROM alloc a WHERE a.str_name='cloud.general'"
      " AND NOT EXISTS (SELECT 1 FROM subscription s WHERE s.pk_alloc=a.pk_alloc"
      f"                 AND s.pk_show='{show}');")
    n = q("SELECT count(*) FROM subscription s JOIN alloc a ON a.pk_alloc=s.pk_alloc"
          " WHERE a.str_name='cloud.general';")
    print(f"cloud.general subscriptions: {n}", flush=True)


def job_xml(name, facility, job_os, tags):
    # DTD child order inside <job> is fixed: paused, ..., maxcores, ..., os.
    os_xml = f"    <os>{job_os}</os>\n" if job_os else ""
    return (SPEC_HEAD % facility
        + f'  <job name="{name}">\n'
        + '    <paused>false</paused>\n    <maxcores>4000</maxcores>\n'
        + os_xml
        + '    <layers>\n'
        + '      <layer name="layer0" type="Render">\n'
        + '        <cmd>/bin/true</cmd>\n        <range>1-4</range>\n'
        + '        <chunk>1</chunk>\n        <cores>100</cores>\n'
        + '        <threadable>false</threadable>\n        <memory>512mb</memory>\n'
        + f'        <tags>{tags}</tags>\n'
        + '        <services><service>shell</service></services>\n'
        + '      </layer>\n    </layers>\n  </job>\n</spec>\n')


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    chan = grpc.insecure_channel(spec.GRPC)
    grpc.channel_ready_future(chan).result(timeout=30)
    stub = job_pb2_grpc.JobInterfaceStub(chan)
    ensure_cloud_subscription()
    for name, fac, job_os, tags in ARCHETYPES:
        stub.LaunchSpec(job_pb2.JobLaunchSpecRequest(
            spec=job_xml(name, fac, job_os, tags)))
        print(f"submitted {name} (facility={fac} os={job_os or '-'} "
              f"tags='{tags}')", flush=True)

    booked = {name: False for name, _, _, _ in ARCHETYPES}
    t0 = time.time()
    while time.time() - t0 < DURATION:
        rows = q("SELECT j.str_name,"
                 " COALESCE((SELECT count(*) FROM proc p WHERE p.pk_job=j.pk_job),0),"
                 " COALESCE((SELECT count(*) FROM frame f WHERE f.pk_job=j.pk_job"
                 "           AND f.str_state='SUCCEEDED'),0)"
                 " FROM job j WHERE j.str_name LIKE '%parity%';")
        for r in [x for x in rows.split("\n") if x]:
            jname, procs, done = r.split("|")
            for name in booked:
                if name in jname and (int(procs) > 0 or int(done) > 0):
                    booked[name] = True
        line = " ".join(f"{n}={'B' if b else '-'}" for n, b in sorted(booked.items()))
        print(f"[parity {MODE}] t={time.time()-t0:5.1f}s {line}", flush=True)
        # Every archetype has a verdict once the decided set can no longer
        # change: booked ones stay booked, and the deliberately-unbookable one
        # (facother under legacy) has the whole window to prove us wrong.
        time.sleep(5)

    got = sorted(n for n, b in booked.items() if b)
    not_got = sorted(n for n, b in booked.items() if not b)
    with open(OUT, "w") as f:
        f.write("booked=" + ",".join(got) + "\n")
        f.write("notbooked=" + ",".join(not_got) + "\n")
    print(f"PARITY RESULT mode={MODE} booked=[{','.join(got)}] "
          f"notbooked=[{','.join(not_got)}] -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
