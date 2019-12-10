
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

import java.io.File;
import javax.annotation.Resource;

import org.junit.Before;
import org.junit.Test;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobSpec;

import static org.junit.Assert.assertEquals;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class GroupManagerTests extends AbstractTransactionalJUnit4SpringContextTests  {

    @Resource
    GroupManager groupManager;

    @Resource
    JobManager jobManager;

    @Resource
    JobLauncher jobLauncher;

    @Resource
    GroupDao groupDao;

    @Resource
    JobDao jobDao;

    @Resource
    DepartmentDao departmentDao;

    @Resource
    ShowDao showDao;

    @Before
    public void setTestMode() {
        jobLauncher.testMode = true;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void createGroup() {
        ShowInterface pipe = showDao.findShowDetail("pipe");
        GroupDetail group = new GroupDetail();
        group.name = "testGroup";
        group.showId = pipe.getId();
        group.parentId =  groupDao.getRootGroupDetail(pipe).getId();
        group.deptId = departmentDao.getDefaultDepartment().getId();
        groupManager.createGroup(group, null);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void setGroupDepartment() {
        ShowInterface pipe = showDao.findShowDetail("pipe");
        GroupDetail group = groupDao.getRootGroupDetail(pipe);

        // Launch a test job
        JobSpec spec = jobLauncher.parse(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        jobLauncher.launch(spec);
        JobInterface job = jobManager.getJob(spec.getJobs().get(0).detail.id);

        // Set the group's department property to Lighting, it should
        // currently be Unknown
        DepartmentInterface dept = departmentDao.findDepartment("Lighting");
        jobDao.updateParent(job, group);

        // Update the group to the Lighting department
        groupManager.setGroupDepartment(group, dept);

        // Now check if the job we launched was also updated to the lighting department
        assertEquals(dept.getDepartmentId(), jobDao.getJobDetail(job.getJobId()).deptId);
    }

}

