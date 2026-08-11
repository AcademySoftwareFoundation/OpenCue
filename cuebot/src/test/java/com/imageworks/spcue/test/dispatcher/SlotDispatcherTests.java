
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

package com.imageworks.spcue.test.dispatcher;

import java.io.File;
import java.util.List;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.ResourceReservationFailureException;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

@ContextConfiguration
public class SlotDispatcherTests extends TransactionalTest {

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    HostDao hostDao;

    @Resource
    JobDao jobDao;

    @Resource
    ProcDao procDao;

    @Resource
    FrameDao frameDao;

    @Resource
    Dispatcher slotDispatcher;

    @Resource
    Dispatcher dispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    private static final String HOSTNAME = "slot_beta";

    private static final String SLOT_JOB = "pipe-dev.cue-testuser_slot_test_v1";

    private static final String HEAVY_SLOT_JOB = "pipe-dev.cue-testuser_slot_test_heavy";

    private static final String REGULAR_JOB = "pipe-dev.cue-testuser_shell_dispatch_test_v1";

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_slot_test.xml"));
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    @Before
    public void setTestMode() {
        slotDispatcher.setTestMode(true);
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(1).setCoresPerProc(100).addTags("test")
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .build();

        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));
    }

    private DispatchHost getSlotHost(int concurrentSlotsLimit) {
        DispatchHost host = hostManager.findDispatchHost(HOSTNAME);
        hostDao.updateConcurrentSlotsLimit(host, concurrentSlotsLimit);
        return hostManager.findDispatchHost(HOSTNAME);
    }

    private JobDetail getSlotJob() {
        return jobManager.findJobDetail(SLOT_JOB);
    }

    private JobDetail getHeavySlotJob() {
        return jobManager.findJobDetail(HEAVY_SLOT_JOB);
    }

    private JobDetail getRegularJob() {
        return jobManager.findJobDetail(REGULAR_JOB);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSlotHostFieldsMapped() {
        DispatchHost host = getSlotHost(4);
        assertTrue(host.isSlotHost());
        assertEquals(4, host.concurrentSlotsLimit);
        assertEquals(4, host.idleSlots);

        hostDao.updateConcurrentSlotsLimit(host, -1);
        DispatchHost regularHost = hostManager.findDispatchHost(HOSTNAME);
        assertFalse(regularHost.isSlotHost());
        assertEquals(-1, regularHost.idleSlots);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchSlotHostToJob() {
        DispatchHost host = getSlotHost(4);
        JobDetail job = getSlotJob();

        // job_frame_dispatch_max is 3 in the test properties, the host has 4 idle slots.
        List<VirtualProc> procs = slotDispatcher.dispatchHost(host, job);
        assertEquals(3, procs.size());

        for (VirtualProc proc : procs) {
            assertEquals(1, proc.slotsReserved);
            assertEquals(0, proc.coresReserved);
            assertEquals(0, proc.memoryReserved);
            assertEquals(0, proc.gpusReserved);

            VirtualProc stored = procDao.getVirtualProc(proc.getProcId());
            assertEquals(1, stored.slotsReserved);
            assertEquals(0, stored.coresReserved);

            FrameDetail frame = frameDao.getFrameDetail(proc.getFrameId());
            assertEquals(FrameState.RUNNING, frame.state);
        }

        // In-memory accounting was decremented and the database derives the same value
        // from SUM(proc.int_slots_reserved).
        assertEquals(1, host.idleSlots);
        assertEquals(1, hostManager.findDispatchHost(HOSTNAME).idleSlots);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchSlotHostCapsAtIdleSlots() {
        DispatchHost host = getSlotHost(2);
        JobDetail job = getSlotJob();

        List<VirtualProc> procs = slotDispatcher.dispatchHost(host, job);
        assertEquals(2, procs.size());
        assertEquals(0, host.idleSlots);

        // The host is full; another dispatch books nothing.
        DispatchHost fullHost = hostManager.findDispatchHost(HOSTNAME);
        assertEquals(0, fullHost.idleSlots);
        assertEquals(0, slotDispatcher.dispatchHost(fullHost, job).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHeavySlotFrames() {
        DispatchHost host = getSlotHost(4);
        JobDetail job = getHeavySlotJob();

        // Each frame requires 3 slots; only one fits in 4.
        List<VirtualProc> procs = slotDispatcher.dispatchHost(host, job);
        assertEquals(1, procs.size());
        assertEquals(3, procs.get(0).slotsReserved);
        assertEquals(1, host.idleSlots);

        // A second frame (3 slots) no longer fits the remaining 1 slot.
        DispatchHost refreshed = hostManager.findDispatchHost(HOSTNAME);
        assertEquals(1, refreshed.idleSlots);
        assertEquals(0, slotDispatcher.dispatchHost(refreshed, job).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchSlotHost() {
        DispatchHost host = getSlotHost(4);

        // The full host dispatch finds slot jobs on its own; the regular job is
        // never considered.
        List<VirtualProc> procs = slotDispatcher.dispatchHost(host);
        assertTrue(procs.size() > 0);
        for (VirtualProc proc : procs) {
            assertTrue(proc.slotsReserved > 0);
            assertEquals(0, proc.coresReserved);
            assertFalse(getRegularJob().getJobId().equals(proc.getJobId()));
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSlotHostDoesNotBookRegularJob() {
        DispatchHost host = getSlotHost(4);
        JobDetail regularJob = getRegularJob();

        // Strict pairing: a slot host never runs a regular (cores/memory) layer.
        assertEquals(0, slotDispatcher.dispatchHost(host, regularJob).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testRegularHostDoesNotBookSlotJob() {
        // The host stays a regular host (no slot limit).
        DispatchHost host = hostManager.findDispatchHost(HOSTNAME);
        JobDetail slotJob = getSlotJob();

        // Strict pairing: the generic dispatcher never books slot-based layers.
        assertEquals(0, dispatcher.dispatchHost(host, slotJob).size());

        // And the generic full-host dispatch only books the regular job.
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        for (VirtualProc proc : procs) {
            assertEquals(0, proc.slotsReserved);
            assertFalse(getSlotJob().getJobId().equals(proc.getJobId()));
            assertFalse(getHeavySlotJob().getJobId().equals(proc.getJobId()));
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobMaxSlotsCap() {
        DispatchHost host = getSlotHost(4);
        JobDetail job = getSlotJob();

        jobDao.updateMaxSlots(job, 2);
        List<VirtualProc> procs = slotDispatcher.dispatchHost(host, job);
        assertEquals(2, procs.size());

        // The job is at its cap; nothing else books.
        DispatchHost refreshed = hostManager.findDispatchHost(HOSTNAME);
        assertEquals(0, slotDispatcher.dispatchHost(refreshed, job).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testJobMaxSlotsRejectAll() {
        DispatchHost host = getSlotHost(4);
        JobDetail job = getSlotJob();

        jobDao.updateMaxSlots(job, 0);
        assertEquals(0, slotDispatcher.dispatchHost(host, job).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFolderMaxSlotsCap() {
        DispatchHost host = getSlotHost(4);
        JobDetail job = getSlotJob();

        jdbcTemplate.update("UPDATE folder_resource SET int_max_slots=2 WHERE "
                + "pk_folder=(SELECT pk_folder FROM job WHERE pk_job=?)", job.getJobId());

        List<VirtualProc> procs = slotDispatcher.dispatchHost(host, job);
        assertEquals(2, procs.size());

        DispatchHost refreshed = hostManager.findDispatchHost(HOSTNAME);
        assertEquals(0, slotDispatcher.dispatchHost(refreshed, job).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSubscriptionMaxSlotsCap() {
        DispatchHost host = getSlotHost(4);
        JobDetail job = getSlotJob();

        jdbcTemplate.update(
                "UPDATE subscription SET int_max_slots=2 WHERE "
                        + "pk_show=(SELECT pk_show FROM job WHERE pk_job=?) AND pk_alloc=?",
                job.getJobId(), host.getAllocationId());

        List<VirtualProc> procs = slotDispatcher.dispatchHost(host, job);
        assertEquals(2, procs.size());

        DispatchHost refreshed = hostManager.findDispatchHost(HOSTNAME);
        assertEquals(0, slotDispatcher.dispatchHost(refreshed, job).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testTriggerRejectsBookingOverHostCap() {
        DispatchHost host = getSlotHost(1);
        JobDetail job = getSlotJob();

        List<DispatchFrame> frames = dispatchSupport.findNextSlotDispatchFrames(job, host, 10);
        assertTrue(frames.size() >= 2);

        slotDispatcher.dispatch(frames.get(0), VirtualProc.buildSlotProc(host, frames.get(0)));

        /*
         * The host cap is spent; a direct insert bypassing the dispatcher's in-memory accounting
         * must be rejected by the before_insert_proc trigger. The raised database exception aborts
         * the test transaction, so this is the last operation of the test.
         */
        VirtualProc over = VirtualProc.buildSlotProc(host, frames.get(1));
        over.frameId = frames.get(1).getFrameId();
        try {
            procDao.insertVirtualProc(over);
            fail("Expected the before_insert_proc trigger to reject booking over the host cap.");
        } catch (ResourceReservationFailureException expected) {
            // Expected: host is at its concurrent slots limit.
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnbookSlotProcReturnsSlots() {
        DispatchHost host = getSlotHost(2);
        JobDetail job = getSlotJob();

        List<VirtualProc> procs = slotDispatcher.dispatchHost(host, job);
        assertEquals(2, procs.size());
        assertEquals(0, hostManager.findDispatchHost(HOSTNAME).idleSlots);

        dispatchSupport.unbookProc(procs.get(0));
        assertEquals(1, hostManager.findDispatchHost(HOSTNAME).idleSlots);
    }
}
