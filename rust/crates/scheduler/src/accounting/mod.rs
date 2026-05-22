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

//! Redis-backed accounting service for the Rust scheduler.
//!
//! Replaces the in-process `ResourceAccountingService` with a shared store that scales
//! horizontally across N scheduler instances. See the Redis-Backed Accounting Reference
//! at `docs/_docs/developer-guide/redis-accounting.md` for architecture; key invariants:
//!
//! - Both Cuebot (release path, see `LettuceAccountingRedisPublisher`) and the Rust
//!   scheduler (booking path, here) mutate the same `acct:*` hashes via Lua scripts
//!   that bump `acct:seq` atomically.
//! - PG accounting tables stay durable via Cuebot's transactional UPDATEs (for
//!   Cuebot-managed shows) or the Rust 2-min recompute loop (for scheduler-managed
//!   shows). `proc` remains the canonical record of bookings.
//! - All reseeds (booted counters + limits + bootstrap) use the `acct:seq` CAS guard
//!   to avoid clobbering concurrent hot-path writes.

pub mod booking_delta;
pub mod bootstrap;
pub mod dao;
pub mod error;
pub mod limit_reseed;
pub mod lua;
pub mod managed_shows;
pub mod recompute;
pub mod redis_client;

use std::sync::Arc;

use miette::Result;
use tokio::sync::OnceCell;
use tracing::{debug, info, warn};
use uuid::Uuid;

use crate::accounting::booking_delta::BookingDelta;
use crate::accounting::dao::AccountingDao;
use crate::accounting::error::AccountingError;
use crate::accounting::managed_shows::ManagedShowsCache;
use crate::accounting::redis_client::{BookMode, BookOutcome, RedisAccounting};
use crate::config::CONFIG;

static ACCOUNTING_SERVICE: OnceCell<Arc<AccountingService>> = OnceCell::const_new();

/// Returns the process-wide `AccountingService`, initializing on first call.
///
/// Initialization connects to Redis and populates the managed-shows cache; the caller
/// is responsible for running `bootstrap::run_blocking_reseed` before the scheduler
/// accepts work, and for spawning the recompute + limit-reseed loops afterwards.
pub async fn accounting_service() -> Result<Arc<AccountingService>> {
    ACCOUNTING_SERVICE
        .get_or_try_init(|| async {
            let service = AccountingService::init().await?;
            Ok(Arc::new(service))
        })
        .await
        .cloned()
}

/// High-level facade that the dispatcher hot path and the background loops both consume.
pub struct AccountingService {
    redis: RedisAccounting,
    dao: Arc<AccountingDao>,
    managed_shows: Arc<ManagedShowsCache>,
}

impl AccountingService {
    /// Connects to Redis, populates the managed-shows cache from PG, and returns a
    /// ready-to-use service. Callers must run `bootstrap::run_blocking_reseed` against
    /// the returned service before the scheduler accepts work.
    pub async fn init() -> Result<Self> {
        let redis = RedisAccounting::connect(&CONFIG.accounting.redis)
            .await
            .map_err(|e| miette::miette!("Failed to connect to redis: {e}"))?;
        let dao = Arc::new(AccountingDao::new().await?);
        let managed_shows = ManagedShowsCache::populate(&dao).await?;
        managed_shows.start_refresh_loop(dao.clone());
        info!(
            "AccountingService initialized: redis={}:{} managed_shows={}",
            CONFIG.accounting.redis.host,
            CONFIG.accounting.redis.port,
            managed_shows.snapshot().len(),
        );
        Ok(Self {
            redis,
            dao,
            managed_shows,
        })
    }

    pub fn redis(&self) -> &RedisAccounting {
        &self.redis
    }

    pub fn dao(&self) -> &Arc<AccountingDao> {
        &self.dao
    }

    pub fn managed_shows(&self) -> &Arc<ManagedShowsCache> {
        &self.managed_shows
    }

    /// Hot-path booking. Atomically checks subscription burst, folder/job caps and
    /// applies the delta to all five `acct:*` hashes. For shows not currently
    /// `b_scheduler_managed = true`, this is a no-op (Cuebot owns the show's accounting).
    pub async fn apply_booking(&self, delta: &BookingDelta) -> Result<(), AccountingError> {
        if !self.managed_shows.contains(&delta.show_id) {
            debug!(
                "apply_booking skipped: show {} is not scheduler-managed",
                delta.show_id
            );
            return Ok(());
        }
        match self.redis.book(delta, BookMode::Enforce).await? {
            BookOutcome::Applied { new_seq: _ } => Ok(()),
            BookOutcome::LimitExceeded {
                table,
                current,
                limit,
            } => Err(AccountingError::LimitExceeded {
                table,
                current,
                limit,
            }),
        }
    }

    /// Force-applies a (typically negated) delta, bypassing all caps. Used by the
    /// dispatcher on DB or RQD failure to roll back a booking that was already counted
    /// in Redis. Cannot return `LimitExceeded`. On Redis failure we log and swallow -
    /// the next recompute (≤2 min) heals Redis from `proc`.
    ///
    /// Intentionally does NOT consult `managed_shows`: if `apply_booking` wrote the
    /// hashes (the only path that reaches this rollback), we must undo it, even if
    /// the show was flipped to Cuebot-managed between the booking and the failure.
    /// Otherwise the orphan booking persists in Redis - the recompute filters by
    /// `b_scheduler_managed=true` in SQL and won't include the show.
    pub async fn apply_force_rollback(&self, delta: &BookingDelta) {
        match self.redis.book(delta, BookMode::Force).await {
            Ok(_) => {}
            Err(err) => {
                warn!(
                    "apply_force_rollback failed for show={} job={}: {err}; \
                     recompute will heal Redis from proc",
                    delta.show_id, delta.job_id
                );
            }
        }
    }

    /// Cheap pre-check that would filter doomed host candidates before host selection.
    /// Returns `Ok(true)` when the requested cores fit under the subscription burst,
    /// `Ok(false)` when they don't. Conservatively returns `true` for non-managed shows
    /// and on transient Redis errors.
    ///
    /// **Currently unwired** because `host_cache::CheckOut.validation` is a sync `Fn`
    /// and calling Redis from inside it requires either making the validation async
    /// (host_cache actor refactor) or precomputing a per-layer (show, alloc) → bookable
    /// map before CheckOut. See the comment at `pipeline/matcher.rs::process_layer`.
    #[allow(dead_code)]
    pub async fn subscription_can_book(
        &self,
        show_id: Uuid,
        alloc_id: Uuid,
        cores_requested: i64,
    ) -> bool {
        if !self.managed_shows.contains(&show_id) {
            return true;
        }
        match self.redis.read_sub_counters(show_id, alloc_id).await {
            Ok((booked, burst)) => burst <= 0 || (booked + cores_requested) <= burst,
            Err(err) => {
                debug!(
                    "subscription_can_book HGET failed for show={show_id} alloc={alloc_id}: \
                     {err}; allowing through, Lua will decide",
                );
                true
            }
        }
    }
}
