"""DOUBLERENDER verdict: does a swept corpse proc take its render down with it?

Companion to inject_doublerender.py. The injector performs the stale
unfenced frame-stop (the release-path defect, one SQL statement, no cuebot
modification); real cuebot then sweeps the orphaned proc and rebooks the
frame. The question this watcher judges is what happens to the FIRST copy,
still rendering on its host:

  - FAIL (the defect, expected on unfixed code): the sweep deletes the proc
    with no RQD kill, the relaunch lands while the first copy is alive, and
    fake_rqd prints DOUBLE LAUNCH -- two hosts rendering the same frame,
    concurrent writes to the same outputs on a real farm.
  - PASS (the fix): the sweep/evict kills the zombie copy (fake_rqd prints
    "kill honored") before or as the frame is rebooked; zero DOUBLE LAUNCH.
  - INCONCLUSIVE: flips or rebooks never happened, or the copies completed
    naturally before the window was exercised; nothing judged.

usage: doublerender_watch.py [duration_s] [interval_s]
"""
import os, re, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 240
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PSQL = spec.psql_cmd()
INJECT_LOG = os.path.join(_HERE, "inject_doublerender.log")
RQD_LOG = os.path.join(_HERE, "rqd.log")
MIN_FLIPS = 3


def rows(sql):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return [ln.split("|") for ln in out.splitlines() if ln]
    except Exception:
        return []


def read(path):
    try:
        with open(path, errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def flips():
    """[(pk_frame, pk_proc, host)] the injector flipped, from its log."""
    return re.findall(r"FLIPPED frame=(\S+) proc=(\S+) host=(\S+)",
                      read(INJECT_LOG))


def main():
    print(f"watching DOUBLERENDER for {DURATION}s: after the injected stale "
          f"frame-stop, the swept corpse's render must not be left running "
          f"when the frame is booked again (fake_rqd's DOUBLE LAUNCH line is "
          f"the crime, its 'kill honored' line is the fix).\n", flush=True)
    t0 = time.time()
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        fl = flips()
        rqd = read(RQD_LOG)
        dbl = rqd.count("DOUBLE LAUNCH")
        kills = rqd.count("kill honored")
        swept = 0
        rebooked = 0
        if fl:
            old_procs = ",".join(f"'{p}'" for _, p, _ in fl)
            frames = ",".join(f"'{f}'" for f, _, _ in fl)
            r = rows(f"SELECT count(*) FROM proc "
                     f"WHERE pk_proc IN ({old_procs});")
            swept = len(fl) - int(r[0][0]) if r else 0
            r = rows(f"SELECT count(*) FROM proc "
                     f"WHERE pk_frame IN ({frames}) "
                     f"AND pk_proc NOT IN ({old_procs});")
            rebooked = int(r[0][0]) if r else 0
        print(f"t={t:5.0f} | flips {len(fl)} | old procs swept {swept} | "
              f"rebooked {rebooked} | DOUBLE LAUNCH {dbl} | zombie kills "
              f"{kills}", flush=True)
        time.sleep(INTERVAL)

    fl = flips()
    rqd = read(RQD_LOG)
    dbl = rqd.count("DOUBLE LAUNCH")
    kills = rqd.count("kill honored")
    swept = 0
    rebooked = 0
    if fl:
        old_procs = ",".join(f"'{p}'" for _, p, _ in fl)
        frames = ",".join(f"'{f}'" for f, _, _ in fl)
        r = rows(f"SELECT count(*) FROM proc WHERE pk_proc IN ({old_procs});")
        swept = len(fl) - int(r[0][0]) if r else 0
        # Any proc ever created for a flipped frame other than the corpse
        # counts as the rebook; frame_history keeps the record even if that
        # run also ended inside the window.
        r = rows(f"SELECT count(DISTINCT fh.pk_frame) FROM frame_history fh "
                 f"WHERE fh.pk_frame IN ({frames});")
        hist = int(r[0][0]) if r else 0
        r = rows(f"SELECT count(*) FROM proc WHERE pk_frame IN ({frames}) "
                 f"AND pk_proc NOT IN ({old_procs});")
        rebooked = max(int(r[0][0]) if r else 0, min(hist, len(fl)))

    print("\n==== DOUBLERENDER VERDICT ====", flush=True)
    print(f"flips {len(fl)}; old procs swept {swept}; rebooked {rebooked}; "
          f"double launches {dbl}; zombie kills {kills}", flush=True)
    if len(fl) < MIN_FLIPS:
        print(f"INCONCLUSIVE: only {len(fl)} frames were flipped (need "
              f"{MIN_FLIPS}); nothing to judge.", flush=True)
    elif rebooked == 0 and dbl == 0:
        print("INCONCLUSIVE: the flipped frames were never booked again; "
              "the window was not exercised.", flush=True)
    elif dbl > 0:
        print(f"FAIL: double render is real. {dbl} relaunch(es) arrived "
              f"while the first copy was still rendering; the sweep deleted "
              f"{swept} corpse proc(s) without any RQD kill. On a real farm "
              f"two hosts are writing the same output files.", flush=True)
    elif kills > 0:
        print(f"PASS: the zombie copies were killed ({kills} kill(s) "
              f"honored) before the frames were relaunched; {rebooked} "
              f"rebooks, zero double launches.", flush=True)
    else:
        print("INCONCLUSIVE: no double launch but no zombie kill either -- "
              "the first copies likely completed before the rebook; lengthen "
              "SIM_DUR_LONG_S or flip earlier.", flush=True)


if __name__ == "__main__":
    main()
