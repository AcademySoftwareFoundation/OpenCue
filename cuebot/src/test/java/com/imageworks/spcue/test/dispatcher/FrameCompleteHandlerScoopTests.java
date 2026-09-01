
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

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doNothing;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * The post-complete worker: one scoop task at a time, re-armed while work remains. An Error out of
 * one batch must not leave the intake without a worker, or the backlog would grow for good and the
 * farm would stop completing.
 */
public class FrameCompleteHandlerScoopTests {

    private FrameCompleteHandler handler;
    private PrometheusMetricsCollector prometheusMetrics;

    @Before
    public void setup() {
        Environment env = mock(Environment.class);
        when(env.getProperty(eq("depend.satisfy_only_on_frame_success"), eq(Boolean.class),
                eq(true))).thenReturn(true);
        when(env.getProperty(anyString(), eq(Long.class), anyLong()))
                .thenAnswer(i -> i.getArgument(2));
        when(env.getProperty(anyString(), eq(Integer.class), anyInt()))
                .thenAnswer(i -> i.getArgument(2));
        handler = new FrameCompleteHandler(env);
        prometheusMetrics = mock(PrometheusMetricsCollector.class);
        handler.setPrometheusMetrics(prometheusMetrics);
        handler.setDispatchSupport(mock(DispatchSupport.class));
        handler.setJobManager(mock(JobManager.class));
        handler.setJobManagerSupport(mock(JobManagerSupport.class));
        handler.setHostManager(mock(HostManager.class));
        handler.setDispatcher(mock(Dispatcher.class));
        handler.setDispatchQueue(mock(DispatchQueue.class));
        handler.setRedirectManager(mock(RedirectManager.class));
    }

    private static QueuedFrameCompletion completion(String frameId) {
        DispatchJob job = new DispatchJob();
        job.id = "job";
        DispatchFrame frame = new DispatchFrame();
        frame.id = frameId;
        frame.layerId = "layer";
        frame.jobId = "job";
        FrameDetail detail = new FrameDetail();
        detail.id = frameId;
        detail.state = FrameState.RUNNING;
        FrameCompleteReport report = FrameCompleteReport.newBuilder()
                .setFrame(RunningFrameInfo.newBuilder().setFrameId(frameId).build()).build();
        return new QueuedFrameCompletion(report, new VirtualProc(), job, new LayerDetail(), detail,
                frame, FrameState.SUCCEEDED, 0);
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
}
