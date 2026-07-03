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

//! In-process accounting store. Single source of truth for the scheduler's booking
//! decisions, replacing the Redis-backed counters. See
//! `docs/_docs/developer-guide/scheduler-accounting.md` for the full design.
//!
//! Only the three enforced vertices are tracked: subscription (`burst`), folder
//! (`int_max_cores`/`int_max_gpus`) and job (`int_max_cores`/`int_max_gpus`). The
//! booking enforcement this replaces incremented layer and point counters too, but
//! never read them, so they are not kept here.
//!
//! Concurrency: one `Mutex` guards the whole state. Every critical section is pure
//! in-memory arithmetic (no I/O, no `.await`), so contention is negligible at this
//! scale and a single lock keeps the three-vertex check-and-increment trivially atomic.
//!
//! ## Pending carry-forward (the hard-cap invariant)
//!
//! The recompute reconciles booked counters by absolute-overwrite from a `SUM(proc)`
//! snapshot, which is read OUTSIDE the lock and is therefore stale: it can miss a proc
//! that committed after the read. To stop the overwrite from erasing such a booking (the
//! only way to under-count → over-book a hard cap), each booking is carried as "pending"
//! until a recompute whose snapshot provably includes its `proc` row has run:
//!
//! - `book` adds the delta to the live counter and to the **in-flight** bucket (proc not
//!   yet committed → in no snapshot yet → always carried).
//! - `confirm` (proc committed + RQD launched) moves the delta from in-flight to a
//!   **settled** bucket, double-buffered by recompute-epoch parity.
//! - `rollback` (dispatch failed) removes the delta from the live counter and in-flight.
//! - The recompute bumps the epoch under the lock *before* its snapshot read, then on
//!   overwrite sets `counter = snapshot + in-flight + settled[both buckets]` and clears
//!   only the settled bucket from *before* this epoch — confirms that raced the snapshot
//!   read land in the other bucket and survive. Double-counting a booking that is in both
//!   the snapshot and a settled bucket is harmless (over-count → under-book → safe).

use std::collections::HashMap;
use std::sync::Mutex;

use uuid::Uuid;

use crate::accounting::booking_delta::BookingDelta;
use crate::models::CoreSize;

/// `-1` is the "unlimited" sentinel on folder/job `int_max_cores`/`int_max_gpus`;
/// the `> 0` guard in [`over_cap`] treats any non-positive cap as unbounded.
const UNLIMITED: i64 = -1;

/// Booked counters for one accounting vertex.
///
/// `cores`/`gpus` is the live booked total the cap check reads. The other fields track
/// the portion still in flight so the recompute's absolute overwrite cannot erase a
/// booking whose `proc` row is not yet in its (stale) snapshot. See the module docs.
#[derive(Default, Clone, Copy, Debug, PartialEq, Eq)]
struct Counter {
    cores: i64,
    gpus: i64,
    /// Booked, proc INSERT not yet confirmed committed. In no snapshot → always carried.
    inflight_cores: i64,
    inflight_gpus: i64,
    /// Bookings that have been confirmed but whose `proc` row may not yet appear in a
    /// recompute snapshot. Uses two alternating buckets indexed by `e % 2`: confirms
    /// during epoch `e` write to bucket `e % 2`, so the recompute can identify and
    /// preserve confirms that raced its snapshot read without clearing ones already
    /// captured by it.
    settled_cores: [i64; 2],
    settled_gpus: [i64; 2],
    /// Slot booking counters. Independent axis: slot frames book slots with 0
    /// cores/gpus and vice-versa. Mirrors the cores/gpus double-buffer exactly.
    slots: i64,
    inflight_slots: i64,
    settled_slots: [i64; 2],
}

impl Counter {
    /// Pending delta to carry across an overwrite: in-flight (uncommitted) bookings plus
    /// the settled bucket `keep` — the one holding confirms that raced *this* pass's
    /// snapshot read. The other settled bucket holds confirms from before the snapshot read,
    /// which are already in the snapshot, so it is NOT carried (and is cleared afterward).
    fn carried_cores(&self, keep: usize) -> i64 {
        self.inflight_cores + self.settled_cores[keep]
    }
    fn carried_gpus(&self, keep: usize) -> i64 {
        self.inflight_gpus + self.settled_gpus[keep]
    }
    fn carried_slots(&self, keep: usize) -> i64 {
        self.inflight_slots + self.settled_slots[keep]
    }

    /// `book`: add to the live total and the in-flight bucket.
    fn add_booking(&mut self, dc: i64, dg: i64, ds: i64) {
        self.cores += dc;
        self.gpus += dg;
        self.slots += ds;
        self.inflight_cores += dc;
        self.inflight_gpus += dg;
        self.inflight_slots += ds;
    }

    /// `confirm`: move from in-flight to the current epoch's settled bucket (live unchanged).
    fn settle(&mut self, dc: i64, dg: i64, ds: i64, bucket: usize) {
        self.inflight_cores -= dc;
        self.inflight_gpus -= dg;
        self.inflight_slots -= ds;
        self.settled_cores[bucket] += dc;
        self.settled_gpus[bucket] += dg;
        self.settled_slots[bucket] += ds;
    }

