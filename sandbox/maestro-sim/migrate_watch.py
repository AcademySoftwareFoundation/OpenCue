"""MIGRATE watcher: two dispatchers, one farm, one show migrated to Maestro.

Three cuebots share the host and completion reports. Cuebots 0 and 1 are the
legacy dispatcher; cuebot 2 is Maestro in managed mode and books the legacy
shows on its own reports as well. One show is flagged b_scheduler_managed.
The invariants, sampled from the database and from Maestro's own metrics on
cuebot 2:

  1. Partition. Every start of a managed-show frame was Maestro's: the
     database's started frames of that show never exceed Maestro's
     cue_maestro_frames_dispatched_total for it. Maestro's counter for every
     legacy show stays at zero.
  2. Progress on both sides. The managed show and every legacy show complete
     frames, so neither dispatcher starves the other on the shared farm.
  3. Clean completions. A managed show's completion lands on the cuebot
     its host reports to; for the hosts pinned to a legacy cuebot (about
     two thirds) that cuebot must release the proc and never rebook it, and
     the rest reach Maestro's own queue. A released proc is deleted, so no
     proc outlives its frame's completion by more than the release latency
     and no RUNNING frame is without its proc for longer: a run identity
     that stays stray for more than ORPHAN_AGE_S is an orphan. The legacy
     path stops the frame in one transaction and queues the release behind
     its booking work, so a stray proc for a few seconds is that queue, not
     a leak; the peak of that in-flight count is reported, not judged.
     fake_rqd sees no frame launched twice.

PASS      : the three points above hold.
FAIL      : a cross-booking (either dispatcher touched the other's show), a
            starved side, an orphan, or a double launch.
INCONCLUSIVE: the farm never filled, so the split was not contended.

usage: migrate_watch.py [duration_s] [interval_s] [fake_rqd log] [maestro metrics url]
"""
import os, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import migrate_common as mc
from migrate_common import counts_by_show, strays, util

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
RQD_LOG = sys.argv[3] if len(sys.argv) > 3 else ""
METRICS_URL = sys.argv[4] if len(sys.argv) > 4 else "http://localhost:8082/metrics"
MANAGED = os.environ.get("SIM_MIGRATE_SHOW", "showA")
LEGACY = [s for s in ("sim", "showA", "showB", "showC", "showD", "showE") if s != MANAGED]
ORPHAN_AGE_S = 30.0
MIN_UTIL = 85.0
MIN_DONE_MANAGED = 100
MIN_DONE_EACH = 20


def maestro_booked():
    return mc.maestro_booked_from(METRICS_URL)


def double_launches():
    return mc.double_launches(RQD_LOG)


def main():
    print(f"watching MIGRATE for {DURATION}s: {MANAGED} on Maestro (cuebot 2), "
          f"{', '.join(LEGACY)} on the legacy dispatcher (cuebots 0 and 1); all three "
          f"cuebots receive reports. PASS needs "
          f"no cross-booking, progress on both sides, no proc or frame stray for more "
          f"than {ORPHAN_AGE_S:.0f}s, and no double launch.\n", flush=True)
    t0 = time.time()
    peak_util = 0.0
    first_seen = {}
    orphans = 0
    inflight_peak = 0
    dbl0 = double_launches()
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        u = util()
        peak_util = max(peak_util, u)
        c = counts_by_show()
        mb = maestro_booked()
        m = c.get(MANAGED, [0, 0, 0, 0])
        leg_run = sum(c[s][0] for s in LEGACY if s in c)
        leg_done = sum(c[s][1] for s in LEGACY if s in c)
        now = time.time()
        cur = strays()
        if cur is None:
            # Sampling failed; keep the existing ages rather than restarting
            # every stray's orphan clock.
            cur = set(first_seen)
        else:
            first_seen = {k: first_seen.get(k, now) for k in cur}
        aged = sum(1 for seen in first_seen.values() if now - seen > ORPHAN_AGE_S)
        orphans = max(orphans, aged)
        inflight_peak = max(inflight_peak, len(cur))
        print(f"t={t:5.0f} | util {u:5.1f}% | {MANAGED}: run {m[0]:4d} done {m[1]:5d} "
              f"wait {m[3]:5d} maestro-booked {mb.get(MANAGED, 0):5d} | legacy: run {leg_run:4d} "
              f"done {leg_done:5d} maestro-booked {sum(mb.get(s, 0) for s in LEGACY):d} | "
              f"stray {len(cur):3d} orphans {aged:d} | double {double_launches() - dbl0}",
              flush=True)
        time.sleep(INTERVAL)

    c = counts_by_show()
    mb = maestro_booked()
    m = c.get(MANAGED, [0, 0, 0, 0])
    started = m[0] + m[1] + m[2]
    booked = mb.get(MANAGED, 0)
    cross_legacy = max(0, started - booked)
    cross_maestro = sum(mb.get(s, 0) for s in LEGACY)
    leg_done = {s: c.get(s, [0, 0, 0, 0])[1] for s in LEGACY}
    dbl = double_launches() - dbl0
    print("\n==== MIGRATE VERDICT ====", flush=True)
    print(f"migrate: managed {MANAGED} started {started} (Maestro booked {booked}), "
          f"legacy done {sum(leg_done.values())} over {len(LEGACY)} shows "
          f"({', '.join(f'{s} {n}' for s, n in leg_done.items())}), cross-bookings "
          f"{cross_legacy}/{cross_maestro}, orphans {orphans} (stray > {ORPHAN_AGE_S:.0f}s), "
          f"releases in flight peak {inflight_peak}, double launches {dbl}, "
          f"peak util {peak_util:.1f}%", flush=True)
    if not mb:
        print("INCONCLUSIVE: Maestro's metrics never answered; is cuebot 2 up in managed "
              "mode?", flush=True)
    elif peak_util < MIN_UTIL:
        print(f"INCONCLUSIVE: the farm only reached {peak_util:.1f}% (< {MIN_UTIL}%), so "
              f"the two dispatchers were not contended.", flush=True)
    elif cross_legacy > 0:
        print(f"FAIL: the legacy dispatcher booked {cross_legacy} frames of the managed "
              f"show {MANAGED}. The legacy query must exclude flagged shows.", flush=True)
    elif cross_maestro > 0:
        print(f"FAIL: Maestro booked {cross_maestro} frames of legacy shows. In managed "
              f"mode it must plan only flagged shows.", flush=True)
    elif dbl > 0:
        print(f"FAIL: fake_rqd saw {dbl} frames launched twice.", flush=True)
    elif m[1] < MIN_DONE_MANAGED:
        print(f"FAIL: the managed show completed only {m[1]} frames (< {MIN_DONE_MANAGED}); "
              f"Maestro made no progress on its show.", flush=True)
    elif any(n < MIN_DONE_EACH for n in leg_done.values()):
        print(f"FAIL: a legacy show completed fewer than {MIN_DONE_EACH} frames "
              f"({leg_done}); the legacy dispatcher was starved.", flush=True)
    elif orphans > 0:
        print(f"FAIL: {orphans} run identities stayed stray for more than {ORPHAN_AGE_S:.0f}s "
              f"(a proc without a RUNNING frame, or a RUNNING frame without a proc); a "
              f"release was dropped or a proc was rebooked across the partition.", flush=True)
    else:
        print(f"PASS: {MANAGED} ran only through Maestro ({booked} frames), the "
              f"{len(LEGACY)} legacy shows ran only through the legacy dispatcher "
              f"({sum(leg_done.values())} frames done), no double launch, no orphan, "
              f"{peak_util:.1f}% peak utilization.", flush=True)


if __name__ == "__main__":
    main()
