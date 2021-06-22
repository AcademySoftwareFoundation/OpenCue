
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



package com.imageworks.spcue.dispatcher;

import java.util.ArrayList;
import java.util.List;

import org.apache.log4j.Logger;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.service.BookingManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;

public class LocalDispatcher extends AbstractDispatcher implements Dispatcher {

    private static final Logger logger =
        Logger.getLogger(LocalDispatcher.class);

    private BookingManager bookingManager;
    private JobManager jobManager;
    private HostManager hostManager;

    private static final int MAX_QUERY_FRAMES = 10;
    private static final int MAX_DISPATCHED_FRAMES = 10;

    @Override
    public List<VirtualProc> dispatchHostToAllShows(DispatchHost host) {
        return new ArrayList<VirtualProc>();
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host) {

        List<LocalHostAssignment> lhas =
            bookingManager.getLocalHostAssignment(host);
        host.isLocalDispatch = true;

        ArrayList<VirtualProc> procs = new ArrayList<VirtualProc>();
        for (LocalHostAssignment lha : lhas) {
            prepHost(host, lha);
            switch(lha.getType()) {
                case JOB_PARTITION:
                    procs.addAll(dispatchHost(host, jobManager.getJob(
                            lha.getJobId()), lha));
                    break;
                case LAYER_PARTITION:
                    procs.addAll(dispatchHost(host, jobManager.getLayerDetail(
                            lha.getLayerId()), lha));
                    break;
                case FRAME_PARTITION:
                    procs.addAll(dispatchHost(host, jobManager.getFrame(
                            lha.getFrameId()), lha));
                    break;
                default:
                    logger.warn("Error, invalid render " +
                                "partition type: " + lha.getType());
            }
        }

        return procs;
    }

    private List<VirtualProc> dispatchHost(DispatchHost host, JobInterface job,
            LocalHostAssignment lha) {

        List<VirtualProc> procs = new ArrayList<VirtualProc>(MAX_DISPATCHED_FRAMES);

        /*
         * Grab a list of frames to dispatch.
         */
        List<DispatchFrame> frames = dispatchSupport.findNextDispatchFrames(job,
                host, MAX_QUERY_FRAMES);

        logger.info("Frames found: " + frames.size() + " for host " +
                host.getName() + " " + host.idleCores + "/" + host.idleMemory +
                " on job " + job.getName());

        for (DispatchFrame frame: frames) {

            /*
             * Check if we have enough memory/cores for this frame, if
             * not move on.
             */
            if (!lha.hasAdditionalResources(lha.getThreads() * 100,
                    frame.minMemory,
                    frame.minGpus,
                    frame.minGpuMemory)) {
                continue;
            }

            /*
             * Build our virtual proc.
             */
            VirtualProc proc =  VirtualProc.build(host, frame, lha);

            /*
             * Double check the job has pending frames.
             */
            if (!dispatchSupport.hasPendingFrames(job)) {
                break;
            }

            /*
             * Dispatch the frame.  If a frame is booked, dispatchHost returns true,
             * else if returns false.  If the dispatch fails in a way
             * that we should stop dispatching immediately (the host is down),
             * a DispatcherException is thrown.
             */
            if (dispatchHost(frame, proc)) {

                procs.add(proc);

                /*
                 * This should stay here and not go into VirtualProc
                 * or else the count will be off if you fail to book.
                 */
                lha.useResources(proc.coresReserved, proc.memoryReserved, proc.gpusReserved, proc.gpuMemoryReserved);
                if (!lha.hasAdditionalResources(lha.getThreads() * 100,
                        Dispatcher.MEM_RESERVED_MIN,
                        Dispatcher.GPU_UNITS_RESERVED_MIN,
                        Dispatcher.MEM_GPU_RESERVED_MIN)) {
                    break;
                }

                if (procs.size() >= MAX_DISPATCHED_FRAMES) {
                    break;
                }
            }
        }

        if (procs.size() == 0) {
            bookingManager.removeInactiveLocalHostAssignment(lha);
        }

        return procs;
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, JobInterface job) {
        /*
         * Load up the local assignment.  If one doesn't exist, that means
         * the user has removed it and no booking action should be taken.
         */
        LocalHostAssignment lha = bookingManager.getLocalHostAssignment(host.getHostId(),
                                                                        job.getJobId());
        prepHost(host, lha);

        return dispatchHost(host, job, lha);
    }

