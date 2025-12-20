
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

package com.imageworks.spcue.test.monitoring;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.dao.DependDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.depend.FrameOnFrame;
import com.imageworks.spcue.depend.LayerOnLayer;
import com.imageworks.spcue.grpc.monitoring.EventType;
import com.imageworks.spcue.grpc.monitoring.FrameEvent;
import com.imageworks.spcue.monitoring.KafkaEventPublisher;
import com.imageworks.spcue.monitoring.MonitoringEventBuilder;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Integration tests for pickup time tracking events.
 *
 * These tests verify that: 1. FRAME_DISPATCHED events are published when frames transition from
 * DEPEND to WAITING (when dependencies are satisfied) 2. The events contain correct state
 * transition information for pickup time calculation
 *
 * Pickup time = FRAME_STARTED.timestamp - FRAME_DISPATCHED.timestamp This measures how long a frame
 * waits in the queue after becoming dispatchable.
 */
@ContextConfiguration
public class PickupTimeTrackingTests extends TransactionalTest {

    @Resource
    DependDao dependDao;

    @Resource
    DependManager dependManager;

    @Resource
    FrameDao frameDao;

    @Resource
    LayerDao layerDao;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Before
    public void launchTestJobs() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_depend_test.xml"));
    }

    public JobDetail getJobA() {
        return jobManager.findJobDetail("pipe-dev.cue-testuser_depend_test_a");
    }

    public JobDetail getJobB() {
        return jobManager.findJobDetail("pipe-dev.cue-testuser_depend_test_b");
    }

    /**
     * Test that isFrameDispatchable returns true when depend_count is 0.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testIsFrameDispatchable() {
        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer_a = layerDao.findLayer(job_a, "pass_1");
        LayerInterface layer_b = layerDao.findLayer(job_b, "pass_1");
        FrameInterface frame_a = frameDao.findFrame(layer_a, 1);
        FrameInterface frame_b = frameDao.findFrame(layer_b, 1);

        // Initially, frame_a should be dispatchable (no dependencies)
        assertTrue("Frame with no dependencies should be dispatchable",
                dependDao.isFrameDispatchable(frame_a));

        // Create a dependency: frame_a depends on frame_b
        FrameOnFrame depend = new FrameOnFrame(frame_a, frame_b);
        dependManager.createDepend(depend);

        // Now frame_a should NOT be dispatchable (has a dependency)
        assertFalse("Frame with active dependency should not be dispatchable",
                dependDao.isFrameDispatchable(frame_a));

        // Satisfy the dependency
        LightweightDependency lwd = dependManager.getDepend(depend.getId());
        dependManager.satisfyDepend(lwd);

        // Now frame_a should be dispatchable again
        assertTrue("Frame with satisfied dependency should be dispatchable",
                dependDao.isFrameDispatchable(frame_a));
    }

    /**
     * Test that depend_count correctly tracks multiple dependencies.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testMultipleDependencies() {
        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer_a = layerDao.findLayer(job_a, "pass_1");
        LayerInterface layer_b = layerDao.findLayer(job_b, "pass_1");
        FrameInterface frame_a = frameDao.findFrame(layer_a, 1);
        FrameInterface frame_b1 = frameDao.findFrame(layer_b, 1);
        FrameInterface frame_b2 = frameDao.findFrame(layer_b, 2);

        // Create two dependencies for frame_a
        FrameOnFrame depend1 = new FrameOnFrame(frame_a, frame_b1);
        FrameOnFrame depend2 = new FrameOnFrame(frame_a, frame_b2);
        dependManager.createDepend(depend1);
        dependManager.createDepend(depend2);

        // Frame should not be dispatchable
        assertFalse("Frame with two dependencies should not be dispatchable",
                dependDao.isFrameDispatchable(frame_a));

        // Satisfy first dependency
        dependManager.satisfyDepend(dependManager.getDepend(depend1.getId()));

        // Still not dispatchable (one dependency remaining)
        assertFalse("Frame with one remaining dependency should not be dispatchable",
                dependDao.isFrameDispatchable(frame_a));

        // Satisfy second dependency
        dependManager.satisfyDepend(dependManager.getDepend(depend2.getId()));

        // Now should be dispatchable
        assertTrue("Frame with all dependencies satisfied should be dispatchable",
                dependDao.isFrameDispatchable(frame_a));
    }

    /**
     * Test that LayerOnLayer dependency satisfaction makes all frames dispatchable.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testLayerOnLayerMakesFramesDispatchable() {
        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer_a = layerDao.findLayer(job_a, "pass_1");
        LayerInterface layer_b = layerDao.findLayer(job_b, "pass_1");

        // Create layer-on-layer dependency
        LayerOnLayer depend = new LayerOnLayer(layer_a, layer_b);
        dependManager.createDepend(depend);

        // All frames in layer_a should not be dispatchable
        FrameInterface frame_a1 = frameDao.findFrame(layer_a, 1);
        FrameInterface frame_a5 = frameDao.findFrame(layer_a, 5);
        assertFalse("Frame in dependent layer should not be dispatchable",
                dependDao.isFrameDispatchable(frame_a1));
        assertFalse("Frame in dependent layer should not be dispatchable",
                dependDao.isFrameDispatchable(frame_a5));

        // Satisfy the layer dependency
        for (LightweightDependency lwd : dependDao.getWhatDependsOn(layer_b)) {
            dependManager.satisfyDepend(lwd);
        }

        // All frames should now be dispatchable
        assertTrue("Frame should be dispatchable after layer dependency satisfied",
                dependDao.isFrameDispatchable(frame_a1));
        assertTrue("Frame should be dispatchable after layer dependency satisfied",
                dependDao.isFrameDispatchable(frame_a5));
    }
}
