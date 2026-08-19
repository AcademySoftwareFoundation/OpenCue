"""CAPDROP verdict: does the accounting mirror survive a cap lowered under load?

Companion to inject_capdrop.py. Two cap-drop corners, one invariant each time:
the accounting mirror must always track the truth (SUM over the procs).

Corner 1, job max cores. Waits until one capdrop job runs wide, then lowers that
job's job_resource.int_max_cores to ~30% of its live usage (what a user does in
production with "set max cores" on a running job; the verify trigger's WHEN
clause exempts cap changes, so the lowering itself always lands). From then on
the planner's plus-flush for that job arrives over the new cap.
  mirror = job_resource.int_cores
  truth  = COALESCE(SUM(proc.int_cores_reserved), 0) for the job

Corner 2, subscription burst. A little later the show's subscription burst is
cut to ~30% of the show's live usage on its allocation (an admin shrinking a
subscription under load). The verify_subscription trigger has the same shape as
verify_job_resources (reject a plus that lands over the cap while the cap column
is unchanged), so a plain plus-flush wedges the same way: the batch aborts, the
pluses re-queue forever, completions keep subtracting directly, the mirror
sinks. If a cut draws no divergence (the one-tick race missed), the burst is
restored and cut again, a few attempts in all, so a broken scheduler cannot get
lucky and a correct one proves itself repeatedly.
  mirror = subscription.int_cores for (show, alloc)
  truth  = COALESCE(SUM(proc.int_cores_reserved), 0) over that show on that alloc

A correct scheduler keeps |mirror - truth| small at every sample (one in-flight
tick of slack). The failure signature is a PERSISTENT divergence or a negative
mirror.

  - PASS: both caps were dropped under real load and every divergence streak
    stayed short, with no negative mirror.
  - FAIL: either mirror diverged persistently (>= FAIL_STREAK samples) or went
    negative.
  - INCONCLUSIVE: the load never got wide enough to drop the caps meaningfully.

usage: capdrop_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
PSQL = spec.psql_cmd()
TOKEN = "simcapdrop"

MIN_RUN_CP = 3000          # drop the job cap only once the job runs >= 30 cores
DROP_FRACTION = 0.3        # new cap = 30% of live usage at drop time
SLACK_CP = 800             # |mirror-truth| tolerated per sample (in-flight ticks)
FAIL_STREAK = 4            # consecutive bad samples (~12s) = wedged accounting
SUB_DELAY_S = 15           # burst cut this long after the job cap cut
SUB_CLEAN_SAMPLES = 10     # clean samples before we restore + re-cut the burst
SUB_MAX_CUTS = 3           # burst cut attempts in all


def q(sql, default=""):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip()
    except Exception:
        return default


def busiest_job():
    out = q(f"SELECT j.pk_job FROM job j JOIN proc p ON p.pk_job = j.pk_job "
            f"WHERE j.str_name LIKE '%{TOKEN}%' GROUP BY j.pk_job "
            f"ORDER BY SUM(p.int_cores_reserved) DESC LIMIT 1;")
    return out or None


def mirror_truth(pk):
    out = q(f"SELECT jr.int_cores, COALESCE((SELECT SUM(p.int_cores_reserved) "
            f"FROM proc p WHERE p.pk_job = jr.pk_job), 0) "
            f"FROM job_resource jr WHERE jr.pk_job = '{pk}';")
    try:
        a, b = out.split("|")
        return int(a), int(b)
    except Exception:
        return None, None


def sub_row(job_pk):
    """(pk_show, pk_alloc, int_burst) of the subscription the job books against."""
    out = q(f"SELECT s.pk_show, s.pk_alloc, s.int_burst FROM subscription s "
            f"WHERE s.pk_show = (SELECT pk_show FROM job WHERE pk_job = '{job_pk}') "
            f"AND s.pk_alloc = (SELECT h.pk_alloc FROM proc p "
            f"JOIN host h ON h.pk_host = p.pk_host "
            f"WHERE p.pk_job = '{job_pk}' LIMIT 1);")
    try:
        show, alloc, burst = out.split("|")
        return show, alloc, int(burst)
    except Exception:
        return None, None, None


def sub_mirror_truth(show, alloc):
    out = q(f"SELECT s.int_cores, COALESCE((SELECT SUM(p.int_cores_reserved) "
            f"FROM proc p JOIN host h ON h.pk_host = p.pk_host "
            f"WHERE p.pk_show = s.pk_show AND h.pk_alloc = s.pk_alloc), 0) "
            f"FROM subscription s WHERE s.pk_show = '{show}' "
            f"AND s.pk_alloc = '{alloc}';")
    try:
        a, b = out.split("|")
        return int(a), int(b)
    except Exception:
        return None, None


def set_burst(show, alloc, burst):
    q(f"UPDATE subscription SET int_burst = {burst} "
      f"WHERE pk_show = '{show}' AND pk_alloc = '{alloc}';")


def main():
    print(f"watching CAPDROP for {DURATION}s: lower one busy job's max cores to "
          f"{int(DROP_FRACTION*100)}% of its usage, then the show's subscription "
          f"burst the same way; each accounting mirror must keep tracking "
          f"SUM(procs).\n", flush=True)
    t0 = time.time()
    target = None
    dropped_at = -1.0
    new_cap = -1
    streak = 0
    worst_streak = 0
    worst_gap = 0
    negative_seen = 0
    sub_show = sub_alloc = None
    sub_burst0 = -1
    sub_cut_at = -1.0
    sub_cuts = 0
    sub_new_burst = -1
    sub_streak = 0
    sub_worst_streak = 0
    sub_worst_gap = 0
    sub_negative_seen = 0
    sub_clean = 0
    sub_restored = False
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        if target is None:
            pk = busiest_job()
            if pk:
                m, truth = mirror_truth(pk)
                if truth is not None and truth >= MIN_RUN_CP:
                    new_cap = int(truth * DROP_FRACTION)
                    q(f"UPDATE job_resource SET int_max_cores = {new_cap} "
                      f"WHERE pk_job = '{pk}';")
                    target = pk
                    dropped_at = t
                    print(f"t={t:5.0f} CAP DROP: job {pk} usage={truth}cp "
                          f"-> int_max_cores={new_cap}cp", flush=True)
            time.sleep(INTERVAL)
            continue

        m, truth = mirror_truth(target)
        if m is None:
            time.sleep(INTERVAL)
            continue
        gap = abs(m - truth)
        bad = gap > SLACK_CP
        streak = streak + 1 if bad else 0
        worst_streak = max(worst_streak, streak)
        worst_gap = max(worst_gap, gap)
        if m < 0:
            negative_seen += 1
        flag = "  <-- DIVERGED" if bad else ""
        print(f"t={t:5.0f} | job mirror {m:7d}cp | truth {truth:7d}cp "
              f"| gap {gap:6d}cp | streak {streak}{flag}", flush=True)

        # Subscription burst corner: arm after the job phase has had its moment.
        if sub_cuts == 0 and t - dropped_at >= SUB_DELAY_S:
            sub_show, sub_alloc, sub_burst0 = sub_row(target)
            if sub_show:
                sm, st = sub_mirror_truth(sub_show, sub_alloc)
                if st is not None and st > 0:
                    sub_new_burst = max(1, int(st * DROP_FRACTION))
                    set_burst(sub_show, sub_alloc, sub_new_burst)
                    sub_cuts = 1
                    sub_cut_at = t
                    print(f"t={t:5.0f} BURST DROP #1: show usage={st}cp "
                          f"-> int_burst={sub_new_burst}cp (was {sub_burst0}cp)",
                          flush=True)
        elif sub_cuts > 0 and not sub_restored:
            sm, st = sub_mirror_truth(sub_show, sub_alloc)
            if sm is not None:
                sgap = abs(sm - st)
                sbad = sgap > SLACK_CP
                sub_streak = sub_streak + 1 if sbad else 0
                sub_worst_streak = max(sub_worst_streak, sub_streak)
                sub_worst_gap = max(sub_worst_gap, sgap)
                sub_clean = 0 if sbad else sub_clean + 1
                if sm < 0:
                    sub_negative_seen += 1
                sflag = "  <-- DIVERGED" if sbad else ""
                print(f"t={t:5.0f} | sub mirror {sm:7d}cp | truth {st:7d}cp "
                      f"| gap {sgap:6d}cp | streak {sub_streak}{sflag}", flush=True)
                # No wedge drawn from this cut: restore and try again, so one
                # lucky flush ordering cannot hide a broken scheduler.
                if sub_clean >= SUB_CLEAN_SAMPLES:
                    if sub_cuts < SUB_MAX_CUTS:
                        set_burst(sub_show, sub_alloc, sub_burst0)
                        print(f"t={t:5.0f} burst restored to {sub_burst0}cp; "
                              f"re-cutting shortly", flush=True)
                        time.sleep(2 * INTERVAL)
                        sm2, st2 = sub_mirror_truth(sub_show, sub_alloc)
                        if st2 and st2 > 0:
                            sub_new_burst = max(1, int(st2 * DROP_FRACTION))
                            set_burst(sub_show, sub_alloc, sub_new_burst)
                            sub_cuts += 1
                            sub_clean = 0
                            print(f"t={time.time()-t0:5.0f} BURST DROP "
                                  f"#{sub_cuts}: show usage={st2}cp -> "
                                  f"int_burst={sub_new_burst}cp", flush=True)
                    else:
                        sub_restored = True
        time.sleep(INTERVAL)

    print("\n==== CAPDROP VERDICT ====", flush=True)
    print(f"cap dropped at t={dropped_at:.0f}s to {new_cap}cp; worst gap "
          f"{worst_gap}cp; worst divergence streak {worst_streak} samples; "
          f"negative mirror samples {negative_seen}", flush=True)
    print(f"burst cuts {sub_cuts} (first at t={sub_cut_at:.0f}s, burst "
          f"{sub_burst0}cp -> {sub_new_burst}cp); sub worst gap {sub_worst_gap}cp; "
          f"sub worst streak {sub_worst_streak} samples; sub negative samples "
          f"{sub_negative_seen}", flush=True)
    if target is None:
        print(f"INCONCLUSIVE: no capdrop job reached {MIN_RUN_CP}cp running; "
              f"nothing to drop. Raise the load or the window.", flush=True)
    elif (negative_seen > 0 or worst_streak >= FAIL_STREAK
            or sub_negative_seen > 0 or sub_worst_streak >= FAIL_STREAK):
        job_bad = negative_seen > 0 or worst_streak >= FAIL_STREAK
        side = "job" if job_bad else "subscription"
        print(f"FAIL: the {side} accounting mirror diverged from the procs after "
              f"the cap drop -- the plus-flush is being rejected while "
              f"completions keep subtracting.", flush=True)
    elif sub_cuts == 0:
        print(f"INCONCLUSIVE: the job cap dropped but the subscription burst was "
              f"never cut (no live usage found on the row).", flush=True)
    else:
        print(f"PASS: both mirrors tracked the procs throughout (job streak "
              f"{worst_streak}, sub streak {sub_worst_streak}, both < "
              f"{FAIL_STREAK}, no negatives) across {sub_cuts} burst cut(s) "
              f"with the caps dropped under load.", flush=True)


if __name__ == "__main__":
    main()
