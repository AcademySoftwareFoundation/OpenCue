use core::fmt;

use host::Host;
use job::{Frame, Job};
use report::CoreDetail;
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
            .map(|run_frame| to_uuid(&run_frame.frame_id))
            .flatten()
            .unwrap_or(Uuid::nil())
            .clone()
    }
}

impl WithUuid for rqd::RunningFrameStatusRequest {
    fn uuid(&self) -> Uuid {
        self.run_frame
            .as_ref()
            .map(|run_frame| to_uuid(&run_frame.frame_id))
            .flatten()
            .unwrap_or(Uuid::nil())
            .clone()
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

impl CoreDetail {
    /// Update CoreDetail by reserving a number of cores
    ///
    /// # Arguments
    ///
    /// * `core_count_with_multiplier` - Number of cores to reserve multiplied by core_multiplier
    ///
    /// # Returns
    ///
    /// * `Ok(())` if cores were reserved successfully
    /// * `Err(String)` if trying to reserve more cores than are available
    pub fn reserve(&mut self, core_count_with_multiplier: usize) -> Result<(), String> {
        if self.idle_cores - (core_count_with_multiplier as i32) < 0 {
            Err(format!(
                "Tried to reserve {} out of {} cores available",
                core_count_with_multiplier, self.idle_cores,
            ))
        } else {
            self.idle_cores -= core_count_with_multiplier as i32;
            self.booked_cores += core_count_with_multiplier as i32;
            Ok(())
        }
    }

    /// Update CoreDetail by releasing a number of previously reserved cores
    ///
    /// # Arguments
    ///
    /// * `core_count_with_multiplier` - The number of cores to release multiplied by core_multiplier
    ///
    /// # Returns
    ///
    /// * `Ok(())` if cores were released successfully
    /// * `Err(String)` if trying to release more cores than are currently reserved
    pub fn release(&mut self, core_count_with_multiplier: u32) -> Result<(), String> {
        if self.booked_cores < core_count_with_multiplier as i32 {
            Err(format!(
                "Tried to release {} out of {} cores reserved",
                core_count_with_multiplier, self.booked_cores,
            ))
        } else {
            self.idle_cores += core_count_with_multiplier as i32;
            self.booked_cores -= core_count_with_multiplier as i32;
            Ok(())
        }
    }

    /// Update CoreDetail by locking a specified number of cores. If the amount requested is
    /// not available, the maximum available will be reserved.
    ///
    /// # Arguments
    ///
    /// * `count_with_multiplier` - Number of cores to lock multiplied by core_multiplier
    ///
    /// # Returns
    ///
    /// * `u32` - The actual number of cores that were locked (may be less than requested if not enough are available)
    pub fn lock_cores(&mut self, count_with_multiplier: u32) -> u32 {
        let amount_not_locked = self.total_cores - self.locked_cores;
        let amount_to_lock = std::cmp::min(amount_not_locked, count_with_multiplier as i32);

        if amount_to_lock > 0 {
            self.locked_cores += amount_to_lock;
            self.idle_cores -= std::cmp::min(amount_to_lock, self.idle_cores)
        }

        amount_to_lock as u32
    }

    /// Update CoreDetail by locking all available cores
    ///
    /// This will set idle_cores to 0 and locked_cores to total_cores
    pub fn lock_all_cores(&mut self) {
        self.idle_cores = 0;
        self.locked_cores = self.total_cores;
    }

    /// Update CoreDetail by unlocking a specified number of cores that were previously locked.
    ///
    /// # Arguments
    ///
    /// * `count_with_multiplier` - Number of cores to unlock multiplied by core_multiplier
    ///
    /// # Returns
    ///
    /// * `u32` - The actual number of cores that were unlocked (may be less than requested if fewer cores are locked)
    pub fn unlock_cores(&mut self, count_with_multiplier: u32) -> u32 {
        let amount_to_unlock = std::cmp::min(count_with_multiplier as i32, self.locked_cores);

        if amount_to_unlock > 0 {
            self.locked_cores -= amount_to_unlock;
            self.idle_cores += amount_to_unlock;
        }
        amount_to_unlock as u32
    }

    /// Update CoreDetail by unlocking all locked cores
    ///
    /// This will unlock all locked cores and add them to idle_cores
    pub fn unlock_all_cores(&mut self) {
        if self.locked_cores > 0 {
            self.idle_cores += self.locked_cores;
            self.locked_cores = 0;
        }
    }
}
