
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
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Point;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.Show;

public interface PointDao {

    /**
     * Inserts a render into the point table
     *
     * @param t
     * @return
     */
    void insertPointConf(PointDetail t);

    /**
     * Inserts and returns an empty render point detail
     *
     * @param show
     * @param dept
     * @return
     */
    PointDetail insertPointConf(Show show, Department dept);

    /**
     * Returns true if the department is being managed by track-it.
     *
     * @param show
     * @param dept
     * @return
     */
    boolean isManaged(Show show, Department dept);

    /**
     * Returns true if a render point config already exists
     * for the specified show and department
     *
     * @param show
     * @param dept
     * @return
     */
    boolean pointConfExists(Show show, Department dept);

    /**
     * Updates the number of cores managed by this department
     *
     * @param cdept
     * @param cores
     */
    void updateManagedCores(Point cdept, int cores);

    /**
     * Enables TI managed.
     *
     * @param p
     * @param task
     * @param cores
     */
    void updateEnableManaged(Point cdept, String task, int cores);

    /**
     * Disables TI mananaged.
     *
     * @param p
     */
    void updateDisableManaged(Point cdept);

    /**
     * Returns a list of all managed point configs.
     *
     * @return
     */
    List<PointDetail> getManagedPointConfs();

    /**
     * Returns a DepartmentConfigDetail by unique ID
     *
     * @param id
     * @return
     */
    PointDetail getPointConfDetail(String id);

    /**
     * Returns a DepartmentConfigDetail using the specified show and department
     *
     *
     * @param show
     * @param dept
     * @return
     */
    PointDetail getPointConfigDetail(Show show, Department dept);

    /**
    * Updates the time at which the point config was last updated.
    *
    * @param t
    */
   void updatePointConfUpdateTime(Point t);

   /**
    *
    * @param job
    * @return
    */
   boolean isOverMinCores(Job job);

}

