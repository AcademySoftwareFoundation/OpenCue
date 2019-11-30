
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



package com.imageworks.spcue.test.dao.postgres;

import java.io.File;
import java.util.List;
import java.util.Set;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.BookingDao;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class DispatcherDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    DispatcherDao dispatcherDao;

    @Resource
    HostDao hostDao;

    @Resource
    ProcDao procDao;

    @Resource
    LayerDao layerDao;

    @Resource
    JobDao jobDao;

    @Resource
    AllocationDao allocationDao;

    @Resource
    JobManager jobManager;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    GroupManager groupManager;

    @Resource
    Dispatcher dispatcher;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    BookingDao bookingDao;

    private static final String HOSTNAME="beta";

    public DispatchHost getHost() {
        return hostDao.findDispatchHost(HOSTNAME);
    }

    public JobDetail getJob1() {
        return jobManager.findJobDetail(
                "pipe-dev.cue-testuser_shell_dispatch_test_v1");
    }

    public JobDetail getJob2() {
        return jobManager.findJobDetail(
                "pipe-dev.cue-testuser_shell_dispatch_test_v2");
    }

    @Before
    public void launchJob() {
        dispatcher.setTestMode(true);
        jobLauncher.testMode = true;
        jobLauncher.launch(
                new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder()
                .setName(HOSTNAME)
                .setBootTime(1192369572)
                .setFreeScratch(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalScratch(195430)
                .setTotalMem(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags("test")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .build();

        hostManager.createHost(host,
                adminManager.findAllocationDetail("spi", "general"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindNextDispatchFrameByHost() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();

        for (LayerDetail layer: layerDao.getLayerDetails(job)) {
            assertTrue(layer.tags.contains("general"));
        }

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT str_tags FROM host WHERE pk_host=?",String.class,
                host.id).contains("general"));

        DispatchFrame frame =  dispatcherDao.findNextDispatchFrame(job, host);
        assertNotNull(frame);
        assertEquals(frame.name, "0001-pass_1");
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testFindNextDispatchFrameByProc() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();

        // TODO: fix the fact you can book the same proc on multiple frames
        //  probably just need to make sure you can't update a proc's frame
        //  assignment unless the frame id is null.

        DispatchFrame frame =  dispatcherDao.findNextDispatchFrame(job, host);
        assertNotNull(frame);
        assertEquals("0001-pass_1", frame.name);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.coresReserved = 100;
        dispatcher.dispatch(frame, proc);

        frame =  dispatcherDao.findNextDispatchFrame(job, proc);
        assertNotNull(frame);
        assertEquals("0001-pass_2", frame.name);
        dispatcher.dispatch(frame, proc);

        frame =  dispatcherDao.findNextDispatchFrame(job, proc);
        assertNotNull(frame);
        assertEquals("0002-pass_1", frame.name);
        dispatcher.dispatch(frame, proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindNextDispatchFramesByProc() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();

        // TODO: fix the fact you can book the same proc on multiple frames
        //  probably just need to make sure you can't update a proc's frame
        //  assignment unless the frame id is null.

        List<DispatchFrame> frames =
            dispatcherDao.findNextDispatchFrames(job, host,10);
        assertEquals(10, frames.size());

        DispatchFrame frame = frames.get(0);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.coresReserved = 100;
        dispatcher.dispatch(frame, proc);

        frame =  dispatcherDao.findNextDispatchFrame(job, proc);
        assertNotNull(frame);
        assertEquals(frame.name,"0001-pass_2");
        dispatcher.dispatch(frame, proc);

        frame =  dispatcherDao.findNextDispatchFrame(job, proc);
        assertNotNull(frame);
        assertEquals(frame.name,"0002-pass_1");
        dispatcher.dispatch(frame, proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindNextDispatchFramesByHostAndJobLocal() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        host.isLocalDispatch = true;
        List<DispatchFrame> frames =
            dispatcherDao.findNextDispatchFrames(job, host, 10);
        assertEquals(10, frames.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindNextDispatchFramesByHostAndLayerLocal() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        LayerInterface layer = jobManager.getLayers(job).get(0);
        host.isLocalDispatch = true;

        List<DispatchFrame> frames =
            dispatcherDao.findNextDispatchFrames(layer, host, 10);
        assertEquals(10, frames.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindNextDispatchFramesByProcAndJobLocal() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        host.isLocalDispatch = true;
        List<DispatchFrame> frames =
            dispatcherDao.findNextDispatchFrames(job, host, 10);
        assertEquals(10, frames.size());

        DispatchFrame frame = frames.get(0);
        VirtualProc proc = VirtualProc.build(host, frame);
        proc.coresReserved = 100;
        proc.isLocalDispatch = true;

        frames = dispatcherDao.findNextDispatchFrames(job, proc, 10);
        assertEquals(10, frames.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindNextDispatchFramesByProcAndLayerLocal() {
        DispatchHost host = getHost();
        JobDetail job = getJob1();
        LayerInterface layer = jobManager.getLayers(job).get(0);
        host.isLocalDispatch = true;

        List<DispatchFrame> frames =
            dispatcherDao.findNextDispatchFrames(layer, host, 10);
        assertEquals(10, frames.size());

        DispatchFrame frame = frames.get(0);
        VirtualProc proc = VirtualProc.build(host, frame);
        proc.coresReserved = 100;
        proc.isLocalDispatch = true;

        frames = dispatcherDao.findNextDispatchFrames(layer, proc, 10);
        assertEquals(10, frames.size());
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testFindDispatchJobs() {
        DispatchHost host = getHost();

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM job WHERE str_state='PENDING'", Integer.class) > 0);

        Set<String> jobs = dispatcherDao.findDispatchJobs(host, 10);
        assertTrue(jobs.size() > 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindDispatchJobsByGroup() {
        DispatchHost host = getHost();
        final JobDetail job = getJob1();

        assertNotNull(job);
        assertNotNull(job.groupId);

        Set<String> jobs = dispatcherDao.findDispatchJobs(host,
                groupManager.getGroupDetail(job));
        assertTrue(jobs.size() > 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindDispatchJobsByShow() {
        DispatchHost host = getHost();
        final JobDetail job = getJob1();
        assertNotNull(job);

        Set<String> jobs = dispatcherDao.findDispatchJobs(host,
                adminManager.findShowEntity("pipe"), 5);
        assertTrue(jobs.size() > 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindDispatchJobsByLocal() {
        DispatchHost host = getHost();
        final JobDetail job = getJob1();
        assertNotNull(job);

        Set<String> jobs = dispatcherDao.findLocalDispatchJobs(host);
        assertEquals(0, jobs.size());

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setThreads(1);
        lja.setMaxMemory(CueUtil.GB16);
        lja.setMaxCoreUnits(200);
        lja.setMaxGpu(1);
        bookingDao.insertLocalHostAssignment(host, job, lja);

        jobs = dispatcherDao.findLocalDispatchJobs(host);
        assertTrue(jobs.size() > 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testfindUnderProcedJob() {
        DispatchHost host = getHost();
        JobDetail job1 = getJob1();
        JobDetail job2 = getJob2();

        jobDao.updateMinCores(job1, 0);
        jobDao.updateMinCores(job2, 1000);

        DispatchFrame frame = dispatcherDao.findNextDispatchFrame(job1, host);
        assertNotNull(frame);

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?",
                String.class, job1.id));

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject(
                "SELECT str_state FROM job WHERE pk_job=?",
                String.class, job2.id));

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.coresReserved = 100;
        dispatcher.dispatch(frame, proc);

        boolean under = dispatcherDao.findUnderProcedJob(job1, proc);
        assertTrue(under);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHigherPriorityJobExistsTrue() {
        DispatchHost host = getHost();
        JobDetail job1 = getJob1();
        JobDetail job2 = getJob2();
        job1.priority = 100;
        job2.priority = 200;

        jobDao.updateMinCores(job1, 0);
        jobDao.updateMinCores(job2, 0);
        jobDao.updatePriority(job1, 100);
        jobDao.updatePriority(job2, 200);

        DispatchFrame frame = dispatcherDao.findNextDispatchFrame(job1, host);
        assertNotNull(frame);

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject(
                        "SELECT str_state FROM job WHERE pk_job=?",
                        String.class, job1.id));

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject(
                        "SELECT str_state FROM job WHERE pk_job=?",
                        String.class, job2.id));

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.coresReserved = 100;
        dispatcher.dispatch(frame, proc);

        boolean isHigher = dispatcherDao.higherPriorityJobExists(job1, proc);
        assertTrue(isHigher);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHigherPriorityJobExistsFalse() {
        DispatchHost host = getHost();
        JobDetail job1 = getJob1();
        JobDetail job2 = getJob2();
        job1.priority = 20000;
        job2.priority = 100;

        jobDao.updatePriority(job1, 20000);
        jobDao.updatePriority(job2, 100);

        DispatchFrame frame = dispatcherDao.findNextDispatchFrame(job1, host);
        assertNotNull(frame);

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject(
                        "SELECT str_state FROM job WHERE pk_job=?",
                        String.class, job1.id));

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject(
                        "SELECT str_state FROM job WHERE pk_job=?",
                        String.class, job2.id));

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.coresReserved = 100;
        dispatcher.dispatch(frame, proc);

        boolean isHigher = dispatcherDao.higherPriorityJobExists(job1, proc);
        assertFalse(isHigher);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHigherPriorityJobExistsMaxProcBound() {
        DispatchHost host = getHost();
        JobDetail job1 = getJob1();
        JobDetail job2 = getJob2();
        job1.priority = 100;
        job2.priority = 200;

        jobDao.updateMaxCores(job2, 0);
        jobDao.updatePriority(job1, 100);
        jobDao.updatePriority(job2, 200);

        DispatchFrame frame = dispatcherDao.findNextDispatchFrame(job1, host);
        assertNotNull(frame);

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject(
                        "SELECT str_state FROM job WHERE pk_job=?",
                        String.class, job1.id));

        assertEquals(JobState.PENDING.toString(),
                jdbcTemplate.queryForObject(
                        "SELECT str_state FROM job WHERE pk_job=?",
                        String.class, job2.id));

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.coresReserved = 100;
        dispatcher.dispatch(frame, proc);

        boolean isHigher = dispatcherDao.higherPriorityJobExists(job1, proc);
        assertFalse(isHigher);
    }
}
