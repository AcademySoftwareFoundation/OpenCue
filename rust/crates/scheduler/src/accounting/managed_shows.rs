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

use crate::accounting::dao::{AccountingDao, BaselineKeys};
use crate::accounting::limit_reseed;
use crate::accounting::recompute;
use crate::accounting::store::Store;
use crate::config::CONFIG;

/// In-process cache of show ids where `b_scheduler_managed = true`. Refreshed by a
/// dedicated `tokio::spawn` loop every `CONFIG.accounting.managed_shows_ttl`
/// (default 30 s).
///
///  - Stale-true (show was managed, now isn't): scheduler keeps booking it against the
///    store for up to one TTL after the flip; the next recompute reconciles from `proc`.
///  - Stale-false (show is now managed, cache still says no): scheduler treats it as
///    Cuebot-managed (no store enforcement) until the next refresh seeds its caps. Cuebot
///    keeps booking it via PG in the meantime, so no decision is made against stale state.
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
    // Single-scheduler (N=1) assumed; if multi-init/graceful-shutdown ever lands this needs
    // a cancellation handle.
    pub fn start_refresh_loop(self: &Arc<Self>, dao: Arc<AccountingDao>, store: Arc<Store>) {
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
                            // Their enforced caps (notably subscription `burst`) may not be
                            // in the store yet - bootstrap only seeded shows managed at
                            // startup, and the periodic limit reseed runs on a slow cadence.
                            // Publishing them into the cache now would flip the booking hot
                            // path to enforce against an unseeded burst (== 0 == "reject
                            // all"). So seed caps FIRST, then publish (the managed-flip gate).
                            let added: Vec<Uuid> = {
                                let lock = inner.read().unwrap_or_else(|p| p.into_inner());
                                new_set
                                    .iter()
                                    .filter(|id| !lock.contains(*id))
                                    .copied()
                                    .collect()
                            };
                            if !added.is_empty() {
                                // Managed-flip blocking gate: seed caps AND booked counters
                                // for the newly-managed shows BEFORE publishing them into the
                                // cache. A flipped show may already have live Cuebot procs, so
                                // the hot path must enforce against real usage from the first
                                // booking, not against unseeded 0s (== full burst free ==
                                // over-book). The booked seed is a one-shot absolute set per
                                // show (no epoch bump), so it does not race the recompute
                                // driver's begin/overwrite sequencing.
                                let seed = async {
                                    limit_reseed::reseed_limits(&store, &dao).await?;
                                    for show in &added {
                                        let rows =
                                            dao.query_booked_snapshot_for_show(*show).await?;
                                        store.seed_show_booked(&recompute::snapshot_to_counters(
                                            &rows,
                                            &BaselineKeys::default(),
                                        ));
                                    }
                                    Ok::<(), miette::Report>(())
                                }
                                .await;
                                if let Err(err) = seed {
                                    // Defer publishing only the *additions* this tick: a
                                    // newly-managed show that is not yet in the cache is
                                    // treated as Cuebot-managed (Cuebot still books it via PG
                                    // until the flip lands) - strictly safer than enforcing
                                    // against unseeded state. Retried next tick.
                                    //
                                    // Removals still apply: a show no longer scheduler-managed
                                    // must drop out of the cache regardless of the seed
                                    // outcome, otherwise apply_booking keeps enforcing the
                                    // store for it indefinitely.
                                    warn!(
                                        "Seed for newly-managed show(s) {:?} failed; deferring \
                                         their cache publish to next tick: {err}",
                                        added
                                    );
                                    let added_set: HashSet<Uuid> = added.iter().copied().collect();
                                    let deferred: HashSet<Uuid> =
                                        new_set.difference(&added_set).copied().collect();
                                    let mut lock = inner.write().unwrap_or_else(|p| p.into_inner());
                                    *lock = deferred;
                                    return;
                                }
                                debug!(
                                    "Seeded caps + booked counters for {} newly-managed \
                                     show(s) before publishing",
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
