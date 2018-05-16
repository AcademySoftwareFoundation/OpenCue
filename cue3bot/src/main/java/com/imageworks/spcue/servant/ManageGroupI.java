
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



package com.imageworks.spcue.servant;

import java.util.List;

import org.springframework.beans.factory.InitializingBean;

import Ice.Current;

import com.imageworks.common.SpiIce.SpiIceException;
import com.imageworks.common.spring.remoting.SpiIceExceptionGenericTemplate;
import com.imageworks.common.spring.remoting.SpiIceExceptionMinimalTemplate;
import com.imageworks.spcue.EntityRemovalError;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.CueClientIce.Group;
import com.imageworks.spcue.CueClientIce.GroupInterfacePrx;
import com.imageworks.spcue.CueClientIce.Job;
import com.imageworks.spcue.CueClientIce.JobInterfacePrx;
import com.imageworks.spcue.CueClientIce._GroupInterfaceDisp;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;

public class ManageGroupI extends _GroupInterfaceDisp  implements InitializingBean {

    private final String id;
    private com.imageworks.spcue.Group group;

    private GroupDao groupDao;
    private JobDao jobDao;
    private GroupManager groupManager;
    private AdminManager adminManager;
    private Whiteboard whiteboard;
    private DispatchQueue manageQueue;

    public ManageGroupI(Ice.Identity i) {
        this.id = i.name;
    }

    @Override
    public Ice.DispatchStatus __dispatch(IceInternal.Incoming in,
                                         Current current) {
        ServantInterceptor.__dispatch(this, in, current);
        return super.__dispatch(in, current);
    }

    public void afterPropertiesSet() throws Exception {
        group = groupDao.getGroup(id);
    }

    public void reparentGroups(final List<GroupInterfacePrx> groups, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
               groupManager.reparentGroupIds(group,
                       ServantUtil.convertProxyListToUniqueList(groups));
            }
        }.execute();
    }

    public void reparentJobs(final List<JobInterfacePrx> jobs, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                final GroupDetail gDetail = groupDao.getGroupDetail(group.getId());
                for (JobInterfacePrx jobPrx: jobs) {
                    groupManager.reparentJob(
                            jobDao.getJob(
                                    jobPrx.ice_getIdentity().name),
                                    gDetail,
                                    new Inherit[] { Inherit.All });
                }
            }
        }.execute();
    }

    public Group createSubGroup(final String name, Current __current)
            throws SpiIceException {

        return new SpiIceExceptionGenericTemplate<Group>() {
            public Group throwOnlyIceExceptions() {
                GroupDetail newGroup = new GroupDetail();
                newGroup.name = name;
                newGroup.parentId = group.getId();
                newGroup.showId = group.getShowId();
                groupManager.createGroup(newGroup, group);
                return whiteboard.getGroup(newGroup.id);
            }
        }.execute();
    }

    public void delete(Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                try {
                    groupManager.deleteGroup(group);
                } catch (Exception e) {
                    throw new EntityRemovalError("Failed to remove group, be sure that there are no " +
                            "jobs or filter actions pointing at the group.", e);
                }
            }
        }.execute();
    }

    public void setDefaultJobMaxCores(final float cores, Current __current)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                groupManager.setGroupDefaultJobMaxCores(group, Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    public void setDefaultJobMinCores(final float cores, Current __current)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                groupManager.setGroupDefaultJobMinCores(group, Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    public void setName(final String name, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                groupDao.updateName(group, name);
            }
        }.execute();
    }

    public void setGroup(final GroupInterfacePrx groupId, Current __current)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                Ice.Identity i = groupId.ice_getIdentity();
                groupManager.setGroupParent(group, groupDao.getGroupDetail(i.name));
            }
        }.execute();
    }

    @Override
    public void setDepartment(final String name, Current __current) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                groupManager.setGroupDepartment(group,
                        adminManager.findDepartment(name));
            }
        }.execute();
    }

    public void setDefaultJobPriority(final int priority, Current __current)
            throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                groupManager.setGroupDefaultJobPriority(group, priority);
            }
        }.execute();
    }

    public List<Group> getGroups(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Group>>() {
            public List<Group> throwOnlyIceExceptions() {
                return whiteboard.getGroups(group);
            }
        }.execute();
    }

    public List<Job> getJobs(Current __current) throws SpiIceException {
        return new SpiIceExceptionGenericTemplate<List<Job>>() {
            public List<Job> throwOnlyIceExceptions() {
                return whiteboard.getJobs(group);
            }
        }.execute();
    }

    @Override
    public void setMaxCores(final float cores, Current arg1) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                groupManager.setGroupMaxCores(group,
                        Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    @Override
    public void setMinCores(final float cores, Current arg1) throws SpiIceException {
        new SpiIceExceptionMinimalTemplate() {
            public void throwOnlyIceExceptions() {
                groupManager.setGroupMinCores(group,
                        Convert.coresToWholeCoreUnits(cores));
            }
        }.execute();
    }

    public GroupDao getGroupDao() {
        return groupDao;
    }

    public void setGroupDao(GroupDao groupDao) {
        this.groupDao = groupDao;
    }

    public GroupManager getGroupManager() {
        return groupManager;
    }

    public void setGroupManager(GroupManager groupManager) {
        this.groupManager = groupManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

}

