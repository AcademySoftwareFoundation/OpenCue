
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

import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.OwnerDao;
import com.imageworks.spcue.service.AdminManager;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.Assert.assertEquals;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class OwnerDaoTests  extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    OwnerDao ownerDao;

    @Autowired
    AdminManager adminManager;

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertOwner() {
        ShowInterface show = adminManager.findShowEntity("pipe");
        OwnerEntity o = new OwnerEntity();
        o.name = "spongebob";
        ownerDao.insertOwner(o, show);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsOwner() {
        ShowInterface show = adminManager.findShowEntity("pipe");
        OwnerEntity o = new OwnerEntity();
        o.name = "spongebob";
        ownerDao.insertOwner(o, show);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetOwner() {
        ShowInterface show = adminManager.findShowEntity("pipe");
        OwnerEntity o = new OwnerEntity();
        o.name = "spongebob";
        ownerDao.insertOwner(o, show);

        assertEquals(o, ownerDao.findOwner("spongebob"));
        assertEquals(o, ownerDao.getOwner(o.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteOwner() {
        ShowInterface show = adminManager.findShowEntity("pipe");
        OwnerEntity o = new OwnerEntity();
        o.name = "spongebob";
        ownerDao.insertOwner(o, show);

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM owner WHERE pk_owner=?",
                Integer.class, o.id));

        ownerDao.deleteOwner(o);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM owner WHERE pk_owner=?",
                Integer.class, o.id));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateShow() {
        ShowInterface show = adminManager.findShowEntity("pipe");
        OwnerEntity o = new OwnerEntity();
        o.name = "spongebob";
        ownerDao.insertOwner(o, show);

        ShowInterface newShow = adminManager.findShowEntity("edu");

        ownerDao.updateShow(o, newShow);

        assertEquals(newShow.getShowId(), jdbcTemplate.queryForObject(
                "SELECT pk_show FROM owner WHERE pk_owner=?",
                String.class, o.id));
    }
}