    private List<VirtualProc> dispatchHost(DispatchHost host, LayerInterface layer,
            LocalHostAssignment lha) {

        List<VirtualProc> procs = new ArrayList<VirtualProc>(MAX_DISPATCHED_FRAMES);
        /*
         * Grab a list of frames to dispatch.
         */
        List<DispatchFrame> frames = dispatchSupport.findNextDispatchFrames(
                layer, host, MAX_QUERY_FRAMES);

        logger.info("Frames found: " + frames.size() + " for host " +
                host.getName() + " " + host.idleCores + "/" + host.idleMemory +
                " on layer " + layer);

        for (DispatchFrame frame: frames) {

            /*
             * Check if we have enough memory/cores for this frame, if
             * not move on.
             */
            if (!lha.hasAdditionalResources(lha.getThreads() * 100,
                    frame.minMemory,
                    frame.minGpus,
                    frame.minGpuMemory)) {
                continue;
            }

            /*
             * Create our virtual proc.
             */
            VirtualProc proc =  VirtualProc.build(host, frame, lha);

            /*
             * Double check if the layer we're booking has pending frames.
             */
            if (!dispatchSupport.hasPendingFrames(layer)) {
                break;
            }

            /*
             * Dispatch the frame.  If a frame is booked, dispatchHost returns true,
             * else if returns false.  If the dispatch fails in a way
             * that we should stop dispatching immediately (the host is down),
             * a DispatcherException is thrown.
             */
            if (dispatchHost(frame, proc)) {

                procs.add(proc);

                /*
                 * This should stay here and not go into VirtualProc
                 * or else the count will be off if you fail to book.
                 */
                lha.useResources(proc.coresReserved, proc.memoryReserved, proc.gpusReserved, proc.gpuMemoryReserved);
                if (!lha.hasAdditionalResources(100,
                        Dispatcher.MEM_RESERVED_MIN,
                        Dispatcher.GPU_UNITS_RESERVED_MIN,
                        Dispatcher.MEM_GPU_RESERVED_MIN)) {
                    break;
                }

                if (procs.size() >= MAX_DISPATCHED_FRAMES) {
                    break;
                }
            }
        }

        if (procs.size() == 0) {
            bookingManager.removeInactiveLocalHostAssignment(lha);
        }

        return procs;
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, LayerInterface layer) {

        /*
         * Load up the local assignment.  If one doesn't exist, that means
         * the user has removed it and no booking action should be taken.
         */

        LocalHostAssignment lha = bookingManager.getLocalHostAssignment(host.getHostId(),
                                                                        layer.getJobId());
        prepHost(host, lha);

        return dispatchHost(host, layer, lha);
    }

    private List<VirtualProc> dispatchHost(DispatchHost host, FrameInterface frame,
        LocalHostAssignment lha) {

        List<VirtualProc> procs = new ArrayList<VirtualProc>(1);

        /*
         * Grab a dispatch frame record for the frame we want to dispatch.
         */
        DispatchFrame dframe = jobManager.getDispatchFrame(frame.getId());
        if (!lha.hasAdditionalResources(lha.getMaxCoreUnits(),
                dframe.minMemory,
                lha.getMaxGpuUnits(),
                dframe.minGpuMemory)) {
            return procs;
        }

        VirtualProc proc =  VirtualProc.build(host, dframe, lha);

        /*
         * Dispatch the frame.  If a frame is booked, dispatchHost returns true,
         * else if returns false.  If the dispatch fails in a way
         * that we should stop dispatching immediately (the host is down),
         * a DispatcherException is thrown.
         */
        if (dispatchHost(dframe, proc)) {
            procs.add(proc);
        }

        if (procs.size() == 0) {
            bookingManager.removeInactiveLocalHostAssignment(lha);
        }

        return procs;
    }

    public List<VirtualProc> dispatchHost(DispatchHost host, FrameInterface frame) {
        /*
         * Load up the local assignment.  If one doesn't exist, that means
         * the user has removed it and no booking action should be taken.
         */

        LocalHostAssignment lha = bookingManager.getLocalHostAssignment(host.getHostId(),
                                                                        frame.getJobId());
        prepHost(host, lha);

        return dispatchHost(host, frame, lha);
    }

    @Override
    public void dispatchProcToJob(VirtualProc proc, JobInterface job) {

        LocalHostAssignment lha = null;
        proc.isLocalDispatch = true;

        try {
            lha = bookingManager.getLocalHostAssignment(proc.getHostId(),
                                                        job.getJobId());
        } catch (EmptyResultDataAccessException e) {
            logger.warn("Unable to find local host assignment for " + proc);
            dispatchSupport.unbookProc(proc);
            return;
        }

        List<DispatchFrame> frames = null;
        switch(lha.getType()) {
            case JOB_PARTITION:
                frames = dispatchSupport.findNextDispatchFrames(job,
                        proc, MAX_QUERY_FRAMES);
                if (frames.size() == 0) {
                     dispatchSupport.unbookProc(proc);
                     dispatchHost(hostManager.getDispatchHost(proc.getHostId()), job);
                     return;
                }

                break;

            case LAYER_PARTITION:
                frames = dispatchSupport.findNextDispatchFrames(
                        jobManager.getLayer(proc.getLayerId()),
                        proc, MAX_QUERY_FRAMES);
                break;

            case FRAME_PARTITION:

                DispatchFrame dispatchFrame =
                    jobManager.getDispatchFrame(lha.getFrameId());
                frames = new ArrayList<DispatchFrame>(1);

                if (dispatchFrame.state.equals(FrameState.WAITING)) {
                    frames.add(dispatchFrame);
                }
                break;

       default:
           throw new DispatcherException(
                   "Invalid local host assignment: " + lha.getType());

        }

        logger.info("Frames found: " + frames.size() + " for host " +
                proc + " " + proc.coresReserved + "/" + proc.memoryReserved +
                " on job " + job.getName());

        for (DispatchFrame frame: frames) {
            if (dispatchProc(frame, proc)) {
                return;
            }
        }

        dispatchSupport.unbookProc(proc);
    }

    /**
     * Copy the local host assignment into the DispatchHost
     *
     * @param host
     * @param lha
     */
    private void prepHost(DispatchHost host, LocalHostAssignment lha) {
        host.isLocalDispatch = true;
        host.idleCores = lha.getIdleCoreUnits();
        host.idleMemory = lha.getIdleMemory();
        host.idleGpus = lha.getIdleGpuUnits();
        host.idleGpuMemory = lha.getIdleGpuMemory();
    }


    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, ShowInterface show) {
        throw new RuntimeException("not implemented");
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, GroupInterface g) {
        throw new RuntimeException("not implemented");
    }

    public JobManager getJobManager() {
        return jobManager;
    }


    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }


    public BookingManager getBookingManager() {
        return bookingManager;
    }


    public void setBookingManager(BookingManager bookingManager) {
        this.bookingManager = bookingManager;
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }
}

