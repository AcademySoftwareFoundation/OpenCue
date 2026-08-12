
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
     * Removes a little bit of reserved memory from every other running frame in order to give some
     * to the target proc.
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
     * Batch variant of {@link #insertVirtualProc}: inserts many procs in one round-trip. Does NOT
     * touch host idle resources (those are reserved up-front by {@link #reserveHostResourcesBatch})
     * nor the subscription/layer/job/folder/point counters, the Scheduler batches those separately.
     * Each proc is assigned a fresh id. Intended for the Scheduler's batch commit path, where the
     * frames were already won via a version-guarded update so duplicate inserts cannot occur.
     *
     * @param procs the procs to insert (non-local)
     */
    void batchInsertVirtualProcs(java.util.List<VirtualProc> procs);

    /**
     * Atomically reserve each host's aggregated idle-resource share for this tick's procs, using a
     * guarded decrement that only books a host that currently has room for its whole share. Returns
     * the set of host ids that had room (were decremented); procs on any other host must NOT be
     * booked. This is what keeps the Scheduler from sending a proc to a host that cannot hold it:
     * an unguarded decrement would drive idle negative, trip the verify_host_resources trigger, and
     * abort the whole batched tick.
     *
     * @param procs the procs whose hosts to reserve (non-local)
     * @return host ids that were successfully reserved
     */
    java.util.Set<String> reserveHostResourcesBatch(java.util.List<VirtualProc> procs);

    /**
     * Return host idle resources reserved by {@link #reserveHostResourcesBatch} for procs that
     * ended up not being booked (e.g. their frame lost the version race). A pure re-increment, so
     * it can never drive idle negative.
     *
     * @param procs the procs whose host reservation to release
     */
    void refundHostResourcesBatch(java.util.List<VirtualProc> procs);

    /**
     * Delete any proc rows sitting on the given frames and return them with their host and reserved
     * resources, so the caller can refund the hosts. Used by the planner's batch commit right after
     * it wins a frame's WAITING to RUNNING transition: a proc still attached to such a frame is
     * provably stale (a crash or a failed completion left it behind), and inserting the new proc
     * would otherwise hit c_proc_uk and wedge the whole batch.
     *
     * @param frameIds
     * @return the deleted stale procs (empty in the normal case)
     */
    java.util.List<VirtualProc> deleteStaleProcsByFrames(java.util.List<String> frameIds);

    /**
     * Delete every proc whose frame is no longer RUNNING and that has been in that state for at
     * least the given age, returning them for host-resource refund. The janitor sweep: an orphaned
     * proc whose frame never gets planned again (job finished or killed) would otherwise hold its
     * host's cores forever, invisible to the commit-time eviction.
     *
     * @param olderThanSeconds minimum age, so an in-flight booking is never swept
     * @return the deleted orphans (empty in the normal case)
     */
    java.util.List<VirtualProc> deleteOrphanedProcs(int olderThanSeconds);

    /**
     * Batch variant of {@link #clearVirtualProcAssignment(FrameInterface)}: clears the proc
     * assignment of many frames in one round-trip. Used by the scheduler's batched completion flush
     * inside its single stop transaction.
     *
     * @param frames the frames whose procs should be unassigned
     */
    void batchClearVirtualProcAssignments(java.util.List<? extends FrameInterface> frames);

    /**
     * Batched unbook for the scheduler's completion flush: deletes many procs in one round-trip and
     * applies every release-side resource credit coalesced (host idle refunds summed per host, and
     * the subscription/layer_resource/job_resource/folder_resource/point decrements summed per
     * key) instead of ~7 single-row updates per proc. Semantically a batched
     * {@code deleteVirtualProc}: reserved amounts are taken from the DELETE's RETURNING clause (the
     * live database values, immune to the stale-reservation race), a proc already deleted by
     * someone else is skipped entirely, and scheduler-managed shows keep their NOTIFY-based
     * accounting instead of the table decrements. Callers must not pass local-dispatch procs (their
     * release touches different tables and stays on the per-proc path).
     *
     * @param procs the procs to delete; non-local only
     * @return the subset actually deleted, with reserved fields refreshed from the database
     */
    java.util.List<VirtualProc> batchDeleteVirtualProcs(java.util.List<VirtualProc> procs);

    /**
     * Pre-acquire (SELECT ... FOR UPDATE, sorted by pk_proc) the proc rows of the given procs
     * inside the current transaction. The scheduler's completion flush calls this before anything
     * else: every single-proc writer (the OOM memory bump's UPDATE proc, whose trigger then locks
     * the host row) acquires "proc, then host", so the flush must lock its proc rows BEFORE its
     * host rows too or the two directions deadlock; observed live as the memory bump holding a
     * proc row and waiting on a host the flush had pre-locked, while the flush's batched DELETE
     * waited on that proc row. Procs already deleted simply don't match and are skipped.
     *
     * @param procs the procs whose proc rows to lock
     */
    void lockProcsForBatch(java.util.List<VirtualProc> procs);

    /**
     * Pre-acquire (SELECT ... FOR UPDATE, sorted by pk_host) the host rows of the given procs
     * inside the current transaction. The scheduler's completion flush calls this after
     * {@link #lockProcsForBatch} and before it touches any frame or stat-counter row, so its lock
     * order is "procs, then hosts, then stats". Hosts-then-stats is the same global order the
     * booking commit uses (reserveHostResourcesBatch, then the frame-start stat pre-locks), which
     * makes the batched transactions incapable of deadlocking each other or the single-row
     * writers.
     *
     * @param procs the procs whose host rows to lock
     */
    void lockHostsForBatch(java.util.List<VirtualProc> procs);

    /**
     * Deletes an existing virtual proc
     *
     * @param proc
     */
    boolean deleteVirtualProc(VirtualProc proc);

    /**
     * Clears a virtual proc assignement. This keeps the proc around but sets pk_frame to null. This
     * would normally happen after a frame completes and before the proc is dispatched again.
     *
     * @param proc
     */
    boolean clearVirtualProcAssignment(ProcInterface proc);

    /**
     * Clear a proc assignment by frame id. Return true if an assignment was cleared.
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
     * Update a procs memory usage based on the given frame it should be running.
     *
     * @param proc
     * @param usedKb
     * @param maxKb
     */
    void updateProcMemoryUsage(FrameInterface f, long rss, long maxRss, long pss, long maxPss,
            long vsize, long maxVsize, long usedGpuMemory, long maxUsedGpuMemory,
            long usedSwapMemory, byte[] children);

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
     * find all procs booked on specified job
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
     * Return a list of all procs that are booked as part of the given local job assignment.
     *
     * @param l
     * @return
     */
    List<VirtualProc> findVirtualProcs(LocalHostAssignment l);
}
