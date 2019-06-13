
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

import com.imageworks.spcue.BuildableLayer;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.LayerType;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobSpec;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;
import com.imageworks.spcue.util.JobLogUtil;
import org.apache.commons.lang.StringUtils;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;

import static org.junit.Assert.*;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class LayerDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    JobDao jobDao;

    @Autowired
    LayerDao layerDao;

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    FacilityDao facilityDao;

    private static String ROOT_FOLDER = "A0000000-0000-0000-0000-000000000000";
    private static String ROOT_SHOW = "00000000-0000-0000-0000-000000000000";
    private static String LAYER_NAME = "pass_1";
    private static String JOB_NAME = "pipe-dev.cue-testuser_shell_v1";

    @Before
    public void testMode() {
        jobLauncher.testMode = true;
    }

    public LayerDetail getLayer() {

        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job =  spec.getJobs().get(0).detail;
        job.groupId = ROOT_FOLDER;
        job.showId = ROOT_SHOW;
        job.logDir = JobLogUtil.getJobLogPath(job);
        job.facilityId = facilityDao.getDefaultFacility().getId();
        jobDao.insertJob(job);

        LayerDetail lastLayer= null;

        for (BuildableLayer buildableLayer: spec.getJobs().get(0).getBuildableLayers()) {

            LayerDetail layer = buildableLayer.layerDetail;
            FrameSet frameSet = new FrameSet(layer.range);
            int num_frames = frameSet.size();
            int chunk_size = layer.chunkSize;

            layer.jobId = job.id;
            layer.showId = ROOT_SHOW;
            layer.totalFrameCount = num_frames / chunk_size;
            if (num_frames % chunk_size > 0) { layer.totalFrameCount++; }

            layerDao.insertLayerDetail(layer);
            layerDao.insertLayerEnvironment(layer, buildableLayer.env);
            lastLayer = layer;
        }

        return lastLayer;
    }

    public JobDetail getJob() {
        return jobDao.findJobDetail(JOB_NAME);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsLayerComplete() {
        layerDao.isLayerComplete(getLayer());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsLayerDispatchable() {
        layerDao.isLayerDispatchable(getLayer());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertLayerDetail() {
        LayerDetail layer = getLayer();
        assertEquals(LAYER_NAME, layer.name);
        assertEquals(layer.chunkSize, 1);
        assertEquals(layer.dispatchOrder,2);
        assertNotNull(layer.id);
        assertNotNull(layer.jobId);
        assertEquals(layer.showId,ROOT_SHOW);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLayerDetail() {
        LayerDetail layer = getLayer();
        assertEquals(LAYER_NAME, layer.name);
        assertEquals(layer.chunkSize, 1);
        assertEquals(layer.dispatchOrder,2);
        assertNotNull(layer.id);
        assertNotNull(layer.jobId);
        assertEquals(layer.showId,ROOT_SHOW);

        LayerDetail l2 = layerDao.getLayerDetail(layer);
        LayerDetail l3 = layerDao.getLayerDetail(layer.id);
        assertEquals(l2, l3);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindLayerDetail() {
        LayerDetail layer = getLayer();
        layerDao.findLayer(getJob(), "pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLayer() {
        LayerDetail layer = getLayer();
        layerDao.getLayer(layer.id);
        layerDao.getLayerDetail(layer);
        layerDao.getLayerDetail(layer.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindLayer() {
        LayerDetail layer = getLayer();
        layerDao.findLayer(getJob(), "pass_1");
        layerDao.findLayerDetail(getJob(), "pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateLayerMinCores() {
        LayerDetail layer = getLayer();
        layerDao.updateLayerMinCores(layer, 200);
        LayerDetail l2 = layerDao.findLayerDetail(getJob(), "pass_1");
        assertEquals(l2.minimumCores,200);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateLayerThreadable() {
        LayerDetail layer = getLayer();
        layerDao.updateThreadable(layer, false);
        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_threadable FROM layer WHERE pk_layer=?",
                Boolean.class, layer.getLayerId()));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateLayerMinMemory() {
        LayerDetail layer = getLayer();

        /*
         * Check to ensure going below Dispatcher.MEM_RESERVED_MIN is
         * not allowed.
         */
        layerDao.updateLayerMinMemory(layer, 8096);
        LayerDetail l2 = layerDao.findLayerDetail(getJob(), "pass_1");
        assertEquals(l2.minimumMemory, Dispatcher.MEM_RESERVED_MIN);

        /*
         * Check regular operation.
         */
        layerDao.updateLayerMinMemory(layer, CueUtil.GB);
        LayerDetail l3 = layerDao.findLayerDetail(getJob(), "pass_1");
        assertEquals(l3.minimumMemory, CueUtil.GB);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateLayerTags() {
        LayerDetail layer = getLayer();

        HashSet<String> tags = new HashSet<String>();
        tags.add("frickjack");
        tags.add("pancake");

        layerDao.updateLayerTags(layer, tags);
        LayerDetail l2 = layerDao.findLayerDetail(getJob(), "pass_1");
        assertEquals(StringUtils.join(l2.tags," | "), "frickjack | pancake");

        tags.clear();
        tags.add("frickjack");

        layerDao.updateLayerTags(layer, tags);
        l2 = layerDao.findLayerDetail(getJob(), "pass_1");
        assertEquals(StringUtils.join(l2.tags," | "), "frickjack");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFrameStateTotals() {
        LayerDetail layer = getLayer();
        layerDao.getFrameStateTotals(layer);
        jobDao.getFrameStateTotals(layer);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetExecutionSummary() {
        LayerDetail layer = getLayer();
        layerDao.getExecutionSummary(layer);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLayerEnvironment() {
        LayerDetail layer = getLayer();
        Map<String,String> map = layerDao.getLayerEnvironment(layer);
        for (Map.Entry<String,String> e : map.entrySet()) {

        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertLayerEnvironment() {
        LayerDetail layer = getLayer();
        layerDao.insertLayerEnvironment(layer, "CHAMBERS","123");
        Map<String,String> env = layerDao.getLayerEnvironment(layer);
        assertEquals(2,env.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertLayerEnvironmentMap() {
        LayerDetail layer = getLayer();
        Map<String,String> map = new HashMap<String,String>();
        map.put("CHAMBERS","123");
        map.put("OVER9000","123");

        layerDao.insertLayerEnvironment(layer, map);
        Map<String,String> env = layerDao.getLayerEnvironment(layer);
        assertEquals(3,env.size());
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testFindPastSameNameMaxRSS() {
        getLayer();
        jobDao.updateState(getJob(), JobState.FINISHED);
        assertEquals(JobState.FINISHED, getJob().state);

        JobDetail lastJob = null;
        lastJob = jobDao.findLastJob("pipe-dev.cue-testuser_shell_v1");
        long maxRss = layerDao.findPastMaxRSS(lastJob, "pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindPastTimeStampMaxRSS() {
        getLayer();
        jobDao.updateState(getJob(), JobState.FINISHED);
        assertEquals(JobState.FINISHED, getJob().state);

        JobDetail lastJob = null;
        lastJob = jobDao.findLastJob("pipe-dev.cue-testuser_shell_v1_2011_05_03_16_03");
        long maxRss = layerDao.findPastMaxRSS(lastJob, "pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindPastNewVersionMaxRSS() {
        getLayer();
        jobDao.updateState(getJob(), JobState.FINISHED);
        assertEquals(JobState.FINISHED, getJob().state);

        JobDetail lastJob = null;
        lastJob = jobDao.findLastJob("pipe-dev.cue-testuser_shell_v2");
        long maxRss = layerDao.findPastMaxRSS(lastJob, "pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindPastNewVersionTimeStampMaxRSS() {
        getLayer();
        jobDao.updateState(getJob(), JobState.FINISHED);
        assertEquals(JobState.FINISHED, getJob().state);

        JobDetail lastJob = null;
        lastJob = jobDao.findLastJob("pipe-dev.cue-testuser_shell_v2_2011_05_03_16_03");
        long maxRss = layerDao.findPastMaxRSS(lastJob, "pass_1");
    }

    @Test(expected=org.springframework.dao.EmptyResultDataAccessException.class)
    @Transactional
    @Rollback(true)
    public void testFindPastNewVersionFailMaxRSS() {
        getLayer();
        jobDao.updateState(getJob(), JobState.FINISHED);
        assertEquals(JobState.FINISHED, getJob().state);

        JobDetail lastJob = null;
        lastJob = jobDao.findLastJob("pipe-dev.cue-testuser_shell_vfail_v2");
        long maxRss = layerDao.findPastMaxRSS(lastJob, "pass_1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateLayerMaxRSS() {
        LayerDetail layer = getLayer();

        layerDao.updateLayerMaxRSS(layer, 1000, true);
        assertEquals(Long.valueOf(1000), jdbcTemplate.queryForObject(
                "SELECT int_max_rss FROM layer_mem WHERE pk_layer=?",
                Long.class, layer.getId()));

        layerDao.updateLayerMaxRSS(layer, 999, true);
        assertEquals(Long.valueOf(999), jdbcTemplate.queryForObject(
                "SELECT int_max_rss FROM layer_mem WHERE pk_layer=?",
                Long.class, layer.getId()));

        layerDao.updateLayerMaxRSS(layer, 900, false);
        assertEquals(Long.valueOf(999), jdbcTemplate.queryForObject(
                "SELECT int_max_rss FROM layer_mem WHERE pk_layer=?",
                Long.class, layer.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateTags() {
        String tag = "dillweed";
        LayerDetail layer = getLayer();
        layerDao.updateTags(layer, tag, LayerType.RENDER);
        assertEquals(tag,jdbcTemplate.queryForObject(
                "SELECT str_tags FROM layer WHERE pk_layer=?", String.class, layer.getLayerId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateMinMemory() {
        long mem = CueUtil.GB;
        LayerDetail layer = getLayer();
        layerDao.updateMinMemory(layer, mem, LayerType.RENDER);
        assertEquals(Long.valueOf(mem), jdbcTemplate.queryForObject(
                "SELECT int_mem_min FROM layer WHERE pk_layer=?",
                Long.class, layer.getLayerId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateMinGpu() {
        long gpu = CueUtil.GB;
        LayerDetail layer = getLayer();
        layerDao.updateMinGpu(layer, gpu, LayerType.RENDER);
        assertEquals(Long.valueOf(gpu),jdbcTemplate.queryForObject(
                "SELECT int_gpu_min FROM layer WHERE pk_layer=?",
                Long.class, layer.getLayerId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateMinCores() {
        int cores = CueUtil.ONE_CORE * 2;
        LayerDetail layer = getLayer();
        layerDao.updateMinCores(layer, cores, LayerType.RENDER);
        assertEquals(Integer.valueOf(cores), jdbcTemplate.queryForObject(
                "SELECT int_cores_min FROM layer WHERE pk_layer=?",
                Integer.class, layer.getLayerId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateMaxCores() {
        int cores = CueUtil.ONE_CORE * 2;
        LayerDetail layer = getLayer();
        layerDao.updateLayerMaxCores(layer, cores);
        assertEquals(Integer.valueOf(cores), jdbcTemplate.queryForObject(
                "SELECT int_cores_max FROM layer WHERE pk_layer=?",
                Integer.class, layer.getLayerId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void isOptimizable() {
        LayerDetail layer = getLayer();

        assertFalse(layerDao.isOptimizable(layer, 5, 3600));

        /*
         * The succeeded count is good but the frames are too long
         * Assert False
         */
        jdbcTemplate.update("UPDATE layer_stat SET int_succeeded_count = 5 WHERE pk_layer=?",
                layer.getLayerId());

        jdbcTemplate.update(
                "UPDATE layer_usage SET int_core_time_success = 3600 * 6" +
                "WHERE pk_layer=?", layer.getLayerId());

        assertFalse(layerDao.isOptimizable(layer, 5, 3600));

        /*
         * Set the frame times lower, so now we meet the criteria
         * Assert True
         */
        jdbcTemplate.update(
                "UPDATE layer_usage SET int_core_time_success = 3500 * 5" +
                "WHERE pk_layer=?", layer.getLayerId());

        assertTrue(layerDao.isOptimizable(layer, 5, 3600));

        /*
         * Take the general tag away.  If a layer is not a general layer
         * it cannot be optmiized.
         * Assert False
         */
        jdbcTemplate.update(
                "UPDATE layer SET str_tags=? WHERE pk_layer=?",
                "desktop",layer.getLayerId());

        assertFalse(layerDao.isOptimizable(layer, 5, 3600));

        /*
         * Layers that are already tagged util should return
         * false as well.
         *
         * Assert False
         */
        jdbcTemplate.update(
                "UPDATE layer SET str_tags=? WHERE pk_layer=?",
                "general | util",layer.getLayerId());

        assertFalse(layerDao.isOptimizable(layer, 5, 3600));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateUsage() {
        LayerDetail layer = getLayer();

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_clock_time_success FROM layer_usage WHERE pk_layer=?",
                Integer.class, layer.getId()));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_core_time_success FROM layer_usage WHERE pk_layer=?",
                Integer.class, layer.getId()));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_frame_success_count FROM layer_usage WHERE pk_layer=?",
                Integer.class, layer.getId()));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_clock_time_fail FROM layer_usage WHERE pk_layer=?",
                Integer.class, layer.getId()));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_core_time_fail FROM layer_usage WHERE pk_layer=?",
                Integer.class, layer.getId()));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_frame_fail_count FROM layer_usage WHERE pk_layer=?",
                Integer.class, layer.getId()));

        /** 60 seconds of 100 core units **/
        ResourceUsage usage = new ResourceUsage(60, 33);

        assertTrue(usage.getClockTimeSeconds() > 0);
        assertTrue(usage.getCoreTimeSeconds() > 0);

        /**
         * Successful frame
         */
        layerDao.updateUsage(layer, usage, 0);
        assertEquals(Long.valueOf(usage.getClockTimeSeconds()), jdbcTemplate.queryForObject(
                "SELECT int_clock_time_success FROM layer_usage WHERE pk_layer=?",
                Long.class, layer.getId()));

        assertEquals(Long.valueOf(usage.getCoreTimeSeconds()), jdbcTemplate.queryForObject(
                "SELECT int_core_time_success FROM layer_usage WHERE pk_layer=?",
                Long.class, layer.getId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_frame_success_count FROM layer_usage WHERE pk_layer=?",
                Integer.class, layer.getId()));

        /**
         * Failed frame
         */
        layerDao.updateUsage(layer, usage, 1);
        assertEquals(Long.valueOf(usage.getClockTimeSeconds()), jdbcTemplate.queryForObject(
                "SELECT int_clock_time_fail FROM layer_usage WHERE pk_layer=?",
                Long.class, layer.getId()));

        assertEquals(Long.valueOf(usage.getCoreTimeSeconds()), jdbcTemplate.queryForObject(
                "SELECT int_core_time_fail FROM layer_usage WHERE pk_layer=?",
                Long.class, layer.getId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT int_frame_fail_count FROM layer_usage WHERE pk_layer=?",
                Integer.class, layer.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void isLayerThreadable() {
        LayerDetail layer = getLayer();
        jdbcTemplate.update(
                "UPDATE layer set b_threadable = false WHERE pk_layer = ?",
                layer.getId());

        assertFalse(layerDao.isThreadable(layer));

        jdbcTemplate.update(
                "UPDATE layer set b_threadable = true WHERE pk_layer = ?",
                layer.getId());

        assertTrue(layerDao.isThreadable(layer));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void enableMemoryOptimizer() {
        LayerDetail layer = getLayer();
        layerDao.enableMemoryOptimizer(layer, false);
        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_optimize FROM layer WHERE pk_layer=?",
                Boolean.class, layer.getLayerId()));

        layerDao.enableMemoryOptimizer(layer, true);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_optimize FROM layer WHERE pk_layer=?",
                Boolean.class, layer.getLayerId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testBalanceMemory() {
        LayerDetail layer = getLayer();
        assertTrue(layerDao.balanceLayerMinMemory(layer, CueUtil.GB));
        jdbcTemplate.update("UPDATE layer_mem SET int_max_rss=? WHERE pk_layer=?",
                CueUtil.GB8, layer.getId());
        assertFalse(layerDao.balanceLayerMinMemory(layer, CueUtil.MB512));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertLayerOutput() {
        LayerDetail layer = getLayer();
        layerDao.insertLayerOutput(layer, "filespec1");
        layerDao.insertLayerOutput(layer, "filespec2");
        layerDao.insertLayerOutput(layer, "filespec3");
        assertEquals(3, layerDao.getLayerOutputs(layer).size());
    }
}


