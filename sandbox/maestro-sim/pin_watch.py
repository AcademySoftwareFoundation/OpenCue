"""PIN watcher: layers pinned to machine lists run there and only there.

The pinned layers are the layers of the simpin jobs (cuebot stores the job
name with underscores); each list is read back from the layer's own tags,
split on '|'. The invariants, sampled from the
database and from Maestro's metrics:

  1. Placement. Every frame of a pinned layer that has run, is running or
     has finished ran on a host in its list: the frame's recorded host and
     the host of its proc are both in the list. A name that exists nowhere
     never runs anything.
  2. Progress. Every pinned layer with at least one real host completes
     MIN_DONE frames while the general flood keeps the farm full, so a pin
     wins the free cores of its own hosts.
  3. No fracture. Pins do not multiply host-spec groups: Maestro's group
     count never exceeds the number of distinct host specs, computed from
     the host table with each host's own name removed from its tags.
  4. Visibility. A pin that names no host is reported: the waitlist reason
     "no host" is non-zero at some point in the run.

PASS      : the four points above hold.
FAIL      : a pinned frame off its list, a starved pin, a fractured group
            count, or a dead pin with no reason.
INCONCLUSIVE: the farm never filled, so the pins were not contended.

usage: pin_watch.py [duration_s] [interval_s] [maestro metrics url]
"""
import os, re, subprocess, sys, time, urllib.request
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import farm_spec as spec

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
METRICS_URL = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8080/metrics"
JOB_RE = "simpin_(one|pair|span|mixed|dead)"
MIN_UTIL = 85.0
MIN_DONE = 10
PSQL = spec.psql_cmd()


def q(sql):
    try:
        return subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True,
                              timeout=15).stdout.strip().splitlines()
    except Exception:
        return []


def pinned_layers():
    """{kind: (pk_layer, set of pinned names)} for the simpin jobs."""
    out = {}
    for r in q("SELECT j.str_name, l.pk_layer, l.str_tags FROM layer l"
               " JOIN job j ON j.pk_job=l.pk_job"
               f" WHERE j.str_name ~ '{JOB_RE}';"):
        job, pk, tags = r.split("|", 2)
        kind = re.search(JOB_RE, job).group(1)
        out[kind] = (pk, {t.strip().lower() for t in tags.split("|") if t.strip()})
    return out


def frame_hosts(pk_layer):
    """[(state, recorded host)] for the layer's frames that have a host."""
    return [tuple(r.split("|", 1)) for r in
            q(f"SELECT str_state, str_host FROM frame WHERE pk_layer='{pk_layer}'"
              " AND str_host IS NOT NULL;")]


def proc_hosts(pk_layer):
    return q("SELECT h.str_name FROM proc p JOIN host h ON h.pk_host=p.pk_host"
             f" WHERE p.pk_layer='{pk_layer}';")


def done(pk_layer):
    rows = q(f"SELECT count(*) FROM frame WHERE pk_layer='{pk_layer}'"
             " AND str_state='SUCCEEDED';")
    return int(rows[0]) if rows else 0


def util():
    rows = q("SELECT round(100.0 * sum(int_cores - int_cores_idle) / sum(int_cores), 1)"
             " FROM host;")
    return float(rows[0]) if rows and rows[0].strip() else 0.0


def host_specs():
    """Distinct host specs: alloc, os and the sorted tags minus the host's name."""
    specs = set()
    for r in q("SELECT h.str_name, h.str_tags, h.pk_alloc, COALESCE(hs.str_os, '')"
               " FROM host h JOIN host_stat hs ON hs.pk_host=h.pk_host;"):
        name, tags, alloc, hos = r.split("|", 3)
        toks = sorted({t.lower() for t in tags.split() if t.lower() != name.lower()})
        specs.add((alloc, hos, " ".join(toks)))
    return len(specs)


def metrics():
    """(groups gauge, {reason: waiting frames}) from Maestro; (None, {}) when down."""
    try:
        body = urllib.request.urlopen(METRICS_URL, timeout=10).read().decode()
    except Exception:
        return None, {}
    g = re.search(r"^cue_maestro_groups_total\{[^}]*\}\s+([0-9.eE+]+)", body, re.M)
    reasons = {}
    for m in re.finditer(r'^cue_maestro_waiting_frames\{[^}]*reason="([^"]+)"[^}]*\}\s+([0-9.eE+]+)',
                         body, re.M):
        reasons[m.group(1)] = reasons.get(m.group(1), 0) + int(float(m.group(2)))
    return (int(float(g.group(1))) if g else None), reasons


