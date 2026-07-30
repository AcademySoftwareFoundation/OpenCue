"""LICENSE verdict: did the planner ever oversubscribe a live license pool?

Companion to fake_license.py (the license server) and inject_license.py (the
load). Every interval it compares, per license, what the FARM is actually
holding against what the pool actually has, using the license server's own
ground truth (its /state endpoint) rather than re-deriving any of it here.

The invariant, and it is the real-world one:

    farm usage + what artists hold  <=  total

Overshooting that is not a scheduling inefficiency, it is frames dying on the
farm at license checkout, which is the failure this feature exists to prevent.
Both kinds of pool are checked:

  floating (katana, maya)  usage is RUNNING frames holding that license.
  host-based (hengine)     usage is DISTINCT MACHINES running it -- frames on a
                           seated machine share its one checkout, so frames may
                           (and should) run far past the seat count.

PASS also demands the test proved something, not merely that nothing broke:

  - a deep backlog waited, so the pools were genuinely under pressure;
  - licensed frames actually ran (a gate that books nothing violates nothing);
  - the UNLICENSED control work kept running, so the gate did not leak onto
    layers that never asked for a license;
  - frames on host-based pools really did share seats (usage in frames well
    above the seat count);
  - artists got the katana seats they asked for mid-run. This is the headroom
    proof: cuebot holds seats back, so a human can still get one while the farm
    is flat out. Artists starved of every seat is a FAIL even if no pool was
    ever oversubscribed.
  - no frame DIED, and the license denials fake_rqd injects were requeued for
    FREE: zero retries spent. A denial means the pool was busy, which is a queue
    to wait in, not a broken frame -- charging retries for it would march a whole
    layer to DEAD whenever licenses are contended.

usage: license_watch.py [duration_s] [interval_s]
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_metrics

def _arg(i, cast, default):
    """Read argv[i] tolerantly. This module is also IMPORTED (simulate.py's
    FAILOVER scenario reuses server_state/farm_usage as ground truth), and an
    importer's argv is not ours, so parsing it must never raise."""
    try:
        return cast(sys.argv[i])
    except (IndexError, ValueError):
        return default


DURATION = _arg(1, int, 180)
INTERVAL = _arg(2, float, 3.0)
PSQL = spec.psql_cmd()
CSV = os.environ.get("SIM_LICENSE_CSV", "")
PORT = int(os.environ.get("SIM_LIC_PORT", "9101"))
STATE_URL = f"http://127.0.0.1:{PORT}/state"
ENV_KEY = os.environ.get("SIM_LIC_ENV_KEY", "CUE_LICENSES")
TOKEN = "simlicense"
# Seat sharing bar for the host-based pool: frames must clear this multiple of
# the seat count, or the per-host gate is being over-strict.
SHARE_FACTOR = float(os.environ.get("SIM_LIC_SHARE_FACTOR", "4"))
# Throughput floor: frames this test's jobs must actually COMPLETE. Without it a
# planner that held every licensed layer would satisfy every invariant here.
MIN_DONE = int(os.environ.get("SIM_LIC_MIN_DONE", "200"))
# Fraction of frames fake_rqd fails with the license-denied exit status, and the
# retry budget those denials are allowed to spend: zero, because requeueing a
# frame that merely waited for a license must be free.
DENY_RATE = float(os.environ.get("SIM_LIC_DENY_RATE", "0"))
MAX_RETRIES = int(os.environ.get("SIM_LIC_MAX_RETRIES", "0"))


def _rows(sql):
    try:
        out = subprocess.run(PSQL + ["-t", "-A", "-F", "\t", "-c", sql],
                             capture_output=True, text=True, timeout=15).stdout
        return [ln.split("\t") for ln in out.strip().splitlines() if ln.strip()]
    except Exception:
        return []


def _scalar(sql, default=0):
    try:
        out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                             timeout=15).stdout.strip()
        return int(out) if out.lstrip("-").isdigit() else default
    except Exception:
        return default


def server_state():
    try:
        with urllib.request.urlopen(STATE_URL, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}


def farm_usage():
    """Per license: RUNNING frames, and the distinct hosts running them.

    Counted from the frame table (what RQD is really executing), independent of
    anything the license server or the planner believes.
    """
    frames, hosts = {}, {}
    for row in _rows(
            f"SELECT le.str_value, f.str_host FROM layer_env le "
            f"JOIN frame f ON f.pk_layer = le.pk_layer "
            f"WHERE le.str_key = '{ENV_KEY}' AND f.str_state = 'RUNNING';"):
        if len(row) < 2:
            continue
        raw, host = row[0], (row[1] or "").strip().lower()
        for name in [p.strip().lower() for p in raw.split(",") if p.strip()]:
            frames[name] = frames.get(name, 0) + 1
            if host:
                hosts.setdefault(name, set()).add(host)
    return frames, hosts


