
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
 */

package com.imageworks.spcue.dao;

import com.imageworks.spcue.DepartmentInterface;

/**
 * This DAO currently does double duty. It handles the creation, removal, and updating of Department
 * and DepartmentConfig entries.
 */
public interface DepartmentDao {

    /**
     * Finds a department by name. Department objects contain only a name and a unique ID.
     *
     * @param name
     * @return Department
     */
    public DepartmentInterface findDepartment(String name);

    /**
     * Finds a department by id. Department objects contain only a name and a unique ID.
     *
     * @param id
     * @return Department
     */
    public DepartmentInterface getDepartment(String id);

    /**
     * Returns the cue's default department. The default department is assigned to any job that
     * falls within a group that doesn't have a department. Usually this is Unassigned.
     *
     * @return Department
     */
    public DepartmentInterface getDefaultDepartment();

    /**
     * Returns true if the department exists
     *
     * @param name
     * @return
     */
    public boolean departmentExists(String name);

    /**
     * Inserts a new department record. Departments are only a name and a unique ID.
     *
     * @param name
     */
    public void insertDepartment(String name);

    /**
     * Removes the specified department.
     *
     * @param d
     */
    public void deleteDepartment(DepartmentInterface d);
}
