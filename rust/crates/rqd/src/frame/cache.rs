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

use std::sync::Arc;

use dashmap::DashMap;
use opencue_proto::report::RunningFrameInfo;
use uuid::Uuid;

use super::running_frame::RunningFrame;

/// Keep track of all frames currently running
/// without losing track of what's running
/// Key: frame_id
pub struct RunningFrameCache {
    cache: DashMap<Uuid, Arc<RunningFrame>>,
}

// Give Caller access to all methods on its inner User
impl std::ops::Deref for RunningFrameCache {
    type Target = DashMap<Uuid, Arc<RunningFrame>>;

    fn deref(&self) -> &Self::Target {
        &self.cache
    }
}

impl RunningFrameCache {
    pub fn init() -> Arc<Self> {
        Arc::new(Self {
            cache: DashMap::with_capacity(30),
        })
    }

    /// Clones the contents of the cache into a vector. This method is potentially expensive,
    /// it should only be used when a snapshot of the current state is required
    pub fn clone_to_running_frame_vec(&self) -> Vec<RunningFrameInfo> {
        self.cache
            .iter()
            .map(|running_frame| running_frame.clone_into_running_frame_info())
            .collect()
    }

    pub fn all_running_frame_ids(&self) -> Vec<Uuid> {
        self.cache.iter().map(|rf| rf.frame_id).collect()
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

    pub fn retain(&self, f: impl FnMut(&Uuid, &mut Arc<RunningFrame>) -> bool) {
        self.cache.retain(f);
    }
}
