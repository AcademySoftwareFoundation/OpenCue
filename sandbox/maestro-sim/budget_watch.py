"""BUDGET watcher: subscription size orders the farm, burst lends.

Four shows on one allocation (see inject_budget.py). Samples utilization,
each show's cores and waiting frames; tier = cores over size. Phases are
read from the database: phase 2 starts when the late shows' jobs exist,
phase 3 when their max cores are cut.

  1. showA alone: the farm fills (peak util >= MIN_UTIL) and showA runs
     past its burst.                                        [burst lends]
  2. the late shows arrive: a show over its burst never gains cores while a
     show under its size is waiting; over the last WINDOW_S before phase 3
     the tiers are within TIER_GAP of each other and the farm is full.
                                                            [size orders]
  3. the late shows capped: showA takes the leftover, past its burst, and
     the farm stays full.                                   [burst lends]

PASS      : every phase holds.
FAIL      : a phase broke; the verdict names it.
INCONCLUSIVE: a phase never started, or a show ran out of work in phase 2.

usage: budget_watch.py [duration_s] [interval_s]
"""
import os, subprocess, sys, time
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
TOKEN = "simbudget"
SHOWS = ("showA", "showB", "showC", "showD")
LATE = SHOWS[1:]
MIN_UTIL = 90.0
TIER_GAP = 0.20
WINDOW_S = 30.0
GRACE_S = 10.0
SETTLE_S = 50.0
PSQL = spec.psql_cmd()


def q(sql):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip().splitlines()
    except Exception:
        return []


def scalar(sql, default=0):
    rows = q(sql)
    try:
        return int(float(rows[0]))
    except (IndexError, ValueError):
        return default


def subs():
    out = {}
    for r in q("SELECT s.str_name, sub.int_size, sub.int_burst FROM subscription sub JOIN show s"
               " ON s.pk_show=sub.pk_show WHERE s.str_name IN ("
               + ",".join(f"'{s}'" for s in SHOWS) + ");"):
        name, size, burst = r.split("|")
        out[name] = (int(size), int(burst))
    return out


def per_show(sql_tail):
    out = {s: 0 for s in SHOWS}
    for r in q(sql_tail):
        name, n = r.split("|")
        if name in out:
            out[name] = int(n)
    return out


def sample():
    rows = q("SELECT round(100.0 * sum(int_cores - int_cores_idle) / sum(int_cores), 1)"
             " FROM host;")
    try:
        u = float(rows[0])
    except (IndexError, ValueError):
        u = 0.0
    cores = per_show("SELECT s.str_name, COALESCE(sum(p.int_cores_reserved),0) FROM proc p"
                     " JOIN show s ON s.pk_show=p.pk_show GROUP BY 1;")
    wait = per_show("SELECT s.str_name, count(*) FROM frame f JOIN job j ON j.pk_job=f.pk_job"
                    f" JOIN show s ON s.pk_show=j.pk_show WHERE j.str_name ILIKE '%{TOKEN}%'"
                    " AND f.str_state='WAITING' GROUP BY 1;")
    return u, cores, wait