    /// `rollback`: undo a `book` (live total and in-flight).
    fn remove_booking(&mut self, dc: i64, dg: i64, ds: i64) {
        self.cores -= dc;
        self.gpus -= dg;
        self.slots -= ds;
        self.inflight_cores -= dc;
        self.inflight_gpus -= dg;
        self.inflight_slots -= ds;
    }
}

/// Folder/job cap pair, in cores. `-1` means unlimited (see [`UNLIMITED`]).
#[derive(Default, Clone, Copy, Debug)]
struct MaxCap {
    max_cores: i64,
    max_gpus: i64,
}

#[derive(Default)]
struct Inner {
    sub: HashMap<(Uuid, Uuid), Counter>,
    folder: HashMap<Uuid, Counter>,
    job: HashMap<Uuid, Counter>,
    /// Subscription burst caps, in cores. Missing == 0 == "reject all" (matches the
    /// Cuebot `IS_SHOW_OVER_BURST` convention and fails closed before the bootstrap seed).
    sub_burst: HashMap<(Uuid, Uuid), i64>,
    folder_caps: HashMap<Uuid, MaxCap>,
    job_caps: HashMap<Uuid, MaxCap>,
    /// Slot caps per vertex (subscription/folder/job), a hard max independent of
    /// cores/gpus. `-1` = unlimited, `0`/missing = reject-all (fail-closed before
    /// the seed). See [`over_slot_cap`].
    sub_slot_caps: HashMap<(Uuid, Uuid), i64>,
    folder_slot_caps: HashMap<Uuid, i64>,
    job_slot_caps: HashMap<Uuid, i64>,
    /// Monotonic recompute epoch. Bumped under the lock at the start of each recompute so
    /// `confirm` tags the correct settled bucket relative to the in-flight snapshot read.
    epoch: u64,
}

/// Outcome of a [`Store::book`] call.
pub enum BookOutcome {
    /// Booking accepted; counters incremented and the delta recorded as pending.
    Applied,
    /// Rejected because a hard cap would be exceeded. `table` is the vertex label the
    /// rejection is attributed to (`subscription`/`folder`/`job`/`folder_gpus`/`job_gpus`).
    LimitExceeded {
        table: &'static str,
        current: i64,
        limit: i64,
    },
}

/// A single enforced cap change, delivered live by the PG `acct_limit_change` listener
/// or applied in bulk by the limit reseed. Values are in cores (GPUs pass through).
#[derive(Debug, Clone)]
pub enum LimitChange {
    SubBurst {
        show_id: Uuid,
        alloc_id: Uuid,
        burst: i64,
    },
    FolderMaxCores {
        folder_id: Uuid,
        max_cores: i64,
    },
    FolderMaxGpus {
        folder_id: Uuid,
        max_gpus: i64,
    },
    JobMaxCores {
        job_id: Uuid,
        max_cores: i64,
    },
    JobMaxGpus {
        job_id: Uuid,
        max_gpus: i64,
    },
    SubMaxSlots {
        show_id: Uuid,
        alloc_id: Uuid,
        max_slots: i64,
    },
    FolderMaxSlots {
        folder_id: Uuid,
        max_slots: i64,
    },
    JobMaxSlots {
        job_id: Uuid,
        max_slots: i64,
    },
}

/// Aggregated `SUM(proc)` totals for one recompute pass, already converted to cores and
/// overlaid on the zero-baseline (every enumerable key present, drained keys carrying 0).
/// Per-vertex booked totals `(cores, gpus, slots)`.
#[derive(Default, Debug)]
pub struct CounterSnapshot {
    pub sub: HashMap<(Uuid, Uuid), (i64, i64, i64)>,
    pub folder: HashMap<Uuid, (i64, i64, i64)>,
    pub job: HashMap<Uuid, (i64, i64, i64)>,
}

/// Process-wide in-memory accounting state.
#[derive(Default)]
pub struct Store {
    inner: Mutex<Inner>,
}

/// `cur + delta` exceeds `cap` only when `cap` is a real (positive) ceiling. A cap of
/// `0` on a subscription burst means "reject all"; on a folder/job max it means unset →
/// treated as unlimited, matching the legacy `> 0` guard. `enforce_zero` selects which
/// convention applies.
fn over_cap(cur: i64, delta: i64, cap: i64, enforce_zero: bool) -> bool {
    if enforce_zero {
        cur + delta > cap
    } else {
        cap > 0 && cur + delta > cap
    }
}

/// Slot cap rule: `-1` (negative) is unlimited; `0` and any missing cap mean
/// "reject all" (fail-closed before the seed); `N >= 0` caps at N. Distinct from
/// [`over_cap`] because `0` is a *valid* admin value (reject all slot work here),
/// so it must not read as "unset/unlimited".
fn over_slot_cap(cur: i64, delta: i64, cap: i64) -> bool {
    cap >= 0 && cur + delta > cap
}

impl Store {
    pub fn new() -> Self {
        Self::default()
    }

