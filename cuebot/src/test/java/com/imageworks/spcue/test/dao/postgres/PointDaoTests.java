
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

import java.io.File;
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
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.PointInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.PointDao;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class PointDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    AdminManager adminManager;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    PointDao pointDao;

    public JobDetail launchJob() {
        jobLauncher.testMode = true;
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void insertDepartmentConfig() {
        ShowEntity show = new ShowEntity();
        show.name = "testtest";
        adminManager.createShow(show);
        DepartmentInterface dept = departmentDao.findDepartment("Lighting");
        PointInterface d = pointDao.insertPointConf(show, dept);

        assertEquals(show.id, jdbcTemplate.queryForObject(
                "SELECT pk_show FROM point WHERE pk_point=?",
                String.class, d.getPointId()));

        assertEquals(dept.getDepartmentId(), jdbcTemplate.queryForObject(
                "SELECT pk_dept FROM point WHERE pk_point=?",
                String.class, d.getPointId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void departmentConfigExists() {
        ShowEntity show = new ShowEntity();
        show.name = "testtest";
        adminManager.createShow(show);

        assertTrue(pointDao.pointConfExists(show,
                departmentDao.getDefaultDepartment()));

        assertFalse(pointDao.pointConfExists(show,
                departmentDao.findDepartment("Lighting")));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateEnableTiManaged() {
        ShowEntity show = new ShowEntity();
        show.name = "testtest";
        adminManager.createShow(show);

        PointInterface config = pointDao.getPointConfigDetail(show,
                departmentDao.getDefaultDepartment());

        //pointDao.updateEnableManaged(config, "Lighting", 10);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getDepartmentConfig() {
        ShowEntity show = new ShowEntity();
        show.name = "testtest";
        adminManager.createShow(show);

        /* Tests both overlodaed methods */
        PointInterface configA = pointDao.getPointConfigDetail(show,
                departmentDao.getDefaultDepartment());

        PointInterface configB = pointDao.getPointConfDetail(
                configA.getPointId());

        assertEquals(configA.getPointId(), configB.getPointId());
        assertEquals(configA.getDepartmentId(), configB.getDepartmentId());
        assertEquals(configA.getShowId(), configB.getShowId());
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testIsOverMinCores() {

        JobDetail job = launchJob();

        PointInterface pointConfig = pointDao.getPointConfigDetail(job,
                departmentDao.getDepartment(job.getDepartmentId()));

        assertFalse(pointDao.isOverMinCores(job));

        // Now update some values so it returns true.
        jdbcTemplate.update("UPDATE point SET int_cores = int_min_cores + 2000000 WHERE pk_point=?",
                pointConfig.getId());

        logger.info(jdbcTemplate.queryForObject("SELECT int_min_cores from point where pk_point=?",
                Integer.class, pointConfig.getId()));

        assertTrue(pointDao.isOverMinCores(job));
    }

}

