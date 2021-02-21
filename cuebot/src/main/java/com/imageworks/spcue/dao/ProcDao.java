
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

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.ProcInterface;
import com.imageworks.spcue.Redirect;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.grpc.host.HardwareState;

/**
 * @category DAO
 */
public interface ProcDao {

    /**
     * Returns the amount of reserved memory a proc has
     *
     * @param proc
     * @return
     */

    long getReservedMemory(ProcInterface proc);

    /**
     * Returns the amount of reserved gpu memory a proc has
     *
     * @param proc
     * @return
     */

    long getReservedGpuMemory(ProcInterface proc);

    /**
     * Return the proc that has exceeded its reserved memory by the largest factor.
     *
     * @param host
     * @return
     */
    VirtualProc getWorstMemoryOffender(HostInterface host);

    /**
     * Removes a little bit of reserved memory from every other running frame
     * in order to give some to the target proc.
     *
     * @param targetProc
     * @param targetMem
     * @return
     */
    boolean balanceUnderUtilizedProcs(ProcInterface targetProc, long targetMem);

    /**
     * Increase a proc's reserved memory.
     *
     * @param id
     * @param value
     * @return
     */
    boolean increaseReservedMemory(ProcInterface p, long value);

    /**
     * Set a proc's reserved memory.
     *
     * @param id
     * @param value
     * @return
     */
    void updateReservedMemory(ProcInterface p, long value);

    /**
     * verifies the mapping bewtween a proc id and a frame id
     *
     * @param procid
     * @param frameid
     * @return
     */
    boolean verifyRunningProc(String procid, String frameid);

    /**
     * Creates a new virtual proc
     *
     * @param proc
     */
    void insertVirtualProc(VirtualProc proc);

    /**
     * Deletes an existing virtual proc
     *
     * @param proc
     */
    boolean deleteVirtualProc(VirtualProc proc);

    /**
     * Clears a virtual proc assignement.  This keeps the proc
     * around but sets pk_frame to null.  This would normally
     * happen after a frame completes and before the proc is
     * dispatched again.
     *
     * @param proc
     */
    boolean clearVirtualProcAssignment(ProcInterface proc);

    /**
     * Clear a proc assignment by frame id.  Return true
     * if an assignment was cleared.
     *
     * @param frame
     * @return
     */
    boolean clearVirtualProcAssignment(FrameInterface frame);

    /**
     * Updates an existing proc's assignment
     *
     * @param proc
     */
    void updateVirtualProcAssignment(VirtualProc proc);

    /**
     * Update a procs memory usage based on the given
     * frame it should be running.
     *
     * @param proc
     * @param usedKb
     * @param maxKb
     */
    void updateProcMemoryUsage(FrameInterface f, long rss, long maxRss,
                               long vsize, long maxVsize);

    /**
     * get aq virual proc from its unique id
     *
     * @param id
     * @return
     */
    VirtualProc getVirtualProc(String id);

    /**
     * get a virtual proc from the frame its assigned to
     *
     * @param frame
     * @return
     */
    VirtualProc findVirtualProc(FrameInterface frame);

    /**
     * gets a list of virtual procs from a FrameLookupRequest
     *
     * @param job
     * @param req
     * @return
     */
    List<VirtualProc> findVirtualProcs(FrameSearchInterface s);

    /**
     * get the list of procs from the host.
     *
     * @param host
     * @return
     */
    List<VirtualProc> findVirtualProcs(HostInterface host);

    /**
     * find all procs booked on a specified layer
     *
     * @param layer
     * @return
     */
    List<VirtualProc> findVirtualProcs(LayerInterface layer);

    /**
     * find all procs  booked on specified job
     *
     * @param job
     * @return
     */
    List<VirtualProc> findVirtualProcs(JobInterface job);

    /**
     *
     * @return
     */
    List<VirtualProc> findOrphanedVirtualProcs();

    /**
     *
     * @return
     */
    List<VirtualProc> findOrphanedVirtualProcs(int limit);

    /**
     * Returns procs with a host in a particular hardware state.
     *
     * @param state
     * @return
     */
    public List<VirtualProc> findVirtualProcs(HardwareState state);

    /**
     * Returns a list if procs using a ProcSearchInterface object.
     *
     * @param r - A ProcSearchInterface object
     * @return a list of virtual procs
     */
    List<VirtualProc> findVirtualProcs(ProcSearchInterface r);

    /**
     * Unbooks a list of virtual procs using a batch query
     *
     * @param procs
     * @return
     */
    void unbookVirtualProcs(List<VirtualProc> procs);

    /**
     * Unbooks a single virtual proc
     *
     * @param procs
     * @return
     */
    void unbookProc(ProcInterface proc);

    /**
     * Used to set the unbook flag on a proc to true or false.
     *
     * @param proc
     * @param unbooked
     */
    public boolean setUnbookState(ProcInterface proc, boolean unbooked);

    /**
     * Updates the proc record with the name of its redirect target.
     *
     * @param p
     * @param r
     */
    public boolean setRedirectTarget(ProcInterface p, Redirect r);

    /**
     * Returns the unique id of the proc's current show
     *
     * @param p
     * @return
     */
    public String getCurrentShowId(ProcInterface p);

    /**
     * Returns the unique id of the procs current job
     *
     * @param p
     * @return
     */
    public String getCurrentJobId(ProcInterface p);

    /**
     * Returns the unique id of the procs current layer
     *
     * @param p
     * @return
     */
    public String getCurrentLayerId(ProcInterface p);

    /**
     * Returns the unique id of the procs current frame
     *
     * @param p
     * @return
     */
    public String getCurrentFrameId(ProcInterface p);

    /**
     * Returns an array of booked virutal procs.
     *
     * @param r
     * @return
     */
    List<VirtualProc> findBookedVirtualProcs(ProcSearchInterface r);

    /**
     * Return true if the proc is an orphan.
     *
     * @param proc
     * @return
     */
    boolean isOrphan(ProcInterface proc);

    /**
     * Return a list of all procs that are booked as part
     * of the given local job assignment.
     *
     * @param l
     * @return
     */
    List<VirtualProc> findVirtualProcs(LocalHostAssignment l);
}

