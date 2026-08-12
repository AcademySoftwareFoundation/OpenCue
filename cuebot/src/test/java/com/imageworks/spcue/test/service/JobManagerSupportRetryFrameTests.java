
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
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.test.util.ReflectionTestUtils;

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the kill-and-confirm-dead-before-release behavior of
 * {@link JobManagerSupport#retryFrame}. The legacy order released the frame (making it immediately
 * dispatchable) before the kill was even sent to RQD, so a retried running frame could be booked
 * onto a second host while the original render was still alive. These tests exercise the method
 * directly with mocked collaborators so the kill/confirm/release ordering can be asserted
 * deterministically without an embedded database.
 */
public class JobManagerSupportRetryFrameTests {

    private static final String KILL_BEFORE_RELEASE_PROPERTY =
            "dispatcher.kill_running_frame_before_release_enabled";
    private static final String RETRY_KILL_BUDGET_PROPERTY =
            "dispatcher.retry_frame_kill_budget_ms";

    private static final String FRAME_ID = "00000000-0000-0000-0000-0000000000f1";
    private static final String JOB_ID = "00000000-0000-0000-0000-0000000000a1";

    private JobManagerSupport jobManagerSupport;
    private JobManager jobManager;
    private HostManager hostManager;
    private RqdClient rqdClient;
    private DispatchSupport dispatchSupport;
    private RedirectManager redirectManager;
    private DependManager dependManager;
    private Environment env;

    private FrameDetail frame;
    private VirtualProc proc;
    private Source source;

    @Before
    public void setup() {
        jobManagerSupport = new JobManagerSupport();
        jobManager = mock(JobManager.class);
        hostManager = mock(HostManager.class);
        rqdClient = mock(RqdClient.class);
        dispatchSupport = mock(DispatchSupport.class);
        redirectManager = mock(RedirectManager.class);
        dependManager = mock(DependManager.class);
        env = mock(Environment.class);

        jobManagerSupport.setJobManager(jobManager);
        jobManagerSupport.setHostManager(hostManager);
        jobManagerSupport.setRqdClient(rqdClient);
        jobManagerSupport.setDispatchSupport(dispatchSupport);
        jobManagerSupport.setRedirectManager(redirectManager);
        jobManagerSupport.setDependManager(dependManager);
        ReflectionTestUtils.setField(jobManagerSupport, "env", env);

        // Kill-before-release enabled by default, with a full confirmation budget. Tests whose
        // render is confirmed gone on the first poll never sleep; tests that need the budget to be
        // spent set it explicitly.
        when(env.getProperty(eq(KILL_BEFORE_RELEASE_PROPERTY), eq(Boolean.class), eq(true)))
                .thenReturn(true);
        when(env.getProperty(eq(RETRY_KILL_BUDGET_PROPERTY), eq(Long.class), eq(10000L)))
                .thenReturn(10000L);

        frame = new FrameDetail();
        frame.id = FRAME_ID;
        frame.jobId = JOB_ID;
        frame.layerId = "00000000-0000-0000-0000-0000000000b1";
        frame.name = "0001-render";
        frame.state = FrameState.RUNNING;
        frame.version = 1;

        proc = new VirtualProc();
        proc.id = "00000000-0000-0000-0000-000000000001";
        proc.frameId = FRAME_ID;
        proc.jobId = JOB_ID;
        proc.hostName = "render-host-01";

        source = new Source("retry test");

        when(hostManager.findVirtualProc(frame)).thenReturn(proc);
        when(dispatchSupport.stopFrame(any(FrameInterface.class), eq(FrameState.WAITING), anyInt()))
                .thenReturn(true);
        when(dependManager.getWhatDependsOn(any(FrameInterface.class), anyBoolean()))
                .thenReturn(Collections.emptyList());
        when(dependManager.getWhatDependsOn(any(LayerInterface.class), anyBoolean()))
                .thenReturn(Collections.emptyList());
        when(jobManager.getJob(JOB_ID)).thenReturn(mock(JobInterface.class));
    }

