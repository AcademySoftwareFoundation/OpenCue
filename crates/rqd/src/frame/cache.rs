use std::sync::Arc;

use dashmap::DashMap;
use opencue_proto::report::RunningFrameInfo;
use uuid::Uuid;

use super::running_frame::{FrameStats, RunningFrame};

/// Keep track of all frames currently running
/// without losing track of what's running
#[derive(Clone)]
pub struct RunningFrameCache {
    cache: DashMap<Uuid, Arc<RunningFrame>>,
}

impl RunningFrameCache {
    pub fn init() -> Arc<Self> {
        Arc::new(Self {
            cache: DashMap::with_capacity(30),
        })
    }

    /// Clones the contents of the cache into a vector. This method is potentially expensive,
    /// it should only be used when a snapshot of the current state is required
    pub fn into_running_frame_vec(&self) -> Vec<RunningFrameInfo> {
        self.cache
            .iter()
            .map(|running_frame| {
                let frame_stats = running_frame
                    .frame_stats
                    .clone()
                    .unwrap_or(FrameStats::default());
                RunningFrameInfo {
                    resource_id: running_frame.request.resource_id.clone(),
                    job_id: running_frame.request.job_id.to_string(),
                    job_name: running_frame.request.job_name.clone(),
                    frame_id: running_frame.request.frame_id.to_string(),
                    frame_name: running_frame.request.frame_name.clone(),
                    layer_id: running_frame.request.layer_id.to_string(),
                    num_cores: running_frame.request.num_cores as i32,
                    start_time: frame_stats.epoch_start_time as i64,
                    max_rss: frame_stats.max_rss as i64,
                    rss: frame_stats.rss as i64,
                    max_vsize: frame_stats.max_vsize as i64,
                    vsize: frame_stats.vsize as i64,
                    attributes: running_frame.request.attributes.clone(),
                    llu_time: frame_stats.llu_time as i64,
                    num_gpus: running_frame.request.num_gpus as i32,
                    max_used_gpu_memory: frame_stats.max_used_gpu_memory as i64,
                    used_gpu_memory: frame_stats.used_gpu_memory as i64,
                    children: frame_stats.children.clone(),
                }
            })
            .collect()
    }

    pub fn insert_running_frame(
        &self,
        running_frame: Arc<RunningFrame>,
    ) -> Option<Arc<RunningFrame>> {
        self.cache.insert(running_frame.frame_id, running_frame)
    }

    pub fn contains(&self, frame_id: &Uuid) -> bool {
        self.cache.contains_key(frame_id)
    }
}
