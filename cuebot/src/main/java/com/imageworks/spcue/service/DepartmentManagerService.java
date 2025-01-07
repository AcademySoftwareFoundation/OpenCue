
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

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.PointInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.TaskEntity;
import com.imageworks.spcue.TaskInterface;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.PointDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.TaskDao;
import com.imageworks.spcue.util.CueUtil;

@Transactional
public class DepartmentManagerService implements DepartmentManager {

    @Autowired
    private Environment env;

    private PointDao pointDao;
    private TaskDao taskDao;
    private ShowDao showDao;
    private JobDao jobDao;

    @Override
    public void createDepartmentConfig(PointDetail renderPoint) {
        pointDao.insertPointConf(renderPoint);
    }

    @Override
    public boolean departmentConfigExists(ShowInterface show, DepartmentInterface dept) {
        return pointDao.pointConfExists(show, dept);
    }

    @Override
    public void createTask(TaskEntity t) {
        taskDao.insertTask(t);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public TaskEntity getTaskDetail(String id) {
        return taskDao.getTaskDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public PointDetail getDepartmentConfigDetail(String id) {
        return pointDao.getPointConfDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public PointDetail getDepartmentConfigDetail(ShowInterface show, DepartmentInterface dept) {
        return pointDao.getPointConfigDetail(show, dept);
    }

    @Override
    public void removeTask(TaskInterface t) {
        taskDao.deleteTask(t);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void setMinCores(TaskInterface t, int coreUnits) {
        if (taskDao.isManaged(t)) {
            taskDao.adjustTaskMinCores(t, coreUnits);
        } else {
            taskDao.updateTaskMinCores(t, coreUnits);
        }
        this.syncJobsWithTask(taskDao.getTaskDetail(t.getTaskId()));
    }

    @Override
    public PointInterface createDepartmentConfig(ShowInterface show, DepartmentInterface dept) {
        return pointDao.insertPointConf(show, dept);
    }

    @Override
    public void clearTasks(PointInterface cdept) {
        taskDao.deleteTasks(cdept);
    }

    @Override
    public void clearTasks(ShowInterface show, DepartmentInterface dept) {
        taskDao.deleteTasks(show, dept);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void clearTaskAdjustment(TaskInterface t) {
        taskDao.clearTaskAdjustment(t);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void disableTiManaged(PointInterface cdept) {
        pointDao.updateDisableManaged(cdept);
        clearTasks(cdept);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void enableTiManaged(PointInterface p, String tiTask, int cores) {
        pointDao.updateEnableManaged(p, tiTask, cores);
        updateManagedTasks(p);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void setManagedCores(PointInterface p, int cores) {
        pointDao.updateManagedCores(p, cores);
        if (pointDao.isManaged(p, p)) {
            updateManagedTasks(p);
        }
    }

    @Override
    public void clearTaskAdjustments(PointInterface cdept) {
        taskDao.clearTaskAdjustments(cdept);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly = true)
    public List<PointDetail> getManagedPointConfs() {
        return pointDao.getManagedPointConfs();
    }

    /**
     * Any task with one of these as the production status is considered in progress.
     */
    private static final Set<String> IN_PROGRESS_TASK_STATUS = new HashSet<String>();
    static {
        IN_PROGRESS_TASK_STATUS.addAll(
                java.util.Arrays.asList(new String[] {"I/P", "Kicked To", "CBB", "Blocked"}));
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void updateManagedTasks(PointInterface pd) {}

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void syncJobsWithTask(TaskEntity t) {

        List<JobInterface> jobs = jobDao.getJobs(t);
        if (jobs.size() == 0) {
            return;
        }

        if (jobs.size() == 1) {
            jobDao.updateMinCores(jobs.get(0), t.minCoreUnits);
            return;
        }

        int core_units_per_job = t.minCoreUnits / (jobs.size() * 100);
        int core_units_left_over = (t.minCoreUnits % (jobs.size() * 100) / 100);

        /*
         * Calculate a base for each job
         */
        Map<JobInterface, Integer[]> minCores = new HashMap<JobInterface, Integer[]>(jobs.size());
        int core_units_unalloc = 0;

        for (JobInterface j : jobs) {
            FrameStateTotals totals = jobDao.getFrameStateTotals(j);
            if (totals.waiting < core_units_per_job) {
                core_units_unalloc = core_units_unalloc + (core_units_per_job - totals.waiting);
                minCores.put(j, new Integer[] {totals.waiting, totals.waiting});
            } else {
                minCores.put(j, new Integer[] {core_units_per_job, totals.waiting});
            }
        }

        /*
         * Apply any left over core units. If the job doesn't have waiting frames to apply them to
         * then don't do anything.
         */
        core_units_left_over = core_units_left_over + core_units_unalloc;
        while (core_units_left_over > 0) {
            boolean applied = false;
            for (JobInterface j : jobs) {
                if (core_units_left_over < 1) {
                    break;
                }
                if (minCores.get(j)[1] - minCores.get(j)[0] > 0) {
                    minCores.get(j)[0] = minCores.get(j)[0] + 1;
                    core_units_left_over = core_units_left_over - 1;
                    applied = true;
                }
            }
            if (!applied) {
                break;
            }
        }

        /*
         * Update the DB
         */
        for (JobInterface j : jobs) {
            jobDao.updateMinCores(j, minCores.get(j)[0] * 100);
        }
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void syncJobsWithTask(DepartmentInterface d, String shot) {
        syncJobsWithTask(taskDao.getTaskDetail(d, shot));
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void syncJobsWithTask(JobInterface job) {
        syncJobsWithTask(taskDao.getTaskDetail(job));
    }

    @Override
    public boolean isManaged(JobInterface j) {
        return taskDao.isManaged(j);
    }

    public TaskDao getTaskDao() {
        return taskDao;
    }

    public void setTaskDao(TaskDao taskDao) {
        this.taskDao = taskDao;
    }

    public ShowDao getShowDao() {
        return showDao;
    }

    public void setShowDao(ShowDao showDao) {
        this.showDao = showDao;
    }

    public PointDao getPointDao() {
        return pointDao;
    }

    public void setPointDao(PointDao pointDao) {
        this.pointDao = pointDao;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }
}
