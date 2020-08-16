
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



package com.imageworks.spcue.test.service;

import java.io.File;
import javax.annotation.Resource;

import com.google.common.collect.ImmutableList;
import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.EntityModificationError;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class HostManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    AdminManager adminManager;

    @Resource
    HostManager hostManager;

    @Resource
    HostDao hostDao;

    @Resource
    FacilityDao facilityDao;

    @Resource
    FrameDao frameDao;

    @Resource
    ProcDao procDao;

    @Resource
    AllocationDao allocationDao;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    OwnerManager ownerManager;

    private static final String HOST_NAME = "alpha1";

    public DispatchHost createHost() {

        RenderHost host = RenderHost.newBuilder()
                .setName(HOST_NAME)
                .setBootTime(1192369572)
                .setFreeMcp(7602)
                .setFreeMemory(15290520)
                .setFreeSwap(2076)
                .setLoad(1)
                .setTotalMcp(19543)
                .setTotalMemory((int) CueUtil.GB16)
                .setTotalSwap(2076)
                .setNimbyEnabled(true)
                .setNumProcs(2)
                .setCoresPerProc(400)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .addAllTags(ImmutableList.of("linux", "64bit"))
                .setFreeGpuMemory((int) CueUtil.MB512)
                .setTotalGpuMemory((int) CueUtil.MB512)
                .build();

        hostDao.insertRenderHost(host,
                adminManager.findAllocationDetail("spi", "general"),
                false);

        return hostDao.findDispatchHost(HOST_NAME);
    }

    @Before
    public void setTestMode() {
        jobLauncher.testMode = true;
    }

    /**
     * Test that moves a host from one allocation to another.
     */
    @Test
    @Transactional
    @Rollback(true)
    public void setAllocation() {
        HostInterface h = createHost();
        hostManager.setAllocation(h,
                allocationDao.findAllocationEntity("spi", "general"));
    }

    /**
     * This test ensures you can't transfer a host that has a proc
     * assigned to a show without a subscription to the destination
     * allocation.
     */
    @Test(expected=EntityModificationError.class)
    @Transactional
    @Rollback(true)
    public void setBadAllocation() {

        jobLauncher.launch(new File("src/test/resources/conf/jobspec/facility.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        FrameDetail frameDetail = frameDao.findFrameDetail(job, "0001-pass_1");
        DispatchFrame frame = frameDao.getDispatchFrame(frameDetail.id);

        DispatchHost h = createHost();

        AllocationEntity ad =
            allocationDao.findAllocationEntity("spi", "desktop");

        VirtualProc proc = VirtualProc.build(h, frame);
        proc.frameId = frame.id;
        procDao.insertVirtualProc(proc);

        AllocationEntity ad2 = allocationDao.findAllocationEntity("spi", "desktop");
        hostManager.setAllocation(h, ad2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetPrefferedShow() {
        DispatchHost h = createHost();

        ShowInterface pshow = adminManager.findShowEntity("pipe");
        OwnerEntity o = ownerManager.createOwner("spongebob", pshow);

        ownerManager.takeOwnership(o, h);

        ShowInterface show = hostManager.getPreferredShow(h);
        assertEquals(pshow, show);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testisPrefferedShow() {
        DispatchHost h = createHost();

        assertFalse(hostManager.isPreferShow(h));

        ShowInterface pshow = adminManager.findShowEntity("pipe");
        OwnerEntity o = ownerManager.createOwner("spongebob", pshow);

        ownerManager.takeOwnership(o, h);

        ShowInterface show = hostManager.getPreferredShow(h);
        assertEquals(pshow, show);

        assertTrue(hostManager.isPreferShow(h));
    }

}

