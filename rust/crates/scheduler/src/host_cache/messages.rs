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

use actix::{Message, MessageResponse};

use bytesize::ByteSize;
use miette::Result;
use uuid::Uuid;

use crate::{
    cluster_key::{ClusterKey, Tag},
    host_cache::{cache::Gate, HostCacheError},
    models::{CoreSize, Host},
    pipeline::placement::LayerProfile,
};

/// Response containing a checked-out host and its associated cluster key.
///
/// Returned when a host is successfully checked out from the cache. The cluster
/// key is needed to return the host to the correct cache group after use.
///
/// # Fields
///
/// * `0` - ClusterKey identifying the cache group this host belongs to
/// * `1` - Host with reserved resources
#[derive(MessageResponse)]
pub struct CheckedOutHost(pub ClusterKey, pub Host);

/// Actor message to check out a host from the cache.
///
/// Requests a host that matches the layer's floor (carried by `profile`) and
/// passes the `gate` function. The cache searches through groups for each
/// tag in priority order (MANUAL > HOSTNAME > HARDWARE > ALLOC) until a
/// suitable host is found.
///
/// The `gate` is a plain `fn` pointer (no closure capture), so this message
/// is non-generic and a single `Handler` impl serves every booking strategy.
/// All per-call data flows through `profile`.
///
/// # Fields
///
/// * `facility_id` - Facility identifier for the cluster key
/// * `show_id` - Show identifier for the cluster key
/// * `tags` - List of tags to search (tried in priority order)
/// * `cores` / `memory` - Range hints for the B-tree query (floors enforced by `gate`)
/// * `profile` - Placement context (floors, compatibility, E-PVM caps + weights)
/// * `gate` - Validates and (for E-PVM) scores each candidate
///
/// # Returns
///
/// * `Ok(CheckedOutHost)` - Successfully found and reserved a matching host
/// * `Err(HostCacheError::NoCandidateAvailable)` - No host meets requirements
/// * `Err(HostCacheError::FailedToQueryHostCache)` - Database query failed
#[derive(Message)]
#[rtype(result = "Result<CheckedOutHost, HostCacheError>")]
pub struct CheckOut {
    pub facility_id: String,
    pub show_id: Uuid,
    pub tags: Vec<Tag>,
    pub cores: CoreSize,
    pub memory: ByteSize,
    pub profile: LayerProfile,
    pub gate: Gate,
}

/// Payload for checking in a host or invalidating a host in the cache.
///
/// Allows either returning a host with updated resources to the cache or
/// invalidating a host by its id, removing it from the cache entirely.
///
/// # Variants
///
/// * `Host(Host)` - Return a host with updated idle resource counts
/// * `Invalidate(Uuid)` - Invalidate and remove a host by id
pub enum CheckInPayload {
    Host(Host),
    Invalidate(Uuid),
}

/// Actor message to return a host to the cache or invalidate it.
///
/// Returns a host back to its cache group with updated resource state, or
/// invalidates a host by id, removing it from the cache. When returning
/// a host, it is removed from the reservation list and becomes available for
/// checkout again. If the cache group has expired, the host is dropped.
///
/// # Fields
///
/// * `0` - ClusterKey identifying which cache group the host belongs to
/// * `1` - CheckInPayload specifying whether to return a host or invalidate by id
///
/// # Returns
///
/// * `()` - Operation completed successfully (host returned/invalidated or cache group expired)
#[derive(Message)]
#[rtype(result = "()")]
pub struct CheckIn(pub ClusterKey, pub CheckInPayload);

/// Actor message to retrieve cache performance metrics.
///
/// Requests the current cache hit/miss statistics from the HostCacheService.
/// Used for monitoring cache effectiveness.
///
/// # Returns
///
/// * `CacheRatioResponse` - Cache performance metrics
#[derive(Message)]
#[rtype(result =  CacheRatioResponse)]
pub struct CacheRatio;

/// Response containing cache performance statistics.
///
/// Provides metrics about cache hit/miss rates for monitoring cache effectiveness.
/// A high hit ratio indicates the cache is effectively reducing database queries.
///
/// # Fields
///
/// * `hit_ratio` - Percentage of cache hits (0-100)
#[derive(MessageResponse)]
pub struct CacheRatioResponse {
    pub hit_ratio: usize,
}
