// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

//! Layer-to-host placement primitives shared by every host-booking strategy.
//!
//! `LayerProfile` is the data-only snapshot of a layer needed to make a
//! placement decision. Gate functions operate on `(&Host, &LayerProfile)`
//! so the host cache actor can be parameterized by a plain `fn` pointer
//! instead of a closure.

use bytesize::ByteSize;
use opencue_proto::host::ThreadMode;

use crate::{
    config::ScoreWeights,
    models::{CoreSize, Host},
};

/// Snapshot of a layer's placement-relevant state.
///
/// Floor + compatibility fields are read by every strategy. The E-PVM context
/// (job/show caps, live usage counters, weights) is only consumed by
/// `epvm_gate / placement_score` and ignored by the Saturation path.
///
/// `job_max_cores` and `show_burst` use the OpenCue convention of `<= 0` meaning
/// "unlimited" cap clamps in `compute_max_more` skip those dimensions, matching
/// the accounting `> 0` cap guard.
#[derive(Debug, Clone)]
pub struct LayerProfile {
    // Floor
    pub cores_min: CoreSize,
    pub mem_min: ByteSize,
    pub gpus_min: i32,
    pub gpu_mem_min: ByteSize,
    // Slot-based scheduling: `> 0` marks the layer slot-based. A slot layer only
    // matches slot-based hosts, and cores/memory floors are ignored on those hosts.
    pub slots_required: u32,
    // Compatibility
    pub os: Option<String>,
    pub threadable: bool,
    // E-PVM context (snapshot at process_layer entry + locally decremented
    // per dispatched frame each iteration).
    pub job_max_cores: i32,
    pub show_burst: i32,
    pub job_cores_in_use: i32,
    pub show_cores_in_use: i32,
    pub weights: ScoreWeights,
}

/// True when the layer has no OS requirement or the host's OS matches it.
pub fn host_matches_layer_os(host: &Host, profile: &LayerProfile) -> bool {
    profile.os.is_none() || host.str_os.as_deref() == profile.os.as_deref()
}

/// Mirrors Cuebot's DispatchQuery filter: hosts in ThreadMode::All only accept
/// threadable layers. Booking a non-threadable layer on such a host would
/// diverge from Cuebot's behavior and starve the layer when ownership of the
/// show moves back to Cuebot.
pub fn host_matches_thread_mode(host: &Host, profile: &LayerProfile) -> bool {
    host.thread_mode != ThreadMode::All || profile.threadable
}

/// Sync per-host validation invoked from the host_cache actor. Checks OS and
/// thread-mode compatibility.
pub fn validate_os_and_thread_mode(host: &Host, profile: &LayerProfile) -> bool {
    host_matches_layer_os(host, profile) && host_matches_thread_mode(host, profile)
}

/// True when the host's idle resources meet the layer's floor on every
/// dimension. Per Branch 4 (G1) the GPU floor lives in the gate, not the
/// B-tree index — both `cores`/`mem` (range hints) and `gpus`/`gpu_mem`
/// (predicate-only) are checked here for completeness.
pub fn fits_floor(host: &Host, profile: &LayerProfile) -> bool {
    host.idle_cores >= profile.cores_min
        && host.idle_memory >= profile.mem_min
        && (host.idle_gpus as i32) >= profile.gpus_min
        && host.idle_gpu_memory >= profile.gpu_mem_min
}

