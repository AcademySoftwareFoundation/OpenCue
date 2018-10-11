
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

import static org.junit.Assert.*;

import java.io.File;

import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.test.context.ContextConfiguration;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.CueIce.DependType;
import com.imageworks.spcue.CueIce.FrameState;
import com.imageworks.spcue.dao.DependDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.depend.*;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.test.TransactionalTest;

@ContextConfiguration
public class DependManagerChunkingTests extends TransactionalTest {

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

    @Resource
    JobManagerSupport jobManagerSupport;

    @Before
    public void launchTestJobs() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/chunk_depend.xml"));
    }

    public JobDetail getJob() {
        return jobManager.findJobDetail("pipe-dev.cue-testuser_chunked_depend");
    }

    public int getTotalDependSum(JobInterface j) {
        return jdbcTemplate.queryForObject(
                "SELECT SUM(int_depend_count) FROM frame WHERE pk_job=?",
                Integer.class, j.getJobId());
    }

    public boolean hasDependFrames(JobInterface j) {
        return jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM frame WHERE pk_job=? AND str_state=?",
                Integer.class, j.getJobId(), FrameState.Depend.toString()) > 0;
    }

    public int getTotalDependSum(LayerInterface l) {
        return jdbcTemplate.queryForObject(
                "SELECT SUM(int_depend_count) FROM frame WHERE pk_layer=?",
                Integer.class, l.getLayerId());
    }

    public boolean hasDependFrames(LayerInterface l) {
        return jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM frame WHERE pk_layer=? AND str_state=?",
                Integer.class, l.getLayerId(), FrameState.Depend.toString()) > 0;
    }

    public int getTotalDependSum(FrameInterface f) {
        return jdbcTemplate.queryForObject(
                "SELECT SUM(int_depend_count) FROM frame WHERE pk_frame=?",
                Integer.class, f.getFrameId());
    }

    public boolean hasDependFrames(FrameInterface f) {
        return jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM frame WHERE pk_frame=? AND str_state=?",
                Integer.class, f.getFrameId(), FrameState.Depend.toString()) > 0;
    }

    public int getDependRecordCount(LayerInterface l) {
        return jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM depend WHERE pk_layer_depend_er=?",
                Integer.class, l.getLayerId());
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
            assertEquals(DependType.LayerOnLayer, lwd.type);
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
            assertEquals(DependType.LayerOnLayer, lwd.type);
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

        assertEquals(101,getDependRecordCount(layer_a));
        assertTrue(hasDependFrames(layer_a));
        assertEquals(100, getTotalDependSum(layer_a));

        LightweightDependency lwd = dependDao.getDepend(depend.getId());
        dependManager.satisfyDepend(lwd);
        assertFalse(hasDependFrames(layer_a));
        assertEquals(0, getTotalDependSum(layer_a));
    }

}

