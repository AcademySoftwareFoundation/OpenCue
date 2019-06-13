
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


package com.imageworks.spcue.test.service;

import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DeedDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.CueUtil;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.Assert.*;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class OwnerManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    OwnerManager ownerManager;

    @Autowired
    AdminManager adminManager;

    @Autowired
    HostManager hostManager;

    @Autowired
    DeedDao deedDao;

    @Autowired
    Whiteboard whiteboard;

    public DispatchHost createHost() {

        RenderHost host = RenderHost.newBuilder()
                .setName("test_host")
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(53500)
                .setFreeSwap(20760)
                .setLoad(1)
                .setTotalMcp(195430)
                .setTotalMem((int) CueUtil.GB16)
                .setTotalSwap((int) CueUtil.GB16)
                .setNimbyEnabled(true)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .setState(HardwareState.UP)
                .setFacility("spi")
                .addTags("general")
                .putAttributes("freeGpu", String.format("%d", CueUtil.MB512))
                .putAttributes("totalGpu", String.format("%d", CueUtil.MB512))
                .build();

        DispatchHost dh = hostManager.createHost(host);
        hostManager.setAllocation(dh,
                adminManager.findAllocationDetail("spi", "general"));

        return dh;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testCreateOwner() {
        ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        OwnerEntity owner = ownerManager.findOwner("spongebob");
        assertEquals(owner.name, "spongebob");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteOwner() {
        ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        assertTrue(ownerManager.deleteOwner(
                ownerManager.findOwner("spongebob")));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetOwner() {
        OwnerEntity o1 = ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        OwnerEntity o2 = ownerManager.getOwner(o1.id);
        assertEquals(o1, o2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindOwner() {
        OwnerEntity o1 = ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        OwnerEntity o2 = ownerManager.findOwner(o1.name);
        assertEquals(o1, o2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetShow() {
        OwnerEntity o = ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        ShowEntity newShow = adminManager.findShowEntity("edu");
        ownerManager.setShow(o, newShow);

        assertEquals(newShow.name, whiteboard.getOwner(o.name).getShow());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testTakeOwnership() {
        OwnerEntity o = ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        DispatchHost host = createHost();
        ownerManager.takeOwnership(o, host);
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testGetDeed() {
        OwnerEntity o = ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        DispatchHost host = createHost();
        DeedEntity d = ownerManager.takeOwnership(o, host);

        assertEquals(d, ownerManager.getDeed(d.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetBlackoutTimes() {
        OwnerEntity o = ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        DispatchHost host = createHost();
        DeedEntity d = ownerManager.takeOwnership(o, host);

        ownerManager.setBlackoutTime(d, 0, 3600);

        assertEquals(0, deedDao.getDeed(d.id).blackoutStart);
        assertEquals(3600, deedDao.getDeed(d.id).blackoutStop);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testEnableDisableBlackout() {
        OwnerEntity o = ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        DispatchHost host = createHost();
        DeedEntity d = ownerManager.takeOwnership(o, host);

        ownerManager.setBlackoutTimeEnabled(d, true);

        assertTrue(deedDao.getDeed(d.id).isBlackoutEnabled);

        ownerManager.setBlackoutTimeEnabled(d, false);

        assertFalse(deedDao.getDeed(d.id).isBlackoutEnabled);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testRemoveDeed() {
        OwnerEntity o = ownerManager.createOwner("spongebob",
                adminManager.findShowEntity("pipe"));

        DispatchHost host = createHost();
        DeedEntity d = ownerManager.takeOwnership(o, host);

        ownerManager.removeDeed(d);
    }
}

