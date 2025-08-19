mod core_size;
mod frame;
mod host;
mod job;
mod layer;
mod virtual_proc;

use uuid::Uuid;

pub use core_size::{CoreSize, CoreSizeWithMultiplier};
pub use frame::DispatchFrame;
pub use host::Host;
pub use job::DispatchJob;
pub use layer::DispatchLayer;
pub use virtual_proc::VirtualProc;

pub fn fmt_uuid(id: &Uuid) -> String {
    id.to_string()
        .split_once("-")
        .unwrap_or((&id.to_string(), ""))
        .0
        .to_string()
}

pub trait Partitionable {
    fn partition_key(&self) -> String;
}
