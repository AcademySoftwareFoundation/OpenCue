
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



package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.Department;
import com.imageworks.spcue.Group;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Show;

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
    Group getGroup(String id);

    /**
     * returns a list of groups using their unique ids
     * @param id
     * @return
     */
    List<Group> getGroups(List<String> id);

    /**
     *
     * @param show
     * @return
     */
    GroupDetail getRootGroupDetail(Show show);

    /**
     * Returns the show's root group.
     *
     * @param show
     * @return
     */
    String getRootGroupId(Show show);

    /**
     * Insert group into specified parent
     *
     * @param group
     */
    void insertGroup(GroupDetail group, Group parent);

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
    void updateDepartment(Group group, Department dept);

    /**
     * Removes the specified group.  You cannot delete a group that contains
     * jobs or other groups or the shows root folder.
     *
     * @param group
     */
    void deleteGroup(Group group);

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
    void updateGroupParent(Group group, Group parent);

    /**
     * Sets the maximum number of procs the group should be running.
     *
     * @param group
     * @param value
     */
    void updateDefaultJobMaxCores(Group group, int value);

    /**
     * Sets the minimum number of procs the group should be running.
     *
     * @param group
     * @param value
     */
    void updateDefaultJobMinCores(Group group, int value);

    /**
     * Sets the maximum number of cores for this group
     *
     * @param group
     * @param value
     */
    public void updateMaxCores(Group group, int value);

    /**
     * Set the minimum number of cores for this group
     *
     * @param group
     * @param value
     */

    public void updateMinCores(Group group, int value);
    /**
     * Renames the group
     *
     * @param group
     * @param value
     */
    void updateName(Group group, String value);

    /**
     * Updates a group's priority.
     *
     * @param group
     * @param value
     */
    void updateDefaultJobPriority(Group group, int value);

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
    List<Group> getChildrenRecursive(Group group);

    /**
     *
     * Returns a list of a groups immediate children
     *
     * @param group
     * @return
     */
    List<Group> getChildren(Group group);

    /**
     * Returns true if the group of the specified job is at or over its min proc
     *
     * @param job
     * @return
     */
    boolean isOverMinCores(Job job);

    /**
     * Returns true if the group is managed.
     *
     * @param group
     * @return
     */
	boolean isManaged(Group group);

	/**
	 * Return a GroupDetail for the specified job.
	 * @param job
	 * @return
	 */
    GroupDetail getGroupDetail(Job job);
}

