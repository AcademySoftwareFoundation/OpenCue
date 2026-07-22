"""Plot a single sim run: utilization, throughput, reserved/backfilled cores, DB load.

Reads <dir>/<tag>_util.csv (util_sampler.py) and <dir>/<tag>_dbstat.csv
(db_sampler.py), plus the cuebot log (SIM_CUEBOT_LOG) for backfill, and writes
under <dir>:
  <tag>_util.png         utilization% + running/waiting frames
  <tag>_throughput.png   frames completing/s (the work-done signal)
  <tag>_reservations.png reservation subsystem: cores held + cumulative backfill
  <tag>_dbstats.png      DB load
simulate.py runs this automatically at the end of a watched run; it can also be
run by hand against any sampled run.

usage: plot_run.py <dir> [tag]
"""
import os, sys, csv
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DIR = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SIM_BENCH_DIR", "/tmp/cmp2")
TAG = sys.argv[2] if len(sys.argv) > 2 else "run"


def load(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def elapsed(rows):
    """Seconds since the first sample, from HH:MM:SS timestamps."""
    t0 = None
    xs = []
    for r in rows:
        t = datetime.strptime(r["ts"], "%H:%M:%S")
        if t0 is None:
            t0 = t
        dt = (t - t0).total_seconds()
        if dt < 0:
            dt += 86400          # midnight wrap
        xs.append(dt)
    return xs


made = []


def _cmdline():
    """The simulate.py invocation that produced this run (written by
    start_samplers into <dir>/<tag>_cmd.txt), for stamping on each graph."""
    p = os.path.join(DIR, f"{TAG}_cmd.txt")
    if os.path.exists(p):
        return open(p).read().strip()
    return os.environ.get("SIM_CMDLINE", "").strip()


CMDLINE = _cmdline()


def finish(fig, out):
    """Stamp the command line along the bottom so a graph is self-documenting,
    then save and close."""
    if CMDLINE:
        fig.text(0.5, 0.01, CMDLINE, ha="center", va="bottom", fontsize=7,
                 family="monospace", color="dimgray", wrap=True)
        fig.tight_layout(rect=[0, 0.05, 1, 1])
    else:
        fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
    made.append(out)


u = load(os.path.join(DIR, f"{TAG}_util.csv"))
ux = elapsed(u) if u else []
ut0 = datetime.strptime(u[0]["ts"], "%H:%M:%S") if u else None

# ---- utilization ----
if u:
    x = ux
    util = [float(r["util_pct"]) for r in u]
    run = [int(r["running_frames"]) for r in u]
    wait = [int(r["waiting_frames"]) for r in u]
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.plot(x, util, color="tab:blue", lw=2, label="utilization %")
    ax1.set_xlabel("seconds")
    ax1.set_ylabel("utilization %", color="tab:blue")
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(x, run, color="tab:green", lw=1, alpha=0.7, label="running frames")
    ax2.plot(x, wait, color="tab:orange", lw=1, alpha=0.7, label="waiting frames")
    ax2.set_ylabel("frames")
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [ln.get_label() for ln in lines], loc="lower right", fontsize=8)
    peak = max(util) if util else 0.0
    ax1.set_title(f"{TAG}: farm utilization (peak {peak:.1f}%)")
    out = os.path.join(DIR, f"{TAG}_util.png")
    finish(fig, out)

