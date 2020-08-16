
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



package com.imageworks.spcue.service;

import java.util.List;

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.ThreadStats;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.Order;
import com.imageworks.spcue.util.FrameSet;

/**
 * JobManager pretty much handles all job management functions. From launching
 * killing jobs, to managing the layers, frames, etc within jobs.
 */
public interface JobManager {

    /**
     * Pause/unpause a job
     *
     * @param job
     * @param paused
     */
    void setJobPaused(JobInterface job, boolean paused);

    /**
     *
     * @param id
     * @return
     */
    public DispatchJob getDispatchJob(String id);

    /**
     *
     * @param id
     * @return
     */
    public DispatchFrame getDispatchFrame(String id);

    /**
     * Returns true if there is a pending job with the specifed
     * name on the cue.
     *
     * @param name
     * @return
     */
    boolean isJobPending(String name);

    /**
     * Returns true if the job has no more frames that
     * can possibly be dispatched.
     *
     * @return
     */
    boolean isJobComplete(JobInterface job);

    /**
     * Returns true if the layer is complete.
     *
     * @param layer
     * @return
     */
    boolean isLayerComplete(LayerInterface layer);

    /**
     * Launches a job spec.
     *
     * @param spec
     */
    void launchJobSpec(JobSpec spec);

    /**
     * Creates a new job entry
     *
     * @param BuildableJob job
     * @return JobDetail
     */
    JobDetail createJob(BuildableJob job);

    /**
     * Removes an existing job entry.  The job must be in the
     * Finished state before it can be removed.
     *
     * @param JobDetail job
     */
    void removeJob(JobInterface job);

    /**
     * Shutting down a job will signal RQD to kill all frames
     * and drop all dependencies for specified job.  Job is
     * put into Shutdown state which should be commited
     * before any other operations are done on the job.
     * When shutdown is complete, the job shoud be marked Finished.
     *
     * @param JobDetail job
     */
    boolean shutdownJob(JobInterface job);

    /**
     * Finds and active job by name.
     *
     * @param String name
     * @return JobDetail
     */
    JobDetail findJobDetail(String name);

    /**
     * Finds and active job by name.
     *
     * @param String name
     * @return JobDetail
     */
    JobInterface findJob(String name);

    /**
     * Gets an active job by ID.
     *
     * @param String id
     * @return JobDetail
     */
    JobDetail getJobDetail(String id);

    /**
     * Gets a job by unique id
     *
     * @param id
     * @return
     */
    JobInterface getJob(String id);

    /**
     *
     * @param id
     * @return LayerDetail
     */
    LayerDetail getLayerDetail(String id);

    /**
    * Return a layer by its unique ID.
    *
    * @param id
    * @return LayerDetail
    */
   LayerInterface getLayer(String id);

    /**
     *
     * @param id
     * @return FrameDetail
     */
    FrameDetail getFrameDetail(String id);

    /**
     * Return a frame with the given ID.
     *
     * @param id
     * @return
     */
    FrameInterface getFrame(String id);

    /**
     * Marks a specific frame as waiting, setting its dependency
     * count to 0 in the process even though it has active
     * dependencies.
     *
     * @param frame
     */
    public void markFrameAsWaiting(FrameInterface frame);

    /**
     * Marks a specific frame as Depend if the frame has
     * active dependencies.  This will pretty much undo
     * a markFrameAsWaiting.  If the frame has no active
     * depends this call should have no effect.
     *
     * @param frame
     */
    public void markFrameAsDepend(FrameInterface frame);

    /**
     * Return the result of the given FrameSearch.
     *
     * @param job
     * @param r
     * @return
     */
    public List<FrameInterface> findFrames(FrameSearchInterface r);

    /**
     * Updates specified frame to new state.
     *
     * @param frame
     * @param state
     */
    public void updateFrameState(FrameInterface frame, FrameState state);

    /**
     * Updates specified job to new state.
     *
     * @param job
     * @param state
     */
    public void updateJobState(JobInterface job, JobState state);

    /**
     * Reorders the specified layer.
     *
     * @param job
     * @param frameSet
     */
    public void reorderLayer(LayerInterface layer, FrameSet frameSet, Order order);

    /**
     *
     * @param layer
     * @param frameSet
     */
    public void staggerLayer(LayerInterface layer, String range, int stagger);

    /**
     * Returns all of the layers for the specified job
     *
     * @param job
     * @return
     */
    public List<LayerInterface> getLayers(JobInterface job);

    /**
     * Returns all of the layers for the specified job
     *
     * @param job
     * @return
     */
    public List<LayerDetail> getLayerDetails(JobInterface job);

    /**
     * Creates the job log directory.  The JobDetail object
     * must have the logDir property populated.
     *
     * @param newJob
     */
    public void createJobLogDirectory(JobDetail newJob);

