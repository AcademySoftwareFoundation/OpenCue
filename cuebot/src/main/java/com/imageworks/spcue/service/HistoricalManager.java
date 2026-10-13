
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

import java.util.List;

import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.dao.HistoricalDao.FrameHistoryBacklog;
import com.imageworks.spcue.dao.HistoricalDao.FrameHistoryDrain;

public interface HistoricalManager {

    /**
     * Returns a list of jobs ready to be archived.
     *
     * @return List<Job>
     */
    List<JobInterface> getFinishedJobs();

    /**
     * Transfers data from the live to the historical tables.
     *
     * @param job
     */
    void transferJob(JobInterface job);

    /**
     * Applies one batch of queued frame history events to frame_history in its own transaction.
     *
     * @param limit maximum number of events to drain
     * @param safe apply each event in its own subtransaction and drop the ones that fail
     * @return the drain outcome
     */
    FrameHistoryDrain drainFrameHistory(int limit, boolean safe);

    /**
     * Returns the approximate size and age of the frame history queue.
     *
     * @return the queue backlog
     */
    FrameHistoryBacklog getFrameHistoryBacklog();

}
