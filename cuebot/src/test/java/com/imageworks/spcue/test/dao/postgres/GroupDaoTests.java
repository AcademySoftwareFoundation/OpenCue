
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

import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.config.TestAppConfig;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import org.junit.Before;
import org.junit.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.Rollback;
import org.springframework.test.context.ContextConfiguration;
import org.springframework.test.context.junit4.AbstractTransactionalJUnit4SpringContextTests;
import org.springframework.test.context.support.AnnotationConfigContextLoader;
import org.springframework.transaction.annotation.Transactional;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

@Transactional
@ContextConfiguration(classes=TestAppConfig.class, loader=AnnotationConfigContextLoader.class)
public class GroupDaoTests extends AbstractTransactionalJUnit4SpringContextTests  {
    
    @Autowired
    GroupDao groupDao;

    @Autowired
    ShowDao showDao;

    @Autowired
    JobManager jobManager;

    @Autowired
    JobLauncher jobLauncher;

    @Before
    public void before() {
        jobLauncher.testMode = true;
    }

    public ShowInterface getShow() {
        return showDao.getShowDetail("00000000-0000-0000-0000-000000000000");
    }

    public JobDetail launchJob() {
        jobLauncher.launch(new File("src/test/resources/conf/jobspec/jobspec.xml"));
        return jobManager.findJobDetail("pipe-dev.cue-testuser_shell_v1");
    }

    public GroupDetail createGroup() {
        GroupDetail group = new GroupDetail();
        group.name = "Shit";
        group.parentId =  groupDao.getRootGroupId(getShow());
        group.showId = getShow().getId();
        groupDao.insertGroup(group, groupDao.getRootGroupDetail(getShow()));
        return group;
    }

