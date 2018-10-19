
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



package com.imageworks.spcue.test.service;

import java.io.File;
import java.util.List;

import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.CueIce.FrameState;
import com.imageworks.spcue.Frame;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.service.EmailSupport;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobSpec;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class EmailSupportTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    JobLauncher jobLauncher;

    @Resource
    EmailSupport emailSupport;

    @Resource
    JobDao jobDao;

    @Resource
    FrameDao frameDao;

    @Before
    public void setTestMode() {
        jobLauncher.testMode = true;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobCompleteEmailSuccess() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);

        JobDetail job = spec.getJobs().get(0).detail;

        jobDao.updateEmail(job, System.getProperty("user.name"));
        /*jdbcTemplate.update("UPDATE job SET str_email=? WHERE pk_job=?",
                System.getProperty("user.name"), job.getId());*/


        // System.out.println(jdbcTemplate.queryForObject("SELECT count(1) FROM frame WHERE pk_job=?", Integer.class, job.getJobId()));

        List<Frame> jobFrames = frameDao.findFrames(new FrameSearch(job));

        System.out.println(jobFrames.size());
        //frameDao.findFrames(new FrameSearch(job))

        jobFrames.forEach(frame -> frameDao.updateFrameState(frame, FrameState.Running));
        jobFrames.forEach(frame -> frameDao.updateFrameState(frame, FrameState.Succeeded));

        System.out.println(jdbcTemplate.queryForObject("SELECT int_succeeded_count FROM job_stat WHERE pk_job=?", Integer.class, job.getJobId()));

        /*jdbcTemplate.update("UPDATE job_stat SET int_succeeded_count = " +
                "(SELECT count(1) FROM frame WHERE pk_job=?) " +
                "WHERE pk_job=?", job.getId(), job.getId());*/

        emailSupport.sendShutdownEmail(job);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobCompleteEmailFail() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);

        JobDetail job = spec.getJobs().get(0).detail;

        jdbcTemplate.update("UPDATE job SET str_email=? WHERE pk_job=?",
                System.getProperty("user.name"), job.getId());

        jdbcTemplate.update("UPDATE job_stat SET int_dead_count=1 " +
        		"WHERE pk_job=?", job.getId());

        emailSupport.sendShutdownEmail(job);
    }
}

