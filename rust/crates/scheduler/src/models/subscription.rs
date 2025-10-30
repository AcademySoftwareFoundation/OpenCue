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
    pub id: String,

    /// Allocation ID that provides the resources
    pub allocation_id: String,

    /// Allocation Name that provides the resources
    pub allocation_name: String,

    /// Show ID that can use the resources
    pub show_id: String,

    /// Base resource allocation size
    pub size: i64,

    /// Additional burst capacity beyond base size (size included)
    pub burst: CoreSize,

    /// Number of CPU cores allocated
    pub booked_cores: CoreSize,

    /// Number of GPUs allocated
    pub gpus: u32,
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
    pub id: String,

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
    pub facility_id: String,

    /// Whether this allocation is enabled
    pub enabled: bool,
}

impl Subscription {
    fn is_frozen(&self) -> bool {
        // Setting a subscription burst to 0 will freeze it
        self.burst.value() <= 0
    }

    pub fn bookable(&self, cores_required: &CoreSize) -> bool {
        !self.is_frozen() &&
        // Booking the amount requested should leave at least one cores reminding
        self.booked_cores.value() + cores_required.value() < self.burst.value()
    }
}
