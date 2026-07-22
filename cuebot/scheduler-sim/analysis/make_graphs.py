"""NEW vs RUST -- 3 graphs: DB reads/s, DB writes/s, DB health (contention)."""
import os
import re
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Directory holding <tag>_dbstat.csv and <tag>_sim.log produced by a run. Override
# with SIM_BENCH_DIR; defaults to the legacy scratch dir used during development.
CMP = os.environ.get("SIM_BENCH_DIR", "/tmp/cmp2")
RUNS = [("new", "new (inline-dispose)", "#1f77b4"), ("rust", "rust", "#d62728")]
WATCH = 185

def sod(h):
    a = list(map(int, h.split(":"))); return a[0]*3600 + a[1]*60 + a[2]

def util_series(tag):
    rx = re.compile(r"\[(\d\d:\d\d:\d\d)\]\s*util=\s*([\d.]+)%"); pts = []
    try:
        for ln in open(f"{CMP}/{tag}_sim.log", errors="ignore"):
            m = rx.search(ln)
            if m: pts.append((sod(m.group(1)), float(m.group(2))))
    except FileNotFoundError: return []
    if not pts: return []
    t0 = pts[0][0]; return [(t-t0, v) for t, v in pts if 0 <= t-t0 <= WATCH]

def rows(tag):
    out = []
    try: f = open(f"{CMP}/{tag}_dbstat.csv", errors="ignore")
    except FileNotFoundError: return []
    f.readline()
    for ln in f:
        p = ln.strip().split(",")
        if len(p) < 11: continue
        try: out.append((sod(p[0]), [int(x) for x in p[1:11]]))
        except ValueError: continue
    return out
# cols after ts: 0 commits,1 rollbacks,2 tup_ret,3 tup_fetch,4 ins,5 upd,6 del,7 deadlocks,8 active,9 lockwait

def rates(tag):
    r = rows(tag)
    o = {k: [] for k in ("reads","writes","rollbacks","deadlocks","lockwait","active")}
    if not r: return o
    t0 = r[0][0]
    for i in range(1, len(r)):
        (ta, a), (tb, b) = r[i-1], r[i]; dt = tb-ta
        if dt <= 0: continue
        rt = tb-t0
        if not (0 <= rt <= WATCH+30): continue
        o["reads"].append((rt, ((b[2]-a[2])+(b[3]-a[3]))/dt))
        o["writes"].append((rt, ((b[4]-a[4])+(b[5]-a[5])+(b[6]-a[6]))/dt))
        o["rollbacks"].append((rt, (b[1]-a[1])/dt))
        o["deadlocks"].append((rt, (b[7]-a[7])/dt))
        o["lockwait"].append((rt, b[9]))
        o["active"].append((rt, b[8]))
    return o

R = {t: rates(t) for t, _, _ in RUNS}

def line(title, fname, ylabel, key):
    plt.figure(figsize=(10,5))
    for tag, label, color in RUNS:
        s = R[tag][key]
        if s: plt.plot([p[0] for p in s], [p[1] for p in s], label=label, color=color, linewidth=1.9)
    plt.title(title); plt.xlabel("seconds since measurement start"); plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3); plt.legend(); plt.tight_layout()
    plt.savefig(f"{CMP}/{fname}", dpi=110); plt.close(); print("wrote", fname)

line("Postgres read rate  (rows returned + fetched / s)", "g_reads.png", "rows read / s", "reads")
line("Postgres write rate  (rows inserted + updated + deleted / s)", "g_writes.png", "rows written / s", "writes")

# health: lock-waiting backends (left) + rollbacks/s (right), both modes
fig, ax1 = plt.subplots(figsize=(10,5)); ax2 = ax1.twinx()
for tag, label, color in RUNS:
    lw, rb = R[tag]["lockwait"], R[tag]["rollbacks"]
    if lw: ax1.plot([p[0] for p in lw], [p[1] for p in lw], color=color, ls="-", lw=1.9, label=f"{label}: lock-waiters")
    if rb: ax2.plot([p[0] for p in rb], [p[1] for p in rb], color=color, ls="--", lw=1.5, label=f"{label}: rollbacks/s")
ax1.set_xlabel("seconds since measurement start"); ax1.set_ylabel("lock-waiting backends (solid)")
ax2.set_ylabel("rollbacks / s (dashed)"); ax1.grid(True, alpha=0.3)
l1, b1 = ax1.get_legend_handles_labels(); l2, b2 = ax2.get_legend_handles_labels()
ax1.legend(l1+l2, b1+b2, loc="upper left", fontsize=8)
plt.title("DB health / contention  (lock-waiting backends + rollback rate)")
plt.tight_layout(); plt.savefig(f"{CMP}/g_health.png", dpi=110); plt.close(); print("wrote g_health.png")

print("\n=== summary (mean / peak) ===")
def st(s): v=[x[1] for x in s]; return (sum(v)/len(v), max(v)) if v else (0,0)
for tag, label, _ in RUNS:
    u=st(util_series(tag)); rd=st(R[tag]["reads"]); wr=st(R[tag]["writes"])
    rb=st(R[tag]["rollbacks"]); lw=st(R[tag]["lockwait"]); dl=st(R[tag]["deadlocks"]); ac=st(R[tag]["active"])
    print(f"{label}: util {u[0]:.0f}/{u[1]:.0f}% | reads {rd[0]:.0f}/{rd[1]:.0f} | writes {wr[0]:.0f}/{wr[1]:.0f} "
          f"| rollbacks/s {rb[0]:.1f}/{rb[1]:.1f} | lock-wait {lw[0]:.1f}/{lw[1]:.0f} | deadlk/s {dl[0]:.2f} | active {ac[0]:.1f}/{ac[1]:.0f}")