# ---- cores vs memory (which resource binds the farm) ----
# Both plotted as % of the farm's own total (from the host table). Whichever pins
# near 100% is the binding constraint: memory high while cores fall short means
# the farm is memory-bound and cores strand. Guarded so older CSVs without the
# memory columns still plot everything else.
if u and "total_mem_kb" in u[0]:
    cpct, mpct = [], []
    for r in u:
        tc = int(r["total_cores"]); tm = int(r["total_mem_kb"])
        cpct.append(100.0 * int(r["busy_cores"]) / tc if tc else 0.0)
        mpct.append(100.0 * int(r["busy_mem_kb"]) / tm if tm else 0.0)
    tot_cores = int(u[-1]["total_cores"]) / 100.0
    tot_mem_tb = int(u[-1]["total_mem_kb"]) / (1024.0 * 1024 * 1024)
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(ux, cpct, color="tab:blue", lw=2,
            label=f"cores used %  (of {int(tot_cores):,} cores)")
    ax.plot(ux, mpct, color="tab:red", lw=2,
            label=f"memory used %  (of {tot_mem_tb:.0f} TB)")
    ax.axhline(100, color="gray", ls=":", lw=1)
    ax.set_ylim(0, 105)
    ax.set_xlabel("seconds")
    ax.set_ylabel("% of farm total")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title(f"{TAG}: cores vs memory "
                 f"(peak cores {max(cpct):.0f}%, peak mem {max(mpct):.0f}%)")
    out = os.path.join(DIR, f"{TAG}_membound.png")
    finish(fig, out)

