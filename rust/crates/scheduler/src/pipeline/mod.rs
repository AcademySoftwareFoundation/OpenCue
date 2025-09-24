use std::sync::atomic::AtomicUsize;

mod dispatcher;
pub mod entrypoint;
mod matcher;

pub static HOST_ATTEMPTS: AtomicUsize = AtomicUsize::new(0);

pub use entrypoint::run;
pub use matcher::MachingService;
