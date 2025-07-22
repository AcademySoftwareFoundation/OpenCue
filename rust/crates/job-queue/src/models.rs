use core::fmt;
use miette::Result;
use std::fmt::Display;

use opencue_proto::host::ThreadMode;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

//=== Job ===
#[derive(Serialize, Deserialize, Clone)]
pub struct DispatchJob {
    pub id: Uuid,
    pub int_priority: i32,
    pub age_days: i32,
}

pub trait Partitionable {
    fn partition_key(&self) -> String;
}

impl fmt::Display for DispatchJob {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.id)
    }
}

impl Partitionable for DispatchJob {
    fn partition_key(&self) -> String {
        self.id.to_string()
    }
}

//=== DispatchLayer ===
#[derive(Serialize, Deserialize)]
pub struct DispatchLayer {
    pub id: Uuid,
    pub job_id: Uuid,
    pub facility_id: Uuid,
    pub show_id: Uuid,
    pub str_os: String,
    pub cores_min: i32,
    pub mem_min: i32,
    pub threadable: bool,
    pub gpus_min: i32,
    pub gpu_mem_min: i32,
    pub tags: String,
}

impl DispatchLayer {
    pub fn with_validation(self) -> (Self, DispatchState) {
        // TODO: Implement validation logic based on opencue's Business logic
        if self.cores_min <= 0 {
            (self, DispatchState::InvalidCoreMinRequirement)
        } else {
            (self, DispatchState::Valid)
        }
    }
}

impl fmt::Display for DispatchLayer {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.id)
    }
}
pub enum DispatchState {
    Valid,
    InvalidCoreMinRequirement,
}

//=== Host ===

#[derive(Clone)]
pub struct Host {
    pub id: Uuid,
    pub name: String,
    pub str_os: Option<String>,
    pub total_cores: u32,
    pub total_memory: u64,
    pub idle_cores: u32,
    pub idle_memory: u64,
    pub idle_gpus: u32,
    pub idle_gpu_memory: u64,
    pub thread_mode: ThreadMode,
}

impl Host {
    pub fn is_allocation_at_or_over_burst(&self, show_id: &Uuid) -> Result<()> {
        todo!("Add more fields to HostModel to fill up this request")
    }
}

impl Display for Host {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}({})", self.name, self.id)
    }
}

//=== DispatchFrame ===

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
    pub min_cores: i32,
    pub max_cores: u32,
    pub threadable: bool,
    pub has_selfish_service: bool,
    pub min_gpus: u32,
    pub min_gpu_memory: u64,
    pub min_memory: u64,
    // On Cuebot these fields come from constants, maybe replicate these constants here
    // pub int_soft_memory_limit: i64,
    // pub int_hard_memory_limit: i64,
    pub services: Option<String>,
    pub os: Option<String>,
    pub loki_url: Option<String>,
}

impl Display for DispatchFrame {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}.{}({})", self.job_name, self.frame_name, self.id)
    }
}

//=== VirtualProc ===

#[derive(Serialize, Deserialize)]
pub struct VirtualProc {
    pub proc_id: Uuid,
    pub host_id: Uuid,
    pub cores_reserved: u32,  // in hundredths
    pub memory_reserved: u64, // in bytes
    pub gpus_reserved: u32,
    pub gpu_memory_reserved: u64, // in bytes
    pub os: String,
    pub is_local_dispatch: bool,
    pub frame: DispatchFrame,
}
