use uuid::Uuid;

pub mod linux;
pub mod machine;
mod nimby;
mod reservation;

#[cfg(target_os = "macos")]
pub mod macos;
pub mod manager;

pub type ResourceId = Uuid;
pub type CoreId = u32;
pub type PhysId = u32;
pub type ThreadId = u32;
