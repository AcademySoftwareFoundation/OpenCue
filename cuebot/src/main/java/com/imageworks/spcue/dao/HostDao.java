
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

import java.sql.Timestamp;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.HostTagType;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.grpc.report.HostReport;
import com.imageworks.spcue.grpc.report.RenderHost;


/**
 * HostDao contains all SQL queries pretaining to host records.
 */
public interface HostDao {

    /**
     * Attempt to obtain an exclusive lock on the host. If another thread alrady
     * has the host locked, a ResourceReservationFailureException is thrown.
     *
     * @param host HostInterface
     * @throws ResourceReservationFailureException when an exclusive lock cannot
     *         be made.
     */
    void lockForUpdate(HostInterface host);

    /**
     * returns true if the specified host id is locked
     *
     * @param host  HostInterface
     * @return  Boolean
     */
    boolean isHostLocked(HostInterface host);

    /**
     * deletes the passed host
     *
     * @param host  HostInterface object to delete
     */
    void deleteHost(HostInterface host);

    /**
     * updates a host with the passed hardware state
     *
     * @param host  HostInterface
     * @param state HardwareState
     */
    void updateHostState(HostInterface host, HardwareState state);

    /**
     * returns a full host detail
     *
     * @param host  HostInterface
     * @return HostDetail
     */
    HostEntity getHostDetail(HostInterface host);

    /**
     * returns full host detail
     *
     * @param id String
     * @return HostEntity
     */
    HostEntity getHostDetail(String id);

    /**
     * returns full host detail
     *
     * @param name String
     * @return HostEntity
     */
    HostEntity findHostDetail(String name);

    /**
     * Return a DispatchHost object from its unique host name
     *
     * @param fqdn String
     * @return DispatchHost
     */
    DispatchHost findDispatchHost(String fqdn);

    /**
     * Return a dispatch host object by id
     *
     * @param id String
     * @return DispatchHost
     */
    DispatchHost getDispatchHost(String id);

    /**
     * Returns a host object by name
     *
     * @param name String
     * @return HostInterface
     */
    HostInterface findHost(String name);

    /**
     * Returns a host object by ID.
     *
     * @param id String
     * @return HostInterface
     */
    HostInterface getHost(String id);

    /**
     * Return the host involved with the given LocalJobAssignment.
     *
     * @param l LocalHostAssignment
     * @return HostInterface
     */
    HostInterface getHost(LocalHostAssignment l);

    /**
     * Inserts a render host and its supporting procs into an allocation.
     *
     * @param report        RenderHost
     * @param a             AllocationInterface
     * @param useLongNames  boolean
     */
    void insertRenderHost(RenderHost report, AllocationInterface a, boolean useLongNames);

    /**
     * Checks to see if a render host exists by name and returns true if it
     * does, false if it doesn't.
     *
     * @param hostname String
     * @return boolean
     */
    boolean hostExists(String hostname);

    /**
     * Updates the host's lock state. Open, Locked, NimbyLocked. Records the
     * source of the lock.
     *
     * @param host   HostInterface
     * @param state  LockState
     * @param source Source
     */
    void updateHostLock(HostInterface host, LockState state, Source source);

    /**
     * Sets the reboot when idle boolean to true or false. If true the cue will
     * issue the reboot command to hosts that ping in idle then set the flag
     * back to false.
     *
     * @param host    HostInterface
     * @param enabled boolean
     */
    void updateHostRebootWhenIdle(HostInterface host, boolean enabled);

    /**
     * Updates a host's allocation
     *
     * @param host  HostInterface
     * @param alloc AllocationInterface
     */
    void updateHostSetAllocation(HostInterface host, AllocationInterface alloc);

    /**
     *
     * @param id   String
     * @param tag  String
     * @param type HostTagType
     */
    void tagHost(String id, String tag, HostTagType type);

    /**
     *
     * @param host HostInterface
     * @param tag  String
     * @param type HostTagType
     */
    void tagHost(HostInterface host, String tag, HostTagType type);

    /**
     *
     * @param host HostInterface
     * @param type HostTagType
     */
    void removeTagsByType(HostInterface host, HostTagType type);

    /**
     * removes a tag
     *
     * @param host HostInterface
     * @param tag  String
     */
    void removeTag(HostInterface host, String tag);

    /**
     * renames a tag from oldTag to newTag
     *
     * @param host   HostInterface
     * @param oldTag String
     * @param newTag String
     */
    void renameTag(HostInterface host, String oldTag, String newTag);

    /**
     * You must run this AFTER you've changed any type of job tags. The reason
     * this is not a trigger or something of that nature is because is an
     * intense process.
     *
     * @param id String
     */
    void recalcuateTags(final String id);

    /**
     *
     * @param host HostInterface
     * @param mode ThreadMode
     */
    void updateThreadMode(HostInterface host, ThreadMode mode);

    /**
     * When a host is in kill mode that means its 256MB+ into the swap and the
     * the worst memory offender is killed.
     *
     * @param h HostInterface
     * @return boolean
     */
    boolean isKillMode(HostInterface h);

    /**
     * Update the specified host's hardware information.
     *
     * @param host        HostInterface
     * @param totalMemory long
     * @param freeMemory  long
     * @param totalSwap   long
     * @param freeSwap    long
     * @param totalScratch    long
     * @param freeScratch     long
     * @param totalGpu    long
     * @param freeGpu     long
     * @param load        int
     * @param os          String
     */
    void updateHostStats(HostInterface host,
            long totalMemory, long freeMemory,
            long totalSwap, long freeSwap,
            long totalScratch, long freeScratch,
            long totalGpu, long freeGpu,
            int load, Timestamp bootTime, String os);

    /**
     * Return true if the HardwareState is Up, false if it is anything else.
     *
     * @param host HostInterface
     * @return boolean
     */
    boolean isHostUp(HostInterface host);

    /**
     * Return the number of whole stranded cores on this host. The must have
     * less than Dispacher.MEM_STRANDED_THRESHHOLD for the cores to be
     * considered stranded.
     *
     * @param h HostInterface
     * @return int
     */
    int getStrandedCoreUnits(HostInterface h);

    /**
     * Return true if the host is preferring a particular show.
     *
     * @param h HostInterface
     * @return boolean
     */
    boolean isPreferShow(HostInterface h);

    /**
     * Return true if the host is a NIMBY host.
     *
     * @param h HostInterface
     * @return boolean
     */
    boolean isNimbyHost(HostInterface h);

    /**
     * Update the host's operating system setting.
     *
     * @param host HostInterface
     * @param os   String
     */
    void updateHostOs(HostInterface host, String os);

    /**
     * Update a host's resource pool using the latest host report.
     *
     * @param host   HostInterface
     * @param report HostReport
     */
    void updateHostResources(HostInterface host, HostReport report);

}

