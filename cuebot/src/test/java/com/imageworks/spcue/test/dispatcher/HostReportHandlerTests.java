
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

import com.imageworks.spcue.dispatcher.HostReportQueue;
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

import java.util.UUID;
import java.util.concurrent.TimeUnit;

import static org.junit.Assert.assertEquals;

@ContextConfiguration
public class HostReportHandlerTests extends TransactionalTest {

    @Resource
    AdminManager adminManager;

    @Resource
    HostManager hostManager;

    @Resource
    HostReportHandler hostReportHandler;

    @Resource
    Dispatcher dispatcher;

    private String hostname;
    private String hostname2;

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        hostname = UUID.randomUUID().toString().substring(0, 8);
        hostname2 = UUID.randomUUID().toString().substring(0, 8);
        hostManager.createHost(getRenderHost(hostname, HardwareState.UP),
                adminManager.findAllocationDetail("spi","general"));
        hostManager.createHost(getRenderHost(hostname2, HardwareState.UP),
                adminManager.findAllocationDetail("spi","general"));
    }

    private static CoreDetail getCoreDetail(int total, int idle, int booked, int locked) {
        return CoreDetail.newBuilder()
                .setTotalCores(total)
                .setIdleCores(idle)
                .setBookedCores(booked)
                .setLockedCores(locked)
                .build();
    }

    private DispatchHost getHost(String hostname) {
        return hostManager.findDispatchHost(hostname);
    }

    private static RenderHost getRenderHost(String hostname, HardwareState state) {
        return RenderHost.newBuilder()
                .setName(hostname)
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(0)
                .setTotalMcp(195430)
                .setTotalMem(8173264)
                .setTotalSwap(20960)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags("test")
                .setState(state)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReport() throws InterruptedException {
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report1 = HostReport.newBuilder()
                .setHost(getRenderHost(hostname, HardwareState.UP))
                .setCoreInfo(cores)
                .build();
        HostReport report2 = HostReport.newBuilder()
                .setHost(getRenderHost(hostname2, HardwareState.UP))
                .setCoreInfo(cores)
                .build();
        HostReport report1_2 = HostReport.newBuilder()
                .setHost(getRenderHost(hostname, HardwareState.DOWN))
                .setCoreInfo(getCoreDetail(200, 200, 100, 0))
                .build();

        hostReportHandler.handleHostReport(report1, false, System.currentTimeMillis());
        DispatchHost host = getHost(hostname);
        assertEquals(LockState.OPEN, host.lockState);
        assertEquals(HardwareState.UP, host.hardwareState);
        hostReportHandler.handleHostReport(report1_2, false, System.currentTimeMillis());
        host = getHost(hostname);
        assertEquals(HardwareState.DOWN, host.hardwareState);

        // Test Queue thread handling
        HostReportQueue queue = hostReportHandler.getReportQueue();
        // Make sure jobs flow normally without any nullpointer exception
        // Expecting results from a ThreadPool based class on JUnit is tricky
        // A future test will be developed to better address the behavior of
        // this feature
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report2); // HOSTNAME2
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report1_2); // HOSTNAME
    }

}

