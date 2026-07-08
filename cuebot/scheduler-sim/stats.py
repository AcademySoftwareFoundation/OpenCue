"""Scheduler assessment: per-host-type utilization + frame mix + throughput.

Read-only DB sampling. Reports the numbers that actually answer "is the
scheduler using the farm well?": cores booked vs capacity overall AND per host
type (large/medium/small), running-frame size mix, throughput, and the overbooking
(host-resource trigger) rejection rate from the cuebot log.

usage: stats.py [duration_s]
"""
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import farm_spec
PSQL = farm_spec.psql_cmd()
FARM_CP = farm_spec.total_cores() * 100  # honor SIM_HOST_COUNTS small-farm mode
DURATION = int(sys.argv[1]) if len(sys.argv) > 1 else 120
STEP = 3.0

def q(sql):
    out = subprocess.run(PSQL+["-c",sql], capture_output=True, text=True, timeout=20).stdout
    return [r for r in out.strip().split("\n") if r != ""]
def scalar(sql, d=0):
    r = q(sql)
    try: return float(r[0]) if r else d
    except ValueError: return d
def reject_count():
    try:
        return int(subprocess.run(["bash","-c","grep -c 'unable to allocate' /tmp/cuebot.log || true"],
                   capture_output=True, text=True).stdout.strip() or 0)
    except Exception: return 0

def db_stats():
    """Snapshot cumulative Postgres activity for the cuebot DB (efficiency cost)."""
    sql=("SELECT xact_commit, xact_rollback, tup_fetched, tup_inserted, "
         "tup_updated, tup_deleted FROM pg_stat_database WHERE datname='cuebot';")
    r=q(sql)
    if not r: return None
    c=r[0].split("|")
    return {"commit":int(c[0]),"rollback":int(c[1]),"fetched":int(c[2]),
            "inserted":int(c[3]),"updated":int(c[4]),"deleted":int(c[5])}

series=[]; t0=time.time(); rej0=reject_count(); db0=db_stats()
print(f"sampling {DURATION}s every {STEP}s  (farm={FARM_CP//100} cores)\n", flush=True)
print(f"{'t':>4} {'live%':>6} {'use%':>6} {'large%':>7} {'medium%':>6} {'small%':>6} "
      f"{'run':>6} {'wait':>7} {'done':>7} {'busy':>5} {'zomb':>6} {'rej/s':>6}", flush=True)
prev_done=None; prev_rej=rej0
while time.time()-t0 < DURATION:
    booked=scalar("SELECT COALESCE(SUM(int_cores_reserved),0) FROM proc;")
    # HONEST utilization: cores held by procs that actually back a RUNNING frame.
    # 'booked' includes zombie procs (pk_frame NULL) that hold cores but do no
    # work; 'live' excludes them so util reflects real running work.
    live=scalar("SELECT COALESCE(SUM(int_cores_reserved),0) FROM proc WHERE pk_frame IS NOT NULL;")
    # USEFUL cores: what the frames actually requested (layer.int_cores_min). The
    # gap live-useful is memory-padding -- cores cuebot reserves to fence off RAM
    # but that do no compute. This is the REAL utilization (NEW and OLD alike).
    useful=scalar("SELECT COALESCE(SUM(l.int_cores_min),0) FROM proc p "
                  "JOIN layer l ON l.pk_layer=p.pk_layer WHERE p.pk_frame IS NOT NULL;")
    zomb=scalar("SELECT count(*) FROM proc WHERE pk_frame IS NULL;")
    run=scalar("SELECT count(*) FROM frame WHERE str_state='RUNNING';")
    wait=scalar("SELECT count(*) FROM frame WHERE str_state='WAITING' AND int_depend_count=0;")
    done=scalar("SELECT count(*) FROM frame WHERE str_state='SUCCEEDED';")
    busy=scalar("SELECT count(DISTINCT pk_host) FROM proc;")
    # per host type util
    pt={"large(128c)":0.0,"medium(32c)":0.0,"small(16c)":0.0}
    for row in q("""SELECT CASE WHEN h.int_cores>=12800 THEN 'large(128c)'
                              WHEN h.int_cores>=3200 THEN 'medium(32c)' ELSE 'small(16c)' END t,
                       round(100.0*COALESCE(sum(p.cp),0)/sum(h.int_cores),1)
                FROM host h LEFT JOIN (SELECT pk_host, sum(int_cores_reserved) cp FROM proc GROUP BY pk_host) p
                  ON p.pk_host=h.pk_host GROUP BY 1;"""):
        c=row.split("|");  pt[c[0]]=float(c[1]) if len(c)>1 and c[1] else 0.0
    util=100.0*booked/FARM_CP
    liveutil=100.0*live/FARM_CP
    usefulutil=100.0*useful/FARM_CP
    rej=reject_count(); rps=(rej-prev_rej)/STEP; prev_rej=rej
    el=time.time()-t0
    series.append((el,util,pt["large(128c)"],pt["medium(32c)"],pt["small(16c)"],run,wait,done,busy,liveutil,zomb,usefulutil))
    print(f"{el:4.0f} {liveutil:6.1f} {usefulutil:6.1f} {pt['large(128c)']:7.1f} {pt['medium(32c)']:6.1f} "
          f"{pt['small(16c)']:6.1f} {int(run):6d} {int(wait):7d} {int(done):7d} "
          f"{int(busy):5d} {int(zomb):6d} {rps:6.0f}", flush=True)
    time.sleep(STEP)

