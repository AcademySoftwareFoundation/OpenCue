
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



package com.imageworks.spcue.test.dao.oracle;

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
import com.imageworks.spcue.Show;
import com.imageworks.spcue.CueIce.HardwareState;
import com.imageworks.spcue.RqdIce.RenderHost;
import com.imageworks.spcue.dao.DeedDao;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.util.CueUtil;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
@TransactionConfiguration(transactionManager="transactionManager")
public class DeedDaoTests  extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    OwnerManager ownerManager;

    @Resource
    DeedDao deedDao;

    @Resource
    AdminManager adminManager;

    @Resource
    HostManager hostManager;

    public DispatchHost createHost() {

        RenderHost host = new RenderHost();
        host.name = "test_host";
        host.bootTime = 1192369572;
        host.freeMcp = 76020;
        host.freeMem = 53500;
        host.freeSwap = 20760;
        host.load = 1;
        host.totalMcp = 195430;
        host.totalMem = (int) CueUtil.GB16;
        host.totalSwap = (int) CueUtil.GB16;
        host.nimbyEnabled = false;
        host.numProcs = 2;
        host.coresPerProc = 100;
        host.tags = new ArrayList<String>();
        host.tags.add("general");
        host.state = HardwareState.Up;
        host.facility = "spi";
        host.attributes = new HashMap<String, String>();
        host.attributes.put("freeGpu", String.format("%d", CueUtil.MB512));
        host.attributes.put("totalGpu", String.format("%d", CueUtil.MB512));

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
        Show s = adminManager.findShowDetail("pipe");
        Owner o = ownerManager.createOwner("squarepants", s);
        Deed d = deedDao.insertDeed(o, host);

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
        Show s = adminManager.findShowDetail("pipe");
        Owner o = ownerManager.createOwner("squarepants", s);
        Deed d = deedDao.insertDeed(o, host);

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
        Show s = adminManager.findShowDetail("pipe");
        Owner o = ownerManager.createOwner("squarepants", s);
        Deed d = deedDao.insertDeed(o, host);

        Deed d2 = deedDao.getDeed(d.id);

        assertEquals(d, d2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void tesGetDeeds() {

        DispatchHost host = createHost();
        Show s = adminManager.findShowDetail("pipe");
        Owner o = ownerManager.createOwner("squarepants", s);
        Deed d = deedDao.insertDeed(o, host);

        assertEquals(1, deedDao.getDeeds(o).size());
        assertEquals(d, deedDao.getDeeds(o).get(0));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testEnableDisableBlackoutTime() {

        DispatchHost host = createHost();
        Show s = adminManager.findShowDetail("pipe");
        Owner o = ownerManager.createOwner("squarepants", s);
        Deed d = deedDao.insertDeed(o, host);

        deedDao.updateBlackoutTimeEnabled(d, true);
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT b_blackout FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));

        deedDao.updateBlackoutTimeEnabled(d, false);
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT b_blackout FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetBlackOutTimes() {

        DispatchHost host = createHost();
        Show s = adminManager.findShowDetail("pipe");
        Owner o = ownerManager.createOwner("squarepants", s);
        Deed d = deedDao.insertDeed(o, host);

        deedDao.setBlackoutTime(d, 3600, 7200);

        assertEquals(Integer.valueOf(3600), jdbcTemplate.queryForObject(
                "SELECT  int_blackout_start FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));

        assertEquals(Integer.valueOf(7200), jdbcTemplate.queryForObject(
                "SELECT int_blackout_stop FROM deed WHERE pk_deed=?",
                Integer.class, d.getId()));
    }
}







