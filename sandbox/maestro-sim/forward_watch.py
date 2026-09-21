"""FORWARD watcher: the completion-forward relay on the isolated-leader topology.

Three cuebots, one farm, one managed show -- but unlike MIGRATE the managed
cuebot (instance 2) is EXCLUDED from the report spread: no RQD knows its
address, the isolated-deployment topology. The two legacy cuebots forward the
managed show's FrameCompleteReports to it (maestro.forward_completions_to),
so its completion drain files them; every forward failure processes the
report locally through the legacy path. Cuebot 0 forwards with the default
deadline (the steady arm); cuebot 1 forwards with a deadline far below the
ACK latency (the ambiguity arm: timed-out-but-delivered forwards
double-process, and the version-guarded stop must resolve every race).
Mid-run the harness SIGKILLs the managed cuebot for one outage window and
restarts it (the kill-switch arm).

The invariants, sampled from the database, the legacy cuebots' forward
counters (cue_completion_forward_total on :8080 / :8081), Maestro's own
counters on :8082, and the managed cuebot's stat log (drained=N):

  1. Forwarding carries the show (fail-first). The legacy cuebots' forwarded
     counters and the managed cuebot's drained count both clear their floors.
     Without the feature or its flag both sit at zero and the scenario FAILS.
  2. Steady health. Before the kill, cuebot 0's fallbacks stay near zero:
     forwarding is the normal path, not a coin flip.
  3. Partition. Every managed-show start was Maestro's (counter-reset-aware
     across the restart); Maestro books no legacy show. Legacy shows
     complete normally.
  4. Kill switch. While the managed cuebot is down the managed show keeps
     completing (local fallback), cuebot 0's breaker engages
     (fallback_breaker rises), and after the restart forwarding resumes.
     No report is ever lost: reports land on the always-up legacy cuebots.
     Completions the dead leader had ACKed but not yet drained stay RUNNING
     until reconciliation (the documented crash contract); strays first seen
     in that window are reported, not judged.
  5. Effectively-once. No frame is ever launched twice (fake_rqd's DOUBLE
     LAUNCH line), and outside the crash window no run identity stays stray:
     every double-processed ambiguous forward lost its race cleanly.

PASS      : all of the above hold.
FAIL      : forwarding never carried the show, fallbacks under steady state,
            a cross-booking, a starved side, a dead breaker, no resumption,
            an orphan outside the crash window, or a double launch.
INCONCLUSIVE: the farm never filled, or the metrics never answered.

usage: forward_watch.py [duration_s] [interval_s] [fake_rqd log] [kill_at_s] [outage_s]
"""
import os, re, subprocess, sys, time, urllib.request
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
RQD_LOG = sys.argv[3] if len(sys.argv) > 3 else ""
KILL_AT = int(sys.argv[4]) if len(sys.argv) > 4 else 0      # 0 = no kill-switch arm
OUTAGE = int(sys.argv[5]) if len(sys.argv) > 5 else 60

MANAGED = os.environ.get("SIM_MIGRATE_SHOW", "showA")
LEGACY = [s for s in ("sim", "showA", "showB", "showC", "showD", "showE") if s != MANAGED]
TOKEN = "simmigrate"
METRICS = {i: f"http://localhost:{8080 + i}/metrics" for i in range(3)}
CUEBOT2_LOG = os.environ.get("SIM_CUEBOT_LOG", "/tmp/cuebot-old.log").replace(
    ".log", "-2.log")
ORPHAN_AGE_S = 30.0
# The restart truncates the managed cuebot's log and resets its counters;
# strays born from KILL_AT until the restarted instance has settled are the
# documented ACKed-but-undrained crash loss, reported but not judged.
CRASH_GRACE_S = 120.0
MIN_UTIL = 85.0
MIN_DONE_MANAGED = 100
MIN_DONE_EACH = 20
MIN_FORWARDED = 100
MIN_DRAINED = 50
MIN_DONE_OUTAGE = 20
MIN_AMBIG_ATTEMPTS = 10
STEADY_FALLBACK_TOL = 20
PSQL = spec.psql_cmd()


def q(sql):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip().splitlines()
    except Exception:
        return []


def counts_by_show():
    """{show: [running, succeeded, dead, waiting]} for the flood jobs."""
    out = {}
    for r in q("SELECT s.str_name,"
               " sum(CASE WHEN f.str_state='RUNNING' THEN 1 ELSE 0 END),"
               " sum(CASE WHEN f.str_state='SUCCEEDED' THEN 1 ELSE 0 END),"
               " sum(CASE WHEN f.str_state='DEAD' THEN 1 ELSE 0 END),"
               " sum(CASE WHEN f.str_state='WAITING' THEN 1 ELSE 0 END)"
               " FROM frame f JOIN job j ON j.pk_job=f.pk_job"
               " JOIN show s ON s.pk_show=j.pk_show"
               f" WHERE j.str_name LIKE '%{TOKEN}%' GROUP BY s.str_name;"):
        name, running, done, dead, wait = r.split("|")
        out[name] = [int(running), int(done), int(dead), int(wait)]
    return out