def main():
    print(f"watching BUDGET for {DURATION}s.\n", flush=True)
    farm = scalar("SELECT COALESCE(sum(int_cores),0) FROM host;")
    slack = max(100, farm // 50)             # one tick of in-flight bookings
    t0 = time.time()
    rows = []                                # (t, util, cores{}, wait{})
    p2 = p3 = None
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        if p2 is None and scalar("SELECT count(*) FROM job WHERE str_name ILIKE"
                                 f" '%{TOKEN}_{LATE[0]}%';") > 0:
            p2 = t
            print(f"t={t:5.0f} phase 2: {', '.join(LATE)} arrived", flush=True)
        if p2 is not None and p3 is None and 0 < scalar(
                "SELECT COALESCE(min(jr.int_max_cores), 0) FROM job_resource jr JOIN job j"
                f" ON j.pk_job=jr.pk_job WHERE j.str_name ILIKE '%{TOKEN}_{LATE[0]}%';") < farm:
            p3 = t
            print(f"t={t:5.0f} phase 3: late shows capped", flush=True)
        u, c, w = sample()
        rows.append((t, u, c, w))
        print(f"t={t:5.0f} | util {u:5.1f}% | "
              + " | ".join(f"{s[-1]} {c[s] // 100:4d}" for s in SHOWS), flush=True)
        time.sleep(INTERVAL)

    sb = subs()
    size = {s: sb.get(s, (0, 0))[0] for s in SHOWS}
    burst = {s: sb.get(s, (0, 0))[1] for s in SHOWS}
    tier = lambda c, s: c[s] / size[s] if size[s] else 0.0
    print("\n==== BUDGET VERDICT ====", flush=True)
    print("subscriptions: " + ", ".join(f"{s} size {size[s] // 100} burst {burst[s] // 100}"
                                       for s in SHOWS) + f" of {farm // 100} cores", flush=True)
    if p2 is None or p3 is None:
        print("INCONCLUSIVE: a phase never started (injector not running?).", flush=True)
        return
    ph1 = [r for r in rows if 30 <= r[0] < p2]
    ph2 = [r for r in rows if p2 + GRACE_S <= r[0] < p3]
    win = [r for r in ph2 if r[0] >= p3 - WINDOW_S]
    ph3 = [r for r in rows if r[0] >= p3 + SETTLE_S]
    if not ph1 or not win or not ph3:
        print("INCONCLUSIVE: a phase has no samples.", flush=True)
        return
    if any(r[3][s] == 0 for r in win for s in SHOWS):
        print("INCONCLUSIVE: a show ran out of waiting frames in phase 2.", flush=True)
        return
    p1_util = max(r[1] for r in ph1)
    p1_a = max(r[2]["showA"] for r in ph1)
    # Lending order: a show over its burst gains nothing while a show under
    # its size is waiting.
    grabs = sum(1 for prev, r in zip(ph2, ph2[1:]) for s in SHOWS
                if prev[2][s] > burst[s] and r[2][s] > prev[2][s] + slack
                and any(prev[2][o] < size[o] and prev[3][o] > 0 for o in SHOWS if o != s))
    mean = {s: sum(tier(r[2], s) for r in win) / len(win) for s in SHOWS}
    hi = max(mean.values())
    gap = (hi - min(mean.values())) / hi if hi > 0 else 0.0
    p2_util = sum(r[1] for r in win) / len(win)
    p3_util = sum(r[1] for r in ph3) / len(ph3)
    p3_a = sum(r[2]["showA"] for r in ph3) / len(ph3)
    print(f"phase 1: peak util {p1_util:.1f}%, showA peak {p1_a // 100} cores", flush=True)
    print(f"phase 2: last {WINDOW_S:.0f}s mean tiers "
          + ", ".join(f"{s} {mean[s]:.2f}" for s in SHOWS)
          + f"; tier gap {gap:.2f}; util {p2_util:.1f}%; over-burst grabs {grabs}", flush=True)
    print(f"phase 3: mean util {p3_util:.1f}%, showA mean {p3_a / 100:.0f} cores", flush=True)
    fails = []
    if p1_util < MIN_UTIL or p1_a <= burst["showA"]:
        fails.append(f"phase 1: showA alone held at {p1_a // 100} cores (burst "
                     f"{burst['showA'] // 100}), peak util {p1_util:.1f}%: burst refused "
                     f"idle capacity")
    if grabs:
        fails.append(f"phase 2: a show over its burst gained cores {grabs} times while a show "
                     f"under its size was waiting")
    if gap > TIER_GAP:
        fails.append(f"phase 2: tiers differ by {gap:.2f} (> {TIER_GAP:.2f}): the farm was not "
                     f"split by subscription size")
    if p2_util < MIN_UTIL:
        fails.append(f"phase 2: utilization {p2_util:.1f}% under contention")
    if p3_util < MIN_UTIL or p3_a <= burst["showA"]:
        fails.append(f"phase 3: the leftover was not lent (util {p3_util:.1f}%, showA "
                     f"{p3_a / 100:.0f} cores, burst {burst['showA'] // 100})")
    for f in fails:
        print("FAIL: " + f, flush=True)
    if not fails:
        print("PASS: showA filled the idle farm, the four shows split by size under "
              "contention, and showA took the leftover past its burst.", flush=True)


if __name__ == "__main__":
    main()
