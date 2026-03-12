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
    sync::{Arc, RwLock},
};

use miette::Result;
use tokio::{sync::OnceCell, time};
use tracing::warn;
use uuid::Uuid;

use crate::{
    config::CONFIG,
    dao::{AllocationName, ResourceAccountingDao, ShowId},
    models::{CoreSize, Subscription},
};

pub struct ResourceAccountingService {
    dao: Arc<ResourceAccountingDao>,
    target_shows: Option<Vec<Uuid>>,
    cache: Arc<RwLock<HashMap<ShowId, HashMap<AllocationName, Subscription>>>>,
}

static RESOURCE_ACCOUNTING_SERVICE: OnceCell<Arc<ResourceAccountingService>> =
    OnceCell::const_new();

pub async fn resource_accounting_service() -> Result<Arc<ResourceAccountingService>> {
    RESOURCE_ACCOUNTING_SERVICE
        .get_or_try_init(|| async {
            let service = ResourceAccountingService::init().await?;
            service.start_async_loop();
            Ok(Arc::new(service))
        })
        .await
        .cloned()
}

impl ResourceAccountingService {
    async fn init() -> Result<Self> {
        let dao = Arc::new(ResourceAccountingDao::new().await?);

        // Resolve show names → UUIDs
        let show_names = CONFIG.scheduler.show_names();
        let target_shows = match show_names {
            Some(show_names) => Some(dao.query_show_ids_by_names(show_names).await?),
            None => None,
        };

        // Fetch subscriptions from DB
        let mut subs = dao.get_subscriptions_by_show().await?;

        // Recompute booked counts from the proc table so the cache is accurate
        // even if the subscription table drifted (e.g. after a crash).
        match dao.recompute_booked_from_proc().await {
            Ok(booked_map) => {
                for ((show_id, alloc_name), (cores_booked, gpus_booked)) in booked_map {
                    let Some(show_subs) = subs.get_mut(&show_id) else {
                        continue;
                    };
                    let Some(sub) = show_subs.get_mut(&alloc_name) else {
                        continue;
                    };
                    sub.booked_cores =
                        CoreSize::from_multiplied(cores_booked.try_into().unwrap_or_else(|_| {
                            warn!(
                                "Recomputed booked cores overflowed i32 for \
                                         show={show_id} alloc={alloc_name}, \
                                         using subscription table value"
                            );
                            sub.booked_cores.value()
                        }));
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
            Err(err) => {
                warn!(
                    "Could not recompute booked cores from proc table on startup; \
                     using subscription table values instead: {err}"
                );
            }
        }

        let cache = Arc::new(RwLock::new(subs));
        Ok(ResourceAccountingService {
            dao,
            target_shows,
            cache,
        })
    }

    /// Resource recalculation loop (layer/job/folder/point/subscription tables)
    fn start_async_loop(&self) {
        let dao = self.dao.clone();
        let target_shows_opt = self.target_shows.clone();

        // One async loop to recalculate all resource tables and the point table
        // (subscription not included)
        tokio::spawn(async move {
            let mut interval = time::interval(CONFIG.queue.resource_recalculation_interval);
            // Skip the immediate first tick — init() already ran the initial computation.
            interval.tick().await;

            loop {
                interval.tick().await;
                if let Err(err) = dao.recompute_all_from_proc(&target_shows_opt).await {
                    warn!("Failed to recompute resource accounting tables from proc: {err}");
                }
            }
        });

        // Subscription recalculation loop
        let cache = self.cache.clone();
        let dao = self.dao.clone();
        let target_shows = self.target_shows.clone();

        // One separate async loop to recalculate subscriptions
        tokio::spawn(async move {
            let mut interval = time::interval(CONFIG.queue.subscription_recalculation_interval);
            // Skip the immediate first tick — init() already fetched + recomputed on startup.
            interval.tick().await;

            loop {
                interval.tick().await;
                recalculate_and_refresh(&cache, &dao, &target_shows).await;
            }
        });
    }

    pub fn get_subscription(&self, allocation_name: &str, show_id: &Uuid) -> Option<Subscription> {
        self.cache
            .read()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
            .get(show_id)?
            .get(allocation_name)
            .cloned()
    }

    /// Records a successful frame booking in the in-memory cache.
    ///
    /// Call this after the frame's database transaction has been committed. The in-memory
    /// `booked_cores` update keeps `bookable()` accurate for subsequent frames in the same
    /// dispatch cycle without waiting for the next DB refresh.
    ///
    /// # Arguments
    ///
    /// * `show_id` - The UUID of the show to which the booking applies
    /// * `alloc_name` - The name of the allocation (resource pool) being booked
    /// * `core_delta` - The change in booked cores (positive for booking, negative for release)
    /// * `gpu_delta` - The change in booked GPUs (positive for booking, negative for release)
    pub fn record_booking(&self, show_id: Uuid, alloc_name: &str, core_delta: i64, gpu_delta: i32) {
        let mut cache = self.cache.write().unwrap_or_else(|p| p.into_inner());
        if let Some(show_subs) = cache.get_mut(&show_id) {
            if let Some(sub) = show_subs.get_mut(alloc_name) {
                let new_booked = sub.booked_cores.value() as i64 + core_delta;
                sub.booked_cores =
                    CoreSize::from_multiplied(new_booked.try_into().unwrap_or_else(|_| {
                        warn!(
                            "Booked cores overflowed i32 for show={show_id} \
                             alloc={alloc_name}, using previous value"
                        );
                        sub.booked_cores.value()
                    }));

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
}

/// Recomputes the subscription table from proc, then refreshes the in-memory cache.
///
/// **Race window:** bookings committed between the DB recompute and the cache write
/// may briefly appear as available capacity. This is acceptable because:
///  - the window is bounded to ~3s,
///  - host-level resource checks provide a hard safety net against actual over-dispatch, and
///  - the delta-tracking approach adds significant complexity for marginal benefit.
async fn recalculate_and_refresh(
    cache: &Arc<RwLock<HashMap<ShowId, HashMap<AllocationName, Subscription>>>>,
    dao: &Arc<ResourceAccountingDao>,
    show_ids: &Option<Vec<Uuid>>,
) {
    // Recompute the subscription table in the DB from the proc table.
    if let Err(err) = dao.recompute_subscription_table(show_ids).await {
        warn!("Failed to recompute subscription table from proc: {err}");
        return;
    }

    // Read fresh subscriptions from the DB.
    let subs = match dao.get_subscriptions_by_show().await {
        Ok(subs) => subs,
        Err(err) => {
            warn!("Failed to fetch subscriptions after recompute: {err}");
            return;
        }
    };

    let mut lock = cache.write().unwrap_or_else(|poison| poison.into_inner());
    *lock = subs;
}
