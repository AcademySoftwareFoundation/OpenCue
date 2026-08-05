"""Frame distribution model derived from the real-farm CSVs.

Per-core-bucket: share of frame COUNT, average memory, and average clock
minutes. Layers (not frames) carry cores/mem in OpenCue, so we sample a core
bucket per layer. Durations are compressed real-minutes -> sim-seconds so the
run completes quickly while preserving the "big frames run longer" shape.
"""
import math
import random

# cores, %count, mem_GB, clock_minutes   (covers ~99.4% of real frames)
BUCKETS = [
    (1,  22.89,  0.52,  2.31),
    (2,  25.54,  1.38,  4.70),
    (4,  34.22,  6.44, 11.38),
    (8,  14.55, 27.27, 30.14),
    (16,  1.88, 63.85, 52.43),
    (32,  0.28, 109.0, 47.98),
    (64,  0.03, 233.12, 40.26),
]

# real-minute -> sim-second compression (4-core ~11 min -> ~3 s)
import os

# real-minute -> sim-second compression. 0.27 makes a 4-core (~11 min) frame run
# ~3 s, which is great for a quick run BUT demands a frame-lifecycle rate
# (~4000/s to keep 1553 hosts full) far above what one cuebot+DB sustains
# (~120/s here). That ceiling, not the scheduler, caps utilization once
# completions are reported concurrently. Raise COMPRESS (longer frames) so the
# required lifecycle rate stays under the ceiling and the farm can actually fill.
# Override per-run with the SIM_COMPRESS env var.
COMPRESS = float(os.environ.get("SIM_COMPRESS", "0.27"))
MIN_SECONDS = 0.5

_cores = [b[0] for b in BUCKETS]
_weights = [b[1] for b in BUCKETS]
_mem_gb = {b[0]: b[2] for b in BUCKETS}
_minutes = {b[0]: b[3] for b in BUCKETS}

GB_KB = 1024 * 1024
CORE_POINTS = 100


def sample_layer_cores():
    """Return a core count for one layer, weighted by real frame share.

    With SIM_MEM_HEAVY_GB set (the low-utilization test) the draw is restricted
    to the small buckets (<= SIM_MEM_HEAVY_MAX_CORES). Those layers are also made
    memory-heavy (see mem_kb_for), so the workload becomes a flood of small,
    memory-hungry jobs with no core-dense work to fall back on: the farm goes
    memory-bound and strands cores, exactly the low-utilization regime we want to
    reproduce. (Without this skew the scheduler simply dodges the heavy small
    jobs, fills cores with balanced 8+ core work, and utilization stays high
    while the heavy jobs starve.)"""
    cores, weights = _cores, _weights
    if MEM_HEAVY_GB > 0:
        small = [(c, w) for c, w in zip(_cores, _weights) if c <= MEM_HEAVY_MAX_CORES]
        cores, weights = [c for c, _ in small], [w for _, w in small]
    return random.choices(cores, weights=weights, k=1)[0]


# Per-layer memory variation. Real frames of the same core count vary widely in
# memory, so we sample each layer's reserved memory from a right-skewed lognormal
# whose MEAN is the bucket's average. The heavy tail means a meaningful share of
# layers want more RAM than the host's GB/core ratio and strand cores
# (memory-bound) -- which is why real farms never reach 100% and why big-memory
# layers get starved. Tune the spread with SIM_MEM_SIGMA (sigma of the
# underlying normal); 0.5 gives p50~=0.88x, p90~=1.7x, p99~=2.8x of the mean.
MEM_SIGMA = float(os.environ.get("SIM_MEM_SIGMA", "0.5"))
_MEM_MIN_KB = int(0.25 * GB_KB)        # floor: no layer reserves under 256 MB
_MEM_MAX_KB = int(480 * GB_KB)         # ceiling: must still fit the largest host

# Low-utilization test (SIM_MEM_HEAVY_GB > 0): make small-core layers
# memory-heavy, breaking the memory-tracks-cores assumption that lets the farm
# pack to ~100%. Hosts run ~3.5-3.9 GB usable per core, so a 1-4 core layer that
# wants, say, 32 GB exhausts a host's RAM long before its cores and strands the
# rest of the cores (memory-bound), exactly the way real memory-hungry work does.
# Sets the MEAN reserved memory (GB) for layers at or below
# SIM_MEM_HEAVY_MAX_CORES cores; the usual lognormal spread still applies on top.
# Off (0) by default.
MEM_HEAVY_GB = float(os.environ.get("SIM_MEM_HEAVY_GB", "0"))
MEM_HEAVY_MAX_CORES = int(os.environ.get("SIM_MEM_HEAVY_MAX_CORES", "4"))
# Memory-hog jobs are RAM-bound, not compute-bound, so in the real world they run
# single-threaded; we mark them non-threadable under the mem-heavy test. Without
# this a threadable frame grabs idle cores and expands to fill the host, hiding
# the memory binding (the few frames that fit on memory still soak up every core)
# and utilization stays pinned near 100%. Non-threadable, a frame uses exactly
# its reserved cores, so once host RAM is exhausted the leftover cores strand.
# SIM_THREADABLE (0/1) overrides this to study packing with/without grab-idle
# expansion independently of the mem-heavy test.
THREADABLE = int(os.environ.get("SIM_THREADABLE", "0" if MEM_HEAVY_GB > 0 else "1"))


