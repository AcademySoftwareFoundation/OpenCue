use core::fmt;

use serde::{Deserialize, Serialize};

//=== JobMessage ===
#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct JobMessage {
    pub pk_job: String,
    pub int_priority: i32,
    pub age_days: i32,
}

pub trait Partitionable {
    fn partition_key(&self) -> &str;
}

impl fmt::Display for JobMessage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "job_id: {}", self.pk_job)
    }
}

impl Partitionable for JobMessage {
    fn partition_key(&self) -> &str {
        &self.pk_job
    }
}

//=== DispatchLayer ===
#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct DispatchLayer {
    pub pk_job: String,
    pub pk_facility: String,
    pub str_os: String,
    pub int_cores_min: i32,
    pub int_mem_min: i32,
    pub b_threadable: bool,
    pub int_gpus_min: i32,
    pub int_gpu_mem_min: i32,
    pub str_tags: String,
}

impl DispatchLayer {
    pub fn with_validation(self) -> (Self, DispatchState) {
        // TODO: Implement validation logic based on opencue's Business logic
        if self.int_cores_min <= 0 {
            (self, DispatchState::InvalidCoreMinRequirement)
        } else {
            (self, DispatchState::Valid)
        }
    }
}

pub enum DispatchState {
    Valid,
    InvalidCoreMinRequirement,
}

//=== HostModel ===

#[derive(sqlx::FromRow, Serialize, Deserialize)]
pub struct HostModel {
    pub pk_host: String,
    pub str_name: String,
}
