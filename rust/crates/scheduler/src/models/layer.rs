use core::fmt;

use bytesize::ByteSize;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::models::{core_size::CoreSize, fmt_uuid};

#[derive(Serialize, Deserialize)]
pub struct DispatchLayer {
    pub id: Uuid,
    pub job_id: Uuid,
    pub facility_id: Uuid,
    pub show_id: Uuid,
    pub job_name: String,
    pub layer_name: String,
    pub str_os: Option<String>,
    pub cores_min: CoreSize,
    pub mem_min: ByteSize,
    pub threadable: bool,
    pub gpus_min: i32,
    pub gpu_mem_min: ByteSize,
    pub tags: String,
}

impl fmt::Display for DispatchLayer {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}.{}({})",
            self.job_name,
            self.layer_name,
            fmt_uuid(&self.id)
        )
    }
}
