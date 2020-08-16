
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



package com.imageworks.spcue.dispatcher;

import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ProcInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.rqd.RunFrame;

/**
 * A class for common dispatcher methods.
 *
 * @category service
 */
public interface DispatchSupport {

    /**
     * Number of procs rebalanced
     */
    static final AtomicLong balanceSuccess = new AtomicLong(0);

    /**
     * Number of procs
     */
    static final AtomicLong balanceFailed = new AtomicLong(0);

    /**
     * Number of times the worst offender was killed
     */
    static final AtomicLong killedOffenderProcs = new AtomicLong(0);

    /**
     * Number of frames killed because the machine totally ran out of memory.
     * This may or may not be the worst offender.
     */
    static final AtomicLong killedOomProcs= new AtomicLong(0);

    /**
     * Long for counting how many procs have been dispatched
     */
    static final AtomicLong dispatchedProcs = new AtomicLong(0);

    /**
     * Long for counting how many cores have been booked
     */
    static final AtomicLong bookedCores = new AtomicLong(0);

    /**
     * Long for counting how many gpu have been booked
     */
    static final AtomicLong bookedGpu = new AtomicLong(0);

    /**
     * Long for counting how many procs have been booked
     */
    static final AtomicLong bookedProcs = new AtomicLong(0);

    /**
     * Long for counting unbooked procs.
     */
    static final AtomicLong unbookedProcs = new AtomicLong(0);

    /**
     * A proc is cleared when an error occurs
     */
    static final AtomicLong clearedProcs = new AtomicLong(0);

    /**
     * Long for counting dispatch errors
     */
    static final AtomicLong bookingErrors = new AtomicLong(0);

    /**
     * Long for counting dispatch retries
     */
    static final AtomicLong  bookingRetries = new AtomicLong(0);

    /**
     * Incremented when RQD and the Cue DB are out of sync.
     */
    static final AtomicLong accountingErrors = new AtomicLong(0);

    /**
     * Incremented when RQD and the Cue DB are out of sync.
     */
    static final AtomicLong fixedFrames = new AtomicLong(0);

    /**
     * Count number of picked up cores.
     */
    static final AtomicLong pickedUpCoresCount = new AtomicLong(0);

    /**
     * Count number of stranded cores.
     */
    static final AtomicLong strandedCoresCount = new AtomicLong(0);
    
    /**
     * Count number of picked up gpu.
     */
    static final AtomicLong pickedUpGpuCount = new AtomicLong(0);

    /**
     * Count number of stranded gpu.
     */
    static final AtomicLong strandedGpuCount = new AtomicLong(0);

    /**
     * Set the proc's frame assignment to null;
     *
     * @param proc
     * @return
     */
    boolean clearVirtualProcAssignement(ProcInterface proc);

    /**
     * Stops the specified frame and sets a new frame state
     * and exit status.
     *
     * @param frame
     * @param state
     * @param exitStatus
     */
    boolean stopFrame(FrameInterface frame, FrameState state, int exitStatus);

    /**
     * Updates the frame to the Running state.  This should
     * be done after RQD has accepted the frame.  Setting
     * the frame's state to running will result in a
     * new entry in the frame_history table for the
     * running frame.
     *
     * @param proc
     * @param frame
     */
    void startFrame(VirtualProc proc, DispatchFrame frame);

    /**
     * Updates a frame with completed stats.
     *
     * @param frame
     * @param state
     * @param exitStatus
     * @param maxrss
     * @return
     */
    boolean stopFrame(FrameInterface frame, FrameState state,
                      int exitStatus, long maxrss);

    /**
     * Reserve the resources in the specified proc for the
     * specified frame.  If the proc does not exist, its
     * inserted, otherwise its updated.
     *
     * When a proc is created, the subscription, host,
     * job, layer, folder, and shot proc counts get updated.
     * This may cause some contention.
     *
     * @param proc
     * @param frame
     */
    public void reserveProc(VirtualProc proc, DispatchFrame frame);

    /**
     * This method clears out a proc that was lost track of.
     * This can happen if the host fails and the proc fails
     * to report in, a network outage occurs, or something
     * of that nature.
     *
     * @param proc
     * @param reason
     * @param exitStatus
     */
    void lostProc(VirtualProc proc, String reason, int exitStatus);

