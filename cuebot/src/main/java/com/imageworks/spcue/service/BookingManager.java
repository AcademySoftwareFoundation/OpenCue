
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

import java.util.List;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;

public interface BookingManager {

    /**
     * Return an active LocalHostAssignment for the given host.
     *
     * @param host
     * @return
     */
    public List<LocalHostAssignment> getLocalHostAssignment(HostInterface host);

    /**
     * Return an active LocalHostAssignment for the given unique ID.
     *
     * @param id
     * @return
     */
    public LocalHostAssignment getLocalHostAssignment(String id);

    /**
     * Return an active LocalHostAssignment for the given job ID and host ID.
     *
     * @param hostId
     * @param jobId
     * @return
     */
    public LocalHostAssignment getLocalHostAssignment(String hostId, String jobId);

    /**
     * Create a local host assignment for the given job.
     *
     * @param host
     * @param job
     * @param lja
     */
    public void createLocalHostAssignment(DispatchHost host,
                                          JobInterface job, LocalHostAssignment lja);

    /**
     * Create a local host assignment for the given layer.
     *
     * @param host
     * @param layer
     * @param lja
     */
    public void createLocalHostAssignment(DispatchHost host,
                                          LayerInterface layer, LocalHostAssignment lja);

    /**
     * Create a local host assignment for the given frame.
     *
     * @param host
     * @param frame
     * @param lja
     */
    public void createLocalHostAssignment(DispatchHost host,
                                          FrameInterface frame, LocalHostAssignment lja);

    /**
     * Return true if the host as a local assignment.
     *
     * @param host
     * @return
     */
    public boolean hasLocalHostAssignment(HostInterface host);

    /**
     * Return true if the given host has active local frames.
     *
     * @param host
     * @return
     */
    public boolean hasActiveLocalFrames(HostInterface host);

    /**
     * Remove the given LocalHostAssignment.
     *
     * @param lha
     */
    void removeLocalHostAssignment(LocalHostAssignment lha);

    /**
     * Deactivate the the given LocalHostAssignment.  Deactivated entries
     * will not book procs.
     *
     * @param lha
     */
    void deactivateLocalHostAssignment(LocalHostAssignment lha);

    /**
     * Set the max resource usage for the given LocalHostAssignment.
     *
     * @param l
     * @param maxCoreUnits
     * @param maxMemory
     * @param maxGpuUnits
     * @param maxGpuMemory
     */
    void setMaxResources(LocalHostAssignment l, int maxCoreUnits, long maxMemory, int maxGpuUnits, long maxGpuMemory);

    /**
     * Remove a LocalHostAssignment if there are no procs assigned to it.
     *
     * @param lha
     */
    void removeInactiveLocalHostAssignment(LocalHostAssignment lha);

    /**
     * Return true if the host is running more cores than the maximum allowed.
     *
     * @param host
     * @return
     */
    boolean hasResourceDeficit(HostInterface host);
}

