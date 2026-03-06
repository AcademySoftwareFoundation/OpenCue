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

use std::{
    collections::HashMap,
    sync::{Arc, Mutex, RwLock},
};

use miette::Result;
use tokio::{sync::OnceCell, time};
use tracing::warn;
use uuid::Uuid;

use crate::{
    config::CONFIG,
    dao::{AllocationDao, AllocationName, ShowId},
    models::{CoreSize, Subscription},
};

/// Key for the pending-delta accumulator: (show_id, alloc_id, alloc_name).
/// `alloc_name` is included so deltas can be re-applied to the cache (which is
/// keyed by name) after a DB refresh without needing a separate id→name lookup.
type DeltaKey = (ShowId, Uuid, AllocationName);
/// Accumulated (core_delta, gpu_delta, retry_count) not yet flushed to the database.
type DeltaValue = (i64, i32, u8);

const MAX_FLUSH_RETRIES: u8 = 5;

pub struct AllocationService {
    cache: Arc<RwLock<HashMap<ShowId, HashMap<AllocationName, Subscription>>>>,
    /// Pending subscription deltas accumulated since the last DB flush.
    ///
    /// Each entry holds the total booked-core and booked-GPU deltas for a
    /// (show, allocation) pair that have been committed to the `proc` table
    /// but not yet written back to the `subscription` table. The background
    /// loop drains this map and applies the deltas once per refresh cycle.
    pending_deltas: Arc<Mutex<HashMap<DeltaKey, DeltaValue>>>,
    allocation_dao: Arc<AllocationDao>,
}

static ALLOCATION_SERVICE: OnceCell<Arc<AllocationService>> = OnceCell::const_new();

pub async fn allocation_service() -> Result<Arc<AllocationService>> {
    ALLOCATION_SERVICE
        .get_or_try_init(|| async {
            let service = AllocationService::init().await?;

            service.start_async_loop();

            Ok(Arc::new(service))
        })
        .await
        .cloned()
}

impl AllocationService {
    async fn init() -> Result<Self> {
        let allocation_dao = Arc::new(AllocationDao::new().await?);
        let pending_deltas = Arc::new(Mutex::new(HashMap::new()));

        // Fetch subscriptions from DB
        let mut subs = allocation_dao.get_subscriptions_by_show().await?;

        // Recompute booked counts from the proc table so the cache is accurate
        // even if the subscription table drifted (e.g. after a crash).
        match allocation_dao.recompute_booked_from_proc().await {
            Ok(booked_map) => {
                for ((show_id, alloc_name), (cores_booked, gpus_booked)) in booked_map {
                    if let Some(show_subs) = subs.get_mut(&show_id) {
                        if let Some(sub) = show_subs.get_mut(&alloc_name) {
                            sub.booked_cores = CoreSize::from_multiplied(
                                cores_booked.try_into().unwrap_or_else(|_| {
                                    warn!(
                                        "Recomputed booked cores overflowed i32 for \
                                         show={show_id} alloc={alloc_name}, \
                                         using subscription table value"
                                    );
                                    sub.booked_cores.value()
                                }),
                            );
                            sub.booked_gpus = gpus_booked.try_into().unwrap_or_else(|_| {
                                warn!(
                                    "Recomputed booked GPUs overflowed u32 for \
                                     show={show_id} alloc={alloc_name}, \
                                     using subscription table value"
                                );
                                sub.booked_gpus
                            });
                        }
                    }
                }
            }
            Err(err) => {
                warn!(
                    "Could not recompute booked cores from proc table on startup; \
                     using subscription table values instead: {err}"
                );
            }
        }

        let cache = Arc::new(RwLock::new(subs));
        Ok(AllocationService {
            cache,
            pending_deltas,
            allocation_dao,
        })
    }

    fn start_async_loop(&self) {
        let cache = self.cache.clone();
        let pending_deltas = self.pending_deltas.clone();
        let allocation_dao = self.allocation_dao.clone();

        tokio::spawn(async move {
            let mut interval = time::interval(CONFIG.queue.allocation_refresh_interval);

            loop {
                interval.tick().await;
                flush_and_refresh(&cache, &pending_deltas, &allocation_dao).await;
            }
        });
    }

    pub fn get_subscription(
        &self,
        allocation_name: &String,
        show_id: &Uuid,
    ) -> Option<Subscription> {
        self.cache
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .get(show_id)?
            .get(allocation_name)
            .cloned()
    }

