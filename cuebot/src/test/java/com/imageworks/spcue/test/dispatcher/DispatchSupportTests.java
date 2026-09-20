
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
import java.util.Map;
import java.util.List;
import java.util.Arrays;
import java.util.ArrayList;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.dispatcher.OomMemoryTracker;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.dispatcher.QueuedFrameCompletion;
import com.imageworks.spcue.dispatcher.FrameBooking;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertTrue;

@ContextConfiguration
public class DispatchSupportTests extends TransactionalTest {

    private static final String SHOW_STATS = "SELECT int_frame_success_count, int_frame_fail_count"
            + " FROM show_stats WHERE pk_show = ?";
    private static final String JOB_USAGE = "SELECT int_frame_success_count, int_frame_fail_count,"
            + " int_core_time_success, int_clock_time_success, int_core_time_fail,"
            + " int_clock_time_fail, int_clock_time_high FROM job_usage WHERE pk_job = ?";
    private static final String LAYER_USAGE = "SELECT int_frame_success_count,"
            + " int_frame_fail_count, int_core_time_success, int_clock_time_success,"
            + " int_core_time_fail, int_clock_time_fail, int_clock_time_high,"
            + " int_clock_time_low FROM layer_usage WHERE pk_layer = ?";

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
    Dispatcher dispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    FrameDao frameDao;

    @Resource
    LayerDao layerDao;

    @Resource
    ShowDao showDao;

    @Resource
    JobDao jobDao;

    private static final String HOSTNAME = "beta";

    private static final String JOBNAME = "pipe-dev.cue-testuser_shell_dispatch_test_v1";

