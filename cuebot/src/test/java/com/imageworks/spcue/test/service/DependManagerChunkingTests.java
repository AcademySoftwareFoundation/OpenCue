
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

import com.google.common.collect.ImmutableList;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.dao.DependDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.depend.FrameByFrame;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.depend.DependType;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.List;

import static org.junit.Assert.*;

@ContextConfiguration
public class DependManagerChunkingTests extends TransactionalTest {

    @Autowired
    DependDao dependDao;

    @Autowired
    DependManager dependManager;

    @Autowired
    FrameDao frameDao;

    @Autowired
    LayerDao layerDao;

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    FrameSearchFactory frameSearchFactory;

    @Before
    public void launchTestJobs() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/chunk_depend.xml"));
    }

    private JobDetail getJob() {
        return jobManager.findJobDetail("pipe-dev.cue-testuser_chunked_depend");
    }

    private int getTotalDependSum(LayerInterface layer) {
        return frameDao.findFrameDetails(frameSearchFactory.create(layer))
                .stream()
                .mapToInt(frame -> frame.dependCount)
                .sum();
    }

    private boolean hasDependFrames(LayerInterface layer) {
        FrameSearchInterface search = frameSearchFactory.create(layer);
        search.filterByFrameStates(ImmutableList.of(FrameState.DEPEND));
        return frameDao.findFrames(search).size() > 0;
    }

    private int getDependRecordCount(LayerInterface l) {
        List<LightweightDependency> activeDeps = dependDao.getWhatThisDependsOn(
                l, DependTarget.ANY_TARGET);
        int numChildDeps = activeDeps.stream().mapToInt(
                dep -> dependDao.getChildDepends(dep).size()).sum();
        return numChildDeps + activeDeps.size();
    }

    /**
     * Test a non-chunked layer depending on a large chunked layer.
     * <1>                <1>
     * <2>
     * <3>
     * <4>
     * <5>
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testCreateAndSatisfyNonChunkOnLargeChunk() {

        JobDetail job = getJob();
        LayerInterface layer_a = layerDao.findLayer(job, "no_chunk");
        LayerInterface layer_b = layerDao.findLayer(job, "large_chunk");

        FrameByFrame depend = new FrameByFrame(layer_a, layer_b);
        dependManager.createDepend(depend);

        assertTrue(hasDependFrames(layer_a));
        assertEquals(100, getTotalDependSum(layer_a));
        // Optimized to LayerOnLayer
        assertEquals(1, getDependRecordCount(layer_a));

        for (LightweightDependency lwd: dependDao.getWhatDependsOn(layer_b)) {
            assertEquals(DependType.LAYER_ON_LAYER, lwd.type);
            dependManager.satisfyDepend(lwd);
        }

        assertFalse(hasDependFrames(layer_a));
        assertEquals(0, getTotalDependSum(layer_a));
    }

    /**
     * Test a large chunked layer depending on a non-chunked layer.
     * <1>                   <1>
     *                       <2>
     *                       <3>
     *                       <4>
     *                       <5>
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testCreateAndSatisfyLargeChunkOnNonChunk() {

        JobDetail job = getJob();
        LayerInterface layer_a = layerDao.findLayer(job, "large_chunk");
        LayerInterface layer_b = layerDao.findLayer(job, "no_chunk");

        FrameByFrame depend = new FrameByFrame(layer_a, layer_b);
        dependManager.createDepend(depend);

        assertTrue(hasDependFrames(layer_a));
        // Optimized to LayerOnLayer
        assertEquals(1, getTotalDependSum(layer_a));
        assertEquals(1, getDependRecordCount(layer_a));

        for (LightweightDependency lwd: dependDao.getWhatDependsOn(layer_b)) {
            assertEquals(DependType.LAYER_ON_LAYER, lwd.type);
            dependManager.satisfyDepend(lwd);
        }

        assertFalse(hasDependFrames(layer_a));
        assertEquals(0, getTotalDependSum(layer_a));
    }

    /**
     * Test a small chunk depending on a non chunk
     * <1>              <1>
     *                  <2>
     *                  <3>
     * <4>              <4>
     *                  <5>
     *                  <6>
     *                  <7>
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testCreateAndSatisfySmallChunkOnNonChunk() {

        JobDetail job = getJob();
        LayerInterface layer_a = layerDao.findLayer(job, "small_chunk");
        LayerInterface layer_b = layerDao.findLayer(job, "no_chunk");

        FrameByFrame depend = new FrameByFrame(layer_a, layer_b);
        dependManager.createDepend(depend);

        assertTrue(hasDependFrames(layer_a));
        assertEquals(100, getTotalDependSum(layer_a));
        assertEquals(101, getDependRecordCount(layer_a));

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        dependManager.satisfyDepend(lwd);
        assertFalse(hasDependFrames(layer_a));
        assertEquals(0, getTotalDependSum(layer_a));
    }

    /**
     * Test a non chunk depending on a small chunk
     *
     * <1>               <1>
     * <2>
     * <3>
     * <4>
     * <5>               <5>
     * <6>
     * <7>
     * <8>
     * <9>
     * <10>
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testCreateAndSatisfyNonChunkOnSmallChunk() {

        JobDetail job = getJob();
        LayerInterface layer_a = layerDao.findLayer(job, "no_chunk");
        LayerInterface layer_b = layerDao.findLayer(job, "small_chunk");

        FrameByFrame depend = new FrameByFrame(layer_a, layer_b);
        dependManager.createDepend(depend);

        assertEquals(101, getDependRecordCount(layer_a));
        assertTrue(hasDependFrames(layer_a));
        assertEquals(100, getTotalDependSum(layer_a));

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        dependManager.satisfyDepend(lwd);
        assertFalse(hasDependFrames(layer_a));
        assertEquals(0, getTotalDependSum(layer_a));
    }

}