    fn lock(&self) -> std::sync::MutexGuard<'_, Inner> {
        self.inner.lock().unwrap_or_else(|p| p.into_inner())
    }

    /// Hot-path booking: atomically check subscription burst and folder/job core/GPU
    /// caps, and on success increment all three vertices and record the delta as in-flight.
    pub fn book(&self, delta: &BookingDelta) -> BookOutcome {
        let core_delta = delta.core_delta;
        let gpu_delta = i64::from(delta.gpu_delta);
        let slot_delta = delta.slot_delta;
        let mut inner = self.lock();

        if core_delta > 0 {
            let cur_sub = inner
                .sub
                .get(&(delta.show_id, delta.alloc_id))
                .map_or(0, |c| c.cores);
            let burst = inner
                .sub_burst
                .get(&(delta.show_id, delta.alloc_id))
                .copied()
                .unwrap_or(0);
            // Subscription burst enforces 0 as "reject all".
            if over_cap(cur_sub, core_delta, burst, true) {
                return BookOutcome::LimitExceeded {
                    table: "subscription",
                    current: cur_sub,
                    limit: burst,
                };
            }

            let cur_folder = inner.folder.get(&delta.folder_id).map_or(0, |c| c.cores);
            let folder_max = inner
                .folder_caps
                .get(&delta.folder_id)
                .map_or(0, |c| c.max_cores);
            if over_cap(cur_folder, core_delta, folder_max, false) {
                return BookOutcome::LimitExceeded {
                    table: "folder",
                    current: cur_folder,
                    limit: folder_max,
                };
            }

            let cur_job = inner.job.get(&delta.job_id).map_or(0, |c| c.cores);
            let job_max = inner.job_caps.get(&delta.job_id).map_or(0, |c| c.max_cores);
            if over_cap(cur_job, core_delta, job_max, false) {
                return BookOutcome::LimitExceeded {
                    table: "job",
                    current: cur_job,
                    limit: job_max,
                };
            }
        }

        if gpu_delta > 0 {
            let cur_folder_gpu = inner.folder.get(&delta.folder_id).map_or(0, |c| c.gpus);
            let folder_gpu_max = inner
                .folder_caps
                .get(&delta.folder_id)
                .map_or(0, |c| c.max_gpus);
            if over_cap(cur_folder_gpu, gpu_delta, folder_gpu_max, false) {
                return BookOutcome::LimitExceeded {
                    table: "folder_gpus",
                    current: cur_folder_gpu,
                    limit: folder_gpu_max,
                };
            }

            let cur_job_gpu = inner.job.get(&delta.job_id).map_or(0, |c| c.gpus);
            let job_gpu_max = inner.job_caps.get(&delta.job_id).map_or(0, |c| c.max_gpus);
            if over_cap(cur_job_gpu, gpu_delta, job_gpu_max, false) {
                return BookOutcome::LimitExceeded {
                    table: "job_gpus",
                    current: cur_job_gpu,
                    limit: job_gpu_max,
                };
            }
        }

        if slot_delta > 0 {
            // Slot caps: `-1` unlimited, `0`/missing reject-all (fail-closed).
            let cur_sub_slots = inner
                .sub
                .get(&(delta.show_id, delta.alloc_id))
                .map_or(0, |c| c.slots);
            let sub_slot_max = inner
                .sub_slot_caps
                .get(&(delta.show_id, delta.alloc_id))
                .copied()
                .unwrap_or(0);
            if over_slot_cap(cur_sub_slots, slot_delta, sub_slot_max) {
                return BookOutcome::LimitExceeded {
                    table: "subscription_slots",
                    current: cur_sub_slots,
                    limit: sub_slot_max,
                };
            }

            let cur_folder_slots = inner.folder.get(&delta.folder_id).map_or(0, |c| c.slots);
            let folder_slot_max = inner
                .folder_slot_caps
                .get(&delta.folder_id)
                .copied()
                .unwrap_or(0);
            if over_slot_cap(cur_folder_slots, slot_delta, folder_slot_max) {
                return BookOutcome::LimitExceeded {
                    table: "folder_slots",
                    current: cur_folder_slots,
                    limit: folder_slot_max,
                };
            }

            let cur_job_slots = inner.job.get(&delta.job_id).map_or(0, |c| c.slots);
            let job_slot_max = inner
                .job_slot_caps
                .get(&delta.job_id)
                .copied()
                .unwrap_or(0);
            if over_slot_cap(cur_job_slots, slot_delta, job_slot_max) {
                return BookOutcome::LimitExceeded {
                    table: "job_slots",
                    current: cur_job_slots,
                    limit: job_slot_max,
                };
            }
        }

        inner
            .sub
            .entry((delta.show_id, delta.alloc_id))
            .or_default()
            .add_booking(core_delta, gpu_delta, slot_delta);
        inner
            .folder
            .entry(delta.folder_id)
            .or_default()
            .add_booking(core_delta, gpu_delta, slot_delta);
        inner
            .job
            .entry(delta.job_id)
            .or_default()
            .add_booking(core_delta, gpu_delta, slot_delta);
        BookOutcome::Applied
    }

    /// Booking settled (proc committed + RQD launched): move the delta from in-flight to
    /// the current epoch's settled bucket. The live counter is unchanged. Exactly one of
    /// `confirm`/`rollback` runs per `book`.
    pub fn confirm(&self, delta: &BookingDelta) {
        let dc = delta.core_delta;
        let dg = i64::from(delta.gpu_delta);
        let ds = delta.slot_delta;
        let mut inner = self.lock();
        let bucket = (inner.epoch % 2) as usize;
        inner
            .sub
            .entry((delta.show_id, delta.alloc_id))
            .or_default()
            .settle(dc, dg, ds, bucket);
        inner
            .folder
            .entry(delta.folder_id)
            .or_default()
            .settle(dc, dg, ds, bucket);
        inner
            .job
            .entry(delta.job_id)
            .or_default()
            .settle(dc, dg, ds, bucket);
    }

    /// Booking failed before launch: undo the live increment and the in-flight delta.
    pub fn rollback(&self, delta: &BookingDelta) {
        let dc = delta.core_delta;
        let dg = i64::from(delta.gpu_delta);
        let ds = delta.slot_delta;
        let mut inner = self.lock();
        inner
            .sub
            .entry((delta.show_id, delta.alloc_id))
            .or_default()
            .remove_booking(dc, dg, ds);
        inner
            .folder
            .entry(delta.folder_id)
            .or_default()
            .remove_booking(dc, dg, ds);
        inner
            .job
            .entry(delta.job_id)
            .or_default()
            .remove_booking(dc, dg, ds);
    }

    /// Apply a release delta (negative cores/gpus) from the Cuebot `acct_release` NOTIFY.
    /// Unconditional and pending-free: releases are for long-settled bookings.
    pub fn apply_release(&self, delta: &BookingDelta) {
        let dc = delta.core_delta;
        let dg = i64::from(delta.gpu_delta);
        let ds = delta.slot_delta;
        let mut inner = self.lock();
        if let Some(c) = inner.sub.get_mut(&(delta.show_id, delta.alloc_id)) {
            c.cores += dc;
            c.gpus += dg;
            c.slots += ds;
        }
        if let Some(c) = inner.folder.get_mut(&delta.folder_id) {
            c.cores += dc;
            c.gpus += dg;
            c.slots += ds;
        }
        if let Some(c) = inner.job.get_mut(&delta.job_id) {
            c.cores += dc;
            c.gpus += dg;
            c.slots += ds;
        }
    }

    /// Begin a recompute pass: bump the epoch under the lock and return the pre-bump value.
    /// Must be called BEFORE reading the `SUM(proc)` snapshot, and the returned epoch passed
    /// to [`Store::overwrite_counters`]. This is what lets a `confirm` racing the snapshot
    /// read land in a settled bucket the overwrite will not clear.
    pub fn begin_recompute(&self) -> u64 {
        let mut inner = self.lock();
        let g = inner.epoch;
        inner.epoch = inner.epoch.wrapping_add(1);
        g
    }

    /// Recompute backstop: overwrite every booked total with `snapshot + carried pending`,
    /// then clear the settled bucket that pre-dates this pass's snapshot read (`epoch % 2`).
    ///
    /// `snapshot` already carries the zero-baseline (drained keys present with `0`). A
    /// confirm that raced the snapshot read tagged the *other* bucket (the epoch was bumped
    /// before the read), so it is carried, not cleared — closing the straddle hole. Keys
    /// absent from `snapshot` (e.g. FINISHED jobs no longer enumerable) keep their value;
    /// only their stale settled bucket is cleared.
    pub fn overwrite_counters(&self, snapshot: &CounterSnapshot, epoch: u64) {
        let clear = (epoch % 2) as usize;
        let keep = 1 - clear;
        let mut inner = self.lock();
        for (&k, &(cores, gpus, slots)) in &snapshot.sub {
            let c = inner.sub.entry(k).or_default();
            c.cores = cores + c.carried_cores(keep);
            c.gpus = gpus + c.carried_gpus(keep);
            c.slots = slots + c.carried_slots(keep);
        }
        for (&k, &(cores, gpus, slots)) in &snapshot.folder {
            let c = inner.folder.entry(k).or_default();
            c.cores = cores + c.carried_cores(keep);
            c.gpus = gpus + c.carried_gpus(keep);
            c.slots = slots + c.carried_slots(keep);
        }
        for (&k, &(cores, gpus, slots)) in &snapshot.job {
            let c = inner.job.entry(k).or_default();
            c.cores = cores + c.carried_cores(keep);
            c.gpus = gpus + c.carried_gpus(keep);
            c.slots = slots + c.carried_slots(keep);
        }
        // Clear the pre-snapshot settled bucket across all keys (confirms older than this
        // pass's snapshot read are provably reflected in the snapshot now).
        for c in inner.sub.values_mut() {
            c.settled_cores[clear] = 0;
            c.settled_gpus[clear] = 0;
            c.settled_slots[clear] = 0;
        }
        for c in inner.folder.values_mut() {
            c.settled_cores[clear] = 0;
            c.settled_gpus[clear] = 0;
            c.settled_slots[clear] = 0;
        }
        for c in inner.job.values_mut() {
            c.settled_cores[clear] = 0;
            c.settled_gpus[clear] = 0;
            c.settled_slots[clear] = 0;
        }
    }

    /// One-shot absolute seed of a show's booked counters when it is flipped to
    /// scheduler-managed, BEFORE it enters the managed-shows cache. At this point the show
    /// has no scheduler bookings (the hot path no-ops for unpublished shows), so there is no
    /// in-flight/settled pending and no concurrent booking on its keys. Unlike the recompute
    /// overwrite this does NOT bump the epoch or touch the settled buckets, so it never
    /// interferes with the single recompute driver's begin/overwrite sequencing. Setting the
    /// live counter directly is what closes the managed-flip over-book window: the first
    /// booking after publish enforces against real usage, not against 0 (= full burst free).
    pub fn seed_show_booked(&self, snapshot: &CounterSnapshot) {
        let mut inner = self.lock();
        for (&k, &(cores, gpus, slots)) in &snapshot.sub {
            let c = inner.sub.entry(k).or_default();
            c.cores = cores;
            c.gpus = gpus;
            c.slots = slots;
        }
        for (&k, &(cores, gpus, slots)) in &snapshot.folder {
            let c = inner.folder.entry(k).or_default();
            c.cores = cores;
            c.gpus = gpus;
            c.slots = slots;
        }
        for (&k, &(cores, gpus, slots)) in &snapshot.job {
            let c = inner.job.entry(k).or_default();
            c.cores = cores;
            c.gpus = gpus;
            c.slots = slots;
        }
    }

    /// Bulk-set caps from the limit reseed (PG → store). Values are in cores; `-1`
    /// unlimited sentinels are preserved by the caller.
    pub fn set_caps(
        &self,
        subs: impl IntoIterator<Item = (Uuid, Uuid, i64, i64)>,
        folders: impl IntoIterator<Item = (Uuid, i64, i64, i64)>,
        jobs: impl IntoIterator<Item = (Uuid, i64, i64, i64)>,
    ) {
        let mut inner = self.lock();
        for (show_id, alloc_id, burst, max_slots) in subs {
            inner.sub_burst.insert((show_id, alloc_id), burst);
            inner.sub_slot_caps.insert((show_id, alloc_id), max_slots);
        }
        for (folder_id, max_cores, max_gpus, max_slots) in folders {
            inner.folder_caps.insert(
                folder_id,
                MaxCap {
                    max_cores,
                    max_gpus,
                },
            );
            inner.folder_slot_caps.insert(folder_id, max_slots);
        }
        for (job_id, max_cores, max_gpus, max_slots) in jobs {
            inner.job_caps.insert(
                job_id,
                MaxCap {
                    max_cores,
                    max_gpus,
                },
            );
            inner.job_slot_caps.insert(job_id, max_slots);
        }
    }

    /// Apply a single live cap change from the `acct_limit_change` listener. A single-field
    /// change on an unseen vertex defaults the other dimension to `UNLIMITED` rather than 0
    /// so it cannot accidentally under-enforce before the next full limit reseed seeds both.
    pub fn apply_limit_change(&self, change: &LimitChange) {
        let mut inner = self.lock();
        match *change {
            LimitChange::SubBurst {
                show_id,
                alloc_id,
                burst,
            } => {
                inner.sub_burst.insert((show_id, alloc_id), burst);
            }
            LimitChange::FolderMaxCores {
                folder_id,
                max_cores,
            } => {
                inner
                    .folder_caps
                    .entry(folder_id)
                    .or_insert(MaxCap::unlimited())
                    .max_cores = max_cores;
            }
            LimitChange::FolderMaxGpus {
                folder_id,
                max_gpus,
            } => {
                inner
                    .folder_caps
                    .entry(folder_id)
                    .or_insert(MaxCap::unlimited())
                    .max_gpus = max_gpus;
            }
            LimitChange::JobMaxCores { job_id, max_cores } => {
                inner
                    .job_caps
                    .entry(job_id)
                    .or_insert(MaxCap::unlimited())
                    .max_cores = max_cores;
            }
            LimitChange::JobMaxGpus { job_id, max_gpus } => {
                inner
                    .job_caps
                    .entry(job_id)
                    .or_insert(MaxCap::unlimited())
                    .max_gpus = max_gpus;
            }
            LimitChange::SubMaxSlots {
                show_id,
                alloc_id,
                max_slots,
            } => {
                inner.sub_slot_caps.insert((show_id, alloc_id), max_slots);
            }
            LimitChange::FolderMaxSlots {
                folder_id,
                max_slots,
            } => {
                inner.folder_slot_caps.insert(folder_id, max_slots);
            }
            LimitChange::JobMaxSlots { job_id, max_slots } => {
                inner.job_slot_caps.insert(job_id, max_slots);
            }
        }
    }

    /// Live booked cores for a job (E-PVM placement snapshot in the matcher). 0 if unseen.
    pub fn job_cores_in_use(&self, job_id: Uuid) -> i64 {
        self.lock().job.get(&job_id).map_or(0, |c| c.cores)
    }

    /// Live booked slots for a job (slot-axis observability). 0 if unseen.
    #[cfg(test)]
    pub fn job_slots_in_use(&self, job_id: Uuid) -> i64 {
        self.lock().job.get(&job_id).map_or(0, |c| c.slots)
    }

    /// `(booked_cores, burst)` for a subscription (matcher over-burst pre-check). Both in
    /// cores; missing entries read as 0.
    pub fn sub_counters(&self, show_id: Uuid, alloc_id: Uuid) -> (i64, i64) {
        let inner = self.lock();
        let booked = inner.sub.get(&(show_id, alloc_id)).map_or(0, |c| c.cores);
        let burst = inner
            .sub_burst
            .get(&(show_id, alloc_id))
            .copied()
            .unwrap_or(0);
        (booked, burst)
    }

    /// Snapshot of booked `(cores, gpus)` per vertex, for the stress-test accounting audit.
    #[cfg(feature = "stress-tests")]
    pub fn audit_snapshot(&self) -> AuditSnapshot {
        let inner = self.lock();
        let booked = |c: &Counter| (c.cores, c.gpus);
        AuditSnapshot {
            sub: inner.sub.iter().map(|(&k, c)| (k, booked(c))).collect(),
            folder: inner.folder.iter().map(|(&k, c)| (k, booked(c))).collect(),
            job: inner.job.iter().map(|(&k, c)| (k, booked(c))).collect(),
        }
    }
}

