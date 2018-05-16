
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
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Point;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.Task;
import com.imageworks.spcue.TaskDetail;

public interface DepartmentManager {

    /**
     * Creates a new render point configurtion.  A render point configuration
     * maps a cue3 department to a Track-It task and priorizes shots based
     * frame and final date info.
     *
     * @param renderPoint
     */
    public void createDepartmentConfig(PointDetail renderPoint);

    /**
     * Creates a new render point configurtion.  A render point configuration
     * maps a cue3 department to a Track-It task and priorizes shots based
     * frame and final date info.
     *
     * @param renderPoint
     */
    public Point createDepartmentConfig(Show show, Department dept);

    /**
     * Returns true if a render point configuration already exists
     * for the specified show and department.
     *
     * @param show
     * @param dept
     * @return
     */
    public boolean departmentConfigExists(Show show, Department dept);

    /**
     * Creates a new task.  A task is for setting minimum procs
     * by shot and department
     *
     * @param t
     */
    public void createTask(TaskDetail t);

    /**
     * Removes the specified task
     *
     * @param t
     */
    public void removeTask(Task t);

    /**
     * Returns task details
     *
     * @param id
     * @return
     */
    public TaskDetail getTaskDetail(String id);

    /**
     * Sets the minimum core value for the specified task.  If the task is managed
     * then the cores will be adjusted, leaving the original min cores value in tact.
     * If the task is not managed then the min cores value is altered directly.
     *
     * @param t
     * @param value
     */
    public void setMinCores(Task t, int coreUnits);

    /**
     * Sets the minimum core value for the specified task.  If the task is managed
     * then the cores will be adjusted, leaving the original min cores value in tact.
     * If the task is not managed then the min cores value is altered directly.
     *
     * @param t
     * @param value
     */
    public void clearTaskAdjustments(Point rp);

    /**
     * Enables TI integration
     *
     * @param rp
     * @param tiTask
     * @param cores
     */
    public void enableTiManaged(Point rp, String tiTask, int coreUnits);

    /**
     * Disables Track-It management
     *
     * @param rp
     */
    public void disableTiManaged(Point rp);

    /**
     * Updates TI Managed tasks and recalculates all of the min core values
     *
     * @param rp
     */
    public void updateManagedTasks(Point rp);

    /**
     * Set the number of cores to normalize the proc point shots with.
     *
     * @param cdept
     * @param cores
     */
    public void setManagedCores(Point cdept, int coreUnits);

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
    PointDetail getDepartmentConfigDetail(Show show, Department dept);

    /**
     * Returns a list of all managed point configurations.  Managed point
     * configurations get priortities from an outside source, such as track it.
     *
     * @return a list of point configurations being managed by Track-It
     */
    List<PointDetail> getManagedPointConfs();

    /**
     * Clears all existing tasks for specified department
     *
     * @param cdept
     */
    public void clearTasks(Point cdept);

    /**
     *  Clears all existing tasks for specified show and department
     * @param show
     * @param dept
     */
    public void clearTasks(Show show, Department dept);

    /**
     * Updates the min proc value of all jobs that fall within
     * the specified task.
     *
     * @param TaskDetail the task to sync with
     */
    void syncJobsWithTask(TaskDetail t);

    /**
     * Updates the min proc value of all jobs that fall within
     * the specified task.
     *
     * @param TaskDetail the task to sync with
     */
    void syncJobsWithTask(Department d, String shot);

    /**
     * Updates the min proc value of all jobs that fall within
     * the specified task.
     *
     * @param TaskDetail the task to sync with
     */
    void syncJobsWithTask(Job job);

    /**
     * Returns true of the job is managed by a department manager.
     *
     * @param j
     */
    boolean isManaged(Job j);

    /**
     *
     * @param t
     */
    void clearTaskAdjustment(Task t);


}

