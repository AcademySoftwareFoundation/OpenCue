
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

import com.imageworks.spcue.MaintenanceTask;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.MaintenanceDao;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class MaintenanceDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {
    
    @Autowired
    MaintenanceDao maintenanceDao;

    @Test
    @Transactional
    @Rollback(true)
    public void testSetUpHostsToDown() {
        maintenanceDao.setUpHostsToDown();
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testLockHistoricalTask() {
        assertTrue(maintenanceDao.lockTask(MaintenanceTask.LOCK_HISTORICAL_TRANSFER));
        assertFalse(maintenanceDao.lockTask(MaintenanceTask.LOCK_HISTORICAL_TRANSFER));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUnlockHistoricalTask() {
        assertTrue(maintenanceDao.lockTask(MaintenanceTask.LOCK_HISTORICAL_TRANSFER));
        maintenanceDao.unlockTask(MaintenanceTask.LOCK_HISTORICAL_TRANSFER);
    }
}


