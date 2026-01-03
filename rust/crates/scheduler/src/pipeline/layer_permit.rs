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

use actix::{Actor, AsyncContext, Handler, Message, WrapFuture};
use scc::HashMap;
use std::{
    sync::Arc,
    time::{Duration, SystemTime},
};
use tokio::sync::OnceCell;
use tracing::{debug, info};
use uuid::Uuid;

use miette::Result;

/// Actor message to request a permit for a layer.
///
/// Requests a permit to process a specific layer. If the layer is already
/// being processed by another task (permit hasn't expired), returns false.
/// Otherwise, grants the permit and returns true.
///
/// # Fields
///
/// * `id` - Unique identifier for the layer
/// * `duration` - How long the permit should be valid
///
/// # Returns
///
/// * `bool` - true if permit was granted, false if layer is already locked
#[derive(Message)]
#[rtype(result = "bool")]
pub struct Request {
    pub id: Uuid,
    pub duration: Duration,
}

/// Actor message to release a permit for a layer.
///
/// # Fields
///
/// * `id` - Unique identifier for the layer
///
/// # Returns
///
/// * `bool` - true if permit was release, false if there wasn't a valid permit
#[derive(Message)]
#[rtype(result = "bool")]
pub struct Release {
    pub id: Uuid,
}

/// Internal representation of a layer permit.
///
/// Tracks when a permit was issued and how long it's valid for.
struct LayerPermit {
    granted_at: SystemTime,
    duration: Duration,
}

impl LayerPermit {
    /// Creates a new permit with the specified duration.
    fn new(duration: Duration) -> Self {
        LayerPermit {
            granted_at: SystemTime::now(),
            duration,
        }
    }

    /// Checks if the permit has expired.
    fn expired(&self) -> bool {
        self.granted_at.elapsed().unwrap_or_default() > self.duration
    }
}

/// Service for managing layer processing permits using the Actor model.
///
/// Prevents multiple tasks from processing the same layer concurrently by
/// issuing time-limited permits. Each layer ID can only have one active
/// permit at a time.
#[derive(Clone)]
pub struct LayerPermitService {
    permits: Arc<HashMap<Uuid, LayerPermit>>,
}

impl Actor for LayerPermitService {
    type Context = actix::Context<Self>;

    fn started(&mut self, ctx: &mut Self::Context) {
        let service = self.clone();

        // Run cleanup every 5 minutes
        ctx.run_interval(Duration::from_secs(5 * 60), move |_act, ctx| {
            let service = service.clone();
            let actor_clone = service.clone();
            ctx.spawn(
                async move { service.cleanup_expired_permits().await }.into_actor(&actor_clone),
            );
        });

        info!("LayerPermitService actor started");
    }

    fn stopped(&mut self, _ctx: &mut Self::Context) {
        info!("LayerPermitService actor stopped");
    }
}

impl Handler<Request> for LayerPermitService {
    type Result = bool;

    fn handle(&mut self, msg: Request, _ctx: &mut Self::Context) -> Self::Result {
        let Request { id, duration } = msg;

        // Check if there's an existing permit
        let existing = self.permits.read_sync(&id, |_, permit| {
            if permit.expired() {
                // Permit exists but has expired
                None
            } else {
                // Permit exists and is still valid
                Some(())
            }
        });

        match existing {
            Some(Some(())) => {
                // Valid permit already exists - deny request
                debug!("Layer {} already has an active permit", id);
                false
            }
            _ => {
                // No valid permit exists - grant new permit
                let new_permit = LayerPermit::new(duration);
                let _ = self.permits.insert_sync(id, new_permit);
                debug!("Granted permit for layer {} (duration: {:?})", id, duration);
                true
            }
        }
    }
}

impl Handler<Release> for LayerPermitService {
    type Result = bool;

    fn handle(&mut self, msg: Release, _ctx: &mut Self::Context) -> Self::Result {
        let Release { id } = msg;

        // Check if there's an existing permit
        let existing = self.permits.remove_sync(&id);

        match existing {
            Some((_, permit)) if !permit.expired() => {
                // Valid permit removed
                true
            }
            _ => {
                // No valid permit found
                false
            }
        }
    }
}

impl LayerPermitService {
    /// Creates a new LayerPermitService with an empty permit map.
    pub fn new() -> Self {
        LayerPermitService {
            permits: Arc::new(HashMap::new()),
        }
    }

    /// Removes expired permits from the map.
    ///
    /// Runs periodically to prevent unbounded growth of the permit map.
    async fn cleanup_expired_permits(&self) {
        let mut expired_keys = Vec::new();

        // Collect expired permit IDs
        self.permits.iter_sync(|id, permit| {
            if permit.expired() {
                expired_keys.push(*id);
            }
            true
        });

        // Remove expired permits
        for id in &expired_keys {
            let _ = self.permits.remove_sync(id);
        }

        if !expired_keys.is_empty() {
            debug!("Cleaned up {} expired layer permits", expired_keys.len());
        }
    }
}

static LAYER_PERMIT_SERVICE: OnceCell<actix::Addr<LayerPermitService>> = OnceCell::const_new();

/// Gets or initializes the singleton layer permit service actor.
///
/// Returns a shared reference to the LayerPermitService actor, creating it
/// if it doesn't exist. The service manages layer processing permits to
/// prevent concurrent processing of the same layer.
///
/// # Returns
///
/// * `Ok(Addr<LayerPermitService>)` - Actor address for sending messages
/// * `Err(miette::Error)` - Failed to initialize the service
pub async fn layer_permit_service() -> Result<actix::Addr<LayerPermitService>> {
    LAYER_PERMIT_SERVICE
        .get_or_try_init(|| async {
            let service = LayerPermitService::new().start();
            Ok(service)
        })
        .await
        .cloned()
}
