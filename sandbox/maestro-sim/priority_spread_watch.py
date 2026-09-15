"""Priority PROPORTIONALITY verdict: is completion share ORDERED by priority?

Companion to inject_priority_spread.py, which contends the farm with N narrow-job
streams differing ONLY in priority (10, 20, ... 100). This samples each class's
completed frames over the run and ends with a per-class table (priority, done,
share%, ideal%) and a verdict:

  - PASS: completion share RISES with priority -- Spearman rank correlation
    (priority, share) >= RHO_MIN (default 0.7) AND the top class clearly
    out-completes the bottom. The lottery delivers a priority-weighted RATE.
    Exact proportionality is NOT required: shares track pri/sum(pri) through the
    middle, but the lowest classes run a little OVER their strict share (the
    lottery floors every class a nonzero chance -- anti-starvation) and the
    highest a little UNDER (equal per-class backlog caps the top at its demand).
  - INCONCLUSIVE: the farm never got contended (spare cores => priority is moot).
  - FAIL: shares are not ordered by priority (rho < RHO_MIN) -- priority is not
    translating into throughput.

'ideal%' is the strictly-proportional share (pri / sum(pri)) shown for reference
only; the PASS test is ORDERING, not a match to ideal. Writes SIM_SPREAD_CSV
(priority,done,share,ideal) so the run graph can plot share-vs-priority.

usage: priority_spread_watch.py [duration_s] [interval_s]
"""
import os, sys, time, subprocess
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec
import sim_metrics

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 300
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
PSQL = spec.psql_cmd()
PRIS = [int(x) for x in
        os.environ.get("SIM_SPREAD_PRIS", "10,20,30,40,50,60,70,80,90,100").split(",")]
RHO_MIN = float(os.environ.get("SIM_SPREAD_RHO_MIN", "0.7"))
CSV = os.environ.get("SIM_SPREAD_CSV", "")


def token(pri):
    return f"prispread{pri:03d}"


def done(pri):
    """SUCCEEDED frames for a class. Jobs are large so they seldom finish+archive
    within the run, keeping this an accurate completed-frame count."""
    tok = token(pri)
    try:
        out = subprocess.run(
            PSQL + ["-c", f"SELECT count(*) FROM frame f JOIN job j ON f.pk_job=j.pk_job "
                          f"WHERE j.str_name LIKE '%{tok}%' AND f.str_state='SUCCEEDED';"],
            capture_output=True, text=True, timeout=15).stdout.strip()
        return int(out) if out.lstrip("-").isdigit() else 0
    except Exception:
        return 0


def spearman(pris, shares):
    """Spearman rank correlation between priority and share (tie-averaged ranks)."""
    n = len(pris)
    if n < 2:
        return 1.0
    prank = {p: r for r, p in enumerate(sorted(pris))}
    pr = [prank[p] for p in pris]
    order = sorted(range(n), key=lambda i: shares[i])
    sr = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and shares[order[j + 1]] == shares[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            sr[order[k]] = avg
        i = j + 1
    d2 = sum((pr[i] - sr[i]) ** 2 for i in range(n))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def main():
    print(f"watching PRIORITY-SPREAD for {DURATION}s: {len(PRIS)} classes "
          f"pri={PRIS}. Share of completed frames should rise with priority.\n",
          flush=True)
    t0 = time.time()
    peak_util = 0.0
    while time.time() - t0 < DURATION:
        util, maxidle = sim_metrics.farm_state()
        peak_util = max(peak_util, util)
        d = {p: done(p) for p in PRIS}
        tot = sum(d.values()) or 1
        line = " ".join(f"p{p}:{100.0*d[p]/tot:4.1f}%" for p in PRIS)
        print(f"t={time.time()-t0:5.0f} | util {util:5.1f}% idle {maxidle:4d}c | {line}",
              flush=True)
        time.sleep(INTERVAL)

    d = {p: done(p) for p in PRIS}
    tot = sum(d.values())
    util, _ = sim_metrics.farm_state()
    peak_util = max(peak_util, util)
    shares = [(d[p] / tot if tot else 0.0) for p in PRIS]
    prisum = sum(PRIS) or 1
    ideal = [p / prisum for p in PRIS]
    rho = spearman(PRIS, shares)

    if CSV:
        try:
            with open(CSV, "w") as f:
                f.write("priority,done,share,ideal\n")
                for i, p in enumerate(PRIS):
                    f.write(f"{p},{d[p]},{shares[i]:.4f},{ideal[i]:.4f}\n")
        except Exception as e:
            print(f"(could not write CSV {CSV}: {e})", flush=True)

    print("\n==== PRIORITY-SPREAD VERDICT ====", flush=True)
    print(f"peak util={peak_util:.1f}%  total completed={tot}", flush=True)
    print(f"{'pri':>4} {'done':>8} {'share%':>7} {'ideal%':>7}", flush=True)
    for i, p in enumerate(PRIS):
        print(f"{p:>4} {d[p]:>8} {shares[i]*100:>6.1f} {ideal[i]*100:>6.1f}", flush=True)
    top, bot = shares[-1], shares[0]
    print(f"Spearman rho(priority, share) = {rho:.3f} "
          f"(>= {RHO_MIN} = ordered by priority); top/bottom share = "
          f"{top*100:.1f}% / {bot*100:.1f}%", flush=True)

    if peak_util < 80 or tot < len(PRIS):
        print(f"INCONCLUSIVE: farm never contended (peak util {peak_util:.0f}%, "
              f"total done {tot}); with spare cores priority does not decide. "
              f"Raise the load and rerun.", flush=True)
    elif rho >= RHO_MIN and top > bot:
        print(f"PASS: completion share is ordered by priority (rho={rho:.2f}); the "
              f"lottery gives higher priority a higher rate. Near-proportional in the "
              f"middle; low classes run a little over (anti-starvation floor), the top "
              f"a little under (equal per-class backlog caps its demand).",
              flush=True)
    else:
        print(f"FAIL: completion share is NOT ordered by priority (rho={rho:.2f} < "
              f"{RHO_MIN}) -- priority is not translating into throughput.", flush=True)


if __name__ == "__main__":
    main()
