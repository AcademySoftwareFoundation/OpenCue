"""Poll cuebot's state and report scheduler-quality metrics over a run.

Read-only observation (via psql) of the live DB: utilization, frame packing
(co-locality), big-frame placement onto big hosts, throughput, and a
starvation check. Reservations live in the scheduler's memory and aren't
visible here; we infer contention behaviour from booking outcomes.
"""
import os
import sys
import time
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import farm_spec

PSQL = farm_spec.psql_cmd()
FARM_CP = farm_spec.total_cores() * 100  # honor SIM_HOST_COUNTS small-farm mode

DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 75
STEP = 2.0


def q(sql):
    out = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True).stdout
    return [r for r in out.strip().split("\n") if r != ""]


def scalar(sql, default=0):
    r = q(sql)
    try:
        return float(r[0]) if r else default
    except ValueError:
        return default


series = []
t0 = time.time()
print(f"sampling every {STEP}s for {DURATION}s ...", flush=True)

while time.time() - t0 < DURATION:
    booked = scalar("SELECT COALESCE(SUM(int_cores_reserved),0) FROM proc;")
    running = scalar("SELECT count(*) FROM frame WHERE str_state='RUNNING';")
    waiting = scalar("SELECT count(*) FROM frame WHERE str_state='WAITING' AND int_depend_count=0;")
    done = scalar("SELECT count(*) FROM frame WHERE str_state='SUCCEEDED';")
    hosts_busy = scalar("SELECT count(DISTINCT pk_host) FROM proc;")
    util = 100.0 * booked / FARM_CP
    series.append((time.time() - t0, util, running, waiting, done, hosts_busy))

    print(f"t={series[-1][0]:5.1f}s util={util:5.1f}% running={int(running):5d} "
          f"waiting={int(waiting):6d} done={int(done):6d} hostsBusy={int(hosts_busy)}/1553",
          flush=True)
    time.sleep(STEP)

# ---- final detailed snapshot ----
print("\n==== SUMMARY ====", flush=True)
peak = max(series, key=lambda s: s[1])
avg_util = sum(s[1] for s in series) / len(series)
print(f"utilization: peak {peak[1]:.1f}%  avg {avg_util:.1f}%  "
      f"(peak running {int(peak[2])} frames, hostsBusy {int(peak[5])}/1553)")
print(f"throughput: {int(series[-1][4])} frames completed in {DURATION}s")

print("\nco-locality (frame packing) at last sample:")
# frames-per-host per running layer: higher = better packing onto fewer hosts
rows = q("""SELECT coalesce(round(avg(fph),2),0), coalesce(round(max(fph),0),0) FROM (
              SELECT pk_layer, count(*)::float/count(distinct pk_host) AS fph
              FROM proc GROUP BY pk_layer) s;""")
vals = rows[0].split("|") if rows else ["0", "0"]
print(f"  avg frames-per-host per running layer: {vals[0]}  (max {vals[1]})")
tot = q("SELECT count(*), count(distinct pk_host) FROM proc;")
print(f"  running procs / busy hosts: {tot[0] if tot else 'n/a'}")

print("\nbig-frame placement (>=16-core frames) by host size:")
for row in q("""SELECT CASE WHEN h.int_cores>=12800 THEN 'large(128c)'
                            WHEN h.int_cores>=3200 THEN 'medium(32c)'
                            ELSE 'small(16c)' END AS host_type,
                       count(*) AS frames
                FROM proc p JOIN host h ON h.pk_host=p.pk_host
                WHERE p.int_cores_reserved>=1600 GROUP BY 1 ORDER BY 2 DESC;"""):
    print(f"  {row}")

print("\nutilization by host type (booked / capacity):")
for row in q("""SELECT CASE WHEN h.int_cores>=12800 THEN 'large(128c)'
                            WHEN h.int_cores>=3200 THEN 'medium(32c)'
                            ELSE 'small(16c)' END AS host_type,
                       count(*) AS hosts,
                       round(100.0*COALESCE(sum(p.cp),0)/sum(h.int_cores),1) AS pct
                FROM host h LEFT JOIN (
                       SELECT pk_host, sum(int_cores_reserved) cp FROM proc GROUP BY pk_host
                     ) p ON p.pk_host=h.pk_host
                GROUP BY 1 ORDER BY 1;"""):
    print(f"  {row}")

# Starvation: compare big (>=16-core) layers' progress to the whole job set.
# Uses completed-frame counts (durable) rather than instantaneous proc sampling.
print("\nbig-layer (>=16-core) progress:")
for row in q("""SELECT l.int_cores_min/100 AS cores,
                       count(DISTINCT l.pk_layer) AS layers,
                       SUM((SELECT count(*) FROM frame f WHERE f.pk_layer=l.pk_layer
                            AND f.str_state='WAITING')) AS waiting,
                       SUM((SELECT count(*) FROM frame f WHERE f.pk_layer=l.pk_layer
                            AND f.str_state='SUCCEEDED')) AS done
                FROM layer l WHERE l.int_cores_min>=1600 GROUP BY 1 ORDER BY 1;"""):
    print(f"  cores|layers|waiting|done = {row}")
