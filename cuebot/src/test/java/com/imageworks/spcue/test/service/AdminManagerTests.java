
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.test.service;

import javax.annotation.Resource;

import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.SpecBuilderException;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.service.AdminManager;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

@Transactional
@ContextConfiguration(classes = TestAppConfig.class, loader = AnnotationConfigContextLoader.class)
public class AdminManagerTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Resource
    AdminManager adminManager;

    @Resource
    FacilityDao facilityDao;

    @Resource
    ShowDao showDao;

    private static final String TEST_ALLOC_NAME = "testAlloc";

    @Test
    @Transactional
    @Rollback(true)
    public void createAllocation() {
        AllocationEntity a = new AllocationEntity();
        a.name = TEST_ALLOC_NAME;
        a.tag = "general";
        adminManager.createAllocation(facilityDao.getDefaultFacility(), a);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void deleteAllocation() {
        AllocationEntity a = new AllocationEntity();
        a.name = facilityDao.getDefaultFacility().getName() + "." + TEST_ALLOC_NAME;
        a.tag = "general";
        adminManager.createAllocation(facilityDao.getDefaultFacility(), a);
        adminManager.deleteAllocation(a);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void setDefaultAllocation() {
        AllocationEntity a = adminManager.getDefaultAllocation();
        assertEquals(a.name, facilityDao.getDefaultFacility().getName() + ".unassigned");

        a = new AllocationEntity();
        a.name = TEST_ALLOC_NAME;
        a.tag = "general";
        adminManager.createAllocation(facilityDao.getDefaultFacility(), a);
        adminManager.setDefaultAllocation(a);

        a = adminManager.getDefaultAllocation();
        assertEquals(a.name, facilityDao.getDefaultFacility().getName() + "." + TEST_ALLOC_NAME);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createShow() {
        ShowEntity show = new ShowEntity();
        show.name = "testtest";
        adminManager.createShow(show);
        ShowEntity result = showDao.findShowDetail(show.name);
        assertEquals(result.name, show.name);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createInvalidShow() {
        ShowEntity show = new ShowEntity();
        show.name = "test/test";
        try {
            adminManager.createShow(show);
            fail("Expected exception");
        } catch (SpecBuilderException e) {
            assertEquals(e.getMessage(), "The show name: test/test is not in the proper format.  "
                    + "Show names must be alpha numeric, no dashes or punctuation.");
        }
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getFacility() {
        adminManager.getFacility("spi");
        adminManager.getFacility("AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createLimit() {
        String limitName = "testlimit";
        adminManager.createLimit(limitName, 42);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void deleteLimit() {
        String limitName = "testlimit";
        adminManager.createLimit(limitName, 42);
        LimitInterface limit = adminManager.findLimit(limitName);
        adminManager.deleteLimit(limit);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void findLimit() {
        String limitName = "testlimit";
        adminManager.createLimit(limitName, 42);
        adminManager.findLimit(limitName);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getLimit() {
        String limitName = "testlimit";
        String limitId = adminManager.createLimit(limitName, 42);

        adminManager.getLimit(limitId);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void setLimitName() {
        String limitName = "testlimit";
        adminManager.createLimit(limitName, 42);
        LimitInterface limit = adminManager.findLimit(limitName);
        adminManager.setLimitName(limit, "newLimitName");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void setLimitMaxValue() {
        String limitName = "testlimit";
        adminManager.createLimit(limitName, 42);
        LimitInterface limit = adminManager.findLimit(limitName);
        adminManager.setLimitMaxValue(limit, 16);
    }
}
