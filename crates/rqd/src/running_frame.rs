use std::sync::Arc;

use dashmap::DashMap;
use opencue_proto::report::RunningFrameInfo;

/// Wrapper around protobuf message RunningFrameInfo
#[derive(Clone, Copy)]
pub struct RunningFrame {}

impl From<RunningFrameInfo> for RunningFrame {
    fn from(frame_info: RunningFrameInfo) -> Self {
        todo!()
    }
}

impl From<RunningFrame> for RunningFrameInfo {
    fn from(frame_info: RunningFrame) -> Self {
        todo!()
    }
}

/// Keep track of all frames currently running
/// TODO: Implement recovery strategy to allow restarting rqd
/// without losing track of what's running
#[derive(Clone)]
pub struct RunningFrameCache {
    cache: DashMap<String, RunningFrame>,
}

impl RunningFrameCache {
    pub fn init() -> Arc<Self> {
        Arc::new(Self {
            cache: DashMap::with_capacity(30),
        })
    }

    pub fn into_running_frame_vec(&self) -> Vec<RunningFrameInfo> {
        self.cache
            .clone()
            .into_iter()
            .map(|(_, running_frame)| running_frame.into())
            .collect()
    }
}
