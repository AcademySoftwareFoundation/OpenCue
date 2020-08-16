
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

import java.sql.Timestamp;
import java.util.List;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.ProcInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.report.HostReport;
import com.imageworks.spcue.grpc.report.RenderHost;

public interface HostManager {

    void rebootWhenIdle(HostInterface host);
    void rebootNow(HostInterface host);

    /**
     * Lock/unlock the specified host.
     *
     * @param host
     * @param state
     * @param source
     */
    void setHostLock(HostInterface host, LockState state, Source source);

    /**
     * Updates the state of a host.
     *
     * @param host HostInterface
     * @param state HardwareState
     */
    void setHostState(HostInterface host, HardwareState state);

    /**
     * Return true if the host is swapping hard enough
     * that killing frames will save the entire machine.
     *
     * @param host
     * @return
     */
    boolean isSwapping(HostInterface host);

    DispatchHost createHost(HostReport report);
    DispatchHost createHost(RenderHost host);

    /**
     * Create a host and move it into the specified allocation.
     *
     * @param rhost
     * @param alloc
     * @return
     */
    DispatchHost createHost(RenderHost rhost, AllocationEntity alloc);


    HostInterface getHost(String id);
    HostInterface findHost(String name);

    DispatchHost getDispatchHost(String id);
    DispatchHost findDispatchHost(String name);

    HostEntity getHostDetail(HostInterface host);
    HostEntity getHostDetail(String id);
    HostEntity findHostDetail(String name);

    /**
     * Returns true of the LockState is not Open.
     *
     * @param host
     * @return
     */
    boolean isLocked(HostInterface host);

    /**
     * Set all host statistics.
     *
     * @param host
     * @param totalMemory
     * @param freeMemory
     * @param totalSwap
     * @param freeSwap
     * @param totalMcp
     * @param freeMcp
     * @param totalGpuMemory
     * @param freeGpuMemory
     * @param load
     * @param bootTime
     * @param os
     */
    void setHostStatistics(HostInterface host,
            long totalMemory, long freeMemory,
            long totalSwap, long freeSwap,
            long totalMcp, long freeMcp,
            long totalGpuMemory, long freeGpuMemory,
            int load, Timestamp bootTime, String os);


    void deleteHost(HostInterface host);

    AllocationInterface getDefaultAllocationDetail();

    void setAllocation(HostInterface host, AllocationInterface alloc);

    void addTags(HostInterface host, String[] tags);
    void removeTags(HostInterface host, String[] tags);
    void renameTag(HostInterface host, String oldTag, String newTag);

    /**
     * Verify that the given proc and frame IDs are assigned
     * to each other in the database.
     *
     * @param procId
     * @param frameId
     * @return
     */
    boolean verifyRunningProc(String procId, String frameId);

    /**
     * Returns a list of VirtualProcs that match
     * the specified criteria.
     *
     * @param r
     * @return a list of VirtualProcs that match the criteria
     */
    List<VirtualProc> findVirtualProcs(ProcSearchInterface r);

    List<VirtualProc> findVirtualProcs(FrameSearchInterface r);
    VirtualProc findVirtualProc(FrameInterface frame);
    List<VirtualProc> findVirtualProcs(HardwareState state);

    /**
     * Returns a list of booked procs.  When a proc is "booked", that means
     * it plans on staying on the same job after it completes the current
     * frame.  If a proc is unbooked, it aways tries to find work to do
     * on another job.
     *
     * @param r
     * @return
     */
    List<VirtualProc> findBookedVirtualProcs(ProcSearchInterface r);

    void unbookVirtualProcs(List<VirtualProc> procs);
    void unbookProc(ProcInterface proc);

    /**
     * Returns the proc who is most deliquent on memory allocation
     * @param h
     * @return
     */
    VirtualProc getWorstMemoryOffender(HostInterface h);

    /**
     * Return the Virtual proc with the specified unique ID.
     *
     * @param id
     * @return
     */
    VirtualProc getVirtualProc(String id);

    /**
     * Return true if the given host is in the Up state.  Other
     * states are Down, Rebooting, RebootWhenIdle, etc.  Only hosts
     * in the Up state should be booked or dispatched.
     *
     * @param host
     * @return
     */
    boolean isHostUp(HostInterface host);

    /**
     * Return true if the proc is an orphan.  An orphan has not
     * had a ping in 5 minutes.
     *
     * @param proc
     * @return
     */
    boolean isOprhan(ProcInterface proc);

    /**
     * Return the number of stranded cores on the host.
     */
    int getStrandedCoreUnits(HostInterface h);
    
    /**
     * Return the number of stranded cores on the host.
     */
    int getStrandedGpu(HostInterface h);

    /**
     * Return true of the host prefers a particular show.
     *
     * @param host
     * @return
     */
    boolean isPreferShow(HostInterface host);

    /**
     * Return a host's preferred show.
     *
     * @param host
     * @return
     */
    ShowInterface getPreferredShow(HostInterface host);

    /**
     * Return all running procs for the given host.
     *
     * @param host
     * @return
     */
    List<VirtualProc> findVirtualProcs(HostInterface host);

    /**
     * Return all running procs for the given LocalHostAssignment.
     *
     * @param l
     * @return
     */
    List<VirtualProc> findVirtualProcs(LocalHostAssignment l);

    /**
     * Set the hosts available idle cores and memory.
     *
     * @param host
     * @param report
     */
    void setHostResources(DispatchHost host, HostReport report);
}

