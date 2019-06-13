
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



package com.imageworks.spcue.test.dao.postgres;

import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.HistoricalDao;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;

import static org.junit.Assert.assertEquals;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class HistoricalDaoTests extends
        AbstractTransactionalJUnit4SpringContextTests {
    
    @Autowired
    private JobManager jobManager;

    @Autowired
    private JobLauncher jobLauncher;

    @Autowired
    private HistoricalDao historicalDao;

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFinishedJobs() {
        historicalDao.getFinishedJobs(24);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testTransferJob() {
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail j = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        jobManager.shutdownJob(j);
        historicalDao.transferJob(j);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM job_history WHERE pk_job=?",
                Integer.class, j.getJobId()));
    }
}

