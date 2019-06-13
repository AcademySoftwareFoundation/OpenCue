
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

import com.google.common.collect.Sets;
import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.ServiceOverrideEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.ServiceDao;
import com.imageworks.spcue.util.CueUtil;
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
public class ServiceDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {
    
    @Autowired
    ServiceDao serviceDao;

    @Test
    @Transactional
    @Rollback(true)
    public void testGetService() {
        ServiceEntity s1 = serviceDao.get("default");
        ServiceEntity s2 = serviceDao.get("AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0");
        assertEquals(s1, s2);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertService() {
        ServiceEntity s = new ServiceEntity();
        s.name = "dillweed";
        s.minCores = 100;
        s.minMemory = CueUtil.GB4;
        s.minGpu = CueUtil.GB;
        s.threadable = false;
        s.tags.addAll(Sets.newHashSet(new String[] { "general"}));

        serviceDao.insert(s);
        assertEquals(s, serviceDao.get("dillweed"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateService() {
        ServiceEntity s = new ServiceEntity();
        s.name = "dillweed";
        s.minCores = 100;
        s.minMemory = CueUtil.GB4;
        s.minGpu = CueUtil.GB;
        s.threadable = false;
        s.tags.addAll(Sets.newHashSet(new String[] { "general"}));

        serviceDao.insert(s);
        assertEquals(s, serviceDao.get("dillweed"));

        s.name = "smacktest";
        s.minCores = 200;
        s.minMemory = CueUtil.GB8;
        s.minGpu = CueUtil.GB2;
        s.threadable = true;
        s.tags = Sets.newLinkedHashSet();
        s.tags.add("linux");

        serviceDao.update(s);
        ServiceEntity s1 =  serviceDao.get(s.getId());

        assertEquals(s.name, s1.name);
        assertEquals(s.minCores, s1.minCores);
        assertEquals(s.minMemory, s1.minMemory);
        assertEquals(s.threadable, s1.threadable);
        assertEquals(s.tags.toArray()[0], s1.tags.toArray()[0]);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteService() {
        ServiceEntity s = new ServiceEntity();
        s.name = "dillweed";
        s.minCores = 100;
        s.minMemory = CueUtil.GB4;
        s.minGpu = CueUtil.GB;
        s.threadable = false;
        s.tags.addAll(Sets.newHashSet(new String[] { "general"}));

        serviceDao.insert(s);
        assertEquals(s, serviceDao.get("dillweed"));

        serviceDao.delete(s);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM service WHERE pk_service=?",
                Integer.class, s.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertServiceOverride() {
        ServiceOverrideEntity s = new ServiceOverrideEntity();
        s.name = "dillweed";
        s.minCores = 100;
        s.minMemory = CueUtil.GB4;
        s.minGpu = CueUtil.GB;
        s.threadable = false;
        s.tags.addAll(Sets.newHashSet(new String[] { "general"}));
        s.showId = "00000000-0000-0000-0000-000000000000";

        serviceDao.insert(s);
        assertEquals(s, serviceDao.getOverride("dillweed"));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateServiceOverride() {
        ServiceOverrideEntity s = new ServiceOverrideEntity();
        s.name = "dillweed";
        s.minCores = 100;
        s.minMemory = CueUtil.GB4;
        s.minGpu = CueUtil.GB2;
        s.threadable = false;
        s.tags.addAll(Sets.newHashSet(new String[] { "general"}));
        s.showId = "00000000-0000-0000-0000-000000000000";

        serviceDao.insert(s);
        assertEquals(s, serviceDao.getOverride("dillweed"));
        assertEquals(s, serviceDao.getOverride("dillweed", s.showId));

        s.name = "smacktest";
        s.minCores = 200;
        s.minMemory = CueUtil.GB8;
        s.minGpu = CueUtil.GB4;
        s.threadable = true;
        s.tags = Sets.newLinkedHashSet();
        s.tags.add("linux");

        serviceDao.update(s);
        ServiceEntity s1 =  serviceDao.getOverride(s.getId());

        assertEquals(s.name, s1.name);
        assertEquals(s.minCores, s1.minCores);
        assertEquals(s.minMemory, s1.minMemory);
        assertEquals(s.minGpu, s1.minGpu);
        assertEquals(s.threadable, s1.threadable);
        assertEquals(s.tags.toArray()[0], s1.tags.toArray()[0]);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteServiceOverride() {
        ServiceOverrideEntity s = new ServiceOverrideEntity();
        s.name = "dillweed";
        s.minCores = 100;
        s.minMemory = CueUtil.GB4;
        s.minGpu = CueUtil.GB;
        s.threadable = false;
        s.tags.addAll(Sets.newHashSet(new String[] { "general"}));
        s.showId = "00000000-0000-0000-0000-000000000000";

        serviceDao.insert(s);
        assertEquals(s, serviceDao.getOverride("dillweed"));
        assertEquals(s, serviceDao.getOverride("dillweed", s.showId));
        serviceDao.delete(s);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(1) FROM show_service WHERE pk_show_service=?",
                Integer.class, s.getId()));
    }
}

