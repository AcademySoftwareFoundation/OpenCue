use actix::{Message, MessageResponse};

use bytesize::ByteSize;
use miette::Result;
use uuid::Uuid;

use crate::{
    cluster_key::{ClusterKey, Tag},
    host_cache::HostCacheError,
    models::{CoreSize, Host},
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
/// Requests a host that matches the specified resource requirements and passes
/// the validation function. The cache will search through groups for each tag
/// in priority order (MANUAL > HOSTNAME > ALLOC) until a suitable host is found.
///
/// If not found in cache, the service will fetch from the database. The host
/// is removed from the cache and must be checked back in after use.
///
/// # Fields
///
/// * `facility_id` - Facility identifier for the cluster key
/// * `show_id` - Show identifier for the cluster key
/// * `tags` - List of tags to search (tried in priority order)
/// * `cores` - Minimum number of cores required
/// * `memory` - Minimum memory required
/// * `validation` - Function to validate additional host requirements
///
/// # Returns
///
/// * `Ok(CheckedOutHost)` - Successfully found and reserved a matching host
/// * `Err(HostCacheError::NoCandidateAvailable)` - No host meets requirements
/// * `Err(HostCacheError::FailedToQueryHostCache)` - Database query failed
#[derive(Message)]
#[rtype(result = "Result<CheckedOutHost, HostCacheError>")]
pub struct CheckOut<F>
where
    F: Fn(&Host) -> bool,
{
    pub facility_id: Uuid,
    pub show_id: Uuid,
    pub tags: Vec<Tag>,
    pub resource_request: ResourceRequest,
    pub validation: F,
}

#[derive(Clone, Copy)]
pub enum ResourceRequest {
    /// Request a machine with at least this amount of cores and memory idle
    CoresAndMemory { cores: CoreSize, memory: ByteSize },
    /// Request a machine with this amount of gpu cores idle
    Gpu(CoreSize),
    /// Request a machine with this amount of frame slots available
    Slots(u32),
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
/// * `hit` - Total number of cache hits (hosts found in cache)
/// * `miss` - Total number of cache misses (required database fetch)
/// * `hit_ratio` - Percentage of cache hits (0-100)
#[derive(MessageResponse)]
pub struct CacheRatioResponse {
    #[allow(dead_code)]
    pub hit: u64,
    #[allow(dead_code)]
    pub miss: u64,
    pub hit_ratio: usize,
}
