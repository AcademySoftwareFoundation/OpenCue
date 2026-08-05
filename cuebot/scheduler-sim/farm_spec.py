"""Render-farm spec for the OpenCue scheduler simulator.

Host counts/cores are the real farm. Nominal RAM is ~4 GB/core, but the memory
actually bookable by frames is LESS: the OS, RQD, monitoring agents and the
filesystem cache take a cut (see system_reserve in HOST_TYPES). That gap, plus
the heavy-tailed per-layer memory in sim_model, is what makes memory -- not
cores -- the binding constraint on real farms, so utilization never hits 100%
and memory-heavy layers get starved.
"""

GB_KB = 1024 * 1024          # 1 GB expressed in kB (cuebot host mem is kB)
CORES_PER_PROC = 100         # 100 core-points == 1 core

import hashlib
import os
import random

FACILITY = "sim"
ALLOC = "general"
TAG = "general"
SHOW = "sim"

# Connection config shared by every helper script, all overridable via SIM_*
# (matching simulate.py's defaults) so the whole harness agrees. No sudo: the
# scripts run as the same non-root user that started Postgres and cuebot, so
# anyone can run the simulator without root or a specific username.
GRPC = os.environ.get("SIM_CUEBOT_GRPC", "localhost:8443")
PG_BIN = os.environ.get("SIM_PG_BIN", "/usr/lib/postgresql/16/bin")
PG_PORT = os.environ.get("SIM_PG_PORT", "5433")
DB_HOST = os.environ.get("SIM_DB_HOST", "127.0.0.1")
DB_USER = os.environ.get("SIM_DB_USER", "cue")
DB_NAME = os.environ.get("SIM_DB_NAME", "cuebot")


def psql_cmd(tab=False):
    """psql argv for read-only queries. No sudo (runs as the current user);
    host/port/user/db come from SIM_* env so it matches simulate.py. tab=True
    selects a tab field separator (for scripts that split on it)."""
    cmd = [os.path.join(PG_BIN, "psql"), "-h", DB_HOST, "-p", str(PG_PORT),
           "-U", DB_USER, "-d", DB_NAME, "-A", "-t"]
    if tab:
        cmd += ["-F", "\t"]
    return cmd

# Capability tags -- RANDOM-pool model. SIM_NTAGS=N (N>=2) turns it on.
#
# This used to model machine CLASS: a clean small/med/large size hierarchy (big
# jobs to big boxes, small work anywhere). That partitions cleanly and does NOT
# fragment -- small work keeps the whole farm. Instead we now scatter N ARBITRARY
# capability tags at random across the machines, the way real sites tag
# licenses / projects / hardware quirks that don't line up with host size:
#
#   * each HOST gets ONE tag, cap{i}, by a stable hash of its name, so the N
#     pools are random ~1/N slices of the farm cutting across small/medium/large;
#   * each LAYER requests ONE tag with a HOT/COLD demand skew (weights
#     TAG_SKEW**i, via SIM_TAG_SKEW) among the pools that can fit it: a few
#     low-index tags pull most of the jobs while high-index tags stay cold (a
#     job is never made impossible, only confined);
#   * 'general' stays on every host so the allocation lookup resolves.
#
# Effect: hosts are spread evenly across pools but DEMAND is skewed, so the hot
# pools are oversubscribed (jobs pile up waiting) while the cold pools sit idle
# -- and a cold pool's idle cores can't be used by the hot pools' waiting work,
# because the tag confines it. That supply/demand imbalance strands cores and
# drops utilization (balanced/uniform tags do NOT: each pool is then a balanced
# mini-farm that just saturates on its own). It also multiplies the host-spec
# groups the planner scans. Matching is still enforced by cuebot's dispatch query
# (no scheduler change).
NTAGS = int(os.environ.get("SIM_NTAGS", "0") or "0")
TAGS_ON = NTAGS >= 2
# Demand-skew strength: job-tag weights are TAG_SKEW**i (pool 0 hottest). 1.0 =
# uniform (balanced, no fragmentation); smaller = steeper (cold pools approach
# zero demand and their hosts idle). The feeder over-submits to hold its backlog,
# so a gentle skew (e.g. 1/(i+1)) barely dents util -- the cold tail has to go
# near zero to actually strand cores, hence a steep default.
TAG_SKEW = float(os.environ.get("SIM_TAG_SKEW", "0.3"))


def _stable_frac(key):
    """Deterministic float in [0,1) from a string key."""
    h = hashlib.md5(key.encode()).hexdigest()
    return int(h[:8], 16) / float(0x100000000)


def host_pool(name):
    """This host's random capability-pool index in [0, NTAGS), stable by name."""
    return int(_stable_frac("cap:" + name) * NTAGS)


def host_tags(name):
    """'general' (for the allocation lookup) plus this host's ONE random
    capability tag, cap{i}. Just 'general' when tagging is off."""
    tags = [TAG]
    if TAGS_ON:
        tags.append(f"cap{host_pool(name)}")
    return tags


_POOL_CAPS = None


