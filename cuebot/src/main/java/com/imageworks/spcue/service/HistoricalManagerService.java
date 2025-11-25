
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

import java.util.ArrayList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.HistoricalJobTransferException;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.dao.HistoricalDao;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.monitoring.HistoricalFrame;
import com.imageworks.spcue.grpc.monitoring.HistoricalJob;
import com.imageworks.spcue.grpc.monitoring.HistoricalLayer;
import com.imageworks.spcue.grpc.monitoring.LayerMemoryRecord;

@Transactional
public class HistoricalManagerService implements HistoricalManager {

    private HistoricalDao historicalDao;

    @Autowired
    private Environment env;

    @Transactional(readOnly = true, isolation = Isolation.SERIALIZABLE)
    public List<JobInterface> getFinishedJobs() {
        return historicalDao.getFinishedJobs(
                env.getRequiredProperty("history.archive_jobs_cutoff_hours", Integer.class));
    }

    @Transactional
    public void transferJob(JobInterface job) {
        try {
            historicalDao.transferJob(job);
        } catch (Exception e) {
            throw new HistoricalJobTransferException(
                    "failed to transfer job " + job.getName() + " to historical table");
        }
    }

    @Override
    @Transactional(readOnly = true)
    public List<HistoricalJob> getJobHistory(List<String> shows, List<String> users,
            List<String> shots, List<String> jobNameRegex, List<JobState> states, long startTime,
            long endTime, int page, int pageSize, int maxResults) {
        return historicalDao.getJobHistory(shows, users, shots, jobNameRegex, states, startTime,
                endTime, page, pageSize, maxResults);
    }

    @Override
    @Transactional(readOnly = true)
    public List<HistoricalFrame> getFrameHistory(String jobId, String jobName,
            List<String> layerNames, List<FrameState> states, long startTime, long endTime,
            int page, int pageSize) {
        return historicalDao.getFrameHistory(jobId, jobName, layerNames, states, startTime, endTime,
                page, pageSize);
    }

    @Override
    @Transactional(readOnly = true)
    public List<HistoricalLayer> getLayerHistory(String jobId, String jobName, long startTime,
            long endTime, int page, int pageSize) {
        return historicalDao.getLayerHistory(jobId, jobName, startTime, endTime, page, pageSize);
    }

    @Override
    @Transactional(readOnly = true)
    public List<LayerMemoryRecord> getLayerMemoryHistory(String layerName, List<String> shows,
            long startTime, long endTime, int maxResults) {
        return historicalDao.getLayerMemoryHistory(layerName, shows, startTime, endTime,
                maxResults);
    }

    public HistoricalDao getHistoricalDao() {
        return historicalDao;
    }

    public void setHistoricalDao(HistoricalDao historicalDao) {
        this.historicalDao = historicalDao;
    }

}
