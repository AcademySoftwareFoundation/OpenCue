
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

package com.imageworks.spcue.dispatcher;

import java.util.UUID;

import org.junit.Test;
import org.springframework.mock.env.MockEnvironment;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;

import static org.junit.Assert.assertEquals;

/**
 * Unit tests for the license-denied exit-status handling in
 * {@link FrameCompleteHandler#determineFrameState}: a configured denied status requeues the frame
 * WAITING instead of marching it to DEAD, the per-frame requeue limit restores ordinary retry
 * accounting, and an unconfigured site sees no behaviour change at all.
 *
 * No Spring context: the handler is constructed directly with a MockEnvironment, which (re)writes
 * the static license-denied configuration each time, so every test sets up its own handler first.
 */
public class FrameCompleteHandlerLicenseTests {

    private static final int DENIED_EXIT = 11;

    private FrameCompleteHandler handler(String deniedStatuses, String requeueLimit) {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("scheduler.license.denied_exit_statuses", deniedStatuses);
        env.setProperty("scheduler.license.denied_requeue_limit", requeueLimit);
        return new FrameCompleteHandler(env);
    }

    /** A running frame that has exhausted its retries: DEAD unless something intervenes. */
    private static DispatchFrame retriedOutFrame() {
        DispatchFrame frame = new DispatchFrame();
        frame.id = UUID.randomUUID().toString();
        frame.state = FrameState.RUNNING;
        frame.retries = 5;
        return frame;
    }

    private static DispatchJob job() {
        DispatchJob job = new DispatchJob();
        job.maxRetries = 1;
        job.autoEat = false;
        return job;
    }

    private static LayerDetail layer() {
        LayerDetail layer = new LayerDetail();
        layer.timeout = 0;
        layer.timeout_llu = 0;
        return layer;
    }

    private static FrameCompleteReport report(int exitStatus) {
        return FrameCompleteReport.newBuilder().setExitStatus(exitStatus).setExitSignal(0)
                .setRunTime(60).setFrame(RunningFrameInfo.newBuilder().setLluTime(0).build())
                .setHost(RenderHost.newBuilder().setNimbyLocked(false).build()).build();
    }

    @Test
    public void deniedStatusRequeuesInsteadOfDead() {
        handler(String.valueOf(DENIED_EXIT), "10");
        assertEquals("license-denied exit must requeue, not kill", FrameState.WAITING,
                FrameCompleteHandler.determineFrameState(job(), layer(), retriedOutFrame(),
                        report(DENIED_EXIT)));
    }

    @Test
    public void unconfiguredSiteSeesNoBehaviourChange() {
        handler("", "10");
        assertEquals("without configured statuses the same exit must go DEAD", FrameState.DEAD,
                FrameCompleteHandler.determineFrameState(job(), layer(), retriedOutFrame(),
                        report(DENIED_EXIT)));
    }

    @Test
    public void otherExitStatusesUnaffected() {
        handler(String.valueOf(DENIED_EXIT), "10");
        assertEquals(FrameState.DEAD, FrameCompleteHandler.determineFrameState(job(), layer(),
                retriedOutFrame(), report(1)));
    }

    @Test
    public void requeueLimitRestoresNormalAccounting() {
        handler(String.valueOf(DENIED_EXIT), "2");
        DispatchFrame frame = retriedOutFrame();

        assertEquals(FrameState.WAITING, FrameCompleteHandler.determineFrameState(job(), layer(),
                frame, report(DENIED_EXIT)));
        FrameCompleteHandler.countLicenseDeniedRequeue(frame.getFrameId());

        assertEquals(FrameState.WAITING, FrameCompleteHandler.determineFrameState(job(), layer(),
                frame, report(DENIED_EXIT)));
        FrameCompleteHandler.countLicenseDeniedRequeue(frame.getFrameId());

        assertEquals("over the requeue limit the frame must fall back to ordinary accounting",
                FrameState.DEAD, FrameCompleteHandler.determineFrameState(job(), layer(), frame,
                        report(DENIED_EXIT)));
    }

    @Test
    public void zeroLimitMeansUnbounded() {
        handler(String.valueOf(DENIED_EXIT), "0");
        DispatchFrame frame = retriedOutFrame();
        for (int i = 0; i < 50; i++) {
            FrameCompleteHandler.countLicenseDeniedRequeue(frame.getFrameId());
        }
        assertEquals(FrameState.WAITING, FrameCompleteHandler.determineFrameState(job(), layer(),
                frame, report(DENIED_EXIT)));
    }
}
