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

//! In-memory accounting service for the Rust scheduler.
//!
//! Holds the per-show resource counters in process - a single source of truth that makes
//! the accounting-drift bug class structurally impossible. See the Scheduler Accounting
//! Reference at `docs/_docs/developer-guide/scheduler-accounting.md` for architecture;
//! key invariants:
//!
//! - The booking hot path checks subscription burst + folder/job caps and increments the
//!   counters atomically under one lock (`Store`). `proc` remains the canonical record.
//! - Releases arrive live via Cuebot's PG `acct_release` NOTIFY (`listener`); cap changes
//!   via `acct_limit_change`. Both are optimisations over the periodic backstops.
//! - The recompute (`SUM(proc)` → counters, carrying pending in-flight bookings forward)
//!   and the limit reseed keep the store convergent and are the recovery mechanism.
//! - Single scheduler instance (N=1) is assumed; the in-memory store is not shared.

pub mod booking_delta;
pub mod bootstrap;
pub mod dao;
pub mod error;
pub mod limit_reseed;
pub mod listener;
pub mod managed_shows;
pub mod recompute;
pub mod store;

use std::sync::Arc;

use miette::Result;
use tokio::sync::OnceCell;
use tracing::{debug, info};
use uuid::Uuid;

use crate::accounting::booking_delta::BookingDelta;
use crate::accounting::dao::AccountingDao;
use crate::accounting::error::AccountingError;
use crate::accounting::managed_shows::ManagedShowsCache;
use crate::accounting::store::{BookOutcome, Store};

static ACCOUNTING_SERVICE: OnceCell<Arc<AccountingService>> = OnceCell::const_new();

/// Returns the process-wide `AccountingService`, initializing on first call.
///
/// Initialization builds the in-memory store and the managed-shows cache; the caller is
/// responsible for running `bootstrap::run_blocking_reseed` before the scheduler accepts
/// work, and for spawning the recompute, limit-reseed, and NOTIFY-listener loops after.
pub async fn accounting_service() -> Result<Arc<AccountingService>> {
    ACCOUNTING_SERVICE
        .get_or_try_init(|| async {
            let service = AccountingService::init().await?;
            Ok(Arc::new(service))
        })
        .await
        .cloned()
}

/// Result of [`AccountingService::apply_booking`]. Carries the delta so the caller can
/// `confirm`/`rollback` without re-deriving managed status (which can flip mid-dispatch).
pub enum Booking {
    /// Show is scheduler-managed and the delta was applied to the store.
    Applied(BookingDelta),
    /// Show is Cuebot-managed; nothing was applied. Confirm/rollback are no-ops.
    NotManaged,
}

/// High-level facade that the dispatcher hot path and the background loops both consume.
pub struct AccountingService {
    store: Arc<Store>,
    dao: Arc<AccountingDao>,
    managed_shows: Arc<ManagedShowsCache>,
}

impl AccountingService {
    /// Builds the in-memory store, populates the managed-shows cache from PG, and starts
    /// the cache refresh loop. Callers must run `bootstrap::run_blocking_reseed` before
    /// the scheduler accepts work.
    pub async fn init() -> Result<Self> {
        let store = Arc::new(Store::new());
        let dao = Arc::new(AccountingDao::new().await?);
        let managed_shows = ManagedShowsCache::populate(&dao).await?;
        // The refresh loop seeds caps for shows that become managed after startup, before
        // publishing them into the cache - so it needs a store handle.
        managed_shows.start_refresh_loop(dao.clone(), store.clone());
        info!(
            "AccountingService initialized (in-memory store): managed_shows={}",
            managed_shows.snapshot().len(),
        );
        Ok(Self {
            store,
            dao,
            managed_shows,
        })
    }

    pub fn store(&self) -> &Arc<Store> {
        &self.store
    }

    pub fn dao(&self) -> &Arc<AccountingDao> {
        &self.dao
    }

    pub fn managed_shows(&self) -> &Arc<ManagedShowsCache> {
        &self.managed_shows
    }

    /// Hot-path booking. Atomically checks subscription burst, folder/job caps and applies
    /// the delta to the counters. For shows not currently `b_scheduler_managed = true` this
    /// is a no-op (Cuebot owns the show's accounting), reported as `Booking::NotManaged`.
    pub fn apply_booking(&self, delta: &BookingDelta) -> Result<Booking, AccountingError> {
        if !self.managed_shows.contains(&delta.show_id) {
            debug!(
                "apply_booking skipped: show {} is not scheduler-managed",
                delta.show_id
            );
            return Ok(Booking::NotManaged);
        }
        match self.store.book(delta) {
            BookOutcome::Applied => Ok(Booking::Applied(delta.clone())),
            BookOutcome::LimitExceeded {
                table,
                current,
                limit,
            } => Err(AccountingError::LimitExceeded {
                table: table.to_string(),
                current,
                limit,
            }),
        }
    }

    /// Booking fully succeeded (proc committed + RQD launched): drop the pending portion,
    /// keep the booked increment. No-op when nothing was booked.
    ///
    /// Intentionally does NOT re-check managed status: if `apply_booking` applied the
    /// delta we must settle it even if the show flipped to Cuebot-managed in between.
    pub fn confirm_booking(&self, booking: &Booking) {
        if let Booking::Applied(delta) = booking {
            self.store.confirm(delta);
        }
    }

    /// Booking failed before launch: undo the counter increment and the pending delta.
    /// No-op when nothing was booked. Like `confirm_booking`, ignores managed status.
    pub fn rollback_booking(&self, booking: &Booking) {
        if let Booking::Applied(delta) = booking {
            self.store.rollback(delta);
        }
    }

    /// Live booked cores for a job (E-PVM placement snapshot in the matcher). 0 if unseen
    /// or the show is not managed.
    pub fn job_cores_in_use(&self, job_id: Uuid) -> i64 {
        self.store.job_cores_in_use(job_id)
    }

    /// `(booked_cores, burst)` for a subscription (matcher over-burst pre-check), in cores.
    pub fn sub_counters(&self, show_id: Uuid, alloc_id: Uuid) -> (i64, i64) {
        self.store.sub_counters(show_id, alloc_id)
    }
}