    /**
     * Optimizes layer settings based on the specified maxRss
     * and run time.
     *
     * @param layer
     * @param maxRss
     * @param runTime
     */
    void optimizeLayer(LayerInterface layer, int cores, long maxRss, int runTime);

    /**
     * Return true if the given job is booked greater than min cores.
     *
     * @param job
     * @return
     */
    boolean isOverMinCores(JobInterface job);

    /**
     * Return true if the given job is booked greater than min gpu.
     *
     * @param job
     * @return
     */
    boolean isOverMinGpu(JobInterface job);

    /**
     * Increase the layer memory requirement to given KB value.
     *
     * @param layer
     * @param memKb
     */
    void increaseLayerMemoryRequirement(LayerInterface layer, long memKb);

    /**
     * Appends a tag to a layer's existing tags.
     *
     * @param layer
     * @param tag
     */
    void appendLayerTag(LayerInterface layer, String tag);

    /**
     * Replace all existing tags with the specified tag.
     *
     * @param layer
     * @param tag
     */
    void setLayerTag(LayerInterface layer, String tag);

    /**
     * Return true if the given layer is threadable.
     *
     * @param layer
     * @return
     */
    boolean isLayerThreadable(LayerInterface layer);

    /**
     * Enable or disable the layer memory optimizer.
     */
    void enableMemoryOptimizer(LayerInterface layer, boolean state);

    /**
     * Return the frame for the given layer and frame number.
     *
     * @param layer
     * @param number
     * @return
     */
    FrameInterface findFrame(LayerInterface layer, int number);

    /**
     *
     * @param job
     * @return
     */
    FrameDetail findLongestFrame(JobInterface job);

    /**
     *
     * @param job
     * @return
     */
    FrameDetail findShortestFrame(JobInterface job);

    /**
     *
     * @param job
     * @return
     */
    FrameStateTotals getFrameStateTotals(JobInterface job);

    /**
     *
     * @param job
     * @return
     */
    ExecutionSummary getExecutionSummary(JobInterface job);

    /**
     *
     * @param job
     * @return
     */
    FrameDetail findHighestMemoryFrame(JobInterface job);

    /**
     *
     * @param job
     * @return
     */
    FrameDetail findLowestMemoryFrame(JobInterface job);

    /**
     * Return the frame state totals by layer.
     *
     * @param layer
     * @return
     */
    FrameStateTotals getFrameStateTotals(LayerInterface layer);

    /**
     * Return the execution summary by layer.
     *
     * @param layer
     * @return
     */
    ExecutionSummary getExecutionSummary(LayerInterface layer);

    /**
     * Update the checkpoint state for the given frame.
     *
     * @param frame
     * @param state
     */
    void updateCheckpointState(FrameInterface frame, CheckpointState state);

    /**
     * Return a list of frames that failed to checkpoint within
     * the given checkpoint point.
     *
     * @param cutoffTimeMs
     * @return
     */
    List<FrameInterface> getStaleCheckpoints(int cutoffTimeSec);

    /**
     * Return a list of registered layer outputs.
     *
     * @param layer
     * @return
     */
    List<String> getLayerOutputs(LayerInterface layer);

    /**
     * Register layer output.
     *
     * @param layer
     * @return
     */
    void registerLayerOutput(LayerInterface layer, String filespec);

    /**
     * Return thread stats for the given layer.
     *
     * @param layer
     * @return
     */
    List<ThreadStats> getThreadStats(LayerInterface layer);

    /**
     * Update the max core value for the given layer.
     *
     * @param layer
     * @param coreUnits
     */
    void setLayerMaxCores(LayerInterface layer, int coreUnits);

    /**
     * Update the min core value for the given layer.
     *
     * @param layer
     * @param coreUnits
     */
    void setLayerMinCores(LayerInterface layer, int coreUnits);

    /**
     * Update the max gpu value for the given layer.
     *
     * @param layer
     * @param gpu
     */
    void setLayerMaxGpu(LayerInterface layer, int gpu);

    /**
     * Update the min gpu value for the given layer.
     *
     * @param layer
     * @param gpu
     */
    void setLayerMinGpu(LayerInterface layer, int gpu);

    /**
     * Add a limit to the given layer.
     *
     * @param layer
     * @param limitId
     */
    void addLayerLimit(LayerInterface layer, String limitId);

    /**
     * Remove a limit from the given layer.
     *
     * @param layer
     * @param limitId
     */
    void dropLayerLimit(LayerInterface layer, String limitId);

    /**
     * Return a list of limits for the given layer.
     *
     * @param layer
     */
    List<LimitEntity> getLayerLimits(LayerInterface layer);
}

