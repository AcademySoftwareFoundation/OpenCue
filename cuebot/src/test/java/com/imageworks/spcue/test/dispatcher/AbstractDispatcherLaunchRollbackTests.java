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

import org.junit.Before;
import org.junit.Test;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.AbstractDispatcher;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.DispatcherException;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdLaunchUnknownOutcomeException;

import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * Tests for the launch-failure rollback in {@link AbstractDispatcher}: a launch whose outcome is
 * unknown (the RPC failed but the frame may be running on the host) must be routed through
 * {@link DispatchSupport#resolveUnknownLaunchOutcome} instead of the legacy release-first rollback,
 * which frees the frame for re-dispatch while the render may still be alive (double-booking). A
 * launch failure that proves the frame did not start keeps the legacy rollback.
 */
public class AbstractDispatcherLaunchRollbackTests {

    private static class TestDispatcher extends AbstractDispatcher {
    }

    private TestDispatcher dispatcher;
    private DispatchSupport dispatchSupport;
    private RqdClient rqdClient;
    private DispatchFrame frame;
    private VirtualProc proc;

    @Before
    public void setup() {
        dispatcher = new TestDispatcher();
        dispatchSupport = mock(DispatchSupport.class);
        rqdClient = mock(RqdClient.class);
        dispatcher.setDispatchSupport(dispatchSupport);
        dispatcher.setRqdClient(rqdClient);

        frame = new DispatchFrame();
        frame.id = "00000000-0000-0000-0000-0000000000f1";
        frame.name = "0001-test_layer";

        proc = new VirtualProc();
        proc.id = "00000000-0000-0000-0000-000000000001";
        proc.frameId = frame.id;
        proc.hostName = "test-host";
    }

    private void failLaunchWith(RuntimeException e) {
        doThrow(e).when(dispatchSupport).runFrame(proc, frame);
    }

    @Test
    public void dispatchHostResolvesUnknownLaunchOutcomeWithoutReleasing() {
        failLaunchWith(new RqdLaunchUnknownOutcomeException("deadline expired", null));

        try {
            dispatcher.dispatchHost(frame, proc);
            fail("expected DispatcherException to stop booking the host");
        } catch (DispatcherException expected) {
        }

        verify(dispatchSupport, times(1)).resolveUnknownLaunchOutcome(proc, frame);
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class), anyString());
        verify(dispatchSupport, never()).clearFrame(any(DispatchFrame.class));
        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
    }

    @Test
    public void dispatchProcResolvesUnknownLaunchOutcomeWithoutReleasing() {
        failLaunchWith(new RqdLaunchUnknownOutcomeException("connection dropped", null));

        try {
            dispatcher.dispatchProc(frame, proc);
            fail("expected DispatcherException");
        } catch (DispatcherException expected) {
        }

        verify(dispatchSupport, times(1)).resolveUnknownLaunchOutcome(proc, frame);
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class), anyString());
        verify(dispatchSupport, never()).clearFrame(any(DispatchFrame.class));
        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
    }

    @Test
    public void dispatchHostKeepsLegacyRollbackForProvenLaunchFailures() {
        // A plain failure proves RQD rejected the launch: the legacy release-and-precaution-kill
        // rollback still applies.
        failLaunchWith(new DispatcherException("rqd rejected the launch"));

        try {
            dispatcher.dispatchHost(frame, proc);
            fail("expected DispatcherException to stop booking the host");
        } catch (DispatcherException expected) {
        }

        verify(dispatchSupport, never()).resolveUnknownLaunchOutcome(any(VirtualProc.class),
                any(DispatchFrame.class));
        verify(dispatchSupport, times(1)).unbookProc(proc);
        verify(dispatchSupport, times(1)).clearFrame(frame);
        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
    }

    @Test
    public void dispatchProcKeepsLegacyRollbackForProvenLaunchFailures() {
        failLaunchWith(new DispatcherException("rqd rejected the launch"));

        try {
            dispatcher.dispatchProc(frame, proc);
            fail("expected DispatcherException");
        } catch (DispatcherException expected) {
        }

        verify(dispatchSupport, never()).resolveUnknownLaunchOutcome(any(VirtualProc.class),
                any(DispatchFrame.class));
        verify(dispatchSupport, times(1)).unbookProc(proc);
        verify(dispatchSupport, times(1)).clearFrame(frame);
        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
    }

    @Test
    public void successfulDispatchTouchesNoRollbackPath() {
        assertTrue(dispatcher.dispatchHost(frame, proc));

        verify(dispatchSupport, times(1)).startFrameAndProc(proc, frame);
        verify(dispatchSupport, times(1)).runFrame(proc, frame);
        verify(dispatchSupport, never()).resolveUnknownLaunchOutcome(any(VirtualProc.class),
                any(DispatchFrame.class));
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(dispatchSupport, never()).clearFrame(any(DispatchFrame.class));
    }
}