impl MaxCap {
    fn unlimited() -> Self {
        MaxCap {
            max_cores: UNLIMITED,
            max_gpus: UNLIMITED,
        }
    }
}

/// Convert a PG centicore total to cores. Booked sums are non-negative.
pub fn centicores_to_cores(centicores: i64) -> i64 {
    i64::from(CoreSize::from_multiplied(centicores).value())
}

/// Convert a PG centicore cap to cores, preserving the `-1` unlimited sentinel.
pub fn centicores_to_cores_cap(centicores: i64) -> i64 {
    if centicores < 0 {
        UNLIMITED
    } else {
        i64::from(CoreSize::from_multiplied_cap(centicores).value())
    }
}

/// Booked `(cores, gpus)` per vertex key, returned by [`Store::audit_snapshot`].
#[cfg(feature = "stress-tests")]
#[derive(Default, Debug)]
pub struct AuditSnapshot {
    pub sub: HashMap<(Uuid, Uuid), (i64, i64)>,
    pub folder: HashMap<Uuid, (i64, i64)>,
    pub job: HashMap<Uuid, (i64, i64)>,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn delta(
        show: Uuid,
        alloc: Uuid,
        folder: Uuid,
        job: Uuid,
        cores: i64,
        gpus: i32,
    ) -> BookingDelta {
        BookingDelta {
            show_id: show,
            alloc_id: alloc,
            folder_id: folder,
            job_id: job,
            core_delta: cores,
            gpu_delta: gpus,
            slot_delta: 0,
        }
    }