def strays():
    """Run identities out of step: procs whose frame is gone or not RUNNING,
    and RUNNING flood frames without a proc."""
    procs = q("SELECT p.pk_proc FROM proc p LEFT JOIN frame f ON f.pk_frame=p.pk_frame"
              " WHERE f.pk_frame IS NULL OR f.str_state<>'RUNNING';")
    frames = q("SELECT f.pk_frame FROM frame f JOIN job j ON j.pk_job=f.pk_job"
               " LEFT JOIN proc p ON p.pk_frame=f.pk_frame"
               f" WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='RUNNING'"
               " AND p.pk_proc IS NULL;")
    return set(procs) | set(frames)


def util():
    rows = q("SELECT round(100.0 * sum(int_cores - int_cores_idle) / sum(int_cores), 1)"
             " FROM host;")
    return float(rows[0]) if rows and rows[0].strip() else 0.0


def metrics_text(instance):
    try:
        return urllib.request.urlopen(METRICS[instance], timeout=5).read().decode()
    except Exception:
        return None


def forward_counts(body):
    """{outcome: n} from cue_completion_forward_total; {} when absent."""
    out = {}
    if body:
        for m in re.finditer(
                r'cue_completion_forward_total\{[^}]*outcome="([^"]+)"[^}]*\}\s+([0-9.eE+]+)',
                body):
            out[m.group(1)] = out.get(m.group(1), 0) + int(float(m.group(2)))
    return out


def maestro_booked(body):
    """{show: frames} from Maestro's dispatch counter; {} while it is not up."""
    out = {}
    if body:
        for m in re.finditer(
                r'cue_maestro_frames_dispatched_total\{[^}]*show="([^"]+)"[^}]*\}\s+([0-9.eE+]+)',
                body):
            out[m.group(1)] = out.get(m.group(1), 0) + int(float(m.group(2)))
    return out


class ResetCounters:
    """Accumulate per-key monotonic counters across a process restart (a
    sampled value below the last seen one means the counter was reset)."""

    def __init__(self):
        self.base = {}
        self.last = {}

    def sample(self, cur):
        for k, v in cur.items():
            if v < self.last.get(k, 0):
                self.base[k] = self.base.get(k, 0) + self.last[k]
            self.last[k] = v

    def total(self, k):
        return self.base.get(k, 0) + self.last.get(k, 0)


class DrainTail:
    """Sum drained=N from the managed cuebot's 'Maestro stat:' lines,
    tailing the log incrementally and surviving the restart's truncation."""

    def __init__(self, path):
        self.path = path
        self.offset = 0
        self.total = 0

    def poll(self):
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return self.total
        if size < self.offset:
            self.offset = 0
        try:
            with open(self.path, errors="ignore") as f:
                f.seek(self.offset)
                chunk = f.read()
                self.offset = f.tell()
        except OSError:
            return self.total
        for m in re.finditer(r"Maestro stat:.*\bdrained=(\d+)", chunk):
            self.total += int(m.group(1))
        return self.total


def double_launches():
    if not RQD_LOG:
        return 0
    try:
        return sum(1 for l in open(RQD_LOG, errors="ignore") if "DOUBLE LAUNCH" in l)
    except Exception:
        return 0


