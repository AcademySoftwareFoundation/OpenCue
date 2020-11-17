
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
import com.imageworks.spcue.dispatcher.commands.DispatchHandleHostReport;
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
public class HostReportHandlerTests extends TransactionalTest {

    @Resource
    AdminManager adminManager;

    @Resource
    HostManager hostManager;

    @Resource
    HostReportHandler hostReportHandler;

    @Resource
    Dispatcher dispatcher;

    private static final String HOSTNAME = "beta";
    private static final String HOSTNAME2 = "alpha";

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        hostManager.createHost(getRenderHost(HOSTNAME),
                adminManager.findAllocationDetail("spi","general"));
        hostManager.createHost(getRenderHost(HOSTNAME2),
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

    private DispatchHost getHost() {
        return hostManager.findDispatchHost(HOSTNAME);
    }

    private static RenderHost getRenderHost(String hostname) {
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
                .setState(HardwareState.UP)
                .setFacility("spi")
                .putAttributes("SP_OS", "Linux")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReport() {
        boolean isBoot = false;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder()
                .setHost(getRenderHost(HOSTNAME))
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = getHost();
        assertEquals(host.lockState, LockState.OPEN);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleQueue() {
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report1 = HostReport.newBuilder()
                .setHost(getRenderHost(HOSTNAME))
                .setCoreInfo(cores)
                .build();
        HostReport report2 = HostReport.newBuilder()
                .setHost(getRenderHost(HOSTNAME2))
                .setCoreInfo(cores)
                .build();
        HostReport report1_2 = HostReport.newBuilder()
                .setHost(getRenderHost(HOSTNAME))
                .setCoreInfo(getCoreDetail(100, 100, 0, 0))
                .build();

        // Set poolSize to zero to avoid executing the jobs
        HostReportQueue queue = hostReportHandler.getReportQueue();
        queue.setBlockExecution(true);
        hostReportHandler.queueHostReport(report1); // HOSTNAME
        hostReportHandler.queueHostReport(report2); // HOSTNAME2
        assertEquals(2, queue.getQueue().size());

        // Ensure first item is report1
        DispatchHandleHostReport handler = (DispatchHandleHostReport) queue.getQueue().peek();
        long insertTime = handler.getReportTime();
        assertEquals(HOSTNAME, handler.getHostName());
        assertEquals(report1.getCoreInfo().getTotalCores(), handler.getHostReport().getCoreInfo().getTotalCores());

        // Add another report for same host as report1
        hostReportHandler.queueHostReport(report1_2);
        // report1_2 should have replaced report1, but kept the same insertTime and order
        handler = (DispatchHandleHostReport) queue.getQueue().peek();
        assertEquals(HOSTNAME, handler.getHostName());
        assertEquals(insertTime, handler.getReportTime());
        assertEquals(report1_2.getCoreInfo().getTotalCores(), handler.getHostReport().getCoreInfo().getTotalCores());

        // Queue size shouldn't change
        assertEquals(2, queue.getQueue().size());
    }

}