# ---- throughput (frames completing / s) ----
# succeeded_frames is a cumulative, monotonic count; its per-sample slope is the
# real work-done rate. High utilization alone can't distinguish a working
# scheduler from one that books then unbooks, so throughput is the signal to
# judge a run on. Light 3-sample smoothing tames sampling jitter.
if u and len(u) > 1:
    done = [int(r["succeeded_frames"]) for r in u]
    tput = [0.0]
    for i in range(1, len(done)):
        dt = ux[i] - ux[i - 1]
        tput.append(max(0.0, (done[i] - done[i - 1]) / dt) if dt > 0 else 0.0)
    sm = []
    for i in range(len(tput)):
        lo, hi = max(0, i - 1), min(len(tput), i + 2)
        sm.append(sum(tput[lo:hi]) / (hi - lo))
    tail = tput[len(tput) // 3:]            # steady state = last 2/3 (past the ramp)
    steady = sum(tail) / len(tail) if tail else 0.0
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(ux, tput, color="tab:green", lw=1, alpha=0.35, label="frames completing/s")
    ax.plot(ux, sm, color="tab:green", lw=2, label="frames completing/s (smoothed)")
    ax.axhline(steady, ls="--", color="tab:gray", lw=1, label=f"steady avg ~{steady:.0f}/s")
    ax.set_xlabel("seconds")
    ax.set_ylabel("frames / s")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title(f"{TAG}: throughput (peak {max(tput):.0f}/s, steady ~{steady:.0f}/s)")
    out = os.path.join(DIR, f"{TAG}_throughput.png")
    finish(fig, out)

# ---- reservation-feature cores: reserved (held) + backfilled (cuebot stat log) ----
# These are the wide-job RESERVATION feature's footprint, NOT booked/in-use cores
# (that is utilization; see the util graph). The scheduler stat line carries, per
# window:
#   reservedCores=N    whole cores currently HELD by the reservation feature
#                      (a point-in-time level: sum of held reservations' widths)
#   backfilledCores=N  whole cores borrowed back onto reserved/draining hosts via
#                      EASY backfill during that window (a flow; we accumulate it)
# Both aligned to the util time base (ut0). Empty if the run predates the metrics.
import re
cb = os.environ.get("SIM_CUEBOT_LOG")
cap = (int(u[0]["total_cores"]) / 100.0) if u else 0.0
if cb and os.path.exists(cb) and ut0 is not None:
    pat = re.compile(r"(\d\d:\d\d:\d\d)\.\d+.*reservedCores=(\d+).*backfilledCores=(\d+)")
    rx, rheld, bx, bcum, cum = [], [], [], [], 0
    # The cuebot log can be hundreds of MB and is still being appended to while
    # this runs. Pre-filter with a cheap substring before the regex, cap the
    # lines scanned so a fast-growing log can't stall us past generate_graphs'
    # timeout, and guard the whole scan so a hiccup never aborts the later
    # DB-load panel.
    try:
        for i, line in enumerate(open(cb, errors="ignore")):
            if i > 20_000_000:
                break
            if "reservedCores=" not in line:
                continue
            m = pat.search(line)
            if not m:
                continue
            dt = (datetime.strptime(m.group(1), "%H:%M:%S") - ut0).total_seconds()
            if dt < -3600:
                dt += 86400                 # midnight wrap
            if dt < 0:
                continue                    # stat line from before the sampled window
            rx.append(dt)
            rheld.append(int(m.group(2)))
            cum += int(m.group(3))
            bx.append(dt)
            bcum.append(cum)
    except Exception as e:
        print("plot_run: reservation scan skipped:", e)

    # One graph for the whole reservation subsystem: cores HELD by reservations (a
    # level, left axis) and the cumulative cores BACKFILLED back onto those
    # draining hosts (right axis). Same stat line, same time base, so they belong
    # together; a twin axis keeps both readable when their magnitudes differ.
    if rx:
        fig, ax1 = plt.subplots(figsize=(11, 5))
        ax1.plot(rx, rheld, color="tab:purple", lw=2, marker="o", ms=3,
                 label="cores held by reservations")
        ax1.set_xlabel("seconds")
        ax1.set_ylabel("cores held by reservations", color="tab:purple")
        ax1.set_ylim(bottom=0)
        ax1.grid(True, alpha=0.3)
        ax2 = ax1.twinx()
        ax2.plot(bx, bcum, color="tab:red", lw=2, marker="s", ms=3,
                 label="cumulative backfilled cores")
        ax2.set_ylabel("cumulative backfilled cores", color="tab:red")
        ax2.set_ylim(bottom=0)
        lines = ax1.get_lines() + ax2.get_lines()
        ax1.legend(lines, [ln.get_label() for ln in lines], loc="upper left", fontsize=8)
        ax1.set_title(f"{TAG}: reservation subsystem "
                      f"(peak {max(rheld)} of {cap:.0f} cores held; "
                      f"{bcum[-1]} cores backfilled total)")
        out = os.path.join(DIR, f"{TAG}_reservations.png")
        finish(fig, out)

# ---- DB load ----
d = load(os.path.join(DIR, f"{TAG}_dbstat.csv"))
if len(d) > 1:
    x = elapsed(d)

    def rate(col):
        vals = [int(r[col]) for r in d]
        out = [0.0]
        for i in range(1, len(vals)):
            dt = x[i] - x[i - 1]
            out.append((vals[i] - vals[i - 1]) / dt if dt > 0 else 0.0)
        return out

    commits = rate("commits")
    ins_r, upd_r, del_r = rate("ins"), rate("upd"), rate("del")
    writes = [ins_r[i] + upd_r[i] + del_r[i] for i in range(len(d))]
    reads = rate("tup_ret")
    lockwait = [int(r["lockwait"]) for r in d]
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.plot(x, commits, color="tab:blue", lw=1.5, label="commits/s")
    ax1.plot(x, writes, color="tab:red", lw=1.5, label="row writes/s (ins+upd+del)")
    ax1.set_xlabel("seconds")
    ax1.set_ylabel("commits / writes per s")
    ax1.grid(True, alpha=0.3)
    ax2 = ax1.twinx()
    ax2.plot(x, reads, color="tab:gray", lw=1, alpha=0.6, label="tuple reads/s")
    ax2.plot(x, lockwait, color="tab:orange", lw=1.2, label="lock waiters")
    ax2.set_ylabel("reads/s  /  lock waiters")
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [ln.get_label() for ln in lines], loc="upper right", fontsize=8)
    ax1.set_title(f"{TAG}: DB load")
    out = os.path.join(DIR, f"{TAG}_dbstats.png")
    finish(fig, out)

if made:
    print("wrote:")
    for m in made:
        print(" ", m)
else:
    print("plot_run: no sampler CSVs found in", DIR)
