mod core_size;
mod frame;
mod host;
mod job;
mod layer;
mod subscription;
mod virtual_proc;

pub use core_size::{CoreSize, CoreSizeWithMultiplier};
pub use frame::DispatchFrame;
pub use host::Host;
pub use job::DispatchJob;
pub use layer::{DispatchLayer, ResourceRequest};
pub use subscription::{Allocation, Subscription};
pub use virtual_proc::VirtualProc;

use uuid::Uuid;

/// Formats a UUID by returning only the first segment before the first hyphen.
///
/// # Arguments
///
/// * `id` - UUID reference
///
/// # Returns
///
/// * `String` - First segment of the UUID (8 characters)
pub fn fmt_uuid(id: &Uuid) -> String {
    // Uuid::simple() returns a 32-character hex string without hyphens
    // We take the first 8 characters which corresponds to the first segment
    id.simple().to_string()[..8].to_string()
}
