
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
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DependDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.EmailSupport;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobSpec;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class EmailSupportTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    JobLauncher jobLauncher;

    @Resource
    EmailSupport emailSupport;

    @Resource
    JobDao jobDao;

    @Resource
    FrameDao frameDao;

    @Resource
    DependDao dependDao;

    @Resource
    LayerDao layerDao;

    @Resource
    DependManager dependManager;

    @Resource
    FrameSearchFactory frameSearchFactory;

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

        // Satisfy all dependencies, this will allow us to mark frames as complete.
        layerDao.getLayers(job)
                .forEach(layer -> dependDao.getWhatThisDependsOn(layer, DependTarget.ANY_TARGET)
                        .forEach(dep -> dependManager.satisfyDepend(dep)));

        frameDao.findFrames(frameSearchFactory.create(job)).forEach(
                frame -> frameDao.updateFrameState(
                        frameDao.getFrame(frame.getFrameId()), FrameState.SUCCEEDED));

        emailSupport.sendShutdownEmail(job);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobCompleteEmailFail() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);

        JobDetail job = spec.getJobs().get(0).detail;

        jobDao.updateEmail(job, System.getProperty("user.name"));

        layerDao.getLayers(job)
                .forEach(layer -> dependDao.getWhatThisDependsOn(layer, DependTarget.ANY_TARGET)
                        .forEach(dep -> dependManager.satisfyDepend(dep)));

        frameDao.findFrames(frameSearchFactory.create(job)).forEach(
                frame -> frameDao.updateFrameState(
                        frameDao.getFrame(frame.getFrameId()), FrameState.DEAD));

        emailSupport.sendShutdownEmail(job);
    }
}

