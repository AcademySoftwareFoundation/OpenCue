"""FOLDERTRIG verdict: does one over-cap folder, policed by a site trigger, cost the
farm anything but that folder's own bookings?

Companion to inject_foldertrig.py, which installed the folder-cap trigger on frame and
split the sim's work across a capped folder and the show's uncapped default folder.
This watcher waits until the capped folder runs wide, then lowers its
folder_resource.int_max_cores to ~30% of its live usage (an admin lowering a cap under
running work), which puts the folder over its cap while the trigger is armed. Once the
folder has decayed back under the cap and stayed clean a while, the cap is restored and
cut again, a few attempts in all.

Three invariants, sampled every INTERVAL seconds:

  1. No booking over the cap. While the capped folder's running cores exceed its cap,
     they may only decay: a rise means Maestro booked into an over-cap folder (the
     trigger would have rejected it, so a rise is a double failure).
  2. The uncapped folder keeps flowing. Its started-frame count must keep rising while
     it has waiting frames and the farm has idle cores; a streak of samples with no
     progress is the production stall this scenario reproduces (every tick committed
     nothing while one folder was over its cap).
  3. No collateral drops. Every "Maestro: commit of N booking(s) ... for job(s) [...]
     failed" WARN in the cuebot log must name only jobs of the capped folder; a dropped
     booking of the uncapped folder is a rejected frame taking its neighbours down.

  - PASS: the cap was cut under real load at least once, and all three held.
  - FAIL: a rise over the cap, a stall of the uncapped folder, or a collateral drop.
  - INCONCLUSIVE: the capped folder never ran wide enough to cut.

Units are core-points internally (100 = 1 core); reported in CORES.

usage: foldertrig_watch.py [duration_s] [interval_s]
"""
import os, re, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_metrics

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
PSQL = spec.psql_cmd()
CP = 100
FOLDER_NAME = "foldertrig"
TOKEN_FREE = "simftfree"
CUEBOT_LOG = os.environ.get("SIM_CUEBOT_LOG", "/tmp/cuebot-new.log")
CSV = os.environ.get("SIM_FOLDERTRIG_CSV", "")

MIN_RUN_CP = 1200          # cut only once the capped folder runs >= 12 cores
DROP_FRACTION = 0.3        # new cap = 30% of live usage at cut time
CLEAN_SAMPLES = 8          # samples back under the cap before restore + re-cut
MAX_CUTS = 3
STALL_FAIL = 6             # consecutive no-progress samples of the free folder (~18s)
MIN_IDLE_CP = 200          # a stall counts only with >= 2 idle cores on the farm

DROP_RE = re.compile(r"Maestro: commit of (\d+) booking\(s\) on host\(s\) \[([^\]]*)\] "
                     r"for job\(s\) \[([^\]]*)\] failed")


def q(sql, default=""):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip()
    except Exception:
        return default


def q_int(sql, default=0):
    out = q(sql)
    return int(out) if out.lstrip("-").isdigit() else default


SHOW = q("SELECT pk_show FROM show WHERE str_name='sim';")
ROOT = q(f"SELECT pk_folder FROM folder WHERE b_default=true AND pk_show='{SHOW}';")


def capped_folder():
    return q(f"SELECT pk_folder FROM folder WHERE str_name='{FOLDER_NAME}' "
             f"AND pk_show='{SHOW}';") or None


def cap_cp(folder):
    return q_int(f"SELECT int_max_cores FROM folder_resource WHERE pk_folder='{folder}';", -1)


def running_cp(folder):
    """Truth: cores reserved by the procs of the folder's jobs."""
    return q_int(f"SELECT COALESCE(SUM(p.int_cores_reserved),0) FROM proc p "
                 f"JOIN job j ON j.pk_job=p.pk_job WHERE j.pk_folder='{folder}';")


def free_started():
    """Monotonic progress of the uncapped folder: its frames that ever left WAITING."""
    return q_int(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                 f"WHERE j.pk_folder='{ROOT}' AND j.str_name LIKE '%{TOKEN_FREE}%' "
                 f"AND f.str_state <> 'WAITING';")


def free_waiting():
    return q_int(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                 f"WHERE j.pk_folder='{ROOT}' AND j.str_name LIKE '%{TOKEN_FREE}%' "
                 f"AND f.str_state='WAITING' AND f.int_depend_count=0;")


def idle_cp():
    return q_int("SELECT COALESCE(SUM(int_cores_idle),0) FROM host;")


def set_cap(folder, cp):
    q(f"UPDATE folder_resource SET int_max_cores={cp} WHERE pk_folder='{folder}';")


class DropScanner:
    """Follows the cuebot log for dropped-piece WARNs and attributes each job to a folder."""

    def __init__(self, capped):
        self.capped = capped
        self.pos = 0
        self.drops = 0
        self.dropped_bookings = 0
        self.collateral = 0
        self.folder_of = {}

    def scan(self):
        try:
            with open(CUEBOT_LOG, errors="ignore") as f:
                f.seek(self.pos)
                chunk = f.read()
                self.pos = f.tell()
        except Exception:
            return
        for m in DROP_RE.finditer(chunk):
            self.drops += 1
            self.dropped_bookings += int(m.group(1))
            jobs = [j.strip() for j in m.group(3).split(",") if j.strip()]
            unknown = [j for j in jobs if j not in self.folder_of]
            if unknown:
                rows = q("SELECT pk_job || '|' || pk_folder FROM job WHERE pk_job IN ("
                         + ",".join(f"'{j}'" for j in unknown) + ");")
                for row in rows.splitlines():
                    if "|" in row:
                        pk, folder = row.split("|", 1)
                        self.folder_of[pk] = folder
            bad = [j for j in jobs if self.folder_of.get(j) != self.capped]
            if bad:
                self.collateral += 1
                print(f"   <-- COLLATERAL DROP: {m.group(1)} booking(s) on {m.group(2)} "
                      f"for job(s) outside the capped folder: {bad}", flush=True)


