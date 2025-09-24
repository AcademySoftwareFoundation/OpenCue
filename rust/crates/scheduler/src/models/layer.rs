use core::fmt;
use std::collections::HashSet;

use bytesize::ByteSize;
use serde::{Deserialize, Serialize};

use crate::models::{DispatchFrame, core_size::CoreSize, fmt_uuid};

#[derive(Serialize, Deserialize, Clone)]
pub struct DispatchLayer {
    pub id: String,
    pub job_id: String,
    pub facility_id: String,
    pub show_id: String,
    pub job_name: String,
    pub layer_name: String,
    pub str_os: Option<String>,
    pub cores_min: CoreSize,
    pub mem_min: ByteSize,
    pub threadable: bool,
    pub gpus_min: i32,
    pub gpu_mem_min: ByteSize,
    pub tags: HashSet<String>,
    pub frames: Vec<DispatchFrame>,
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

impl DispatchLayer {
    pub fn drain_frames(&mut self, count: usize) {
        self.frames.drain(0..count);
    }
}
