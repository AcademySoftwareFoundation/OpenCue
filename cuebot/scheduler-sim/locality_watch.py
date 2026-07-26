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