def unlicensed_running():
    """RUNNING frames of this test's UNLICENSED layers (the control group).

    A layer is unlicensed when it has no CUE_LICENSES row at all, or an empty
    one. It must be entirely unaffected by licensing.
    """
    return _scalar(
        f"SELECT count(*) FROM frame f "
        f"JOIN job j ON j.pk_job = f.pk_job "
        f"LEFT JOIN layer_env le ON le.pk_layer = f.pk_layer "
        f"AND le.str_key = '{ENV_KEY}' "
        f"WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state = 'RUNNING' "
        f"AND (le.str_value IS NULL OR le.str_value = '');")


def waiting_backlog():
    return _scalar(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                   f"WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='WAITING' "
                   f"AND f.int_depend_count=0;")


def dead_frames():
    return _scalar(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                   f"WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='DEAD';")


def succeeded():
    return _scalar(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                   f"WHERE j.str_name LIKE '%{TOKEN}%' AND f.str_state='SUCCEEDED';")


def denied_requeued():
    """Frames sitting WAITING after a license denial: cuebot rewrites the vendor's
    exit status to SKIP_RETRY (286) precisely so the requeue spends no retry, so
    this is the count of denials currently parked for another attempt."""
    return _scalar(f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                   f"WHERE j.str_name LIKE '%{TOKEN}%' AND f.int_exit_status=286;")


def retries_spent():
    """Retries charged to license denials across this test's frames. A denial
    must cost NONE: a busy pool is a queue to wait in, not a failure. Frames may
    legitimately spend retries on MEMORY failures (exit 33: the OOM kill+bump
    path retries by design, and the locality bonus packs same-layer frames
    tightly enough to produce a few), so retries explained by a frame's OOM
    runs in frame_history are subtracted; only the unexplained excess counts as
    a denial being charged."""
    return _scalar(
        f"SELECT COALESCE(SUM(GREATEST(0, f.int_retries - COALESCE(oom.n,0))),0) "
        f"FROM frame f JOIN job j ON f.pk_job=j.pk_job "
        f"LEFT JOIN (SELECT pk_frame, count(*) AS n FROM frame_history "
        f"           WHERE int_exit_status=33 GROUP BY pk_frame) oom "
        f"       ON oom.pk_frame=f.pk_frame "
        f"WHERE j.str_name LIKE '%{TOKEN}%';")


