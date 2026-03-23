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

use host::Host;
use job::{Frame, Job};
use rqd::RunFrame;
use uuid::Uuid;

mod comment;
mod criterion;
mod cue;
mod department;
mod depend;
pub mod facility;
#[allow(clippy::all, clippy::pedantic, clippy::nursery)]
mod filter;
pub mod host;
#[allow(clippy::all, clippy::pedantic, clippy::nursery)]
pub mod job;
mod limit;
#[allow(clippy::all, clippy::pedantic, clippy::nursery)]
mod render_partition;
pub mod report;
pub mod rqd;
mod service;
pub mod show;
mod subscription;
mod task;

pub trait WithUuid {
    fn uuid(&self) -> Uuid;
}

impl WithUuid for job::Job {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.id).unwrap_or_default()
    }
}

impl WithUuid for job::Layer {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.id).unwrap_or_default()
    }
}

impl WithUuid for facility::Allocation {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.id).unwrap_or_default()
    }
}

impl WithUuid for show::Show {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.id).unwrap_or_default()
    }
}

impl WithUuid for report::RunningFrameInfo {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.frame_id).unwrap_or(Uuid::nil())
    }
}

impl WithUuid for rqd::RqdStaticGetRunningFrameStatusRequest {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.frame_id).unwrap_or(Uuid::nil())
    }
}

impl WithUuid for rqd::RqdStaticKillRunningFrameRequest {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.frame_id).unwrap_or(Uuid::nil())
    }
}

impl WithUuid for rqd::RunningFrameKillRequest {
    fn uuid(&self) -> Uuid {
        self.run_frame
            .as_ref()
            .and_then(|run_frame| to_uuid(&run_frame.frame_id))
            .unwrap_or(Uuid::nil())
    }
}

impl WithUuid for rqd::RunningFrameStatusRequest {
    fn uuid(&self) -> Uuid {
        self.run_frame
            .as_ref()
            .and_then(|run_frame| to_uuid(&run_frame.frame_id))
            .unwrap_or(Uuid::nil())
    }
}

pub fn to_uuid(stringified_id_from_protobuf: &str) -> Option<Uuid> {
    Uuid::parse_str(stringified_id_from_protobuf).ok()
}

impl RunFrame {
    pub fn job_id(&self) -> Uuid {
        to_uuid(&self.job_id).unwrap_or(Uuid::nil())
    }
    pub fn frame_id(&self) -> Uuid {
        to_uuid(&self.frame_id).unwrap_or(Uuid::nil())
    }
    pub fn layer_id(&self) -> Uuid {
        to_uuid(&self.layer_id).unwrap_or(Uuid::nil())
    }
    pub fn resource_id(&self) -> Uuid {
        to_uuid(&self.resource_id).unwrap_or(Uuid::nil())
    }
}

impl fmt::Display for Frame {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}/({})", self.name, self.id)
    }
}

impl fmt::Display for Job {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}/({})", self.name, self.id)
    }
}

impl fmt::Display for Host {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}/({})", self.name, self.id)
    }
}
