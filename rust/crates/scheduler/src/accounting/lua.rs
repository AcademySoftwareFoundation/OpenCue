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

// TODO: per-booking idempotency token if duplicate-booking rate becomes material (design §5).

/// Hot-path booking script. KEYS / ARGV layout:
///
/// ```text
/// KEYS[1] = acct:sub:{show_id}:{alloc_id}
/// KEYS[2] = acct:folder:{folder_id}
/// KEYS[3] = acct:job:{job_id}
/// KEYS[4] = acct:layer:{layer_id}
/// KEYS[5] = acct:point:{dept_id}:{show_id}
/// KEYS[6] = acct:seq
/// ARGV[1] = core_delta  (signed int as string)
/// ARGV[2] = gpu_delta   (signed int as string)
/// ARGV[3] = force       ("0" to enforce limits, "1" to bypass)
/// ```
///
/// Return shape:
/// - `{1, new_seq}`                              on success
/// - `{0, table_name, current_value, limit}`     on limit-exceeded (force=0 only)
///
/// Cap semantics:
/// - **Subscription burst** is enforced unconditionally. `int_burst=0` means
///   "reject all bookings", matching Cuebot's `s.int_cores + ? > s.int_burst`
///   check in `SubscriptionDaoJdbc.IS_SHOW_OVER_BURST`. The bootstrap reseed
///   populates burst before the scheduler accepts work, so unconfigured
///   subscriptions cannot dispatch.
/// - **Folder / job `int_max_cores`** retain the `> 0` guard. Cuebot's convention
///   uses `-1` (the schema default for `folder_resource.int_max_cores`) as the
///   "unlimited" sentinel, and 0 is not a meaningful configured value for these
///   caps in practice.
pub const BOOK_OR_FORCE: &str = r#"
local core_d = tonumber(ARGV[1])
local gpu_d  = tonumber(ARGV[2])
local force  = ARGV[3] == "1"

if not force and core_d > 0 then
  local cur_sub   = tonumber(redis.call('HGET', KEYS[1], 'int_cores') or "0")
  local sub_burst = tonumber(redis.call('HGET', KEYS[1], 'burst')     or "0")
  if (cur_sub + core_d) > sub_burst then
    return {0, "subscription", cur_sub, sub_burst}
  end

  local cur_folder = tonumber(redis.call('HGET', KEYS[2], 'int_cores')     or "0")
  local folder_max = tonumber(redis.call('HGET', KEYS[2], 'int_max_cores') or "0")
  if folder_max > 0 and (cur_folder + core_d) > folder_max then
    return {0, "folder", cur_folder, folder_max}
  end

  local cur_job = tonumber(redis.call('HGET', KEYS[3], 'int_cores')     or "0")
  local job_max = tonumber(redis.call('HGET', KEYS[3], 'int_max_cores') or "0")
  if job_max > 0 and (cur_job + core_d) > job_max then
    return {0, "job", cur_job, job_max}
  end
end

redis.call('HINCRBY', KEYS[1], 'int_cores', core_d)
redis.call('HINCRBY', KEYS[1], 'int_gpus',  gpu_d)
redis.call('HINCRBY', KEYS[2], 'int_cores', core_d)
redis.call('HINCRBY', KEYS[2], 'int_gpus',  gpu_d)
redis.call('HINCRBY', KEYS[3], 'int_cores', core_d)
redis.call('HINCRBY', KEYS[3], 'int_gpus',  gpu_d)
redis.call('HINCRBY', KEYS[4], 'int_cores', core_d)
redis.call('HINCRBY', KEYS[4], 'int_gpus',  gpu_d)
redis.call('HINCRBY', KEYS[5], 'int_cores', core_d)
redis.call('HINCRBY', KEYS[5], 'int_gpus',  gpu_d)
-- `acct:seq` is bumped on every mutation, including force-mode rollbacks (design
-- §2.4 - all mutations bump seq so concurrent reseed CAS attempts notice). Trade-off:
-- during a wave of force-rollbacks (e.g. flaky RQD launch failures) the reseed CAS
-- budget can be exhausted, causing the recompute cycle to skip. Acceptable per
-- design - hot-path writes are keeping Redis fresh; recompute is reconciliation,
-- not primary sync.
return {1, redis.call('INCR', KEYS[6])}
"#;

/// Reseed write under the `acct:seq` CAS guard. Used by both the recompute loop
/// and the limit reseed loop. ARGV-encoded ops (rather than KEYS) because Redis
/// Cluster is out of scope (single-node per design §2.4) and ARGV avoids the
/// 8000-key EVALSHA limit when reseeding thousands of shows in one shot.
///
/// ```text
/// KEYS[1] = acct:seq
/// ARGV[1] = seq_before (string-encoded i64)
/// ARGV[2] = n_ops      (string-encoded i64)
/// For i in 1..=n_ops:
///   ARGV[2 + 3*(i-1) + 1] = key
///   ARGV[2 + 3*(i-1) + 2] = field
///   ARGV[2 + 3*(i-1) + 3] = value
/// ```
///
/// Returns `1` on success, `0` on CAS miss (caller recomputes snapshot and retries).
/// Does NOT bump `acct:seq` - reseed is reconciliation, not mutation; bumping would
/// invalidate any concurrent CAS attempts.
pub const RESEED_CAS: &str = r#"
local cur = redis.call('GET', KEYS[1]) or "0"
if cur ~= ARGV[1] then return 0 end

local n = tonumber(ARGV[2])
for i = 0, n - 1 do
  local base = 3 + i * 3
  redis.call('HSET', ARGV[base], ARGV[base + 1], ARGV[base + 2])
end
return 1
"#;
