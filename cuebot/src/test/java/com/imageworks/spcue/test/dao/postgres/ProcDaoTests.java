
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

package com.imageworks.spcue.test.dao.postgres;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import javax.annotation.Resource;

import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.Environment;
import org.springframework.core.env.MapPropertySource;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.criteria.Direction;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.ProcSearchFactory;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.dao.criteria.Sort;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.ResourceReservationFailureException;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.ProcSearchCriteria;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class ProcDaoTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Autowired
    private Environment env;

    @Autowired
    private ConfigurableEnvironment springEnv;

    @Resource
    ProcDao procDao;

    @Resource
    HostDao hostDao;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    FrameDao frameDao;

    @Resource
    LayerDao layerDao;

    @Resource
    DispatcherDao dispatcherDao;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    ShowDao showDao;

    @Resource
    Dispatcher dispatcher;

    @Resource
    FrameSearchFactory frameSearchFactory;

    @Resource
    ProcSearchFactory procSearchFactory;

    private static String PK_ALLOC = "00000000-0000-0000-0000-000000000000";

    /**
     * Name of the test-scoped property source that flips dispatcher.scheduler_manages_resources;
     * added per-test and always removed in an @After hook so it cannot leak into other tests.
     */
    private static final String SCHEDULER_MANAGES_PROPS = "procDaoTestsSchedulerManages";

    private long MEM_RESERVED_DEFAULT;
    private long MEM_GPU_RESERVED_DEFAULT;

    public DispatchHost createHost() {

        RenderHost host = RenderHost.newBuilder().setName("beta").setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem((int) CueUtil.GB32).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(8).setCoresPerProc(100)
                .setState(HardwareState.UP).setFacility("spi").build();

        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh, adminManager.findAllocationDetail("spi", "general"));

        return hostDao.findDispatchHost("beta");
    }

    public JobDetail launchJob() {
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
    }

    @Before
    public void setDispatcherTestMode() {
        dispatcher.setTestMode(true);
        jobLauncher.testMode = true;
        this.MEM_RESERVED_DEFAULT =
                env.getRequiredProperty("dispatcher.memory.mem_reserved_default", Long.class);
        this.MEM_GPU_RESERVED_DEFAULT =
                env.getRequiredProperty("dispatcher.memory.mem_gpu_reserved_default", Long.class);
    }

    @After
    public void resetSchedulerManagedCache() {
        // @Rollback rolls back the DB row but leaves the in-process Guava cache populated; clear
        // it so the next test reads the (rolled-back) value from the DB instead of stale cache.
        showDao.invalidateSchedulerManagedCache();
    }

    @After
    public void removeSchedulerManagesPropertyOverride() {
        // Idempotent: only tests that injected the override actually have one to remove.
        springEnv.getPropertySources().remove(SCHEDULER_MANAGES_PROPS);
    }

    /** Injects dispatcher.scheduler_manages_resources=true for the current test only. */
    private void enableExternalSchedulerAccounting() {
        springEnv.getPropertySources().addFirst(new MapPropertySource(SCHEDULER_MANAGES_PROPS,
                Collections.singletonMap("dispatcher.scheduler_manages_resources", Boolean.TRUE)));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDontVerifyRunningProc() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail fd = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(fd.getId());
        VirtualProc proc = VirtualProc.build(host, frame);
        dispatcher.dispatch(frame, proc);

        // Confirm was have a running frame.
        assertEquals("RUNNING", jdbcTemplate.queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame=?", String.class, frame.id));

        assertTrue(procDao.verifyRunningProc(proc.getId(), frame.getId()));
        jobManager.shutdownJob(job);

        int result = jdbcTemplate.update("UPDATE job SET ts_stopped = "
                + "current_timestamp - interval '10' minute " + "WHERE pk_job=?", job.id);

        assertEquals(1, result);
        assertFalse(procDao.verifyRunningProc(proc.getId(), frame.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertVirtualProc() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteVirtualProc() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        procDao.deleteVirtualProc(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClearVirtualProcAssignment() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        procDao.clearVirtualProcAssignment(proc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testClearVirtualProcAssignmentByFrame() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        assertTrue(procDao.clearVirtualProcAssignment(frame));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateVirtualProcAssignment() {

        DispatchHost host = createHost();

        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame1.id;
        proc.layerId = frame1.layerId;
        proc.showId = frame1.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame1.getId());

        proc.frameId = frame2.id;

        procDao.updateVirtualProcAssignment(proc);
        procDao.verifyRunningProc(proc.getId(), frame2.getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testVerifyRunningProcAfterReassignment() {
        // Pins the proc-reuse semantics that strict fencing relies on: a proc id is retained when a
        // host picks up its next frame, so verifyRunningProc must report the proc as owning only
        // its
        // *current* frame, not the previous one.
        DispatchHost host = createHost();

        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame1.id;
        proc.layerId = frame1.layerId;
        proc.showId = frame1.showId;

        procDao.insertVirtualProc(proc);
        assertTrue(procDao.verifyRunningProc(proc.getId(), frame1.getId()));
        assertFalse(procDao.verifyRunningProc(proc.getId(), frame2.getId()));

        proc.frameId = frame2.id;
        procDao.updateVirtualProcAssignment(proc);

        // After reuse the proc owns frame2; a stale report referencing frame1 is no longer
        // verified.
        assertFalse(procDao.verifyRunningProc(proc.getId(), frame1.getId()));
        assertTrue(procDao.verifyRunningProc(proc.getId(), frame2.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateProcMemoryUsage() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);
        procDao.verifyRunningProc(proc.getId(), frame.getId());
        byte[] children = new byte[100];

        procDao.updateProcMemoryUsage(frame, 100, 100, 100, 100, 1000, 1000, 0, 0, 0, children);

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetVirtualProc() {
        DispatchHost host = createHost();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM host WHERE pk_host=?", Integer.class, host.id));

        JobDetail job = launchJob();
        FrameDetail fd = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");

        DispatchFrame frame = frameDao.getDispatchFrame(fd.getId());
        VirtualProc proc = VirtualProc.build(host, frame);
        dispatcher.dispatch(frame, proc);

        assertTrue(procDao.verifyRunningProc(proc.getId(), frame.getId()));

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM proc WHERE pk_proc=?", Integer.class, proc.id));

        VirtualProc verifyProc = procDao.getVirtualProc(proc.getId());
        assertEquals(host.allocationId, verifyProc.allocationId);
        assertEquals(proc.coresReserved, verifyProc.coresReserved);
        assertEquals(proc.frameId, verifyProc.frameId);
        assertEquals(proc.hostId, verifyProc.hostId);
        assertEquals(proc.id, verifyProc.id);
        assertEquals(proc.jobId, verifyProc.jobId);
        assertEquals(proc.layerId, verifyProc.layerId);
        assertEquals(proc.showId, verifyProc.showId);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindVirtualProc() {

        DispatchHost host = createHost();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM host WHERE pk_host=?", Integer.class, host.id));

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        procDao.findVirtualProc(frame);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindVirtualProcs() {

        DispatchHost host = createHost();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM host WHERE pk_host=?", Integer.class, host.id));

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        assertEquals(1, procDao.findVirtualProcs(HardwareState.UP).size());
        assertEquals(1, procDao.findVirtualProcs(host).size());
        assertEquals(1, procDao.findVirtualProcs(job).size());
        assertEquals(1, procDao.findVirtualProcs(frame).size());
        assertEquals(1, procDao.findVirtualProcs(frameSearchFactory.create(job)).size());
        assertEquals(1,
                procDao.findVirtualProcs(frameSearchFactory.create((LayerInterface) frame)).size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindOrphanedVirtualProcs() {
        DispatchHost host = createHost();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM host WHERE pk_host=?", Integer.class, host.id));

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        assertEquals(0, procDao.findOrphanedVirtualProcs().size());

        /**
         * This is destructive to running jobs
         */
        jdbcTemplate.update("UPDATE proc SET ts_ping = (current_timestamp - interval '30' day)");

        assertEquals(1, procDao.findOrphanedVirtualProcs().size());
        assertTrue(procDao.isOrphan(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsPingOlderThan() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        assertFalse(procDao.isPingOlderThan(proc, 3600000L));

        jdbcTemplate.update("UPDATE proc SET ts_ping = (current_timestamp - interval '2' hour)");

        assertTrue(procDao.isPingOlderThan(proc, 3600000L));
        // Still younger than a 3-hour bound.
        assertFalse(procDao.isPingOlderThan(proc, 10800000L));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsHostRebootedSinceDispatch() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        // Host booted before the proc was dispatched: no proof the render is dead.
        assertFalse(procDao.isHostRebootedSinceDispatch(proc));

        // A boot only slightly after dispatch stays within the clock-skew safety margin.
        jdbcTemplate.update(
                "UPDATE host_stat SET ts_booted = (current_timestamp + interval '1' minute) "
                        + "WHERE pk_host = ?",
                host.id);
        assertFalse(procDao.isHostRebootedSinceDispatch(proc));

        // A boot well after dispatch proves the render died with the reboot.
        jdbcTemplate
                .update("UPDATE host_stat SET ts_booted = (current_timestamp + interval '1' hour) "
                        + "WHERE pk_host = ?", host.id);
        assertTrue(procDao.isHostRebootedSinceDispatch(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnbookProc() {

        DispatchHost host = createHost();

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        procDao.unbookProc(proc);
        assertTrue(jdbcTemplate.queryForObject("SELECT b_unbooked FROM proc WHERE pk_proc=?",
                Boolean.class, proc.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnbookVirtualProcs() {

        DispatchHost host = createHost();

        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        List<VirtualProc> procs = new ArrayList<VirtualProc>();
        procs.add(proc);

        procDao.unbookVirtualProcs(procs);

        assertTrue(jdbcTemplate.queryForObject("SELECT b_unbooked FROM proc WHERE pk_proc=?",
                Boolean.class, proc.id));
    }

    @Test(expected = ResourceReservationFailureException.class)
    @Transactional
    @Rollback(true)
    public void testIncreaseReservedMemoryFail() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        procDao.increaseReservedMemory(proc, 8173264l * 8);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIncreaseReservedMemory() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = PK_ALLOC;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        procDao.insertVirtualProc(proc);

        procDao.increaseReservedMemory(proc, 3145728);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetReservedMemory() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        VirtualProc _proc = procDao.findVirtualProc(frame);
        assertEquals(Long.valueOf(this.MEM_RESERVED_DEFAULT), jdbcTemplate.queryForObject(
                "SELECT int_mem_reserved FROM proc WHERE pk_proc=?", Long.class, _proc.id));
        assertEquals(this.MEM_RESERVED_DEFAULT, procDao.getReservedMemory(_proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetReservedGpuMemory() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        VirtualProc _proc = procDao.findVirtualProc(frame);
        assertEquals(Long.valueOf(this.MEM_GPU_RESERVED_DEFAULT), jdbcTemplate.queryForObject(
                "SELECT int_gpu_mem_reserved FROM proc WHERE pk_proc=?", Long.class, _proc.id));
        assertEquals(this.MEM_GPU_RESERVED_DEFAULT, procDao.getReservedGpuMemory(_proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testBalanceUnderUtilizedProcs() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail1 = frameDao.findFrameDetail(job, "0001-pass_1");
        DispatchFrame frame1 = frameDao.getDispatchFrame(frameDetail1.id);

        VirtualProc proc1 = VirtualProc.build(host, frame1);
        proc1.frameId = frame1.id;
        procDao.insertVirtualProc(proc1);

        byte[] children = new byte[100];
        procDao.updateProcMemoryUsage(frame1, 250000, 250000, 250000, 250000, 250000, 250000, 0, 0,
                0, children);
        layerDao.updateLayerMaxRSS(frame1, 250000, true);

        FrameDetail frameDetail2 = frameDao.findFrameDetail(job, "0002-pass_1");
        DispatchFrame frame2 = frameDao.getDispatchFrame(frameDetail2.id);

        VirtualProc proc2 = VirtualProc.build(host, frame2);
        proc2.frameId = frame2.id;
        procDao.insertVirtualProc(proc2);

        procDao.updateProcMemoryUsage(frame2, 255000, 255000, 250000, 250000, 255000, 255000, 0, 0,
                0, children);
        layerDao.updateLayerMaxRSS(frame2, 255000, true);

        FrameDetail frameDetail3 = frameDao.findFrameDetail(job, "0003-pass_1");
        DispatchFrame frame3 = frameDao.getDispatchFrame(frameDetail3.id);

        VirtualProc proc3 = VirtualProc.build(host, frame3);
        proc3.frameId = frame3.id;
        procDao.insertVirtualProc(proc3);

        procDao.updateProcMemoryUsage(frame3, 3145728, 3145728, 3145728, 3145728, 3145728, 3145728,
                0, 0, 0, children);
        layerDao.updateLayerMaxRSS(frame3, 300000, true);

        procDao.balanceUnderUtilizedProcs(proc3, 100000);
        procDao.increaseReservedMemory(proc3, this.MEM_RESERVED_DEFAULT + 100000);

        // Check the target proc
        VirtualProc targetProc = procDao.getVirtualProc(proc3.getId());
        assertEquals(this.MEM_RESERVED_DEFAULT + 100000, targetProc.memoryReserved);

        // Check other procs
        VirtualProc firstProc = procDao.getVirtualProc(proc1.getId());
        assertEquals(this.MEM_RESERVED_DEFAULT - 50000 - 1, firstProc.memoryReserved);

        VirtualProc secondProc = procDao.getVirtualProc(proc2.getId());
        assertEquals(this.MEM_RESERVED_DEFAULT - 50000 - 1, secondProc.memoryReserved);

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCurrentShowId() {

        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        assertEquals(job.getShowId(), procDao.getCurrentShowId(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCurrentJobId() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        assertEquals(job.getJobId(), procDao.getCurrentJobId(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCurrentLayerId() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        assertEquals(frame.getLayerId(), procDao.getCurrentLayerId(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetCurrentFrameId() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        VirtualProc proc = VirtualProc.build(host, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        assertEquals(frame.getFrameId(), procDao.getCurrentFrameId(proc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getProcsBySearch() {
        DispatchHost host = createHost();

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");

        /*
         * Book 5 procs.
         */
        for (int i = 1; i < 6; i++) {
            FrameDetail f = frameDao.findFrameDetail(job, String.format("%04d-pass_1", i));
            VirtualProc proc = new VirtualProc();
            proc.allocationId = null;
            proc.coresReserved = 100;
            proc.hostId = host.id;
            proc.hostName = host.name;
            proc.jobId = job.id;
            proc.frameId = f.id;
            proc.layerId = f.layerId;
            proc.showId = f.showId;
            proc.childProcesses = "".getBytes();
            procDao.insertVirtualProc(proc);
        }

        ProcSearchInterface r;

        /*
         * Search for all 5 running procs
         */
        r = procSearchFactory.create();
        r.addSort(new Sort("proc.ts_booked", Direction.ASC));
        ProcSearchCriteria criteriaA = r.getCriteria();
        r.setCriteria(criteriaA.toBuilder().addShows("pipe").build());
        assertEquals(5, procDao.findVirtualProcs(r).size());

        /*
         * Limit the result to 1 result.
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaB = r.getCriteria();
        r.setCriteria(criteriaB.toBuilder().addShows("pipe").addMaxResults(1).build());
        assertEquals(1, procDao.findVirtualProcs(r).size());

        /*
         * Change the first result to 1, which should limt the result to 4.
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaC = r.getCriteria();
        r.setCriteria(criteriaC.toBuilder().addShows("pipe").setFirstResult(2).build());
        r.addSort(new Sort("proc.ts_booked", Direction.ASC));
        assertEquals(4, procDao.findVirtualProcs(r).size());

        /*
         * Now try to do the eqivalent of a limit/offset
         */
        r = procSearchFactory.create();
        ProcSearchCriteria criteriaD = r.getCriteria();
        r.setCriteria(
                criteriaD.toBuilder().addShows("pipe").setFirstResult(3).addMaxResults(2).build());
        assertEquals(2, procDao.findVirtualProcs(r).size());

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testVirtualProcWithSelfishService() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();

        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1_preprocess");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);
        frame.minCores = 250;
        frame.threadable = true;

        // Frame from a non-selfish sevice
        VirtualProc proc = VirtualProc.build(host, frame, "something-else");
        assertEquals(250, proc.coresReserved);

        // When no selfish service config is provided
        proc = VirtualProc.build(host, frame);
        assertEquals(250, proc.coresReserved);

        // Frame with a selfish service
        proc = VirtualProc.build(host, frame, "shell", "something-else");
        assertEquals(800, proc.coresReserved);
    }

    /**
     * Cuebot-managed show: deleteVirtualProc decrements the five PG accounting tables. With
     * dispatcher.scheduler_manages_resources at its default (false) the decrement-skip gate in
     * ProcDaoJdbc is closed, so this is the path every show takes regardless of the
     * b_scheduler_managed flag. Regression guard for the default branch.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testProcDestroyedCuebotManagedShowDecrementsAccountingTables() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);

        // After insert, the five tables carry +100 (proc booked).
        int subCoresAfterInsert = readSubCores(proc.showId, proc.allocationId);
        int layerCoresAfterInsert = readLayerCores(proc.layerId);
        int jobCoresAfterInsert = readJobCores(proc.jobId);
        int folderCoresAfterInsert = readFolderCores(proc.jobId);
        int pointCoresAfterInsert = readPointCores(proc.jobId);

        procDao.deleteVirtualProc(proc);

        // Cuebot-managed: the five tables are decremented back down by 100.
        assertEquals(subCoresAfterInsert - 100, readSubCores(proc.showId, proc.allocationId));
        assertEquals(layerCoresAfterInsert - 100, readLayerCores(proc.layerId));
        assertEquals(jobCoresAfterInsert - 100, readJobCores(proc.jobId));
        assertEquals(folderCoresAfterInsert - 100, readFolderCores(proc.jobId));
        assertEquals(pointCoresAfterInsert - 100, readPointCores(proc.jobId));
    }

    /**
     * Show flagged {@code b_scheduler_managed=true} AND
     * {@code dispatcher.scheduler_manages_resources=true}: deleteVirtualProc must <em>not</em>
     * decrement the five PG accounting tables. Only then does an EXTERNAL scheduler own them (its
     * recompute rewrites them from SUM(proc)); the release is announced via NOTIFY instead. The
     * skip requires BOTH conditions — the property is injected with high precedence for this test
     * only and removed in an @After hook.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testProcDestroyedSchedulerManagedShowSkipsAccountingDecrement() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);

        int subCoresAfterInsert = readSubCores(proc.showId, proc.allocationId);
        int layerCoresAfterInsert = readLayerCores(proc.layerId);
        int jobCoresAfterInsert = readJobCores(proc.jobId);
        int folderCoresAfterInsert = readFolderCores(proc.jobId);
        int pointCoresAfterInsert = readPointCores(proc.jobId);

        // Both halves of the gate: the property (removed by the @After hook) ...
        enableExternalSchedulerAccounting();

        // ... and the show flag. The ShowDao writer-cache refresh means the next
        // isSchedulerManaged() call sees true immediately on this Cuebot. The @After hook clears
        // the cache so this transient flip doesn't leak into other tests.
        ShowEntity show = showDao.getShowDetail(proc.showId);
        showDao.updateSchedulerManaged(show, true);

        procDao.deleteVirtualProc(proc);

        // External-scheduler-managed: the five tables are NOT decremented (recompute owns them).
        assertEquals(subCoresAfterInsert, readSubCores(proc.showId, proc.allocationId));
        assertEquals(layerCoresAfterInsert, readLayerCores(proc.layerId));
        assertEquals(jobCoresAfterInsert, readJobCores(proc.jobId));
        assertEquals(folderCoresAfterInsert, readFolderCores(proc.jobId));
        assertEquals(pointCoresAfterInsert, readPointCores(proc.jobId));
    }

    /**
     * Show flagged {@code b_scheduler_managed=true} but dispatcher.scheduler_manages_resources left
     * at its default (false): the decrements still happen. This is the fail-safe default — the
     * in-process Maestro's 'managed' mode uses the same show flag, but its bookings increment these
     * tables, so its releases must decrement them or the counters ratchet upward until every cap
     * looks full.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testProcDestroyedManagedShowWithoutPropertyStillDecrements() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame = frameDao.findFrameDetail(job, "0001-pass_1");

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = 100;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;

        procDao.insertVirtualProc(proc);

        int subCoresAfterInsert = readSubCores(proc.showId, proc.allocationId);
        int layerCoresAfterInsert = readLayerCores(proc.layerId);
        int jobCoresAfterInsert = readJobCores(proc.jobId);
        int folderCoresAfterInsert = readFolderCores(proc.jobId);
        int pointCoresAfterInsert = readPointCores(proc.jobId);

        // Only the show flag; the property stays at its default (false).
        ShowEntity show = showDao.getShowDetail(proc.showId);
        showDao.updateSchedulerManaged(show, true);

        procDao.deleteVirtualProc(proc);

        // The flag alone does not open the skip gate: decrements happen as usual.
        assertEquals(subCoresAfterInsert - 100, readSubCores(proc.showId, proc.allocationId));
        assertEquals(layerCoresAfterInsert - 100, readLayerCores(proc.layerId));
        assertEquals(jobCoresAfterInsert - 100, readJobCores(proc.jobId));
        assertEquals(folderCoresAfterInsert - 100, readFolderCores(proc.jobId));
        assertEquals(pointCoresAfterInsert - 100, readPointCores(proc.jobId));
    }

    /**
     * reserveHostResourcesBatch aggregates the demand of several procs on the same host into one
     * guarded decrement, and refundHostResourcesBatch restores the same idle counters exactly.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testReserveAndRefundHostResourcesBatch() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        VirtualProc proc1 = buildBatchProc(host, job, frame1, 100);
        VirtualProc proc2 = buildBatchProc(host, job, frame2, 200);

        long idleCores = readHostIdleCores(host.id);
        long idleMem = readHostIdleMem(host.id);

        Set<String> affordable = procDao.reserveHostResourcesBatch(Arrays.asList(proc1, proc2));

        assertEquals(Collections.singleton(host.id), affordable);
        assertEquals(idleCores - 300, readHostIdleCores(host.id));
        assertEquals(idleMem - 200000, readHostIdleMem(host.id));

        procDao.refundHostResourcesBatch(Arrays.asList(proc1, proc2));

        assertEquals(idleCores, readHostIdleCores(host.id));
        assertEquals(idleMem, readHostIdleMem(host.id));
    }

    /**
     * The reservation guard is per-host and aggregated: two procs that each fit individually but
     * together exceed the host's idle cores leave the host out of the affordable set and its idle
     * counters completely untouched (0-row guarded update, no partial reservation).
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testReserveHostResourcesBatchRefusesOverCommittedHost() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        long idleCores = readHostIdleCores(host.id);
        long idleMem = readHostIdleMem(host.id);

        // Individually affordable, aggregate demand = idleCores + 100.
        VirtualProc proc1 = buildBatchProc(host, job, frame1, (int) idleCores);
        VirtualProc proc2 = buildBatchProc(host, job, frame2, 100);

        Set<String> affordable = procDao.reserveHostResourcesBatch(Arrays.asList(proc1, proc2));

        assertTrue(affordable.isEmpty());
        assertEquals(idleCores, readHostIdleCores(host.id));
        assertEquals(idleMem, readHostIdleMem(host.id));
    }

    /**
     * batchInsertVirtualProcs writes only the proc rows: host idle is debited by the up-front
     * reserveHostResourcesBatch (the commit-path sequence) and must not be debited a second time by
     * the insert, unlike the single-proc insertVirtualProc which does both.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testBatchInsertVirtualProcsWritesRowsWithoutTouchingHostIdle() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        VirtualProc proc1 = buildBatchProc(host, job, frame1, 100);
        VirtualProc proc2 = buildBatchProc(host, job, frame2, 100);

        long idleCores = readHostIdleCores(host.id);
        procDao.reserveHostResourcesBatch(Arrays.asList(proc1, proc2));
        long idleCoresAfterReserve = readHostIdleCores(host.id);
        assertEquals(idleCores - 200, idleCoresAfterReserve);

        procDao.batchInsertVirtualProcs(Arrays.asList(proc1, proc2));

        assertEquals(2, countProcsOnHost(host.id));
        assertTrue(procDao.verifyRunningProc(proc1.getId(), frame1.getId()));
        assertTrue(procDao.verifyRunningProc(proc2.getId(), frame2.getId()));
        // The insert itself did not double-debit the host.
        assertEquals(idleCoresAfterReserve, readHostIdleCores(host.id));
    }

    /**
     * batchDeleteVirtualProcs removes the rows, refunds host idle and credits the accounting tables
     * exactly once: mirror image of what two single-proc inserts debited, and a repeat call on the
     * same (already deleted) procs is a no-op with no second refund.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testBatchDeleteVirtualProcsRefundsAndCreditsExactlyOnce() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        long idleCoresBeforeInsert = readHostIdleCores(host.id);
        int jobCoresBeforeInsert = readJobCores(job.id);

        // Single-proc inserts debit host idle AND the accounting tables (+100 each), so the batch
        // delete must credit both back symmetrically.
        VirtualProc proc1 = buildBatchProc(host, job, frame1, 100);
        VirtualProc proc2 = buildBatchProc(host, job, frame2, 100);
        procDao.insertVirtualProc(proc1);
        procDao.insertVirtualProc(proc2);

        assertEquals(idleCoresBeforeInsert - 200, readHostIdleCores(host.id));
        assertEquals(jobCoresBeforeInsert + 200, readJobCores(job.id));
        int subCoresAfterInsert = readSubCores(proc1.showId, proc1.allocationId);
        int layerCoresAfterInsert = readLayerCores(proc1.layerId);

        List<VirtualProc> deleted = procDao.batchDeleteVirtualProcs(Arrays.asList(proc1, proc2));

        assertEquals(2, deleted.size());
        assertEquals(0, countProcsOnHost(host.id));
        assertEquals(idleCoresBeforeInsert, readHostIdleCores(host.id));
        assertEquals(jobCoresBeforeInsert, readJobCores(job.id));
        assertEquals(subCoresAfterInsert - 200, readSubCores(proc1.showId, proc1.allocationId));
        assertEquals(layerCoresAfterInsert - 200, readLayerCores(proc1.layerId));

        // Repeat delete: the procs no longer exist, so nothing comes back and
        // nothing is refunded or credited a second time.
        assertTrue(procDao.batchDeleteVirtualProcs(Arrays.asList(proc1, proc2)).isEmpty());
        assertEquals(idleCoresBeforeInsert, readHostIdleCores(host.id));
        assertEquals(jobCoresBeforeInsert, readJobCores(job.id));
    }

    /**
     * deleteStaleProcsByFrames reaps only procs sitting on the listed frames, returns the corpse
     * with its host/allocation keys populated (for the caller's orphan-render kill), and
     * refunds/credits only what the reaped proc held.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteStaleProcsByFramesOnlyReapsListedFrames() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        VirtualProc proc1 = buildBatchProc(host, job, frame1, 100);
        VirtualProc proc2 = buildBatchProc(host, job, frame2, 100);
        procDao.insertVirtualProc(proc1);
        procDao.insertVirtualProc(proc2);

        long idleCoresAfterInsert = readHostIdleCores(host.id);
        int jobCoresAfterInsert = readJobCores(job.id);

        List<VirtualProc> stale = procDao.deleteStaleProcsByFrames(Arrays.asList(frame1.id));

        assertEquals(1, stale.size());
        VirtualProc corpse = stale.get(0);
        assertEquals(proc1.getProcId(), corpse.getProcId());
        assertEquals(host.name, corpse.hostName);
        assertEquals(host.allocationId, corpse.allocationId);

        // Only the listed frame's proc died; its neighbor survives untouched.
        assertEquals(1, countProcsOnHost(host.id));
        assertTrue(procDao.verifyRunningProc(proc2.getId(), frame2.getId()));

        // Refund and credit cover exactly the reaped proc's share.
        assertEquals(idleCoresAfterInsert + 100, readHostIdleCores(host.id));
        assertEquals(jobCoresAfterInsert - 100, readJobCores(job.id));
    }

    /**
     * deleteOrphanedProcs honors both halves of its predicate: a proc is swept only when its frame
     * is not RUNNING and its booking is older than the cutoff. A fresh proc survives the sweep and
     * so does an old proc whose frame is genuinely RUNNING.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteOrphanedProcsHonorsCutoffAndFrameState() {
        DispatchHost host = createHost();
        JobDetail job = launchJob();
        FrameDetail frame1 = frameDao.findFrameDetail(job, "0001-pass_1");
        FrameDetail frame2 = frameDao.findFrameDetail(job, "0002-pass_1");

        VirtualProc proc1 = buildBatchProc(host, job, frame1, 100);
        VirtualProc proc2 = buildBatchProc(host, job, frame2, 100);
        procDao.insertVirtualProc(proc1);
        procDao.insertVirtualProc(proc2);

        long idleCoresAfterInsert = readHostIdleCores(host.id);

        // Both frames are non-RUNNING, but both bookings are fresh: nothing is swept.
        assertTrue(procDao.deleteOrphanedProcs(300).isEmpty());

        // Age proc1 past the cutoff: its non-RUNNING frame makes it a corpse.
        jdbcTemplate.update("UPDATE proc SET ts_booked = current_timestamp - interval '1' hour "
                + "WHERE pk_proc = ?", proc1.getProcId());

        List<VirtualProc> swept = procDao.deleteOrphanedProcs(300);
        assertEquals(1, swept.size());
        assertEquals(proc1.getProcId(), swept.get(0).getProcId());
        assertEquals(idleCoresAfterInsert + 100, readHostIdleCores(host.id));

        // Age proc2 too, but put its frame in RUNNING: an active render is never swept.
        jdbcTemplate.update("UPDATE proc SET ts_booked = current_timestamp - interval '1' hour "
                + "WHERE pk_proc = ?", proc2.getProcId());
        jdbcTemplate.update("UPDATE frame SET str_state = 'RUNNING' WHERE pk_frame = ?", frame2.id);

        assertTrue(procDao.deleteOrphanedProcs(300).isEmpty());
        assertEquals(1, countProcsOnHost(host.id));
    }

    /** Proc with the real allocation and accounting keys set, as the batch commit path builds. */
    private VirtualProc buildBatchProc(DispatchHost host, JobDetail job, FrameDetail frame,
            int cores) {
        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.allocationId;
        proc.coresReserved = cores;
        proc.memoryReserved = 100000;
        proc.hostId = host.id;
        proc.hostName = host.name;
        proc.jobId = job.id;
        proc.frameId = frame.id;
        proc.layerId = frame.layerId;
        proc.showId = frame.showId;
        return proc;
    }

    private long readHostIdleCores(String hostId) {
        return jdbcTemplate.queryForObject("SELECT int_cores_idle FROM host WHERE pk_host=?",
                Long.class, hostId);
    }

    private long readHostIdleMem(String hostId) {
        return jdbcTemplate.queryForObject("SELECT int_mem_idle FROM host WHERE pk_host=?",
                Long.class, hostId);
    }

    private int countProcsOnHost(String hostId) {
        return jdbcTemplate.queryForObject("SELECT COUNT(*) FROM proc WHERE pk_host=?",
                Integer.class, hostId);
    }

    private int readSubCores(String showId, String allocId) {
        Integer v = jdbcTemplate.queryForObject(
                "SELECT int_cores FROM subscription WHERE pk_show=? AND pk_alloc=?", Integer.class,
                showId, allocId);
        return v == null ? 0 : v;
    }

    private int readLayerCores(String layerId) {
        Integer v = jdbcTemplate.queryForObject(
                "SELECT int_cores FROM layer_resource WHERE pk_layer=?", Integer.class, layerId);
        return v == null ? 0 : v;
    }

    private int readJobCores(String jobId) {
        Integer v = jdbcTemplate.queryForObject("SELECT int_cores FROM job_resource WHERE pk_job=?",
                Integer.class, jobId);
        return v == null ? 0 : v;
    }

    private int readFolderCores(String jobId) {
        Integer v =
                jdbcTemplate.queryForObject(
                        "SELECT int_cores FROM folder_resource WHERE pk_folder = "
                                + "(SELECT pk_folder FROM job WHERE pk_job=?)",
                        Integer.class, jobId);
        return v == null ? 0 : v;
    }

    private int readPointCores(String jobId) {
        Integer v = jdbcTemplate.queryForObject(
                "SELECT int_cores FROM point WHERE pk_dept = (SELECT pk_dept FROM job WHERE pk_job=?) "
                        + "AND pk_show = (SELECT pk_show FROM job WHERE pk_job=?)",
                Integer.class, jobId, jobId);
        return v == null ? 0 : v;
    }
}
