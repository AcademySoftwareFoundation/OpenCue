#[cfg(test)]
pub mod helper {
    use rand::prelude::*;
    use uuid::Uuid;

    use crate::job::{Job, JobState};

    pub fn new_job() -> Job {
        Job {
            id: Uuid::new_v4().to_string(),
            state: JobState::Pending.into(),
            name: format!("test_id_{:}", rand::random::<u32>()),
            shot: todo!(),
            show: todo!(),
            user: todo!(),
            group: todo!(),
            facility: todo!(),
            os: todo!(),
            priority: todo!(),
            min_cores: todo!(),
            max_cores: todo!(),
            log_dir: todo!(),
            is_paused: todo!(),
            has_comment: todo!(),
            auto_eat: todo!(),
            start_time: todo!(),
            stop_time: todo!(),
            job_stats: todo!(),
            min_gpus: todo!(),
            max_gpus: todo!(),
            uid_optional: todo!(),
        }
    }
}
