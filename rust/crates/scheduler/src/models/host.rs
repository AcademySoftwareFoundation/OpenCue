use std::fmt::Display;

use bytesize::ByteSize;
use chrono::{DateTime, Local, Utc};
use opencue_proto::host::ThreadMode;
use uuid::Uuid;

use crate::models::{core_size::CoreSize, fmt_uuid};

// TODO: Evaluate removing Clone and passing Host's reference around
#[derive(Clone, Debug)]
pub struct Host {
    pub(crate) id: Uuid,
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
    pub(crate) alloc_id: Uuid,
    pub(crate) alloc_name: String,
    pub(crate) last_updated: DateTime<Utc>,
}

impl Host {
    /// Creates a new Host instance for testing purposes.
    ///
    /// # Arguments
    ///
    /// * `id` - Host identifier
    /// * `name` - Host name
    /// * `str_os` - Operating system string
    /// * `total_cores` - Total number of cores on the host
    /// * `total_memory` - Total memory available on the host
    /// * `idle_cores` - Number of idle cores
    /// * `idle_memory` - Amount of idle memory
    /// * `idle_gpus` - Number of idle GPUs
    /// * `idle_gpu_memory` - Amount of idle GPU memory
    /// * `thread_mode` - Threading mode configuration
    /// * `alloc_available_cores` - Available cores for allocation
    /// * `allocation_name` - Name of the allocation
    ///
    /// # Returns
    ///
    /// * `Host` - New host instance configured for testing
    #[allow(dead_code)]
    #[allow(dead_code, clippy::too_many_arguments)]
    pub fn new_for_test(
        id: Uuid,
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
        alloc_id: Uuid,
        alloc_name: String,
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
            alloc_id,
            alloc_name,
            last_updated: Local::now().with_timezone(&Utc),
        }
    }
}

impl Display for Host {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}({})", self.name, fmt_uuid(&self.id))
    }
}
