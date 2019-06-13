
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

package com.imageworks.spcue.test.dao.criteria;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.criteria.JobSearchFactory;
import com.imageworks.spcue.dao.criteria.JobSearchInterface;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.JobSearchCriteria;
import com.imageworks.spcue.service.JobLauncher;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class JobSearchTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    JobSearchFactory jobSearchFactory;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    WhiteboardDao whiteboardDao;

    @Autowired
    ShowDao showDao;

    @Before
    public void launchTestJobs() {
        ClassLoader classLoader = getClass().getClassLoader();
        jobLauncher.testMode = true;

        File file = new File(
                classLoader.getResource("conf/jobspec/jobspec.xml").getFile());
        jobLauncher.launch(file);

        file = new File(
                classLoader.getResource("conf/jobspec/jobspec_other_show.xml").getFile());
        jobLauncher.launch(file);
    }

    @Test
    @Transactional
    @Rollback
    public void testGetCriteria() {
        JobSearchCriteria criteria = JobSearchInterface.criteriaFactory();

        JobSearchInterface jobSearch = jobSearchFactory.create(criteria);

        assertEquals(criteria, jobSearch.getCriteria());
    }

    @Test
    @Transactional
    @Rollback
    public void testSetCriteria() {
        JobSearchCriteria criteria = JobSearchInterface.criteriaFactory()
                .toBuilder()
                .addIds("fake-job-id")
                .build();
        JobSearchInterface jobSearch = jobSearchFactory.create();

        // Ensure we can distinguish between the default and non-default criteria.
        assertNotEquals(criteria, jobSearch.getCriteria());

        jobSearch.setCriteria(criteria);

        assertEquals(criteria, jobSearch.getCriteria());
    }

    @Test
    @Transactional
    @Rollback
    public void testFilterByShow() {
        JobSearchCriteria criteria = JobSearchInterface.criteriaFactory()
                .toBuilder()
                .setIncludeFinished(true)
                .build();
        JobSearchInterface jobSearch = jobSearchFactory.create(criteria);
        jobSearch.filterByShow(showDao.findShowDetail("pipe"));

        List<Job> jobs = whiteboardDao.getJobs(jobSearch).getJobsList();

        assertEquals(1, jobs.size());
    }
}
