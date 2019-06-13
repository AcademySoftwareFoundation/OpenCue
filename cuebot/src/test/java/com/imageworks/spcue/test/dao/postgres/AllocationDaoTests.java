
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

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.service.AdminManager;
import org.junit.Before;
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
public class AllocationDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    AllocationDao allocDao;

    @Autowired
    FacilityDao facilityDao;

    @Autowired
    AdminManager adminManager;

    public static final String ALLOC_FQN = "spi.test_alloc";
    public static final String ALLOC_NAME = "test_alloc";
    public static final String ALLOC_TAG = "test";

    private AllocationEntity alloc;

    @Before
    public void before() {

        alloc = new AllocationEntity();
        alloc.name = ALLOC_NAME;
        alloc.tag = ALLOC_TAG;

        allocDao.insertAllocation(
                facilityDao.getFacility("spi"),  alloc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetAllocation() {
        allocDao.getAllocationEntity(alloc.getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindAllocation() {
        FacilityInterface f = facilityDao.getFacility("spi");
        allocDao.findAllocationEntity(f.getName(), ALLOC_NAME);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindAllocation2() {
        FacilityInterface f = facilityDao.getFacility("spi");
        allocDao.findAllocationEntity(ALLOC_FQN);
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteAllocation() {
        allocDao.deleteAllocation(alloc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteAllocationWithProc() {

        // Use the alloc so deleting triggers it just to be disaled.
        ShowEntity show = adminManager.getShowEntity(
                "00000000-0000-0000-0000-000000000000");
        adminManager.createSubscription(show, alloc, 10, 10);
        allocDao.deleteAllocation(alloc);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM alloc WHERE pk_alloc=? AND b_enabled = false",
                Integer.class, alloc.getAllocationId()));

        assertEquals(ALLOC_FQN, jdbcTemplate.queryForObject(
                "SELECT str_name FROM alloc WHERE pk_alloc=? AND b_enabled = false",
                String.class, alloc.getAllocationId()));

        // Now re-enable it.
        allocDao.insertAllocation(facilityDao.getDefaultFacility(), alloc);
        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM alloc WHERE pk_alloc=? AND b_enabled = true",
                Integer.class, alloc.getAllocationId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateAllocationName() {
        allocDao.updateAllocationName(alloc, "frickjack");
        assertEquals("spi.frickjack", jdbcTemplate.queryForObject(
                "SELECT str_name FROM alloc WHERE pk_alloc=?",
                String.class,
                alloc.getId()));
    }

    @Test(expected = IllegalArgumentException.class)
    @Transactional
    @Rollback(true)
    public void testUpdateAllocationNameBad() {
        allocDao.updateAllocationName(alloc, "spi.frickjack");
        assertEquals("spi.frickjack", jdbcTemplate.queryForObject(
                "SELECT str_name FROM alloc WHERE pk_alloc=?",
                String.class, alloc.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateAllocationTag() {
        allocDao.updateAllocationTag(alloc, "foo");
        assertEquals("foo",jdbcTemplate.queryForObject(
                "SELECT str_tag FROM alloc WHERE pk_alloc=?",
                String.class, alloc.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateAllocationBillable() {
        allocDao.updateAllocationBillable(alloc, false);

        assertFalse(jdbcTemplate.queryForObject(
                "SELECT b_billable FROM alloc WHERE pk_alloc=?",
                Boolean.class, alloc.getId()));

        allocDao.updateAllocationBillable(alloc, true);

        assertTrue(jdbcTemplate.queryForObject(
                "SELECT b_billable FROM alloc WHERE pk_alloc=?",
                Boolean.class, alloc.getId()));
    }
}


