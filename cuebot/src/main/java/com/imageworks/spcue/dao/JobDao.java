
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
import java.util.Map;

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.DepartmentInterface;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.TaskEntity;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.util.JobLogUtil;

public interface JobDao {

    /**
     * Updates all jobs in the speficed group to the
     * max cores value.
     *
     * @param g
     * @param cores
     */
    public void updateMaxCores(GroupInterface g, int cores);

    /**
     * Updates all jobs in the specifid group to the
     * min cores value.
     *
     * @param g
     * @param cores
     */
    public void updateMinCores(GroupInterface g, int cores);

    /**
     * Updates all jobs in the speficed group to the
     * max gpu value.
     *
     * @param g
     * @param gpu
     */
    public void updateMaxGpus(GroupInterface g, int gpus);

    /**
     * Updates all jobs in the specifid group to the
     * min gpu value.
     *
     * @param g
     * @param gpu
     */
    public void updateMinGpus(GroupInterface g, int gpus);

    /**
     * Updates all jobs in the specified group to the
     * set priority.
     *
     * @param g
     * @param priority
     */
    public void updatePriority(GroupInterface g, int priority);

    /**
     * Updates a jobs parent group to specified group
     *
     * @param job
     * @param group
     */
    void updateParent(JobInterface job, GroupDetail group, Inherit[] inherit);

    /**
     * Returns an execution summary for the specified job.
     *
     * @param job
     * @return
     */
    ExecutionSummary getExecutionSummary(JobInterface job);

    /**
     * returns a FrameStateTotals object with all of the
     * job's frame state totals.
     *
     * @param job
     * @return
     */
    FrameStateTotals getFrameStateTotals(JobInterface job);

    /**
     * Returns a DispatchJob from its unique id
     *
     * @param uuid
     * @return
     */
    DispatchJob getDispatchJob(String uuid);

    /**
     * Returns true if the job has no more frames that
     * can possibly be dispatched.
     *
     * @param job
     * @return
     */
    boolean isJobComplete(JobInterface job);

    /**
     * Inserts a JobDetail.  The job will not be pending until its
     * activated.
     *
     * @param j
     */
    void insertJob(JobDetail j, JobLogUtil jobLogUtil);

    /**
     * Finds a Job from its name.  This method returns only
     * the current running job.
     *
     * @param name
     * @return
     */
    JobInterface findJob(String name);

    /**
     * Finds a JobDetail from its name.  This method returns only
     * the current running job.
     *
     * @param name
     * @return
     */
    JobDetail findJobDetail(String name);

    /**
     * Gets a JobDetail from its unique ID
     *
     * @param id
     * @return
     */
    JobDetail getJobDetail(String id);

    /**
     * Returns a job by its ID
     *
     * @param id
     * @return
     */
    JobInterface getJob(String id);

    /**
     * Returns a list of jobs assigned to a specific task.
     *
     * @param idl
     * @return
     */
    List<JobInterface> getJobs(TaskEntity t);

    /**
     * Finds all the jobs in a show.
     *
     * @param show
     * @return
     */
    List<JobDetail> findJobs(ShowInterface show);

    /**
     *
     * @param group
     * @return
     */
    List<JobDetail> findJobs(GroupInterface group);

    /**
     * Returns true if an active job with the specified name exists
     *
     * @param name
     * @return
     */
    boolean exists(String name);

    /**
     * Deletes specified job from DB
     *
     * @param job
     */
    void deleteJob(JobInterface job);

    /**
     * Activate job in lauching state.
     *
     * @param job
     */
    void activateJob(JobInterface job, JobState jobState);

    /**
     * updates the state of a job with new job state
     *
     * @param job
     * @param state
     */
    void updateState(JobInterface job, JobState state);

    /**
     * updates a job to the finished state. returns true
     * if the job was updated
     *
     * @param job
     */
    boolean updateJobFinished(JobInterface job);

    /**
     * reteurns true if job is over its minimum proc
     *
     * @param job
     * @return boolean
     */
    boolean isOverMinCores(JobInterface job);

    /**
     * returns true if a job has pending frames.
     *
     * @param job
     * @return
     */
    boolean hasPendingFrames(JobInterface job);

    /**
     * returns true if job is over max procs
     *
     * @param job
     * @return
     */
    boolean isOverMaxCores(JobInterface job);

    /**
     * returns true if job is at its max proc
     *
     * @param job
     * @return
     */
    boolean isAtMaxCores(JobInterface job);

    /**
     * Return true if adding given core units to the job
     * will set the job over its max core value.
     *
     * @param job
     * @param coreUnits
     * @return
     */
    boolean isOverMaxCores(JobInterface job, int coreUnits);

