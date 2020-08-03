/*
 * Copyright Contributors to the OpenCue Project
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


package com.imageworks.spcue.test.util;

import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.util.JobLogUtil;
import org.junit.Before;
import org.junit.Test;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;

import javax.annotation.Resource;

import static org.junit.Assert.assertEquals;

@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class JobLogUtilTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    private JobLogUtil jobLogUtil;

    private String logRoot;

    @Before
    public void setUp() {
        // This value should match what's defined in test/resources/opencue.properties.
        logRoot = "/arbitraryLogDirectory";
    }

    @Test
    public void testGetJobLogRootDir() {
        assertEquals(logRoot, jobLogUtil.getJobLogRootDir());
    }

    @Test
    public void testGetJobLogDir() {
        assertEquals(logRoot + "/show/shot/logs", jobLogUtil.getJobLogDir("show", "shot"));
    }

    @Test
    public void testGetJobLogPath() {
        JobDetail jobDetail = new JobDetail();
        jobDetail.id = "id";
        jobDetail.name = "name";
        jobDetail.showName = "show";
        jobDetail.shot = "shot";
        assertEquals(logRoot + "/show/shot/logs/name--id", jobLogUtil.getJobLogPath(jobDetail));
    }
}

