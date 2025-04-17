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

package com.imageworks.spcue.dispatcher;

import java.util.List;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.util.CueUtil;

public interface Dispatcher {

    // Maximum number of core points that can be assigned to a frame
    public static final int CORE_POINTS_RESERVED_MAX = 2400;

    // The default number of core points assigned to a frame, if no core
    // point value is specified
    public static final int CORE_POINTS_RESERVED_DEFAULT = 100;

    // The minimum amount of core points you can assign to a frame.
    public static final int CORE_POINTS_RESERVED_MIN = 10;

    // The minimum amount of gpu points you can assign to a frame.
    public static final int GPU_UNITS_RESERVED_DEFAULT = 0;
    public static final int GPU_UNITS_RESERVED_MIN = 0;

    // Amount of load per core a host can have before the perceived
    // number of idle cores is modified to reflect load conditions
    // on the host.
    public static final int CORE_LOAD_THRESHOLD = 5;

    // Amount of memory that has to be idle for the rest of the cores
    // on the machine to be considered stranded.
    public static final long MEM_STRANDED_THRESHHOLD = CueUtil.GB + CueUtil.MB512;

    // Determines the service default minimum memory per frame.
    public static final long MEM_SERVICE_RESERVED_DEFAULT = CueUtil.GB4;

    // Determines the service default minimum gpu per frame.
    public static final long MEM_SERVICE_GPU_RESERVED_DEFAULT = 0;

    // Return value for cleared frame
    public static final int EXIT_STATUS_FRAME_CLEARED = 299;

    /*
     * An orphan proc occurs when a proc is left with no frame assignment.
     */
    public static final int EXIT_STATUS_FRAME_ORPHAN = 301;

    /*
     * A failed kill occurs when a user tries to kill a frame and RQD throws an exception.
     */
    public static final int EXIT_STATUS_FAILED_KILL = 302;

    // Return value for cleared frame
    public static final int EXIT_STATUS_DOWN_HOST = 399;

    // Upgrade the memory on the layer by 1g and retry.
    public static final int EXIT_STATUS_MEMORY_FAILURE = 33;

    // Upgrade the memory on the layer by 1g and retry.
    public static final int DOCKER_EXIT_STATUS_MEMORY_FAILURE = 137;

    // max retry time
    public static final int FRAME_TIME_NO_RETRY = 3600 * 8;

    // The maximum amount of virtual memory a frame can be using
    // without being penalized for it.
    public static final long VIRTUAL_MEM_THRESHHOLD = CueUtil.GB2;

    // How long to keep track of a frame kill request
    public static final int FRAME_KILL_CACHE_EXPIRE_AFTER_WRITE_MINUTES = 3;

    // A higher number gets more deep booking but less spread on the cue.
    public static final int DEFAULT_MAX_FRAMES_PER_PASS = 4;

    // Disable RQD communication.
    public static boolean testMode = false;

    // The time in seconds it takes for a proc or frame to orphan.
    public static final int ORPHANED_SECONDS = 300;

    // The chance a frame will unbook itself to run a higher priority frame.
    // 0 will never unbook, > 100 will always unbook.
    public static final int UNBOOK_FREQUENCY = 101;

    // The default operating system assigned to host that don't report one.
    public static final String OS_DEFAULT = "rhel40";

    // The default minimum memory increase for when jobs fail due to not enough
    // memory
    public static final long MINIMUM_MEMORY_INCREASE = CueUtil.GB2;

    public static final double SOFT_MEMORY_MULTIPLIER = 1.6;
    public static final double HARD_MEMORY_MULTIPLIER = 2.0;

    /**
     * Dispatch a host to the facility.
     *
     * @param host
     * @return A list of procs that were dispatched.
     */
    List<VirtualProc> dispatchHostToAllShows(DispatchHost host);

    /**
     * Dispatch a host to the facility.
     *
     * @param host
     * @return A list of procs that were dispatched.
     */
    List<VirtualProc> dispatchHost(DispatchHost host);

    /**
     * Dispatch a host to the specified group and specify the maximum number of frames to dispatch
     * from the host.
     *
     * @param host
     * @param g
     * @param numFrames
     * @return
     */
    List<VirtualProc> dispatchHost(DispatchHost host, GroupInterface g);

    /**
     * Dispatch a host to the specified job.
     *
     * @param host
     * @param job
     * @return A list of procs that were dispatched.
     * @throws DispatcherException if an error occurs.
     */
    List<VirtualProc> dispatchHost(DispatchHost host, JobInterface job);

    /**
     * Dispatch a host to the specified job.
     *
     * @param host
     * @param job
     * @return A list of procs that were dispatched.
     * @throws DispatcherException if an error occurs.
     */
    List<VirtualProc> dispatchHost(DispatchHost host, LayerInterface layer);

    /**
     * Dispatch a host to the specified job.
     *
     * @param host
     * @param job
     * @return A list of procs that were dispatched.
     * @throws DispatcherException if an error occurs.
     */
    List<VirtualProc> dispatchHost(DispatchHost host, FrameInterface frame);

    /**
     * Dispatch a proc to the specified job.
     *
     * @param proc
     * @param job
     * @throws DispatcherException if an error occurs.
     */
    void dispatchProcToJob(VirtualProc proc, JobInterface job);

    /**
     * Return true if the dispatcher should not talk to RQD
     *
     * @return
     */
    boolean isTestMode();

    /**
     * Return true if the dispatcher should not talk to RQD
     *
     * @return
     */
    void setTestMode(boolean enabled);

    /**
     * Handles assigning a processor to a specified frame.
     *
     * @param frame
     * @param proc
     *
     * @throws FrameReservationException if the frame cannot be reserved.
     * @throws ResourceReservationFailureException if resources cannot be reserved.
     * @throws RqdClientException if communication with RQD fails.
     */
    void dispatch(DispatchFrame frame, VirtualProc proc);

    /**
     * Dispatch the given host to the specified show.
     *
     * @param host
     * @param show
     * @return
     */
    List<VirtualProc> dispatchHost(DispatchHost host, ShowInterface show);
}
