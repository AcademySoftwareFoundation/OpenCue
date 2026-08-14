"""Render cue_scheduler_fragmented_cores{reason} (a frag_watch.py CSV) as the
stacked bars-by-cause view -- the same panel as the Grafana Fragmentation graph.

usage: frag_plot.py <run_frag.csv> [out.png]
"""
import csv
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

REASONS = [("packing", "#E8873A"), ("memory", "#D1443B"),
           ("resource", "#8E5FC7"), ("cap", "#3E7CB1")]

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else src.rsplit(".", 1)[0] + ".png"

t, data = [], {r: [] for r, _ in REASONS}
with open(src) as f:
    for row in csv.DictReader(f):
        t.append(float(row["t"]))
        for r, _ in REASONS:
            data[r].append(float(row.get(r, 0.0)))

BG, FG, GRID, MUT = "#0d1218", "#d6dee8", "#242f3b", "#8b97a5"
fig, ax = plt.subplots(figsize=(12, 5.2), dpi=150)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

x = np.arange(len(t))
bottom = np.zeros(len(t))
for reason, color in REASONS:
    vals = np.array(data[reason])
    ax.bar(x, vals, bottom=bottom, width=0.92, color=color, edgecolor=BG,
           linewidth=0.3, label=reason)
    bottom += vals

ax.set_title("Scheduler fragmentation by cause", color=FG, fontsize=15,
             fontweight="bold", loc="left", pad=12)
ax.text(0, 1.045, "cue_scheduler_fragmented_cores{reason}  ·  live simulator run",
        transform=ax.transAxes, color=MUT, fontsize=9.5)
ax.set_xlabel("time in run", color=MUT, fontsize=10)
ax.set_ylabel("blocked work  (cores)", color=MUT, fontsize=10)
step = max(1, len(t) // 12)
ax.set_xticks(x[::step])
ax.set_xticklabels([f"{int(t[i])}s" for i in x[::step]], fontsize=8)
for s in ax.spines.values():
    s.set_color(GRID)
ax.tick_params(colors=MUT)
ax.set_axisbelow(True)
ax.yaxis.grid(True, color=GRID, linewidth=0.7)
ax.xaxis.grid(False)
ax.margins(x=0.01)
handles = [Patch(facecolor=c, label=r) for r, c in REASONS]
ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=10,
          labelcolor=FG, ncol=4, bbox_to_anchor=(0, -0.13))
fig.tight_layout()
fig.savefig(out, facecolor=BG, bbox_inches="tight")
print("wrote", out)