    /// Records a successful frame booking in the in-memory cache and the pending-delta
    /// accumulator.
    ///
    /// Call this after the frame's database transaction has been committed. The in-memory
    /// `booked_cores` update keeps `bookable()` accurate for subsequent frames in the same
    /// dispatch cycle without waiting for the next DB refresh. The pending delta is flushed
    /// to the `subscription` table by the background loop.
    pub fn record_booking(
        &self,
        show_id: Uuid,
        alloc_id: Uuid,
        alloc_name: &str,
        core_delta: i64,
        gpu_delta: i32,
    ) {
        // Update the in-memory booked_cores/booked_gpus immediately so the next
        // bookable() check within this dispatch cycle sees the correct state.
        {
            let mut cache = self.cache.write().unwrap_or_else(|p| p.into_inner());
            if let Some(show_subs) = cache.get_mut(&show_id) {
                if let Some(sub) = show_subs.get_mut(alloc_name) {
                    let new_booked = sub.booked_cores.value() as i64 + core_delta;
                    sub.booked_cores = CoreSize::from_multiplied(
                        new_booked.try_into().unwrap_or_else(|_| {
                            warn!(
                                "Booked cores overflowed i32 for show={show_id} \
                                 alloc={alloc_name}, using previous value"
                            );
                            sub.booked_cores.value()
                        }),
                    );

                    let new_gpus = sub.booked_gpus as i64 + gpu_delta as i64;
                    sub.booked_gpus = new_gpus.try_into().unwrap_or_else(|_| {
                        warn!(
                            "Booked GPUs overflowed u32 for show={show_id} \
                             alloc={alloc_name}, using previous value"
                        );
                        sub.booked_gpus
                    });
                }
            }
        }

        // Accumulate the delta for the next background flush to DB.
        let mut deltas = self
            .pending_deltas
            .lock()
            .unwrap_or_else(|p| p.into_inner());
        let entry = deltas
            .entry((show_id, alloc_id, alloc_name.to_owned()))
            .or_insert((0, 0, 0));
        entry.0 += core_delta;
        entry.1 += gpu_delta;
    }
}

/// Drains pending subscription deltas, flushes them to the database, refreshes the
/// in-memory cache, and re-applies any deltas that accumulated during the flush window.
async fn flush_and_refresh(
    cache: &Arc<RwLock<HashMap<ShowId, HashMap<AllocationName, Subscription>>>>,
    pending_deltas: &Arc<Mutex<HashMap<DeltaKey, DeltaValue>>>,
    allocation_dao: &Arc<AllocationDao>,
) {
    // Drain the accumulator before refreshing so the upcoming DB read
    // reflects the flushed deltas.
    let deltas_to_flush: HashMap<DeltaKey, DeltaValue> = {
        let mut lock = pending_deltas.lock().unwrap_or_else(|p| p.into_inner());
        std::mem::take(&mut *lock)
    };

    for ((show_id, alloc_id, alloc_name), (core_delta, gpu_delta, retries)) in &deltas_to_flush {
        if let Err(err) = allocation_dao
            .flush_subscription_delta(*show_id, *alloc_id, *core_delta, *gpu_delta)
            .await
        {
            let new_retries = retries + 1;
            if new_retries >= MAX_FLUSH_RETRIES {
                panic!(
                    "Failed to flush subscription delta for \
                     show={show_id} alloc={alloc_id}: {err}\n\
                     The subscription table is now out of sync with in-flight bookings. \
                     Restarting to recompute booked counts from the proc table."
                );
            }
            warn!(
                "Failed to flush subscription delta for \
                 show={show_id} alloc={alloc_id}: {err}. \
                 Will retry next cycle (attempt {new_retries}/{MAX_FLUSH_RETRIES})."
            );
            // Put the failed delta back into the accumulator for retry.
            let mut lock = pending_deltas.lock().unwrap_or_else(|p| p.into_inner());
            let entry = lock
                .entry((*show_id, *alloc_id, alloc_name.clone()))
                .or_insert((0, 0, 0));
            entry.0 += core_delta;
            entry.1 += gpu_delta;
            entry.2 = new_retries;
        }
    }

    // Refresh the in-memory cache from the DB (now includes flushed deltas).
    let subs = allocation_dao
        .get_subscriptions_by_show()
        .await
        .expect("Failed to fetch list of subscriptions.");
    let mut lock = cache.write().unwrap_or_else(|poison| poison.into_inner());
    *lock = subs;

    // Re-apply pending deltas on top of the fresh DB snapshot.
    //
    // Between the `take` (line above that drains the accumulator) and here,
    // `record_booking()` may have been called from dispatch threads. Those
    // calls updated the cache *and* pushed new deltas into `pending_deltas`.
    // However, the `*lock = subs` assignment above just replaced the entire
    // cache with the DB snapshot, erasing those in-memory updates.
    //
    // Additionally, any deltas that failed to flush (re-inserted during the
    // flush loop above) are also sitting in `pending_deltas`.
    //
    // Both categories represent bookings committed to the `proc` table but
    // not yet reflected in the `subscription` table. Without re-applying
    // them here, `bookable()` would under-count booked resources and risk
    // over-subscribing the allocation until the next refresh cycle.
    let current_deltas = pending_deltas.lock().unwrap_or_else(|p| p.into_inner());
    for ((show_id, _alloc_id, alloc_name), (core_delta, gpu_delta, _retries)) in
        current_deltas.iter()
    {
        if let Some(show_subs) = lock.get_mut(show_id) {
            if let Some(sub) = show_subs.get_mut(alloc_name.as_str()) {
                let new_cores = sub.booked_cores.value() as i64 + core_delta;
                sub.booked_cores = CoreSize::from_multiplied(
                    new_cores.try_into().unwrap_or(sub.booked_cores.value()),
                );
                let new_gpus = sub.booked_gpus as i64 + *gpu_delta as i64;
                sub.booked_gpus = new_gpus.try_into().unwrap_or(sub.booked_gpus);
            }
        }
    }
}
