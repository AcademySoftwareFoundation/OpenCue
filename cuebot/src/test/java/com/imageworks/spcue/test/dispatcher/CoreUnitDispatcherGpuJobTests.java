
/*
 * Copyright (c) 2018 Sony Pictures Imageworks Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */



package com.imageworks.spcue.test.dispatcher;

import com.imageworks.spcue.*;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.*;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.List;

import static org.junit.Assert.assertEquals;

@ContextConfiguration
public class CoreUnitDispatcherGpuJobTests extends TransactionalTest {

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Autowired
    HostManager hostManager;

    @Autowired
    AdminManager adminManager;

    @Autowired
    GroupManager groupManager;

    @Autowired
    Dispatcher dispatcher;

    private static final String HOSTNAME = "beta";

    private static final String JOBNAME =
        "pipe-dev.cue-middletier_shell_dispatch_gpu_test_v1";

    private static final String TARGET_JOB =
        "pipe-dev.cue-middletier_shell_dispatch_gpu_test_v2";

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_gpu_test.xml"));
    }

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        RenderHost host = RenderHost.newBuilder()
                .setName(HOSTNAME)
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem((int) CueUtil.GB8)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem((int) CueUtil.GB8)
                .setTotalSwap((int) CueUtil.GB2)
                .setNimbyEnabled(false)
                .setNumProcs(1)
                .setCoresPerProc(200)
                .addTags("test")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();

        hostManager.createHost(host,
                adminManager.findAllocationDetail("spi", "general"));
    }

    public JobDetail getJob() {
        return jobManager.findJobDetail(JOBNAME);
    }

    public JobDetail getTargetJob() {
        return jobManager.findJobDetail(TARGET_JOB);
    }

    public DispatchHost getHost() {
        return hostManager.findDispatchHost(HOSTNAME);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchHost() {
        DispatchHost host = getHost();

        List<VirtualProc> procs =  dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchGpuRemovedHostToNonGpuJob() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        host.idleMemory = (long) host.idleMemory - Math.min(CueUtil.GB4, host.idleMemory);
        host.idleCores = (int) host.idleCores - Math.min(100, host.idleCores);
        host.idleGpu = 0;
        List<VirtualProc> procs =  dispatcher.dispatchHost(host, job);
        assertEquals(0, procs.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchGpuHostToGroup() {
        DispatchHost host = getHost();
        JobDetail job = getJob();
        GroupDetail group = groupManager.getGroupDetail(job);

        List<VirtualProc> procs =  dispatcher.dispatchHost(host, group);
        assertEquals(1, procs.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchGpuHostToShowNoPrefer() {
        DispatchHost host = getHost();
        JobDetail job = getJob();
        ShowEntity show = adminManager.findShowEntity("edu");

        List<VirtualProc> procs =  dispatcher.dispatchHost(host);
        assertEquals(1, procs.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDispatchRemovedGpuHostToShowPrefer() {
        DispatchHost host = getHost();
        JobDetail job = getJob();
        ShowEntity show = adminManager.findShowEntity("edu");

        List<VirtualProc> procs =  dispatcher.dispatchHost(host, show);
        assertEquals(0, procs.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void dispatchProcToJob() {
        DispatchHost host = getHost();
        JobDetail job = getJob();

        List<VirtualProc> procs = dispatcher.dispatchHost(host, job);
        VirtualProc proc = procs.get(0);
        dispatcher.dispatchProcToJob(proc, job);
    }
}

