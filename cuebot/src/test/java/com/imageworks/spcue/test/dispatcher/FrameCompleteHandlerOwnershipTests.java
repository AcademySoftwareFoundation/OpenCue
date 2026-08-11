
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
import org.mockito.invocation.InvocationOnMock;
import org.mockito.stubbing.Answer;
import org.springframework.core.env.Environment;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.PrometheusMetricsCollector;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the run-ownership fence in {@link FrameCompleteHandler#handleFrameCompleteReport}:
 * a completion report may only stop the frame while its reporting proc still owns that frame. A
 * report from a superseded run (the frame was freed by retry/eat/lostProc/reaper and possibly
 * re-dispatched elsewhere) must never stop the frame, since doing so frees the frame under the run
 * currently rendering it and sustains a kill/report/free/rebook cascade. These tests drive the
 * handler directly with mocked collaborators; the embedded-database FrameCompleteHandlerTests cover
 * the applied-report paths.
 */
public class FrameCompleteHandlerOwnershipTests {

    private static final String RESOURCE_ID = "00000000-0000-0000-0000-000000000001";
    private static final String FRAME_ID = "00000000-0000-0000-0000-0000000000f1";
    private static final String OTHER_FRAME_ID = "00000000-0000-0000-0000-0000000000f2";
    private static final String JOB_ID = "00000000-0000-0000-0000-0000000000a1";
    private static final String LAYER_ID = "00000000-0000-0000-0000-0000000000b1";

    private FrameCompleteHandler handler;
    private HostManager hostManager;
    private JobManager jobManager;
    private RedirectManager redirectManager;
    private DispatchSupport dispatchSupport;
    private Dispatcher dispatcher;
    private DispatchQueue dispatchQueue;
    private PrometheusMetricsCollector prometheusMetrics;

    private VirtualProc proc;
    private FrameCompleteReport report;

    @Before
    public void setup() {
        Environment env = mock(Environment.class);
        when(env.getProperty(eq("depend.satisfy_only_on_frame_success"), eq(Boolean.class),
                eq(true))).thenReturn(true);
        handler = new FrameCompleteHandler(env);

        hostManager = mock(HostManager.class);
        jobManager = mock(JobManager.class);
        redirectManager = mock(RedirectManager.class);
        dispatchSupport = mock(DispatchSupport.class);
        dispatcher = mock(Dispatcher.class);
        dispatchQueue = mock(DispatchQueue.class);
        // Mocked rather than instantiated: the real collector registers static Prometheus
        // counters, which throws on double registration across tests.
        prometheusMetrics = mock(PrometheusMetricsCollector.class);

        handler.setHostManager(hostManager);
        handler.setJobManager(jobManager);
        handler.setRedirectManager(redirectManager);
        handler.setDispatchSupport(dispatchSupport);
        handler.setDispatcher(dispatcher);
        handler.setDispatchQueue(dispatchQueue);
        handler.setJobManagerSupport(mock(JobManagerSupport.class));
        handler.setPrometheusMetrics(prometheusMetrics);

        // Run queued dispatch tasks inline so redirect/unbook effects can be asserted directly.
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
        proc.hostName = "render-host-01";

        report = FrameCompleteReport.newBuilder()
                .setFrame(RunningFrameInfo.newBuilder().setResourceId(RESOURCE_ID)
                        .setFrameId(FRAME_ID).setFrameName("0001-render").setJobName("test-job")
                        .setLayerId(LAYER_ID).build())
                .setExitStatus(0).build();

        when(hostManager.getVirtualProc(RESOURCE_ID)).thenReturn(proc);
    }

    /**
     * The incident case: the frame was freed by a retry (proc row kept, pk_frame nulled) and is
     * already RUNNING on another host. The superseded report must not stop the frame; the idle
     * reporting proc is redirected instead.
     */
    @Test
    public void supersededReportDoesNotStopFrameRunningElsewhere() {
        proc.frameId = null;

        FrameDetail runningFrame = new FrameDetail();
        runningFrame.id = FRAME_ID;
        runningFrame.state = FrameState.RUNNING;
        when(jobManager.getFrameDetail(FRAME_ID)).thenReturn(runningFrame);
        when(redirectManager.hasRedirect(proc)).thenReturn(true);

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, never()).stopFrame(any(FrameInterface.class), any(FrameState.class),
                anyInt(), anyLong());
        verify(dispatchSupport, never()).unbookProc(proc);
        verify(redirectManager, times(1)).redirect(proc);
        // The fence must divert before the frame is even read for stopping.
        verify(jobManager, never()).getDispatchFrame(FRAME_ID);
    }

    /**
     * A resent duplicate whose proc has already booked its next frame is dropped outright:
     * unbooking the proc would orphan the newer frame.
     */
    @Test
    public void supersededReportForProcOnAnotherFrameIsDropped() {
        proc.frameId = OTHER_FRAME_ID;

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, never()).stopFrame(any(FrameInterface.class), any(FrameState.class),
                anyInt(), anyLong());
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(redirectManager, never()).redirect(any(VirtualProc.class));
    }

    /**
     * A report from the run that still owns the frame passes the fence and stops the frame.
     */
    @Test
    public void currentRunReportStopsFrame() {
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

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, times(1)).stopFrame(eq(frame), eq(FrameState.SUCCEEDED), anyInt(),
                anyLong());
    }

    /**
     * The frame was concurrently stopped and re-dispatched onto the same proc: the stale report
     * must be dropped instead of unbooking the proc from under the new live run.
     */
    @Test
    public void staleReportDoesNotUnbookProcRunningTheFrameAgain() {
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
        // The version fence rejects the stop: another actor got to the frame first.
        when(dispatchSupport.stopFrame(eq(frame), any(FrameState.class), anyInt(), anyLong()))
                .thenReturn(false);
        // A fresh read shows this proc owning the frame again: a newer run is alive on it.
        VirtualProc currentProc = new VirtualProc();
        currentProc.id = RESOURCE_ID;
        currentProc.jobId = JOB_ID;
        currentProc.frameId = FRAME_ID;
        currentProc.hostName = proc.hostName;
        when(hostManager.getVirtualProc(RESOURCE_ID)).thenReturn(proc, currentProc);

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(redirectManager, never()).redirect(any(VirtualProc.class));
    }

    /**
     * A stale exit-0 report dropped because its proc is running a newer instance of the same frame
     * is a discarded render result, and must be counted as such even though the proc is kept.
     */
    @Test
    public void droppedStaleSuccessReportIncrementsDroppedCounter() {
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
                .thenReturn(false);
        // A fresh read shows this proc owning the frame again: a newer run is alive on it.
        VirtualProc currentProc = new VirtualProc();
        currentProc.id = RESOURCE_ID;
        currentProc.jobId = JOB_ID;
        currentProc.frameId = FRAME_ID;
        currentProc.hostName = proc.hostName;
        when(hostManager.getVirtualProc(RESOURCE_ID)).thenReturn(proc, currentProc);

        handler.handleFrameCompleteReport(report);

        verify(prometheusMetrics, times(1)).incrementFrameCompleteDropped(0);
        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(redirectManager, never()).redirect(any(VirtualProc.class));
    }

    /**
     * A stale report whose frame row is gone entirely still releases the reporting proc (the
     * pre-existing release semantics), and is counted as a dropped report.
     */
    @Test
    public void staleReportWithMissingFrameRowStillReleasesProc() {
        proc.frameId = null;
        when(jobManager.getFrameDetail(FRAME_ID)).thenThrow(new EmptyResultDataAccessException(1));
        when(redirectManager.hasRedirect(proc)).thenReturn(false);

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, times(1)).unbookProc(proc);
        verify(prometheusMetrics, times(1)).incrementFrameCompleteDropped(0);
    }

    /**
     * A stale report for a frame that was stopped by another actor and not re-dispatched still
     * releases the idle reporting proc (legacy behavior).
     */
    @Test
    public void staleReportReleasesIdleProc() {
        DispatchJob job = new DispatchJob();
        job.id = JOB_ID;
        job.state = JobState.PENDING;
        job.maxRetries = 3;

        LayerDetail layer = new LayerDetail();
        layer.id = LAYER_ID;

        FrameDetail frameDetail = new FrameDetail();
        frameDetail.id = FRAME_ID;
        frameDetail.state = FrameState.WAITING;
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
                .thenReturn(false);
        when(redirectManager.hasRedirect(proc)).thenReturn(false);
        // The concurrent stop cleared the proc's assignment; the fresh read confirms it idle.
        VirtualProc idleProc = new VirtualProc();
        idleProc.id = RESOURCE_ID;
        idleProc.jobId = JOB_ID;
        idleProc.frameId = null;
        idleProc.hostName = proc.hostName;
        when(hostManager.getVirtualProc(RESOURCE_ID)).thenReturn(proc, idleProc);

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, times(1)).unbookProc(proc);
    }

    /**
     * The frame was stopped by another actor and this proc was then booked onto a different frame
     * before the stale report was disposed of. The pre-release fresh read must catch the newer
     * assignment and drop the report; releasing the proc would delete the row under the live run of
     * the other frame and orphan it.
     */
    @Test
    public void staleReportDoesNotReleaseProcReassignedToAnotherFrame() {
        DispatchJob job = new DispatchJob();
        job.id = JOB_ID;
        job.state = JobState.PENDING;
        job.maxRetries = 3;

        LayerDetail layer = new LayerDetail();
        layer.id = LAYER_ID;

        FrameDetail frameDetail = new FrameDetail();
        frameDetail.id = FRAME_ID;
        frameDetail.state = FrameState.WAITING;
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
                .thenReturn(false);
        // A fresh read shows the proc booked onto a different frame in the meantime.
        VirtualProc currentProc = new VirtualProc();
        currentProc.id = RESOURCE_ID;
        currentProc.jobId = JOB_ID;
        currentProc.frameId = OTHER_FRAME_ID;
        currentProc.hostName = proc.hostName;
        when(hostManager.getVirtualProc(RESOURCE_ID)).thenReturn(proc, currentProc);

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, never()).unbookProc(any(VirtualProc.class));
        verify(redirectManager, never()).redirect(any(VirtualProc.class));
    }

    /**
     * Regression guard for the orphaned path: when the reporting proc's row is gone and another
     * proc owns the frame, the pre-existing superseded guard in finalizeOrphanedFrameComplete still
     * refuses to stop the frame.
     */
    @Test
    public void orphanedSupersededReportStillIgnored() {
        when(hostManager.getVirtualProc(RESOURCE_ID))
                .thenThrow(new EmptyResultDataAccessException(1));

        DispatchJob job = new DispatchJob();
        job.id = JOB_ID;
        job.state = JobState.PENDING;

        LayerDetail layer = new LayerDetail();
        layer.id = LAYER_ID;

        FrameDetail frameDetail = new FrameDetail();
        frameDetail.id = FRAME_ID;
        frameDetail.state = FrameState.RUNNING;

        DispatchFrame frame = new DispatchFrame();
        frame.id = FRAME_ID;
        frame.state = FrameState.RUNNING;
        frame.layerId = LAYER_ID;
        frame.jobId = JOB_ID;

        when(jobManager.getDispatchFrame(FRAME_ID)).thenReturn(frame);
        when(jobManager.getFrameDetail(FRAME_ID)).thenReturn(frameDetail);
        when(jobManager.getDispatchJob(JOB_ID)).thenReturn(job);
        when(jobManager.getLayerDetail(LAYER_ID)).thenReturn(layer);
        // Another proc owns the frame now: the report is from a superseded run.
        when(hostManager.findVirtualProc(frame)).thenReturn(new VirtualProc());

        handler.handleFrameCompleteReport(report);

        verify(dispatchSupport, never()).stopFrame(any(FrameInterface.class), any(FrameState.class),
                anyInt(), anyLong());
    }
}