/// Predicts the number of ADDITIONAL frames of the layer (beyond the first
/// one being booked this tick) that could be dispatched to the same host
/// within this same tick.
///
/// # How the bound is built
///
/// The result is the minimum of up to six independent bounds — four physical
/// ones (cores, memory, GPUs, GPU memory) and two core-denominated caps
/// (`job_max_cores`, `show_burst`). Each bound asks the same question in its
/// own units: "after the first frame's `min` has been reserved, how many more
/// `min`-sized chunks fit before this resource is exhausted?"
///
/// A bound is *omitted* from the minimum (rather than contributing 0) when:
///   - a physical `<dim>_min` is 0 — the layer makes no demand on that dim,
///     so the dim cannot constrain anything; or
///   - a cap is `<= 0` — OpenCue's "unlimited" sentinel (mirrors the Lua
///     `> 0` cap guard); or
///   - the layer has no core demand (`cores_min == 0`), in which case the
///     core-denominated caps have no unit to divide by.
///
/// # Degenerate and stale input
///
/// If every bound is omitted (no demand on any dim), the function returns 0
/// rather than `i64::MAX` — there is no meaningful notion of "one more frame"
/// to report.
///
/// Live-usage counters can briefly exceed their cap (stale snapshot or
/// compensation rollback in flight). The matcher's pre-checkout guard usually
/// catches this; if it slips through, the cap bound clamps to 0 instead of
/// going negative.
/// True when the job is already at/over its core cap and cannot fit even one
/// more `cores_min`-sized frame. `job_max_cores <= 0` is OpenCue's "unlimited"
/// sentinel (never at cap), matching the accounting `job_max > 0` guard
/// and `core_cap_bound` above.
///
/// All arguments are in whole cores (see the unit invariant in `accounting::store` and
/// `DispatchLayer.job_max_cores`). Used by the matcher's pre-checkout skip so a
/// job sitting at its cap isn't re-checked-out and re-rejected every pass; the
/// booking call remains the authoritative gate, so a stale-low `job_cores_in_use`
/// (e.g. an absent store entry defaulting to 0) only causes a missed skip, never
/// an incorrect one.
pub fn job_at_core_cap(job_cores_in_use: i32, cores_min: i32, job_max_cores: i32) -> bool {
    job_max_cores > 0 && job_cores_in_use.saturating_add(cores_min) > job_max_cores
}

pub fn compute_max_more(host: &Host, profile: &LayerProfile) -> i64 {
    let cores_min = profile.cores_min.value() as i64;
    let mem_min = profile.mem_min.as_u64() as i64;
    let gpus_min = profile.gpus_min as i64;
    let gpu_mem_min = profile.gpu_mem_min.as_u64() as i64;

    // Physical headroom on a single dimension: how many additional `min`-sized
    // chunks remain in the idle pool after the first frame is allocated.
    // `None` means "no demand on this dim" — skipped when taking the minimum.
    let physical_bound =
        |idle: i64, min: i64| -> Option<i64> { (min > 0).then(|| (idle - min) / min) };

    // Headroom against a core-denominated administrative cap (job_max_cores
    // or show_burst): how many additional frames can be booked before live
    // usage hits the cap. Skipped when the cap is unset (`<= 0`) or the layer
    // has no core demand. The numerator is clamped at 0 to absorb stale
    // snapshots where in-use already exceeds the cap.
    let core_cap_bound = |cap: i32, in_use: i32| -> Option<i64> {
        (cap > 0 && cores_min > 0).then(|| {
            let slack = (cap as i64 - in_use as i64 - cores_min).max(0);
            slack / cores_min
        })
    };

    let bounds = [
        physical_bound(host.idle_cores.value() as i64, cores_min),
        physical_bound(host.idle_memory.as_u64() as i64, mem_min),
        physical_bound(host.idle_gpus as i64, gpus_min),
        physical_bound(host.idle_gpu_memory.as_u64() as i64, gpu_mem_min),
        core_cap_bound(profile.job_max_cores, profile.job_cores_in_use),
        core_cap_bound(profile.show_burst, profile.show_cores_in_use),
    ];

    // Final clamp to 0 catches the case where the host doesn't even satisfy
    // the floor (so a physical bound went negative); gates normally check
    // `fits_floor` first, but `compute_max_more` is defensive about it.
    bounds
        .into_iter()
        .flatten()
        .min()
        .map(|b| b.max(0))
        .unwrap_or(0)
}

