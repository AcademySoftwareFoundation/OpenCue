"""TAGMAX verdict: the planner's cross-group layer dedup under heavy fragmentation.

Companion to `simulate.py --tagmax-test` (normally driven by --verify). The full
farm is shattered into many host-spec groups by a large capability-tag count
(SIM_NTAGS, default 120), while a run-anywhere slice (SIM_GENERAL_FRAC, default
0.3) of layers carry no tag and so stay on plain 'general', a candidate in EVERY
group at once. Without the dedup the planner re-plans each such layer once per
group per tick; the parallel per-host commit then pulls the same waiting frames,
and all but one copy loses the frame.int_version race at commit. With the dedup a
layer placed in one group this tick is skipped in the rest, so planned frames
about equal committed frames and the wasted planning disappears.

The signal is the Scheduler's own per-window stat line in the cuebot log
(SIM_CUEBOT_LOG):

    Scheduler stat: ... | farm ... groups=G | flow committed=C planned=P raceLost=R ...

raceLost (= planned - committed) is the frames a plan produced that lost the
version race. This watcher sums planned and raceLost across the run (past a warmup
window) and asserts the loss stayed a small fraction of planned:

  INVARIANT:
    - raceLost / planned <= SIM_TAGMAX_MAX_RACE (default 0.10). With the dedup
      this sits near zero; without it the run-anywhere layers push it near 1.

  COVERAGE (floors, so the verdict cannot pass vacuously):
    - summed planned >= SIM_TAGMAX_MIN_PLANNED (default 5000): the planner did
      real work, not one idle window;
    - peak host-spec groups >= SIM_TAGMAX_MIN_GROUPS (default 80): the tag
      fragmentation actually materialised (an un-fragmented farm cannot exhibit
      the cross-group duplication this guards against).

usage: tagmax_watch.py [duration_s] [interval_s]
"""
import os, re, sys, time

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 180
INTERVAL = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
CUEBOT_LOG = os.environ.get("SIM_CUEBOT_LOG", "/tmp/cuebot-new.log")
MAX_FRAC = float(os.environ.get("SIM_TAGMAX_MAX_RACE", "0.10"))
MIN_PLANNED = int(os.environ.get("SIM_TAGMAX_MIN_PLANNED", "5000"))
MIN_GROUPS = int(os.environ.get("SIM_TAGMAX_MIN_GROUPS", "80"))

# Each "Scheduler stat" line carries one window's planned/raceLost plus the last
# planned tick's host-spec group count. groups=G precedes the flow section on the
# same line (see Scheduler.maybeLogStat).
STAT_RE = re.compile(
    r"Scheduler stat:.*?groups=(\d+).*?"
    r"flow committed=(\d+) planned=(\d+) raceLost=(\d+)")


def parse_log():
    """(planned_total, race_total, peak_groups, windows) from the cuebot log,
    dropping the first stat window as warmup (it spans the farm fill and is not
    representative). Re-reads the whole file each call; the log is truncated at
    each cuebot start, so it holds only this scenario's stats."""
    try:
        txt = open(CUEBOT_LOG, errors="ignore").read()
    except Exception:
        return 0, 0, 0, 0
    rows = STAT_RE.findall(txt)
    if len(rows) > 1:
        rows = rows[1:]                      # drop warmup window
    planned = race = peak_groups = 0
    for groups, _committed, p, r in rows:
        planned += int(p)
        race += int(r)
        peak_groups = max(peak_groups, int(groups))
    return planned, race, peak_groups, len(rows)


def main():
    print(f"watching TAGMAX for {DURATION}s: planner cross-group dedup must hold, "
          f"raceLost/planned <= {MAX_FRAC:.0%} (floors: planned >= {MIN_PLANNED}, "
          f"groups >= {MIN_GROUPS}).  log={CUEBOT_LOG}\n", flush=True)
    t0 = time.time()
    planned = race = peak_groups = windows = 0
    while time.time() - t0 < DURATION:
        t = time.time() - t0
        planned, race, peak_groups, windows = parse_log()
        frac = (100.0 * race / planned) if planned else 0.0
        print(f"t={t:5.0f} | windows {windows:3d} | planned {planned:8d} "
              f"raceLost {race:8d} = {frac:5.1f}% | peak groups {peak_groups:4d}",
              flush=True)
        time.sleep(INTERVAL)

    planned, race, peak_groups, windows = parse_log()
    frac = (100.0 * race / planned) if planned else 0.0
    print("\n==== TAGMAX VERDICT ====", flush=True)
    print(f"windows={windows}  planned={planned}  raceLost={race} = {frac:.1f}%  "
          f"peak host-spec groups={peak_groups}", flush=True)
    if planned < MIN_PLANNED or peak_groups < MIN_GROUPS:
        print(f"INCONCLUSIVE: coverage too thin (planned {planned} < {MIN_PLANNED} "
              f"or peak groups {peak_groups} < {MIN_GROUPS}); nothing proven. "
              f"Raise load, tag count or duration.", flush=True)
    elif frac > 100.0 * MAX_FRAC:
        print(f"FAIL: raceLost {race} / planned {planned} = {frac:.1f}% of planned "
              f"(floor {100.0 * MAX_FRAC:.1f}%), across {peak_groups} host-spec "
              f"groups. The planner is re-planning a layer across groups and losing "
              f"the copies to the version race: the cross-group dedup is not "
              f"holding.", flush=True)
    else:
        print(f"PASS: raceLost {race} / planned {planned} = {frac:.1f}% of planned "
              f"(floor {100.0 * MAX_FRAC:.1f}%), across {peak_groups} host-spec "
              f"groups. Cross-group layer dedup holds, planned about equals "
              f"committed.", flush=True)


if __name__ == "__main__":
    main()
