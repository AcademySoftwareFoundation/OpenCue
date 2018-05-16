
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



package com.imageworks.spcue.service;

import java.util.List;

import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.Department;
import com.imageworks.spcue.Group;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.dao.DepartmentDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.util.CueUtil;

@Transactional
public class GroupManagerService implements GroupManager {

    private GroupDao groupDao;

    private JobDao jobDao;

    private DepartmentDao departmentDao;

    private DepartmentManager departmentManager;

    @Override
    public void setGroupDefaultJobPriority(Group g, int priority) {
        groupDao.updateDefaultJobPriority(g, priority);
        jobDao.updatePriority(g, priority);
    }

    @Override
    public void setGroupDefaultJobMaxCores(Group g, int coreUnits) {
        groupDao.updateDefaultJobMaxCores(g,coreUnits);
        if (coreUnits != CueUtil.FEATURE_DISABLED && !groupDao.isManaged(g)) {
            jobDao.updateMaxCores(g,coreUnits);
        }
    }

    @Override
    public void setGroupDefaultJobMinCores(Group g, int coreUnits) {
        groupDao.updateDefaultJobMinCores(g,coreUnits);
        if (coreUnits != CueUtil.FEATURE_DISABLED && !groupDao.isManaged(g)) {
            jobDao.updateMinCores(g,coreUnits);
        }
    }

    @Override
    public void setGroupMaxCores(Group g, int coreUnits) {
        groupDao.updateMaxCores(g,coreUnits);
    }

    @Override
    public void setGroupMinCores(Group g, int coreUnits) {
        groupDao.updateMinCores(g,coreUnits);
    }

    @Override
    public void setGroupParent(Group group, Group newParent) {
        groupDao.updateGroupParent(group, newParent);
    }

    @Override
    public void deleteGroup(Group group) {
        groupDao.deleteGroup(group);
    }

    @Override
    public void createGroup(GroupDetail group, Group parent) {
        Department d;
        if (group.getDepartmentId() == null) {
            d = departmentDao.getDefaultDepartment();
            group.deptId = d.getId();
        }
        else {
            d = departmentDao.getDepartment(group.getDepartmentId());
        }
        groupDao.insertGroup(group, parent);

        if (!departmentManager.departmentConfigExists(group, d)) {
            departmentManager.createDepartmentConfig(group, d);
        }
    }

    @Override
    public void reparentGroups(Group group, List<Group> groups) {
        for (Group g : groups) {
            groupDao.updateGroupParent(g, group);
        }
    }

    @Override
    public void reparentJob(Job job, GroupDetail group, Inherit[] inherit) {
        jobDao.updateParent(job, group, inherit);
    }

    @Override
    public void reparentGroupIds(Group group, List<String> groups) {
        reparentGroups(group, groupDao.getGroups(groups));
    }

    @Override
    public void setGroupDepartment(Group group, Department dept) {
        /*
         * If this is the first time the show is using this department
         * a department configuration is created.
         */
        if (!departmentManager.departmentConfigExists(group, dept)) {
            departmentManager.createDepartmentConfig(group, dept);
        }
        groupDao.updateDepartment(group, dept);
        jobDao.updateDepartment(group, dept);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public Group getGroup(String id) {
        return groupDao.getGroup(id);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public GroupDetail getGroupDetail(String id) {
        return groupDao.getGroupDetail(id);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public GroupDetail getRootGroupDetail(Show s) {
        return groupDao.getRootGroupDetail(s);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public GroupDetail getGroupDetail(Job j) {
        return groupDao.getGroupDetail(j);
    }

    public GroupDao getGroupDao() {
        return groupDao;
    }

    public void setGroupDao(GroupDao groupDao) {
        this.groupDao = groupDao;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    public DepartmentDao getDepartmentDao() {
        return departmentDao;
    }

    public void setDepartmentDao(DepartmentDao departmentDao) {
        this.departmentDao = departmentDao;
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }
}

