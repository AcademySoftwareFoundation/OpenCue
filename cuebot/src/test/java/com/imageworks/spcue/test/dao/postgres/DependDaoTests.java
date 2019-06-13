
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

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DependDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.depend.*;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;

import static org.junit.Assert.*;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class DependDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    DependDao dependDao;

    @Autowired
    FrameDao frameDao;

    @Autowired
    LayerDao layerDao;

    @Autowired
    JobManager jobManager;

    @Autowired
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

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJobOnJob() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        JobOnJob depend = new JobOnJob(job_a, job_b);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.JOB_ON_JOB, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJobOnLayer() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        LayerInterface layer = layerDao.findLayer(job_b, "pass_1");
        JobOnLayer depend = new JobOnLayer(job_a, layer);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.JOB_ON_LAYER, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertJobOnFrame() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        FrameDetail frame = frameDao.findFrameDetail(job_b, "0001-pass_1");
        JobOnFrame depend = new JobOnFrame(job_a, frame);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.JOB_ON_FRAME, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertLayerOnJob() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer = layerDao.findLayer(job_b, "pass_1");

        LayerOnJob depend = new LayerOnJob(layer, job_a);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.LAYER_ON_JOB, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertLayerOnLayer() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer_a = layerDao.findLayer(job_a, "pass_1");
        LayerInterface layer_b = layerDao.findLayer(job_b, "pass_1");

        LayerOnLayer depend = new LayerOnLayer(layer_a, layer_b);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.LAYER_ON_LAYER, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertLayerOnFrame() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer = layerDao.findLayer(job_a, "pass_1");
        FrameDetail frame = frameDao.findFrameDetail(job_b, "0001-pass_1");

        LayerOnFrame depend = new LayerOnFrame(layer, frame);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.LAYER_ON_FRAME, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertFrameOnJob() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        FrameDetail frame = frameDao.findFrameDetail(job_b, "0001-pass_1");

        FrameOnJob depend = new FrameOnJob(frame, job_a);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.FRAME_ON_JOB, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertFrameOnLayer() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer = layerDao.findLayer(job_a, "pass_1");
        FrameDetail frame = frameDao.findFrameDetail(job_b, "0001-pass_1");

        FrameOnLayer depend = new FrameOnLayer(frame,layer);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.FRAME_ON_LAYER, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertFrameOnFrame() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        FrameDetail frame_a = frameDao.findFrameDetail(job_a, "0001-pass_1");
        FrameDetail frame_b = frameDao.findFrameDetail(job_b, "0001-pass_1");

        FrameOnFrame depend = new FrameOnFrame(frame_a, frame_b);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.FRAME_ON_FRAME, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertFrameByFrame() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer_a = layerDao.findLayer(job_a, "pass_1");
        LayerInterface layer_b = layerDao.findLayer(job_b, "pass_1");

        FrameByFrame depend = new FrameByFrame(layer_a, layer_b);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.FRAME_BY_FRAME, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertPreviousFrame() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();
        LayerInterface layer_a = layerDao.findLayer(job_a, "pass_1");
        LayerInterface layer_b = layerDao.findLayer(job_b, "pass_1");

        PreviousFrame depend = new PreviousFrame(layer_a, layer_b);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.PREVIOUS_FRAME, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReinsertFrameOnFrame() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        FrameDetail frame_a = frameDao.findFrameDetail(job_a, "0001-pass_1");
        FrameDetail frame_b = frameDao.findFrameDetail(job_b, "0001-pass_1");

        FrameOnFrame depend = new FrameOnFrame(frame_a, frame_b);
        dependDao.insertDepend(depend);

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        assertEquals(depend.getId(), lwd.getId());
        assertEquals(DependType.FRAME_ON_FRAME, lwd.type);
        assertEquals(DependTarget.EXTERNAL, lwd.target);
        assertTrue(lwd.active);
        assertFalse(lwd.anyFrame);

        dependDao.setInactive(lwd);

        // Try to reinsert it now that the original is inactive.
        depend = new FrameOnFrame(frame_a, frame_b);
        dependDao.insertDepend(depend);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetWhatDependsOnJob() {
        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        JobOnJob depend = new JobOnJob(job_a, job_b);
        dependDao.insertDepend(depend);

        assertEquals(1, dependDao.getWhatDependsOn(job_b).size());
        assertEquals(0, dependDao.getWhatDependsOn(job_a).size());
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testGetWhatDependsOnLayer() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        LayerInterface layer_a = layerDao.findLayer(job_a, "pass_1");
        LayerInterface layer_b = layerDao.findLayer(job_b, "pass_1");

        LayerOnLayer depend = new LayerOnLayer(layer_a, layer_b);
        dependDao.insertDepend(depend);

        assertEquals(1, dependDao.getWhatDependsOn(layer_b).size());
        assertEquals(0, dependDao.getWhatDependsOn(layer_a).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetWhatDependsOnLayerInactive() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        LayerInterface layer_a = layerDao.findLayer(job_a, "pass_1");
        LayerInterface layer_b = layerDao.findLayer(job_b, "pass_1");

        LayerOnLayer depend = new LayerOnLayer(layer_a, layer_b);
        dependDao.insertDepend(depend);

        dependDao.setInactive(dependDao.getDepend(depend.getId()));

        assertEquals(1, dependDao.getWhatDependsOn(layer_b, false).size());
        assertEquals(0, dependDao.getWhatDependsOn(layer_b, true).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetWhatDependsOnFrame() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        FrameDetail frame_a = frameDao.findFrameDetail(job_a, "0001-pass_1");
        FrameDetail frame_b = frameDao.findFrameDetail(job_b, "0001-pass_1");

        FrameOnFrame depend = new FrameOnFrame(frame_a, frame_b);
        dependDao.insertDepend(depend);

        assertEquals(1, dependDao.getWhatDependsOn(frame_b).size());
        assertEquals(0, dependDao.getWhatDependsOn(frame_a).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetWhatDependsOnFrameInactive() {

        JobDetail job_a = getJobA();
        JobDetail job_b = getJobB();

        FrameDetail frame_a = frameDao.findFrameDetail(job_a, "0001-pass_1");
        FrameDetail frame_b = frameDao.findFrameDetail(job_b, "0001-pass_1");

        FrameOnFrame depend = new FrameOnFrame(frame_a, frame_b);
        dependDao.insertDepend(depend);

        dependDao.setInactive(dependDao.getDepend(depend.getId()));

        assertEquals(1, dependDao.getWhatDependsOn(frame_b, false).size());
        assertEquals(0, dependDao.getWhatDependsOn(frame_b, true).size());
        assertEquals(0, dependDao.getWhatDependsOn(frame_a, true).size());
    }
}