    /**
     * Unbooks a proc with no message
     *
     * @param proc
     */
    void unbookProc(VirtualProc proc);

    /**
     * Unbooks a virtual proc.  Takes a reason which is
     * printed to the console.
     */
    void unbookProc(VirtualProc proc, String reason);

    /**
     * Returns the next N frames to be dispatched from the
     * specified job.
     *
     * @param job
     * @param proc
     * @param limit
     * @return
     */
    List<DispatchFrame> findNextDispatchFrames(JobInterface job,
            VirtualProc proc, int limit);

    /**
     *
     * Returns the next N frames to be dispatched from the
     * specified job.
     *
     * @param job
     * @param host
     * @param limit
     * @return
     */
    List<DispatchFrame> findNextDispatchFrames(JobInterface job, DispatchHost host,
                                               int limit);

    /**
     * Return the next N frames to be dispatched from the specified layer.
     *
     * @param layer
     * @param host
     * @param limit
     * @return
     */
    List<DispatchFrame> findNextDispatchFrames(LayerInterface layer, DispatchHost host,
                                               int limit);

    /**
     * Return the next N frames to be dispatched from the specified layer.
     *
     * @param layer
     * @param proc
     * @param limit
     * @return
     */
    List<DispatchFrame> findNextDispatchFrames(LayerInterface layer, VirtualProc proc,
                                               int limit);
    /**
     *
     * @param excludeJob
     * @param proc
     * @return
     */
    boolean findUnderProcedJob(JobInterface excludeJob, VirtualProc proc);

    /**
     * Return true if there are higher priority jobs to run.
     *
     * @param baseJob
     * @param proc
     * @return boolean
     */
    boolean higherPriorityJobExists(JobDetail baseJob, VirtualProc proc);

    /**
     * Run the frame on the specified proc.
     *
     * @param proc
     * @param frame
     * @throws DispatcherException              if an error occurs during dispatching
     */
    void runFrame(VirtualProc proc, DispatchFrame frame);

    /**
     * Return true if the specified show is over its burst
     * size of the given proc's allocation.
     *
     * @param proc
     * @return
     */
    boolean isShowOverBurst(VirtualProc proc);


    /**
     * Returns the job that can utilize the specified host.
     *
     * @param host
     * @return
     */
    Set<String> findDispatchJobsForAllShows(DispatchHost host, int numJobs);

    /**
     * Returns the highest priority job that can utilize
     * the specified host
     *
     * @param host
     * @return
     */
    Set<String> findDispatchJobs(DispatchHost host, int numJobs);

    /**
     * Returns the highest priority jobs that can utilize
     * the specified host in the specified group.
     *
     * @param host
     * @return  A set of unique job ids.
     */
    Set<String> findDispatchJobs(DispatchHost host, GroupInterface p);

    /**
     *
     * @param host
     * @return  A set of unique job ids.
     */
    Set<String> findLocalDispatchJobs(DispatchHost host);

    /**
     * Creates and returns and RQD RunFrame object.
     *
     * Once the RunFrame object is created string replacement is done
     * in the frame command to replace any tags in the command.
     *
     * Currently these tags are supported: [IFRAME] - integer frame (no padding)
     * [ZFRAME] - 4 padded frame [LAYER] - the layer name [JOB] - the job name
     * [IFRAME] - the full frame name
     * [JOB] - the job name
     * [LAYER] - the layer name
     *
     * @param proc
     * @param frame
     * @return RunFrame
     */
    RunFrame prepareRqdRunFrame(VirtualProc proc, DispatchFrame frame);



    /**
     * Checks to see if job passes basic tests for dispatchability.
     * Tests include if the proc is over its max, if it has pending
     * frames, and if its paused.
     *
     * @param job
     * @param local indicates a local dispatch or not
     * @return boolean
     */
    boolean isJobDispatchable(JobInterface job, boolean local);

    /**
     * returns true of the cue has jobs with pending frames
     * that are not paused or in a non bookable state.
     *
     * @return
     */
    boolean isCueBookable(FacilityInterface f);

    /**
     * Increases the amount of memory reserved for a running frame.
     * Returns true if the memory value actually increased.  If the value
     * is lower than current reserved memory it is ignored.
     *
     * @param proc
     * @param value
     */
    boolean increaseReservedMemory(ProcInterface proc, long value);

