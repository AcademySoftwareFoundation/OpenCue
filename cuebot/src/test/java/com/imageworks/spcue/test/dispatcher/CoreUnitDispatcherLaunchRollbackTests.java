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

import java.util.Collections;

import org.junit.Before;
import org.junit.Test;
import org.springframework.mock.env.MockEnvironment;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.CoreUnitDispatcher;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.DispatcherException;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdLaunchUnknownOutcomeException;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Tests for the launch-failure rollback in {@link CoreUnitDispatcher}'s DispatchFrameTemplate, the
 * path used by production dispatching: a launch whose outcome is unknown (the RPC failed but the
 * frame may be running on the host) must be routed through
 * {@link DispatchSupport#resolveUnknownLaunchOutcome} instead of the legacy release-first rollback,
 * which frees the frame for re-dispatch while the render may still be alive (double-booking). A
 * launch failure that proves the frame did not start keeps the legacy rollback.
 */
public class CoreUnitDispatcherLaunchRollbackTests {

    private static final int FRAME_QUERY_MAX = 5;

    private CoreUnitDispatcher dispatcher;
    private DispatchSupport dispatchSupport;
    private RqdClient rqdClient;
    private JobDetail job;
    private DispatchFrame frame;
    private VirtualProc proc;

    @Before
    public void setup() {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("dispatcher.memory.mem_reserved_min", "262144");
        env.setProperty("dispatcher.memory.mem_gpu_reserved_default", "0");
        env.setProperty("dispatcher.memory.mem_gpu_reserved_min", "0");
        env.setProperty("dispatcher.frame_query_max", String.valueOf(FRAME_QUERY_MAX));

        dispatcher = new CoreUnitDispatcher(env);
        dispatchSupport = mock(DispatchSupport.class);
        rqdClient = mock(RqdClient.class);
        dispatcher.setDispatchSupport(dispatchSupport);
        dispatcher.setRqdClient(rqdClient);

        job = new JobDetail();
        job.id = "00000000-0000-0000-0000-0000000000j1";
        job.name = "test_job";

        frame = new DispatchFrame();
        frame.id = "00000000-0000-0000-0000-0000000000f1";
        frame.name = "0001-test_layer";

        proc = new VirtualProc();
        proc.id = "00000000-0000-0000-0000-000000000001";
        proc.frameId = frame.id;
        proc.hostName = "test-host";

        when(dispatchSupport.findNextDispatchFrames(job, proc, FRAME_QUERY_MAX))
                .thenReturn(Collections.singletonList(frame));
    }

    @Test
    public void dispatchProcToJobResolvesUnknownLaunchOutcomeWithoutReleasing() {
        doThrow(new RqdLaunchUnknownOutcomeException("deadline expired", null))
                .when(dispatchSupport).runFrame(proc, frame);

        // The template's DispatcherException is swallowed by dispatchProcToJob, so the call
        // returns normally.
        dispatcher.dispatchProcToJob(proc, job);

        verify(dispatchSupport, times(1)).resolveUnknownLaunchOutcome(proc, frame);
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class), anyString());
        verify(dispatchSupport, never()).clearFrame(any(DispatchFrame.class));
        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
    }

    @Test
    public void dispatchProcToJobKeepsLegacyRollbackForProvenLaunchFailures() {
        // A plain failure proves RQD rejected the launch: the legacy release-and-precaution-kill
        // rollback still applies.
        doThrow(new DispatcherException("rqd rejected the launch")).when(dispatchSupport)
                .runFrame(proc, frame);

        dispatcher.dispatchProcToJob(proc, job);

        verify(dispatchSupport, never()).resolveUnknownLaunchOutcome(any(VirtualProc.class),
                any(DispatchFrame.class));
        verify(dispatchSupport, times(1)).unbookProc(proc);
        verify(dispatchSupport, times(1)).clearFrame(frame);
        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
    }
}