/// E-PVM placement score with W3 normalization (per-dimension stranded
/// resource expressed as fractional layer-frames). Lower scores indicate
/// better fits; a perfect ratio match scores 0.
///
/// For GPU-requesting layers (`gpus_min > 0`), GPU and GPU-memory stranding
/// terms participate normally. For non-GPU layers, the GPU dimension is
/// REPLACED by a soft-reservation penalty proportional to the host's idle
/// GPU capacity — favors non-GPU hosts for non-GPU work without ignoring
/// GPU hosts when no GPU layers are pending (design Branch 5-iii).
pub fn placement_score(host: &Host, profile: &LayerProfile) -> f64 {
    let max_more = compute_max_more(host, profile) as f64;
    let w = &profile.weights;

    // W3 normalization: numerator and denominator share units, so the result
    // is dimensionless (fractional layer-frames stranded).
    let waste = |idle: f64, min: f64| -> f64 {
        if min > 0.0 {
            ((idle - min) - max_more * min) / min
        } else {
            0.0
        }
    };

    let cores_waste = waste(
        host.idle_cores.value() as f64,
        profile.cores_min.value() as f64,
    );
    let mem_waste = waste(
        host.idle_memory.as_u64() as f64,
        profile.mem_min.as_u64() as f64,
    );

    let gpu_term = if profile.gpus_min > 0 {
        let g_waste = waste(host.idle_gpus as f64, profile.gpus_min as f64);
        let gm_waste = waste(
            host.idle_gpu_memory.as_u64() as f64,
            profile.gpu_mem_min.as_u64() as f64,
        );
        w.gpus * g_waste + w.gpu_mem * gm_waste
    } else {
        // Soft-reservation penalty for non-GPU layers on GPU hosts. Count and
        // GB are scaled by independent weights so operators tune the
        // count-vs-memory balance explicitly. SI gigabytes (1e9) for the
        // memory unit.
        let idle_gpu_mem_gb = host.idle_gpu_memory.as_u64() as f64 / 1e9;
        w.gpu_count_reservation * host.idle_gpus as f64 + w.gpu_mem_reservation * idle_gpu_mem_gb
    };

    w.cores * cores_waste + w.mem * mem_waste + gpu_term
}

/// Result of pairing a host and layer on the slot-based axis.
///
/// Slot hosts and slot layers are strictly paired: a slot host runs only slot
/// layers and vice-versa. On a slot host, cores/memory floors are irrelevant —
/// the only constraint is the per-host concurrent slots cap.
enum SlotMatch {
    /// Neither host nor layer is slot-based: use the normal cores/memory gate.
    Neither,
    /// Both slot-based and the host has room for the layer's slots: accept.
    Accept,
    /// Pairing mismatch, or slot host at capacity: reject.
    Reject,
}

fn match_slots(host: &Host, profile: &LayerProfile) -> SlotMatch {
    match (host.concurrent_slots_limit, profile.slots_required) {
        // Slot host + slot layer: enforce the per-host concurrency cap.
        (Some(limit), req) if req > 0 => {
            if host.running_slots_count + req <= limit {
                SlotMatch::Accept
            } else {
                SlotMatch::Reject
            }
        }
        // Regular host + regular layer.
        (None, 0) => SlotMatch::Neither,
        // Slot host + regular layer, or regular host + slot layer.
        _ => SlotMatch::Reject,
    }
}

/// Saturation strategy gate: validate-only. Returns `Some(0.0)` when the host
/// is a valid candidate; the constant score is irrelevant because the
/// Saturation path is first-fit, not lowest-score.
pub fn saturation_gate(host: &Host, profile: &LayerProfile) -> Option<f64> {
    match match_slots(host, profile) {
        SlotMatch::Neither => {
            (validate_os_and_thread_mode(host, profile) && fits_floor(host, profile)).then_some(0.0)
        }
        // Slot placement: only OS compatibility matters (cores/mem/thread-mode
        // are irrelevant on slot hosts; the cap was checked in match_slots).
        SlotMatch::Accept => host_matches_layer_os(host, profile).then_some(0.0),
        SlotMatch::Reject => None,
    }
}