    public GroupDetail createSubGroup(GroupDetail parent) {
        GroupDetail group = new GroupDetail();
        group.name = "SubShit";
        group.parentId =  parent.id;
        group.showId = getShow().getId();
        groupDao.insertGroup(group, groupDao.getGroup(parent.id));
        return group;
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetGroup() {
        GroupDetail group = createGroup();
        GroupInterface g = groupDao.getGroup(group.id);
        assertEquals(group.id,g.getGroupId());
        assertEquals(group.id,g.getId());
        assertEquals(group.name, g.getName());
        assertEquals(group.showId, g.getShowId());
    }


    @Test
    @Transactional
    @Rollback(true)
    public void testGetGroups() {
        GroupDetail group = createGroup();
        List<String> l = new ArrayList<String>();
        l.add(group.id);
        List<GroupInterface> g = groupDao.getGroups(l);
        assertEquals(1, g.size());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetRootGroupId() {
        groupDao.getRootGroupId(getShow());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertGroup() {
        GroupDetail group = createGroup();
        assertFalse(group.isNew());
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testInsertGroupAlternateMethod() {
        GroupDetail group = new GroupDetail();
        group.name = "Shit";
        group.parentId =  groupDao.getRootGroupId(getShow());
        group.showId = getShow().getId();
        groupDao.insertGroup(group);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testDeleteGroup() {
        // Can't delete groups yet, will fail
        GroupDetail group = createGroup();

        assertEquals(Integer.valueOf(1), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM folder WHERE pk_folder=?",
                Integer.class, group.getId()));

        groupDao.deleteGroup(group);

        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM folder WHERE pk_folder=?",
                Integer.class, group.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateGroupParent() {
        GroupDetail group =  createGroup();
        GroupDetail subgroup = createSubGroup(group);
        groupDao.updateGroupParent(subgroup,
                groupDao.getGroupDetail(
                        groupDao.getRootGroupId(getShow())));

        assertEquals(Integer.valueOf(1),jdbcTemplate.queryForObject(
                "SELECT int_level FROM folder_level WHERE pk_folder=?",
                Integer.class, subgroup.getId()));

        groupDao.updateGroupParent(subgroup, group);

        assertEquals(Integer.valueOf(2),jdbcTemplate.queryForObject(
                "SELECT int_level FROM folder_level WHERE pk_folder=?",
                Integer.class, subgroup.getId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateDefaultJobMaxCores() {
        GroupDetail group =  createGroup();
        assertEquals(Integer.valueOf(-1), jdbcTemplate.queryForObject(
                "SELECT int_job_max_cores FROM folder WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
        groupDao.updateDefaultJobMaxCores(group, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_job_max_cores FROM folder WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
        groupDao.updateDefaultJobMaxCores(group, -1);
        assertEquals(Integer.valueOf(-1), jdbcTemplate.queryForObject(
                "SELECT int_job_max_cores FROM folder WHERE pk_folder=?",
                Integer.class, group.getGroupId()));

    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateDefaultJobMinCores() {
        GroupDetail group =  createGroup();
        assertEquals(Integer.valueOf(-1), jdbcTemplate.queryForObject(
                "SELECT int_job_min_cores FROM folder WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
        groupDao.updateDefaultJobMinCores(group, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_job_min_cores FROM folder WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateDefaultJobPriority() {
        GroupDetail group =  createGroup();
        assertEquals(Integer.valueOf(-1), jdbcTemplate.queryForObject(
                "SELECT int_job_priority FROM folder WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
        groupDao.updateDefaultJobPriority(group, 1000);
        assertEquals(Integer.valueOf(1000), jdbcTemplate.queryForObject(
                "SELECT int_job_priority FROM folder WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateMinCores() {
        GroupDetail group =  createGroup();
        assertEquals(Integer.valueOf(0), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM folder_resource WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
        groupDao.updateMinCores(group, 10);
        assertEquals(Integer.valueOf(10), jdbcTemplate.queryForObject(
                "SELECT int_min_cores FROM folder_resource WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateMaxCores() {
        GroupDetail group =  createGroup();
        assertEquals(Integer.valueOf(-1), jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM folder_resource WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
        groupDao.updateMaxCores(group, 100);
        assertEquals(Integer.valueOf(100), jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM folder_resource WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
        groupDao.updateMaxCores(group, -5);
        assertEquals(Integer.valueOf(-1), jdbcTemplate.queryForObject(
                "SELECT int_max_cores FROM folder_resource WHERE pk_folder=?",
                Integer.class, group.getGroupId()));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsManaged() {
        GroupDetail group =  createGroup();
        assertEquals(false, groupDao.isManaged(group));
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testUpdateName() {
        GroupDetail group =  createGroup();
        groupDao.updateName(group, "NewName");
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetGroupDetail() {
        GroupDetail group = createGroup();
        GroupDetail group2 = groupDao.getGroupDetail(group.id);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetChildrenRecursive() {
        boolean is_test2 = false;
        boolean is_test3 = false;

        GroupDetail g1 = new GroupDetail();
        g1.name = "Test1";
        g1.showId = getShow().getId();
        groupDao.insertGroup(g1, groupDao.getRootGroupDetail(getShow()));

        GroupDetail g2 = new GroupDetail();
        g2.name = "Test2";
        g2.showId = getShow().getId();
        groupDao.insertGroup(g2, groupDao.getRootGroupDetail(getShow()));

        for ( GroupInterface g: groupDao.getChildrenRecursive(groupDao.getGroup("A0000000-0000-0000-0000-000000000000"))) {
            if (g.getName().equals("Test1")) {
                is_test2 = true;
            }
            if (g.getName().equals("Test2")) {
                is_test3 = true;
            }
        }
        assertTrue(is_test2);
        assertTrue(is_test3);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testGetChildren() {
        boolean is_testuserA = false;
        boolean is_testuserB = false;

        GroupDetail g1 = new GroupDetail();
        g1.name = "testuserA";
        g1.showId = getShow().getId();
        groupDao.insertGroup(g1, groupDao.getRootGroupDetail(getShow()));

        GroupDetail g2 = new GroupDetail();
        g2.name = "testuserB";
        g2.showId = getShow().getId();
        groupDao.insertGroup(g2, groupDao.getRootGroupDetail(getShow()));

        List<GroupInterface> groups = groupDao.getChildren(groupDao.getGroup("A0000000-0000-0000-0000-000000000000"));
        for (GroupInterface g : groups) {
            if (g.getName().equals("testuserA")) {
                is_testuserA = true;
            }
            if (g.getName().equals("testuserB")) {
                is_testuserB = true;
            }
        }
        assertTrue(is_testuserA);
        assertTrue(is_testuserB);
    }

    @Test
    @Transactional
    @Rollback(true)
    public void testIsOverMinCores() {

        JobDetail job = launchJob();
        assertFalse(groupDao.isOverMinCores(job));

        String groupid =  jdbcTemplate.queryForObject("SELECT pk_folder FROM job WHERE pk_job=?",
                String.class, job.getJobId());

        // Now update some values so it returns true.
        jdbcTemplate.update("UPDATE folder_resource SET int_cores = int_min_cores + 1 WHERE pk_folder=?",
                groupid);

        assertTrue(groupDao.isOverMinCores(job));
    }
}


