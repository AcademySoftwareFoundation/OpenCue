
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

package com.imageworks.spcue.service;

import java.util.List;

import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.PointInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.TaskEntity;
import com.imageworks.spcue.TaskInterface;

public interface DepartmentManager {

    /**
     * Creates a new render point configurtion. A render point configuration maps an OpenCue
     * department to a Track-It task and priorizes shots based frame and final date info.
     *
     * @param renderPoint
     */
    public void createDepartmentConfig(PointDetail renderPoint);

    /**
     * Creates a new render point configurtion. A render point configuration maps an OpenCue
     * department to a Track-It task and priorizes shots based frame and final date info.
     *
     * @param renderPoint
     */
    public PointInterface createDepartmentConfig(ShowInterface show, DepartmentInterface dept);

    /**
     * Returns true if a render point configuration already exists for the specified show and
     * department.
     *
     * @param show
     * @param dept
     * @return
     */
    public boolean departmentConfigExists(ShowInterface show, DepartmentInterface dept);

    /**
     * Creates a new task. A task is for setting minimum procs by shot and department
     *
     * @param t
     */
    public void createTask(TaskEntity t);

    /**
     * Removes the specified task
     *
     * @param t
     */
    public void removeTask(TaskInterface t);

    /**
     * Returns task details
     *
     * @param id
     * @return
     */
    public TaskEntity getTaskDetail(String id);

    /**
     * Sets the minimum core value for the specified task. If the task is managed then the cores
     * will be adjusted, leaving the original min cores value in tact. If the task is not managed
     * then the min cores value is altered directly.
     *
     * @param t
     * @param value
     */
    public void setMinCores(TaskInterface t, int coreUnits);

    /**
     * Sets the minimum core value for the specified task. If the task is managed then the cores
     * will be adjusted, leaving the original min cores value in tact. If the task is not managed
     * then the min cores value is altered directly.
     *
     * @param t
     * @param value
     */
    public void clearTaskAdjustments(PointInterface rp);

    /**
     * Enables TI integration
     *
     * @param rp
     * @param tiTask
     * @param cores
     */
    public void enableTiManaged(PointInterface rp, String tiTask, int coreUnits);

    /**
     * Disables Track-It management
     *
     * @param rp
     */
    public void disableTiManaged(PointInterface rp);

    /**
     * Updates TI Managed tasks and recalculates all of the min core values
     *
     * @param rp
     */
    public void updateManagedTasks(PointInterface rp);

    /**
     * Set the number of cores to normalize the proc point shots with.
     *
     * @param cdept
     * @param cores
     */
    public void setManagedCores(PointInterface cdept, int coreUnits);

    /**
     * Returns a department configuration detail object from its id.
     *
     * @param id
     * @return
     */
    PointDetail getDepartmentConfigDetail(String id);

    /**
     * Returns a department configuration detail object
     *
     * @param show
     * @param dept
     * @return
     */
    PointDetail getDepartmentConfigDetail(ShowInterface show, DepartmentInterface dept);

    /**
     * Returns a list of all managed point configurations. Managed point configurations get
     * priortities from an outside source, such as track it.
     *
     * @return a list of point configurations being managed by Track-It
     */
    List<PointDetail> getManagedPointConfs();

    /**
     * Clears all existing tasks for specified department
     *
     * @param cdept
     */
    public void clearTasks(PointInterface cdept);

    /**
     * Clears all existing tasks for specified show and department
     * 
     * @param show
     * @param dept
     */
    public void clearTasks(ShowInterface show, DepartmentInterface dept);

    /**
     * Updates the min proc value of all jobs that fall within the specified task.
     *
     * @param TaskDetail the task to sync with
     */
    void syncJobsWithTask(TaskEntity t);

    /**
     * Updates the min proc value of all jobs that fall within the specified task.
     *
     * @param TaskDetail the task to sync with
     */
    void syncJobsWithTask(DepartmentInterface d, String shot);

    /**
     * Updates the min proc value of all jobs that fall within the specified task.
     *
     * @param TaskDetail the task to sync with
     */
    void syncJobsWithTask(JobInterface job);

    /**
     * Returns true of the job is managed by a department manager.
     *
     * @param j
     */
    boolean isManaged(JobInterface j);

    /**
     *
     * @param t
     */
    void clearTaskAdjustment(TaskInterface t);

}
