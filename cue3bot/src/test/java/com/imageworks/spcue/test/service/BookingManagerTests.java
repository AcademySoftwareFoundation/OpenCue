
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
import java.util.ArrayList;
import java.util.HashMap;

import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.Frame;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.CueIce.RenderPartitionType;
import com.imageworks.spcue.dao.BookingDao;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.ResourceReservationFailureException;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.iceclient.RqdClient;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.BookingManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.CueUtil;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class BookingManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    @Resource
    HostDao hostDao;

    @Resource
    BookingDao bookingDao;

    @Resource
    DispatcherDao dispatcherDao;

    @Resource
    ProcDao procDao;

    @Resource
    BookingManager bookingManager;

    @Resource
    Dispatcher localDispatcher;

    @Resource
    RqdClient rqdClient;

    @Resource
    Whiteboard whiteboard;


    @Before
    public void setTestMode() {
        localDispatcher.setTestMode(true);
        rqdClient.setTestMode(true);
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
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();

        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh,
                adminManager.findAllocationDetail("spi", "general"));

        return dh;
    }

    public JobDetail launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail d = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        jobManager.setJobPaused(d, false);
        return d;
    }

    public JobDetail launchJob2() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        JobDetail d = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");
        jobManager.setJobPaused(d, false);
        return d;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createLocalHostAssignment() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment l1 = new LocalHostAssignment();
        l1.setMaxCoreUnits(200);
        l1.setMaxMemory(CueUtil.GB4);
        l1.setThreads(2);

        bookingManager.createLocalHostAssignment(h, j, l1);
        LocalHostAssignment l2 = bookingManager.getLocalHostAssignment(h.getHostId(),
                                                                       j.getJobId());

        assertEquals(l1.id, l2.id);
        assertEquals(l1.getFrameId(), l2.getFrameId());
        assertEquals(l1.getLayerId(), l2.getLayerId());
        assertEquals(l1.getJobId(), l2.getJobId());
        assertEquals(l1.getIdleCoreUnits(), l2.getIdleCoreUnits());
        assertEquals(l1.getMaxCoreUnits(), l2.getMaxCoreUnits());
        assertEquals(l1.getThreads(), l2.getThreads());
        assertEquals(l1.getIdleMemory(), l2.getIdleMemory());
        assertEquals(l1.getMaxMemory(), l2.getMaxMemory());
        assertFalse(bookingManager.hasActiveLocalFrames(h));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void hasLocalHostAssignment() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment l1 = new LocalHostAssignment();
        l1.setMaxCoreUnits(200);
        l1.setMaxMemory(CueUtil.GB4);
        l1.setThreads(2);

        assertFalse(bookingManager.hasLocalHostAssignment(h));

        bookingManager.createLocalHostAssignment(h, j, l1);
        assertTrue(bookingManager.hasLocalHostAssignment(h));

        bookingManager.removeLocalHostAssignment(l1);
        assertFalse(bookingManager.hasLocalHostAssignment(h));

        assertFalse(bookingManager.hasActiveLocalFrames(h));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void hasActiveLocalFrames() {
        // See LocalDispatcherTests
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createLocalHostAssignmentForJob() {

        DispatchHost h = createHost();
        JobDetail job = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);

        bookingManager.createLocalHostAssignment(h, job, lja);

        assertNotNull(lja.getJobId());
        assertEquals(job.getJobId(), lja.getJobId());
        assertEquals(RenderPartitionType.JobPartition, lja.getType());
        assertFalse(bookingManager.hasActiveLocalFrames(h));

        whiteboard.getRenderPartition(lja);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createLocalHostAssignmentForLayer() {

        DispatchHost h = createHost();
        JobDetail job = launchJob2();
        Layer layer = jobManager.getLayers(job).get(0);

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB8);
        lja.setThreads(1);

        bookingManager.createLocalHostAssignment(h, layer, lja);

        assertNotNull(layer.getLayerId());
        assertEquals(layer.getLayerId(), lja.getLayerId());
        assertEquals(RenderPartitionType.LayerPartition, lja.getType());
        assertFalse(bookingManager.hasActiveLocalFrames(h));

        whiteboard.getRenderPartition(lja);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createLocalHostAssignmentForFrame() {

        DispatchHost h = createHost();
        JobDetail job = launchJob2();
        Layer layer = jobManager.getLayers(job).get(0);
        Frame frame = jobManager.findFrame(layer, 5);

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB8);
        lja.setThreads(1);

        bookingManager.createLocalHostAssignment(h, frame, lja);

        assertNotNull(frame.getFrameId());
        assertEquals(frame.getFrameId(), lja.getFrameId());
        assertEquals(RenderPartitionType.FramePartition, lja.getType());
        assertFalse(bookingManager.hasActiveLocalFrames(h));

        whiteboard.getRenderPartition(lja);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void deactivateLocalHostAssignment() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);

        bookingManager.createLocalHostAssignment(h, j, lja);
        bookingManager.deactivateLocalHostAssignment(lja);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void setMaxResources() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);

        bookingManager.createLocalHostAssignment(h, j, lja);

        /*
         * Lower the cores.
         */
        bookingManager.setMaxResources(lja, 100, CueUtil.GB2, CueUtil.MB256);

        LocalHostAssignment l2 = bookingManager.getLocalHostAssignment(lja.id);

        assertEquals(100, l2.getMaxCoreUnits());
        assertEquals(CueUtil.GB2, l2.getMaxMemory());
        assertEquals(CueUtil.MB256, l2.getMaxGpu());

        /*
         * Raise the values.
         */
        bookingManager.setMaxResources(lja, 200, CueUtil.GB4, CueUtil.MB512);

        l2 = bookingManager.getLocalHostAssignment(lja.id);
        assertEquals(200, l2.getMaxCoreUnits());
        assertEquals(CueUtil.GB4, l2.getMaxMemory());
        assertEquals(CueUtil.MB512, l2.getMaxGpu());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void setIllegalMaxResources() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_cores_idle FROM host WHERE pk_host=?",
                Integer.class, h.getId()));

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setMaxGpu(CueUtil.MB512);
        lja.setThreads(2);

        bookingManager.createLocalHostAssignment(h, j, lja);

        /*
         * Raise the cores too high
         */
        bookingManager.setMaxResources(lja, 800, CueUtil.GB2, 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void removeLocalHostAssignment() {

        DispatchHost h = createHost();
        JobDetail j = launchJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setMaxCoreUnits(200);
        lja.setMaxMemory(CueUtil.GB4);
        lja.setThreads(2);

        bookingManager.createLocalHostAssignment(h, j, lja);
        assertFalse(bookingManager.hasActiveLocalFrames(h));

        /*
         * Now remove the local host assignment.
         */
        bookingManager.removeLocalHostAssignment(lja);

        /*
         * Ensure its gone.
         */
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM host_local WHERE pk_host_local = ?",
                Integer.class, lja.getId()));

        /*
         * Ensure the cores are back on the host.
         */
        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_cores_idle FROM host WHERE pk_host= ?",
                Integer.class, h.getId()));
    }
}

