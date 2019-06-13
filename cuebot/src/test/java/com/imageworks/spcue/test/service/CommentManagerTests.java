
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

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.service.CommentManager;
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


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)

public class CommentManagerTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    JobManager jobManager;

    @Autowired
    CommentManager commentManager;

    public JobDetail launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail d = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        jobManager.setJobPaused(d, false);
        return d;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobComment() {

        JobDetail j = launchJob();

        CommentDetail c = new CommentDetail();
        c.message = "A test comment";
        c.subject = "A test subject";
        c.user = "Mr. Bigglesworth";
        c.timestamp = new java.sql.Timestamp(System.currentTimeMillis());

        commentManager.addComment(j, c);


    }
}

