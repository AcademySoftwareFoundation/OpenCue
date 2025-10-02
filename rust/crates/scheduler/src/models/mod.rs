mod core_size;
mod frame;
mod host;
mod job;
mod layer;
mod virtual_proc;

pub use core_size::{CoreSize, CoreSizeWithMultiplier};
pub use frame::DispatchFrame;
pub use host::Host;
pub use job::DispatchJob;
pub use layer::DispatchLayer;
pub use virtual_proc::VirtualProc;

/// Formats a UUID by returning only the first segment before the first hyphen.
///
/// # Arguments
///
/// * `id` - Full UUID string
///
/// # Returns
///
/// * `String` - First segment of the UUID, or the full string if no hyphen exists
pub fn fmt_uuid(id: &String) -> String {
    id.split_once("-")
        .unwrap_or((&id.to_string(), ""))
        .0
        .to_string()
}
