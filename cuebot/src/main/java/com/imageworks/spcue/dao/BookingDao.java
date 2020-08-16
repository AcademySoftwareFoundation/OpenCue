
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

public interface BookingDao {

    /**
     * Updates the maximum number of cores the given local
     * host assignment should use.
     *
     * @param l
     * @return
     */
    boolean updateMaxCores(LocalHostAssignment l, int maxCoreUnits);

    /**
     * Updates the maximum number of gpu's the given local
     * host assignment should use.
     *
     * @param l
     * @return
     */
    boolean updateMaxGpu(LocalHostAssignment l, int gpu);

    /**
     * Updates the maximum amount of memory a given local host
     * assignment should use.
     *
     * @param l
     * @return
     */
    boolean updateMaxMemory(LocalHostAssignment l, long maxMemory);

    /**
     * Updates the maximum amount of gpu memory a given local host
     * assignment should use.
     *
     * @param l
     * @return
     */
    boolean updateMaxGpuMemory(LocalHostAssignment l, long maxGpuMemory);

    /**
     * Create a new LocalHostAssignment attached to the given job.
     *
     * @param host
     * @param job
     * @param lha
     */
    void insertLocalHostAssignment(HostInterface host, JobInterface job,
                                   LocalHostAssignment lha);

    /**
     * Create a new LocalHostAssignment attached to the given layer.
     *
     * @param host
     * @param layer
     * @param lha
     */
    void insertLocalHostAssignment(HostInterface host, LayerInterface layer,
                                   LocalHostAssignment lha);

    /**
     * Create a new LocalHostAssignment attached to the given frame.
     *
     * @param host
     * @param frame
     * @param lha
     */
    void insertLocalHostAssignment(HostInterface host, FrameInterface frame,
                                   LocalHostAssignment lha);

    /**
     * Return the host + jobs local booking assignment properties.
     * @param host
     * @param job
     * @return
     */
    List<LocalHostAssignment> getLocalJobAssignment(HostInterface host);

    /**
     * Return the host + jobs local booking assignment properties.
     * @param host
     * @param job
     * @return
     */
    LocalHostAssignment getLocalJobAssignment(String id);

    /**
     * Return the host + jobs local booking assignment properties.
     * @param hostId
     * @param jobId
     * @return
     */
    LocalHostAssignment getLocalJobAssignment(String hostId, String jobId);

    /**
     * Return true if the host has a local job assignment.
     *
     * @param host
     * @return
     */
    boolean hasLocalJob(HostInterface host);

    /**
     * Returns true if the host has an active local booking.
     *
     * @param host
     * @return
     */
    boolean hasActiveLocalJob(HostInterface host);

    /**
     * Return true if the host is in blackout time.
     *
     * @param h
     * @return
     */
    boolean isBlackoutTime(HostInterface h);

    /**
     * Delete the given LocalHostAssignment.
     *
     * @param e
     */
    boolean deleteLocalJobAssignment(LocalHostAssignment lha);

    /**
     * Deactivate the given LocalHostAssignment.
     *
     * @param l
     */
    boolean deactivate(LocalHostAssignment l);

    /**
     * Return the difference between the number of assigned cores and
     * the given coreUnits.
     *
     * @param l
     * @param coreUnits
     * @return
     */
    int getCoreUsageDifference(LocalHostAssignment l, int coreUnits);

    /**
     * Return the difference between the number of assigned cores and
     * the given coreUnits.
     *
     * @param l
     * @param coreUnits
     * @return
     */
    int getGpuUsageDifference(LocalHostAssignment l, int gpu);

    /**
     * Allocate additional cores from the given host.
     *
     * @param h
     * @param cores
     * @return
     */
    boolean allocateCoresFromHost(HostInterface h, int cores);

    /**
     * Deallocate cores from the given host, returning them to its pool.
     *
     * @param h
     * @param cores
     * @return
     */
    boolean deallocateCoresFromHost(HostInterface h, int cores);

    /**
     * Allocate additional gpu from the given host.
     *
     * @param h
     * @param gpu
     * @return
     */
    boolean allocateGpuFromHost(HostInterface h, int gpu);

    /**
     * Deallocate gpu from the given host, returning them to its pool.
     *
     * @param h
     * @param gpu
     * @return
     */
    boolean deallocateGpuFromHost(HostInterface h, int gpu);

    /**
     * Return true if the Host has a resource deficit.  A
     * deficit can occur if there are more resources in use than the
     * maximum allowed due to changes from the user.
     *
     * @param l
     * @return
     */
    boolean hasResourceDeficit(HostInterface host);

}

