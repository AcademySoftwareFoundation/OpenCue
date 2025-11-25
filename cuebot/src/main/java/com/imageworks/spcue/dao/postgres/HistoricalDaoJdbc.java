
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

package com.imageworks.spcue.dao.postgres;

import java.util.Collections;
import java.util.List;

import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.dao.HistoricalDao;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.monitoring.HistoricalFrame;
import com.imageworks.spcue.grpc.monitoring.HistoricalJob;
import com.imageworks.spcue.grpc.monitoring.HistoricalLayer;
import com.imageworks.spcue.grpc.monitoring.LayerMemoryRecord;

public class HistoricalDaoJdbc extends JdbcDaoSupport implements HistoricalDao {

    private static final String GET_FINISHED_JOBS = JobDaoJdbc.GET_JOB + "WHERE "
            + "job.str_state = ? " + "AND " + "current_timestamp - job.ts_stopped > ";

    public List<JobInterface> getFinishedJobs(int cutoffHours) {
        String interval = "interval '" + cutoffHours + "' hour";
        return getJdbcTemplate().query(GET_FINISHED_JOBS + interval, JobDaoJdbc.JOB_MAPPER,
                JobState.FINISHED.toString());
    }

    public void transferJob(JobInterface job) {
        /**
         * All of the historical transfer happens inside of triggers
         */
        getJdbcTemplate().update("DELETE FROM job WHERE pk_job=?", job.getJobId());
    }

    @Override
    public List<HistoricalJob> getJobHistory(List<String> shows, List<String> users,
            List<String> shots, List<String> jobNameRegex, List<JobState> states, long startTime,
            long endTime, int page, int pageSize, int maxResults) {
        // Historical queries are handled via Elasticsearch when enabled
        return Collections.emptyList();
    }

    @Override
    public List<HistoricalFrame> getFrameHistory(String jobId, String jobName,
            List<String> layerNames, List<FrameState> states, long startTime, long endTime,
            int page, int pageSize) {
        // Historical queries are handled via Elasticsearch when enabled
        return Collections.emptyList();
    }

    @Override
    public List<HistoricalLayer> getLayerHistory(String jobId, String jobName, long startTime,
            long endTime, int page, int pageSize) {
        // Historical queries are handled via Elasticsearch when enabled
        return Collections.emptyList();
    }

    @Override
    public List<LayerMemoryRecord> getLayerMemoryHistory(String layerName, List<String> shows,
            long startTime, long endTime, int maxResults) {
        // Historical queries are handled via Elasticsearch when enabled
        return Collections.emptyList();
    }
}
