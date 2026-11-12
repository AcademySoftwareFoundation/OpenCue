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

package com.imageworks.spcue.test.service;

import java.util.Arrays;
import java.util.Collections;

import org.junit.Before;
import org.junit.Test;
import org.mockito.InOrder;
import org.springframework.core.env.Environment;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link JobManagerSupport#killForHostLock}: confirmed kills return the frame to
 * WAITING with {@link Dispatcher#EXIT_STATUS_HOST_LOCKED} and no redirect, unconfirmed kills leave
 * the frame RUNNING.
 */
public class JobManagerSupportKillForHostLockTests {

    private static final String RETRY_KILL_BUDGET_PROPERTY =
            "dispatcher.retry_frame_kill_budget_ms";

    private JobManagerSupport jobManagerSupport;
    private JobManager jobManager;
    private HostManager hostManager;
    private RqdClient rqdClient;
    private DispatchSupport dispatchSupport;
    private RedirectManager redirectManager;
    private Environment env;

    private HostEntity host;
    private Source source;

    @Before
    public void setup() {
        jobManagerSupport = new JobManagerSupport();
        jobManager = mock(JobManager.class);
        hostManager = mock(HostManager.class);
        rqdClient = mock(RqdClient.class);
        dispatchSupport = mock(DispatchSupport.class);
        redirectManager = mock(RedirectManager.class);
        env = mock(Environment.class);

        jobManagerSupport.setJobManager(jobManager);
        jobManagerSupport.setHostManager(hostManager);
        jobManagerSupport.setRqdClient(rqdClient);
        jobManagerSupport.setDispatchSupport(dispatchSupport);
        jobManagerSupport.setRedirectManager(redirectManager);
        ReflectionTestUtils.setField(jobManagerSupport, "env", env);
        when(env.getProperty(eq(RETRY_KILL_BUDGET_PROPERTY), eq(Long.class), eq(10000L)))
                .thenReturn(10000L);
        when(dispatchSupport.stopFrame(any(FrameInterface.class), eq(FrameState.WAITING), anyInt()))
                .thenReturn(true);

        host = new HostEntity();
        host.id = "host-id";
        host.name = "workstation-01";
        source = new Source("HostApi:night-render");
    }

    private FrameDetail frame(String id, String name) {
        FrameDetail frame = new FrameDetail();
        frame.id = id;
        frame.name = name;
        frame.state = FrameState.RUNNING;
        frame.version = 1;
        when(jobManager.getFrameDetail(id)).thenReturn(frame);
        return frame;
    }

    private VirtualProc proc(String id, String frameId) {
        VirtualProc proc = new VirtualProc();
        proc.id = id;
        proc.frameId = frameId;
        proc.hostId = host.id;
        proc.hostName = host.name;
        return proc;
    }

    @Test
    public void confirmedKillStopsFrameAsWaitingWithoutRedirect() {
        FrameDetail frame = frame("frame-1", "0001-render");
        VirtualProc proc = proc("proc-1", frame.id);
        when(hostManager.findVirtualProcs(host)).thenReturn(Collections.singletonList(proc));
        when(rqdClient.isFrameRunning(host.name, frame.id)).thenReturn(false);

        JobManagerSupport.HostLockKillResult result =
                jobManagerSupport.killForHostLock(host, source);

        assertEquals(1, result.framesKilled);
        assertTrue(result.framesDeferred.isEmpty());
        InOrder inOrder = inOrder(rqdClient, dispatchSupport);
        inOrder.verify(rqdClient).killFrame(eq(proc), anyString());
        inOrder.verify(dispatchSupport).stopFrame(frame, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_HOST_LOCKED);
        inOrder.verify(dispatchSupport).unbookProc(eq(proc), anyString());
        verifyNoInteractions(redirectManager);
    }

    @Test
    public void unconfirmedKillLeavesFrameRunningAndDeferred() {
        FrameDetail alive = frame("frame-1", "0001-render");
        FrameDetail dead = frame("frame-2", "0002-render");
        VirtualProc aliveProc = proc("proc-1", alive.id);
        VirtualProc deadProc = proc("proc-2", dead.id);
        when(hostManager.findVirtualProcs(host)).thenReturn(Arrays.asList(aliveProc, deadProc));
        when(rqdClient.isFrameRunning(host.name, alive.id))
                .thenThrow(new RuntimeException("rqd unreachable"));
        when(rqdClient.isFrameRunning(host.name, dead.id)).thenReturn(false);

        JobManagerSupport.HostLockKillResult result =
                jobManagerSupport.killForHostLock(host, source);

        assertEquals(1, result.framesKilled);
        assertEquals(Collections.singletonList("0001-render"), result.framesDeferred);
        verify(dispatchSupport, never()).stopFrame(eq(alive), any(FrameState.class), anyInt());
        verify(dispatchSupport, never()).unbookProc(eq(aliveProc), anyString());
        verify(dispatchSupport).stopFrame(dead, FrameState.WAITING,
                Dispatcher.EXIT_STATUS_HOST_LOCKED);
    }

    @Test
    public void hostWithoutProcsKillsNothing() {
        when(hostManager.findVirtualProcs(host)).thenReturn(Collections.emptyList());

        JobManagerSupport.HostLockKillResult result =
                jobManagerSupport.killForHostLock(host, source);

        assertEquals(0, result.framesKilled);
        verifyNoInteractions(rqdClient);
    }
}
