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
