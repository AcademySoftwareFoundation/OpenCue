
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

import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class DepartmentDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    AdminManager adminManager;


    @Test
    @Transactional
    @Rollback(true)
    public void testGetDepartment() {
        String dept= "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA0";
        assertEquals(dept, departmentDao.getDepartment(dept).getId());
        assertEquals(dept, departmentDao.getDepartment(dept).getDepartmentId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testFindDepartment() {
        String dept= "Hair";
        assertEquals(dept, departmentDao.findDepartment(dept).getName());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testgetDefaultDepartment() {
        assertEquals(jdbcTemplate.queryForObject(
                "SELECT pk_dept FROM dept WHERE b_default=true",
                String.class),departmentDao.getDefaultDepartment().getId());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDepartmentExists() {
        String dept= "Cloth";
        assertTrue(departmentDao.departmentExists(dept));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertDepartment() {
        String deptName = "TestDept";
        departmentDao.insertDepartment(deptName);
        DepartmentInterface d = departmentDao.findDepartment(deptName);
        assertEquals(d.getName(), deptName);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteDepartment() {
        String deptName = "TestDept";
        departmentDao.insertDepartment(deptName);
        DepartmentInterface d = departmentDao.findDepartment(deptName);
        assertEquals(d.getName(), deptName);
        departmentDao.deleteDepartment(d);
    }
}

