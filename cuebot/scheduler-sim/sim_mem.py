"""Per-frame ACTUAL RSS model for the fake RQD: the real memory map plus a tail.

A real RQD reports each running frame's ACTUAL resident memory (RSS), which is
NOT what the frame reserved. Submitters reserve a flat rule-of-thumb 4 GB/core
(sim_model.reserved_kb_for), but real usage follows the per-core memory map from
the farm CSV (sim_model.mem_gb_for_cores): a 1-core filer reserves 4 GB yet only
touches ~0.5 GB, an 8-16 core frame runs right at the 4 GB/core line, and a tail
runs OVER it. Those over-reservation frames are what drive cuebot's OOM machinery.
The old harness faked a flat 512 MB for every frame, so a host's summed RSS never
approached physical memory and the host-OOM balancer could never fire.

This models PEAK RSS the way a render actually behaves: a layer's frames are the
same scene at different times, so they cluster around ONE layer baseline. We draw
that baseline per LAYER, then wobble each frame a little around it. Deterministic
by layer/frame id, so the periodic host report (rqd_report.py) and the completion
report (fake_rqd.py) agree on a frame's number without sharing state:

    base      = mem_gb_for_cores(cores)                   (real average USAGE, GB)
    baseline  = lognormal(mean=base, sigma=SIM_RSS_SIGMA) (per-LAYER: the layer's
                                                           characteristic usage)
    peak_rss  = baseline * (1 +/- SIM_RSS_JITTER)         (per-FRAME wobble, ~10%)
                * rare heavy-tail multiplier              (per-frame leak frames)

The map is keyed on cores BOOKED (its CSV definition), so we key on the frame's
booked core-points too. Overboard (peak_rss above the flat reservation) is left
for cuebot to judge against what it booked: small jobs sit far under, big jobs
cross the line through the natural spread, and a small SIM_RSS_OVERBOARD_RATE tail
leaks far over. RSS ramps to the peak over the first SIM_RSS_RAMP_FRAC of the run,
then plateaus.

Tunables (env): SIM_RSS_SIGMA, SIM_RSS_JITTER, SIM_RSS_OVERBOARD_RATE,
SIM_RSS_OVERBOARD_MULT, SIM_RSS_RAMP_FRAC.
"""
import hashlib
import math
import os

import sim_model

GB_KB = 1024 * 1024

# cuebot launches a frame with soft_memory_limit = reserved * SOFT_MEMORY_MULTIPLIER
# (Dispatcher), so a frame's reserved memory is recoverable from the soft limit.
SOFT_MEMORY_MULTIPLIER = 1.6

RSS_SIGMA = float(os.environ.get("SIM_RSS_SIGMA", "0.5"))                    # spread of usage around the map average
RSS_OVERBOARD_RATE = float(os.environ.get("SIM_RSS_OVERBOARD_RATE", "0.03"))  # fraction that leak far over the peak
RSS_OVERBOARD_MULT = float(os.environ.get("SIM_RSS_OVERBOARD_MULT", "3.0"))   # up to N x the drawn peak
RSS_RAMP_FRAC = float(os.environ.get("SIM_RSS_RAMP_FRAC", "0.3"))            # reach peak by this fraction of runtime
RSS_JITTER = float(os.environ.get("SIM_RSS_JITTER", "0.10"))                 # per-frame +/- wobble around the layer baseline

_MEM_MAX_KB = int(480 * GB_KB)   # cap a single frame's RSS at the largest host's RAM


def _u(frame_id, salt):
    """Deterministic uniform [0,1) from a frame id + salt. Stable across processes
    and reports so the host report and the completion agree on a frame's RSS."""
    h = hashlib.md5(f"{frame_id}:{salt}".encode()).hexdigest()
    return int(h[:8], 16) / float(0x100000000)


def reserved_from_soft_limit(soft_limit_kb):
    """Recover a frame's reserved memory (kB) from the soft_memory_limit cuebot
    launched it with (reserved * SOFT_MEMORY_MULTIPLIER). 0 if unknown."""
    return int(soft_limit_kb / SOFT_MEMORY_MULTIPLIER) if soft_limit_kb and soft_limit_kb > 0 else 0


def peak_rss_kb(cores, frame_id, layer_id):
    """Per-frame PEAK actual RSS (kB), deterministic by layer + frame id.

    Two stages, matching how a render behaves: the frames of a layer are the same
    scene at different times, so they cluster around ONE baseline.
      1. LAYER baseline: draw the layer's characteristic usage once, keyed on the
         LAYER, from the real per-core usage map (the CSV "memory by cores booked")
         with a lognormal spread (RSS_SIGMA). Every frame of the layer resolves the
         same baseline.
      2. per-FRAME jitter: wobble each frame +/- RSS_JITTER (~10%) around that
         baseline, keyed on the FRAME, so frames vary a little but not wildly.
    A rare per-frame leak tail (one frame that blows up) stays per-frame.
    Independent of the (flat) reservation, so a whole layer sits near or over what
    it reserved together -- which is what drives cuebot's OOM machinery."""
    base_kb = sim_model.mem_gb_for_cores(max(1, cores)) * GB_KB
    # 1. LAYER baseline: lognormal with MEAN == base (mu = ln(mean) - sigma^2/2),
    # Box-Muller from two stable uniforms keyed on the LAYER, so every frame of the
    # layer resolves the identical baseline without sharing state.
    u1 = max(1e-9, _u(layer_id, "n1"))
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * _u(layer_id, "n2"))
    mu = math.log(base_kb) - 0.5 * RSS_SIGMA * RSS_SIGMA
    baseline = math.exp(mu + RSS_SIGMA * z)
    # 2. per-FRAME jitter: +/- RSS_JITTER around the layer baseline.
    rss = baseline * (1.0 + RSS_JITTER * (2.0 * _u(frame_id, "jit") - 1.0))
    # rare memory-leak tail: a small fraction of individual frames blow past the
    # baseline (a genuine per-frame leak), kept per-frame.
    if _u(frame_id, "ob") < RSS_OVERBOARD_RATE:
        rss *= 1.0 + _u(frame_id, "obm") * (RSS_OVERBOARD_MULT - 1.0)
    return max(1, int(min(_MEM_MAX_KB, rss)))


def rss_at(cores, frame_id, layer_id, elapsed_s, duration_s):
    """Current RSS (kB) elapsed_s into a frame of total duration_s: ramps from
    ~30% of the peak to the peak over the first SIM_RSS_RAMP_FRAC of the run, then
    plateaus. Falls back to the peak when the duration is unknown."""
    peak = peak_rss_kb(cores, frame_id, layer_id)
    if duration_s <= 0 or RSS_RAMP_FRAC <= 0:
        return peak
    frac = min(1.0, max(0.0, elapsed_s / (duration_s * RSS_RAMP_FRAC)))
    return max(1, int(peak * (0.3 + 0.7 * frac)))
