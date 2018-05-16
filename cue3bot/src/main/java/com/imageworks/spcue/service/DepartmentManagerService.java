
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

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.Department;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Point;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.Task;
import com.imageworks.spcue.TaskDetail;
import com.imageworks.spcue.TrackitTaskDetail;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.PointDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.TaskDao;
import com.imageworks.spcue.dao.TrackitDao;
import com.imageworks.spcue.util.CueUtil;

@Transactional
public class DepartmentManagerService implements DepartmentManager {

    private PointDao pointDao;
    private TaskDao taskDao;
    private ShowDao showDao;
    private JobDao jobDao;
    private TrackitDao trackitDao;

    @Override
    public void createDepartmentConfig(PointDetail renderPoint) {
        pointDao.insertPointConf(renderPoint);
    }

    @Override
    public boolean departmentConfigExists(Show show, Department dept) {
        return pointDao.pointConfExists(show, dept);
    }

    @Override
    public void createTask(TaskDetail t) {
        taskDao.insertTask(t);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public TaskDetail getTaskDetail(String id) {
        return taskDao.getTaskDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public PointDetail getDepartmentConfigDetail(String id) {
        return pointDao.getPointConfDetail(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public PointDetail getDepartmentConfigDetail(Show show, Department dept) {
        return pointDao.getPointConfigDetail(show, dept);
    }

    @Override
    public void removeTask(Task t) {
        taskDao.deleteTask(t);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void setMinCores(Task t, int coreUnits) {
        if (taskDao.isManaged(t)) {
            taskDao.adjustTaskMinCores(t, coreUnits);
        } else {
            taskDao.updateTaskMinCores(t, coreUnits);
        }
        this.syncJobsWithTask(taskDao.getTaskDetail(t.getTaskId()));
    }

    @Override
    public Point createDepartmentConfig(Show show, Department dept) {
        return pointDao.insertPointConf(show, dept);
    }

    @Override
    public void clearTasks(Point cdept) {
        taskDao.deleteTasks(cdept);
    }

    @Override
    public void clearTasks(Show show, Department dept) {
        taskDao.deleteTasks(show, dept);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void clearTaskAdjustment(Task t) {
        taskDao.clearTaskAdjustment(t);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void disableTiManaged(Point cdept) {
        pointDao.updateDisableManaged(cdept);
        clearTasks(cdept);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void enableTiManaged(Point p, String tiTask, int cores) {
        pointDao.updateEnableManaged(p, tiTask, cores);
        updateManagedTasks(p);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void setManagedCores(Point p, int cores) {
        pointDao.updateManagedCores(p, cores);
        if (pointDao.isManaged(p, p)) {
            updateManagedTasks(p);
        }
    }

    @Override
    public void clearTaskAdjustments(Point cdept) {
        taskDao.clearTaskAdjustments(cdept);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<PointDetail> getManagedPointConfs() {
        return pointDao.getManagedPointConfs();
    }


    /**
     * Any task with one of these as the production status is
     * considered in progress.
     */
    private static final Set<String> IN_PROGRESS_TASK_STATUS = new HashSet<String>();
    static  {
        IN_PROGRESS_TASK_STATUS.addAll(java.util.Arrays.asList(
                new String[] {"I/P","Kicked To","CBB","Blocked"}));
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void updateManagedTasks(Point pd ) {

        Show show = showDao.getShowDetail(pd.getShowId());
        PointDetail p = pointDao.getPointConfDetail(pd.getPointId());
        pointDao.updatePointConfUpdateTime(p);

        /*
         * First calculate raw point ratios, which will be used to calculate
         * the normalized proc point values
         */
        float totalRawPoints = 0f;
        float rawPoints = 0f;

        List<TrackitTaskDetail> tasks = trackitDao.getTasks(show.getName(), p.tiTask);
        HashMap<String,Float> rawCache = new HashMap<String,Float>(tasks.size());

        for (TrackitTaskDetail task: tasks) {
            if (!IN_PROGRESS_TASK_STATUS.contains(task.status)) {
                continue;
            }
            rawPoints = ((task.frameCount / 10f) / task.weeks);
            rawCache.put(task.shot, rawPoints);
            totalRawPoints = totalRawPoints + rawPoints;
        }

        /*
         * Now create TaskDetail objects which will be merged into
         * the current data set.  Tasks with a 0 minCores value will
         * be deleted.
         */
        float normalizedRawPoints = p.cores / totalRawPoints;
        for (TrackitTaskDetail task: tasks) {

            TaskDetail td = new TaskDetail();
            td.pointId = p.getPointId();
            td.deptId = p.getDepartmentId();
            td.showId = p.getShowId();
            td.shot = task.shot;

            if (!IN_PROGRESS_TASK_STATUS.contains(task.status)) {
                td.minCoreUnits = 0;
            }
            else {
                td.minCoreUnits = (int) ((rawCache.get(task.shot) * normalizedRawPoints) + 0.5f);
                if (td.minCoreUnits < CueUtil.ONE_CORE) {
                    td.minCoreUnits = CueUtil.ONE_CORE;
                }
            }
            taskDao.mergeTask(td);
            syncJobsWithTask(td);
        }
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void syncJobsWithTask(TaskDetail t) {

        List<Job> jobs = jobDao.getJobs(t);
        if (jobs.size() == 0) {
            return;
        }

        if (jobs.size() == 1) {
            jobDao.updateMinCores(jobs.get(0), t.minCoreUnits);
            return;
        }

        int core_units_per_job =  t.minCoreUnits / (jobs.size() * 100);
        int core_units_left_over = (t.minCoreUnits % (jobs.size() * 100) / 100);

        /*
         * Calculate a base for each job
         */
        Map<Job,Integer[]> minCores = new HashMap<Job,Integer[]>(jobs.size());
        int core_units_unalloc = 0;

        for (Job j: jobs) {
            FrameStateTotals totals = jobDao.getFrameStateTotals(j);
            if (totals.waiting  < core_units_per_job) {
                core_units_unalloc= core_units_unalloc
                    + (core_units_per_job - totals.waiting);
                minCores.put(j, new Integer[] {totals.waiting, totals.waiting});
            }
            else {
                minCores.put(j, new Integer[] {core_units_per_job, totals.waiting});
            }
        }

        /*
         * Apply any left over core units. If the job doesn't have
         * waiting frames to apply them to then don't do anything.
         */
        core_units_left_over = core_units_left_over + core_units_unalloc;
        while (core_units_left_over > 0) {
            boolean applied = false;
            for (Job j: jobs) {
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
        for (Job j: jobs) {
            jobDao.updateMinCores(j, minCores.get(j)[0] * 100);
        }
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void syncJobsWithTask(Department d, String shot) {
        syncJobsWithTask(taskDao.getTaskDetail(d, shot));
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void syncJobsWithTask(Job job) {
        syncJobsWithTask(taskDao.getTaskDetail(job));
    }

    @Override
    public boolean isManaged(Job j) {
        return taskDao.isManaged(j);
    }

    public TaskDao getTaskDao() {
        return taskDao;
    }

    public void setTaskDao(TaskDao taskDao) {
        this.taskDao = taskDao;
    }

    public TrackitDao getTrackitDao() {
        return trackitDao;
    }

    public void setTrackitDao(TrackitDao trackitDao) {
        this.trackitDao = trackitDao;
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

