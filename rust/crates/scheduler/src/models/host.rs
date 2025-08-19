use std::fmt::Display;

use opencue_proto::host::ThreadMode;
use uuid::Uuid;

use crate::models::{core_size::CoreSize, fmt_uuid};

#[derive(Clone)]
pub struct Host {
    pub(crate) id: Uuid,
    pub(crate) name: String,
    pub(crate) str_os: Option<String>,
    pub(crate) total_cores: CoreSize,
    pub(crate) total_memory: u64,
    pub(crate) idle_cores: CoreSize,
    pub(crate) idle_memory: u64,
    pub(crate) idle_gpus: u32,
    pub(crate) idle_gpu_memory: u64,
    pub(crate) thread_mode: ThreadMode,
    pub(crate) alloc_available_cores: CoreSize,
    pub(crate) allocation_name: String,
}

impl Display for Host {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}({})", self.name, fmt_uuid(&self.id))
    }
}
