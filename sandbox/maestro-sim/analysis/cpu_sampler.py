import time, os, sys, glob
OUT=sys.argv[1]; CLK=os.sysconf("SC_CLK_TCK")
def snap():
    f=open("/proc/stat").readline().split()[1:]
    idle=int(f[3])+int(f[4]); tot=sum(int(x) for x in f)
    g={"cuebot":0,"postgres":0,"scheduler":0,"python":0}
    for p in glob.glob("/proc/[0-9]*/stat"):
        try:
            d=open(p).read(); comm=d.split("(",1)[1].rsplit(")",1)[0]
            r=d.rsplit(")",1)[1].split(); j=int(r[11])+int(r[12])
            if comm=="java": g["cuebot"]+=j
            elif comm.startswith("postgres"): g["postgres"]+=j
            elif comm=="cue-scheduler": g["scheduler"]+=j
            elif comm.startswith("python"): g["python"]+=j
        except: pass
    return tot,idle,g
pt,pi,pg=snap(); pT=time.time()
open(OUT,"w").write("ts,total_cpu_pct,cuebot_cores,postgres_cores,scheduler_cores,python_cores\n")
while True:
    time.sleep(3); t,i,g=snap(); now=time.time(); dt=now-pT; dtot=t-pt
    cpu=100.0*(dtot-(i-pi))/dtot if dtot>0 else 0
    c=lambda k:(g[k]-pg[k])/CLK/dt if dt>0 else 0
    open(OUT,"a").write(f"{time.strftime('%H:%M:%S')},{cpu:.1f},{c('cuebot'):.2f},{c('postgres'):.2f},{c('scheduler'):.2f},{c('python'):.2f}\n")
    pt,pi,pg,pT=t,i,g,now
