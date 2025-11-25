
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
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.monitoring.HistoricalFrame;
import com.imageworks.spcue.grpc.monitoring.HistoricalJob;
import com.imageworks.spcue.grpc.monitoring.HistoricalLayer;
import com.imageworks.spcue.grpc.monitoring.LayerMemoryRecord;

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
     * Query historical job records with optional filters.
     *
     * @param shows List of show names to filter by
     * @param users List of usernames to filter by
     * @param shots List of shot names to filter by
     * @param jobNameRegex Regular expression patterns for job names
     * @param states List of job states to filter by
     * @param startTime Start time filter (Unix epoch milliseconds)
     * @param endTime End time filter (Unix epoch milliseconds)
     * @param page Page number for pagination
     * @param pageSize Number of results per page
     * @param maxResults Maximum total results
     * @return List of HistoricalJob records
     */
    List<HistoricalJob> getJobHistory(List<String> shows, List<String> users, List<String> shots,
            List<String> jobNameRegex, List<JobState> states, long startTime, long endTime,
            int page, int pageSize, int maxResults);

    /**
     * Query historical frame records for a specific job.
     *
     * @param jobId Job ID to query
     * @param jobName Job name to query
     * @param layerNames List of layer names to filter by
     * @param states List of frame states to filter by
     * @param startTime Start time filter (Unix epoch milliseconds)
     * @param endTime End time filter (Unix epoch milliseconds)
     * @param page Page number for pagination
     * @param pageSize Number of results per page
     * @return List of HistoricalFrame records
     */
    List<HistoricalFrame> getFrameHistory(String jobId, String jobName, List<String> layerNames,
            List<FrameState> states, long startTime, long endTime, int page, int pageSize);

    /**
     * Query historical layer records for a specific job.
     *
     * @param jobId Job ID to query
     * @param jobName Job name to query
     * @param startTime Start time filter (Unix epoch milliseconds)
     * @param endTime End time filter (Unix epoch milliseconds)
     * @param page Page number for pagination
     * @param pageSize Number of results per page
     * @return List of HistoricalLayer records
     */
    List<HistoricalLayer> getLayerHistory(String jobId, String jobName, long startTime,
            long endTime, int page, int pageSize);

    /**
     * Query historical memory usage for a specific layer type. This is useful for memory prediction
     * based on historical data.
     *
     * @param layerName Layer name pattern to query
     * @param shows List of show names to filter by
     * @param startTime Start time filter (Unix epoch milliseconds)
     * @param endTime End time filter (Unix epoch milliseconds)
     * @param maxResults Maximum number of records to return
     * @return List of LayerMemoryRecord records
     */
    List<LayerMemoryRecord> getLayerMemoryHistory(String layerName, List<String> shows,
            long startTime, long endTime, int maxResults);

}
