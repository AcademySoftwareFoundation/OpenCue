
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

import com.imageworks.spcue.*;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.SubscriptionDao;
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
public class SubscriptionDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    SubscriptionDao subscriptionDao;

    @Autowired
    AllocationDao allocationDao;

    @Autowired
    ShowDao showDao;

    @Autowired
    FacilityDao facilityDao;

    public static final String SUB_NAME = "test.pipe";
    public static final String ALLOC_NAME = "test";

    private AllocationEntity alloc;

    public ShowInterface getShow() {
        return showDao.getShowDetail("00000000-0000-0000-0000-000000000000");
    }

    public SubscriptionEntity buildSubscription(ShowInterface t, AllocationInterface a) {
        SubscriptionEntity s = new SubscriptionEntity();
        s.allocationId = a.getId();
        s.showId = t.getId();
        s.burst = 500;
        s.size = 100;
        return s;
    }

    public AllocationEntity buildAllocation() {
        AllocationEntity a = new AllocationEntity();
        a.tag = "test";
        a.name = ALLOC_NAME;
        a.facilityId = facilityDao.getDefaultFacility().getFacilityId();
        return a;
    }

    @Before
    public void before() {
        alloc =  new AllocationEntity();
        alloc.name = ALLOC_NAME;
        alloc.tag = "test";
        allocationDao.insertAllocation(
                facilityDao.getDefaultFacility(), alloc);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testHasRunningProcs() {
        SubscriptionEntity s = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(s);
        assertFalse(subscriptionDao.hasRunningProcs(s));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsShowOverSize() {

        SubscriptionEntity sub = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(sub);

        assertFalse(this.subscriptionDao.isShowOverSize(getShow(), alloc));

        jdbcTemplate.update(
                "UPDATE subscription SET int_cores = ? WHERE pk_subscription = ?",
                100, sub.getSubscriptionId());

        assertFalse(subscriptionDao.isShowOverSize(getShow(), alloc));

        jdbcTemplate.update(
                "UPDATE subscription SET int_cores = ? WHERE pk_subscription = ?",
                101, sub.getSubscriptionId());

        assertEquals(true, subscriptionDao.isShowOverSize(getShow(), alloc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsShowAtOrOverSize() {

        SubscriptionEntity sub = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(sub);
        assertFalse(this.subscriptionDao.isShowAtOrOverSize(getShow(), alloc));

        jdbcTemplate.update(
                "UPDATE subscription SET int_cores = ? WHERE pk_subscription = ?",
                100, sub.getSubscriptionId());

        assertTrue(subscriptionDao.isShowAtOrOverSize(getShow(), alloc));

        jdbcTemplate.update(
                "UPDATE subscription SET int_cores = ? WHERE pk_subscription = ?",
                200, sub.getSubscriptionId());

        assertTrue(subscriptionDao.isShowAtOrOverSize(getShow(), alloc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsShowOverBurst() {
        subscriptionDao.insertSubscription(buildSubscription(getShow(), alloc));

        // Burst is 500 so 600 would be over burst.
        assertTrue(subscriptionDao.isShowOverBurst(getShow(), alloc, 600));

        // Burst is 500 so 300 would be under burst.
        assertFalse(subscriptionDao.isShowOverBurst(getShow(), alloc, 300));
    }

    @Test(expected=org.springframework.jdbc.UncategorizedSQLException.class)
    @Transactional
    @Rollback(true)
    public void testIsShowAtOrOverBurst() {

        SubscriptionEntity sub = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(sub);
        assertFalse(subscriptionDao.isShowAtOrOverBurst(getShow(), alloc));

        jdbcTemplate.update(
                "UPDATE subscription SET int_cores = ? WHERE pk_subscription = ?",
                500, sub.getSubscriptionId());

        assertTrue(subscriptionDao.isShowAtOrOverBurst(getShow(), alloc));

        jdbcTemplate.update(
                "UPDATE subscription SET int_cores = ? WHERE pk_subscription = ?",
                501, sub.getSubscriptionId());

        assertTrue(subscriptionDao.isShowAtOrOverBurst(getShow(), alloc));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetSubscriptionDetail() {

        FacilityInterface f = facilityDao.getDefaultFacility();

        SubscriptionEntity s = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(s);
        assertNotNull(s.id);
        assertNotNull(s.getId());

        SubscriptionEntity s1 =  subscriptionDao.getSubscriptionDetail(
                s.getSubscriptionId());

        assertEquals(alloc.getName() + ".pipe", s1.name);
        assertEquals(s.burst, s1.burst);
        assertEquals(s.id, s1.id);
        assertEquals(s.size, s1.size);
        assertEquals(s.allocationId, s1.allocationId);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertSubscription() {
        SubscriptionEntity s = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(s);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteSubscription() {
        SubscriptionEntity s = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(s);
        subscriptionDao.deleteSubscription(s);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateSubscriptionSize() {
        SubscriptionEntity s = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(s);
        subscriptionDao.updateSubscriptionSize(s, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_size FROM subscription WHERE pk_subscription=?",
                Integer.class, s.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateSubscriptionBurst() {
        SubscriptionEntity s = buildSubscription(getShow(), alloc);
        subscriptionDao.insertSubscription(s);
        subscriptionDao.updateSubscriptionBurst(s, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_burst FROM subscription WHERE pk_subscription=?",
                Integer.class, s.getId()));
    }
}


