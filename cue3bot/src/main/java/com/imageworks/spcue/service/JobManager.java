
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

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.Frame;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.ThreadStats;
import com.imageworks.spcue.CueIce.CheckpointState;
import com.imageworks.spcue.CueIce.FrameState;
import com.imageworks.spcue.CueIce.Order;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.util.FileSequence.FrameSet;

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
    void setJobPaused(Job job, boolean paused);

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
    boolean isJobComplete(Job job);

    /**
     * Returns true if the layer is complete.
     *
     * @param layer
     * @return
     */
    boolean isLayerComplete(Layer layer);

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
    void removeJob(Job job);

    /**
     * Shutting down a job will signal RQD to kill all frames
     * and drop all dependencies for specified job.  Job is
     * put into Shutdown state which should be commited
     * before any other operations are done on the job.
     * When shutdown is complete, the job shoud be marked Finished.
     *
     * @param JobDetail job
     */
    boolean shutdownJob(Job job);

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
    Job findJob(String name);

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
    Job getJob(String id);

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
   Layer getLayer(String id);

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
    Frame getFrame(String id);

    /**
     * Marks a specific frame as waiting, setting its dependency
     * count to 0 in the process even though it has active
     * dependencies.
     *
     * @param frame
     */
    public void markFrameAsWaiting(Frame frame);

    /**
     * Marks a specific frame as Depend if the frame has
     * active dependencies.  This will pretty much undo
     * a markFrameAsWaiting.  If the frame has no active
     * depends this call should have no effect.
     *
     * @param frame
     */
    public void markFrameAsDepend(Frame frame);

    /**
     * Return the result of the given FrameSearch.
     *
     * @param job
     * @param r
     * @return
     */
    public List<Frame> findFrames(FrameSearch r);

    /**
     * Updates specified frame to new state.
     *
     * @param frame
     * @param state
     */
    public void updateFrameState(Frame frame, FrameState state);

    /**
     * Reorders the specified layer.
     *
     * @param job
     * @param frameSet
     */
    public void reorderLayer(Layer layer, FrameSet frameSet, Order order);

    /**
     *
     * @param layer
     * @param frameSet
     */
    public void staggerLayer(Layer layer, String range, int stagger);

    /**
     * Returns all of the layers for the specified job
     *
     * @param job
     * @return
     */
    public List<Layer> getLayers(Job job);

    /**
     * Returns all of the layers for the specified job
     *
     * @param job
     * @return
     */
    public List<LayerDetail> getLayerDetails(Job job);

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
    void optimizeLayer(Layer layer, int cores, long maxRss, int runTime);

    /**
     * Return true if the given job is booked greater than min cores.
     *
     * @param job
     * @return
     */
    boolean isOverMinCores(Job job);

    /**
     * Increase the layer memory requirement to given KB value.
     *
     * @param layer
     * @param memKb
     */
    void increaseLayerMemoryRequirement(Layer layer, long memKb);

    /**
     * Appends a tag to a layer's existing tags.
     *
     * @param layer
     * @param tag
     */
    void appendLayerTag(Layer layer, String tag);

    /**
     * Replace all existing tags with the specified tag.
     *
     * @param layer
     * @param tag
     */
    void setLayerTag(Layer layer, String tag);

    /**
     * Return true if the given layer is threadable.
     *
     * @param layer
     * @return
     */
    boolean isLayerThreadable(Layer layer);

    /**
     * Enable or disable the layer memory optimizer.
     */
    void enableMemoryOptimizer(Layer layer, boolean state);

    /**
     * Return the frame for the given layer and frame number.
     *
     * @param layer
     * @param number
     * @return
     */
    Frame findFrame(Layer layer, int number);

    /**
     *
     * @param job
     * @return
     */
    FrameDetail findLongestFrame(Job job);

    /**
     *
     * @param job
     * @return
     */
    FrameDetail findShortestFrame(Job job);

    /**
     *
     * @param job
     * @return
     */
    FrameStateTotals getFrameStateTotals(Job job);

    /**
     *
     * @param job
     * @return
     */
    ExecutionSummary getExecutionSummary(Job job);

    /**
     *
     * @param job
     * @return
     */
    FrameDetail findHighestMemoryFrame(Job job);

    /**
     *
     * @param job
     * @return
     */
    FrameDetail findLowestMemoryFrame(Job job);

    /**
     * Return the frame state totals by layer.
     *
     * @param layer
     * @return
     */
    FrameStateTotals getFrameStateTotals(Layer layer);

    /**
     * Return the execution summary by layer.
     *
     * @param layer
     * @return
     */
    ExecutionSummary getExecutionSummary(Layer layer);

    /**
     * Update the checkpoint state for the given frame.
     *
     * @param frame
     * @param state
     */
    void updateCheckpointState(Frame frame, CheckpointState state);

    /**
     * Return a list of frames that failed to checkpoint within
     * the given checkpoint point.
     *
     * @param cutoffTimeMs
     * @return
     */
    List<Frame> getStaleCheckpoints(int cutoffTimeSec);

    /**
     * Return a list of registered layer outputs.
     *
     * @param layer
     * @return
     */
    List<String> getLayerOutputs(Layer layer);

    /**
     * Register layer output.
     *
     * @param layer
     * @return
     */
    void registerLayerOutput(Layer layer, String filespec);

    /**
     * Return thread stats for the given layer.
     *
     * @param layer
     * @return
     */
    List<ThreadStats> getThreadStats(Layer layer);

    /**
     * Update the max core value for the given layer.
     *
     * @param layer
     * @param coreUnits
     */
    void setLayerMaxCores(Layer layer, int coreUnits);

    /**
     * Update the min core value for the given layer.
     *
     * @param layer
     * @param coreUnits
     */
    void setLayerMinCores(Layer layer, int coreUnits);
}