def main():
    st = server_state()
    if not st:
        print(f"watching LICENSE: cannot reach the license server at {STATE_URL}",
              flush=True)
    totals = st.get("totals", {})
    host_based = st.get("host_based", {})
    names = sorted(totals) or ["hengine", "katana", "maya"]
    print(f"watching LICENSE for {DURATION}s: farm usage + artist holds must never "
          f"exceed a pool. Pools: "
          + ", ".join(f"{n}={totals.get(n, '?')}"
                      f"{' seats' if host_based.get(n) else ''}" for n in names)
          + ".\n", flush=True)

    t0 = time.time()
    # Worst (highest) oversubscription seen per license, and the peaks that make
    # the verdict readable.
    over = {n: 0 for n in names}
    peak_use = {n: 0 for n in names}
    peak_frames = {n: 0 for n in names}
    peak_backlog = 0
    peak_unlicensed = 0
    art_got = {n: 0 for n in names}
    art_wanted = {n: 0 for n in names}
    samples = 0
    rows = []

    while time.time() - t0 < DURATION:
        st = server_state()
        totals = st.get("totals", totals)
        host_based = st.get("host_based", host_based)
        holds = st.get("artist_holds", {})
        wanted = st.get("artist_wanted", {})
        frames, hosts = farm_usage()
        backlog = waiting_backlog()
        unlic = unlicensed_running()
        util, _ = sim_metrics.farm_state()
        samples += 1
        peak_backlog = max(peak_backlog, backlog)
        peak_unlicensed = max(peak_unlicensed, unlic)

        line = []
        for n in names:
            total = int(totals.get(n, 0))
            art = int(holds.get(n, 0))
            art_got[n] = max(art_got[n], art)
            art_wanted[n] = max(art_wanted[n], int(wanted.get(n, 0)))
            nframes = frames.get(n, 0)
            # host-based pools are measured in machines, floating ones in frames
            use = len(hosts.get(n, [])) if host_based.get(n) else nframes
            peak_use[n] = max(peak_use[n], use)
            peak_frames[n] = max(peak_frames[n], nframes)
            excess = (use + art) - total
            if excess > over[n]:
                over[n] = excess
            unit = "seats" if host_based.get(n) else "frames"
            flag = "  <-- OVER POOL" if excess > 0 else ""
            line.append(f"{n} {use}+{art}/{total} {unit}{flag}")
        rows.append((time.time() - t0, util, backlog, unlic,
                     [peak_use[n] for n in names]))
        print(f"t={time.time()-t0:5.0f} | util {util:5.1f}% | " + " | ".join(line)
              + f" | unlicensed {unlic:5d} | waiting {backlog:6d}", flush=True)
        time.sleep(INTERVAL)

    dead = dead_frames()
    done = succeeded()
    requeued = denied_requeued()
    retries = retries_spent()

    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("t,util,backlog,unlicensed," + ",".join(names) + "\n")
                for (t, util, backlog, unlic, uses) in rows:
                    f.write(f"{t:.0f},{util:.1f},{backlog},{unlic},"
                            + ",".join(str(u) for u in uses) + "\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    print("\n==== LICENSE VERDICT ====", flush=True)
    for n in names:
        unit = "seats" if host_based.get(n) else "frames"
        print(f"{n:<8} total={totals.get(n, '?')}  peak farm use={peak_use[n]} {unit}"
              f"  peak frames={peak_frames[n]}"
              f"  artists held={art_got[n]}/{art_wanted[n]}"
              f"  worst oversubscription={over[n]}", flush=True)
    print(f"peak waiting backlog={peak_backlog}  peak unlicensed running="
          f"{peak_unlicensed}  succeeded={done}  dead={dead}", flush=True)
    print(f"license denials requeued={requeued}  retries spent={retries} "
          f"(a denial must spend none)", flush=True)

    worst = max(over.values()) if over else 0
    seat_pools = [n for n in names if host_based.get(n)]
    shared_ok = all(
        peak_frames[n] >= SHARE_FACTOR * max(1, peak_use[n]) for n in seat_pools)
    starved = [n for n in names if art_wanted[n] > 0 and art_got[n] == 0]

    if not totals:
        print("INCONCLUSIVE: no license server state -- fake_license.py did not run.",
              flush=True)
    elif samples < 5:
        print(f"INCONCLUSIVE: only {samples} samples taken; run longer.", flush=True)
    elif peak_backlog < 1000:
        print(f"INCONCLUSIVE: backlog too shallow (peak waiting {peak_backlog} "
              f"< 1000) to put the pools under pressure. Raise the load.", flush=True)
    elif all(peak_use[n] == 0 for n in names):
        print("INCONCLUSIVE: no licensed frame ever ran -- the gate booked nothing, "
              "so nothing was proven. Check the provider is reachable.", flush=True)
    elif worst > 0:
        bad = [f"{n} by {over[n]}" for n in names if over[n] > 0]
        print(f"FAIL: pool oversubscribed ({', '.join(bad)}) -- the planner booked "
              f"past what the license server had free, which fails frames at "
              f"checkout on a real farm.", flush=True)
    elif dead > 0:
        print(f"FAIL: {dead} frames DEAD -- license contention must requeue a frame, "
              f"never kill it.", flush=True)
    elif retries > MAX_RETRIES:
        # The requeue must be free. If retries pile up, license denials are being
        # charged as failures and a busy pool would eventually DEAD the layer.
        print(f"FAIL: {retries} retries were spent (allowed {MAX_RETRIES}) -- a "
              f"license denial is being charged as a frame failure instead of "
              f"requeued for free.", flush=True)
    elif DENY_RATE > 0 and requeued == 0:
        print(f"FAIL: license denials were injected (rate {DENY_RATE}) but no frame "
              f"came back as a free requeue -- the requeue path never ran, so it is "
              f"unproven.", flush=True)
    elif done < MIN_DONE:
        # Throughput floor. A gate that holds everything violates no invariant and
        # would otherwise pass, so completions have to be checked explicitly.
        print(f"FAIL: only {done} frames completed (< {MIN_DONE}) -- the farm barely "
              f"ran, so holding the pools proves nothing about throughput.",
              flush=True)
    elif peak_unlicensed == 0:
        print("FAIL: no unlicensed frame ever ran -- licensing is gating work that "
              "never asked for a license.", flush=True)
    elif not shared_ok:
        detail = ", ".join(f"{n}: {peak_frames[n]} frames on {peak_use[n]} seats"
                           for n in seat_pools)
        print(f"FAIL: host-based seats are not being shared ({detail}) -- frames on "
              f"a seated machine share its checkout, so frames should run far past "
              f"the seat count.", flush=True)
    elif starved:
        print(f"FAIL: artists got NO seats on {', '.join(starved)} -- headroom is "
              f"not being held back, so a human cannot get a license while the farm "
              f"is busy (the complaint this feature exists to fix).", flush=True)
    else:
        detail = ", ".join(
            f"{n} peaked {peak_use[n]}/{totals.get(n)}"
            + (f" seats carrying {peak_frames[n]} frames" if host_based.get(n) else "")
            for n in names)
        print(f"PASS: no pool ever oversubscribed ({detail}); artists took "
              f"{art_got.get('katana', 0)} katana seats mid-run; {peak_unlicensed} "
              f"unlicensed frames ran unaffected; {requeued} license denials were "
              f"requeued for free ({retries} retries spent); {done} frames "
              f"succeeded and {dead} died.", flush=True)


if __name__ == "__main__":
    main()
