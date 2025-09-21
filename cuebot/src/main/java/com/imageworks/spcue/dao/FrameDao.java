
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

import java.util.List;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.FrameStateDisplayOverride;
import com.imageworks.spcue.grpc.job.FrameStateDisplayOverrideSeq;
import com.imageworks.spcue.util.FrameSet;

public interface FrameDao {

    /**
     * finds the frame in the job that used the lowest amount of memory
     *
     * @param job
     * @return
     */
    public FrameDetail findLowestMemoryFrame(JobInterface job);

    /**
     * finds the frame in the job that used the highest amount of memory,
     *
     * @param job
     * @return
     */
    public FrameDetail findHighestMemoryFrame(JobInterface job);

    /**
     * Returns the data for the shortest succeeded frame.
     *
     * @param job
     * @return
     */
    public FrameDetail findShortestFrame(JobInterface job);

    /**
     * Returns the data for the longest succeeded frame.
     *
     * @param job
     * @return
     */
    public FrameDetail findLongestFrame(JobInterface job);

    /**
     * Checks to see how many retries a frame has. If that number is greater than or equal to the
     * jobs max retries, the frame is marked as dead.
     *
     * @param frame
     */
    void checkRetries(FrameInterface frame);

    /**
     * Batch inserts a frameSet of frames.
     *
     * @param frame
     */
    void insertFrames(LayerDetail layer, List<Integer> frames);

    /**
     * Retrieve a FrameDetail from something that implements Frame
     *
     * @param frame
     * @return FrameDetail
     */
    FrameDetail getFrameDetail(FrameInterface frame);

    /**
     * Retrieve a FrameDetail from its unique ID.
     *
     * @param id
     * @return FrameDetail
     */
    FrameDetail getFrameDetail(String id);

    /**
     *
     * @param job
     * @param name
     * @return
     */
    FrameDetail findFrameDetail(JobInterface job, String name);

    /**
     * Returns a minimal Frame from its ID
     *
     * @param id
     * @return Frame
     */
    FrameInterface getFrame(String id);

    /**
     * Finds a minimal frame from its job and frame name
     *
     * @param job
     * @param name
     * @return Frame
     */
    FrameInterface findFrame(JobInterface job, String name);

    /**
     * Finds a minimal frame from its layer and number.
     *
     * @param job
     * @param name
     * @return Frame
     */
    FrameInterface findFrame(LayerInterface layer, int number);

    /**
     * Find a list of minimal frames from a job and FrameLookupRequest.
     *
     * @param job
     * @param r
     * @return List<Frame>
     */
    List<FrameInterface> findFrames(FrameSearchInterface r);

    /**
     * Find a list of FrameDetail objects from a job and FrameLookupRequest.
     *
     * @param job
     * @param r
     * @return List<FrameDetail>
     */
    List<FrameDetail> findFrameDetails(FrameSearchInterface r);

    /**
     * Updates the specified frame's state.
     *
     * @param frame
     * @param state
     */
    boolean updateFrameState(FrameInterface frame, FrameState state);

    /**
     * Updates a frame to indicate its now running.
     *
     * @param proc
     * @param frame
     * @return
     */
    void updateFrameStarted(VirtualProc proc, FrameInterface frame);

    /**
     * Updates a frame to the stopped state. The frame MUST be in the Running state to be stopped.
     *
     * @param proc
     * @param frame
     * @param report
     */
    boolean updateFrameStopped(FrameInterface frame, FrameState state, int exitStatus);

    /**
     * Updates a frame to the stopped state. The frame MUST be in the Running state to be stopped.
     *
     * @param frame
     * @param state
     * @param exitStatus
     * @param maxRss
     * @return
     */
    boolean updateFrameStopped(FrameInterface frame, FrameState state, int exitStatus, long maxRss);

    /**
     * Sets a frame to an unreserved waiting state.
     *
     * @param frame
     * @return
     */
    boolean updateFrameCleared(FrameInterface frame);

    /**
     * Sets a frame exitStatus to EXIT_STATUS_MEMORY_FAILURE
     *
     * @param frame
     * @return whether the frame has been updated
     */
    boolean updateFrameMemoryError(FrameInterface frame);

    /**
     * Sets a frame to an unreserved waiting state.
     *
     * @param frame
     * @return
     */
    boolean updateFrameHostDown(FrameInterface frame);

    /**
     * Returns a DispatchFrame object from the frame's uinique ID.
     *
     * @param uuid
     * @return DispatchFrame
     */
    DispatchFrame getDispatchFrame(String uuid);