print("\n==== ASSESSMENT ====")
peak=max(series,key=lambda s:s[9]); avg=sum(s[9] for s in series)/len(series)
zmax=max(s[10] for s in series)
# Separate ramp from steady state: time to first reach 95% live util, and the
# average live util AFTER that point (sustain quality, ramp excluded).
SAT=95.0
sat=next((s for s in series if s[9]>=SAT), None)
if sat:
    tail=[s for s in series if s[0]>=sat[0]]
    ssavg=sum(s[9] for s in tail)/len(tail)
    print(f"time-to-saturate (first live>= {SAT:.0f}%): {sat[0]:.0f}s")
    print(f"steady-state avg live util (after saturate): {ssavg:.1f}%  "
          f"(min {min(s[9] for s in tail):.1f}% over {len(tail)} samples)")
else:
    print(f"time-to-saturate (first live>= {SAT:.0f}%): NEVER reached in window")
uavg=sum(s[11] for s in series)/len(series); upeak=max(s[11] for s in series)
print(f"HONEST utilization (cores backing RUNNING frames): peak {peak[9]:.1f}%  avg {avg:.1f}%")
print(f"REAL utilization (cores frames actually compute on, excl. memory padding): "
      f"peak {upeak:.1f}%  avg {uavg:.1f}%")
print(f"  memory-padding waste: {avg-uavg:.1f} pts of 'util' are idle cores fenced off for RAM")
print(f"zombie procs (pk_frame NULL, holding cores, doing no work): peak {int(zmax)}")
if zmax > 50:
    print(f"  *** PROC LEAK DETECTED: {int(zmax)} dead reservations hold cores but back no running frame ***")
print(f"  at honest peak: large {peak[2]:.0f}%  medium {peak[3]:.0f}%  small {peak[4]:.0f}%  "
      f"busyHosts {int(peak[8])}/1553")
jmax=max(s[2] for s in series); rmax=max(s[3] for s in series); emax=max(s[4] for s in series)
print(f"per-type peak util: large {jmax:.0f}%  medium {rmax:.0f}%  small {emax:.0f}%")
thru=(series[-1][7]-series[0][7])/(series[-1][0]-series[0][0] or 1)
completed=int(series[-1][7]-series[0][7])
print(f"throughput: {thru:.0f} frames/s  ({completed} completed in window)")
print(f"overbooking rejections during window: {reject_count()-rej0}")

# DB load (efficiency cost): delta of Postgres activity over the window.
db1=db_stats(); wall=series[-1][0]-series[0][0] or 1
if db0 and db1:
    dC=db1["commit"]-db0["commit"]; dR=db1["rollback"]-db0["rollback"]
    dF=db1["fetched"]-db0["fetched"]; dI=db1["inserted"]-db0["inserted"]
    dU=db1["updated"]-db0["updated"]; dD=db1["deleted"]-db0["deleted"]
    rowops=dI+dU+dD
    per=lambda x: x/completed if completed else 0
    print("\nDB load (Postgres activity over window — efficiency cost):")
    print(f"  transactions: {dC} commit + {dR} rollback  ({dC/wall:.0f}/s, "
          f"{per(dC):.1f}/frame)")
    print(f"  row writes:   {dI} ins + {dU} upd + {dD} del = {rowops}  "
          f"({rowops/wall:.0f}/s, {per(rowops):.1f}/frame)")
    print(f"  rows fetched: {dF}  ({dF/wall:.0f}/s, {per(dF):.0f}/frame)")
# GPU accounting (only if the farm has GPUs). Verifies the scheduler reserves
# GPUs/gpu-mem and -- critically -- never places a GPU frame on a non-GPU host.
gpu_cap=scalar("SELECT COALESCE(sum(int_gpus),0) FROM host;")
if gpu_cap>0:
    gpu_hosts=scalar("SELECT count(*) FROM host WHERE int_gpus>0;")
    gpu_resv=scalar("SELECT COALESCE(sum(int_gpus_reserved),0) FROM proc WHERE pk_frame IS NOT NULL;")
    gpu_run=scalar("SELECT count(*) FROM proc WHERE int_gpus_reserved>0 AND pk_frame IS NOT NULL;")
    gpu_mem_cap=scalar("SELECT COALESCE(sum(int_gpu_mem),0) FROM host;")
    gpu_mem_resv=scalar("SELECT COALESCE(sum(int_gpu_mem_reserved),0) FROM proc WHERE pk_frame IS NOT NULL;")
    # CORRECTNESS: a GPU proc must never land on a host with no GPUs.
    misplaced=scalar("SELECT count(*) FROM proc p JOIN host h ON h.pk_host=p.pk_host "
                     "WHERE p.int_gpus_reserved>0 AND h.int_gpus=0;")
    print("\nGPU accounting (last sample):")
    print(f"  GPU hosts: {int(gpu_hosts)}  GPU units: {int(gpu_cap)}  "
          f"reserved: {int(gpu_resv)} ({100.0*gpu_resv/gpu_cap:.1f}%)  "
          f"running GPU frames: {int(gpu_run)}")
    print(f"  GPU mem: reserved {gpu_mem_resv/1048576:.0f} GB of {gpu_mem_cap/1048576:.0f} GB "
          f"({100.0*gpu_mem_resv/gpu_mem_cap if gpu_mem_cap else 0:.1f}%)")
    if misplaced>0:
        print(f"  *** CORRECTNESS BUG: {int(misplaced)} GPU procs on non-GPU hosts ***")
    else:
        print(f"  correctness OK: 0 GPU procs on non-GPU hosts")
print("\nrunning-frame size mix (last sample):")
for row in q("""SELECT int_cores_reserved/100 AS cores, count(*) FROM proc GROUP BY 1 ORDER BY 1;"""):
    print(f"  {row.replace('|',' cores: ')}")
print("\nco-locality (frames per busy host, last sample):")
print(f"  {q('SELECT count(*), count(distinct pk_host) FROM proc;')}")
