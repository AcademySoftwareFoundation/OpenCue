
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

import static org.junit.Assert.*;

import java.util.ArrayList;
import java.util.HashMap;

import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.transaction.TransactionConfiguration;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.Deed;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.Owner;
import com.imageworks.spcue.ShowDetail;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.util.CueUtil;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")

public class OwnerManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    OwnerManager ownerManager;

    @Resource
    AdminManager adminManager;

    @Resource
    HostManager hostManager;

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
                adminManager.findShowDetail("pipe"));

        Owner owner = ownerManager.findOwner("spongebob");
        assertEquals(owner.name, "spongebob");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteOwner() {
        ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        assertTrue(ownerManager.deleteOwner(
                ownerManager.findOwner("spongebob")));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetOwner() {
        Owner o1 = ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        Owner o2 = ownerManager.getOwner(o1.id);
        assertEquals(o1, o2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindOwner() {
        Owner o1 = ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        Owner o2 = ownerManager.findOwner(o1.name);
        assertEquals(o1, o2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetShow() {
        Owner o = ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        ShowDetail newShow = adminManager.findShowDetail("edu");
        ownerManager.setShow(o, newShow);

        String confirmShow = jdbcTemplate.queryForObject(
                "SELECT pk_show FROM owner WHERE pk_owner=?",
                String.class, o.id);

        assertEquals(newShow.id, confirmShow);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testTakeOwnership() {
        Owner o = ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        DispatchHost host = createHost();
        ownerManager.takeOwnership(o, host);
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testGetDeed() {
        Owner o = ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        DispatchHost host = createHost();
        Deed d = ownerManager.takeOwnership(o, host);

        assertEquals(d, ownerManager.getDeed(d.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetBlackoutTimes() {
        Owner o = ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        DispatchHost host = createHost();
        Deed d = ownerManager.takeOwnership(o, host);

        ownerManager.setBlackoutTime(d, 0, 3600);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_blackout_start FROM deed WHERE pk_deed=?",
                Integer.class, d.id));

        assertEquals(Integer.valueOf(3600), jdbcTemplate.queryForObject(
                "SELECT int_blackout_stop FROM deed WHERE pk_deed=?",
                Integer.class, d.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testEnableDisableBlackout() {
        Owner o = ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        DispatchHost host = createHost();
        Deed d = ownerManager.takeOwnership(o, host);

        ownerManager.setBlackoutTimeEnabled(d, true);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT b_blackout FROM deed WHERE pk_deed=?",
                Integer.class, d.id));

        ownerManager.setBlackoutTimeEnabled(d, false);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT b_blackout FROM deed WHERE pk_deed=?",
                Integer.class, d.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testRemoveDeed() {
        Owner o = ownerManager.createOwner("spongebob",
                adminManager.findShowDetail("pipe"));

        DispatchHost host = createHost();
        Deed d = ownerManager.takeOwnership(o, host);

        ownerManager.removeDeed(d);

    }
}

