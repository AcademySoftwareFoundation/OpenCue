
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
import com.imageworks.spcue.PointInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.PointDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.DepartmentManager;
import com.imageworks.spcue.test.AssumingTrackitEnabled;

import static org.junit.Assert.assertTrue;


@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class DepartmentManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    @Rule
    public AssumingTrackitEnabled assumingTrackitEnabled;

    @Resource
    DepartmentManager departmentManager;

    @Resource
    ShowDao showDao;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    AdminManager adminManager;

    @Resource
    PointDao pointDao;

    private static final String TEST_TI_TASK_NAME = "RINT";

    @Test
    @Transactional
    @Rollback(true)
    public void enableTiManaged() {
        ShowInterface show = showDao.findShowDetail("pipe");
        DepartmentInterface dept = departmentDao.getDefaultDepartment();
        PointInterface rp = pointDao.getPointConfigDetail(show, dept);

        departmentManager.disableTiManaged(rp);
        departmentManager.enableTiManaged(rp, TEST_TI_TASK_NAME, 1000);

        // TODO(bcipriano) Once this test is enabled this assert should be updated to use
        //  DAO objects instead of querying the db directly.
        assertTrue(0 < jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM task,point WHERE point.pk_point = task.pk_point AND " +
                "point.pk_dept=? AND point.pk_show=?",
                Integer.class, dept.getDepartmentId(), show.getShowId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateTiManagedTasks() {
        ShowInterface show = showDao.findShowDetail("pipe");
        DepartmentInterface dept = departmentDao.getDefaultDepartment();
        PointInterface rp;

        try {
            rp = pointDao.getPointConfigDetail(show, dept);
        }
        catch (org.springframework.dao.DataRetrievalFailureException e) {
            pointDao.insertPointConf(show, dept);
            rp = pointDao.getPointConfigDetail(show,dept);
        }
        departmentManager.disableTiManaged(rp);
        departmentManager.enableTiManaged(rp, TEST_TI_TASK_NAME, 1000);

        // TODO(bcipriano) Once this test is enabled these asserts should be updated to use
        //  DAO objects instead of querying the db directly.

        assertTrue(0 < jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM task,point WHERE point.pk_point = task.pk_point AND " +
                "point.pk_dept=? AND point.pk_show=?",
                Integer.class, dept.getDepartmentId(), show.getShowId()));

        departmentManager.updateManagedTasks(rp);

        assertTrue(0 < jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM task,point WHERE point.pk_point = task.pk_point AND " +
                "point.pk_dept=? AND point.pk_show=?",
                Integer.class, dept.getDepartmentId(), show.getShowId()));

        departmentManager.disableTiManaged(rp);

    }
}

