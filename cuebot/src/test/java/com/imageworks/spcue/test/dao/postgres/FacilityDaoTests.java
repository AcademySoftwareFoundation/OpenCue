
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

import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FacilityDao;
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
public class FacilityDaoTests extends AbstractTransactionalJUnit4SpringContextTests {
    
    @Autowired
    FacilityDao facilityDao;

    @Test
    @Transactional
    @Rollback(true)
    public void testGetDetaultFacility() {
        assertEquals(jdbcTemplate.queryForObject(
                "SELECT pk_facility FROM facility WHERE b_default=true",
                String.class),facilityDao.getDefaultFacility().getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetFacility() {
        String id = "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0";
        assertEquals(id, facilityDao.getFacility(id).getId());
        assertEquals(id, facilityDao.getFacility("spi").getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFacilityExists() {
        assertTrue(facilityDao.facilityExists("spi"));
        assertFalse(facilityDao.facilityExists("rambo"));
    }
}

