mod actor;
mod cache;
pub mod messages;

use actix::{Actor, Addr};
pub use cache::HostCache;

use miette::Diagnostic;
use thiserror::Error;

use miette::Result;
use tokio::sync::OnceCell;
use tracing::error;

use crate::host_cache::messages::CacheRatio;

pub use actor::HostCacheService;

static HOST_CACHE: OnceCell<Addr<HostCacheService>> = OnceCell::const_new();

/// Singleton getter for the cache service
pub async fn host_cache_service() -> Result<Addr<HostCacheService>> {
    HOST_CACHE
        .get_or_try_init(|| async {
            let service = HostCacheService::new().await?.start();

            // TODO: Uncomment and make test aware
            // service.clone().start();

            Ok(service)
        })
        .await
        .cloned()
}

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
