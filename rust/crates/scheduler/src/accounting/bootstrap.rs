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

use miette::Result;
use tracing::info;

use crate::accounting::limit_reseed;
use crate::accounting::recompute;
use crate::accounting::AccountingService;

/// Blocking startup seed. Populates the in-memory store from PG before the scheduler
/// accepts work: the enforced caps (subscription burst, folder/job max cores+gpus) first,
/// then booked counters from `SUM(proc)`. The store is the only copy of this state, so
/// this gate is mandatory - dispatching before it completes would book every hard cap wide
/// open against empty counters.
///
/// Must complete successfully before `recompute::spawn_loop` / `limit_reseed::spawn_loop`
/// / `listener::spawn_loop` are spawned and before any dispatcher accepts a host report.
pub async fn run_blocking_reseed(service: &AccountingService) -> Result<()> {
    info!("Bootstrap seed: starting (caps, then booked counters)");
    limit_reseed::reseed_once(service).await?;
    recompute::reseed_store_once(service).await?;
    info!("Bootstrap seed: complete");
    Ok(())
}
