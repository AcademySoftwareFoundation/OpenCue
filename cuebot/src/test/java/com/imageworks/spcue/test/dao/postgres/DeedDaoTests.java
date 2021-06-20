
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



package com.imageworks.spcue.test.dao.postgres;

import javax.annotation.Resource;

import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

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
import com.imageworks.spcue.test.AssumingPostgresEngine;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class DeedDaoTests  extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    OwnerManager ownerManager;

    @Resource
    DeedDao deedDao;

    @Resource
    AdminManager adminManager;

    @Resource
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
                .setFreeGpuMem((int) CueUtil.MB512)
                .setTotalGpuMem((int) CueUtil.MB512)
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
}

