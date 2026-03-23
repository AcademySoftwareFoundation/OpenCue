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

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::{cluster::Cluster, models::fmt_uuid};

/// Basic information to collect a job on the database for dispatching
#[derive(Serialize, Deserialize, Clone)]
pub struct DispatchJob {
    pub id: Uuid,
    pub int_priority: i32,
    pub source_cluster: Cluster,
}

impl fmt::Display for DispatchJob {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", fmt_uuid(&self.id))
    }
}
