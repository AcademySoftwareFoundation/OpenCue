
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

package com.imageworks.spcue.dao;

import com.imageworks.spcue.MaintenanceTask;

/**
 * the MaintenanceDao is for queries to run at a specific intervals
 *
 * @category DAO
 */
public interface MaintenanceDao {

    /**
     * Set hosts to the down state that have not pinged in within 5 minutes and return the number
     * hosts that failed the check.
     *
     * @return int
     */
    int setUpHostsToDown();

    /**
     * Lock specified task
     *
     * @param task
     * @return
     */
    boolean lockTask(MaintenanceTask task);

    /**
     * Locks a test for the specified number of minutes. No other thread will execute this task,
     * even if the task is unlocked for N amount of time.
     *
     * @param task
     * @param minutes
     * @return
     */
    public boolean lockTask(MaintenanceTask task, int minutes);

    /**
     * Unlock specified task
     *
     * @param task
     */
    void unlockTask(MaintenanceTask task);

}