    @Test
    public void killsAndConfirmsDeadBeforeReleasingFrame() {
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID)).thenReturn(false);

        jobManagerSupport.retryFrame(frame, source);

        InOrder inOrder = inOrder(rqdClient, dispatchSupport);
        inOrder.verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        inOrder.verify(rqdClient, times(1)).isFrameRunning(proc.hostName, FRAME_ID);
        inOrder.verify(dispatchSupport, times(1)).stopFrame(eq(frame), eq(FrameState.WAITING),
                anyInt());
        verify(jobManager, times(1)).updateJobState(any(JobInterface.class), eq(JobState.PENDING));
    }

    @Test
    public void registersRedirectBothBeforeTheKillAndAfterTheFrameIsWaiting() {
        // addRedirect only registers when the job has a frame this proc can be dispatched to. The
        // pre-kill attempt covers the report landing during confirmation, but at that point the
        // retried frame is still RUNNING, so on a job whose only remaining work is that frame it
        // finds nothing. The attempt after the stop is the one that registers there.
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID)).thenReturn(false);

        jobManagerSupport.retryFrame(frame, source);

        InOrder inOrder = inOrder(redirectManager, rqdClient, dispatchSupport);
        inOrder.verify(redirectManager, times(1)).addRedirect(eq(proc), any(JobInterface.class),
                eq(false), eq(source));
        inOrder.verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        inOrder.verify(dispatchSupport, times(1)).stopFrame(eq(frame), eq(FrameState.WAITING),
                anyInt());
        inOrder.verify(redirectManager, times(1)).addRedirect(eq(proc), any(JobInterface.class),
                eq(false), eq(source));
    }

    @Test
    public void doesNotRetryTheRedirectWhenTheFrameIsNotReleased() {
        // A deferred retry leaves the frame RUNNING, so there is no post-stop redirect attempt.
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID)).thenReturn(true);
        when(env.getProperty(eq(RETRY_KILL_BUDGET_PROPERTY), eq(Long.class), eq(10000L)))
                .thenReturn(0L);

        jobManagerSupport.retryFrame(frame, source);

        verify(redirectManager, times(1)).addRedirect(eq(proc), any(JobInterface.class), eq(false),
                eq(source));
    }

    @Test
    public void waitsForRenderToExitBeforeReleasing() {
        // The render is still alive on the first poll and gone on the second; a real budget is
        // needed so the poll loop is willing to wait for the second answer.
        when(env.getProperty(eq(RETRY_KILL_BUDGET_PROPERTY), eq(Long.class), eq(10000L)))
                .thenReturn(10000L);
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID)).thenReturn(true).thenReturn(false);

        jobManagerSupport.retryFrame(frame, source);

        verify(rqdClient, times(2)).isFrameRunning(proc.hostName, FRAME_ID);
        verify(dispatchSupport, times(1)).stopFrame(eq(frame), eq(FrameState.WAITING), anyInt());
    }

    @Test
    public void defersRetryWhenRenderOutlivesKillBudget() {
        // A budget shorter than one poll interval: the render is polled once, is still alive, and
        // the budget is spent before another poll is due.
        when(env.getProperty(eq(RETRY_KILL_BUDGET_PROPERTY), eq(Long.class), eq(10000L)))
                .thenReturn(200L);
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID)).thenReturn(true);

        jobManagerSupport.retryFrame(frame, source);

        // Fail closed: the frame must be left RUNNING and none of the release steps may run.
        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(rqdClient, times(1)).isFrameRunning(proc.hostName, FRAME_ID);
        verify(dispatchSupport, never()).stopFrame(any(FrameInterface.class), any(FrameState.class),
                anyInt());
        verify(jobManager, never()).updateFrameState(any(FrameInterface.class),
                any(FrameState.class));
        verify(jobManager, never()).updateJobState(any(JobInterface.class), any(JobState.class));
    }

    @Test
    public void skipsConfirmationPollWhenBudgetIsAlreadySpent() {
        // Each confirmation poll is a gRPC call bounded by grpc.rqd_task_deadline, so polling once
        // the shared budget is gone would let a bulk retry spend that deadline per frame on top of
        // the budget. Past the deadline the kill is still delivered and the frame is deferred.
        when(env.getProperty(eq(RETRY_KILL_BUDGET_PROPERTY), eq(Long.class), eq(10000L)))
                .thenReturn(0L);

        jobManagerSupport.retryFrame(frame, source);

        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
        verify(dispatchSupport, never()).stopFrame(any(FrameInterface.class), any(FrameState.class),
                anyInt());
    }

    @Test
    public void defersRetryWhenHostIsUnreachable() {
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID))
                .thenThrow(new RuntimeException("host unreachable"));

        jobManagerSupport.retryFrame(frame, source);

        verify(dispatchSupport, never()).stopFrame(any(FrameInterface.class), any(FrameState.class),
                anyInt());
        verify(jobManager, never()).updateFrameState(any(FrameInterface.class),
                any(FrameState.class));
    }

    @Test
    public void releasesWhenKillRpcFailsButRenderIsConfirmedGone() {
        // The kill RPC failing does not mean the render is alive; the confirmation poll decides.
        doThrow(new RuntimeException("kill rpc failed")).when(rqdClient).killFrame(eq(proc),
                anyString());
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID)).thenReturn(false);

        jobManagerSupport.retryFrame(frame, source);

        verify(dispatchSupport, times(1)).stopFrame(eq(frame), eq(FrameState.WAITING), anyInt());
    }

    @Test
    public void retriesFrameWithNoProcWithoutTouchingRqd() {
        when(hostManager.findVirtualProc(frame)).thenThrow(new EmptyResultDataAccessException(1));

        jobManagerSupport.retryFrame(frame, source);

        verify(rqdClient, never()).killFrame(any(VirtualProc.class), anyString());
        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
        verify(dispatchSupport, times(1)).stopFrame(eq(frame), eq(FrameState.WAITING), anyInt());
    }

    @Test
    public void forcesWaitingFromFreshReadWhenFrameAlreadyStopped() {
        // The frame was concurrently stopped (e.g. the killed render's own completion report landed
        // first and failed the frame): the fallback must re-read the frame and reset it to WAITING
        // at the fresh version.
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID)).thenReturn(false);
        when(dispatchSupport.stopFrame(any(FrameInterface.class), eq(FrameState.WAITING), anyInt()))
                .thenReturn(false);
        FrameDetail freshFrame = new FrameDetail();
        freshFrame.id = FRAME_ID;
        freshFrame.state = FrameState.DEAD;
        freshFrame.version = 3;
        when(jobManager.getFrameDetail(FRAME_ID)).thenReturn(freshFrame);

        jobManagerSupport.retryFrame(frame, source);

        verify(jobManager, times(1)).updateFrameState(freshFrame, FrameState.WAITING);
    }

    @Test
    public void doesNotForceWaitingWhenFrameIsRunningAgain() {
        // The frame was stopped and already re-dispatched by the time the fallback runs: forcing
        // WAITING now would free a frame that is being rendered.
        when(rqdClient.isFrameRunning(proc.hostName, FRAME_ID)).thenReturn(false);
        when(dispatchSupport.stopFrame(any(FrameInterface.class), eq(FrameState.WAITING), anyInt()))
                .thenReturn(false);
        FrameDetail freshFrame = new FrameDetail();
        freshFrame.id = FRAME_ID;
        freshFrame.state = FrameState.RUNNING;
        freshFrame.version = 3;
        when(jobManager.getFrameDetail(FRAME_ID)).thenReturn(freshFrame);

        jobManagerSupport.retryFrame(frame, source);

        verify(jobManager, never()).updateFrameState(any(FrameInterface.class),
                any(FrameState.class));
    }

    @Test
    public void bulkRetrySharesOneKillBudgetAcrossFrames() {
        // A zero budget means the shared deadline is already spent when the first frame is
        // processed. Every frame must still get its kill, none may be confirmed or released, and
        // no frame may spend a confirmation RPC, so a bulk retry cannot hold a manage thread for
        // one full budget per frame.
        when(env.getProperty(eq(RETRY_KILL_BUDGET_PROPERTY), eq(Long.class), eq(10000L)))
                .thenReturn(0L);

        FrameDetail frame2 = new FrameDetail();
        frame2.id = "00000000-0000-0000-0000-0000000000f2";
        frame2.jobId = JOB_ID;
        frame2.layerId = frame.layerId;
        frame2.name = "0002-render";
        frame2.state = FrameState.RUNNING;
        frame2.version = 1;

        VirtualProc proc2 = new VirtualProc();
        proc2.id = "00000000-0000-0000-0000-000000000002";
        proc2.frameId = frame2.id;
        proc2.jobId = JOB_ID;
        proc2.hostName = "render-host-02";
        when(hostManager.findVirtualProc(frame2)).thenReturn(proc2);

        FrameSearchInterface search = mock(FrameSearchInterface.class);
        when(jobManager.findFrames(search))
                .thenReturn(Arrays.<FrameInterface>asList(frame, frame2));

        jobManagerSupport.retryFrames(search, source);

        verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(rqdClient, times(1)).killFrame(eq(proc2), anyString());
        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
        // Fail closed for both: neither frame may be released while its render is unconfirmed.
        verify(dispatchSupport, never()).stopFrame(any(FrameInterface.class), any(FrameState.class),
                anyInt());
    }

    @Test
    public void usesLegacyReleaseThenKillOrderWhenDisabledByProperty() {
        when(env.getProperty(eq(KILL_BEFORE_RELEASE_PROPERTY), eq(Boolean.class), eq(true)))
                .thenReturn(false);

        jobManagerSupport.retryFrame(frame, source);

        InOrder inOrder = inOrder(dispatchSupport, rqdClient);
        inOrder.verify(dispatchSupport, times(1)).stopFrame(eq(frame), eq(FrameState.WAITING),
                anyInt());
        inOrder.verify(rqdClient, times(1)).killFrame(eq(proc), anyString());
        verify(rqdClient, never()).isFrameRunning(anyString(), anyString());
    }
}
