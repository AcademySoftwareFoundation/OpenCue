# scheduler-sim analysis tooling

Ad-hoc benchmarking helpers for comparing scheduler modes (`--mode new|old|rust`)
under `simulate.py`. **Samplers** record DB/CPU load *during* a run; **plotters**
turn the recordings into graphs/tables *after*. The driver writes nothing to the
repo — point everything at a scratch dir.

All plotters read from `$SIM_BENCH_DIR` (default `/tmp/cmp2`) and expect files
named `<tag>_dbstat.csv`, `<tag>_cpu.csv`, `<tag>_sim.log` per run.

## Samplers (run in the background, alongside `simulate.py`)

- `db_sampler.py <out.csv>` — every 2s, snapshots `pg_stat_database`
  (commits/rollbacks, tuples read/written, deadlocks) + `pg_stat_activity`
  (active backends, lock-waiters). Honors `SIM_PG_HOST`/`SIM_PG_PORT`.
- `cpu_sampler.py <out.csv>` — every 3s, total CPU% + per-process cores for
  cuebot (java), postgres, cue-scheduler, python (from `/proc`).

```bash
BENCH=/tmp/bench; mkdir -p $BENCH
python analysis/db_sampler.py  $BENCH/new_dbstat.csv &
python analysis/cpu_sampler.py $BENCH/new_cpu.csv &
python simulate.py --mode new --feed 240 --stats 90 > $BENCH/new_sim.log 2>&1
kill %1 %2
```

## Plotters / analyzers (run after; `SIM_BENCH_DIR=$BENCH`)

- `make_graphs.py` — NEW vs RUST: 3 graphs (reads/s, writes/s, DB
  health = lock-waiters + rollbacks). Tags: `new`, `rust`.
- `make_graphs_ba.py` — before vs after: same 3 graphs. Tags: `before`, `after`.
- `analyze_sweep.py` — prints a steady-state median table for the 2×2 grid
  {new,rust}×{compress2,compress8}. Tags: `before`, `new8`, `rust2`, `rust8`.

```bash
SIM_BENCH_DIR=$BENCH python analysis/make_graphs.py     # writes g_*.png
SIM_BENCH_DIR=$BENCH python analysis/analyze_sweep.py   # prints table
```

Generated `*.csv` / `*.png` are gitignored.
