
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
import java.util.Set;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.VirtualProc;

/**
* DispatcherDao provides DAO methods used by the DispatchService
*/
public interface DispatcherDao {

    /**
     * Schedules the next frame on the specified job that can utilize
     * the free resources on the host.
     *
     * @param host
     * @param job
     * @return
     */
    DispatchFrame scheduleNextDispatchFrame(JobInterface job, DispatchHost host);

    /**
     * Schedules the next frame based on the supplied job
     *
     * @param job
     * @param proc
     * @return DispatchFrame
     */
    DispatchFrame scheduleNextDispatchFrame(JobInterface job, VirtualProc proc);

    /**
     * Schedules the next frame on the specified job that can utilize
     * the free resources on the host.
     *
     * @param host
     * @param job
     * @return
     */
    List<DispatchFrame> scheduleNextDispatchFrames(JobInterface job, DispatchHost host, int limit);

    /**
     * Schedules the next frame based on the supplied job
     *
     * @param job
     * @param proc
     * @return DispatchFrame
     */
    List<DispatchFrame> scheduleNextDispatchFrames(JobInterface job, VirtualProc proc, int limit);

    /**
     * Return a list of jobs which could use resources of the specified
     * host. It does not consider show priority.
     *
     * @param host
     * @param numJobs
     * @return
     */
    Set<String> findDispatchJobsForAllShows(DispatchHost host, int numJobs);

    /**
     * Return a list of jobs which could use resources of the specified
     * host
     *
     * @param host
     * @param numJobs
     * @return
     */
    Set<String> findDispatchJobs(DispatchHost host, int numJobs);

    /**
    * Return a list of jobs which could use resources of the specified
    * host that are in the specified group.
    *
    * @param host
    * @param numJobs
    * @return
    */
    Set<String> findDispatchJobs(DispatchHost host, GroupInterface g);

    /**
     * Finds an under proced job if one exists and returns it,
     * otherwise it returns null.
     *
     * @param excludeJob
     * @param proc
     * @return
     */
    boolean findUnderProcedJob(JobInterface excludeJob, VirtualProc proc);

    /**
     * Returns true if there exists a higher priority job than the base job
     *
     * @param baseJob
     * @param proc
     * @return boolean
     */
    boolean higherPriorityJobExists(JobDetail baseJob, VirtualProc proc);

    /**
    * Dispatch the given host to the specified show.  Look for a max of numJobs.
    *
    * @param host
    * @param show
    * @param numJobs
    * @return
    */
   Set<String> findDispatchJobs(DispatchHost host, ShowInterface show, int numJobs);

   /**
    * Find a list of local dispatch jobs.
    *
    * @param host
    * @return
    */
   Set<String> findLocalDispatchJobs(DispatchHost host);

   /**
    * Schedules a list of frames from the given layer.
    *
    * @param layer
    * @param proc
    * @param limit
    * @return
    */
   List<DispatchFrame> scheduleNextDispatchFrames(LayerInterface layer, VirtualProc proc,
                                              int limit);

   /**
    * Schedules a list of frames from the given layer.
    *
    * @param layer
    * @param host
    * @param limit
    * @return
    */
   List<DispatchFrame> scheduleNextDispatchFrames(LayerInterface layer, DispatchHost host,
                                              int limit);

   /**
    * Schedules a frame with the frame's uinique ID to dispatch.
    *
    * @param frameId
    * @return DispatchFrame
    */
   List<DispatchFrame> scheduleDispatchFrame(String frameId);

   /**
    * Unschedules the specified frames (Resets the scheduled state of the frames.)
    *
    * @param dispatchFrames
    * @param excluded
    * @return
    */
   void unscheduleDispatchFrames(List<DispatchFrame> dispatchFrames,
                                 Set<DispatchFrame> excluded);
}


