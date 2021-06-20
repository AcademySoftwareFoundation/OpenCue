
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

import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.HostReportHandler;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.report.CoreDetail;
import com.imageworks.spcue.grpc.report.HostReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.test.TransactionalTest;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;

@ContextConfiguration
public class HostReportHandlerGpuTests extends TransactionalTest {

    @Resource
    AdminManager adminManager;

    @Resource
    HostManager hostManager;

    @Resource
    HostReportHandler hostReportHandler;

    @Resource
    Dispatcher dispatcher;

    private static final String HOSTNAME = "beta";

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    private static CoreDetail getCoreDetail(int total, int idle, int booked, int locked) {
        return CoreDetail.newBuilder()
                .setTotalCores(total)
                .setIdleCores(idle)
                .setBookedCores(booked)
                .setLockedCores(locked)
                .build();
    }

    private DispatchHost getHost() {
        return hostManager.findDispatchHost(HOSTNAME);
    }

    private static RenderHost getRenderHost() {
        return RenderHost.newBuilder()
                .setName(HOSTNAME)
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(0)
                .setTotalMcp(195430)
                .setTotalMem(1048576L * 4096)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags("test")
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .setNumGpus(64)
                .setFreeGpuMem(1048576L * 2000)
                .setTotalGpuMem(1048576L * 2048)
                .build();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReport() {
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder()
                .setHost(getRenderHost())
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, true);
        DispatchHost host = getHost();
        assertEquals(host.lockState, LockState.OPEN);
        assertEquals(host.memory, 4294443008L);
        assertEquals(host.gpus, 64);
        assertEquals(host.idleGpus, 64);
        assertEquals(host.gpuMemory, 1048576L * 2048);
        assertEquals(host.idleGpuMemory, 2147483648L);
    }
}

