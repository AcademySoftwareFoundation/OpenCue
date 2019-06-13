
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
import com.imageworks.spcue.*;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.Order;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.*;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.transaction.AfterTransaction;
import org.springframework.test.context.transaction.BeforeTransaction;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;

import static org.hamcrest.Matchers.contains;
import static org.junit.Assert.*;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class JobManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    JobManagerSupport jobManagerSupport;

    @Autowired
    HostManager hostManager;

    @Autowired
    AdminManager adminManager;

    @Autowired
    LayerDao layerDao;

    @Autowired
    DispatcherDao dispatcherDao;

    @Autowired
    FrameDao frameDao;

    @Autowired
    JobDao jobDao;

    @Autowired
    FrameSearchFactory frameSearchFactory;

    private static final String JOB1 = "pipe-dev.cue-testuser_shell_dispatch_test_v1";
    private static final String JOB2 = "pipe-dev.cue-testuser_shell_dispatch_test_v2";
    private static final String JOB3 = "pipe-dev.cue-testuser_shell_v1";

    public JobDetail getJob1() {
        return jobManager.findJobDetail(JOB1);
    }

    public JobDetail getJob2() {
        return jobManager.findJobDetail(JOB2);
    }

    public JobDetail getJob3() {
        return jobManager.findJobDetail(JOB3);
    }

    public DispatchHost createHost() {

        RenderHost host = RenderHost.newBuilder()
                .setName("test_host")
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem((int) CueUtil.GB16)
                .setTotalSwap((int) CueUtil.GB16)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .addTags("general")
                .build();

        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh,
                adminManager.findAllocationDetail("spi", "general"));

        return dh;
    }

    @BeforeTransaction
    public void init() {
        jobLauncher.testMode = true;

        for (String jobName : ImmutableList.of(JOB1, JOB2, JOB3)) {
            try {
                JobInterface job = jobDao.findJob(jobName);
                jobDao.updateJobFinished(job);
                jobDao.deleteJob(job);
            } catch (EmptyResultDataAccessException e) {
                // Job doesn't exist, ignore.
            }
        }

        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        jobLauncher.launch(spec);

        spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);

        for (String jobName : ImmutableList.of(JOB1, JOB2, JOB3)) {
            jobDao.updatePaused(jobDao.findJob(jobName), true);
        }
    }

    @AfterTransaction
    public void destroy() {
        for (String jobName : ImmutableList.of(JOB1, JOB2, JOB3)) {
            JobInterface job = jobDao.findJob(jobName);
            jobDao.updateJobFinished(job);
            jobDao.deleteJob(job);
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLaunchAutoEatJob() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/autoeat.xml"));
        jobLauncher.launch(spec);

        assertTrue(jobDao.getDispatchJob(spec.getJobs().get(0).detail.id).autoEat);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLaunchJob() {
        LayerDetail job1Layer = layerDao.findLayerDetail(jobDao.findJob(JOB1), "pass_1");
        assertEquals(CueUtil.GB2, job1Layer.minimumMemory);
        assertEquals(100, job1Layer.minimumCores);

        // check some job_stats values
        assertEquals(20, getJob1().totalFrames);
        assertEquals(10, jobDao.getFrameStateTotals(jobDao.findJob(JOB2)).waiting);
        assertEquals(0, jobDao.getFrameStateTotals(jobDao.findJob(JOB1)).depend);

        FrameStateTotals job3FrameStates = jobDao.getFrameStateTotals(jobDao.findJob(JOB3));
        assertEquals(1, job3FrameStates.waiting);
        assertEquals(10, job3FrameStates.depend);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testShutdownRelaunchJob() {
        JobDetail job1 = getJob1();
        JobDetail job2 = getJob2();
        logger.info("job detail: " + job2.getName());
        logger.info("job state " + job2.state.toString());

        jobManager.shutdownJob(job1);
        jobManager.shutdownJob(job2);

        assertEquals(JobState.FINISHED, jobDao.getJobDetail(job1.id).state);

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));

        getJob1();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testShutdownJob() {
        JobDetail job = getJob1();
        logger.info("job detail: " + job.getName());
        logger.info("job state " + job.state.toString());

        jobManager.shutdownJob(getJob1());

        assertEquals(JobState.FINISHED, jobDao.getJobDetail(job.id).state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAutoNameJob() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_autoname.xml"));
        jobLauncher.launch(spec);

        assertEquals(JobState.PENDING, jobDao.findJobDetail(spec.conformJobName("autoname")).state);
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testShowAlias() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/show_alias.xml"));
        jobLauncher.launch(spec);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMisNamedJob() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_misnamed.xml"));
        assertEquals("pipe-dev.cue-testuser_pipe_dev.cue_testuser_blah_blah_v1",spec.getJobs().get(0).detail.name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testMisNamedJob2() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_misnamed.xml"));

        assertEquals(spec.conformJobName("blah_____blah_v1"),
                                         "pipe-dev.cue-testuser_blah_blah_v1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testPostFrameJobLaunch() {
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec_postframes.xml"));
        jobLauncher.launch(spec);

        String jobId = spec.getJobs().get(0).detail.id;
        String postJobId = spec.getJobs().get(0).getPostJob().detail.id;

        assertEquals(JobState.PENDING, jobDao.getJobDetail(jobId).state);
        assertTrue(jobManager.shutdownJob(jobManager.getJob(jobId)));
        assertEquals(JobState.FINISHED, jobDao.getJobDetail(jobId).state);
        assertEquals(JobState.PENDING, jobDao.getJobDetail(postJobId).state);
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testReorderLayerFirst() {

        JobDetail job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_2");

        jobManager.reorderLayer(layer, new FrameSet("5-10"), Order.FIRST);

        assertEquals(-6, frameDao.findFrameDetail(job, "0005-pass_2").dispatchOrder);
        assertEquals(-5, frameDao.findFrameDetail(job, "0006-pass_2").dispatchOrder);
        assertEquals(-4, frameDao.findFrameDetail(job, "0007-pass_2").dispatchOrder);
        assertEquals(-3, frameDao.findFrameDetail(job, "0008-pass_2").dispatchOrder);
        assertEquals(-2, frameDao.findFrameDetail(job, "0009-pass_2").dispatchOrder);
        assertEquals(-1, frameDao.findFrameDetail(job, "0010-pass_2").dispatchOrder);
        assertEquals(3, frameDao.findFrameDetail(job, "0004-pass_2").dispatchOrder);
        assertEquals(2, frameDao.findFrameDetail(job, "0003-pass_2").dispatchOrder);
        assertEquals(1, frameDao.findFrameDetail(job, "0002-pass_2").dispatchOrder);
        assertEquals(0, frameDao.findFrameDetail(job, "0001-pass_2").dispatchOrder);

        DispatchHost host = createHost();
        jobManager.setJobPaused(job, false);

        String[] order = new String[] {
                "0005-pass_2","0006-pass_2","0007-pass_2","0008-pass_2",
                "0009-pass_2","0010-pass_2","0001-pass_1","0001-pass_2"
        };

        for (String f: order) {
            DispatchFrame frame =  dispatcherDao.findNextDispatchFrame(job, host);
            frameDao.updateFrameState(frame, FrameState.SUCCEEDED);
            assertEquals(f, frame.getName());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReorderLayerLast() {

        JobDetail job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        jobManager.reorderLayer(layer, new FrameSet("1-5"), Order.LAST);

        assertEquals(11, frameDao.findFrameDetail(job, "0001-pass_1").dispatchOrder);
        assertEquals(12, frameDao.findFrameDetail(job, "0002-pass_1").dispatchOrder);
        assertEquals(13, frameDao.findFrameDetail(job, "0003-pass_1").dispatchOrder);
        assertEquals(14, frameDao.findFrameDetail(job, "0004-pass_1").dispatchOrder);
        assertEquals(15, frameDao.findFrameDetail(job, "0005-pass_1").dispatchOrder);

        DispatchHost host = createHost();
        jobManager.setJobPaused(job, false);

        String[] order = new String[] {
                "0001-pass_2","0002-pass_2","0003-pass_2","0004-pass_2",
                "0005-pass_2","0006-pass_1","0006-pass_2","0007-pass_1"
        };

        for (String f: order) {
            DispatchFrame frame = dispatcherDao.findNextDispatchFrame(job, host);
            frameDao.updateFrameState(frame, FrameState.SUCCEEDED);
            assertEquals(f, frame.getName());
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testReorderLayerReverse() {

        JobDetail job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        jobManager.reorderLayer(layer, new FrameSet("1-5"), Order.REVERSE);

        assertEquals(0, frameDao.findFrameDetail(job, "0005-pass_1").dispatchOrder);
        assertEquals(1, frameDao.findFrameDetail(job, "0004-pass_1").dispatchOrder);
        assertEquals(2, frameDao.findFrameDetail(job, "0003-pass_1").dispatchOrder);
        assertEquals(3, frameDao.findFrameDetail(job, "0002-pass_1").dispatchOrder);
        assertEquals(4, frameDao.findFrameDetail(job, "0001-pass_1").dispatchOrder);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testStaggerLayer() {

        JobDetail job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");
        FrameSet staggeredFrameSet = new FrameSet("1-10:2");
        jobManager.staggerLayer(layer,"1-10",2);

        for (int i=0; i < staggeredFrameSet.size(); i++) {
            assertEquals(
                    staggeredFrameSet.get(i),
                    frameDao.findFrameDetail(
                            job, CueUtil.buildFrameName(layer, staggeredFrameSet.get(i))).number);
        }

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLayers() {
        JobDetail job = getJob1();
        jobManager.getLayerDetails(job);
        jobManager.getLayers(job);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void eatLayer() {
        JobInterface job = getJob1();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");
        FrameSearchInterface r = frameSearchFactory.create(layer);
        FrameSearchCriteria criteria = r.getCriteria();
        r.setCriteria(criteria.toBuilder()
                .setPage(1)
                .setLimit(5)
                .build());
        jobManagerSupport.eatFrames(r, new Source());

        assertTrue(
                frameDao.findFrameDetails(frameSearchFactory.create(layer))
                        .stream()
                        .allMatch(frame -> frame.state == FrameState.EATEN));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void optimizeLayer() {
        JobInterface job = getJob3();
        LayerDetail layer = layerDao.findLayerDetail(job, "pass_1");

        assertEquals(Dispatcher.MEM_RESERVED_DEFAULT, layer.minimumMemory);
        assertThat(layer.tags, contains("general"));

        /*
         * Make sure the layer is optimizable.
         */
        frameDao.findFrames(frameSearchFactory.create(layer))
                .stream()
                .limit(5)
                .forEach(frame -> frameDao.updateFrameState(frame, FrameState.SUCCEEDED));
        layerDao.updateUsage(layer, new ResourceUsage(100, 3500 * 5), 0);

        // Test to make sure our optimization
        jobManager.optimizeLayer(layer, 100, CueUtil.MB512, 120);

        assertEquals(
                CueUtil.MB512 + CueUtil.MB256,
                layerDao.findLayerDetail(job, "pass_1").minimumMemory);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsLayerThreadable() {
        JobInterface job = getJob3();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        assertFalse(jobManager.isLayerThreadable(layer));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLayer() {
        JobInterface job = getJob3();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");
        assertEquals(layer, jobManager.getLayer(layer.getId()));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testFindFrame() {
        JobInterface job = getJob3();
        LayerInterface layer = layerDao.findLayer(job, "pass_1");

        FrameInterface frame = jobManager.findFrame(layer, 1);
        assertEquals("0001-pass_1", frame.getName());
    }
}
