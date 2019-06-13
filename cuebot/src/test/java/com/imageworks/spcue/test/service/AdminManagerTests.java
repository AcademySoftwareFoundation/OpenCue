
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

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.service.AdminManager;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class AdminManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    AdminManager adminManager;

    @Autowired
    FacilityDao facilityDao;

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
    public void createShow() {
        ShowEntity show = new ShowEntity();
        show.name = "testtest";
        adminManager.createShow(show);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getFacility() {
        adminManager.getFacility("spi");
        adminManager.getFacility("AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1");
    }


}

