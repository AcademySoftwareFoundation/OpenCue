
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



package com.imageworks.spcue.dao.postgres;

import java.util.List;

import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.Job;
import com.imageworks.spcue.CueIce.JobState;
import com.imageworks.spcue.dao.HistoricalDao;

public class HistoricalDaoJdbc extends JdbcDaoSupport implements HistoricalDao {

    private static final String GET_FINISHED_JOBS =
        JobDaoJdbc.GET_JOB +
        "WHERE " +
            "job.str_state=? " +
         "AND " +
             "systimestamp - job.ts_stopped > ";

    public List<Job> getFinishedJobs(int cutoffHours) {
        String interval = "interval '" + cutoffHours + "' hour";
        return getJdbcTemplate().query(GET_FINISHED_JOBS + interval,
                JobDaoJdbc.JOB_MAPPER, JobState.Finished.toString());
    }

    public void transferJob(Job job) {
        /**
         * All of the historical transfer happens inside of triggers
         */
        getJdbcTemplate().update("DELETE FROM job WHERE pk_job=?", job.getJobId());
    }
}

