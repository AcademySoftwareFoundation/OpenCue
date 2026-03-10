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

use std::sync::Arc;

use miette::Result;
use tokio::{sync::OnceCell, time};
use tracing::warn;

use crate::{config::CONFIG, dao::ResourceAccountingDao};

pub struct ResourceAccountingService {
    dao: Arc<ResourceAccountingDao>,
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
        Ok(ResourceAccountingService { dao })
    }

    fn start_async_loop(&self) {
        let dao = self.dao.clone();

        tokio::spawn(async move {
            let mut interval = time::interval(CONFIG.queue.resource_recalculation_interval);

            loop {
                interval.tick().await;
                if let Err(err) = dao.recompute_all_from_proc().await {
                    warn!("Failed to recompute resource accounting tables from proc: {err}");
                }
            }
        });
    }
}
