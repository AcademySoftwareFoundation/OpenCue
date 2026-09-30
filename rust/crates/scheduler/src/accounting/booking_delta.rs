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

/// A single booking-or-release applied atomically to the five Redis accounting hashes.
///
/// Field shape matches the Cuebot release publisher (`LettuceAccountingRedisPublisher`),
/// so both sides of the booking lifecycle converge on the same `acct:*` keys.
#[derive(Debug, Clone)]
pub struct BookingDelta {
    pub show_id: Uuid,
    pub alloc_id: Uuid,
    pub folder_id: Uuid,
    pub job_id: Uuid,
    pub layer_id: Uuid,
    pub dept_id: Uuid,
    pub core_delta: i64,
    pub gpu_delta: i32,
}

impl BookingDelta {
    /// Returns the same delta with every numeric component negated.
    pub fn negated(&self) -> BookingDelta {
        BookingDelta {
            show_id: self.show_id,
            alloc_id: self.alloc_id,
            folder_id: self.folder_id,
            job_id: self.job_id,
            layer_id: self.layer_id,
            dept_id: self.dept_id,
            core_delta: -self.core_delta,
            gpu_delta: -self.gpu_delta,
        }
    }

    pub fn sub_key(&self) -> String {
        format!("acct:sub:{}:{}", self.show_id, self.alloc_id)
    }

    pub fn folder_key(&self) -> String {
        format!("acct:folder:{}", self.folder_id)
    }

    pub fn job_key(&self) -> String {
        format!("acct:job:{}", self.job_id)
    }

    pub fn layer_key(&self) -> String {
        format!("acct:layer:{}", self.layer_id)
    }

    pub fn point_key(&self) -> String {
        format!("acct:point:{}:{}", self.dept_id, self.show_id)
    }
}

pub const SEQ_KEY: &str = "acct:seq";

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> BookingDelta {
        BookingDelta {
            show_id: Uuid::nil(),
            alloc_id: Uuid::nil(),
            folder_id: Uuid::nil(),
            job_id: Uuid::nil(),
            layer_id: Uuid::nil(),
            dept_id: Uuid::nil(),
            core_delta: 100,
            gpu_delta: 1,
        }
    }

    #[test]
    fn negated_inverts_only_numeric_fields() {
        let d = fixture();
        let n = d.negated();
        assert_eq!(n.core_delta, -100);
        assert_eq!(n.gpu_delta, -1);
        assert_eq!(n.show_id, d.show_id);
    }

    #[test]
    fn keys_match_cuebot_publisher_format() {
        // Format must match LettuceAccountingRedisPublisher.evalRelease - both sides
        // mutate the same hashes.
        let d = fixture();
        assert_eq!(
            d.sub_key(),
            "acct:sub:00000000-0000-0000-0000-000000000000:00000000-0000-0000-0000-000000000000"
        );
        assert_eq!(
            d.folder_key(),
            "acct:folder:00000000-0000-0000-0000-000000000000"
        );
        assert_eq!(d.job_key(), "acct:job:00000000-0000-0000-0000-000000000000");
        assert_eq!(
            d.layer_key(),
            "acct:layer:00000000-0000-0000-0000-000000000000"
        );
        assert_eq!(
            d.point_key(),
            "acct:point:00000000-0000-0000-0000-000000000000:00000000-0000-0000-0000-000000000000"
        );
    }
}
