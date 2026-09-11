
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
import java.sql.Timestamp;
import java.util.ArrayList;
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
import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameReservationException;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitHostUsage;
import com.imageworks.spcue.grpc.limit.LimitType;
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
import static org.junit.Assert.fail;

/**
 * The limit dispatch gate and the settlement counting model, end to end against the real queries:
 * external holds and recent bookings merge into usage, HOST limits clamp per machine, the soft
 * threshold packs instead of spreading, and non-ENFORCED or stale limits never block.
 *
 * Uses jobspec_dispatch_test's pass_1/pass_2 layers: pass_1 gets bound to the limit under test,
 * pass_2 stays unbound as the control that unlimited work is never affected.
 */
@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class LimitDispatchGateTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    DispatcherDao dispatcherDao;

    @Resource
    LimitDao limitDao;

    @Resource
    LayerDao layerDao;

    @Resource
    HostDao hostDao;

    @Resource
    JobManager jobManager;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    Dispatcher dispatcher;

    @Resource
    JobLauncher jobLauncher;

    private static final String HOSTNAME = "beta";
    private static final String OTHER_HOST = "gamma";
    private static final String LIMIT_NAME = "houdini";

    @Before
    public void launchJob() {
        dispatcher.setTestMode(true);
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                .setFreeMcp(CueUtil.GB).setFreeMem(53500).setFreeSwap(20760).setLoad(1)
                .setTotalMcp(CueUtil.GB4).setTotalMem(8173264).setTotalSwap(20960)
                .setNimbyEnabled(false).setNumProcs(2).setCoresPerProc(100).addTags("test")
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .build();
        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));
    }

    private DispatchHost getHost() {
        return hostDao.findDispatchHost(HOSTNAME);
    }

    private JobDetail getJob() {
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_dispatch_test_v1");
    }

    /** Creates the limit and binds pass_1 to it; pass_2 stays unbound as the control. */
    private LimitEntity createBoundLimit(int maxValue, LimitType type,
            LimitEnforcement enforcement) {
        String limitId = limitDao.createLimit(LIMIT_NAME, maxValue, type, enforcement, -1);
        LayerDetail layer = layerDao.findLayerDetail(getJob(), "pass_1");
        assertTrue(layerDao.addLimit(layer, limitId, LimitBindSource.SPEC));
        return limitDao.getLimit(limitId);
    }

    /** Applies an external report of one token per named host and refreshes the usage row. */
    private void report(LimitEntity limit, Timestamp captureTime, String... hosts) {
        List<LimitHostUsage> holds = new ArrayList<LimitHostUsage>();
        for (String host : hosts) {
            holds.add(LimitHostUsage.newBuilder().setHostName(host).setTokens(1).build());
        }
        limitDao.replaceExternalHolds(limit, holds, "test", captureTime);
        limitDao.refreshUsage(limit);
    }

    private static Timestamp now() {
        return new Timestamp(System.currentTimeMillis());
    }

    /**
     * Pushes every proc's dispatch time back so it sits outside the settle window, modelling a
     * booking the license server has had ample time to observe.
     */
    private void ageBookingsPastSettleWindow() {
        jdbcTemplate
                .update("UPDATE proc SET ts_dispatched = ts_dispatched - INTERVAL '10 minutes'");
    }

    private static Timestamp beforeBooking() {
        // Well before the test transaction's current_timestamp, so procs dispatched in this
        // transaction land after the watermark and count as pending -- even after
        // ageBookingsPastSettleWindow() pushed them back 10 minutes.
        return new Timestamp(System.currentTimeMillis() - 660 * 1000L);
    }

    private List<String> findFrameNames() {
        List<String> names = new ArrayList<String>();
        for (DispatchFrame frame : dispatcherDao.findNextDispatchFrames(getJob(), getHost(), 20)) {
            names.add(frame.name);
        }
        return names;
    }

    private boolean boundLayerIsBookable() {
        return findFrameNames().stream().anyMatch(name -> name.endsWith("pass_1"));
    }

    private VirtualProc bookOneBoundFrame() {
        DispatchHost host = getHost();
        LayerDetail layer = layerDao.findLayerDetail(getJob(), "pass_1");
        List<DispatchFrame> frames = dispatcherDao.findNextDispatchFrames(layer, host, 1);
        assertEquals(1, frames.size());
        DispatchFrame frame = frames.get(0);
        VirtualProc proc = VirtualProc.build(host, frame, getJob().os);
        proc.coresReserved = 100;
        dispatcher.dispatch(frame, proc);
        return proc;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testExternalHoldsSaturateFrameLimit() {
        // External holds alone saturate a FRAME limit with zero Cue frames running, and the
        // unbound layer is untouched in every configuration.
        LimitEntity limit = createBoundLimit(2, LimitType.FRAME, LimitEnforcement.ENFORCED);
        assertTrue(boundLayerIsBookable());

        report(limit, now(), OTHER_HOST, "delta");
        assertFalse("Two external tokens must saturate a FRAME limit of 2", boundLayerIsBookable());
        assertTrue("The unbound layer must keep booking",
                findFrameNames().stream().allMatch(name -> name.endsWith("pass_2")));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHostLimitAtMaxAllowsHolderBlocksNewHost() {
        LimitEntity limit = createBoundLimit(1, LimitType.HOST, LimitEnforcement.ENFORCED);

        // The one allowed machine is someone else: this host may not light up a second one.
        report(limit, now(), OTHER_HOST);
        assertFalse(boundLayerIsBookable());

        // The one allowed machine is this host: booking here consumes nothing new.
        report(limit, now(), HOSTNAME);
        assertTrue("A host already holding the token must keep booking at max",
                boundLayerIsBookable());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSoftThresholdPacksInsteadOfSpreading() {
        LimitEntity limit = createBoundLimit(3, LimitType.HOST, LimitEnforcement.ENFORCED);
        limitDao.setSoftValue(limit, 1);

        // Between soft and max: only holders may book, and this host holds nothing.
        report(limit, now(), OTHER_HOST);
        assertFalse("Above the soft threshold a non-holding host must not book",
                boundLayerIsBookable());

        // Same usage band, but this host already holds a token: packing is allowed.
        report(limit, now(), OTHER_HOST, HOSTNAME);
        assertTrue(boundLayerIsBookable());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAdvisoryAndDisabledNeverBlock() {
        LimitEntity limit = createBoundLimit(1, LimitType.HOST, LimitEnforcement.ADVISORY);
        report(limit, now(), OTHER_HOST, "delta", "epsilon");
        assertTrue("An ADVISORY limit must never block, at any usage", boundLayerIsBookable());

        limitDao.setEnforcement(limit, LimitEnforcement.DISABLED);
        assertTrue("A DISABLED limit must be ignored entirely", boundLayerIsBookable());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testStaleEnforcedLimitDoesNotBlock() {
        LimitEntity limit = createBoundLimit(1, LimitType.HOST, LimitEnforcement.ENFORCED);
        limitDao.setReportTtl(limit, 60);

        // A fresh saturating report blocks.
        report(limit, now(), OTHER_HOST);
        assertFalse(boundLayerIsBookable());

        // The same report an hour old is stale: the license server is still enforcing for
        // real, so gating the farm on data known to be wrong only buys idle time.
        report(limit, new Timestamp(System.currentTimeMillis() - 3600 * 1000L), OTHER_HOST);
        assertTrue("A stale ENFORCED limit must stop blocking", boundLayerIsBookable());
        assertTrue(limitDao.getLimit(limit.getLimitId()).isReportStale());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHoldingHostKeepsBookingFramesAtHostLimitMax() {
        // A HOST limit means all frames on a machine share one token: a host that lit the limit
        // up must keep taking bound frames even at max. This is the frame-start re-check's
        // regression guard -- the old frame-count re-check refused every start past max_value
        // and clamped a holding host to max_value concurrent frames.
        createBoundLimit(1, LimitType.HOST, LimitEnforcement.ENFORCED);

        bookOneBoundFrame();
        assertTrue("The one allowed machine is this host; more frames here are free",
                boundLayerIsBookable());
        bookOneBoundFrame();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFrameStartReCheckStopsBatchOvershoot() {
        // The dispatch gate is evaluated once per find query, so a batch found under headroom
        // could overshoot a FRAME limit as it books frame by frame. The frame-start re-check
        // sees the procs booked earlier in the batch as pending and refuses the overshoot.
        createBoundLimit(1, LimitType.FRAME, LimitEnforcement.ENFORCED);

        DispatchHost host = getHost();
        LayerDetail layer = layerDao.findLayerDetail(getJob(), "pass_1");
        List<DispatchFrame> frames = dispatcherDao.findNextDispatchFrames(layer, host, 2);
        assertEquals(2, frames.size());

        VirtualProc first = VirtualProc.build(host, frames.get(0), getJob().os);
        first.coresReserved = 100;
        dispatcher.dispatch(frames.get(0), first);

        VirtualProc second = VirtualProc.build(getHost(), frames.get(1), getJob().os);
        second.coresReserved = 100;
        try {
            dispatcher.dispatch(frames.get(1), second);
            fail("The second start of a batch must be refused once the first fills the limit");
        } catch (FrameReservationException expected) {
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testBookingCountsAsPendingUntilSettled() {
        LimitEntity limit = createBoundLimit(10, LimitType.FRAME, LimitEnforcement.ENFORCED);
        bookOneBoundFrame();

        // No reporter: the running proc counts, exactly the pre-settlement behavior.
        LimitEntity counted = limitDao.getLimit(limit.getLimitId());
        assertEquals(1, counted.pendingUsage);
        assertEquals(0, counted.settledUsage);
        assertEquals(1, counted.getCurrentUsage());

        // A report captured inside the settle window of the booking has not had time to observe
        // the checkout, so its silence is not evidence: the booking still counts.
        report(limit, now());
        counted = limitDao.getLimit(limit.getLimitId());
        assertEquals("A booking inside the settle window must keep counting", 1,
                counted.getCurrentUsage());

        // Once the booking is older than the settle window, a report saying nothing is checked
        // out is believable: the frame held its license for part of its life and released it.
        // This is the regression guard for the whole settlement rewrite -- under max() merging
        // it could never drop to zero.
        ageBookingsPastSettleWindow();
        report(limit, now());
        counted = limitDao.getLimit(limit.getLimitId());
        assertEquals("A settled booking the server does not report must stop counting", 0,
                counted.getCurrentUsage());

        // A report captured before the booking has not observed it yet: still pending.
        report(limit, beforeBooking());
        counted = limitDao.getLimit(limit.getLimitId());
        assertEquals(1, counted.pendingUsage);
        assertEquals(1, counted.getCurrentUsage());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSettledAndPendingMergePerHost() {
        LimitEntity limit = createBoundLimit(10, LimitType.FRAME, LimitEnforcement.ENFORCED);
        bookOneBoundFrame();

        // Settled tokens and a pending booking on the same host are disjoint in time and add
        // for a FRAME limit.
        List<LimitHostUsage> holds = new ArrayList<LimitHostUsage>();
        holds.add(LimitHostUsage.newBuilder().setHostName(HOSTNAME).setTokens(2).build());
        limitDao.replaceExternalHolds(limit, holds, "test", beforeBooking());
        limitDao.refreshUsage(limit);

        LimitEntity counted = limitDao.getLimit(limit.getLimitId());
        assertEquals(2, counted.settledUsage);
        assertEquals(1, counted.pendingUsage);
        assertEquals(3, counted.getCurrentUsage());

        // The same situation under a HOST limit is one machine, not three tokens, and the
        // pending booking on an already-settled host is not counted twice.
        limitDao.setLimitType(limit, LimitType.HOST);
        counted = limitDao.getLimit(limit.getLimitId());
        assertEquals(1, counted.settledUsage);
        assertEquals(0, counted.pendingUsage);
        assertEquals(1, counted.getCurrentUsage());
        assertEquals(1, counted.hostCount);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDuplicateBindingCannotDoubleCount() {
        LimitEntity limit = createBoundLimit(10, LimitType.FRAME, LimitEnforcement.ENFORCED);
        LayerDetail layer = layerDao.findLayerDetail(getJob(), "pass_1");

        // The second bind is a no-op under the unique constraint; without it every aggregate
        // joining layer_limit would count this layer's procs twice.
        assertFalse(layerDao.addLimit(layer, limit.getLimitId(), LimitBindSource.AUTO));

        bookOneBoundFrame();
        assertEquals("A layer bound twice must contribute once", 1,
                limitDao.getLimit(limit.getLimitId()).getCurrentUsage());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAffinityOrderingPrefersWorkWithoutNewLicense() {
        // pass_1 needs a HOST license this host does not hold; ADVISORY, so nothing is
        // blocked -- the ordering alone should put pass_2's work first.
        LimitEntity limit = createBoundLimit(5, LimitType.HOST, LimitEnforcement.ADVISORY);
        report(limit, now(), OTHER_HOST);

        List<String> names = findFrameNames();
        assertTrue(names.stream().anyMatch(name -> name.endsWith("pass_1")));
        assertEquals("Work needing no new license must come first", "0001-pass_2", names.get(0));

        // Once this host holds the license, natural dispatch order returns.
        report(limit, now(), OTHER_HOST, HOSTNAME);
        assertEquals("A holding host must not deprioritize the licensed layer", "0001-pass_1",
                findFrameNames().get(0));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAffinityOrderingIgnoresDisabledLimits() {
        LimitEntity limit = createBoundLimit(5, LimitType.HOST, LimitEnforcement.DISABLED);
        report(limit, now(), OTHER_HOST);
        assertEquals("A DISABLED limit must not reorder dispatch", "0001-pass_1",
                findFrameNames().get(0));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testBalancedModeJobFindHonorsLimits() {
        // BALANCED mode's job-finding query gates on limits like PRIORITY mode does: a job whose
        // every waiting layer is blocked vacates the ranks instead of being picked and then
        // yielding no frames. A job keeps qualifying as long as any of its layers can book.
        DispatcherDao.SchedulingMode previousMode = dispatcherDao.getSchedulingMode();
        dispatcherDao.setSchedulingMode(DispatcherDao.SchedulingMode.BALANCED);
        try {
            String jobId = getJob().getJobId();
            Set<String> jobs = dispatcherDao.findDispatchJobs(getHost(),
                    adminManager.findShowEntity("pipe"), 5);
            assertTrue("The job must be found before any limit saturates", jobs.contains(jobId));

            // A saturated limit on pass_1 alone must not exclude the job: pass_2 can still book.
            LimitEntity limit = createBoundLimit(0, LimitType.FRAME, LimitEnforcement.ENFORCED);
            jobs = dispatcherDao.findDispatchJobs(getHost(), adminManager.findShowEntity("pipe"),
                    5);
            assertTrue("A job with any bookable layer must keep qualifying", jobs.contains(jobId));

            // With every layer blocked, the job must vacate the job-find ranks.
            LayerDetail pass2 = layerDao.findLayerDetail(getJob(), "pass_2");
            assertTrue(layerDao.addLimit(pass2, limit.getLimitId(), LimitBindSource.SPEC));
            jobs = dispatcherDao.findDispatchJobs(getHost(), adminManager.findShowEntity("pipe"),
                    5);
            assertFalse("A fully limit-blocked job must not be picked in BALANCED mode",
                    jobs.contains(jobId));
        } finally {
            dispatcherDao.setSchedulingMode(previousMode);
        }
    }
}
