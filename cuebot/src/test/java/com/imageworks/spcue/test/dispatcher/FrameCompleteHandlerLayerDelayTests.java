
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
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.LayerDelayRules;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.FrameState;
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
 * End-to-end coverage of the automatic layer backoff: a FrameCompleteReport carrying an exit status
 * configured in dispatcher.layer_delay.rules must write the reporting layer's start-after gate, and
 * nothing else must.
 *
 * The rules property is empty by default. Rather than start a second application context to
 * override it -- the test harness supports only one, since the embedded database and the gRPC
 * server's fixed port are both per-process -- these tests install the rule set directly on the
 * shared FrameCompleteHandler and restore it afterwards. LayerDelayRulesTests covers the parsing of
 * the property itself.
 */
public class FrameCompleteHandlerLayerDelayTests extends TransactionalTest {

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
    Dispatcher dispatcher;

    private static final String HOSTNAME = "beta";

    /** The exit status these tests configure a delay rule for. */
    private static final int LICENSE_EXIT_STATUS = 330;

    private static final int CONFIGURED_DELAY_MINUTES = 5;

    private Map<Integer, Duration> originalDelayRules;

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    /**
     * FrameCompleteHandler is a context-wide singleton, so the rules are restored in
     * {@link #tearDown()} to keep the other dispatcher tests running against the configured default
     * (no rules).
     */
    @Before
    public void installDelayRules() {
        originalDelayRules = frameCompleteHandler.getDelayRules();
        frameCompleteHandler.setDelayRules(
                LayerDelayRules.parse(LICENSE_EXIT_STATUS + ":" + CONFIGURED_DELAY_MINUTES));
    }

    @After
    public void tearDown() {
        frameCompleteHandler.setDelayRules(originalDelayRules);
    }

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_gpus_test.xml"));
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder().setName(HOSTNAME).setBootTime(1192369572)
                // The minimum amount of free space in the temporary directory to book a host.
                .setFreeMcp(CueUtil.GB).setFreeMem((int) CueUtil.GB8).setFreeSwap(20760).setLoad(0)
                .setTotalMcp(CueUtil.GB4).setTotalMem(CueUtil.GB8).setTotalSwap(CueUtil.GB2)
                .setNimbyEnabled(false).setNumProcs(40).setCoresPerProc(100)
                .setState(HardwareState.UP).setFacility("spi").putAttributes("SP_OS", "Linux")
                .setNumGpus(8).setFreeGpuMem(CueUtil.GB16 * 8).setTotalGpuMem(CueUtil.GB16 * 8)
                .build();

        hostManager.createHost(host, adminManager.findAllocationDetail("spi", "general"));
    }

    /**
     * Books the single frame of pipe-default-testuser_test0/layer0 and returns its proc.
     */
    private VirtualProc bookOneFrame(JobDetail job) {
        jobManager.setJobPaused(job, false);
        DispatchHost host = hostManager.findDispatchHost(HOSTNAME);
        List<VirtualProc> procs = dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
        return procs.get(0);
    }

    private void reportFrameComplete(VirtualProc proc, int exitStatus) {
        RunningFrameInfo info = RunningFrameInfo.newBuilder().setJobId(proc.getJobId())
                .setLayerId(proc.getLayerId()).setFrameId(proc.getFrameId())
                .setResourceId(proc.getProcId()).build();
        frameCompleteHandler.handleFrameCompleteReport(
                FrameCompleteReport.newBuilder().setFrame(info).setExitStatus(exitStatus).build());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testConfiguredExitStatusDelaysLayer() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");
        assertNull(layerDao.getLayerDetail(layer.getLayerId()).startAfter);

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        LayerDetail delayed = layerDao.getLayerDetail(layer.getLayerId());
        assertNotNull("A configured exit status must write the layer's start-after gate",
                delayed.startAfter);
        assertEquals("Automatic backoff: exit status " + LICENSE_EXIT_STATUS,
                delayed.startAfterReason);

        // The gate is the configured backoff into the future. Postgres current_timestamp is the
        // transaction's start time, which is somewhat before now, so only bound the window
        // loosely: what matters is that the configured duration was used and not some default.
        long millisOut = delayed.startAfter.getTime() - System.currentTimeMillis();
        assertTrue(
                "Expected a gate up to " + CONFIGURED_DELAY_MINUTES + " minutes out, got "
                        + millisOut + "ms",
                millisOut > 0 && millisOut <= CONFIGURED_DELAY_MINUTES * 60 * 1000L);
        assertTrue("Gate is implausibly close, the configured backoff was probably not used",
                millisOut > (CONFIGURED_DELAY_MINUTES - 2) * 60 * 1000L);

        // The frame itself is left retriable rather than dead: the layer gate is what holds it.
        assertEquals(FrameState.WAITING, frameDao.getFrameDetail(proc.getFrameId()).state);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testEatenFrameDoesNotDelayLayer() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");
        jobDao.updateAutoEat(job, true);

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, LICENSE_EXIT_STATUS);

        // Auto-eat wins over the delay rule: nothing is going to retry an eaten frame, so
        // delaying the layer would only keep the job from finishing.
        assertEquals(FrameState.EATEN, frameDao.getFrameDetail(proc.getFrameId()).state);
        assertNull("An eaten frame must not delay its layer",
                layerDao.getLayerDetail(layer.getLayerId()).startAfter);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnconfiguredExitStatusDoesNotDelayLayer() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, 1);

        assertNull("An exit status with no rule must not delay its layer",
                layerDao.getLayerDetail(layer.getLayerId()).startAfter);
        assertNull(layerDao.getLayerDetail(layer.getLayerId()).startAfterReason);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSuccessfulFrameDoesNotDelayLayer() {
        JobDetail job = jobManager.findJobDetail("pipe-default-testuser_test0");
        LayerDetail layer = layerDao.findLayerDetail(job, "layer0");

        VirtualProc proc = bookOneFrame(job);
        reportFrameComplete(proc, 0);

        assertNull("A successful frame must not delay its layer",
                layerDao.getLayerDetail(layer.getLayerId()).startAfter);
    }
}
