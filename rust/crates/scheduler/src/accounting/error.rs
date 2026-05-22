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

use thiserror::Error;

/// Errors from the Redis-backed accounting service.
///
/// The booking hot path (`apply_booking`) can fail in three meaningful ways:
/// - `LimitExceeded`: the Lua check rejected the booking because a hard cap
///   (subscription burst, folder/job `int_max_cores`, or folder/job
///   `int_max_gpus`) would be exceeded. Carries the offending table, the current
///   counter value, and the limit - used to build user-facing error messages.
/// - `Unavailable`: Redis is unreachable or in a state where bookings can't safely
///   proceed (empty after a restart, before bootstrap reseed has run). The dispatcher
///   maps this to an idle-cycle equivalent - design §4.3 row 5.
/// - `Unexpected`: anything else (Lua syntax error, malformed return, etc.). Surfaced
///   for diagnostics; same dispatch consequence as `Unavailable`.
#[derive(Error, Debug)]
pub enum AccountingError {
    #[error("limit exceeded on {table}: current={current} limit={limit}")]
    LimitExceeded {
        table: String,
        current: i64,
        limit: i64,
    },

    #[error("redis unavailable: {0}")]
    Unavailable(String),

    /// Surfaced via `DispatchVirtualProcError::AccountingUnexpected` when a hot-path
    /// booking ever needs to be CAS-guarded. Currently only the reseed loops use CAS
    /// (and they swallow contention with a warn-log per design §2.4), so this is
    /// reachable code for future expansion rather than the live path today.
    #[allow(dead_code)]
    #[error("CAS contention exceeded retry budget; reseed cycle skipped")]
    CasContentionExceeded,

    #[error("accounting redis error: {0}")]
    Unexpected(String),
}

impl From<redis::RedisError> for AccountingError {
    fn from(err: redis::RedisError) -> Self {
        if err.is_connection_refusal() || err.is_io_error() || err.is_timeout() {
            AccountingError::Unavailable(err.to_string())
        } else {
            AccountingError::Unexpected(err.to_string())
        }
    }
}