def _pool_caps():
    """{pool: (max_cores, max_usable_mem_kb)} over the hosts in each random pool,
    computed once from the farm spec. A layer can run in a pool only if that pool
    holds a host big enough for it."""
    global _POOL_CAPS
    if _POOL_CAPS is None:
        caps = {}
        for name, cores, mem_kb in all_hosts():
            p = host_pool(name)
            c, m = caps.get(p, (0, 0))
            caps[p] = (max(c, cores), max(m, mem_kb))
        _POOL_CAPS = caps
    return _POOL_CAPS


def layer_tag(cores, mem_kb):
    """A capability tag cap{i} for a layer, drawn among the pools that hold a host
    fitting it (cores AND usable memory); None when tagging is off. Demand is
    SKEWED, not uniform: low-index pools are "hot" (weights TAG_SKEW**i, set by
    SIM_TAG_SKEW), so a few tags pull most jobs while high-index pools stay cold.
    With tags spread evenly on HOSTS, the hot pools oversubscribe (work waits) and
    the cold pools idle (no eligible work) -- the imbalance that drops util.
    Feasibility-constrained so a job is only confined, never made impossible."""
    if not TAGS_ON:
        return None
    caps = _pool_caps()
    feasible = [p for p, (c, m) in caps.items() if cores <= c and mem_kb <= m]
    if not feasible:                      # wider than any host in any pool
        feasible = [max(caps, key=lambda p: caps[p][0])]
    weights = [TAG_SKEW ** p for p in feasible]   # exponential: pool 0 hottest
    return f"cap{random.choices(feasible, weights=weights, k=1)[0]}"

# (type name, count, cores, nominal_mem_GB, system_reserve_GB) -- the full farm.
# Usable RAM for frames = nominal - system_reserve. A "128 GB" box does not give
# frames 128 GB: the OS, RQD, monitoring agents and the filesystem cache take a
# cut (bigger boxes run more daemons/cache, so the reserve grows with size).
# Usable lands around 3.5-3.9 GB/core -- tight enough that the heavy-tailed
# per-layer memory (sim_model) strands cores instead of packing perfectly.
HOST_TYPES = [
    ("large",   246, 128, 512, 16),
    ("medium",  303,  32, 128, 12),
    ("small",  1004,  16,  64,  8),
]

# Small-farm override for quick, legible debugging runs. Set SIM_HOST_COUNTS to
# "large,medium,small" counts (e.g. "2,3,5") to keep the per-type core/mem shape but
# shrink the farm so booking dynamics are easy to watch. Every script that
# imports farm_spec then agrees on the same small farm.
_counts = os.environ.get("SIM_HOST_COUNTS")
if _counts:
    _c = [int(x) for x in _counts.split(",")]
    HOST_TYPES = [(t[0], _c[i], t[2], t[3], t[4]) for i, t in enumerate(HOST_TYPES)]


def all_hosts():
    """Yield (hostname, cores, usable_mem_kb) for every host in the farm.

    usable_mem = nominal - system_reserve (see HOST_TYPES): the RAM actually
    bookable by frames after the OS and host agents take their cut.
    """
    for type_name, count, cores, mem_gb, reserve_gb in HOST_TYPES:
        usable_kb = (mem_gb - reserve_gb) * GB_KB
        for i in range(1, count + 1):
            yield (f"{type_name}{i:04d}", cores, usable_kb)


def total_cores():
    return sum(count * cores for _, count, cores, _, _ in HOST_TYPES)


def total_hosts():
    return sum(count for _, count, _, _, _ in HOST_TYPES)


# GPU. SIM_GPU=F: F of the FARM is GPU-capable (drawn only from medium/small hosts --
# the 32c/16c machines), and F of layers are GPU layers (see sim_model). GPU
# placement is enforced entirely by cuebot's dispatch query (idle_gpus /
# idle_gpu_mem vs the layer's minGpus / minGpuMemory) -- no scheduler change.
# The point is to exercise the scheduler's GPU accounting, not GPU realism.
GPU_FRAC = float(os.environ.get("SIM_GPU", "0"))
GPU_HOST_TYPES = ("medium", "small")   # only the 32c/16c machines carry GPUs
GPU_CORES_PER_GPU = 4             # a GPU host gets cores/4 GPUs


def host_gpu(name, cores, usable_kb):
    """(num_gpus, total_gpu_mem_kb) for a host; (0, 0) if not GPU-capable.

    Deterministic per host name (stable hash) so register_hosts and rqd_report
    agree -- the heartbeat reports the same GPU spec every round. Only medium/small
    hosts are eligible; the per-eligible-host probability is scaled so the GPU
    hosts add up to GPU_FRAC of the WHOLE farm. GPU memory is 1:1 with the host's
    usable CPU memory (proportional, per the design)."""
    if GPU_FRAC <= 0:
        return (0, 0)
    type_name = name.rstrip("0123456789")
    if type_name not in GPU_HOST_TYPES:
        return (0, 0)
    eligible = sum(t[1] for t in HOST_TYPES if t[0] in GPU_HOST_TYPES)
    p = min(1.0, GPU_FRAC * total_hosts() / eligible) if eligible else 0.0
    if _stable_frac("gpu:" + name) < p:
        return (max(1, cores // GPU_CORES_PER_GPU), usable_kb)
    return (0, 0)
