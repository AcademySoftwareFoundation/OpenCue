
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

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import io.grpc.Status;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;
import org.springframework.core.env.Environment;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.PrometheusMetricsCollector;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.MaestroCompletionForwarder;
import com.imageworks.spcue.dispatcher.MaestroCompletionQueue;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RqdReportRunningFrameCompletionRequest;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the Maestro completion-forward relay: a legacy cuebot (maestro.enabled=no)
 * forwards a scheduler-managed show's completion reports to the isolated Maestro deployment, with
 * the legacy path as the fallback on every failure, a consecutive-failure breaker, and target
 * rotation. The wire is stood in for by overriding {@link MaestroCompletionForwarder#send}; the
 * handler is driven directly with mocked collaborators, like the ownership-fence tests.
 */
public class MaestroCompletionForwarderTests {

    private static final String RESOURCE_ID = "00000000-0000-0000-0000-000000000001";
    private static final String FRAME_ID = "00000000-0000-0000-0000-0000000000f1";
    private static final String JOB_ID = "00000000-0000-0000-0000-0000000000a1";
    private static final String LAYER_ID = "00000000-0000-0000-0000-0000000000b1";
    private static final String SHOW_ID = "00000000-0000-0000-0000-0000000000c1";
    private static final String TARGET_A = "leader:8443";
    private static final String TARGET_B = "standby:8443";

    private FrameCompleteHandler handler;
    private HostManager hostManager;
    private JobManager jobManager;
    private DispatchSupport dispatchSupport;
    private ShowDao showDao;
    private PrometheusMetricsCollector prometheusMetrics;

    private VirtualProc proc;
    private FrameCompleteReport report;

    /** Records every forward attempt; targets listed in {@code failing} refuse the send. */
    private static final class RecordingForwarder extends MaestroCompletionForwarder {
        final List<String> attempts = new ArrayList<String>();
        final Set<String> failing = new HashSet<String>();

        RecordingForwarder(Environment env) {
            super(env);
        }

        @Override
        protected void send(String target, RqdReportRunningFrameCompletionRequest request) {
            attempts.add(target);
            if (failing.contains(target)) {
                throw Status.UNAVAILABLE.withDescription("injected").asRuntimeException();
            }
        }
    }

    @Before
    public void setup() {
        wireHandler(null);
    }

    @After
    public void drainQueue() {
        MaestroCompletionQueue.drain();
    }

    /** Environment for the forwarder itself, with a short breaker cooldown for probe tests. */
    private Environment forwarderEnv(String targets, long cooldownSeconds) {
        Environment env = mock(Environment.class);
        when(env.getProperty("maestro.forward_completions_to", "")).thenReturn(targets);
        when(env.getProperty(anyString(), eq(Long.class), anyLong()))
                .thenAnswer(i -> i.getArgument(2));
        when(env.getProperty(anyString(), eq(Integer.class), anyInt()))
                .thenAnswer(i -> i.getArgument(2));
        when(env.getProperty("maestro.forward_breaker_cooldown_s", Long.class, 30L))
                .thenReturn(cooldownSeconds);
        return env;
    }

    private RecordingForwarder forwarder(String targets) {
        return forwarder(targets, 30L);
    }

    private RecordingForwarder forwarder(String targets, long cooldownSeconds) {
        RecordingForwarder fwd = new RecordingForwarder(forwarderEnv(targets, cooldownSeconds));
        fwd.setHostManager(hostManager);
        fwd.setShowDao(showDao);
        fwd.setPrometheusMetrics(prometheusMetrics);
        return fwd;
    }

    /**
     * Build the handler under a Maestro mode (null = the property is unset, the legacy dispatcher
     * owns every show), with enough of the stop-frame graph mocked for a report to process to the
     * end through the legacy path.
     */
    private void wireHandler(String maestroMode) {
        Environment env = mock(Environment.class);
        when(env.getProperty(eq("depend.satisfy_only_on_frame_success"), eq(Boolean.class),
                eq(true))).thenReturn(true);
        when(env.getProperty(anyString(), eq(Long.class), anyLong()))
                .thenAnswer(i -> i.getArgument(2));
        when(env.getProperty(anyString(), eq(Integer.class), anyInt()))
                .thenAnswer(i -> i.getArgument(2));
        when(env.getProperty("maestro.enabled", "no")).thenReturn(maestroMode);
        handler = new FrameCompleteHandler(env);

        hostManager = mock(HostManager.class);
        jobManager = mock(JobManager.class);
        dispatchSupport = mock(DispatchSupport.class);
        showDao = mock(ShowDao.class);
        prometheusMetrics = mock(PrometheusMetricsCollector.class);
        DispatchQueue dispatchQueue = mock(DispatchQueue.class);
        Dispatcher dispatcher = mock(Dispatcher.class);

        handler.setHostManager(hostManager);
        handler.setJobManager(jobManager);
        handler.setRedirectManager(mock(RedirectManager.class));
        handler.setDispatchSupport(dispatchSupport);
        handler.setDispatcher(dispatcher);
        handler.setDispatchQueue(dispatchQueue);
        handler.setJobManagerSupport(mock(JobManagerSupport.class));
        handler.setPrometheusMetrics(prometheusMetrics);
        handler.setShowDao(showDao);

        doAnswer(new Answer<Void>() {
            public Void answer(InvocationOnMock invocation) {
                ((KeyRunnable) invocation.getArgument(0)).run();
                return null;
            }
        }).when(dispatchQueue).execute(any(KeyRunnable.class));
        when(dispatcher.isTestMode()).thenReturn(false);

        proc = new VirtualProc();
        proc.id = RESOURCE_ID;
        proc.jobId = JOB_ID;
        proc.frameId = FRAME_ID;
        proc.showId = SHOW_ID;
        proc.hostName = "render-host-01";

        report = FrameCompleteReport.newBuilder()
                .setFrame(RunningFrameInfo.newBuilder().setResourceId(RESOURCE_ID)
                        .setFrameId(FRAME_ID).setFrameName("0001-render").setJobName("test-job")
                        .setLayerId(LAYER_ID).build())
                .setExitStatus(0).build();

        when(hostManager.getVirtualProc(RESOURCE_ID)).thenReturn(proc);

        DispatchJob job = new DispatchJob();
        job.id = JOB_ID;
        job.state = JobState.PENDING;
        job.maxRetries = 3;

        LayerDetail layer = new LayerDetail();
        layer.id = LAYER_ID;

        FrameDetail frameDetail = new FrameDetail();
        frameDetail.id = FRAME_ID;
        frameDetail.state = FrameState.RUNNING;
        frameDetail.exitStatus = 1;

        DispatchFrame frame = new DispatchFrame();
        frame.id = FRAME_ID;
        frame.state = FrameState.RUNNING;
        frame.layerId = LAYER_ID;
        frame.jobId = JOB_ID;

        when(jobManager.getDispatchJob(JOB_ID)).thenReturn(job);
        when(jobManager.getLayerDetail(LAYER_ID)).thenReturn(layer);
        when(jobManager.getFrameDetail(FRAME_ID)).thenReturn(frameDetail);
        when(jobManager.getDispatchFrame(FRAME_ID)).thenReturn(frame);
        when(dispatchSupport.stopFrame(eq(frame), any(FrameState.class), anyInt(), anyLong()))
                .thenReturn(true);
    }

    /** A managed show's report with the flag set is forwarded and not processed locally. */
    @Test
    public void managedShowReportIsForwardedNotProcessedLocally() {
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(true);
        RecordingForwarder fwd = forwarder(TARGET_A);
        handler.setCompletionForwarder(fwd);

        handler.handleFrameCompleteReport(report);

        assertEquals(List.of(TARGET_A), fwd.attempts);
        verify(dispatchSupport, never()).stopFrame(any(DispatchFrame.class), any(FrameState.class),
                anyInt(), anyLong());
        verify(hostManager, times(1)).getVirtualProc(RESOURCE_ID);
        verify(prometheusMetrics, times(1)).incrementCompletionForward("forwarded");
    }

    /** A legacy show's report is never forwarded, and its proc is read exactly once. */
    @Test
    public void legacyShowReportIsNeverForwardedAndProcReadOnce() {
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(false);
        RecordingForwarder fwd = forwarder(TARGET_A);
        handler.setCompletionForwarder(fwd);

        handler.handleFrameCompleteReport(report);

        assertTrue(fwd.attempts.isEmpty());
        verify(hostManager, times(1)).getVirtualProc(RESOURCE_ID);
        verify(dispatchSupport, times(1)).stopFrame(any(DispatchFrame.class),
                eq(FrameState.SUCCEEDED), anyInt(), anyLong());
    }

    /** With the flag unset the hook is inert: no forward, no proc read beyond today's. */
    @Test
    public void emptyFlagDisablesForwardingEntirely() {
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(true);
        RecordingForwarder fwd = forwarder("");
        handler.setCompletionForwarder(fwd);

        handler.handleFrameCompleteReport(report);

        assertTrue(fwd.attempts.isEmpty());
        verify(hostManager, times(1)).getVirtualProc(RESOURCE_ID);
        verify(dispatchSupport, times(1)).stopFrame(any(DispatchFrame.class),
                eq(FrameState.SUCCEEDED), anyInt(), anyLong());
    }

    /**
     * A forward failure processes the report locally with a FRESH proc read (the pre-send snapshot
     * is up to a deadline stale, and the run-ownership fence must not judge it), and no exception
     * surfaces to the gRPC layer (RQD already delivered its report successfully).
     */
    @Test
    public void forwardFailureFallsBackLocallyWithFreshProcRead() {
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(true);
        RecordingForwarder fwd = forwarder(TARGET_A);
        fwd.failing.add(TARGET_A);
        handler.setCompletionForwarder(fwd);

        handler.handleFrameCompleteReport(report);

        assertEquals(List.of(TARGET_A), fwd.attempts);
        verify(hostManager, times(2)).getVirtualProc(RESOURCE_ID);
        verify(dispatchSupport, times(1)).stopFrame(any(DispatchFrame.class),
                eq(FrameState.SUCCEEDED), anyInt(), anyLong());
        verify(prometheusMetrics, times(1)).incrementCompletionForward("fallback_error");
    }

    /**
     * The ownership fence judges the POST-send proc: a frame freed and rebooked while the forward
     * attempt was in flight must be diverted by the fresh read, never stopped off the stale
     * pre-send snapshot.
     */
    @Test
    public void forwardFailureFenceJudgesFreshProc() {
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(true);
        RecordingForwarder fwd = forwarder(TARGET_A);
        fwd.failing.add(TARGET_A);
        handler.setCompletionForwarder(fwd);

        VirtualProc freed = new VirtualProc();
        freed.id = RESOURCE_ID;
        freed.jobId = JOB_ID;
        freed.frameId = null;
        freed.showId = SHOW_ID;
        freed.hostName = "render-host-01";
        when(hostManager.getVirtualProc(RESOURCE_ID)).thenReturn(proc, freed);

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, never()).stopFrame(any(DispatchFrame.class), any(FrameState.class),
                anyInt(), anyLong());
    }

    /**
     * Three consecutive failures open the breaker: the next report takes the instant fallback with
     * no send attempt, and after the cooldown exactly one probe attempt is made.
     */
    @Test
    public void breakerOpensAfterConsecutiveFailuresAndProbesAfterCooldown()
            throws InterruptedException {
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(true);
        RecordingForwarder fwd = forwarder(TARGET_A, 1L);
        fwd.failing.add(TARGET_A);

        for (int i = 0; i < 3; i++) {
            assertFalse(fwd.forwardIfManaged(report).forwarded());
        }
        assertEquals(3, fwd.attempts.size());

        // Breaker open: instant fallback, no send.
        assertFalse(fwd.forwardIfManaged(report).forwarded());
        assertEquals(3, fwd.attempts.size());
        verify(prometheusMetrics, times(1)).incrementCompletionForward("fallback_breaker");

        // After the cooldown the next report is the probe; it succeeds and closes the breaker.
        Thread.sleep(1100);
        fwd.failing.clear();
        assertTrue(fwd.forwardIfManaged(report).forwarded());
        assertEquals(4, fwd.attempts.size());
        assertTrue(fwd.forwardIfManaged(report).forwarded());
        assertEquals(5, fwd.attempts.size());
    }

    /** A failed probe re-opens the breaker for another full cooldown. */
    @Test
    public void failedProbeReopensBreaker() throws InterruptedException {
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(true);
        RecordingForwarder fwd = forwarder(TARGET_A, 1L);
        fwd.failing.add(TARGET_A);

        for (int i = 0; i < 3; i++) {
            fwd.forwardIfManaged(report);
        }
        Thread.sleep(1100);
        fwd.forwardIfManaged(report);
        assertEquals(4, fwd.attempts.size());

        fwd.forwardIfManaged(report);
        assertEquals(4, fwd.attempts.size());
    }

    /** A cuebot with Maestro enabled never forwards regardless of the flag (loop protection). */
    @Test
    public void maestroEnabledCuebotNeverForwards() {
        wireHandler("managed");
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(true);
        MaestroCompletionForwarder fwd = mock(MaestroCompletionForwarder.class);
        handler.setCompletionForwarder(fwd);

        handler.handleFrameCompleteReport(report);

        verifyNoInteractions(fwd);
        assertEquals(1, MaestroCompletionQueue.drain().size());
    }

    /** Target rotation on failure: the target that failed is not the next attempt's target. */
    @Test
    public void rotatesTargetAfterFailure() {
        when(showDao.isSchedulerManaged(SHOW_ID)).thenReturn(true);
        RecordingForwarder fwd = forwarder(TARGET_A + "," + TARGET_B);
        fwd.failing.add(TARGET_A);

        assertFalse(fwd.forwardIfManaged(report).forwarded());
        assertTrue(fwd.forwardIfManaged(report).forwarded());
        assertEquals(List.of(TARGET_A, TARGET_B), fwd.attempts);
    }
}