/// E-PVM strategy gate: validate, then score. Returns `Some(score)` when the
/// host fits; `None` otherwise. The cache picks the lowest score among up to
/// `max_candidates` scanned.
pub fn epvm_gate(host: &Host, profile: &LayerProfile) -> Option<f64> {
    match match_slots(host, profile) {
        SlotMatch::Neither => (validate_os_and_thread_mode(host, profile)
            && fits_floor(host, profile))
        .then(|| placement_score(host, profile)),
        // Slot placements don't strand cores/memory, so E-PVM scoring is
        // meaningless — every valid slot host ties at a constant score.
        SlotMatch::Accept => host_matches_layer_os(host, profile).then_some(0.0),
        SlotMatch::Reject => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use uuid::Uuid;

    fn profile_with(os: Option<&str>, threadable: bool) -> LayerProfile {
        LayerProfile {
            cores_min: CoreSize::from_multiplied(100),
            mem_min: ByteSize::gb(1),
            gpus_min: 0,
            gpu_mem_min: ByteSize::gb(0),
            slots_required: 0,
            os: os.map(str::to_string),
            threadable,
            job_max_cores: 0,
            show_burst: 0,
            job_cores_in_use: 0,
            show_cores_in_use: 0,
            weights: ScoreWeights::default(),
        }
    }

    fn host_with_os(str_os: Option<&str>) -> Host {
        host_with(str_os, ThreadMode::Variable)
    }

    fn host_with_thread_mode(thread_mode: ThreadMode) -> Host {
        host_with(Some("Linux"), thread_mode)
    }

    fn host_with(str_os: Option<&str>, thread_mode: ThreadMode) -> Host {
        Host::new_for_test(
            Uuid::new_v4(),
            "test-host".to_string(),
            str_os.map(str::to_string),
            CoreSize::from_multiplied(100),
            ByteSize::gb(64),
            CoreSize::from_multiplied(100),
            ByteSize::gb(64),
            0,
            ByteSize::gb(0),
            thread_mode,
            CoreSize::from_multiplied(100),
            Uuid::new_v4(),
            "test-alloc".to_string(),
            None,
        )
    }

    #[test]
    fn host_matches_when_layer_os_is_not_set() {
        let host = host_with_os(Some("Linux"));
        let profile = profile_with(None, true);
        assert!(host_matches_layer_os(&host, &profile));
    }

    #[test]
    fn host_matches_when_layer_os_matches_host_os() {
        let host = host_with_os(Some("Linux"));
        let profile = profile_with(Some("Linux"), true);
        assert!(host_matches_layer_os(&host, &profile));
    }

    #[test]
    fn host_does_not_match_when_layer_os_differs_from_host_os() {
        let host = host_with_os(Some("Linux"));
        let profile = profile_with(Some("Windows"), true);
        assert!(!host_matches_layer_os(&host, &profile));
    }

    #[test]
    fn job_at_core_cap_unlimited_sentinels_never_at_cap() {
        // 0 and -1 are the "unlimited" sentinels: never at cap regardless of use.
        assert!(!job_at_core_cap(1000, 10, 0));
        assert!(!job_at_core_cap(1000, 10, -1));
    }

    #[test]
    fn job_at_core_cap_exactly_at_cap_is_true() {
        // in_use == cap: no room for even one more cores_min-sized frame.
        assert!(job_at_core_cap(10, 1, 10));
    }

    #[test]
    fn job_at_core_cap_one_frame_of_room_is_false() {
        // in_use + cores_min == cap: exactly one more frame fits.
        assert!(!job_at_core_cap(9, 1, 10));
        assert!(!job_at_core_cap(8, 2, 10));
    }

    #[test]
    fn job_at_core_cap_over_cap_is_true() {
        // Stale snapshot / compensation rollback can leave in_use above cap.
        assert!(job_at_core_cap(12, 1, 10));
    }

    #[test]
    fn job_at_core_cap_zero_cores_min_only_when_over_cap() {
        // A GPU-only frame (cores_min == 0) is at-cap only if usage already
        // strictly exceeds the cap; at exactly the cap it can still "fit" (0 cores).
        assert!(!job_at_core_cap(10, 0, 10));
        assert!(job_at_core_cap(11, 0, 10));
    }

    #[test]
    fn thread_mode_all_rejects_non_threadable_layer() {
        let host = host_with_thread_mode(ThreadMode::All);
        let profile = profile_with(Some("Linux"), false);
        assert!(!host_matches_thread_mode(&host, &profile));
    }

    #[test]
    fn thread_mode_all_accepts_threadable_layer() {
        let host = host_with_thread_mode(ThreadMode::All);
        let profile = profile_with(Some("Linux"), true);
        assert!(host_matches_thread_mode(&host, &profile));
    }

    #[test]
    fn thread_mode_variable_accepts_any_threadability() {
        let host = host_with_thread_mode(ThreadMode::Variable);
        assert!(host_matches_thread_mode(
            &host,
            &profile_with(Some("Linux"), true)
        ));
        assert!(host_matches_thread_mode(
            &host,
            &profile_with(Some("Linux"), false)
        ));
    }

    #[test]
    fn thread_mode_auto_accepts_any_threadability() {
        let host = host_with_thread_mode(ThreadMode::Auto);
        assert!(host_matches_thread_mode(
            &host,
            &profile_with(Some("Linux"), true)
        ));
        assert!(host_matches_thread_mode(
            &host,
            &profile_with(Some("Linux"), false)
        ));
    }
}

#[cfg(test)]
mod scoring_tests {
    //! T1 tests for `compute_max_more`, `placement_score`, and the gates.
    //! Java parity examples come from `ref/Scheduler.java:702-710`.

    use super::*;
    use proptest::prelude::*;
    use uuid::Uuid;

    /// Build a host with explicit core/mem/gpu/gpu-mem idle resources. Uses
    /// raw `CoreSize(n)` (not `from_multiplied`) so test arithmetic matches
    /// the units used in placement scoring directly.
    fn host(idle_cores: i32, idle_memory_gb: u64, idle_gpus: u32, idle_gpu_memory_gb: u64) -> Host {
        use opencue_proto::host::ThreadMode;
        Host::new_for_test(
            Uuid::new_v4(),
            "h".to_string(),
            Some("Linux".to_string()),
            CoreSize(idle_cores),
            ByteSize::gb(idle_memory_gb),
            CoreSize(idle_cores),
            ByteSize::gb(idle_memory_gb),
            idle_gpus,
            ByteSize::gb(idle_gpu_memory_gb),
            ThreadMode::Auto,
            CoreSize(idle_cores),
            Uuid::new_v4(),
            "test-alloc".to_string(),
            None,
        )
    }

    fn layer(cores_min: i32, mem_min_gb: u64, gpus_min: i32, gpu_mem_min_gb: u64) -> LayerProfile {
        LayerProfile {
            cores_min: CoreSize(cores_min),
            mem_min: ByteSize::gb(mem_min_gb),
            gpus_min,
            gpu_mem_min: ByteSize::gb(gpu_mem_min_gb),
            slots_required: 0,
            os: None,
            threadable: true,
            job_max_cores: 0,
            show_burst: 0,
            job_cores_in_use: 0,
            show_cores_in_use: 0,
            weights: ScoreWeights::default(),
        }
    }

    // ---- compute_max_more --------------------------------------------------

    #[test]
    fn max_more_perfect_fit_is_zero() {
        // idle exactly meets min: 1 frame fits (the "first" one), 0 additional
        let h = host(4, 4, 0, 0);
        let l = layer(4, 4, 0, 0);
        assert_eq!(compute_max_more(&h, &l), 0);
    }

    #[test]
    fn max_more_ample_room() {
        // 64-core / 64GB host, 4-core / 4GB layer → fits 16 total, 15 additional
        let h = host(64, 64, 0, 0);
        let l = layer(4, 4, 0, 0);
        assert_eq!(compute_max_more(&h, &l), 15);
    }

    #[test]
    fn max_more_memory_binds() {
        // Plenty of cores, memory is the bottleneck
        let h = host(64, 8, 0, 0);
        let l = layer(4, 4, 0, 0);
        // After first frame: 60 cores / 4GB remaining. Memory allows 1 more.
        assert_eq!(compute_max_more(&h, &l), 1);
    }

    #[test]
    fn max_more_job_cap_binds_below_physical() {
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.job_max_cores = 12;
        l.job_cores_in_use = 0;
        // (12 - 0 - 4) / 4 = 2 additional frames before cap.
        assert_eq!(compute_max_more(&h, &l), 2);
    }

    #[test]
    fn max_more_show_burst_binds_below_physical() {
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.show_burst = 100;
        l.show_cores_in_use = 90;
        // (100 - 90 - 4) / 4 = 1 additional frame.
        assert_eq!(compute_max_more(&h, &l), 1);
    }

    #[test]
    fn max_more_show_burst_at_cap_returns_zero() {
        // booked + cores_min == burst: the first frame fits exactly, no more.
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.show_burst = 100;
        l.show_cores_in_use = 96;
        assert_eq!(compute_max_more(&h, &l), 0);
    }

    #[test]
    fn max_more_show_burst_tighter_than_job_cap() {
        // Both caps set; the tighter one (burst) binds.
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.job_max_cores = 100;
        l.job_cores_in_use = 0;
        l.show_burst = 20;
        l.show_cores_in_use = 0;
        // job: (100 - 0 - 4) / 4 = 24. burst: (20 - 0 - 4) / 4 = 4. min → 4.
        assert_eq!(compute_max_more(&h, &l), 4);
    }

    #[test]
    fn max_more_job_cap_tighter_than_show_burst() {
        // Mirror image: job cap binds when tighter than burst.
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.job_max_cores = 20;
        l.job_cores_in_use = 0;
        l.show_burst = 100;
        l.show_cores_in_use = 0;
        // job: (20 - 0 - 4) / 4 = 4. burst: (100 - 0 - 4) / 4 = 24. min → 4.
        assert_eq!(compute_max_more(&h, &l), 4);
    }

    #[test]
    fn max_more_show_burst_already_exceeded_returns_zero() {
        // Stale snapshot or compensation rollback in flight: booked already
        // above burst. Pre-checkout guard in matcher catches this; if it slips
        // through, max_more clamps to 0 (the `.max(0)` in `compute_max_more`).
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.show_burst = 100;
        l.show_cores_in_use = 110;
        assert_eq!(compute_max_more(&h, &l), 0);
    }

    #[test]
    fn max_more_unlimited_cap_sentinel_is_ignored() {
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.job_max_cores = -1; // OpenCue "unlimited" sentinel
        l.show_burst = 0; // also treated as unlimited
        assert_eq!(compute_max_more(&h, &l), 15);
    }

    #[test]
    fn max_more_all_dims_degenerate_returns_zero() {
        // No demand on any dimension → no meaningful bound
        let h = host(64, 64, 0, 0);
        let l = layer(0, 0, 0, 0);
        assert_eq!(compute_max_more(&h, &l), 0);
    }

    #[test]
    fn max_more_gpu_layer_gpu_binds() {
        let h = host(64, 64, 4, 16);
        let l = layer(4, 4, 2, 8);
        // GPU: (4 - 2) / 2 = 1 additional
        // GPU mem: (16 - 8) / 8 = 1 additional
        // Cores/mem allow 15. Min → 1.
        assert_eq!(compute_max_more(&h, &l), 1);
    }

    // ---- placement_score ---------------------------------------------------

    #[test]
    fn score_perfect_fit_is_zero() {
        // Java parity: 4-core / 4GB host, 4-core / 4GB layer → max_more=0, score=0
        let h = host(4, 4, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        // no GPU on host so reservation penalty is moot
        l.weights.gpu_count_reservation = 0.0;
        l.weights.gpu_mem_reservation = 0.0;
        assert_eq!(placement_score(&h, &l), 0.0);
    }

    #[test]
    fn score_ratio_match_is_zero() {
        // Java parity: 64-core / 64GB host, 4-core / 4GB layer → max_more=15, score=0
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.weights.gpu_count_reservation = 0.0;
        l.weights.gpu_mem_reservation = 0.0;
        assert_eq!(placement_score(&h, &l), 0.0);
    }

    #[test]
    fn score_memory_stranded_is_positive() {
        // 4-core / 64GB host, 4-core / 4GB layer: cores binds max_more=0,
        // memory has 60GB stranded.
        let h = host(4, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.weights.gpu_count_reservation = 0.0;
        l.weights.gpu_mem_reservation = 0.0;
        // mem_waste = ((64GB - 4GB) - 0 * 4GB) / 4GB = 15 fractional frames
        // score = weights.mem * 15 = 15.0 with defaults.
        let s = placement_score(&h, &l);
        assert!(s > 14.99 && s < 15.01, "expected ~15, got {}", s);
    }

    #[test]
    fn score_weight_scales_term() {
        let h = host(4, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.weights.mem = 2.0; // double the memory weight
        l.weights.gpu_count_reservation = 0.0;
        l.weights.gpu_mem_reservation = 0.0;
        let s = placement_score(&h, &l);
        assert!(s > 29.99 && s < 30.01, "expected ~30, got {}", s);
    }

    #[test]
    fn score_non_gpu_layer_on_gpu_host_penalized() {
        // Non-GPU layer fits cores/mem perfectly on a GPU host. With reservation
        // penalty, the GPU host scores higher than an identical non-GPU host.
        let gpu_host = host(4, 4, 8, 80);
        let non_gpu_host = host(4, 4, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        // Equal-weight split so the legacy single-knob math (penalty = count + GB)
        // is preserved as the baseline.
        l.weights.gpu_count_reservation = 1.0;
        l.weights.gpu_mem_reservation = 1.0;

        let s_gpu = placement_score(&gpu_host, &l);
        let s_non_gpu = placement_score(&non_gpu_host, &l);

        assert_eq!(s_non_gpu, 0.0);
        // Penalty = 1.0 * 8 + 1.0 * 80 = 88
        assert!(
            s_gpu > 87.99 && s_gpu < 88.01,
            "expected ~88, got {}",
            s_gpu
        );
    }

    #[test]
    fn score_split_gpu_reservation_weights_independent() {
        // Same host, vary each reservation weight independently and check that
        // each contributes only the dimension it controls.
        let gpu_host = host(4, 4, 8, 80);
        let mut l = layer(4, 4, 0, 0);

        // Count-only: should be 3.0 * 8 + 0.0 * 80 = 24
        l.weights.gpu_count_reservation = 3.0;
        l.weights.gpu_mem_reservation = 0.0;
        let s_count_only = placement_score(&gpu_host, &l);
        assert!(
            (s_count_only - 24.0).abs() < 0.01,
            "expected ~24, got {}",
            s_count_only
        );

        // Mem-only: should be 0.0 * 8 + 0.5 * 80 = 40
        l.weights.gpu_count_reservation = 0.0;
        l.weights.gpu_mem_reservation = 0.5;
        let s_mem_only = placement_score(&gpu_host, &l);
        assert!(
            (s_mem_only - 40.0).abs() < 0.01,
            "expected ~40, got {}",
            s_mem_only
        );
    }

    #[test]
    fn score_non_gpu_layer_on_non_gpu_host_no_gpu_term() {
        let h = host(4, 4, 0, 0);
        let l = layer(4, 4, 0, 0);
        // Even with default reservation weights (2.0, 2.0), host has 0 GPUs and
        // 0 GPU memory → 0 penalty.
        assert_eq!(placement_score(&h, &l), 0.0);
    }

    #[test]
    fn score_gpu_layer_uses_stranding_not_reservation() {
        // GPU layer on a GPU host: reservation penalty should NOT apply; the
        // GPU dimensions contribute via W3 stranding only.
        let h = host(4, 4, 4, 8);
        let mut l = layer(4, 4, 2, 8);
        // Would dominate if applied.
        l.weights.gpu_count_reservation = 100.0;
        l.weights.gpu_mem_reservation = 100.0;

        let s = placement_score(&h, &l);
        // GPU: (4-2 - 1*2) / 2 = 0, GPU mem: (8-8 - 1*8) / 8 = -1
        // But max_more is clamped by GPU: min(15, 15, 1, 0) = 0
        // Wait — gpu_mem: (8-8) / 8 = 0 additional. max_more = 0.
        // Cores: ((4-4) - 0) / 4 = 0
        // Mem: ((4-4) - 0) / 4 = 0
        // GPU: ((4-2) - 0) / 2 = 1
        // GPU mem: ((8-8) - 0) / 8 = 0
        // score = 0 + 0 + 2.0*1 + 1.0*0 = 2.0
        assert!(s > 1.99 && s < 2.01, "expected ~2.0, got {}", s);
    }

    // ---- gates -------------------------------------------------------------

    #[test]
    fn saturation_gate_returns_some_zero_when_valid() {
        let h = host(4, 4, 0, 0);
        let l = layer(4, 4, 0, 0);
        assert_eq!(saturation_gate(&h, &l), Some(0.0));
    }

    #[test]
    fn saturation_gate_rejects_on_os_mismatch() {
        let h = host(4, 4, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.os = Some("Windows".to_string());
        assert_eq!(saturation_gate(&h, &l), None);
    }

    #[test]
    fn saturation_gate_rejects_on_floor_shortfall() {
        let h = host(2, 4, 0, 0);
        let l = layer(4, 4, 0, 0);
        assert_eq!(saturation_gate(&h, &l), None);
    }

    // ── Slot-based pairing gate ──────────────────────────────────────────────

    fn slot_host(limit: u32, running: u32) -> Host {
        let mut h = host(4, 4, 0, 0);
        h.concurrent_slots_limit = Some(limit);
        h.running_slots_count = running;
        h
    }

    fn slot_layer(slots: u32) -> LayerProfile {
        let mut l = layer(4, 4, 0, 0);
        l.slots_required = slots;
        l
    }

    #[test]
    fn slot_host_accepts_slot_layer_within_cap() {
        // 2 running + 2 requested <= 8 cap.
        assert_eq!(saturation_gate(&slot_host(8, 2), &slot_layer(2)), Some(0.0));
    }

    #[test]
    fn slot_host_rejects_slot_layer_over_cap() {
        // 7 running + 2 requested > 8 cap.
        assert_eq!(saturation_gate(&slot_host(8, 7), &slot_layer(2)), None);
    }

    #[test]
    fn slot_host_rejects_regular_layer() {
        // Strict pairing: a slot host never runs a non-slot layer.
        assert_eq!(saturation_gate(&slot_host(8, 0), &layer(4, 4, 0, 0)), None);
    }

    #[test]
    fn regular_host_rejects_slot_layer() {
        // Strict pairing: a slot layer never runs on a non-slot host.
        assert_eq!(saturation_gate(&host(4, 4, 0, 0), &slot_layer(1)), None);
    }

    #[test]
    fn slot_gate_ignores_core_and_memory_floor() {
        // Slot host with zero idle cores/memory still accepts a slot layer.
        let mut h = slot_host(8, 0);
        h.idle_cores = CoreSize(0);
        h.idle_memory = ByteSize::gb(0);
        assert_eq!(saturation_gate(&h, &slot_layer(4)), Some(0.0));
    }

    #[test]
    fn epvm_gate_scores_slot_placement_constant() {
        // Slot placements tie at a constant score (no core stranding to minimize).
        assert_eq!(epvm_gate(&slot_host(8, 0), &slot_layer(1)), Some(0.0));
    }

    #[test]
    fn epvm_gate_returns_score_when_valid() {
        let h = host(64, 64, 0, 0);
        let mut l = layer(4, 4, 0, 0);
        l.weights.gpu_count_reservation = 0.0;
        l.weights.gpu_mem_reservation = 0.0;
        // Ratio match → score 0
        assert_eq!(epvm_gate(&h, &l), Some(0.0));
    }

    #[test]
    fn epvm_gate_rejects_on_floor_shortfall() {
        let h = host(2, 4, 0, 0);
        let l = layer(4, 4, 0, 0);
        assert_eq!(epvm_gate(&h, &l), None);
    }

    // ---- proptest experiment ----------------------------------------------

    proptest! {
        /// `placement_score` is non-negative under default weights when the
        /// host satisfies the layer's floor. The W3 numerator (idle - min) -
        /// max_more*min is non-negative by construction since
        /// max_more = floor((idle - min) / min).
        #[test]
        fn prop_score_non_negative(
            idle_cores in 1i32..256,
            idle_mem_gb in 1u64..512,
            cores_min in 1i32..64,
            mem_min_gb in 1u64..64,
        ) {
            prop_assume!(idle_cores >= cores_min);
            prop_assume!(idle_mem_gb >= mem_min_gb);
            let h = host(idle_cores, idle_mem_gb, 0, 0);
            let mut l = layer(cores_min, mem_min_gb, 0, 0);
            // GPU terms zero on non-GPU host anyway, but be explicit.
            l.weights.gpu_count_reservation = 0.0;
            l.weights.gpu_mem_reservation = 0.0;
            let s = placement_score(&h, &l);
            prop_assert!(s >= 0.0, "score was negative: {}", s);
        }

        /// Non-GPU layer soft-reservation: holding cores/mem fixed at a perfect
        /// fit, increasing the host's idle GPUs strictly increases the score.
        #[test]
        fn prop_gpu_reservation_monotonic(
            gpus_a in 0u32..16,
            extra in 1u32..16,
        ) {
            let gpus_b = gpus_a + extra;
            let h_a = host(4, 4, gpus_a, 0);
            let h_b = host(4, 4, gpus_b, 0);
            let mut l = layer(4, 4, 0, 0);
            // Only count varies in this prop; isolate the count knob.
            l.weights.gpu_count_reservation = 1.0;
            l.weights.gpu_mem_reservation = 0.0;
            let s_a = placement_score(&h_a, &l);
            let s_b = placement_score(&h_b, &l);
            prop_assert!(s_b > s_a, "expected {} > {} (a={} gpus, b={} gpus)", s_b, s_a, gpus_a, gpus_b);
        }

        /// Perfect ratio match: when idle and min are proportional across all
        /// active dimensions, the score is zero (no stranding).
        #[test]
        fn prop_ratio_match_scores_zero(
            cores_min in 1i32..16,
            mem_min_gb in 1u64..16,
            k in 1u64..16,
        ) {
            // Host is k times the layer on both dims (so ratios match).
            let h = host((cores_min as u64 * k) as i32, mem_min_gb * k, 0, 0);
            let mut l = layer(cores_min, mem_min_gb, 0, 0);
            l.weights.gpu_count_reservation = 0.0;
            l.weights.gpu_mem_reservation = 0.0;
            let s = placement_score(&h, &l);
            prop_assert!(s.abs() < 1e-6, "expected ~0, got {}", s);
        }
    }
}
