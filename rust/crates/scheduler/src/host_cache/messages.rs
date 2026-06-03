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

use uuid::Uuid;

use crate::{cluster_key::ClusterKey, models::Host};

/// Result of a successful host check-out.
///
/// The cluster key is needed to return the host to the correct cache group
/// after use.
pub struct CheckedOutHost(pub ClusterKey, pub Host);

/// Argument to [`HostCacheService::check_in_payload`] — either return a host
/// with updated resources, or invalidate a host by id (removing any
/// outstanding reservation but not re-adding the host to the cache).
pub enum CheckInPayload {
    Host(Host),
    Invalidate(Uuid),
}

/// Snapshot of host-cache hit/miss statistics.
pub struct CacheRatioResponse {
    #[allow(dead_code)]
    pub hit: u64,
    #[allow(dead_code)]
    pub miss: u64,
    pub hit_ratio: usize,
}
