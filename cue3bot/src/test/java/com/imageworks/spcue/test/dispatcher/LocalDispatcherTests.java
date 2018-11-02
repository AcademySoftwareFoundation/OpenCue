
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



package com.imageworks.spcue.test.dispatcher;

import java.io.File;
import java.util.List;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.BookingDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.BookingManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@ContextConfiguration
public class LocalDispatcherTests extends TransactionalTest {

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    GroupManager groupManager;

    @Resource
    Dispatcher localDispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    FrameDao frameDao;

    @Resource
    BookingManager bookingManager;

    @Resource
    BookingDao bookingDao;

    private static final String HOSTNAME = "beta";

    private static final String JOBNAME =
        "pipe-dev.cue-testuser_shell_dispatch_test_v1";

    private static final String TARGET_JOB =
        "pipe-dev.cue-testuser_shell_dispatch_test_v2";

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    @Before
    public void setTestMode() {
        localDispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder()
                .setName(HOSTNAME)
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(0)
                .setTotalMcp(195430)
                .setTotalMem(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(400)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .addTags("test")
                .putAttributes("SP_OS", "Linux")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();

        hostManager.createHost(host,
                adminManager.findAllocationDetail("spi", "general"));
    }

    public JobDetail getJob() {
        return jobManager.findJobDetail(JOBNAME);
    }

    public JobDetail getTargetJob() {
        return jobManager.findJobDetail(TARGET_JOB);
    }

    public DispatchHost getHost() {
        return hostManager.findDispatchHost(HOSTNAME);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHostAutoDetectJob() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        LocalHostAssignment lja = new LocalHostAssignment();
        lja.setThreads(1);
        lja.setMaxMemory(CueUtil.GB8);
        lja.setMaxCoreUnits(200);
        bookingManager.createLocalHostAssignment(host, job, lja);

        List<VirtualProc> procs =  localDispatcher.dispatchHost(host);

        // Should have 2 procs.
        assertEquals(2, procs.size());
        assertTrue(bookingManager.hasActiveLocalFrames(host));

        /*
         * Check to ensure the procs are marked as local.
         */
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(0).getId()));

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(1).getId()));

        /*
         * Check to ensure the right job was booked.
         */
        assertEquals(job.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_job FROM proc WHERE pk_proc=?",
                String.class, procs.get(0).getId()));

        assertEquals(job.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_job FROM proc WHERE pk_proc=?",
                String.class, procs.get(1).getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHostAutoDetectLayer() {
        DispatchHost host = getHost();
        JobDetail job = getJob();
        LayerInterface layer = jobManager.getLayers(job).get(0);

        LocalHostAssignment lba = new LocalHostAssignment(300, 1, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(host, layer, lba);

        List<VirtualProc> procs =  localDispatcher.dispatchHost(host);

        // Should have 2 procs.
        assertEquals(3, procs.size());
        assertTrue(bookingManager.hasActiveLocalFrames(host));

        /*
         * Check that they are all marked local.
         */
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(0).getId()));

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(1).getId()));

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(2).getId()));

        /*
         * Check that they are all frame the same layer.
         */
        assertEquals(layer.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_layer FROM proc WHERE pk_proc=?",
                String.class, procs.get(0).getId()));

        assertEquals(layer.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_layer FROM proc WHERE pk_proc=?",
                String.class, procs.get(1).getId()));

        assertEquals(layer.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_layer FROM proc WHERE pk_proc=?",
                String.class, procs.get(2).getId()));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHostAutoDetectFrame() {
        DispatchHost host = getHost();
        JobDetail job = getJob();
        LayerInterface layer = jobManager.getLayers(job).get(0);
        FrameInterface frame = jobManager.findFrame(layer, 5);

        LocalHostAssignment lba = new LocalHostAssignment(200, 1, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(host, frame, lba);

        List<VirtualProc> procs =  localDispatcher.dispatchHost(host);

        /*
         * Should always be 1 or 0, in this case it should be 1.
         */
        assertEquals(1, procs.size());
        assertTrue(bookingManager.hasActiveLocalFrames(host));
        /*
         * Check the frame id.
         */
        assertEquals(frame.getFrameId(), jdbcTemplate.queryForObject(
                "SELECT pk_frame FROM proc WHERE pk_proc=?",
                String.class, procs.get(0).getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHostToLocalJob() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        LocalHostAssignment lba = new LocalHostAssignment(200, 1, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(host, job, lba);

        List<VirtualProc> procs =  localDispatcher.dispatchHost(host, job);

        // Should have 2 procs.
        assertEquals(2, procs.size());
        assertTrue(bookingManager.hasActiveLocalFrames(host));

        // Check that they are local.
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(0).getId()));

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(1).getId()));

        /*
         * Check to ensure the right job was booked.
         */
        assertEquals(job.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_job FROM proc WHERE pk_proc=?",
                String.class, procs.get(0).getId()));

        assertEquals(job.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_job FROM proc WHERE pk_proc=?",
                String.class, procs.get(1).getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHostToLocalLayer() {
        DispatchHost host = getHost();
        JobDetail job = getJob();
        LayerInterface layer = jobManager.getLayers(job).get(0);

        LocalHostAssignment lba = new LocalHostAssignment(300, 1, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(host, layer, lba);

        List<VirtualProc> procs =  localDispatcher.dispatchHost(host, layer);

        // Should have 2 procs.
        assertEquals(3, procs.size());
        assertTrue(bookingManager.hasActiveLocalFrames(host));

        /*
         * Check that they are all marked local.
         */
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(0).getId()));

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(1).getId()));

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(2).getId()));

        /*
         * Check that they are all frame the same layer.
         */
        assertEquals(layer.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_layer FROM proc WHERE pk_proc=?",
                String.class, procs.get(0).getId()));

        assertEquals(layer.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_layer FROM proc WHERE pk_proc=?",
                String.class, procs.get(1).getId()));

        assertEquals(layer.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_layer FROM proc WHERE pk_proc=?",
                String.class, procs.get(2).getId()));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHostToLocalFrame() {
        DispatchHost host = getHost();
        JobDetail job = getJob();
        LayerInterface layer = jobManager.getLayers(job).get(0);
        FrameInterface frame = jobManager.findFrame(layer, 5);

        LocalHostAssignment lba = new LocalHostAssignment(200, 1, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(host, frame, lba);

        List<VirtualProc> procs =  localDispatcher.dispatchHost(host, frame);

        /*
         * Should always be 1 or 0 procs, in this case 1.
         */
        assertEquals(1, procs.size());
        assertTrue(bookingManager.hasActiveLocalFrames(host));
        /*
         * Check the frame id.
         */
        assertEquals(frame.getFrameId(), jdbcTemplate.queryForObject(
                "SELECT pk_frame FROM proc WHERE pk_proc=?",
                String.class, procs.get(0).getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHostToLocalFrameTwice() {
        DispatchHost host = getHost();
        JobDetail job = getJob();
        LayerInterface layer = jobManager.getLayers(job).get(0);
        FrameInterface frame = jobManager.findFrame(layer, 5);

        LocalHostAssignment lba = new LocalHostAssignment(200, 1, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(host, frame, lba);

        List<VirtualProc> procs =  localDispatcher.dispatchHost(host, frame);

        /*
         * Should always be 1 or 0 procs, in this case 1.
         */
        assertEquals(1, procs.size());

        /*
         * Dispatch again.
         */
        procs =  localDispatcher.dispatchHost(host, frame);

        /*
         * Should always be 1 or 0 procs, in this case 0.
         */
        assertEquals(0, procs.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHostToLocalJobDeficit() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        LocalHostAssignment lba = new LocalHostAssignment(800, 8, CueUtil.GB8, 1);
        bookingManager.createLocalHostAssignment(host, job, lba);

        List<VirtualProc> procs =  localDispatcher.dispatchHost(host, job);

        // Should have 1 proc.
        assertEquals(1, procs.size());
        assertTrue(bookingManager.hasActiveLocalFrames(host));

        // Check that they are local.
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_local FROM proc WHERE pk_proc=?",
                Boolean.class, procs.get(0).getId()));
        /*
         * Check to ensure the right job was booked.
         */
        assertEquals(job.getId(), jdbcTemplate.queryForObject(
                "SELECT pk_job FROM proc WHERE pk_proc=?",
                String.class, procs.get(0).getId()));

        /*
         * Now, lower our min cores to create a deficit.
         */
        assertFalse(bookingManager.hasResourceDeficit(host));
        bookingManager.setMaxResources(lba, 700, 0, 1);
        assertTrue(bookingManager.hasResourceDeficit(host));
    }
}