    /**
     * Attempts to balance the reserved memory on a proc by
     * taking away reserved memory from frames that are well under
     * their reservation.
     *
     * @param proc
     * @param value
     */
    boolean balanceReservedMemory(ProcInterface proc, long value);

    /**
     * Update the jobs usage counters.
     *
     * @param frame
     * @param exitStatus
     */
    void updateUsageCounters(FrameInterface frame, int exitStatus);

    /**
     * Sets a frame to running if there is a proc with the frame.
     *
     * @param frame
     */
    void fixFrame(DispatchFrame frame);

    /**
     * Sets the frame state to waiting for a frame with
     * no running proc.
     *
     * @param frame
     */
    void clearFrame(DispatchFrame frame);

    /**
     * Update memory usage data for the given frame.
     *
     * @param frame
     * @param rss
     * @param maxRss
     */
    void updateFrameMemoryUsage(FrameInterface frame, long rss, long maxRss);

    /**
     * Update memory usage data for a given frame's proc record.  The
     * frame is used to update the proc so the update fails if the proc
     * has been rebooked onto a new frame.
     *
     * @param frame
     * @param rss
     * @param maxRss
     * @param vsize
     * @param maxVsize
     */
    void updateProcMemoryUsage(FrameInterface frame, long rss, long maxRss, long vsize,
                               long maxVsize);

    /**
     * Return true if adding the given core units would put the show
     * over its burst value.
     *
     * @param show
     * @param alloc
     * @param coreUnits
     * @return
     */
    boolean isShowOverBurst(ShowInterface show, AllocationInterface alloc, int coreUnits);

    /**
     * Return true if the job can take new procs.
     *
     * @param job
     * @return
     */
    boolean isJobBookable(JobInterface job);

    /**
     * Return true if the job can take the given number of new core units.
     *
     * @param job
     * @return
     */
    boolean isJobBookable(JobInterface job, int coreUnits, int gpu);

    /**
     * Return true if the specified show is at or over its
     * burst value for the given allocation.
     *
     * @param show
     * @param alloc
     * @return
     */
    boolean isShowAtOrOverBurst(ShowInterface show, AllocationInterface alloc);

    /**
     * Return true if the specified show is over its
     * guaranteed subscription size.
     *
     * @param proc
     * @return
     */
    boolean isShowOverSize(VirtualProc proc);

    /**
     * Pickup any cores that were stranded on the given host.
     *
     * @param host
     */
    void pickupStrandedCores(DispatchHost host);

    /**
     * Return true if the host has stranded cores.
     *
     * @param host
     * @return
     */
    boolean hasStrandedCores(HostInterface host);

    /**
     * Add stranded cores for the given host. Stranded
     * cores will automatically be added to the next frame dispatched
     * from the host to make up for cores stranded with no memory.
     *
     * @param host
     * @param cores
     */
    void strandCores(DispatchHost host, int cores);

    /**
     * Lowers the perceived idle cores on a machine if
     * the load is over certain threshold.
     *
     * @param host
     * @param load
     */
    void determineIdleCores(DispatchHost host, int load);

    /**
     * Pickup any gpu that were stranded on the given host.
     *
     * @param host
     */
    void pickupStrandedGpu(DispatchHost host);

    /**
     * Return true if the host has stranded gpu.
     *
     * @param host
     * @return
     */
    boolean hasStrandedGpu(HostInterface host);

    /**
     * Add stranded gpu for the given host. Stranded
     * gpu will automatically be added to the next frame dispatched
     * from the host to make up for gpu stranded with no memory.
     *
     * @param host
     * @param gpu
     */
    void strandGpu(DispatchHost host, int gpu);

    /**
     * Lowers the perceived idle gpu on a machine if
     * the load is over certain threshold.
     *
     * @param host
     * @param load
     */
    void determineIdleGpu(DispatchHost host, int load);

    /**
     * Return a set of job IDs that can take the given host.
     *
     * @param host
     * @param show
     * @param numJobs
     * @return
     */
    Set<String> findDispatchJobs(DispatchHost host, ShowInterface show, int numJobs);

    /**
     * Return true of the job has pending frames.
     *
     * @param job
     * @return
     */
    boolean hasPendingFrames(JobInterface job);

    /**
     * Return true if the layer has pending frames.
     *
     * @param layer
     * @return
     */
    boolean hasPendingFrames(LayerInterface layer);

}

