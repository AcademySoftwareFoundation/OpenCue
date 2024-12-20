use core::fmt;
use std::path::Display;

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
mod filter;
pub mod host;
pub mod job;
mod limit;
mod render_partition;
pub mod report;
pub mod rqd;
mod service;
pub mod show;
mod subscription;
mod task;
pub mod test_utils;

pub trait WithUuid {
    fn uuid(&self) -> Uuid;
}

impl WithUuid for job::Job {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.id).expect("Failed to convert Uuid, protocol version is incompatible")
    }
}

impl WithUuid for job::Layer {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.id).expect("Failed to convert Uuid, protocol version is incompatible")
    }
}

impl WithUuid for facility::Allocation {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.id).expect("Failed to convert Uuid, protocol version is incompatible")
    }
}

impl WithUuid for show::Show {
    fn uuid(&self) -> Uuid {
        to_uuid(&self.id).expect("Failed to convert Uuid, protocol version is incompatible")
    }
}

pub fn to_uuid(stringified_id_from_protobuf: &str) -> Option<Uuid> {
    Uuid::parse_str(stringified_id_from_protobuf).ok()
}

impl From<Frame> for RunFrame {
    fn from(value: Frame) -> Self {
        RunFrame {
            resource_id: todo!(),
            job_id: todo!(),
            job_name: todo!(),
            frame_id: todo!(),
            frame_name: todo!(),
            layer_id: todo!(),
            command: todo!(),
            user_name: todo!(),
            log_dir: todo!(),
            show: todo!(),
            shot: todo!(),
            job_temp_dir: todo!(),
            frame_temp_dir: todo!(),
            log_file: todo!(),
            log_dir_file: todo!(),
            start_time: todo!(),
            num_cores: todo!(),
            gid: todo!(),
            ignore_nimby: todo!(),
            environment: todo!(),
            attributes: todo!(),
            num_gpus: todo!(),
            children: todo!(),
            uid_optional: todo!(),
        }
    }
}

impl fmt::Display for Frame {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:}/({:})", self.name, self.id)
    }
}

impl fmt::Display for Job {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:}/({:})", self.name, self.id)
    }
}

impl fmt::Display for Host {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:}/({:})", self.name, self.id)
    }
}