    /**
     * Set the specified frame to the Waiting state and its depend count to 0.
     *
     * @param frame
     */
    void markFrameAsWaiting(FrameInterface frame);

    /**
     * If the specified frame has active dependencies, reset the dependency count and set the frame
     * state to Depend
     *
     * @param frame
     */
    void markFrameAsDepend(FrameInterface frame);

    /**
     * Reverses the specified frame range. The revese layer implementation is is more intensive than
     * other reorder operations because we look up the dispatch order for each frame and then switch
     * them.
     *
     * @param layer
     * @param frameSet
     */
    public void reorderLayerReverse(LayerInterface layer, FrameSet frameSet);

    /**
     *
     * Reorders specified frames to the end of the dispatch order. This works by finding the frame
     * with the highest dispatch value, and updating the specified frames with higher values. The
     * rest of the frames in the layer are not touched.
     *
     * @param layer
     * @param frameSet
     */
    public void reorderFramesLast(LayerInterface layer, FrameSet frameSet);

    /**
     * Reorders specified frames to the top of the dispatch order. This works by finding the frame
     * with the lowest dispatch order and updating targeted frames with even lower dispatcher
     * orders, negative numbers are allowed.
     *
     * @param layer
     * @param frameSet
     */
    public void reorderFramesFirst(LayerInterface layer, FrameSet frameSet);

    /**
     * This would reorder frames so that it would render the specified sequence on a staggered frame
     * range. The frame set must be a staggered range.
     *
     * @param layer
     * @param frameSet
     */
    public void staggerLayer(LayerInterface layer, String range, int stagger);

    /**
     * Returns a list of Running frames that have not had a proc assigned to them in over 5 min.
     * This can happen when an operation aborts due to a deadlock.
     *
     * @return
     */
    List<FrameInterface> getOrphanedFrames();

    /**
     * Return a list of all frames that have positive dependency counts for the specified
     * dependency.
     *
     * @param depend
     * @return
     */
    List<FrameInterface> getDependentFrames(LightweightDependency depend);

    /**
     * Returns true if the frame is succeeded.
     *
     * @param f
     * @return
     */
    public boolean isFrameComplete(FrameInterface f);

    /**
     * Attempts to fix the case where a proc is assigned to a frame but the frame is in the waiting
     * state.
     *
     * @param proc
     * @param frame
     * @return
     */
    boolean updateFrameFixed(VirtualProc proc, FrameInterface frame);

    /**
     * Return a ResourceUsage object which repesents the amount of clock and core time the frame has
     * used up until this point.
     *
     * @param f
     * @return
     */
    ResourceUsage getResourceUsage(FrameInterface f);

    /**
     * Update memory usage values and LLU time for the given frame. The frame must be in the Running
     * state. If the frame is locked by another thread, the process is aborted because we'll most
     * likely get a new update one minute later.
     *
     * @param f
     * @param maxRss
     * @param rss
     * @param lluTime
     * @throws FrameReservationException if the frame is locked by another thread.
     */
    void updateFrameMemoryUsageAndLluTime(FrameInterface f, long maxRss, long rss, long lluTime);

    /**
     * Attempt to put a exclusive row lock on the given frame. The frame must be in the specified
     * state.
     *
     * @param frame
     * @param state
     * @throws FrameReservationException if the frame changes state before the lock can be applied.
     */
    void lockFrameForUpdate(FrameInterface frame, FrameState state);

    /**
     * Return true if the specified frame is an orphan.
     *
     * @param frame
     * @return
     */
    boolean isOrphan(FrameInterface frame);

    /**
     * Update a frame's checkpoint state status.
     *
     * @param frame
     * @param state
     * @return
     */
    boolean updateFrameCheckpointState(FrameInterface frame, CheckpointState state);

    /**
     * Return a list of checkpoints that have failed to report back in within a certain cutoff time.
     *
     * @param cutoffTime
     * @return
     */
    List<FrameInterface> getStaleCheckpoints(int cutoffTimeMs);

    /**
     * Create a frame state display override.
     *
     * @param frameId String
     * @param override FrameStateDisplayOverride
     */
    void setFrameStateDisplayOverride(String frameId, FrameStateDisplayOverride override);

    /**
     * Get the frame overrides for a specific frame
     *
     * @param frameId
     * @return List<FrameStateDisplayOverride>
     */
    FrameStateDisplayOverrideSeq getFrameStateDisplayOverrides(String frameId);

    /**
     * Update a frame override with new text/color
     *
     * @param frameId
     * @param override FrameStateDisplayOverride
     */
    void updateFrameStateDisplayOverride(String frameId, FrameStateDisplayOverride override);
}
