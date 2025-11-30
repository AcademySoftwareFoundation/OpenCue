
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

import java.util.List;

import com.imageworks.spcue.JobInterface;

public interface HistoricalDao {

    /**
     * Return all jobs that have been finished longer than the specified cut off in hours.
     *
     * @param cutoffHours
     * @return
     */
    List<JobInterface> getFinishedJobs(int cutoffHours);

    /**
     * Transfer a job from the live tables to the historical tables.
     *
     * @param job
     */
    void transferJob(JobInterface job);

}
