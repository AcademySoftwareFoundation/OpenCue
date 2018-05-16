
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



package com.imageworks.spcue.dao;

import java.util.List;

import com.imageworks.spcue.Frame;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Layer;
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
    boolean updateMaxGpu(LocalHostAssignment l, long maxGpu);

    /**
     * Create a new LocalHostAssignment attached to the given job.
     *
     * @param host
     * @param job
     * @param lha
     */
    void insertLocalHostAssignment(Host host, Job job,
            LocalHostAssignment lha);

    /**
     * Create a new LocalHostAssignment attached to the given layer.
     *
     * @param host
     * @param layer
     * @param lha
     */
    void insertLocalHostAssignment(Host host, Layer layer,
            LocalHostAssignment lha);

    /**
     * Create a new LocalHostAssignment attached to the given frame.
     *
     * @param host
     * @param frame
     * @param lha
     */
    void insertLocalHostAssignment(Host host, Frame frame,
            LocalHostAssignment lha);

    /**
     * Return the host + jobs local booking assignment properties.
     * @param host
     * @param job
     * @return
     */
    List<LocalHostAssignment> getLocalJobAssignment(Host host);

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
    boolean hasLocalJob(Host host);

    /**
     * Returns true if the host has an active local booking.
     *
     * @param host
     * @return
     */
    boolean hasActiveLocalJob(Host host);

    /**
     * Return true if the host is in blackout time.
     *
     * @param h
     * @return
     */
    boolean isBlackoutTime(Host h);

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
     * Allocate additional cores from the given host.
     *
     * @param h
     * @param cores
     * @return
     */
    boolean allocateCoresFromHost(Host h, int cores);

    /**
     * Deallocate cores from the given host, returning them to its pool.
     *
     * @param h
     * @param cores
     * @return
     */
    boolean deallocateCoresFromHost(Host h, int cores);

    /**
     * Return true if the Host has a resource deficit.  A
     * deficit can occur if there are more resources in use than the
     * maximum allowed due to changes from the user.
     *
     * @param l
     * @return
     */
    boolean hasResourceDeficit(Host host);

}

