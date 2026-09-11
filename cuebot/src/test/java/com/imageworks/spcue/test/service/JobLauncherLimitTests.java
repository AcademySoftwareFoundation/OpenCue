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

package com.imageworks.spcue.test.service;

import java.io.File;
import java.util.List;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.EntityCreationError;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobLaunchException;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitType;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobSpec;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class JobLauncherLimitTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    @Resource
    LayerDao layerDao;

    @Resource
    LimitDao limitDao;

    private static final String JOB_NAME = "pipe-dev.cue-testuser_shell_v1";

    private static final File SPEC = new File("src/test/resources/conf/jobspec/jobspec_limit.xml");

    @Before
    public void setTestMode() {
        jobLauncher.testMode = true;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLaunchRejectsUndefinedLimits() {
        try {
            jobLauncher.launch(SPEC);
            fail("expected the launch to be rejected");
        } catch (EntityCreationError e) {
            // Both undefined limits are reported, along with the layers using them.
            assertTrue(e.getMessage(),
                    e.getMessage().contains("util (used by " + JOB_NAME + "/pass_1_preprocess)"));
            assertTrue(e.getMessage(),
                    e.getMessage().contains("arnold (used by " + JOB_NAME + "/pass_1)"));
        }

        assertFalse("no job should have been created", jobManager.isJobPending(JOB_NAME));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLaunchReportsOnlyUndefinedLimits() {
        limitDao.createLimit("util", 15, LimitType.FRAME, LimitEnforcement.ENFORCED, -1);

        try {
            jobLauncher.launch(SPEC);
            fail("expected the launch to be rejected");
        } catch (EntityCreationError e) {
            assertTrue(e.getMessage(), e.getMessage().contains("arnold"));
            assertFalse(e.getMessage(), e.getMessage().contains("util (used by"));
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLaunchSucceedsWhenLimitsExist() {
        limitDao.createLimit("util", 15, LimitType.FRAME, LimitEnforcement.ENFORCED, -1);
        limitDao.createLimit("arnold", 20, LimitType.FRAME, LimitEnforcement.ENFORCED, -1);

        jobLauncher.launch(SPEC);

        JobDetail job = jobManager.findJobDetail(JOB_NAME);
        LayerInterface layer = layerDao.findLayer(job, "pass_1");
        List<String> limits = layerDao.getLimitNames(layer);
        assertEquals(1, limits.size());
        assertEquals("arnold", limits.get(0));
    }

    /**
     * Job creation has to fail closed on its own, since it is also reachable without going through
     * the launcher's verification step.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testCreateJobRejectsUndefinedLimits() {
        JobSpec spec = jobLauncher.parse(SPEC);

        try {
            jobManager.launchJobSpec(spec);
            fail("expected job creation to be rejected");
        } catch (JobLaunchException e) {
            assertTrue(e.getMessage(),
                    e.getMessage().contains("references limits that do not exist: util"));
        }
    }
}