    private static final String TARGET_JOB = "pipe-dev.cue-testuser_shell_dispatch_test_v2";

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(0)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(2).setCoresPerProc(400).addTags("test")
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .setFreeGpuMem((int) CueUtil.MB512).setTotalGpuMem((int) CueUtil.MB512).build();

        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));
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
    public void testDetermineIdleCores() {
        DispatchHost host = getHost();

        int grace_load = Dispatcher.CORE_LOAD_THRESHOLD * (host.cores / 100);

        // Machine is idle, no load.
        dispatchSupport.determineIdleCores(host, 0);
        assertEquals(800, host.idleCores);

        // Machine is idle but shows load of 200.
        host.idleCores = 800;
        dispatchSupport.determineIdleCores(host, 200);
        assertEquals(grace_load + 600, host.idleCores);

        // Machine is idle but has the grace load.
        host.idleCores = 800;
        dispatchSupport.determineIdleCores(host, grace_load);
        assertEquals(800, host.idleCores);

        // Machine has 100 units idle, grace_load -1
        host.idleCores = 100;
        dispatchSupport.determineIdleCores(host, 700 + grace_load - 1);
        assertEquals(100, host.idleCores);

        // Machine has 100 units idle, grace_load + 1
        host.idleCores = 100;
        dispatchSupport.determineIdleCores(host, 700 + grace_load + 1);
        assertEquals(99, host.idleCores);
    }

    // ---- the batch start and the frame version ----------------------------

    private DispatchFrame frame(String name) {
        FrameDetail detail = frameDao.findFrameDetail(getJob(), name);
        return jobManager.getDispatchFrame(detail.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void aBatchStartKeepsTheFrameVersionInStep() {
        DispatchFrame frame = frame("0001-pass_1");
        VirtualProc proc = VirtualProc.build(getHost(), frame);
        int before = frame.version;
        List<FrameBooking> won = dispatchSupport.startFramesAndProcsBatch(
                new ArrayList<>(Arrays.asList(new FrameBooking(frame, proc))));
        assertEquals(1, won.size());
        assertEquals("the in-memory version follows the row", before + 1, frame.version);
        // A failed launch rolls back on that version: the proc goes, then the
        // clear must fence on the run this batch started.
        dispatchSupport.unbookProc(proc);
        assertTrue("clearFrame must match the run this batch started",
                dispatchSupport.clearFrame(frame));
    }

    // ---- the counter batch against the per-frame path ---------------------

    private long[] counters(String sql, String key) {
        Map<String, Object> row = jdbcTemplate.queryForMap(sql, key);
        long[] out = new long[row.size()];
        int i = 0;
        for (Object v : row.values())
            out[i++] = ((Number) v).longValue();
        return out;
    }

    private static long[] head(long[] a, int n) {
        return Arrays.copyOf(a, n);
    }

    private static long[] delta(long[] before, long[] after) {
        long[] d = new long[before.length];
        for (int i = 0; i < d.length; i++)
            d[i] = after[i] - before[i];
        return d;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void theCounterBatchAndThePerFramePathAgree() {
        // Four frames per layer: a success, a failure, a signal-killed frame and
        // a memory failure, each on its own core and gpu count so a row's sums
        // are distinct numbers. The per-frame path files layer pass_1, the batch
        // files layer pass_2: both must move the show and job counters by the
        // same amount and leave the two layers' rows identical, clock extremes
        // included, with one success and three failures.
        int[] statuses = {0, 1, -9, Dispatcher.EXIT_STATUS_MEMORY_FAILURE};
        int[] cores = {200, 300, 400, 500};
        int[] gpus = {3, 1, 2, 0};
        List<DispatchFrame> perFrame = new ArrayList<>();
        List<DispatchFrame> batch = new ArrayList<>();
        for (int i = 1; i <= statuses.length; i++) {
            perFrame.add(frame(String.format("%04d-pass_1", i)));
            batch.add(frame(String.format("%04d-pass_2", i)));
        }
        for (int i = 0; i < statuses.length; i++) {
            for (DispatchFrame f : Arrays.asList(perFrame.get(i), batch.get(i))) {
                jdbcTemplate.update(
                        "UPDATE frame SET int_cores = ?, int_gpus = ? WHERE pk_frame = ?", cores[i],
                        gpus[i], f.getFrameId());
            }
        }
        String show = perFrame.get(0).showId, job = perFrame.get(0).jobId;
        String layerA = perFrame.get(0).layerId, layerB = batch.get(0).layerId;

        long[] s0 = counters(SHOW_STATS, show), j0 = counters(JOB_USAGE, job),
                a0 = counters(LAYER_USAGE, layerA), b0 = counters(LAYER_USAGE, layerB);
        // The per-frame path's own three writes, in this transaction: the
        // service method runs outside any transaction (NOT_SUPPORTED) and
        // would wait on the rows this test holds.
        for (int i = 0; i < statuses.length; i++) {
            ResourceUsage usage = frameDao.getResourceUsage(perFrame.get(i));
            showDao.updateFrameCounters(perFrame.get(i), statuses[i]);
            jobDao.updateUsage(perFrame.get(i), usage, statuses[i]);
            layerDao.updateUsage(perFrame.get(i), usage, statuses[i]);
        }
        long[] s1 = counters(SHOW_STATS, show), j1 = counters(JOB_USAGE, job),
                a1 = counters(LAYER_USAGE, layerA);

        List<QueuedFrameCompletion> scoop = new ArrayList<>();
        for (int i = 0; i < statuses.length; i++)
            scoop.add(new QueuedFrameCompletion(FrameCompleteReport.getDefaultInstance(),
                    new VirtualProc(), jobManager.getDispatchJob(job), new LayerDetail(),
                    new FrameDetail(), batch.get(i),
                    statuses[i] == 0 ? FrameState.SUCCEEDED : FrameState.DEAD, statuses[i]));
        dispatchSupport.updateUsageCountersBatch(scoop);
        long[] s2 = counters(SHOW_STATS, show), j2 = counters(JOB_USAGE, job),
                b1 = counters(LAYER_USAGE, layerB);

        assertArrayEquals("show counters: per frame vs batch", delta(s0, s1), delta(s1, s2));
        assertArrayEquals("job usage sums: per frame vs batch", head(delta(j0, j1), 6),
                head(delta(j1, j2), 6));
        assertArrayEquals("layer usage, all eight columns: per frame vs batch", delta(a0, a1),
                delta(b0, b1));
        assertArrayEquals("one success and three failures on the show", new long[] {1, 3},
                delta(s1, s2));
        assertTrue("the success frame's core time is in the sums", delta(b0, b1)[2] > 0);
    }

    // ---- the plan sees a frame's memory bump -------------------------------

    @Test
    @Transactional
    @Rollback(true)
    public void thePlanReservesAFramesMemoryBump() {
        // The frame OOMed once and carries a per-frame bump above the layer's
        // memory: the plan must fit and reserve it at the bumped size, or the
        // commit's capacity gate sees a sum the plan never reserved.
        DispatchFrame frame = frame("0001-pass_1");
        long bump = frame.getMinMemory() * 2;
        OomMemoryTracker.INSTANCE.onOom(frame.getFrameId(), frame.getLayerId(), bump, 1000);
        try {
            LayerInterface layer = layerDao.findLayerDetail(getJob(), "pass_1");
            List<FrameBooking> plan = dispatcher.planHost(getHost(), layer, 0, 0, 0, 10);
            FrameBooking booked = null;
            for (FrameBooking b : plan)
                if (b.frame.getFrameId().equals(frame.getFrameId()))
                    booked = b;
            assertTrue("the bumped frame is in the plan", booked != null);
            assertTrue("the plan reserved the bump: " + booked.proc.memoryReserved + " < " + bump,
                    booked.proc.memoryReserved >= bump);
            // The invariant itself: the commit's capacity gate sees the sum the
            // plan reserved, so it books every frame of the plan. A plan that
            // fit the frames at the layer's size is dropped whole at the gate
            // once one of them grows to the bump.
            List<FrameBooking> won =
                    dispatchSupport.startFramesAndProcsBatch(new ArrayList<>(plan));
            assertEquals("the gate books every frame the plan reserved", plan.size(), won.size());
        } finally {
            OomMemoryTracker.INSTANCE.onSuccess(frame.getFrameId());
        }
    }

    // ---- the batch stop ---------------------------------------------------

    private QueuedFrameCompletion completionOf(DispatchFrame frame, VirtualProc proc) {
        return new QueuedFrameCompletion(FrameCompleteReport.getDefaultInstance(), proc,
                jobManager.getDispatchJob(frame.jobId), new LayerDetail(), new FrameDetail(), frame,
                FrameState.SUCCEEDED, 0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void theBatchStopReleasesExactlyWhatItsBookingReserved() {
        // Two frames started by the batch; one completion carries the current
        // version, the other a stale one. The current one wins: its frame is
        // SUCCEEDED, its proc gone, the host's cores and memory back by exactly
        // its reservation. The stale one changes nothing.
        DispatchFrame f1 = frame("0001-pass_1");
        DispatchFrame f2 = frame("0002-pass_1");
        VirtualProc p1 = VirtualProc.build(getHost(), f1);
        VirtualProc p2 = VirtualProc.build(getHost(), f2);
        List<FrameBooking> won = dispatchSupport.startFramesAndProcsBatch(
                new ArrayList<>(Arrays.asList(new FrameBooking(f1, p1), new FrameBooking(f2, p2))));
        assertEquals(2, won.size());
        String hostId = getHost().getHostId();
        long[] before =
                counters("SELECT int_cores_idle, int_mem_idle FROM host WHERE pk_host = ?", hostId);
        f2.version -= 1;
        boolean[] stopped = dispatchSupport.stopFramesBatch(
                new ArrayList<>(Arrays.asList(completionOf(f1, p1), completionOf(f2, p2))));
        assertTrue("the current completion wins", stopped[0]);
        assertFalse("a stale completion changes nothing", stopped[1]);
        assertEquals("SUCCEEDED", jdbcTemplate.queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame = ?", String.class, f1.getFrameId()));
        assertEquals("RUNNING", jdbcTemplate.queryForObject(
                "SELECT str_state FROM frame WHERE pk_frame = ?", String.class, f2.getFrameId()));
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT count(*) FROM proc WHERE pk_frame = ?", Integer.class, f1.getFrameId()));
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT count(*) FROM proc WHERE pk_frame = ?", Integer.class, f2.getFrameId()));
        long[] after =
                counters("SELECT int_cores_idle, int_mem_idle FROM host WHERE pk_host = ?", hostId);
        assertEquals("the winner's cores are back", before[0] + p1.coresReserved, after[0]);
        assertEquals("the winner's memory is back", before[1] + p1.memoryReserved, after[1]);
        assertTrue(p1.unbooked);
        assertFalse(p2.unbooked);
    }
}