    /**
     * reteurns true if job is over its minimum gpus
     *
     * @param job
     * @return boolean
     */
    boolean isOverMinGpus(JobInterface job);

    /**
     * returns true if job is over max gpus
     *
     * @param job
     * @return
     */
    boolean isOverMaxGpus(JobInterface job);

    /**
     * returns true if job is at its max gpus
     *
     * @param job
     * @return
     */
    boolean isAtMaxGpus(JobInterface job);

    /**
     * Return true if adding given gpus to the job
     * will set the job over its max gpus value.
     *
     * @param job
     * @param gpus
     * @return
     */
    boolean isOverMaxGpus(JobInterface job, int gpus);

    /**
     * sets the jobs new priority value
     *
     * @param j
     * @param v
     */
    void updatePriority(JobInterface j, int v);

    /**
     * sets the jobs new min proc value
     *
     * @param j
     * @param v
     */
    void updateMinCores(JobInterface j, int v);

    /**
     * sets the jobs new max proc value
     *
     * @param j
     * @param v
     */
    void updateMaxCores(JobInterface j, int v);

    /**
     * sets the jobs new min gpu value
     *
     * @param j
     * @param v
     */
    void updateMinGpus(JobInterface j, int v);

    /**
     * sets the jobs new max gpu value
     *
     * @param j
     * @param v
     */
    void updateMaxGpus(JobInterface j, int v);

    /**
     * Update a job's paused state
     *
     * @param j
     * @param b
     */
    void updatePaused(JobInterface j, boolean b);

    /**
     * Update a jobs auto-eat state
     *
     * @param j
     * @param b
     */
    void updateAutoEat(JobInterface j, boolean b);

    /**
     * Updates the int_max_retries column with the value of
     * max_retries.  Checks to make sure max_retries
     * is greater than 0 and less than or equal to
     * MAX_FRAME_RETRIES
     *
     * @param Job
     * @param max_retries
     */
    void updateMaxFrameRetries(JobInterface j, int max_retries);

    /**
     * Inserts a map into the job's env table
     *
     *
     * @param job
     * @param env
     */
    void insertEnvironment(JobInterface job, Map<String,String> env);

    /**
     * Update jobs max RSS.  Only updates if the passed in value
     * is greater than the current value of int_max_rss
     *
     * @param job
     * @param env
     */
    void updateMaxRSS(JobInterface job, long maxRss);

    /**
     * Inserts a key/value pair into the jobs env table
     *
     * @param job
     * @param key
     * @param value
     */
    void insertEnvironment(JobInterface job, String key, String value);

    /**
     * Grabs the job environment
     *
     * @param job
     * @return
     */
    Map<String,String> getEnvironment(JobInterface job);

    /**
     * Updates the job's log path in the DB.  This doesn't touch the file
     * system.
     *
     * @param job
     * @param path
     */
    public void updateLogPath(JobInterface job, String path);

    /**
     *
     * @param name
     * @return
     */
    public JobDetail findLastJob(String name);

    /**
     * Returns true of the cue has some pending jobs
     *
     * @return
     */
    public boolean cueHasPendingJobs(FacilityInterface f);

    /**
     * Enables/disables autobooking for specified job.
     *
     * @param value
     */
    public void enableAutoBooking(JobInterface job, boolean value);

    /**
     * Enables/disables auto unbooking for specified job.
     *
     * @param job
     * @param value
     */
    void enableAutoUnBooking(JobInterface job, boolean value);

    /**
     * Maps the post job to the specified job
     *
     * @param job
     */
    void mapPostJob(BuildableJob job);

    /**
     * Activates the specified job's post job
     *
     * @param job
     */
    void activatePostJob(JobInterface job);

    /**
     * Update all jobs in the specified group to the
     * specified department.
     *
     * @param group
     */
    void updateDepartment(GroupInterface group, DepartmentInterface dept);

    /**
     * Update the specified job to the specified department.
     *
     * @param group
     */
    void updateDepartment(JobInterface job, DepartmentInterface dept);

    /**
     * Set the job's new parent.  The job will automatically
     * inherit all relevant settings from the group.
     *
     * @param job
     * @param dest
     */
    void updateParent(JobInterface job, GroupDetail dest);

    /**
     * Update layer usage with processor time usage.
     * This happens when the proc has completed or failed some work.
     *
     * @param proc
     * @param newState
     */
    void updateUsage(JobInterface job, ResourceUsage usage, int exitStatus);

    /**
     * Returns true if the job is launching
     *
     * @param j
     * @return
     */
    boolean isLaunching(JobInterface j);

    void updateEmail(JobInterface job, String email);
}

