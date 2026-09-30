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

// TODO: multi-scheduler race - first-mover-wins reseed semantics deferred (design §5).
// Today's single-scheduler model means there is no concurrent bootstrap; when leader
// election lands, only the leader should call run_blocking_reseed at startup.

use miette::Result;
use tracing::info;

use crate::accounting::limit_reseed;
use crate::accounting::recompute;
use crate::accounting::AccountingService;

/// Blocking startup reseed. Populates Redis from PG before the scheduler accepts work:
/// limit fields (subscription burst, folder/job/point caps) first, then booked counters
/// (`int_cores`/`int_gpus`) from `SUM(proc)`. Idempotent - `HSET` overwrites, and the
/// limit-fields and booked-counter-fields are disjoint so a partial Redis state from a
/// previous run is safely replaced.
///
/// Must complete successfully before `recompute::spawn_loop` / `limit_reseed::spawn_loop`
/// are spawned and before any dispatcher accepts a host report - see design §4.3 row 5.
pub async fn run_blocking_reseed(service: &AccountingService) -> Result<()> {
    info!("Bootstrap reseed: starting (limits, then booked counters)");
    limit_reseed::reseed_once(service).await?;
    recompute::reseed_redis_once(service).await?;
    info!("Bootstrap reseed: complete");
    Ok(())
}
