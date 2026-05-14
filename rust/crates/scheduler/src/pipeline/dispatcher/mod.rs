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

pub mod actor;
pub mod error;
mod frame_set;
pub mod messages;

use miette::Result;
use std::sync::Arc;

pub use actor::RqdDispatcherService;
use tokio::sync::OnceCell;

use crate::dao::{LayerDao, ProcDao};

static RQD_DISPATCHER: OnceCell<RqdDispatcherService> = OnceCell::const_new();

/// Singleton getter for the RQD dispatcher service.
///
/// Returns a cloned handle to the service. `RqdDispatcherService` is `Clone`
/// and internally `Arc`-shared, so the returned value is cheap to pass around.
pub async fn rqd_dispatcher_service() -> Result<RqdDispatcherService, miette::Error> {
    RQD_DISPATCHER
        .get_or_try_init(|| async {
            use crate::{
                config::CONFIG,
                dao::{FrameDao, HostDao},
            };

            let frame_dao = Arc::new(FrameDao::new().await?);
            let layer_dao = Arc::new(LayerDao::new().await?);
            let host_dao = Arc::new(HostDao::new().await?);
            let proc_dao = Arc::new(ProcDao::new().await?);

            RqdDispatcherService::new(
                frame_dao,
                layer_dao,
                host_dao,
                proc_dao,
                CONFIG.rqd.dry_run_mode,
            )
            .await
        })
        .await
        .cloned()
}
