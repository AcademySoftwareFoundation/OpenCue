use std::fmt::Display;

use bytesize::ByteSize;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::models::{core_size::CoreSize, fmt_uuid};

#[derive(Serialize, Deserialize)]
pub struct DispatchFrame {
    // Entity fields
    pub id: Uuid,
    pub frame_name: String,

    // LayerEntity fields
    pub show_id: Uuid,
    pub facility_id: Uuid,
    pub job_id: Uuid,

    // FrameEntity fields
    pub layer_id: Uuid,

    // DispatchFrame specific fields
    pub command: String,
    pub range: String,
    pub chunk_size: i32,
    pub show_name: String,
    pub shot: String,
    pub user: String,
    pub uid: Option<i32>,
    pub log_dir: String,
    pub layer_name: String,
    pub job_name: String,
    // Min cores can be a negative, representing `machine_total_cores - min_cores`
    pub min_cores: CoreSize,
    pub layer_cores_limit: Option<CoreSize>,
    pub threadable: bool,
    pub has_selfish_service: bool,
    pub min_gpus: u32,
    pub min_gpu_memory: ByteSize,
    pub min_memory: ByteSize,
    // On Cuebot these fields come from constants, maybe replicate these constants here
    // pub int_soft_memory_limit: i64,
    // pub int_hard_memory_limit: i64,
    pub services: Option<String>,
    pub os: Option<String>,
    pub loki_url: Option<String>,
}

impl Display for DispatchFrame {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}.{}.{}({})",
            self.job_name,
            self.layer_name,
            self.frame_name,
            fmt_uuid(&self.id)
        )
    }
}
