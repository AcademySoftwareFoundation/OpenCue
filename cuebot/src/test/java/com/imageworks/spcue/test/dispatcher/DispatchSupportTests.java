
/*
 * Copyright Contributors to the OpenCue Project
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

import java.io.File;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;

@ContextConfiguration
public class DispatchSupportTests extends TransactionalTest {

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    HostManager hostManager;

    @Resource
    AdminManager adminManager;

    @Resource
    GroupManager groupManager;

    @Resource
    Dispatcher dispatcher;

    @Resource
    DispatchSupport dispatchSupport;

    @Resource
    FrameDao frameDao;

    private static final String HOSTNAME = "beta";

    private static final String JOBNAME =
        "pipe-dev.cue-testuser_shell_dispatch_test_v1";

    private static final String TARGET_JOB =
        "pipe-dev.cue-testuser_shell_dispatch_test_v2";

    @Before
    public void launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec_dispatch_test.xml"));
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
                .setFreeMemory(53500)
                .setFreeSwap(20760)
                .setLoad(0)
                .setTotalMcp(195430)
                .setTotalMemory(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(400)
                .addTags("test")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .setFreeGpuMemory((int) CueUtil.MB512)
                .setTotalGpuMemory((int) CueUtil.MB512)
                .build();

        hostManager.createHost(host,
                adminManager.findAllocationDetail("spi","general"));
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
    public void testDetermineIdleCores() {
        DispatchHost host = getHost();

        int grace_load = Dispatcher.CORE_LOAD_THRESHOLD * (host.cores / 100);

        // Machine is idle, no load.
        dispatchSupport.determineIdleCores(host, 0);
        assertEquals(800, host.idleCores);

        // Machine is idle but shows load of 200.
        host.idleCores = 800;
        dispatchSupport.determineIdleCores(host, 200);
        assertEquals(grace_load + 600, host.idleCores);

        //Machine is idle but has the grace load.
        host.idleCores = 800;
        dispatchSupport.determineIdleCores(host, grace_load);
        assertEquals(800, host.idleCores);

        //Machine has 100 units idle, grace_load -1
        host.idleCores = 100;
        dispatchSupport.determineIdleCores(host, 700 + grace_load - 1);
        assertEquals(100, host.idleCores);

        // Machine has 100 units idle, grace_load + 1
        host.idleCores = 100;
        dispatchSupport.determineIdleCores(host, 700 + grace_load + 1);
        assertEquals(99, host.idleCores);
    }
}

