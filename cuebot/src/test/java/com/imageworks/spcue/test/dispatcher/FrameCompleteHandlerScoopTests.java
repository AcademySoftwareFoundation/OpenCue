
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

import java.util.List;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.core.env.Environment;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.PrometheusMetricsCollector;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.QueuedFrameCompletion;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * The post-complete worker: one scoop task at a time, re-armed while work remains, and a scoop
 * filed in phases that fail alone. An Error out of one batch must not leave the intake without a
 * worker, or the backlog would grow for good and the farm would stop completing. Inside a scoop,
 * one frame's failure costs that frame only, a failed counter batch is filed again per frame
 * exactly once, and a failed completion check never touches the counters again.
 */
public class FrameCompleteHandlerScoopTests {

    private FrameCompleteHandler handler;
    private PrometheusMetricsCollector prometheusMetrics;
    private DispatchSupport dispatchSupport;
    private JobManager jobManager;
    // The worker reuses one scoop list, so a mock sees it empty later: sizes are taken at the call.
    private final BlockingQueue<Integer> batchSizes = new LinkedBlockingQueue<Integer>();

    @Before
    public void setup() {
        wire(true);
    }

    @After
    public void teardown() {
        handler.shutdown();
    }

    private void wire(boolean satisfyDependOnlyOnFrameSuccess) {
        if (handler != null) {
            handler.shutdown();
        }
        Environment env = mock(Environment.class);
        when(env.getProperty(eq("depend.satisfy_only_on_frame_success"), eq(Boolean.class),
                eq(true))).thenReturn(satisfyDependOnlyOnFrameSuccess);
        when(env.getProperty(anyString(), eq(Long.class), anyLong()))
                .thenAnswer(i -> i.getArgument(2));
        when(env.getProperty(anyString(), eq(Integer.class), anyInt()))
                .thenAnswer(i -> i.getArgument(2));
        handler = new FrameCompleteHandler(env);
        prometheusMetrics = mock(PrometheusMetricsCollector.class);
        dispatchSupport = mock(DispatchSupport.class);
        jobManager = mock(JobManager.class);
        doAnswer(i -> {
            batchSizes.add(((List<?>) i.getArgument(0)).size());
            return null;
        }).when(dispatchSupport).updateUsageCountersBatch(any());
        handler.setPrometheusMetrics(prometheusMetrics);
        handler.setDispatchSupport(dispatchSupport);
        handler.setJobManager(jobManager);
        handler.setJobManagerSupport(mock(JobManagerSupport.class));
        handler.setHostManager(mock(HostManager.class));
        handler.setDispatcher(mock(Dispatcher.class));
        handler.setDispatchQueue(mock(DispatchQueue.class));
        handler.setRedirectManager(mock(RedirectManager.class));
    }

    private static QueuedFrameCompletion completion(String frameId) {
        return completion(frameId, FrameState.SUCCEEDED, 1, "show");
    }

    /**
     * All completions share one layer and one job; the show names the frame to the metrics mock.
     */
    private static QueuedFrameCompletion completion(String frameId, FrameState state, int runTime,
            String show) {
        DispatchJob job = new DispatchJob();
        job.id = "job";
        DispatchFrame frame = new DispatchFrame();
        frame.id = frameId;
        frame.layerId = "layer";
        frame.jobId = "job";
        frame.show = show;
        FrameDetail detail = new FrameDetail();
        detail.id = frameId;
        detail.state = FrameState.RUNNING;
        FrameCompleteReport report =
                FrameCompleteReport
                        .newBuilder().setRunTime(runTime).setFrame(RunningFrameInfo.newBuilder()
                                .setFrameId(frameId).setNumCores(8).setMaxRss(1000L).build())
                        .build();
        return new QueuedFrameCompletion(report, new VirtualProc(), job, new LayerDetail(), detail,
                frame, state, 0);
    }

    /**
     * Park the worker inside a scoop of its own, so the completions queued next wait in the queue
     * and land together in one later scoop. Counting the returned latch down lets the worker go.
     */
    private CountDownLatch parkTheWorker() throws InterruptedException {
        CountDownLatch parked = new CountDownLatch(1);
        CountDownLatch release = new CountDownLatch(1);
        doAnswer(i -> {
            parked.countDown();
            release.await(5, TimeUnit.SECONDS);
            return null;
        }).when(prometheusMetrics).recordFrameCompleted(any(), eq("blocker"), any());
        handler.queuePostOps(completion("blocker", FrameState.SUCCEEDED, 1, "blocker"));
        assertTrue(parked.await(5, TimeUnit.SECONDS));
        return release;
    }

    @Test
    public void anErrorInOneScoopDoesNotStopTheNextOne() {
        doThrow(new AssertionError("boom")).doNothing().when(prometheusMetrics)
                .recordFrameCompleted(any(), any(), any());
        handler.queuePostOps(completion("f1"));
        verify(prometheusMetrics, timeout(5000).times(1)).recordFrameCompleted(any(), any(), any());
        handler.queuePostOps(completion("f2"));
        verify(prometheusMetrics, timeout(5000).times(2)).recordFrameCompleted(any(), any(), any());
    }

    @Test
    public void aFrameThatFailsItsOwnFilingDoesNotStopTheScoop() throws InterruptedException {
        doThrow(new RuntimeException("boom")).when(prometheusMetrics).recordFrameCompleted(any(),
                eq("bad"), any());
        CountDownLatch release = parkTheWorker();
        handler.queuePostOps(completion("bad", FrameState.SUCCEEDED, 1, "bad"));
        handler.queuePostOps(completion("good", FrameState.SUCCEEDED, 1, "show"));
        release.countDown();
        verify(prometheusMetrics, timeout(5000)).recordFrameCompleted(any(), eq("show"), any());
        assertEquals(Integer.valueOf(1), batchSizes.poll(5, TimeUnit.SECONDS));
        assertEquals(Integer.valueOf(2), batchSizes.poll(5, TimeUnit.SECONDS));
    }

    @Test
    public void aSuccessReplacesAnEatenLayerRepresentative() throws InterruptedException {
        wire(false);
        CountDownLatch release = parkTheWorker();
        handler.queuePostOps(completion("eaten", FrameState.EATEN, 0, "show"));
        handler.queuePostOps(completion("done", FrameState.SUCCEEDED, 42, "show"));
        release.countDown();
        verify(jobManager, timeout(5000)).optimizeLayer(any(), eq(8), eq(1000L), eq(42));
    }

    @Test
    public void aFailedCounterBatchFilesEachFrameAloneOnce() throws InterruptedException {
        doThrow(new RuntimeException("boom")).when(dispatchSupport)
                .updateUsageCountersBatch(argThat(l -> l.size() == 2));
        CountDownLatch release = parkTheWorker();
        handler.queuePostOps(completion("f1"));
        handler.queuePostOps(completion("f2"));
        release.countDown();
        verify(dispatchSupport, timeout(5000).times(2)).updateUsageCounters(any(), anyInt());
        verify(dispatchSupport, times(2)).updateUsageCountersBatch(any());
    }

    @Test
    public void aFailedCompletionCheckNeverFilesTheCountersAgain() {
        when(jobManager.isLayerComplete(any())).thenThrow(new RuntimeException("boom"));
        handler.queuePostOps(completion("f1"));
        verify(jobManager, timeout(5000)).isLayerComplete(any());
        handler.queuePostOps(completion("f2"));
        verify(dispatchSupport, timeout(5000).times(2)).updateUsageCountersBatch(any());
        verify(dispatchSupport, never()).updateUsageCounters(any(), anyInt());
    }
}
