
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

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.PointInterface;
import com.imageworks.spcue.TaskEntity;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.PointDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.TaskDao;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.test.AssumingPostgresEngine;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class TaskDaoTests extends AbstractTransactionalJUnit4SpringContextTests {

    @Autowired
    @Rule
    public AssumingPostgresEngine assumingPostgresEngine;

    @Resource
    ShowDao showDao;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    TaskDao taskDao;

    @Resource
    PointDao pointDao;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Before
    public void testMode() {
        jobLauncher.testMode = true;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void insertTask() {
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");

        String dept = jdbcTemplate.queryForObject(
                "SELECT pk_dept FROM job WHERE pk_job=?", String.class, job.getJobId());

        // Add in a new task, the job should switch to using this task.
        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDepartment(dept));

        TaskEntity t = new TaskEntity(p, "dev.foo", 100);
        taskDao.insertTask(t);

        t = taskDao.getTaskDetail(t.id);
        taskDao.deleteTask(t);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void deleteTask() {
        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());
        TaskEntity t = new TaskEntity(p, "dev.cue", 100);
        taskDao.insertTask(t);
        taskDao.deleteTask(t);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void deleteTasksByShowAndDepartment() {

        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        int task_count = jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM task WHERE pk_point=?",
                Integer.class, p.getPointId());

        TaskEntity t = new TaskEntity(p, "dev.cue");
        taskDao.insertTask(t);

        assertEquals(Integer.valueOf(task_count + 1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM task WHERE pk_point=?",
                Integer.class, p.getPointId()));

        taskDao.deleteTasks(p);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM task WHERE pk_point=?",
                Integer.class, p.getPointId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void deleteTasksByDepartmentConfig() {

        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        TaskEntity t = new TaskEntity(p,
                "dev.cue");
        t.minCoreUnits = 100;
        taskDao.insertTask(t);

        taskDao.deleteTasks(p);

        /**
         * This is always
         */
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM task WHERE pk_point=?",
                Integer.class, p.getPointId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getTaskDetail() {

        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        TaskEntity t = new TaskEntity(p, "dev.cue");

        taskDao.insertTask(t);
        TaskEntity newTask = taskDao.getTaskDetail(t.getTaskId());
        assertEquals(newTask.id,t.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void getTaskDetailByDept() {
        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        TaskEntity t = new TaskEntity(p, "dev.cue");

        taskDao.insertTask(t);
        TaskEntity newTask = taskDao.getTaskDetail(departmentDao.getDefaultDepartment(), "dev.cue");
        assertEquals(newTask.id,t.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void updateTaskMinProcs() {

        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        TaskEntity t = new TaskEntity(p, "dev.cue");
        t.minCoreUnits = 100;
        taskDao.insertTask(t);
        TaskEntity newTask = taskDao.getTaskDetail(t.getTaskId());
        taskDao.updateTaskMinCores(newTask, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM task WHERE pk_task=?",
                Integer.class, newTask.getTaskId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void adjustTaskMinProcs() {

        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        TaskEntity t = new TaskEntity(p,"dev.cue");
        t.minCoreUnits = 10;
        taskDao.insertTask(t);
        TaskEntity newTask = taskDao.getTaskDetail(t.getTaskId());
        taskDao.updateTaskMinCores(newTask, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM task WHERE pk_task=?",
                Integer.class, newTask.getTaskId()));

        taskDao.adjustTaskMinCores(t, 105);

        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM task WHERE pk_task=?",
                Integer.class, newTask.getTaskId()));
        assertEquals(Integer.valueOf(5), jdbcTemplate.queryForObject(
                "SELECT int_adjust_cores FROM task WHERE pk_task=?",
                Integer.class, newTask.getTaskId()));

        taskDao.adjustTaskMinCores(t, 50);

        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM task WHERE pk_task=?",
                Integer.class, newTask.getTaskId()));
        assertEquals(Integer.valueOf(-50), jdbcTemplate.queryForObject(
                "SELECT int_adjust_cores FROM task WHERE pk_task=?",
                Integer.class, newTask.getTaskId()));
    }


    @Test
    @Transactional
    @Rollback(true)
    public void mergeTask() {

        PointInterface p = pointDao.getPointConfigDetail(
                showDao.findShowDetail("pipe"),
                departmentDao.getDefaultDepartment());

        TaskEntity t = new TaskEntity(p, "dev.cue");
        taskDao.insertTask(t);

        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM task WHERE pk_task=?",
                Integer.class, t.getTaskId()));

        TaskEntity newTask = taskDao.getTaskDetail(t.getTaskId());
        newTask.minCoreUnits = 200;
        taskDao.mergeTask(newTask);

        assertEquals(Integer.valueOf(200), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM task WHERE pk_task=?",
                Integer.class, newTask.getTaskId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void isJobManaged() {
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        JobDetail job = jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
        assertFalse(taskDao.isManaged(job));
    }
}

