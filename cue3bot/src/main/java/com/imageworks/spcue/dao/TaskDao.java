
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

import com.imageworks.spcue.Department;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Point;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.Task;
import com.imageworks.spcue.TaskDetail;

public interface TaskDao {

    /**
     * Delete all tasks for the specified dept config
     *
     * @param d
     */
    void deleteTasks(Point cdept);

    /**
     * Delete all tasks for the specified show and dept
     *
     * @param d
     */
    void deleteTasks(Show show, Department dept);

    /**
     * Inserts a new task. A task is a shot based department priority.
     *
     * @param task
     */
    void insertTask(TaskDetail task);

    /**
     * Remove specified task.
     *
     * @param task
     */
    void deleteTask(Task task);

    /**
     * Returns a task from its unique id
     *
     * @param id
     */
    TaskDetail getTaskDetail(String id);

    /**
     * Returns a job's task representation
     *
     * @param j
     * @return
     */
    TaskDetail getTaskDetail(Job j);

    /**
     * Updates the specified tasks min procs
     *
     * @param t
     * @param value
     */
    void updateTaskMinCores(Task t, int value);

    /**
     * Inserts a task if if does not exist, otherwise its updated.
     *
     * @param t
     */
    void mergeTask(TaskDetail t);

    /**
     * Returns true if the task is ti-managed.
     */
    boolean isManaged(Task t);

    /**
     * Adjusts the specified task's min cores to value. Only use adjust when the
     * task is managed.
     *
     * @param t
     * @param value
     */
    void adjustTaskMinCores(Task t, int value);

    /**
     *
     * @param cdept
     */
    void clearTaskAdjustments(Point cdept);

    /**
     *
     * @param t
     */
    void clearTaskAdjustment(Task t);

    /**
     * Returns a TaskDetail from a department id and shot name.
     *
     * @param d
     * @param shot
     * @return
     */
    TaskDetail getTaskDetail(Department d, String shot);

    /**
     * Returns true if the specified job is being managed by a task.
     *
     * @param Job
     */
    boolean isManaged(Job j);
}

