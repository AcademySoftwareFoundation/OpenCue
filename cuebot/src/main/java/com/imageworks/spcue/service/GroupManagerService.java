
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

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.util.CueUtil;

@Service
@Transactional
public class GroupManagerService implements GroupManager {

    @Autowired
    private GroupDao groupDao;

    @Autowired
    private JobDao jobDao;

    @Override
    public void setGroupDefaultJobPriority(GroupInterface g, int priority) {
        groupDao.updateDefaultJobPriority(g, priority);
        jobDao.updatePriority(g, priority);
    }

    @Override
    public void setGroupDefaultJobMaxCores(GroupInterface g, int coreUnits) {
        groupDao.updateDefaultJobMaxCores(g,coreUnits);
        if (coreUnits != CueUtil.FEATURE_DISABLED && !groupDao.isManaged(g)) {
            jobDao.updateMaxCores(g,coreUnits);
        }
    }

    @Override
    public void setGroupDefaultJobMinCores(GroupInterface g, int coreUnits) {
        groupDao.updateDefaultJobMinCores(g,coreUnits);
        if (coreUnits != CueUtil.FEATURE_DISABLED && !groupDao.isManaged(g)) {
            jobDao.updateMinCores(g,coreUnits);
        }
    }

    @Override
    public void setGroupMaxCores(GroupInterface g, int coreUnits) {
        groupDao.updateMaxCores(g,coreUnits);
    }

    @Override
    public void setGroupMinCores(GroupInterface g, int coreUnits) {
        groupDao.updateMinCores(g,coreUnits);
    }

    @Override
    public void setGroupParent(GroupInterface group, GroupInterface newParent) {
        groupDao.updateGroupParent(group, newParent);
    }

    @Override
    public void deleteGroup(GroupInterface group) {
        groupDao.deleteGroup(group);
    }

    @Override
    public void createGroup(GroupDetail group, GroupInterface parent) {
        groupDao.insertGroup(group, parent);
    }

    @Override
    public void reparentGroups(GroupInterface group, List<GroupInterface> groups) {
        for (GroupInterface g : groups) {
            groupDao.updateGroupParent(g, group);
        }
    }

    @Override
    public void reparentJob(JobInterface job, GroupDetail group, Inherit[] inherit) {
        jobDao.updateParent(job, group, inherit);
    }

    @Override
    public void reparentGroupIds(GroupInterface group, List<String> groups) {
        reparentGroups(group, groupDao.getGroups(groups));
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public GroupInterface getGroup(String id) {
        return groupDao.getGroup(id);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public GroupDetail getGroupDetail(String id) {
        return groupDao.getGroupDetail(id);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public GroupDetail getRootGroupDetail(ShowInterface s) {
        return groupDao.getRootGroupDetail(s);
    }

    @Override
    @Transactional(propagation=Propagation.REQUIRED, readOnly=true)
    public GroupDetail getGroupDetail(JobInterface j) {
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

}

