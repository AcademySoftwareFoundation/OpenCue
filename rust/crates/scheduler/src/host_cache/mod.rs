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

mod actor;
mod cache;
pub mod messages;
mod store;

use actix::{Actor, Addr};
pub use cache::HostCache;

use miette::Diagnostic;
use thiserror::Error;
use uuid::Uuid;

use miette::Result;
use tokio::sync::OnceCell;
use tracing::error;

use crate::host_cache::messages::CacheRatio;

pub use actor::HostCacheService;

pub type HostId = Uuid;

static HOST_CACHE: OnceCell<Addr<HostCacheService>> = OnceCell::const_new();

/// Gets or initializes the singleton host cache service actor.
///
/// Returns a shared reference to the HostCacheService actor, creating it
/// if it doesn't exist. The service manages host availability caching and
/// checkout/checkin operations.
///
/// # Returns
///
/// * `Ok(Addr<HostCacheService>)` - Actor address for sending messages
/// * `Err(miette::Error)` - Failed to initialize the service
pub async fn host_cache_service() -> Result<Addr<HostCacheService>> {
    HOST_CACHE
        .get_or_try_init(|| async {
            let service = HostCacheService::new().await?.start();

            Ok(service)
        })
        .await
        .cloned()
}

/// Retrieves the current cache hit ratio as a percentage.
///
/// Returns the ratio of cache hits to total cache accesses (hits + misses)
/// as a percentage value between 0 and 100.
///
/// # Returns
///
/// * `usize` - Cache hit ratio percentage (0-100), or 0 if service unavailable
#[allow(dead_code)]
pub async fn hit_ratio() -> usize {
    let host_cache = host_cache_service().await;
    match host_cache {
        Ok(cache) => {
            cache
                .send(CacheRatio)
                .await
                .expect("Actor is offline")
                .hit_ratio
        }
        Err(_) => 0,
    }
}

#[derive(Debug, Error, Diagnostic)]
pub enum HostCacheError {
    #[error("No host found with the required resources")]
    NoCandidateAvailable,

    #[error(
        "Failed to query Host. Cache is functional, but can't probably load new values from the database"
    )]
    FailedToQueryHostCache(String),
}
