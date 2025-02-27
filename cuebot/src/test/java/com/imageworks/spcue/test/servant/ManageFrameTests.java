
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

package com.imageworks.spcue.test.servant;

import javax.annotation.Resource;

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.grpc.job.*;
import com.imageworks.spcue.servant.ManageFrame;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;

import org.junit.Test;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;
import java.io.File;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class ManageFrameTests extends AbstractTransactionalJUnit4SpringContextTests {
    @Resource
    FrameDao frameDao;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    ManageFrame manageFrame;

    public JobDetail launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
    }

    private FrameStateDisplayOverride createFrameStateDisplayOverride(FrameState state, String text,
            int red, int green, int blue) {
        FrameStateDisplayOverride override = FrameStateDisplayOverride.newBuilder().setState(state)
                .setText(text).setColor(FrameStateDisplayOverride.RGB.newBuilder().setRed(red)
                        .setGreen(green).setBlue(blue).build())
                .build();

        return override;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFrameStateOverride() {
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        Frame jobFrame = Frame.newBuilder().setId(frame.getFrameId()).setName(frame.getName())
                .setState(frame.state).build();

        // create initial override
        FrameStateDisplayOverride override =
                createFrameStateDisplayOverride(FrameState.SUCCEEDED, "FINISHED", 200, 200, 123);
        FrameStateDisplayOverrideRequest req = FrameStateDisplayOverrideRequest.newBuilder()
                .setFrame(jobFrame).setOverride(override).build();
        FakeStreamObserver<FrameStateDisplayOverrideResponse> responseObserver =
                new FakeStreamObserver<FrameStateDisplayOverrideResponse>();
        manageFrame.setFrameStateDisplayOverride(req, responseObserver);
        FrameStateDisplayOverrideSeq results =
                frameDao.getFrameStateDisplayOverrides(frame.getFrameId());
        assertEquals(1, results.getOverridesCount());

        // try to create same override
        manageFrame.setFrameStateDisplayOverride(req, responseObserver);
        results = frameDao.getFrameStateDisplayOverrides(frame.getFrameId());
        assertEquals(1, results.getOverridesCount());

        // try to update override text
        FrameStateDisplayOverride overrideUpdated =
                createFrameStateDisplayOverride(FrameState.SUCCEEDED, "DONE", 200, 200, 123);
        FrameStateDisplayOverrideRequest reqUpdated = FrameStateDisplayOverrideRequest.newBuilder()
                .setFrame(jobFrame).setOverride(overrideUpdated).build();
        manageFrame.setFrameStateDisplayOverride(reqUpdated, responseObserver);
        results = frameDao.getFrameStateDisplayOverrides(frame.getFrameId());
        assertEquals(1, results.getOverridesCount());
        assertEquals(overrideUpdated, results.getOverridesList().get(0));

        // add a new override
        FrameStateDisplayOverride overrideNew =
                createFrameStateDisplayOverride(FrameState.EATEN, "NOMNOM", 120, 50, 123);
        FrameStateDisplayOverrideRequest reqNew = FrameStateDisplayOverrideRequest.newBuilder()
                .setFrame(jobFrame).setOverride(overrideNew).build();
        manageFrame.setFrameStateDisplayOverride(reqNew, responseObserver);
        results = frameDao.getFrameStateDisplayOverrides(frame.getFrameId());
        assertEquals(2, results.getOverridesCount());
    }
}