def main():
    print(f"watching FORWARD for {DURATION}s: {MANAGED} managed on the isolated cuebot 2 "
          f"(no RQD reports it), legacy cuebots 0 and 1 forward its completions there "
          f"(cuebot 1 with an ambiguity-arm deadline); kill-switch arm at t={KILL_AT}s "
          f"for {OUTAGE}s. PASS needs forwarding to carry the show, near-zero steady "
          f"fallbacks on cuebot 0, no cross-booking, breaker fallback + resumption "
          f"around the outage, no orphan outside the crash window, no double launch.\n",
          flush=True)
    t0 = time.time()
    peak_util = 0.0
    booked = ResetCounters()
    drain = DrainTail(CUEBOT2_LOG)
    first_seen = {}
    orphans = 0
    crash_strays = 0
    metrics_seen = False
    dbl0 = double_launches()

    # Phase snapshots (filled as the run crosses its marks). The resume
    # snapshot is taken at the first sample where the restarted managed
    # cuebot answers its metrics again, so the resume window is measured
    # from actual readiness, not a guessed startup time.
    steady = None          # (fwd0, managed_done) last sample before the kill mark
    resume_snap = None     # (fwd0, managed_done) once cuebot 2 is back
    kill_end = KILL_AT + OUTAGE if KILL_AT else 0
    grace_end = kill_end + CRASH_GRACE_S if KILL_AT else 0

    while time.time() - t0 < DURATION:
        t = time.time() - t0
        u = util()
        peak_util = max(peak_util, u)
        c = counts_by_show()
        m = c.get(MANAGED, [0, 0, 0, 0])
        leg_done = sum(c[s][1] for s in LEGACY if s in c)
        f0 = forward_counts(metrics_text(0))
        f1 = forward_counts(metrics_text(1))
        m2 = metrics_text(2)
        if m2 is not None:
            metrics_seen = True
            booked.sample(maestro_booked(m2))
        drained = drain.poll()

        now = time.time()
        cur = strays()
        first_seen = {k: first_seen.get(k, now) for k in cur}
        in_crash_window = lambda seen: KILL_AT and KILL_AT - 10 <= seen - t0 <= grace_end
        aged = sum(1 for seen in first_seen.values()
                   if now - seen > ORPHAN_AGE_S and not in_crash_window(seen))
        crash_strays = max(crash_strays, sum(1 for seen in first_seen.values()
                                             if in_crash_window(seen)))
        orphans = max(orphans, aged)

        # The killer thread's clock starts slightly before this watcher's, so
        # the kill can land just before t reaches KILL_AT; keep the steady
        # snapshot strictly clear of it by re-taking it only well before the
        # mark, leaving kill-moment fallbacks to the outage phase.
        if KILL_AT and t < KILL_AT - 10:
            steady = (dict(f0), m[1])
        if KILL_AT and resume_snap is None and t > kill_end and m2 is not None:
            resume_snap = (dict(f0), m[1])

        print(f"t={t:5.0f} | util {u:5.1f}% | {MANAGED}: run {m[0]:4d} done {m[1]:5d} "
              f"booked {booked.total(MANAGED):5d} drained {drained:5d} | "
              f"legacy done {leg_done:5d} | fwd0 {f0.get('forwarded', 0):5d} "
              f"err0 {f0.get('fallback_error', 0):3d} brk0 {f0.get('fallback_breaker', 0):4d} | "
              f"fwd1 {f1.get('forwarded', 0):5d} err1 {f1.get('fallback_error', 0):4d} "
              f"brk1 {f1.get('fallback_breaker', 0):4d} | stray {len(cur):3d} "
              f"orphans {aged:d} | double {double_launches() - dbl0}", flush=True)
        time.sleep(INTERVAL)

    c = counts_by_show()
    m = c.get(MANAGED, [0, 0, 0, 0])
    started = m[0] + m[1] + m[2]
    f0 = forward_counts(metrics_text(0))
    f1 = forward_counts(metrics_text(1))
    m2 = metrics_text(2)
    if m2 is not None:
        metrics_seen = True
        booked.sample(maestro_booked(m2))
    drained = drain.poll()
    booked_managed = booked.total(MANAGED)
    cross_legacy = max(0, started - booked_managed)
    cross_maestro = sum(booked.total(s) for s in LEGACY)
    leg_done = {s: c.get(s, [0, 0, 0, 0])[1] for s in LEGACY}
    dbl = double_launches() - dbl0
    forwarded = f0.get("forwarded", 0) + f1.get("forwarded", 0)
    ambig_attempts = f1.get("forwarded", 0) + f1.get("fallback_error", 0)

    steady_fallbacks = None
    breaker_hits = None
    outage_done = None
    resumed_fwd = None
    if KILL_AT and steady is not None:
        steady_fallbacks = (steady[0].get("fallback_error", 0)
                            + steady[0].get("fallback_breaker", 0))
        if resume_snap is not None:
            breaker_hits = (resume_snap[0].get("fallback_breaker", 0)
                            - steady[0].get("fallback_breaker", 0))
            outage_done = resume_snap[1] - steady[1]
            resumed_fwd = f0.get("forwarded", 0) - resume_snap[0].get("forwarded", 0)

    print("\n==== FORWARD VERDICT ====", flush=True)
    print(f"forward: managed {MANAGED} started {started} done {m[1]} "
          f"(Maestro booked {booked_managed}, drained {drained}), forwarded {forwarded} "
          f"(cuebot0 {f0.get('forwarded', 0)}/err {f0.get('fallback_error', 0)}"
          f"/brk {f0.get('fallback_breaker', 0)}, ambiguity cuebot1 "
          f"{f1.get('forwarded', 0)}/err {f1.get('fallback_error', 0)}"
          f"/brk {f1.get('fallback_breaker', 0)}), steady fallbacks "
          f"{steady_fallbacks}, outage done {outage_done} breaker hits {breaker_hits} "
          f"resumed fwd {resumed_fwd}, crash-window strays {crash_strays}, legacy done "
          f"{sum(leg_done.values())} ({', '.join(f'{s} {n}' for s, n in leg_done.items())}), "
          f"cross-bookings {cross_legacy}/{cross_maestro}, orphans {orphans}, "
          f"double launches {dbl}, peak util {peak_util:.1f}%", flush=True)

    if not metrics_seen:
        print("INCONCLUSIVE: the managed cuebot's metrics never answered; is cuebot 2 "
              "up in managed mode?", flush=True)
    elif peak_util < MIN_UTIL:
        print(f"INCONCLUSIVE: the farm only reached {peak_util:.1f}% (< {MIN_UTIL}%), so "
              f"the topology was not contended.", flush=True)
    elif m[1] < MIN_DONE_MANAGED:
        print(f"FAIL: the managed show completed only {m[1]} frames "
              f"(< {MIN_DONE_MANAGED}).", flush=True)
    elif forwarded < MIN_FORWARDED:
        print(f"FAIL: only {forwarded} completions were forwarded (< {MIN_FORWARDED}); "
              f"the relay never carried the managed show -- with the feature off this "
              f"is 0 and the scenario fails first.", flush=True)
    elif drained < MIN_DRAINED:
        print(f"FAIL: the managed cuebot's drain filed only {drained} completions "
              f"(< {MIN_DRAINED}); forwards were ACKed but the drain did not process "
              f"them.", flush=True)
    elif steady_fallbacks is not None and steady_fallbacks > STEADY_FALLBACK_TOL:
        print(f"FAIL: {steady_fallbacks} managed-show completions fell back to the "
              f"legacy path on cuebot 0 before the kill (> {STEADY_FALLBACK_TOL}); "
              f"forwarding is flapping under steady state.", flush=True)
    elif cross_legacy > 0:
        print(f"FAIL: the legacy dispatcher booked {cross_legacy} frames of the managed "
              f"show {MANAGED}.", flush=True)
    elif cross_maestro > 0:
        print(f"FAIL: Maestro booked {cross_maestro} frames of legacy shows.", flush=True)
    elif any(n < MIN_DONE_EACH for n in leg_done.values()):
        print(f"FAIL: a legacy show completed fewer than {MIN_DONE_EACH} frames "
              f"({leg_done}); the legacy dispatcher was starved.", flush=True)
    elif KILL_AT and steady is not None and resume_snap is None:
        print("FAIL: the managed cuebot never answered its metrics again after the "
              "outage window; the restart did not come back.", flush=True)
    elif KILL_AT and breaker_hits is not None and breaker_hits <= 0:
        print(f"FAIL: the managed cuebot was down for {OUTAGE}s but cuebot 0's breaker "
              f"never took a report (fallback_breaker unchanged); the kill switch did "
              f"not engage.", flush=True)
    elif KILL_AT and outage_done is not None and outage_done < MIN_DONE_OUTAGE:
        print(f"FAIL: the managed show completed only {outage_done} frames while the "
              f"managed cuebot was down (< {MIN_DONE_OUTAGE}); the local fallback did "
              f"not carry it.", flush=True)
    elif KILL_AT and resumed_fwd is not None and resumed_fwd <= 0:
        print("FAIL: no completion was forwarded after the managed cuebot restarted; "
              "forwarding did not resume.", flush=True)
    elif ambig_attempts < MIN_AMBIG_ATTEMPTS:
        print(f"FAIL: the ambiguity arm made only {ambig_attempts} forward attempts "
              f"(< {MIN_AMBIG_ATTEMPTS}); the tiny-deadline cuebot never exercised the "
              f"double-process race.", flush=True)
    elif dbl > 0:
        print(f"FAIL: fake_rqd saw {dbl} frames launched twice.", flush=True)
    elif orphans > 0:
        print(f"FAIL: {orphans} run identities stayed stray for more than "
              f"{ORPHAN_AGE_S:.0f}s outside the crash window; a double-processed or "
              f"fallen-back completion was lost.", flush=True)
    else:
        print(f"PASS: forwarding carried {forwarded} of the managed show's completions "
              f"to the isolated cuebot (drained {drained}), the breaker fell back and "
              f"forwarding resumed around a {OUTAGE}s outage, the ambiguity arm's "
              f"{ambig_attempts} racy forwards resolved effectively-once, and the "
              f"legacy shows ran undisturbed ({sum(leg_done.values())} done, "
              f"{peak_util:.1f}% peak util).", flush=True)


if __name__ == "__main__":
    main()
