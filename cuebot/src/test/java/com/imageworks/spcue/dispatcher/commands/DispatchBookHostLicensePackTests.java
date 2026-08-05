
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

package com.imageworks.spcue.dispatcher.commands;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;

import org.junit.Before;
import org.junit.Test;
import org.mockito.InOrder;
import org.springframework.mock.env.MockEnvironment;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobEntity;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.LicenseBookingGate;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.service.JobManager;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anySet;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link DispatchBookHostLicensePack}: pack jobs are dispatched before the normal
 * booking order, the preferred show survives packing, and a pack pass that finds nothing still
 * falls through to the exact booking the host would have received without packing.
 */
public class DispatchBookHostLicensePackTests {

    private static final List<RunningFrameInfo> RUNNING =
            Collections.singletonList(RunningFrameInfo.newBuilder().setLayerId("l1").build());

    private DispatchHost host;
    private LicenseBookingGate gate;
    private JobManager jobManager;
    private Dispatcher dispatcher;
    private MockEnvironment env;

    @Before
    public void setUp() {
        host = new DispatchHost();
        host.id = "host1";
        host.name = "host1";
        host.idleCores = 800;
        host.idleMemory = 8_000_000L;
        host.idleGpus = 0;
        host.idleGpuMemory = 0;

        gate = mock(LicenseBookingGate.class);
        jobManager = mock(JobManager.class);
        dispatcher = mock(Dispatcher.class);
        env = new MockEnvironment();
        env.setProperty("dispatcher.memory.mem_reserved_min", "262144");
        env.setProperty("dispatcher.memory.mem_gpu_reserved_min", "0");
    }

    private DispatchBookHostLicensePack command(ShowEntity preferredShow) {
        return new DispatchBookHostLicensePack(host, RUNNING, preferredShow, gate, jobManager,
                dispatcher, env);
    }

    @Test
    public void packJobsDispatchedBeforeNormalBooking() {
        JobInterface job = new JobEntity("job1");
        when(gate.hostBasedLicensesRunning(RUNNING))
                .thenReturn(new HashSet<>(Arrays.asList("hengine")));
        when(gate.findPackableJobs(anySet(), eq(host), anyInt())).thenReturn(Arrays.asList("job1"));
        when(jobManager.getJob("job1")).thenReturn(job);

        command(null).run();

        InOrder order = inOrder(dispatcher);
        order.verify(dispatcher).dispatchHost(host, job);
        order.verify(dispatcher).dispatchHost(host);
    }

    @Test
    public void preferredShowSurvivesPacking() {
        ShowEntity show = new ShowEntity();
        show.id = "show1";
        show.name = "show1";
        JobInterface job = new JobEntity("job1");
        when(gate.hostBasedLicensesRunning(RUNNING))
                .thenReturn(new HashSet<>(Arrays.asList("hengine")));
        when(gate.findPackableJobs(anySet(), eq(host), anyInt())).thenReturn(Arrays.asList("job1"));
        when(jobManager.getJob("job1")).thenReturn(job);

        command(show).run();

        InOrder order = inOrder(dispatcher);
        order.verify(dispatcher).dispatchHost(host, job);
        order.verify(dispatcher).dispatchHost(host, show);
    }

    @Test
    public void emptyPackStillBooksNormally() {
        when(gate.hostBasedLicensesRunning(RUNNING)).thenReturn(Collections.emptySet());

        command(null).run();

        verify(dispatcher, never()).dispatchHost(eq(host), any(JobInterface.class));
        verify(dispatcher).dispatchHost(host);
    }

    @Test
    public void gateFailureStillBooksNormally() {
        when(gate.hostBasedLicensesRunning(RUNNING)).thenThrow(new RuntimeException("db down"));

        command(null).run();

        verify(dispatcher).dispatchHost(host);
    }
}
