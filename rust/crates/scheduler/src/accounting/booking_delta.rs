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

/// A single booking-or-release applied to the in-memory accounting store. Carries only the
/// three enforced vertices (subscription/folder/job); layer and point are intentionally not
/// tracked because nothing reads or enforces them.
///
/// `core_delta`/`gpu_delta` are signed: positive on a booking, negative on a release.
/// Rollback and release are expressed as the store subtracting/adding these directly, so
/// no separate negation helper is needed.
#[derive(Debug, Clone)]
pub struct BookingDelta {
    pub show_id: Uuid,
    pub alloc_id: Uuid,
    pub folder_id: Uuid,
    pub job_id: Uuid,
    pub core_delta: i64,
    pub gpu_delta: i32,
}
