
/*
 * Copyright Contributors to the OpenCue Project
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

import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowInterface;

public interface GroupManager {

    void setGroupMaxCores(GroupInterface g, int coreUnits);
    void setGroupMinCores(GroupInterface g, int coreUnits);
    void setGroupDefaultJobMinCores(GroupInterface g, int coreUnits);
    void setGroupDefaultJobMaxCores(GroupInterface g, int coreUnits);
    void setGroupMaxGpu(GroupInterface g, int gpu);
    void setGroupMinGpu(GroupInterface g, int gpu);
    void setGroupDefaultJobMinGpu(GroupInterface g, int gpu);
    void setGroupDefaultJobMaxGpu(GroupInterface g, int gpu);
    void setGroupDefaultJobPriority(GroupInterface g, int priority);

    /**
     * Return the group from its unique ID
     *
     * @param id
     * @return
     */
    GroupInterface getGroup(String id);

    /**
     * Return the root group for the specified show.
     *
     * @param s
     * @return
     */
    GroupDetail getRootGroupDetail(ShowInterface s);

    /**
     * Return the GroupDetail by job.
     *
     * @param j
     * @return
     */
    GroupDetail getGroupDetail(JobInterface j);

    /**
     * Return a GroupDetail from its unique ID
     *
     * @param id
     * @return
     */
    GroupDetail getGroupDetail(String id);

    void setGroupParent(GroupInterface group, GroupInterface newParent);

    void deleteGroup(GroupInterface group);

    void createGroup(GroupDetail group, GroupInterface parent);

    /**
     * Re-parent a job to the specified group.
     *
     * @param job
     * @param group
     * @param inherit
     */
    void reparentJob(JobInterface job, GroupDetail group, Inherit[] inherit);

    /**
     * Parents a list of groups to the specified group
     *
     * @param group
     * @param groups
     */
    void reparentGroups(GroupInterface group, List<GroupInterface> groups);

    /**
     * Re-parent a list of unique group IDs.
     *
     * @param group
     * @param groups
     */
    void reparentGroupIds(GroupInterface group, List<String> groups);

    /**
     * Sets the group's department all all jobs in that
     * group to the new department.
     *
     * @param group
     * @param d
     */
    void setGroupDepartment(GroupInterface group, DepartmentInterface d);
}

