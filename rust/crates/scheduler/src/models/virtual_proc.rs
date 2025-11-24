use std::fmt::Display;

use bytesize::ByteSize;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::models::{fmt_uuid, CoreSizeWithMultiplier, DispatchFrame};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct VirtualProc {
    pub proc_id: Uuid,
    pub host_id: Uuid,
    pub show_id: Uuid,
    pub layer_id: Uuid,
    pub job_id: Uuid,
    pub frame_id: Uuid,
    pub alloc_id: Uuid,
    pub host_name: String,
    pub cores_reserved: CoreSizeWithMultiplier,
    pub memory_reserved: ByteSize,
    pub gpus_reserved: u32,
    pub gpu_memory_reserved: ByteSize,
    pub os: String,
    pub is_local_dispatch: bool,
    pub frame: DispatchFrame,
}

impl Display for VirtualProc {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "(proc_id={}) {}->host={}",
            fmt_uuid(&self.proc_id),
            self.frame,
            fmt_uuid(&self.host_id),
        )
    }
}
