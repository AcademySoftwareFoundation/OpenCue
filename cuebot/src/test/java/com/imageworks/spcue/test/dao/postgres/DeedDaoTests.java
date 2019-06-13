
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



package com.imageworks.spcue.test.dao.postgres;

import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DeedDao;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.OwnerManager;
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
public class DeedDaoTests  extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    OwnerManager ownerManager;

    @Autowired
    DeedDao deedDao;

    @Autowired
    AdminManager adminManager;

    @Autowired
    HostManager hostManager;

    public DispatchHost createHost() {

        RenderHost host = RenderHost.newBuilder()
                .setName("test_host")
                .setBootTime(1192369572)
                .setFreeMcp(76020)
                .setFreeMem(15290520)
                .setFreeSwap(2076)
                .setLoad(1)
                .setTotalMcp(19543)
                .setTotalMem((int) CueUtil.GB16)
                .setTotalSwap((int) CueUtil.GB16)
                .setNimbyEnabled(false)
                .setNumProcs(2)
                .setCoresPerProc(100)
                .addTags("general")
                .setState(HardwareState.UP)
                .setFacility("spi")
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
    public void testInsertDeed() {

        DispatchHost host = createHost();
        ShowInterface s = adminManager.findShowEntity("pipe");
        OwnerEntity o = ownerManager.createOwner("squarepants", s);
        DeedEntity d = deedDao.insertDeed(o, host);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));

        assertEquals(host.getName(), d.host);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void tesDeleteDeed() {

        DispatchHost host = createHost();
        ShowInterface s = adminManager.findShowEntity("pipe");
        OwnerEntity o = ownerManager.createOwner("squarepants", s);
        DeedEntity d = deedDao.insertDeed(o, host);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));

        assertTrue(deedDao.deleteDeed(d));

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));

        assertFalse(deedDao.deleteDeed(d));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void tesGetDeed() {

        DispatchHost host = createHost();
        ShowInterface s = adminManager.findShowEntity("pipe");
        OwnerEntity o = ownerManager.createOwner("squarepants", s);
        DeedEntity d = deedDao.insertDeed(o, host);

        DeedEntity d2 = deedDao.getDeed(d.id);

        assertEquals(d, d2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void tesGetDeeds() {

        DispatchHost host = createHost();
        ShowInterface s = adminManager.findShowEntity("pipe");
        OwnerEntity o = ownerManager.createOwner("squarepants", s);
        DeedEntity d = deedDao.insertDeed(o, host);

        assertEquals(1, deedDao.getDeeds(o).size());
        assertEquals(d, deedDao.getDeeds(o).get(0));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testEnableDisableBlackoutTime() {

        DispatchHost host = createHost();
        ShowInterface s = adminManager.findShowEntity("pipe");
        OwnerEntity o = ownerManager.createOwner("squarepants", s);
        DeedEntity d = deedDao.insertDeed(o, host);

        deedDao.updateBlackoutTimeEnabled(d, true);
        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_blackout FROM deed WHERE pk_deed=?",
                Boolean.class, d.getId()));

        deedDao.updateBlackoutTimeEnabled(d, false);
        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_blackout FROM deed WHERE pk_deed=?",
                Boolean.class, d.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetBlackOutTimes() {

        DispatchHost host = createHost();
        ShowInterface s = adminManager.findShowEntity("pipe");
        OwnerEntity o = ownerManager.createOwner("squarepants", s);
        DeedEntity d = deedDao.insertDeed(o, host);

        deedDao.setBlackoutTime(d, 3600, 7200);

        assertEquals(Integer.valueOf(3600), jdbcTemplate.queryForObject(
                "SELECT int_blackout_start FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));

        assertEquals(Integer.valueOf(7200), jdbcTemplate.queryForObject(
                "SELECT int_blackout_stop FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));
    }
}