def main():
    folder = None
    t0 = time.time()
    while folder is None and time.time() - t0 < 60:
        folder = capped_folder()
        if folder is None:
            time.sleep(INTERVAL)
    if folder is None:
        print("INCONCLUSIVE: the capped folder was never created.", flush=True)
        return
    cap0 = cap_cp(folder)
    scanner = DropScanner(folder)
    print(f"watching FOLDERTRIG {folder[:8]} (cap {cap0 // CP} cores, trigger armed) for "
          f"{DURATION}s: cut the cap under load, the uncapped folder must keep booking "
          f"and no drop may touch it.\n", flush=True)
    cuts = 0
    cut_at = -1.0
    new_cap = -1
    clean = 0
    rises = 0
    prev_run = None
    prev_started = free_started()
    stall = 0
    worst_stall = 0
    rows = []
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        cap = cap_cp(folder)
        run = running_cp(folder)
        started = free_started()
        waiting = free_waiting()
        idle = idle_cp()
        util, _ = sim_metrics.farm_state()
        scanner.scan()

        over = cap >= 0 and run > cap
        rise = over and prev_run is not None and prev_run > cap and run > prev_run
        if rise:
            rises += 1
        # Progress of the uncapped folder: a stall counts only when it had work
        # and the farm had room, so a saturated farm is not a stall.
        if started > prev_started or waiting == 0 or idle < MIN_IDLE_CP:
            stall = 0
        else:
            stall += 1
        worst_stall = max(worst_stall, stall)
        prev_started = started
        prev_run = run

        flag = ""
        if rise:
            flag += "  <-- BOOKED OVER CAP"
        if stall >= STALL_FAIL:
            flag += "  <-- UNCAPPED FOLDER STALLED"
        print(f"t={t:5.0f} | util {util:5.1f}% | capped {run // CP:4d} / cap {cap // CP:4d} "
              f"cores{' OVER' if over else '    '} | free started {started:6d} waiting "
              f"{waiting:6d} | drops {scanner.drops} collateral {scanner.collateral}{flag}",
              flush=True)
        rows.append((t, run // CP, cap // CP, started, waiting, util))

        # Cut the cap once the folder runs wide; restore and re-cut after a clean spell.
        if cuts == 0 and run >= MIN_RUN_CP:
            new_cap = max(CP, int(run * DROP_FRACTION))
            set_cap(folder, new_cap)
            cuts, cut_at, clean = 1, t, 0
            # A chunk that landed between this sample and the cut is not a
            # booking over the cap: the decay check starts from a fresh read.
            prev_run = running_cp(folder)
            print(f"t={t:5.0f} CAP CUT #1: capped folder usage={run}cp -> "
                  f"int_max_cores={new_cap}cp (was {cap}cp)", flush=True)
        elif cuts > 0 and cuts < MAX_CUTS:
            clean = clean + 1 if not over else 0
            if clean >= CLEAN_SAMPLES:
                set_cap(folder, cap0)
                print(f"t={t:5.0f} cap restored to {cap0}cp; re-cutting once it runs wide",
                      flush=True)
                time.sleep(4 * INTERVAL)
                run2 = running_cp(folder)
                if run2 >= MIN_RUN_CP:
                    new_cap = max(CP, int(run2 * DROP_FRACTION))
                    set_cap(folder, new_cap)
                    cuts += 1
                    cut_at = time.time() - t0
                    print(f"t={cut_at:5.0f} CAP CUT #{cuts}: usage={run2}cp -> "
                          f"int_max_cores={new_cap}cp", flush=True)
                clean = 0
                prev_run = running_cp(folder)
        time.sleep(INTERVAL)

    scanner.scan()
    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("t,capped_running_cores,cap_cores,free_started,free_waiting,util\n")
                for r in rows:
                    f.write(",".join(f"{v:.1f}" if isinstance(v, float) else str(v)
                                     for v in r) + "\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    print("\n==== FOLDERTRIG VERDICT ====", flush=True)
    print(f"cuts={cuts} (last at t={cut_at:.0f}s to {new_cap}cp) over-cap rises={rises} "
          f"worst free stall={worst_stall} samples dropped WARNs={scanner.drops} "
          f"dropped bookings={scanner.dropped_bookings} collateral drops={scanner.collateral}",
          flush=True)
    if cuts == 0:
        njobs = q_int(f"SELECT count(*) FROM job WHERE pk_folder='{folder}';", -1)
        print(f"INCONCLUSIVE: the capped folder never reached {MIN_RUN_CP}cp running "
              f"({njobs} job(s) in it); nothing to cut. Raise the load or the window.",
              flush=True)
    elif rises > 0 or worst_stall >= STALL_FAIL or scanner.collateral > 0:
        why = []
        if rises:
            why.append(f"{rises} booking(s) landed in the folder while it was over its cap")
        if worst_stall >= STALL_FAIL:
            why.append(f"the uncapped folder stalled for {worst_stall} samples with work "
                       f"waiting and cores idle")
        if scanner.collateral:
            why.append(f"{scanner.collateral} dropped piece(s) named jobs outside the "
                       f"capped folder")
        print("FAIL: " + "; ".join(why) + ".", flush=True)
    else:
        print(f"PASS: across {cuts} cap cut(s) the over-cap folder only decayed, the "
              f"uncapped folder kept booking (worst stall {worst_stall} < {STALL_FAIL}), "
              f"and every dropped piece ({scanner.drops}) named only the capped folder.",
              flush=True)


if __name__ == "__main__":
    main()
