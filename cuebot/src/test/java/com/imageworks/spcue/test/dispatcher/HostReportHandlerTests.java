
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

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.HostReportHandler;
import com.imageworks.spcue.FacilityInterface;
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
    private static final String NEW_HOSTNAME = "gamma";

    @Before
    public void setTestMode() {
        dispatcher.setTestMode(true);
    }

    @Before
    public void createHost() {
        hostManager.createHost(getRenderHost(),
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

    private static RenderHost getRenderHost() {
        return RenderHost.newBuilder()
                .setName(HOSTNAME)
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
                .setFreeGpuMem((int) CueUtil.MB512)
                .setTotalGpuMem((int) CueUtil.MB512)
                .build();
    }

    private static RenderHost getNewRenderHost(String tags) {
        return RenderHost.newBuilder()
                .setName(NEW_HOSTNAME)
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
                .addTags(tags)
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
                .setHost(getRenderHost())
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = getHost();
        assertEquals(host.lockState, LockState.OPEN);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithNewAllocation() {
        FacilityInterface facility = adminManager.getFacility(
                "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0");
        assertEquals(facility.getName(), "spi");

        AllocationEntity detail = new AllocationEntity();
        detail.name = "test";
        detail.tag = "test";
        adminManager.createAllocation(facility, detail);
        detail = adminManager.findAllocationDetail("spi", "test");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder()
                .setHost(getNewRenderHost("test"))
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), detail.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithExistentAllocation() {
        AllocationEntity alloc = adminManager.getAllocationDetail(
                "00000000-0000-0000-0000-000000000006");
        assertEquals(alloc.getName(), "spi.general");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder()
                .setHost(getNewRenderHost("general"))
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), alloc.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHandleHostReportWithNonExistentTags() {
        AllocationEntity alloc = adminManager.getAllocationDetail(
                "00000000-0000-0000-0000-000000000002");
        assertEquals(alloc.getName(), "lax.unassigned");

        boolean isBoot = true;
        CoreDetail cores = getCoreDetail(200, 200, 0, 0);
        HostReport report = HostReport.newBuilder()
                .setHost(getNewRenderHost("nonexistent"))
                .setCoreInfo(cores)
                .build();

        hostReportHandler.handleHostReport(report, isBoot);
        DispatchHost host = hostManager.findDispatchHost(NEW_HOSTNAME);
        assertEquals(host.getAllocationId(), alloc.id);
    }
}

