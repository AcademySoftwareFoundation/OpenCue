use uuid::Uuid;

pub mod gpu;
pub mod linux;
pub mod machine;
#[cfg(feature = "nimby")]
pub mod nimby;
mod oom;
mod reservation;

#[cfg(target_os = "macos")]
pub mod macos;
pub mod manager;

pub type ResourceId = Uuid;
pub type CoreId = u32;
pub type PhysId = u32;
pub type ThreadId = u32;

pub use oom::OOM_REASON_MSG;