def mem_kb_for(cores):
    """Sample reserved memory (kB) for one layer of the given core count.

    Lognormal with mean == the bucket's average memory (mu = ln(mean) -
    sigma^2/2). Clamped to [256 MB, 480 GB] so nothing is unschedulable.
    Deterministic given the RNG seed, so runs are reproducible. With
    SIM_MEM_HEAVY_GB set, small-core layers instead center on that GB mean so
    they go memory-bound and strand cores (the low-utilization test).
    """
    mean_gb = _mem_gb[cores]
    if MEM_HEAVY_GB > 0 and cores <= MEM_HEAVY_MAX_CORES:
        mean_gb = MEM_HEAVY_GB
    mean_kb = mean_gb * GB_KB
    mu = math.log(mean_kb) - 0.5 * MEM_SIGMA * MEM_SIGMA
    sample = random.lognormvariate(mu, MEM_SIGMA)
    return int(min(_MEM_MAX_KB, max(_MEM_MIN_KB, sample)))


# --- Reservation vs actual usage -------------------------------------------
# These are two DIFFERENT numbers, and conflating them is what hides real OOM
# behaviour:
#
#   reserved_kb_for(cores)  -- what the SUBMITTER books. Production submitters use
#       a flat rule of thumb of RESERVED_GB_PER_CORE per core regardless of what a
#       frame will really use, so a 1-core filer that only touches ~0.5 GB still
#       reserves 4 GB. cuebot places on this (int_mem_min), so at 4 GB/core against
#       ~3.5-3.9 GB usable per core the farm runs out of RAM before cores: memory
#       bound, exactly like production.
#
#   mem_gb_for_cores(cores) -- what a frame ACTUALLY uses on the host: the real
#       per-core average from the farm memory map (BUCKETS). The fake RQD reports
#       RSS from this (see sim_mem), so a host's summed RSS is its true memory
#       pressure and cuebot's OOM machinery sees the same picture as in production.
RESERVED_GB_PER_CORE = float(os.environ.get("SIM_RESERVED_GB_PER_CORE", "4"))


def reserved_kb_for(cores):
    """Memory (kB) a submitter reserves for one layer of `cores` cores: a flat
    RESERVED_GB_PER_CORE per core, clamped to the schedulable range. With
    SIM_MEM_HEAVY_GB set, small-core layers instead reserve that heavy mean (with
    the usual lognormal spread) so they go memory-bound and strand cores, exactly
    as before -- the low-utilization test is unchanged."""
    if MEM_HEAVY_GB > 0 and cores <= MEM_HEAVY_MAX_CORES:
        mean_kb = MEM_HEAVY_GB * GB_KB
        mu = math.log(mean_kb) - 0.5 * MEM_SIGMA * MEM_SIGMA
        sample = random.lognormvariate(mu, MEM_SIGMA)
        return int(min(_MEM_MAX_KB, max(_MEM_MIN_KB, sample)))
    return int(min(_MEM_MAX_KB, max(_MEM_MIN_KB, RESERVED_GB_PER_CORE * cores * GB_KB)))


def mem_gb_for_cores(cores):
    """Average ACTUAL frame memory (GB) for a layer of `cores` cores booked, from
    the real memory map (BUCKETS). This is real USAGE, not the reservation. Exact
    at the known buckets; linear-interpolates between them and extrapolates past
    the largest at its per-core rate, so any core count maps to a sensible mean."""
    if cores in _mem_gb:
        return _mem_gb[cores]
    lo = hi = None
    for c in _cores:                       # _cores is ascending
        if c <= cores:
            lo = c
        if c >= cores and hi is None:
            hi = c
    if lo is None:                         # below the smallest bucket
        return _mem_gb[_cores[0]] * cores / _cores[0]
    if hi is None:                         # above the largest: extrapolate per-core
        return _mem_gb[_cores[-1]] * cores / _cores[-1]
    if lo == hi:
        return _mem_gb[lo]
    frac = (cores - lo) / float(hi - lo)
    return _mem_gb[lo] + frac * (_mem_gb[hi] - _mem_gb[lo])


# GPU layers. SIM_GPU=F: a fraction F of layers are GPU layers. A GPU layer runs
# mostly on the GPU, so it asks for few software cores (GPU_CORES) and 1 GPU; its
# GPU memory is sampled from the same mem model and its CPU memory is half that.
# gpu_memory must stay under cuebot's mem_gpu_reserved_max (100 GB) or the job is
# REJECTED (cuebot throws, unlike CPU memory which clamps), so we cap at 90 GB.
GPU_FRAC = float(os.environ.get("SIM_GPU", "0"))
GPU_CORES = 4
_GPU_MEM_MAX_KB = int(90 * GB_KB)


def is_gpu_layer():
    """True for a fraction GPU_FRAC of layers. Short-circuits when GPU is off so
    a non-GPU run draws the RNG identically to before (stays reproducible)."""
    return GPU_FRAC > 0 and random.random() < GPU_FRAC


def gpu_layer_kb():
    """(cores, gpu_mem_kb, cpu_mem_kb) for one GPU layer: GPU_CORES software
    cores, gpu memory sampled from the mem model (capped), and CPU memory reserved
    by the same flat per-core rule as everything else (reserved_kb_for)."""
    gpu_mem = min(_GPU_MEM_MAX_KB, mem_kb_for(GPU_CORES))
    cpu_mem = reserved_kb_for(GPU_CORES)
    return GPU_CORES, gpu_mem, cpu_mem


def duration_seconds(core_points):
    """Sim run-time for a frame given its reserved core points (100 == 1 core)."""
    cores = max(1, core_points // CORE_POINTS)
    # nearest known bucket
    nearest = min(_cores, key=lambda c: abs(c - cores))
    return max(MIN_SECONDS, _minutes[nearest] * COMPRESS)
