
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

import javax.annotation.Resource;

import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.test.AssumingPostgresEngine;

import static org.junit.Assert.assertEquals;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class LimitDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    LimitDao limitDao;

    private static String LIMIT_NAME = "test-limit";
    private static int LIMIT_MAX_VALUE = 32;

    @Test
    @Transactional
    @Rollback(true)
    public void testCreateLimit() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);
        LimitEntity limit = limitDao.getLimit(limitId);
        assertEquals(limit.id, limitId);
        assertEquals(limit.name, LIMIT_NAME);
        assertEquals(limit.maxValue, LIMIT_MAX_VALUE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteLimit() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);
        LimitEntity limit = limitDao.getLimit(limitId);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM limit_record WHERE pk_limit_record=?",
                Integer.class, limitId));

        limitDao.deleteLimit(limit);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM limit_record WHERE pk_limit_record=?",
                Integer.class, limitId));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindLimit() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);

        LimitEntity limit = limitDao.findLimit(LIMIT_NAME);
        assertEquals(limit.name, LIMIT_NAME);
        assertEquals(limit.maxValue, LIMIT_MAX_VALUE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetLimit() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);

        LimitEntity limit = limitDao.getLimit(limitId);
        assertEquals(limit.name, LIMIT_NAME);
        assertEquals(limit.maxValue, LIMIT_MAX_VALUE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetLimitName() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);
        LimitEntity limit = limitDao.getLimit(limitId);
        String newName = "heyIChanged";

        limitDao.setLimitName(limit, newName);

        limit = limitDao.getLimit(limitId);
        assertEquals(limit.id, limitId);
        assertEquals(limit.name, newName);
        assertEquals(limit.maxValue, LIMIT_MAX_VALUE);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testSetMaxValue() {
        String limitId = limitDao.createLimit(LIMIT_NAME, LIMIT_MAX_VALUE);
        LimitEntity limit = limitDao.getLimit(limitId);
        int newValue = 600;

        limitDao.setMaxValue(limit, newValue);

        limit = limitDao.getLimit(limitId);
        assertEquals(limit.id, limitId);
        assertEquals(limit.name, LIMIT_NAME);
        assertEquals(limit.maxValue, newValue);
    }
}
