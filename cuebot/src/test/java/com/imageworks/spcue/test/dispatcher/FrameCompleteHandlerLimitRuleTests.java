
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
import java.time.Duration;
import java.util.List;
import java.util.Map;
import javax.annotation.Resource;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.LayerDelayRules;
import com.imageworks.spcue.dispatcher.LimitRuleCache;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitType;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * Failure-rule discovery, end to end: a frame failing with a limit's exit status binds its layer to
 * the limit (AUTO provenance) and writes the layer backoff, while statuses no limit claims fall
 * back to the deprecated dispatcher.layer_delay.rules property.
 */
public class FrameCompleteHandlerLimitRuleTests extends TransactionalTest {

    @Resource
    AdminManager adminManager;

    @Resource
    FrameCompleteHandler frameCompleteHandler;

    @Resource
    HostManager hostManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    JobManager jobManager;

    @Resource
    JobDao jobDao;

    @Resource
    FrameDao frameDao;

    @Resource
    LayerDao layerDao;

    @Resource
    LimitDao limitDao;

    @Resource
    LimitRuleCache limitRuleCache;

    @Resource
    Dispatcher dispatcher;

    @Resource
    com.imageworks.spcue.dao.DispatcherDao dispatcherDao;

    private static final String HOSTNAME = "beta";
    private static final String LIMIT_NAME = "houdini";
    private static final int LICENSE_EXIT_STATUS = 330;

    private Map<Integer, Duration> originalDelayRules;

