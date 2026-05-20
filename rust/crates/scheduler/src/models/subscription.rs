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

use crate::models::CoreSize;

/// Represents a subscription linking an allocation to a show with resource limits.
///
/// A subscription defines how many resources (cores, GPUs) from a specific allocation
/// are available for a particular show. It includes both base capacity (size) and
/// burst capacity for handling peak loads.
///
/// This is the internal business logic representation, isolated from database schema changes.
#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct Subscription {
    /// Unique subscription identifier
    pub id: Uuid,

    /// Allocation ID that provides the resources
    pub allocation_id: Uuid,

    /// Allocation Name that provides the resources
    pub allocation_name: String,

    /// Show ID that can use the resources
    pub show_id: Uuid,

    /// Base resource allocation size
    pub size: i64,

    /// Additional burst capacity beyond base size (size included)
    pub burst: CoreSize,

    /// Number of CPU cores allocated
    pub booked_cores: CoreSize,

    /// Number of GPUs currently booked against this subscription
    pub booked_gpus: u32,
}

/// Represents an allocation (resource pool) in the system.
///
/// An allocation is a pool of compute resources that can be assigned to shows
/// through subscriptions. It represents a logical grouping of hosts and their
/// resources within a facility.
///
/// This is the internal business logic representation, isolated from database schema changes.
#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct Allocation {
    /// Unique allocation identifier
    pub id: Uuid,

    /// Allocation name
    pub name: String,

    /// Whether this allocation can be edited
    pub allow_edit: bool,

    /// Whether this is the default allocation
    pub is_default: bool,

    /// Optional tag for categorization
    pub tag: Option<String>,

    /// Whether usage is billable
    pub billable: bool,

    /// Facility ID that owns this allocation
    pub facility_id: Uuid,

    /// Whether this allocation is enabled
    pub enabled: bool,
}

impl Subscription {
    fn is_frozen(&self) -> bool {
        // Setting a subscription burst to 0 will freeze it
        self.burst.value() <= 0
    }

    pub fn can_book(&self, cores_required: &CoreSize) -> bool {
        !self.is_frozen()
            && self.booked_cores.value() + cores_required.value() <= self.burst.value()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_subscription(booked_cores: i32, burst: i32) -> Subscription {
        Subscription {
            id: Uuid::new_v4(),
            allocation_id: Uuid::new_v4(),
            allocation_name: "test-alloc".to_string(),
            show_id: Uuid::new_v4(),
            size: 100,
            burst: CoreSize(burst),
            booked_cores: CoreSize(booked_cores),
            booked_gpus: 0,
        }
    }

    #[test]
    fn test_can_book_within_burst() {
        let sub = make_subscription(100, 200);
        assert!(sub.can_book(&CoreSize(50)));
    }

    #[test]
    fn test_can_book_exactly_at_burst() {
        let sub = make_subscription(150, 200);
        assert!(sub.can_book(&CoreSize(50)));
    }

    #[test]
    fn test_can_book_exceeds_burst() {
        let sub = make_subscription(180, 200);
        assert!(!sub.can_book(&CoreSize(50)));
    }

    #[test]
    fn test_can_book_frozen_subscription_zero_burst() {
        let sub = make_subscription(0, 0);
        assert!(!sub.can_book(&CoreSize(1)));
    }

    #[test]
    fn test_can_book_frozen_subscription_negative_burst() {
        let sub = make_subscription(0, -10);
        assert!(!sub.can_book(&CoreSize(1)));
    }
}
