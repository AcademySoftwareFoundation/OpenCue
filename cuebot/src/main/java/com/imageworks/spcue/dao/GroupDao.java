
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



package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ShowInterface;

/**
 * A DAO for Group DB operations.
 *
 * @category DAO
 */
public interface GroupDao {

    /**
     * returns the group from its unique id
     *
     * @param id
     * @return
     */
    GroupInterface getGroup(String id);

    /**
     * returns a list of groups using their unique ids
     * @param id
     * @return
     */
    List<GroupInterface> getGroups(List<String> id);

    /**
     *
     * @param show
     * @return
     */
    GroupDetail getRootGroupDetail(ShowInterface show);

    /**
     * Returns the show's root group.
     *
     * @param show
     * @return
     */
    String getRootGroupId(ShowInterface show);

    /**
     * Insert group into specified parent
     *
     * @param group
     */
    void insertGroup(GroupDetail group, GroupInterface parent);

    /**
     *
     * @param group
     */
    void insertGroup(GroupDetail group);

    /**
     * Updates the groups department.
     *
     * @param group
     * @param dept
     */
    void updateDepartment(GroupInterface group, DepartmentInterface dept);

    /**
     * Removes the specified group.  You cannot delete a group that contains
     * jobs or other groups or the shows root folder.
     *
     * @param group
     */
    void deleteGroup(GroupInterface group);

    /**
     * Sets the group's new parent.  Triggers will handle any recursive level
     * changes.
     *
     * @param group
     * @param parent
     *
     * @throws EntityModificationError          throws this if the group is the top level group
     *                                          which cannot be parented to another group.
     */
    void updateGroupParent(GroupInterface group, GroupInterface parent);

    /**
     * Sets the maximum number of procs the group should be running.
     *
     * @param group
     * @param value
     */
    void updateDefaultJobMaxCores(GroupInterface group, int value);

    /**
     * Sets the minimum number of procs the group should be running.
     *
     * @param group
     * @param value
     */
    void updateDefaultJobMinCores(GroupInterface group, int value);

    /**
     * Sets the maximum number of cores for this group
     *
     * @param group
     * @param value
     */
    public void updateMaxCores(GroupInterface group, int value);

    /**
     * Set the minimum number of cores for this group
     *
     * @param group
     * @param value
     */

    public void updateMinCores(GroupInterface group, int value);

    /**
     * Sets the maximum number of procs the group should be running.
     *
     * @param group
     * @param value
     */
    void updateDefaultJobMaxGpu(GroupInterface group, int value);

    /**
     * Sets the minimum number of procs the group should be running.
     *
     * @param group
     * @param value
     */
    void updateDefaultJobMinGpu(GroupInterface group, int value);

    /**
     * Sets the maximum number of Gpu for this group
     *
     * @param group
     * @param value
     */
    public void updateMaxGpu(GroupInterface group, int value);

    /**
     * Set the minimum number of Gpu for this group
     *
     * @param group
     * @param value
     */

    public void updateMinGpu(GroupInterface group, int value);

    /**
     * Renames the group
     *
     * @param group
     * @param value
     */
    void updateName(GroupInterface group, String value);

    /**
     * Updates a group's priority.
     *
     * @param group
     * @param value
     */
    void updateDefaultJobPriority(GroupInterface group, int value);

    /**
     * Returns a full GroupDetail object from its unique id
     *
     * @param id
     * @return
     */
    GroupDetail getGroupDetail(String id);

    /**
     * Returns a recursive list of a group's children
     *
     * @param group
     * @return
     */
    List<GroupInterface> getChildrenRecursive(GroupInterface group);

    /**
     *
     * Returns a list of a groups immediate children
     *
     * @param group
     * @return
     */
    List<GroupInterface> getChildren(GroupInterface group);

    /**
     * Returns true if the group of the specified job is at or over its min proc
     *
     * @param job
     * @return
     */
    boolean isOverMinCores(JobInterface job);

    /**
     * Returns true if the group of the specified job is at or over its min gpu
     *
     * @param job
     * @return
     */
    boolean isOverMinGpu(JobInterface job);

    /**
     * Returns true if the group is managed.
     *
     * @param group
     * @return
     */
	boolean isManaged(GroupInterface group);

	/**
	 * Return a GroupDetail for the specified job.
	 * @param job
	 * @return
	 */
    GroupDetail getGroupDetail(JobInterface job);
}

