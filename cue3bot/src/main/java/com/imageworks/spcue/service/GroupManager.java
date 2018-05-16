
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

import com.imageworks.spcue.Department;
import com.imageworks.spcue.Group;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Show;

public interface GroupManager {

    void setGroupMaxCores(Group g, int coreUnits);
    void setGroupMinCores(Group g, int coreUnits);
    void setGroupDefaultJobMinCores(Group g, int coreUnits);
    void setGroupDefaultJobMaxCores(Group g, int coreUnits);
    void setGroupDefaultJobPriority(Group g, int priority);

    /**
     * Return the group from its unique ID
     *
     * @param id
     * @return
     */
    Group getGroup(String id);

    /**
     * Return the root group for the specified show.
     *
     * @param s
     * @return
     */
    GroupDetail getRootGroupDetail(Show s);

    /**
     * Return the GroupDetail by job.
     *
     * @param j
     * @return
     */
    GroupDetail getGroupDetail(Job j);

    /**
     * Return a GroupDetail from its unique ID
     *
     * @param id
     * @return
     */
    GroupDetail getGroupDetail(String id);

    void setGroupParent(Group group, Group newParent);

    void deleteGroup(Group group);

    void createGroup(GroupDetail group, Group parent);

    /**
     * Re-parent a job to the specified group.
     *
     * @param job
     * @param group
     * @param inherit
     */
    void reparentJob(Job job, GroupDetail group, Inherit[] inherit);

    /**
     * Parents a list of groups to the specified group
     *
     * @param group
     * @param groups
     */
    void reparentGroups(Group group, List<Group> groups);

    /**
     * Re-parent a list of unique group IDs.
     *
     * @param group
     * @param groups
     */
    void reparentGroupIds(Group group, List<String> groups);

    /**
     * Sets the group's department all all jobs in that
     * group to the new department.
     *
     * @param group
     * @param d
     */
    void setGroupDepartment(Group group, Department d);
}

