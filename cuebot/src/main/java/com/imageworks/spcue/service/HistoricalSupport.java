
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

import org.apache.log4j.Logger;

import com.imageworks.spcue.JobInterface;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.stereotype.Service;

@Service
public class HistoricalSupport {
    private static final Logger logger = Logger.getLogger(HistoricalSupport.class);

    @Autowired
    private HistoricalManager historicalManager;

    public void archiveHistoricalJobData() {
        logger.info("running historical job data transfer");
        List<JobInterface> jobs = historicalManager.getFinishedJobs();
        for (JobInterface j: jobs) {
            logger.info("transfering job " + j.getId() + "/" + j.getName());
            try {
                historicalManager.transferJob(j);
            } catch (Exception e) {
                logger.warn("failed to transfer job, " + e);
            }
        }
    }

    public HistoricalManager getHistoricalManager() {
        return historicalManager;
    }

    public void setHistoricalManager(HistoricalManager historicalManager) {
        this.historicalManager = historicalManager;
    }
}