    /// A pure slot booking delta (0 cores/gpus) for the slot-axis tests.
    fn slot_delta(show: Uuid, alloc: Uuid, folder: Uuid, job: Uuid, slots: i64) -> BookingDelta {
        BookingDelta {
            show_id: show,
            alloc_id: alloc,
            folder_id: folder,
            job_id: job,
            core_delta: 0,
            gpu_delta: 0,
            slot_delta: slots,
        }
    }

    fn applied(o: BookOutcome) -> bool {
        matches!(o, BookOutcome::Applied)
    }

    fn ids() -> (Uuid, Uuid, Uuid, Uuid) {
        (
            Uuid::new_v4(),
            Uuid::new_v4(),
            Uuid::new_v4(),
            Uuid::new_v4(),
        )
    }

    #[test]
    fn book_rejects_when_unseeded_burst_is_zero() {
        // Missing burst == 0 == reject all (fail closed before any seed).
        let store = Store::new();
        let d = delta(
            Uuid::new_v4(),
            Uuid::new_v4(),
            Uuid::new_v4(),
            Uuid::new_v4(),
            1,
            0,
        );
        assert!(matches!(
            store.book(&d),
            BookOutcome::LimitExceeded {
                table: "subscription",
                ..
            }
        ));
    }

    #[test]
    fn book_enforces_job_hard_cap_atomically() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 1000, -1)], [(folder, -1, -1, -1)], [(job, 10, -1, -1)]);
        let d = delta(show, alloc, folder, job, 6, 0);
        assert!(applied(store.book(&d))); // 6 <= 10
                                          // Second booking of 6 would reach 12 > 10 -> rejected. No partial state.
        assert!(matches!(
            store.book(&d),
            BookOutcome::LimitExceeded {
                table: "job",
                current: 6,
                limit: 10
            }
        ));
        assert_eq!(store.job_cores_in_use(job), 6);
    }

    #[test]
    fn unlimited_sentinel_never_rejects() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps(
            [(show, alloc, 1_000_000, -1)],
            [(folder, -1, -1, -1)],
            [(job, -1, -1, -1)],
        );
        let d = delta(show, alloc, folder, job, 500, 4);
        assert!(applied(store.book(&d)));
    }

    /// Recompute that runs entirely after a confirm reconciles the counter to `SUM(proc)`.
    #[test]
    fn confirm_then_recompute_keeps_booked() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, -1, -1, -1)]);
        let d = delta(show, alloc, folder, job, 10, 0);
        assert!(applied(store.book(&d)));
        store.confirm(&d);
        let epoch = store.begin_recompute();
        let snap = CounterSnapshot {
            job: [(job, (10, 0, 0))].into_iter().collect(),
            ..Default::default()
        };
        store.overwrite_counters(&snap, epoch);
        assert_eq!(store.job_cores_in_use(job), 10);
    }

    #[test]
    fn rollback_undoes_book() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, -1, -1, -1)]);
        let d = delta(show, alloc, folder, job, 10, 0);
        assert!(applied(store.book(&d)));
        store.rollback(&d);
        assert_eq!(store.job_cores_in_use(job), 0);
        let epoch = store.begin_recompute();
        let snap = CounterSnapshot {
            job: [(job, (0, 0, 0))].into_iter().collect(),
            ..Default::default()
        };
        store.overwrite_counters(&snap, epoch);
        assert_eq!(store.job_cores_in_use(job), 0);
    }

    /// In-flight booking (booked, not yet confirmed) absent from the snapshot must survive.
    #[test]
    fn recompute_carries_forward_in_flight_booking() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, 20, -1, -1)]);
        let d = delta(show, alloc, folder, job, 8, 0);
        assert!(applied(store.book(&d))); // booked, still in-flight (not confirmed)

        let epoch = store.begin_recompute();
        let snap = CounterSnapshot {
            sub: [((show, alloc), (0, 0, 0))].into_iter().collect(),
            folder: [(folder, (0, 0, 0))].into_iter().collect(),
            job: [(job, (0, 0, 0))].into_iter().collect(),
        };
        store.overwrite_counters(&snap, epoch);
        assert_eq!(store.job_cores_in_use(job), 8);
    }

    /// THE STRADDLE HOLE (M1): a recompute reads its snapshot, THEN a booking commits and
    /// is confirmed, THEN the overwrite lands. The confirm tagged the post-`begin_recompute`
    /// bucket, so the overwrite must NOT erase it. Without epoch double-buffering this
    /// over-books a hard cap.
    #[test]
    fn recompute_does_not_erase_booking_confirmed_after_snapshot_read() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, 20, -1, -1)]);
        let d = delta(show, alloc, folder, job, 8, 0);
        assert!(applied(store.book(&d)));

        // Recompute begins (epoch bumped) and reads a snapshot that does NOT yet see the proc.
        let epoch = store.begin_recompute();
        // Proc commits + dispatch succeeds AFTER the snapshot read -> confirm now.
        store.confirm(&d);
        // Overwrite lands. The confirm tagged the other settled bucket, so 8 survives.
        let snap = CounterSnapshot {
            sub: [((show, alloc), (0, 0, 0))].into_iter().collect(),
            folder: [(folder, (0, 0, 0))].into_iter().collect(),
            job: [(job, (0, 0, 0))].into_iter().collect(),
        };
        store.overwrite_counters(&snap, epoch);
        assert_eq!(
            store.job_cores_in_use(job),
            8,
            "booking confirmed after the snapshot read was erased"
        );

        // The following recompute (proc now visible) reconciles cleanly to the true value.
        let epoch2 = store.begin_recompute();
        let snap2 = CounterSnapshot {
            sub: [((show, alloc), (8 * 100 / 100, 0, 0))].into_iter().collect(),
            folder: [(folder, (8, 0, 0))].into_iter().collect(),
            job: [(job, (8, 0, 0))].into_iter().collect(),
        };
        store.overwrite_counters(&snap2, epoch2);
        assert_eq!(store.job_cores_in_use(job), 8);
    }

    #[test]
    fn release_decrements_unconditionally() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, -1, -1, -1)]);
        let d = delta(show, alloc, folder, job, 10, 0);
        assert!(applied(store.book(&d)));
        store.confirm(&d);
        // Cuebot sends a release as a negative delta; the listener applies it as-is.
        store.apply_release(&delta(show, alloc, folder, job, -10, 0));
        assert_eq!(store.job_cores_in_use(job), 0);
    }

    /// A dropped release NOTIFY leaves the counter reading high (safe: under-book); the next
    /// recompute heals it down to `SUM(proc)`. Must never strand a hard cap as over-booked.
    #[test]
    fn missed_release_heals_via_recompute() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, -1, -1, -1)]);
        let d = delta(show, alloc, folder, job, 10, 0);
        assert!(applied(store.book(&d)));
        store.confirm(&d);
        // Settle the booking through one full recompute so it leaves the pending buckets.
        let e1 = store.begin_recompute();
        store.overwrite_counters(
            &CounterSnapshot {
                sub: [((show, alloc), (10, 0, 0))].into_iter().collect(),
                folder: [(folder, (10, 0, 0))].into_iter().collect(),
                job: [(job, (10, 0, 0))].into_iter().collect(),
            },
            e1,
        );
        let e2 = store.begin_recompute();
        store.overwrite_counters(
            &CounterSnapshot {
                sub: [((show, alloc), (10, 0, 0))].into_iter().collect(),
                folder: [(folder, (10, 0, 0))].into_iter().collect(),
                job: [(job, (10, 0, 0))].into_iter().collect(),
            },
            e2,
        );
        // Frame completed and Cuebot deleted the proc, but the release NOTIFY was dropped:
        // the store still reads 10 (high → under-book, never over-book).
        assert_eq!(store.job_cores_in_use(job), 10);
        // Recompute sees the drained proc (SUM = 0) and heals the counter down.
        let e3 = store.begin_recompute();
        store.overwrite_counters(
            &CounterSnapshot {
                sub: [((show, alloc), (0, 0, 0))].into_iter().collect(),
                folder: [(folder, (0, 0, 0))].into_iter().collect(),
                job: [(job, (0, 0, 0))].into_iter().collect(),
            },
            e3,
        );
        assert_eq!(store.job_cores_in_use(job), 0);
    }

    /// Managed-flip seed: a show flipped to managed already has live Cuebot procs. After
    /// seeding the booked counters from `SUM(proc)`, the first scheduler booking enforces
    /// against real usage, not against 0. Without the seed it would over-book the burst.
    #[test]
    fn managed_flip_seed_prevents_overbook() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, -1, -1, -1)]);
        // Cuebot already has 90 cores booked on this (show, alloc) at flip time.
        let seed = CounterSnapshot {
            sub: [((show, alloc), (90, 0, 0))].into_iter().collect(),
            folder: [(folder, (90, 0, 0))].into_iter().collect(),
            job: [(job, (90, 0, 0))].into_iter().collect(),
        };
        store.seed_show_booked(&seed);
        assert_eq!(store.sub_counters(show, alloc), (90, 100));
        // A 20-core booking would reach 110 > 100 burst -> must reject (not over-book).
        assert!(matches!(
            store.book(&delta(show, alloc, folder, job, 20, 0)),
            BookOutcome::LimitExceeded {
                table: "subscription",
                current: 90,
                limit: 100
            }
        ));
        // A 10-core booking fits exactly at the burst.
        assert!(applied(store.book(&delta(show, alloc, folder, job, 10, 0))));
    }

    #[test]
    fn live_limit_change_updates_cap() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, 50, -1, -1)]);
        let d = delta(show, alloc, folder, job, 40, 0);
        assert!(applied(store.book(&d))); // 40 <= 50
                                          // Operator lowers the hard cap to 30 live; further bookings must reject.
        store.apply_limit_change(&LimitChange::JobMaxCores {
            job_id: job,
            max_cores: 30,
        });
        let d2 = delta(show, alloc, folder, job, 1, 0);
        assert!(matches!(
            store.book(&d2),
            BookOutcome::LimitExceeded { table: "job", .. }
        ));
    }

    // ── Slot axis ────────────────────────────────────────────────────────────

    /// Missing slot cap (unseeded) rejects all slot work — fail-closed.
    #[test]
    fn slot_book_missing_cap_rejects_all() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        // No set_caps: slot caps default to 0 = reject-all.
        assert!(matches!(
            store.book(&slot_delta(show, alloc, folder, job, 1)),
            BookOutcome::LimitExceeded {
                table: "subscription_slots",
                ..
            }
        ));
    }

    /// `-1` slot cap is unlimited; many slot bookings succeed.
    #[test]
    fn slot_unlimited_cap_never_rejects() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, -1, -1, -1)]);
        for _ in 0..100 {
            assert!(applied(store.book(&slot_delta(show, alloc, folder, job, 1))));
        }
        assert_eq!(store.job_slots_in_use(job), 100);
    }

    /// The folder slot cap is enforced (and `0` means reject-all even at the folder level).
    #[test]
    fn slot_book_respects_folder_cap() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        // sub/job unlimited, folder capped at 2 slots.
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, 2)], [(job, -1, -1, -1)]);
        assert!(applied(store.book(&slot_delta(show, alloc, folder, job, 2)))); // fills the cap
        assert!(matches!(
            store.book(&slot_delta(show, alloc, folder, job, 1)),
            BookOutcome::LimitExceeded {
                table: "folder_slots",
                current: 2,
                limit: 2
            }
        ));
    }

    /// The slot axis is fully independent of the core/gpu axes: a slot booking
    /// consumes no core budget, and a core booking consumes no slot budget.
    #[test]
    fn slot_axis_independent_from_cores() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        // Cores capped tight at 1; slots capped generously.
        store.set_caps([(show, alloc, 1, -1)], [(folder, 1, -1, -1)], [(job, 1, -1, 10)]);
        // A 5-slot booking (0 cores) is unaffected by the 1-core cap.
        assert!(applied(store.book(&slot_delta(show, alloc, folder, job, 5))));
        assert_eq!(store.job_slots_in_use(job), 5);
        assert_eq!(store.job_cores_in_use(job), 0);
        // A 1-core booking still fits its own budget, untouched by slot usage.
        assert!(applied(store.book(&delta(show, alloc, folder, job, 1, 0))));
        assert_eq!(store.job_cores_in_use(job), 1);
    }

    /// A release NOTIFY with a negative slot delta decrements the slot counters.
    #[test]
    fn slot_release_decrements() {
        let (show, alloc, folder, job) = ids();
        let store = Store::new();
        store.set_caps([(show, alloc, 100, -1)], [(folder, -1, -1, -1)], [(job, -1, -1, 10)]);
        assert!(applied(store.book(&slot_delta(show, alloc, folder, job, 4))));
        assert_eq!(store.job_slots_in_use(job), 4);
        store.apply_release(&slot_delta(show, alloc, folder, job, -3));
        assert_eq!(store.job_slots_in_use(job), 1);
    }
}
