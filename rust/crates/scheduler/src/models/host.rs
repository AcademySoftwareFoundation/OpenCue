use std::fmt::Display;

use bytesize::ByteSize;
use opencue_proto::host::ThreadMode;

use crate::models::{core_size::CoreSize, fmt_uuid};

// TODO: Evaluate removing Clone and passing Host's reference around
#[derive(Clone, Debug)]
pub struct Host {
    pub(crate) id: String,
    pub(crate) name: String,
    pub(crate) str_os: Option<String>,
    pub(crate) total_cores: CoreSize,
    pub(crate) total_memory: ByteSize,
    pub(crate) idle_cores: CoreSize,
    pub(crate) idle_memory: ByteSize,
    pub(crate) idle_gpus: u32,
    pub(crate) idle_gpu_memory: ByteSize,
    pub(crate) thread_mode: ThreadMode,
    pub(crate) alloc_available_cores: CoreSize,
    pub(crate) allocation_name: String,
}

impl Host {
    pub fn new_for_test(
        id: String,
        name: String,
        str_os: Option<String>,
        total_cores: CoreSize,
        total_memory: ByteSize,
        idle_cores: CoreSize,
        idle_memory: ByteSize,
        idle_gpus: u32,
        idle_gpu_memory: ByteSize,
        thread_mode: ThreadMode,
        alloc_available_cores: CoreSize,
        allocation_name: String,
    ) -> Self {
        Self {
            id,
            name,
            str_os,
            total_cores,
            total_memory,
            idle_cores,
            idle_memory,
            idle_gpus,
            idle_gpu_memory,
            thread_mode,
            alloc_available_cores,
            allocation_name,
        }
    }
}

impl Display for Host {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}({})", self.name, fmt_uuid(&self.id))
    }
}
