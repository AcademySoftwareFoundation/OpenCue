
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

import java.sql.Timestamp;
import java.util.List;

import com.imageworks.spcue.Allocation;
import com.imageworks.spcue.AllocationDetail;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.Frame;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.HostDetail;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Proc;
import com.imageworks.spcue.Show;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.CueGrpc.HardwareState;
import com.imageworks.spcue.CueGrpc.HostReport;
import com.imageworks.spcue.CueGrpc.RenderHost;
import com.imageworks.spcue.CueIce.LockState;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dao.criteria.ProcSearch;

public interface HostManager {

    void rebootWhenIdle(Host host);
    void rebootNow(Host host);

    /**
     * Lock/unlock the specified host.
     *
     * @param host
     * @param state
     * @param source
     */
    void setHostLock(Host host, LockState state, Source source);

    /**
     * Updates the state of a host.
     *
     * @param host
     * @param state
     * @param source
     */
    void setHostState(Host host, HardwareState state);

    /**
     * Return true if the host is swapping hard enough
     * that killing frames will save the entire machine.
     *
     * @param host
     * @return
     */
    boolean isSwapping(Host host);

    DispatchHost createHost(HostReport report);
    DispatchHost createHost(RenderHost host);

    /**
     * Create a host and move it into the specified allocation.
     *
     * @param rhost
     * @param alloc
     * @return
     */
    DispatchHost createHost(RenderHost rhost, AllocationDetail alloc);


    Host getHost(String id);
    Host findHost(String name);

    DispatchHost getDispatchHost(String id);
    DispatchHost findDispatchHost(String name);

    HostDetail getHostDetail(Host host);
    HostDetail getHostDetail(String id);
    HostDetail findHostDetail(String name);

    /**
     * Returns true of the LockState is not Open.
     *
     * @param host
     * @return
     */
    boolean isLocked(Host host);

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
     * @param totalGpu
     * @param freeGpu
     * @param load
     * @param bootTime
     * @param os
     */
    void setHostStatistics(Host host,
            long totalMemory, long freeMemory,
            long totalSwap, long freeSwap,
            long totalMcp, long freeMcp,
            long totalGpu, long freeGpu,
            int load, Timestamp bootTime, String os);


    void deleteHost(Host host);

    Allocation getDefaultAllocationDetail();

    void setAllocation(Host host, Allocation alloc);

    void addTags(Host host, String[] tags);
    void removeTags(Host host, String[] tags);
    void renameTag(Host host, String oldTag, String newTag);

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
    List<VirtualProc> findVirtualProcs(ProcSearch r);

    List<VirtualProc> findVirtualProcs(FrameSearch r);
    VirtualProc findVirtualProc(Frame frame);
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
    List<VirtualProc> findBookedVirtualProcs(ProcSearch r);

    void unbookVirtualProcs(List<VirtualProc> procs);
    void unbookProc(Proc proc);

    /**
     * Returns the proc who is most deliquent on memory allocation
     * @param h
     * @return
     */
    VirtualProc getWorstMemoryOffender(Host h);

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
    boolean isHostUp(Host host);

    /**
     * Return true if the proc is an orphan.  An orphan has not
     * had a ping in 5 minutes.
     *
     * @param proc
     * @return
     */
    boolean isOprhan(Proc proc);

    /**
     * Return the number of stranded cores on the host.
     */
    int getStrandedCoreUnits(Host h);

    /**
     * Return true of the host prefers a particular show.
     *
     * @param host
     * @return
     */
    boolean isPreferShow(Host host);

    /**
     * Return a host's preferred show.
     *
     * @param host
     * @return
     */
    Show getPreferredShow(Host host);

    /**
     * Return all running procs for the given host.
     *
     * @param host
     * @return
     */
    List<VirtualProc> findVirtualProcs(Host host);

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

