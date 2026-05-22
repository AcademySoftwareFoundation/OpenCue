
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.service;

import com.imageworks.spcue.VirtualProc;

/**
 * Publishes per-release accounting deltas to Redis for scheduler-managed shows. Implementations may
 * be no-op (when {@code accounting.redis.enabled=false}) or Lettuce-backed.
 *
 * See the Redis-Backed Accounting Reference at
 * {@code docs/_docs/developer-guide/redis-accounting.md} for the protocol. The decrement is applied
 * atomically across {@code acct:sub:*}, {@code acct:folder:*}, {@code acct:job:*},
 * {@code acct:layer:*}, {@code acct:point:*} and bumps {@code acct:seq}.
 */
public interface AccountingRedisPublisher {

    /**
     * Publish a release delta. Must be invoked only after the surrounding Postgres transaction has
     * committed (typically from {@code TransactionSynchronization.afterCommit}).
     *
     * @param proc the released VirtualProc; provides showId, jobId, layerId, allocationId,
     *        folderId, deptId, coresReserved, gpusReserved. Callers must ensure folderId and
     *        deptId are populated (production hydration paths do this via {@code
     *        ProcDaoJdbc.VIRTUAL_PROC_MAPPER}).
     */
    void publishRelease(VirtualProc proc);

    /** True when this publisher actually writes to Redis. */
    boolean isEnabled();
}
