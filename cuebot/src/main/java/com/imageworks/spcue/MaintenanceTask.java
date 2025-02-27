
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

package com.imageworks.spcue;

/**
 * MaintenanceTasks are stored in the task_lock table. Before a maintenance operation kicks off a
 * lock must be taken out on it so multiple bots don't run the same task.
 */
public enum MaintenanceTask {

    /**
     * Lock the transfer of jobs to the historical table
     */
    LOCK_HISTORICAL_TRANSFER,

    /**
     * Lock the hardware start check
     */
    LOCK_HARDWARE_STATE_CHECK,

    /**
     * Lock the orphaned proc check
     */
    LOCK_ORPHANED_PROC_CHECK,

    /**
     * Lock for task updates
     */
    LOCK_TASK_UPDATE,

    /**
     * Lock the stale checkpoint task.
     */
    LOCK_STALE_CHECKPOINT
}
