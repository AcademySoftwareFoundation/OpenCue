"""2x2 grid: {new,rust} x {compress2,compress8}. Steady-state medians (t90-180)."""
import os
import statistics as st
CMP = os.environ.get("SIM_BENCH_DIR", "/tmp/cmp2")
# logical tag -> file prefix
CELLS=[("new  @2","before"),("new  @8","new8"),("rust @2","rust2"),("rust @8","rust8")]
def sod(h):
    a=list(map(int,h.split(":"))); return a[0]*3600+a[1]*60+a[2]
def sim_t0(pre):
    try:
        for ln in open(f"{CMP}/{pre}_sim.log",errors="ignore"):
            if "] util=" in ln:
                return sod(ln[1:9])
    except FileNotFoundError: return None
    return None
def med_sim(pre,key,lo,hi):
    import re
    t0=sim_t0(pre)
    if t0 is None: return None
    rx=re.compile(r"\[(\d\d:\d\d:\d\d)\].*?"+key+r"=\s*([\d.]+)")
    v=[]
    for ln in open(f"{CMP}/{pre}_sim.log",errors="ignore"):
        m=rx.search(ln)
        if m:
            t=sod(m.group(1))-t0
            if lo<=t<=hi: v.append(float(m.group(2)))
    return st.median(v) if v else None
def med_csv(pre,suffix,colidx,lo,hi,rate=False):
    t0=sim_t0(pre)
    if t0 is None: return None
    try: rows=[ln.strip().split(",") for ln in open(f"{CMP}/{pre}_{suffix}.csv",errors="ignore")][1:]
    except FileNotFoundError: return None
    data=[]
    for r in rows:
        try: data.append((sod(r[0]),[float(x) for x in r[1:]]))
        except: pass
    if not data: return None
    v=[]
    if rate:
        for i in range(1,len(data)):
            (ta,a),(tb,b)=data[i-1],data[i]; dt=tb-ta
            if dt<=0: continue
            t=tb-t0
            if lo<=t<=hi: v.append((b[colidx]-a[colidx])/dt)
    else:
        for ts,c in data:
            t=ts-t0
            if lo<=t<=hi and colidx < len(c): v.append(c[colidx])
    return st.median(v) if v else None
# dbstat cols (after ts): 0 commits,1 rollbacks,2 tup_ret,3 tup_fetch,4 ins,5 upd,6 del,7 deadlk,8 active,9 lockwait
# cpu cols (after ts): 0 total_cpu%,1 cuebot,2 postgres,3 scheduler,4 python
LO,HI=90,180
print(f"{'cell':8} {'util%':>6} {'done/s':>7} {'orphan':>7} {'reads/s':>9} {'writes/s':>9} {'rollbk/s':>8} {'lockwt':>6} {'CPU%':>5} {'pg':>5} {'cuebot':>6} {'rust':>5} {'py':>5}")
for name,pre in CELLS:
    util=med_sim(pre,"util",LO,HI); done=med_sim(pre,"done/s",LO,HI); orp=med_sim(pre,"orphan",LO,HI)
    def rd(): 
        a=med_csv(pre,"dbstat",2,LO,HI,True); b=med_csv(pre,"dbstat",3,LO,HI,True)
        return (a+b) if (a is not None and b is not None) else None
    def wr():
        xs=[med_csv(pre,"dbstat",i,LO,HI,True) for i in (4,5,6)]
        return sum(x for x in xs if x is not None) if any(x is not None for x in xs) else None
    reads=rd(); writes=wr(); rb=med_csv(pre,"dbstat",1,LO,HI,True); lw=med_csv(pre,"dbstat",9,LO,HI,False)
    cpu=med_csv(pre,"cpu",0,LO,HI,False); pg=med_csv(pre,"cpu",2,LO,HI,False)
    cb=med_csv(pre,"cpu",1,LO,HI,False); ru=med_csv(pre,"cpu",3,LO,HI,False); py=med_csv(pre,"cpu",4,LO,HI,False)
    def f(x,d=0): return ("%.{}f".format(d)%x) if x is not None else "-"
    print(f"{name:8} {f(util):>6} {f(done):>7} {f(orp):>7} {f(reads):>9} {f(writes):>9} {f(rb,1):>8} {f(lw,2):>6} {f(cpu):>5} {f(pg,2):>5} {f(cb,2):>6} {f(ru,2):>5} {f(py,2):>5}")