def main():
    print(f"watching PIN for {DURATION}s: pinned layers must run only on their hosts, "
          f"complete {MIN_DONE} frames each, leave the host-spec group count whole, and a "
          f"dead pin must show the waitlist reason 'no host'.\n", flush=True)
    t0 = time.time()
    peak_util = 0.0
    violations = {}
    groups_peak = 0
    reasons_seen = {}
    metrics_ok = False
    kinds = {}
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        u = util()
        peak_util = max(peak_util, u)
        kinds = pinned_layers()
        g, reasons = metrics()
        if g is not None:
            metrics_ok = True
            groups_peak = max(groups_peak, g)
        for k, v in reasons.items():
            reasons_seen[k] = max(reasons_seen.get(k, 0), v)
        line = []
        for kind, (pk, pins) in sorted(kinds.items()):
            off = [h for _s, h in frame_hosts(pk) if h.lower() not in pins]
            off += [h for h in proc_hosts(pk) if h.lower() not in pins]
            violations[kind] = max(violations.get(kind, 0), len(off))
            line.append(f"{kind} {done(pk):3d}/{len(frame_hosts(pk)):3d} off {len(off)}")
        print(f"t={t:5.0f} | util {u:5.1f}% | groups {g if g is not None else '-'} | "
              + " | ".join(line), flush=True)
        time.sleep(INTERVAL)

    specs = host_specs()
    finals = {kind: done(pk) for kind, (pk, _p) in kinds.items()}
    started = {kind: len(frame_hosts(pk)) for kind, (pk, _p) in kinds.items()}
    real = [k for k in ("one", "pair", "span", "mixed") if k in kinds]
    pin_reason = {k: v for k, v in reasons_seen.items() if k.lower() == "no host" and v > 0}
    total_off = sum(violations.values())
    print("\n==== PIN VERDICT ====", flush=True)
    print(f"pin: off-list frames {total_off}, groups peak {groups_peak} (specs {specs}), done "
          + ", ".join(f"{k} {finals.get(k, 0)}" for k in ("one", "pair", "span", "mixed", "dead"))
          + f", dead started {started.get('dead', 0)}, no-host reason {'seen' if pin_reason else 'none'}, "
          f"peak util {peak_util:.1f}%", flush=True)
    if not kinds:
        print("INCONCLUSIVE: no pinned job was found; did the injector run?", flush=True)
    elif not metrics_ok:
        print("INCONCLUSIVE: Maestro's metrics never answered.", flush=True)
    elif peak_util < MIN_UTIL:
        print(f"INCONCLUSIVE: the farm only reached {peak_util:.1f}% (< {MIN_UTIL}%), so the "
              f"pins were not contended.", flush=True)
    elif total_off > 0:
        print(f"FAIL: {total_off} frames of pinned layers ran off their host lists "
              f"({violations}).", flush=True)
    elif groups_peak > specs:
        print(f"FAIL: Maestro saw {groups_peak} host-spec groups for {specs} specs; pins "
              f"fractured the grouping.", flush=True)
    elif any(finals.get(k, 0) < MIN_DONE for k in real):
        print(f"FAIL: a pinned layer completed fewer than {MIN_DONE} frames "
              f"({ {k: finals.get(k, 0) for k in real} }); Maestro does not place pinned "
              f"layers on their hosts.", flush=True)
    elif started.get("dead", 0) > 0:
        print(f"FAIL: the dead pin started {started['dead']} frames.", flush=True)
    elif not pin_reason:
        print("FAIL: the dead pin never showed the waitlist reason 'no host'.", flush=True)
    else:
        print(f"PASS: every pinned frame ran on its list, "
              + ", ".join(f"{k} {finals[k]}" for k in real)
              + f" frames done, {groups_peak} groups for {specs} specs, the dead pin shows "
              f"{sorted(pin_reason)}, {peak_util:.1f}% peak utilization.", flush=True)


if __name__ == "__main__":
    main()
