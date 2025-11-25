
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
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.monitoring.HistoricalFrame;
import com.imageworks.spcue.grpc.monitoring.HistoricalJob;
import com.imageworks.spcue.grpc.monitoring.HistoricalLayer;
import com.imageworks.spcue.grpc.monitoring.LayerMemoryRecord;

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

    /**
     * Query historical job records from the job_history table.
     */
    List<HistoricalJob> getJobHistory(List<String> shows, List<String> users, List<String> shots,
            List<String> jobNameRegex, List<JobState> states, long startTime, long endTime,
            int page, int pageSize, int maxResults);

    /**
     * Query historical frame records from the frame_history table.
     */
    List<HistoricalFrame> getFrameHistory(String jobId, String jobName, List<String> layerNames,
            List<FrameState> states, long startTime, long endTime, int page, int pageSize);

    /**
     * Query historical layer records from the layer_history table.
     */
    List<HistoricalLayer> getLayerHistory(String jobId, String jobName, long startTime,
            long endTime, int page, int pageSize);

    /**
     * Query historical memory usage for a layer type.
     */
    List<LayerMemoryRecord> getLayerMemoryHistory(String layerName, List<String> shows,
            long startTime, long endTime, int maxResults);

}
