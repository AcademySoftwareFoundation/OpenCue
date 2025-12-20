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
use uuid::Uuid;

use crate::{
    config::CONFIG, dao::AllocationDao, dao::AllocationName, dao::ShowId, models::Subscription,
};

pub struct AllocationService {
    cache: Arc<RwLock<HashMap<ShowId, HashMap<AllocationName, Subscription>>>>,
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
        let cache = Arc::new(RwLock::new(HashMap::new()));
        let service = AllocationService {
            cache: cache.clone(),
            allocation_dao: allocation_dao.clone(),
        };

        // Fetch data at init to avoid having to wait for a loop iteration to fill up the cache
        let subs = allocation_dao.get_subscriptions_by_show().await?;
        let mut lock = cache.write().unwrap_or_else(|poison| poison.into_inner());
        *lock = subs;

        Ok(service)
    }

    fn start_async_loop(&self) {
        let cache = self.cache.clone();
        let allocation_dao = self.allocation_dao.clone();

        tokio::spawn(async move {
            let mut interval = time::interval(CONFIG.queue.allocation_refresh_interval);

            loop {
                interval.tick().await;

                let subs = allocation_dao
                    .get_subscriptions_by_show()
                    .await
                    .expect("Failed to fetch list of subscriptions.");
                let mut lock = cache.write().unwrap_or_else(|poison| poison.into_inner());
                *lock = subs;
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
}
