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

use uuid::Uuid;

pub mod linux;
pub mod machine;
#[cfg(feature = "nimby")]
pub mod nimby;
mod oom;
mod reservation;

#[cfg(target_os = "macos")]
pub mod macos;
pub mod manager;

pub type ResourceId = Uuid;
pub type CoreId = u32;
pub type PhysId = u32;
pub type ThreadId = u32;

pub use oom::OOM_REASON_MSG;
