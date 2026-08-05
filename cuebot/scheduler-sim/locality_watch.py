"""LOCALITY (same-layer packing) verdict: does the locality bonus actually work?

The scheduler's locality bonus (scheduler.locality_bonus, Scheduler.java) makes
placement prefer a host that ALREADY runs the candidate's layer, so a freed core
is refilled by the same layer (cache/asset warmth). This watcher measures that
behaviour directly with REFILL AFFINITY: of the procs newly booked between two
samples, what fraction landed on a host where their layer already had a proc at
the previous sample? That is literally the decision the bonus biases, so it
separates cleanly:

  - bonus ON : most refills return to a warm host        -> high hit rate
  - bonus OFF: refills follow the E-PVM least-utilized
               preference and scatter                     -> near-accidental rate

Only layers that HAD >=1 proc at the previous sample are counted (a layer's
first-ever placement has no warm host to prefer, and a layer booking onto its
very first host tells us nothing about affinity). The first WARMUP seconds are
skipped so the farm-fill phase (everything is a first placement) never dilutes
the signal. A secondary packing metric (avg procs per (layer,host) pair) is
printed for context, matching metrics.py's co-locality view.

  - PASS: refill hit rate >= SIM_LOCALITY_MIN_HIT (default 0.15, calibrated: full-farm bonus-ON measures ~29%, bonus-OFF ~1.3%) over enough
    refills (>= SIM_LOCALITY_MIN_SAMPLES, default 300).
  - INCONCLUSIVE: too few refills observed (farm not churning) -- raise load
    or duration.
  - FAIL: rate below the floor -- the bonus is not steering refills.

usage: locality_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
PSQL = spec.psql_cmd()
WARMUP = float(os.environ.get("SIM_LOCALITY_WARMUP", "40"))
MIN_HIT = float(os.environ.get("SIM_LOCALITY_MIN_HIT", "0.15"))
MIN_SAMPLES = int(os.environ.get("SIM_LOCALITY_MIN_SAMPLES", "300"))
CSV = os.environ.get("SIM_LOCALITY_CSV", "")
# SIM_LOCALITY_MODE=frames counts FRAME STARTS instead of new proc rows. The
# proc view is right for verifying the planner's bonus (every planner booking is
# a new proc), but it is blind to the legacy dispatcher's same-proc rebooking,
# which UPDATES the proc it keeps. A frame start is the one event both
# schedulers produce identically, so it is the fair A/B view. This mode also
# prints a CHANCE baseline (expected hits if placement ignored warmth, given
# current occupancy) and the LIFT over it, so runs at different farm fill are
# comparable.
MODE = os.environ.get("SIM_LOCALITY_MODE", "procs")
TOTAL_HOSTS = int(os.environ.get("SIM_LOCALITY_HOSTS", "0"))  # 0 = count live


def frames_running():
    """(pk_frame, pk_layer, host) for every RUNNING frame, plus the live host
    count for the chance baseline."""
    try:
        out = subprocess.run(PSQL + ["-c",
            "SELECT pk_frame, pk_layer, lower(str_host) FROM frame "
            "WHERE str_state = 'RUNNING' AND str_host IS NOT NULL;"],
            capture_output=True, text=True, timeout=15).stdout
        rows = []
        for line in out.strip().splitlines():
            parts = line.split("|")
            if len(parts) == 3:
                rows.append(tuple(parts))
        return rows
    except Exception:
        return []


def host_count():
    try:
        out = subprocess.run(PSQL + ["-c", "SELECT count(*) FROM host;"],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        return int(out) if out.isdigit() else 0
    except Exception:
        return 0


def main_frames():
    nhosts = TOTAL_HOSTS or host_count() or 1
    print(f"watching LOCALITY (frame-start affinity, fair to both schedulers) "
          f"for {DURATION}s over {nhosts} hosts: a frame START counts as a hit "
          f"when its layer was already running on that host at the previous "
          f"sample. chance = expected hits for warmth-blind placement; "
          f"lift = rate/chance (warmup {WARMUP:.0f}s skipped).\n", flush=True)
    t0 = time.time()
    prev_ids = set()
    prev_layer_hosts = {}
    hits = 0
    total = 0
    expected = 0.0
    rows_out = []
    # Cache-warmth (TIME locality). The affinity above is binary and
    # instantaneous: a hit needs the layer running on the host at the previous
    # sample. But a host whose last frame of the layer finished seconds ago is
    # just as warm, and the planner's bonus (fed from live procs only) cannot
    # see it. last_seen remembers, per (layer, host), when the pair last had a
    # running frame; every start that is NOT a live hit is classified by that
    # age. The histogram tells us how much warmth exists just past the
    # currently-rewarded window, i.e. what a time-window bonus would buy.
    last_seen = {}
    warm_ages = []                 # age (s) of each non-live start with history
    # Buckets span RAM-warmth (seconds) AND texture-tile-cache warmth
    # (minutes+): tiles cached on a host's local disk outlive the frames that
    # pulled them by minutes to hours, so a start on a host the layer ran on
    # MINUTES ago still saves the network fetch. "never" = the layer never ran
    # on that host within this watch.
    warm_buckets = {"live": 0, "<=5s": 0, "<=15s": 0, "<=60s": 0, "<=5m": 0,
                    "<=15m": 0, "<=1h": 0, ">1h": 0, "never": 0}
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        rows = frames_running()
        ids = set(r[0] for r in rows)
        layer_hosts = {}
        for _, lay, host in rows:
            layer_hosts.setdefault(lay, set()).add(host)
        new_hits = new_total = 0
        new_exp = 0.0
        if prev_ids and t > WARMUP:
            for fid, lay, host in rows:
                if fid in prev_ids:
                    continue                     # was already running
                warm = prev_layer_hosts.get(lay)
                if warm:
                    new_total += 1
                    new_exp += len(warm) / nhosts  # chance of a blind warm landing
                    if host in warm:
                        new_hits += 1
                # Warmth age, for EVERY start (layers with no live presence
                # anywhere still have per-host history worth classifying).
                seen = last_seen.get((lay, host))
                if warm and host in warm:
                    warm_buckets["live"] += 1
                elif seen is None:
                    warm_buckets["never"] += 1
                else:
                    age = t - seen
                    warm_ages.append(age)
                    if age <= 5:
                        warm_buckets["<=5s"] += 1
                    elif age <= 15:
                        warm_buckets["<=15s"] += 1
                    elif age <= 60:
                        warm_buckets["<=60s"] += 1
                    elif age <= 300:
                        warm_buckets["<=5m"] += 1
                    elif age <= 900:
                        warm_buckets["<=15m"] += 1
                    elif age <= 3600:
                        warm_buckets["<=1h"] += 1
                    else:
                        warm_buckets[">1h"] += 1
            hits += new_hits
            total += new_total
            expected += new_exp
        for _, lay, host in rows:
            last_seen[(lay, host)] = t
        rate = (hits / total) if total else 0.0
        chance = (expected / total) if total else 0.0
        lift = (rate / chance) if chance > 0 else 0.0
        print(f"t={t:5.0f} | running {len(rows):5d} | new {new_total:4d} hit {new_hits:4d} "
              f"| cum rate {rate:5.1%} chance {chance:5.1%} lift {lift:5.1f}x "
              f"({hits}/{total})", flush=True)
        rows_out.append((t, len(rows), new_total, new_hits, rate, chance, lift))
        # Checkpoint the histogram every sample: a run killed mid-way (box
        # restarts happen) still leaves the current answer on disk.
        try:
            with open("/tmp/locality_warmth_checkpoint.txt", "w") as ck:
                ck.write(f"t={t:.0f} rate={rate:.4f} chance={chance:.4f} "
                         f"hits={hits} total={total}\n")
                for k, v in warm_buckets.items():
                    ck.write(f"{k} {v}\n")
        except Exception:
            pass
        prev_ids = ids
        prev_layer_hosts = layer_hosts
        time.sleep(INTERVAL)

    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("t,running,new,hits,cum_rate,chance,lift\n")
                for r in rows_out:
                    f.write(f"{r[0]:.0f},{r[1]},{r[2]},{r[3]},{r[4]:.4f},{r[5]:.4f},{r[6]:.2f}\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    rate = (hits / total) if total else 0.0
    chance = (expected / total) if total else 0.0
    lift = (rate / chance) if chance > 0 else 0.0
    print("\n==== LOCALITY (frame-start) VERDICT ====", flush=True)
    print(f"frame-start affinity: hits={hits} of starts={total} rate={rate:.1%} "
          f"chance={chance:.1%} lift={lift:.1f}x", flush=True)
    nb = sum(warm_buckets.values())
    if nb:
        print("cache warmth of every start (age since the layer last ran on "
              "that host):", flush=True)
        for k in ("live", "<=5s", "<=15s", "<=60s", "<=5m", "<=15m", "<=1h",
                  ">1h", "never"):
            v = warm_buckets[k]
            print(f"  {k:>6}: {v:6d}  ({v / nb:5.1%})", flush=True)
        near = warm_buckets["<=5s"] + warm_buckets["<=15s"]
        print(f"warm-but-dark (layer ran there <=15s ago yet counts cold to the "
              f"live-only bonus): {near} starts, {near / nb:.1%}", flush=True)
        tiles = (near + warm_buckets["<=60s"] + warm_buckets["<=5m"]
                 + warm_buckets["<=15m"] + warm_buckets["<=1h"])
        print(f"tile-cache warm (layer ran there <=1h ago; what a windowed "
              f"affinity bonus could harvest): {tiles} starts, {tiles / nb:.1%}",
              flush=True)
    print("(measurement only: no PASS/FAIL gate in frames mode)", flush=True)


def procs():
    """(pk_proc, pk_layer, pk_host) for every live proc."""
    try:
        out = subprocess.run(PSQL + ["-c", "SELECT pk_proc, pk_layer, pk_host FROM proc "
                                           "WHERE pk_layer IS NOT NULL;"],
                             capture_output=True, text=True, timeout=15).stdout
        rows = []
        for line in out.strip().splitlines():
            parts = line.split("|")
            if len(parts) == 3:
                rows.append(tuple(parts))
        return rows
    except Exception:
        return []


def main():
    if MODE == "frames":
        main_frames()
        return
    print(f"watching LOCALITY (refill affinity) for {DURATION}s: of newly booked "
          f"procs whose layer already ran somewhere, the fraction landing on a "
          f"warm host must reach {MIN_HIT:.0%} (warmup {WARMUP:.0f}s skipped).\n",
          flush=True)
    t0 = time.time()
    prev_ids = set()
    prev_layer_hosts = {}
    hits = 0
    total = 0
    rows_out = []
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        rows = procs()
        ids = set(r[0] for r in rows)
        layer_hosts = {}
        for _, lay, host in rows:
            layer_hosts.setdefault(lay, set()).add(host)
        new_hits = new_total = 0
        if prev_ids and t > WARMUP:
            for pid, lay, host in rows:
                if pid in prev_ids:
                    continue                     # not new
                warm = prev_layer_hosts.get(lay)
                if not warm:
                    continue                     # first placement: no affinity to test
                new_total += 1
                if host in warm:
                    new_hits += 1
            hits += new_hits
            total += new_total
        # Secondary: packing (avg procs per (layer,host) pair), for context.
        pairs = sum(len(h) for h in layer_hosts.values())
        pack = (len(rows) / pairs) if pairs else 0.0
        rate = (hits / total) if total else 0.0
        print(f"t={t:5.0f} | procs {len(rows):5d} | new {new_total:3d} hit {new_hits:3d} "
              f"| cum rate {rate:5.1%} ({hits}/{total}) | pack {pack:4.1f}", flush=True)
        rows_out.append((t, len(rows), new_total, new_hits, rate, pack))
        prev_ids = ids
        prev_layer_hosts = layer_hosts
        time.sleep(INTERVAL)

    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("t,procs,new,hits,cum_rate,pack\n")
                for r in rows_out:
                    f.write(f"{r[0]:.0f},{r[1]},{r[2]},{r[3]},{r[4]:.4f},{r[5]:.2f}\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    rate = (hits / total) if total else 0.0
    print("\n==== LOCALITY VERDICT ====", flush=True)
    print(f"refill affinity: hits={hits} of refills={total} rate={rate:.1%} "
          f"(floor {MIN_HIT:.0%}, min samples {MIN_SAMPLES})", flush=True)
    if total < MIN_SAMPLES:
        print(f"INCONCLUSIVE: only {total} refills observed (< {MIN_SAMPLES}); the "
              f"farm did not churn enough to measure affinity. Raise load/duration.",
              flush=True)
    elif rate >= MIN_HIT:
        print(f"PASS: {rate:.1%} of refills returned to a warm host (>= {MIN_HIT:.0%}) "
              f"over {total} refills -- the locality bonus is steering placement.",
              flush=True)
    else:
        print(f"FAIL: only {rate:.1%} of refills returned to a warm host "
              f"(< {MIN_HIT:.0%}) over {total} refills -- locality bonus not "
              f"effective.", flush=True)


if __name__ == "__main__":
    main()
