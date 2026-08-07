
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

import java.time.Duration;
import java.util.Collections;
import java.util.Map;

import org.junit.Test;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.grpc.job.FrameExitStatus;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;

import static org.junit.Assert.assertEquals;

/**
 * Pure unit tests for the frame state and exit status decision logic in FrameCompleteHandler. No
 * Spring context or database required.
 */
public class FrameCompleteHandlerFrameStateTests {

    private static final int EXIT_SIGNAL_SIGTERM = 15;
    private static final int EXIT_SIGNAL_TIME_EXPIRED = 119;

    private DispatchJob job;
    private LayerDetail layer;
    private DispatchFrame frame;
    private FrameDetail frameDetail;
    private Map<Integer, Duration> delayRules = Collections.emptyMap();

    public FrameCompleteHandlerFrameStateTests() {
        job = new DispatchJob();
        job.maxRetries = 3;
        job.autoEat = false;

        layer = new LayerDetail();
        layer.timeout = 0;
        layer.timeout_llu = 0;

        frame = new DispatchFrame();
        frame.state = FrameState.RUNNING;
        frame.retries = 0;

        frameDetail = new FrameDetail();
        frameDetail.exitStatus = 0;
    }

    private FrameCompleteReport report(int exitStatus, int exitSignal) {
        return FrameCompleteReport.newBuilder()
                .setFrame(RunningFrameInfo.newBuilder().setFrameId("frame-id").build())
                .setHost(RenderHost.newBuilder().setNimbyLocked(false).build())
                .setExitStatus(exitStatus).setExitSignal(exitSignal).build();
    }

    private FrameState determine(FrameCompleteReport report) {
        return FrameCompleteHandler.determineFrameState(job, layer, frame, report, frameDetail,
                delayRules);
    }

    @Test
    public void testWaitingFramePreservesState() {
        frame.state = FrameState.WAITING;
        assertEquals(FrameState.WAITING, determine(report(1, 0)));
    }

    @Test
    public void testEatenFramePreservesState() {
        frame.state = FrameState.EATEN;
        assertEquals(FrameState.EATEN, determine(report(0, 0)));
    }

    @Test
    public void testDeadFrameBecomesDependWithoutAutoEat() {
        frame.state = FrameState.DEAD;
        assertEquals(FrameState.DEPEND, determine(report(1, 0)));
    }

    @Test
    public void testDeadFrameBecomesEatenWithAutoEat() {
        frame.state = FrameState.DEAD;
        job.autoEat = true;
        assertEquals(FrameState.EATEN, determine(report(1, 0)));
    }

    @Test
    public void testZeroExitStatusSucceeds() {
        assertEquals(FrameState.SUCCEEDED, determine(report(0, 0)));
    }

    @Test
    public void testNonZeroExitStatusWaitsForRetry() {
        assertEquals(FrameState.WAITING, determine(report(1, 0)));
    }

    @Test
    public void testSkipRetryWaitsEvenWhenRetriesExhausted() {
        frame.retries = job.maxRetries;
        assertEquals(FrameState.WAITING, determine(report(FrameExitStatus.SKIP_RETRY_VALUE, 0)));
    }

    @Test
    public void testTimeExpiredSignalWaitsEvenWhenRetriesExhausted() {
        frame.retries = job.maxRetries;
        assertEquals(FrameState.WAITING, determine(report(1, EXIT_SIGNAL_TIME_EXPIRED)));
    }

    @Test
    public void testFailedLaunchStatusWaitsWithRetriesLeft() {
        assertEquals(FrameState.WAITING, determine(report(FrameExitStatus.FAILED_LAUNCH_VALUE, 0)));
    }

    @Test
    public void testFailedLaunchSignalWaitsWithRetriesLeft() {
        assertEquals(FrameState.WAITING, determine(report(1, FrameExitStatus.FAILED_LAUNCH_VALUE)));
    }

    @Test
    public void testTimeExpiredSignalIgnoredWhenMaxRetriesZero() {
        job.maxRetries = 0;
        assertEquals(FrameState.DEAD, determine(report(1, EXIT_SIGNAL_TIME_EXPIRED)));
    }

    @Test
    public void testFailedLaunchDiesWhenRetriesExhausted() {
        frame.retries = job.maxRetries;
        assertEquals(FrameState.DEAD, determine(report(FrameExitStatus.FAILED_LAUNCH_VALUE, 0)));
    }

    @Test
    public void testFailedLaunchSignalDiesWhenRetriesExhausted() {
        frame.retries = job.maxRetries;
        assertEquals(FrameState.DEAD, determine(report(1, FrameExitStatus.FAILED_LAUNCH_VALUE)));
    }

    @Test
    public void testNimbyKillWaitsEvenWhenRetriesExhausted() {
        frame.retries = job.maxRetries;
        FrameCompleteReport report = FrameCompleteReport.newBuilder(report(1, EXIT_SIGNAL_SIGTERM))
                .setHost(RenderHost.newBuilder().setNimbyLocked(true).build()).build();
        assertEquals(FrameState.WAITING, determine(report));
    }

    @Test
    public void testAutoEatEatsFailedFrame() {
        job.autoEat = true;
        assertEquals(FrameState.EATEN, determine(report(1, 0)));
    }

    @Test
    public void testLluTimeoutKillsFrame() {
        layer.timeout_llu = 30;
        long staleLluTime = System.currentTimeMillis() / 1000 - 3600;
        FrameCompleteReport report = FrameCompleteReport.newBuilder(report(1, 0))
                .setFrame(RunningFrameInfo.newBuilder().setLluTime(staleLluTime).build()).build();
        assertEquals(FrameState.DEAD, determine(report));
    }

