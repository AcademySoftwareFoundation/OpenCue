"""SHOWTIER watcher: shows share an allocation in proportion to their sizes.

Samples the two shows' cores in use and computes each show's tier, cores in
use over subscription size. The physical invariant, from the legacy
dispatcher's show walk: while both shows have work, the allocation splits so
that the tiers are equal, and no show goes above its burst. Both shows here
have sizes that add up to the farm, so equal tiers means each show holds its
size.

The verdict reads the last WINDOW_S seconds of samples, past the first fill
and one replacement wave, and needs contention (both shows still waiting)
and a full farm, or it is INCONCLUSIVE.

PASS      : mean tiers within TIER_GAP of each other, nobody above burst.
FAIL      : the disease. The tiers differ by more than TIER_GAP (the slot
            draw split the allocation by priority, not by size), or a show
            ran above its burst.
INCONCLUSIVE: the farm never filled, or a show ran out of waiting frames.

usage: showtier_watch.py [duration_s] [interval_s]
"""
import os, subprocess, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
SHOWS = ("showA", "showB")
TOKEN = "simshowtier"
WINDOW_S = 30.0
TIER_GAP = 0.15
MIN_UTIL = 85.0
PSQL = spec.psql_cmd()


def q(sql):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip().splitlines()
    except Exception:
        return []


def scalar(sql):
    rows = q(sql)
    return int(rows[0]) if rows and rows[0].strip().lstrip("-").isdigit() else 0


def sizes():
    out = {}
    for r in q("SELECT s.str_name, sub.int_size, sub.int_burst FROM subscription sub"
               " JOIN show s ON s.pk_show=sub.pk_show"
               f" WHERE s.str_name IN ('{SHOWS[0]}','{SHOWS[1]}');"):
        name, size, burst = r.split("|")
        out[name] = (int(size), int(burst))
    return out


def sample():
    util = q("SELECT round(100.0 * sum(int_cores - int_cores_idle) / sum(int_cores), 1)"
             " FROM host;")
    u = float(util[0]) if util and util[0].strip() else 0.0
    cores, wait = {}, {}
    for s in SHOWS:
        cores[s] = scalar("SELECT COALESCE(sum(p.int_cores_reserved),0) FROM proc p"
                          " JOIN show s ON s.pk_show=p.pk_show"
                          f" WHERE s.str_name='{s}';")
        wait[s] = scalar("SELECT count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job"
                         " JOIN show s ON s.pk_show=j.pk_show"
                         f" WHERE s.str_name='{s}' AND j.str_name LIKE '%{TOKEN}%'"
                         " AND f.str_state='WAITING';")
    return u, cores, wait


def main():
    print(f"watching SHOWTIER for {DURATION}s. PASS needs the two tiers (cores over "
          f"subscription size) within {TIER_GAP:.2f} of each other over the last "
          f"{WINDOW_S:.0f}s, nobody above burst, both shows still waiting.\n", flush=True)
    t0 = time.time()
    rows = []
    peak_util = 0.0
    over_burst = 0
    sz = {}
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        # Sizes are re-read every sample: the injector sets them at its start,
        # and the reference is whatever the subscription says now.
        cur = sizes()
        if len(cur) < 2:
            time.sleep(INTERVAL)
            continue
        if cur != sz:
            sz = cur
            print("sizes: " + ", ".join(f"{s} {sz[s][0] // 100} cores (burst "
                                        f"{sz[s][1] // 100})" for s in SHOWS), flush=True)
        util, cores, wait = sample()
        peak_util = max(peak_util, util)
        tier = {s: cores[s] / sz[s][0] if sz[s][0] else 0.0 for s in SHOWS}
        if any(cores[s] > sz[s][1] for s in SHOWS):
            over_burst += 1
        print(f"t={t:5.0f} | util {util:5.1f}% | "
              + " | ".join(f"{s} {cores[s] // 100:5d} cores tier {tier[s]:4.2f} "
                           f"wait {wait[s]:5d}" for s in SHOWS), flush=True)
        rows.append((t, util, tier, wait))
        time.sleep(INTERVAL)

    if not rows:
        print("\n==== SHOWTIER VERDICT ====\nINCONCLUSIVE: the two shows are not seeded.",
              flush=True)
        return
    tail = [r for r in rows if r[0] >= DURATION - WINDOW_S] or rows[-3:]
    mean = {s: sum(r[2][s] for r in tail) / len(tail) for s in SHOWS}
    contended = all(r[3][s] > 0 for r in tail for s in SHOWS)
    hi = max(mean.values())
    gap = (hi - min(mean.values())) / hi if hi > 0 else 0.0
    print("\n==== SHOWTIER VERDICT ====", flush=True)
    print(f"peak util {peak_util:.1f}%; last {WINDOW_S:.0f}s mean tiers "
          + ", ".join(f"{s} {mean[s]:.2f}" for s in SHOWS)
          + f"; tier gap {gap:.2f}; samples over burst {over_burst}", flush=True)
    if peak_util < MIN_UTIL:
        print(f"INCONCLUSIVE: the farm only reached {peak_util:.1f}% (< {MIN_UTIL}%).",
              flush=True)
    elif not contended:
        print("INCONCLUSIVE: a show ran out of waiting frames inside the window, so the "
              "split was not contended.", flush=True)
    elif over_burst > 0:
        print(f"FAIL: a show ran above its burst in {over_burst} samples.", flush=True)
    elif gap > TIER_GAP:
        print(f"FAIL: the tiers differ by {gap:.2f} (> {TIER_GAP:.2f}). The slot draw split "
              f"the allocation by priority, not by subscription size: the small show runs "
              f"over its size while the large one sits under it.", flush=True)
    else:
        print(f"PASS: tiers within {gap:.2f} of each other; the allocation is shared in "
              f"proportion to size, nobody above burst, at {peak_util:.1f}% peak "
              f"utilization.", flush=True)


if __name__ == "__main__":
    main()
