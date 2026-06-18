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

use std::collections::HashSet;
use std::panic::AssertUnwindSafe;
use std::sync::{Arc, RwLock};

use futures::FutureExt;
use tokio::time;
use tracing::{debug, error, warn};
use uuid::Uuid;

use crate::accounting::dao::AccountingDao;
use crate::accounting::limit_reseed;
use crate::accounting::redis_client::RedisAccounting;
use crate::config::CONFIG;

/// In-process cache of show ids where `b_scheduler_managed = true`. Refreshed by a
/// dedicated `tokio::spawn` loop every `CONFIG.accounting.managed_shows_ttl`
/// (default 30 s).
///
///  - Stale-true (show was managed, now isn't): scheduler keeps writing Redis for up to
///    one TTL after the flip; orphan writes are reseeded away within 5 min.
///  - Stale-false (show is now managed, cache still says no): scheduler dispatches without
///    Redis writes. Silent over-count until next refresh + next recompute heal (≤2 min
///    after refresh). Acceptable per design §4.3.1.
pub struct ManagedShowsCache {
    inner: Arc<RwLock<HashSet<Uuid>>>,
}

impl ManagedShowsCache {
    /// Populates the cache from PG synchronously, then returns it.
    /// Use `start_refresh_loop` to start the background refresh.
    pub async fn populate(dao: &AccountingDao) -> miette::Result<Arc<Self>> {
        let initial = dao.query_managed_show_ids().await?;
        let cache = Arc::new(Self {
            inner: Arc::new(RwLock::new(initial.into_iter().collect())),
        });
        Ok(cache)
    }

    /// Spawns a background loop that refreshes the cache every TTL.
    ///
    /// The `JoinHandle` is intentionally dropped - the loop runs until the process
    /// exits. Safe today because `AccountingService` is held by a `OnceCell` and
    /// `start_refresh_loop` is only called from `init`. If multi-init or graceful
    /// shutdown ever becomes a requirement (multi-scheduler rollout, integration
    /// tests that recreate the service), this needs a `CancellationToken` or a
    /// stored handle.
    // TODO: cancellation handle when multi-init/graceful-shutdown lands (design §5).
    pub fn start_refresh_loop(self: &Arc<Self>, dao: Arc<AccountingDao>, redis: RedisAccounting) {
        let inner = self.inner.clone();
        tokio::spawn(async move {
            let mut interval = time::interval(CONFIG.accounting.managed_shows_ttl);
            // Skip the immediate first tick - populate() already fetched on startup.
            interval.tick().await;
            loop {
                interval.tick().await;
                let result = AssertUnwindSafe(async {
                    match dao.query_managed_show_ids().await {
                        Ok(ids) => {
                            let new_set: HashSet<Uuid> = ids.into_iter().collect();

                            // Shows that became scheduler-managed since the last refresh.
                            // Their accounting limits (notably subscription `burst`) may
                            // not be in Redis yet - bootstrap only seeded shows managed at
                            // startup, and the periodic limit reseed runs on a slow cadence.
                            // Publishing them into the cache now would flip the booking hot
                            // path to enforce against an unseeded burst (== 0 == "reject
                            // all"). So seed limits FIRST, then publish.
                            let added: Vec<Uuid> = {
                                let lock = inner.read().unwrap_or_else(|p| p.into_inner());
                                new_set
                                    .iter()
                                    .filter(|id| !lock.contains(*id))
                                    .copied()
                                    .collect()
                            };
                            if !added.is_empty() {
                                if let Err(err) = limit_reseed::reseed_limits(&redis, &dao).await {
                                    // Defer publishing this tick: a managed show that is
                                    // not yet in the cache dispatches without Redis
                                    // enforcement (silent over-count, healed by the next
                                    // recompute) - strictly safer than enforcing against an
                                    // unseeded burst. Retried on the next tick.
                                    warn!(
                                        "Limit seed for newly-managed show(s) {:?} failed; \
                                         deferring cache publish to next tick: {err}",
                                        added
                                    );
                                    return;
                                }
                                debug!(
                                    "Seeded limits for {} newly-managed show(s) before publishing",
                                    added.len()
                                );
                            }

                            let mut lock = inner.write().unwrap_or_else(|p| p.into_inner());
                            *lock = new_set;
                            debug!("ManagedShowsCache refreshed: {} shows", lock.len());
                        }
                        Err(err) => {
                            warn!("Failed to refresh managed-shows cache: {err}");
                        }
                    }
                })
                .catch_unwind()
                .await;
                if let Err(e) = result {
                    error!("Managed-shows refresh iteration panicked: {:?}", e);
                }
            }
        });
    }

    pub fn contains(&self, show_id: &Uuid) -> bool {
        self.inner
            .read()
            .unwrap_or_else(|p| p.into_inner())
            .contains(show_id)
    }

    /// Snapshot the current set. Used by recompute/limit-reseed loops to scope their
    /// queries; we already filter by `b_scheduler_managed=true` in SQL, but keeping
    /// this helper makes the contract explicit and gives tests a hook.
    pub fn snapshot(&self) -> HashSet<Uuid> {
        self.inner.read().unwrap_or_else(|p| p.into_inner()).clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_cache(set: HashSet<Uuid>) -> ManagedShowsCache {
        ManagedShowsCache {
            inner: Arc::new(RwLock::new(set)),
        }
    }

    #[test]
    fn contains_reflects_initial_population() {
        let id = Uuid::new_v4();
        let mut set = HashSet::new();
        set.insert(id);
        let cache = make_cache(set);
        assert!(cache.contains(&id));
        assert!(!cache.contains(&Uuid::new_v4()));
    }

    #[test]
    fn snapshot_returns_independent_copy() {
        let id = Uuid::new_v4();
        let mut set = HashSet::new();
        set.insert(id);
        let cache = make_cache(set);
        let snap = cache.snapshot();
        assert_eq!(snap.len(), 1);
        assert!(snap.contains(&id));
    }
}
