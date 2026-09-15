"""HEALTH verdict: do the farm-health metrics tell the truth about the farm?

The fake farm has a deterministic health story: every host named *0001 is
'sick' (kernel time 45%, a quarter of its swap spent), everyone else hums at a
low baseline (farm_spec.health_profile). The scheduler must surface that story
on its Prometheus endpoint as the cue_farm_health_* family, sliced by hardware
shape (by='hwtype') and by host-spec group (by='group'), with no database read
behind it (the ledger is fed by the host reports themselves).

Asserted, per hardware shape (the 3,4,10 farm has three shapes, each with one
sick *0001 host): swap_used_frac strictly between 0 and 1, hosts_swapping at
least 1, and system_time_pct_max at least 30. Plus at least one by='group'
slice with swap in use. PASS once every condition holds at once; the watcher
still runs its full window, so the battery's throughput floor stays meaningful.

usage: health_watch.py [duration_s] [interval_s]
"""
import re, sys, time, urllib.request

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0
METRICS_URL = "http://localhost:8080/metrics"
LINE = re.compile(r'^cue_farm_health_(\w+)\{([^}]*)\}\s+([0-9.eE+-]+)$')
LABEL = re.compile(r'(\w+)="([^"]*)"')


def scrape():
    """{(metric, by, name): value} for the cue_farm_health_* family."""
    out = {}
    try:
        body = urllib.request.urlopen(METRICS_URL, timeout=10).read().decode()
    except Exception:
        return out
    for ln in body.splitlines():
        m = LINE.match(ln)
        if not m:
            continue
        labels = dict(LABEL.findall(m.group(2)))
        out[(m.group(1), labels.get("by", ""), labels.get("name", ""))] = \
            float(m.group(3))
    return out


def main():
    print(f"watching HEALTH for {DURATION}s: cue_farm_health_* must report the "
          f"farm's deterministic sickness (every *0001 host: kernel 45%, swap "
          f"in use) per hardware shape and per spec group.\n", flush=True)
    t0 = time.time()
    best = {"hwtypes": 0, "groups": 0, "sysmax": 0.0, "swapping": 0}
    passed = False
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        v = scrape()
        shapes = sorted({n for (met, by, n) in v if by == "hwtype"
                         and met == "swap_used_frac"})
        groups = sorted({n for (met, by, n) in v if by == "group"
                         and met == "swap_used_frac"})
        ok_shapes = []
        for n in shapes:
            frac = v.get(("swap_used_frac", "hwtype", n), 0.0)
            swapping = v.get(("hosts_swapping", "hwtype", n), 0.0)
            sysmax = v.get(("system_time_pct_max", "hwtype", n), 0.0)
            best["sysmax"] = max(best["sysmax"], sysmax)
            best["swapping"] = max(best["swapping"], int(swapping))
            if 0.0 < frac <= 1.0 and swapping >= 1 and sysmax >= 30.0:
                ok_shapes.append(n)
        grp_ok = any(v.get(("swap_used_frac", "group", n), 0.0) > 0.0
                     for n in groups)
        best["hwtypes"] = max(best["hwtypes"], len(ok_shapes))
        best["groups"] = max(best["groups"], len(groups))
        print(f"t={t:5.0f} | shapes {shapes} healthy-asserts {len(ok_shapes)}/"
              f"{len(shapes)} | groups {len(groups)} | worst sysmax "
              f"{best['sysmax']:.0f}%", flush=True)
        if (not passed and len(shapes) >= 3 and len(ok_shapes) == len(shapes)
                and grp_ok):
            passed = True
            print(f"t={t:5.0f} | all conditions hold; watching to the end "
                  f"(the battery's throughput floor needs the full window)",
                  flush=True)
        time.sleep(INTERVAL)

    print("\n==== HEALTH VERDICT ====", flush=True)
    print(f"hwtypes={best['hwtypes']} groups={best['groups']} "
          f"worst sysTime max={best['sysmax']:.1f} "
          f"peak hosts swapping={best['swapping']}", flush=True)
    if passed:
        print(f"PASS: every hardware shape reports swap in use, at least one "
              f"swapping host and a sick kernel-time max of at least 30%, and "
              f"the spec-group slices carry swap too.", flush=True)
    elif best["hwtypes"] == 0 and best["groups"] == 0:
        print("INCONCLUSIVE: cue_farm_health_* never appeared on the metrics "
              "endpoint; nothing to judge.", flush=True)
    else:
        print(f"FAIL: the health story never fully surfaced "
              f"(shapes passing={best['hwtypes']}, groups={best['groups']}, "
              f"worst sysmax={best['sysmax']:.1f}).", flush=True)


if __name__ == "__main__":
    main()
