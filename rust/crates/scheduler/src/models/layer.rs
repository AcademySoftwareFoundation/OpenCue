// Copyright Contributors to the OpenCue Project
//
// Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
// in compliance with the License. You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software distributed under the License
// is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
// or implied. See the License for the specific language governing permissions and limitations under
// the License.

use core::fmt;
use std::collections::HashSet;

use bytesize::ByteSize;
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::models::{core_size::CoreSize, fmt_uuid, DispatchFrame};

#[derive(Serialize, Deserialize, Clone, Debug)]
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
    pub gpus_min: CoreSize,
    pub gpu_mem_min: ByteSize,
    pub slots_required: u32,
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

/// Describes what resources are required to run a frame from this layer
#[derive(Clone, Copy)]
pub enum ResourceRequest {
    /// Request a machine with at least this amount of cores and memory idle
    CoresAndMemory { cores: CoreSize, memory: ByteSize },
    /// Request a machine with this amount of gpu cores idle
    Gpu { cores: CoreSize, memory: ByteSize },
    /// Request a machine with this amount of frame slots available
    Slots(u32),
}

impl DispatchLayer {
    /// Removes frames with matching IDs from this layer's frame list.
    ///
    /// Used to clean up frames after dispatch attempts (both successful and failed)
    /// to prevent livelock situations where frames are repeatedly retried.
    ///
    /// # Arguments
    ///
    /// * `frame_ids` - Vector of frame IDs to remove from the layer
    pub fn drain_frames(&mut self, frame_ids: Vec<Uuid>) {
        self.frames.retain(|f| !frame_ids.contains(&f.id))
    }

    pub fn resource_request(&self) -> ResourceRequest {
        if self.slots_required > 0 {
            ResourceRequest::Slots(self.slots_required)
        } else if self.gpus_min.value() > 0 {
            ResourceRequest::Gpu {
                cores: self.gpus_min,
                memory: self.gpu_mem_min,
            }
        } else {
            ResourceRequest::CoresAndMemory {
                cores: self.cores_min,
                memory: self.mem_min,
            }
        }
    }
}
