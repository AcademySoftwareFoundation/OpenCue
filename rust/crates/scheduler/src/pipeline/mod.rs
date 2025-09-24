use std::sync::atomic::AtomicUsize;

mod dispatcher;
pub mod entrypoint;
mod matcher;

pub static HOST_CYCLES: AtomicUsize = AtomicUsize::new(0);

pub use entrypoint::run;
pub use matcher::MatchingService;