    @Test
    public void testLayerTimeoutKillsFrame() {
        layer.timeout = 10;
        FrameCompleteReport report =
                FrameCompleteReport.newBuilder(report(1, 0)).setRunTime(11 * 60).build();
        assertEquals(FrameState.DEAD, determine(report));
    }

    @Test
    public void testLongRunningFrameIsNotRetried() {
        FrameCompleteReport report = FrameCompleteReport.newBuilder(report(1, 0))
                .setRunTime(Dispatcher.FRAME_TIME_NO_RETRY + 1).build();
        assertEquals(FrameState.DEAD, determine(report));
    }

    @Test
    public void testRetriesExhaustedKillsFrame() {
        frame.retries = job.maxRetries;
        assertEquals(FrameState.DEAD, determine(report(1, 0)));
    }

    @Test
    public void testMemoryFailureStatusWaitsEvenWhenRetriesExhausted() {
        frame.retries = job.maxRetries;
        assertEquals(FrameState.WAITING,
                determine(report(Dispatcher.EXIT_STATUS_MEMORY_FAILURE, 0)));
    }

    @Test
    public void testMemoryFailureSignalWaitsEvenWhenRetriesExhausted() {
        frame.retries = job.maxRetries;
        assertEquals(FrameState.WAITING,
                determine(report(1, Dispatcher.EXIT_STATUS_MEMORY_FAILURE)));
    }

    @Test
    public void testDockerMemoryFailureWaitsEvenWhenRetriesExhausted() {
        frame.retries = job.maxRetries;
        assertEquals(FrameState.WAITING,
                determine(report(Dispatcher.DOCKER_EXIT_STATUS_MEMORY_FAILURE, 0)));
    }

    @Test
    public void testStoredMemoryFailureWaitsEvenWhenRetriesExhausted() {
        // A Cuebot-initiated memory kill stores the memory failure status on the frame while rqd
        // reports a plain kill; it must get the same retry exemption as an rqd-reported OOM.
        frame.retries = job.maxRetries;
        frameDetail.exitStatus = Dispatcher.EXIT_STATUS_MEMORY_FAILURE;
        assertEquals(FrameState.WAITING, determine(report(1, EXIT_SIGNAL_SIGTERM)));
    }

    private static final int LICENSE_EXIT_STATUS = 330;

    @Test
    public void testDelayRuleStatusWaits() {
        delayRules = Collections.singletonMap(LICENSE_EXIT_STATUS, Duration.ofMinutes(5));
        assertEquals(FrameState.WAITING, determine(report(LICENSE_EXIT_STATUS, 0)));
    }

    @Test
    public void testDelayRuleStatusWaitsEvenWhenRetriesExhausted() {
        delayRules = Collections.singletonMap(LICENSE_EXIT_STATUS, Duration.ofMinutes(5));
        frame.retries = job.maxRetries;
        assertEquals(FrameState.WAITING, determine(report(LICENSE_EXIT_STATUS, 0)));
    }

    @Test
    public void testAutoEatWinsOverDelayRule() {
        delayRules = Collections.singletonMap(LICENSE_EXIT_STATUS, Duration.ofMinutes(5));
        job.autoEat = true;
        assertEquals(FrameState.EATEN, determine(report(LICENSE_EXIT_STATUS, 0)));
    }

    @Test
    public void testDelayRuleStatusImmuneToTimeouts() {
        delayRules = Collections.singletonMap(LICENSE_EXIT_STATUS, Duration.ofMinutes(5));
        layer.timeout = 10;
        FrameCompleteReport report = FrameCompleteReport.newBuilder(report(LICENSE_EXIT_STATUS, 0))
                .setRunTime(11 * 60).build();
        assertEquals(FrameState.WAITING, determine(report));
    }

    @Test
    public void testDelayRuleUsesResolvedExitStatus() {
        // A stored memory-failure status wins over the reported status (resolveExitStatus), so a
        // delay rule keyed on the reported status must not match. With the layer timeout exceeded
        // the frame goes DEAD, proving the delay branch did not fire on the raw reported status.
        delayRules = Collections.singletonMap(LICENSE_EXIT_STATUS, Duration.ofMinutes(5));
        frameDetail.exitStatus = Dispatcher.EXIT_STATUS_MEMORY_FAILURE;
        layer.timeout = 10;
        FrameCompleteReport report = FrameCompleteReport.newBuilder(report(LICENSE_EXIT_STATUS, 0))
                .setRunTime(11 * 60).build();
        assertEquals(FrameState.DEAD, determine(report));
    }

    @Test
    public void testUnconfiguredDelayStatusFollowsNormalPath() {
        assertEquals(FrameState.WAITING, determine(report(LICENSE_EXIT_STATUS, 0)));
        frame.retries = job.maxRetries;
        assertEquals(FrameState.DEAD, determine(report(LICENSE_EXIT_STATUS, 0)));
    }

    @Test
    public void testResolveExitStatusPrefersStoredMemoryFailure() {
        FrameDetail frameDetail = new FrameDetail();
        frameDetail.exitStatus = Dispatcher.EXIT_STATUS_MEMORY_FAILURE;
        assertEquals(Dispatcher.EXIT_STATUS_MEMORY_FAILURE,
                FrameCompleteHandler.resolveExitStatus(report(0, 0), frameDetail));
    }

    @Test
    public void testResolveExitStatusUsesReportedStatus() {
        FrameDetail frameDetail = new FrameDetail();
        frameDetail.exitStatus = 1;
        assertEquals(7, FrameCompleteHandler.resolveExitStatus(report(7, 0), frameDetail));
    }
}
