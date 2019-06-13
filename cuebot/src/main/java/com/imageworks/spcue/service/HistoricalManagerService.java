
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */



package com.imageworks.spcue.service;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.HistoricalJobTransferException;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.dao.HistoricalDao;

@Service
@Transactional
public class HistoricalManagerService implements HistoricalManager {

    @Autowired
    private HistoricalDao historicalDao;

    public static final int ARCHIVE_JOBS_CUTOFF_HOURS = 72 ;


    @Transactional(readOnly=true, isolation=Isolation.SERIALIZABLE)
    public List<JobInterface> getFinishedJobs() {
        return historicalDao.getFinishedJobs(ARCHIVE_JOBS_CUTOFF_HOURS);
    }

    @Transactional
    public void transferJob(JobInterface job) {
        try {
            historicalDao.transferJob(job);
        } catch (Exception e) {
            throw new HistoricalJobTransferException("failed to transfer job " +
                    job.getName() + " to historical table");
        }
    }

    public HistoricalDao getHistoricalDao() {
        return historicalDao;
    }

    public void setHistoricalDao(HistoricalDao historicalDao) {
        this.historicalDao = historicalDao;
    }


}