    @Before
    public void setUp() {
        dispatcher.setTestMode(true);
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_gpus_test.xml"));

        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                .setFreeMcp(CueUtil.GB).setFreeMem((int) CueUtil.GB8).setFreeSwap(20760).setLoad(0)
                .setTotalMcp(CueUtil.GB4).setTotalMem(CueUtil.GB8).setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false).setNumProcs(40).setCoresPerProc(100)
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .setNumGpus(8).setFreeGpuMem(CueUtil.GB16 * 8).setTotalGpuMem(CueUtil.GB16 * 8)
                .build();
        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));

        originalDelayRules = frameCompleteHandler.getDelayRules();
        // The cache is a context-wide singleton with an interval; limits created inside this
        // test's transaction must be visible to it immediately, and must not leak into other
        // tests after the rollback.
        limitRuleCache.invalidate();
    }

    @After
    public void tearDown() {
        frameCompleteHandler.setDelayRules(originalDelayRules);
        limitRuleCache.invalidate();
    }

    private LimitEntity createRuleLimit(int delayMinutes, boolean autoTag) {
        String limitId =
                limitDao.createLimit(LIMIT_NAME, 30, LimitType.HOST, LimitEnforcement.ADVISORY, -1);
        LimitEntity limit = limitDao.getLimit(limitId);
        limitDao.setFailureRule(limit, LICENSE_EXIT_STATUS, delayMinutes, autoTag);
        limitRuleCache.invalidate();
        return limit;
    }

    private VirtualProc bookOneFrame(JobDetail job) {
        jobManager.setJobPaused(job, false);
        DispatchHost host = hostManager.findDispatchHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        return procs.get(0);
    }

    private VirtualProc bookOneFrameDirectly(JobDetail job) {
        DispatchHost host = hostManager.findDispatchHost(HOSTNAME);
        List<com.imageworks.spcue.DispatchFrame> frames =
                dispatcherDao.findNextDispatchFrames(job, host, 1);
        assertEquals(1, frames.size());
        VirtualProc proc = VirtualProc.build(host, frames.get(0), job.os);
        proc.coresReserved = 100;
        dispatcher.dispatch(frames.get(0), proc);
        return proc;
    }

    private void reportFrameComplete(VirtualProc proc, int exitStatus) {
        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        frameCompleteHandler.handleFrameCompleteReport(
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(exitStatus).build());
    }

    /**
     * Asserts the backoff lands about {@code delayMinutes} in the future, with a generous tolerance
     * for the gap between the transaction's timestamp and the wall clock.
     */
    private static void assertDelayedByAbout(int delayMinutes, java.sql.Timestamp startAfter) {
        long deltaMs = startAfter.getTime() - System.currentTimeMillis();
        long expectedMs = delayMinutes * 60_000L;
        assertTrue("Delay of " + deltaMs + "ms is not about " + delayMinutes + " minutes",
                Math.abs(deltaMs - expectedMs) < 90_000L);
    }

    private String bindingSource(String layerId, String limitId) {
        List<String> sources = jdbcTemplate.queryForList(
                "SELECT str_source FROM layer_limit WHERE pk_layer=? AND pk_limit_record=?",
                String.class, layerId, limitId);
        assertEquals(1, sources.size());
        return sources.get(0);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFailingFrameTagsAndDelaysLayer() {
        LimitEntity limit = createRuleLimit(5, true);
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        assertEquals("AUTO", bindingSource(layer.getLayerId(), limit.getLimitId()));
        LayerDetail delayed = layerDao.getLayerDetail(layer.getLayerId());
        assertNotNull("A claimed exit status must delay the layer", delayed.startAfter);
        assertDelayedByAbout(5, delayed.startAfter);
        assertEquals(
                "Automatic backoff: limit " + LIMIT_NAME + ", exit status " + LICENSE_EXIT_STATUS,
                delayed.startAfterReason);
        // The frame rides the delay path rather than consuming a retry or dying.
        assertEquals(FrameState.WAITING, frameDao.getFrameDetail(proc.getFrameId()).state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSecondFailureIsIdempotent() {
        LimitEntity limit = createRuleLimit(2, true);
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        // An operator clears the backoff, the frame re-books and fails again while the
        // shortage persists. Booked directly: dispatchHost's job-lock cache would skip a job
        // it just dispatched.
        jdbcTemplate.update("UPDATE layer SET ts_start_after = NULL WHERE pk_layer = ?",
                layer.getLayerId());
        VirtualProc proc2 = bookOneFrameDirectly(job);
        reportFrameComplete(proc2, LICENSE_EXIT_STATUS);

        assertEquals("A burst of failing frames must bind once, not once per frame",
                Integer.valueOf(1),
                jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM layer_limit WHERE pk_layer=? AND pk_limit_record=?",
                        Integer.class, layer.getLayerId(), limit.getLimitId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testPureDiscoveryTagsWithoutDelaying() {
        LimitEntity limit = createRuleLimit(0, true);
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        assertEquals("AUTO", bindingSource(layer.getLayerId(), limit.getLimitId()));
        assertNull("delay_minutes = 0 must learn coverage without changing dispatch",
                layerDao.getLayerDetail(layer.getLayerId()).startAfter);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testAutoTagOffDelaysWithoutTagging() {
        LimitEntity limit = createRuleLimit(5, false);
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        assertEquals("auto_tag = false must not bind the layer", Integer.valueOf(0),
                jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM layer_limit WHERE pk_layer=? AND pk_limit_record=?",
                        Integer.class, layer.getLayerId(), limit.getLimitId()));
        LayerDetail delayed = layerDao.getLayerDetail(layer.getLayerId());
        assertNotNull(delayed.startAfter);
        assertDelayedByAbout(5, delayed.startAfter);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testEatenFrameNeverTags() {
        LimitEntity limit = createRuleLimit(5, true);
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");
        jobDao.updateAutoEat(job, true);

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        assertEquals(FrameState.EATEN, frameDao.getFrameDetail(proc.getFrameId()).state);
        assertEquals(Integer.valueOf(0),
                jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM layer_limit WHERE pk_layer=? AND pk_limit_record=?",
                        Integer.class, layer.getLayerId(), limit.getLimitId()));
        assertNull(layerDao.getLayerDetail(layer.getLayerId()).startAfter);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSpecBindingIsNeverDowngraded() {
        LimitEntity limit = createRuleLimit(5, true);
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");
        layerDao.addLimit(layer, limit.getLimitId(), LimitBindSource.SPEC);

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        assertEquals("A submitter's declaration is never downgraded to a machine's guess", "SPEC",
                bindingSource(layer.getLayerId(), limit.getLimitId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDbRuleTakesPrecedenceOverPropertyEntry() {
        // The property maps the same status to a 60-minute delay; the limit's 5-minute rule
        // must win, recognizably by its reason string.
        frameCompleteHandler.setDelayRules(LayerDelayRules.parse(LICENSE_EXIT_STATUS + ":60"));
        createRuleLimit(5, true);
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        assertEquals(
                "Automatic backoff: limit " + LIMIT_NAME + ", exit status " + LICENSE_EXIT_STATUS,
                layerDao.getLayerDetail(layer.getLayerId()).startAfterReason);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnclaimedPropertyStatusStillDelays() {
        // A status only the deprecated property lists keeps working unchanged, so upgrading
        // changes no behavior on day one.
        frameCompleteHandler.setDelayRules(LayerDelayRules.parse("332:7"));
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, 332);

        LayerDetail delayed = layerDao.getLayerDetail(layer.getLayerId());
        assertNotNull(delayed.startAfter);
        assertEquals("Automatic backoff: exit status 332", delayed.startAfterReason);
        assertEquals(FrameState.WAITING, frameDao.getFrameDetail(proc.getFrameId()).state);
    }
}
