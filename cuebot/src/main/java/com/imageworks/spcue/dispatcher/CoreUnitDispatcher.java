
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



package com.imageworks.spcue.dispatcher;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import org.apache.log4j.Logger;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobDispatchException;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.util.CueUtil;

/**
 * The Core Unit Dispatcher.
 *
 * The dispatching pipeline is a 3 stage process.  Steps
 * 1 and 2 are separate DB transactions.
 *
 * 1. Attempt to start the frame by updating to the
 * Running state.  If another thread gets there first,
 * a FrameReservationException is thrown.
 *
 * 2. Reserve processor resources and update resource counts
 * on the host, subscription, job, layer, group, and shot.
 *
 * 3. Contact RQD and launch the frame.
 *
 * Error Handling
 *
 * Depending on where the error happens and what the error is,
 * you might have to take the necessary steps to undo the dispatch
 * because the transaction is not held open the entire time.
 *
 * FrameReservationException - You don't have to undo anything.
 *
 * ResourceDuplicationFailureException - If there is ever a bug that
 * causes the dispatcher to try and dispatch a frame with a proc
 * already assigned to it, catching this and continuing to the next
 * frame will ensure your dispatcher doesn't get stuck trying to
 * launch just one frame.  You can also try to fix the frame by
 * running dispatchSupport.fixFrame().
 *
 * ResourceReservationFailureException - This means the host didn't have
 * the resources the dispatcher expected it to have.  In this case
 * you have to dispatchSupport.clearFrame(frame) to set the frame back
 * to the Waiting state.
 *
 * For all other exceptions, both the frame and the proc have to be
 * manually removed.
 */
public class CoreUnitDispatcher implements Dispatcher {
    private static final Logger logger =
        Logger.getLogger(CoreUnitDispatcher.class);

    private DispatchSupport dispatchSupport;

    private JobManager jobManager;

    private RqdClient rqdClient;

    private HostManager hostManager;

    public boolean testMode = false;

    /*
     * Maximum number of jobs to query.
     */
    private static final int JOB_QUERY_MAX = 20;

    /*
     * Number of seconds before waiting to book the same job
     * from a different host.
     */
    private static final int JOB_LOCK_EXPIRE_SECONDS = 5;

    /*
     * Maximum number of frames to query from the DB
     * to attempt to dispatch.
     */
    private static final int FRAME_QUERY_MAX = 10;

    /* Maximum number of frames to book at one time on
     * the same host.
     */
    private static final int JOB_FRAME_DISPATCH_MAX = 2;

    /*
     * Maximum number of frames to dispatch from a host
     * at one time.
     */
    private static final int HOST_FRAME_DISPATCH_MAX = 12;

    /*
     * Keeps a map of unique job IDs that should be skipped
     * over for booking until the record has expired.
     */
    // TODO: concurrencyLevel(3) is likely too low given the number of dispatch threads
    private Cache<String, String> jobLock = CacheBuilder.newBuilder()
        .concurrencyLevel(3)
        .expireAfterWrite(JOB_LOCK_EXPIRE_SECONDS, TimeUnit.SECONDS)
        .build();

    private List<VirtualProc> dispatchJobs(DispatchHost host, Set<String> jobs) {
        List<VirtualProc> procs = new ArrayList<VirtualProc>();

        try {
            for (String jobid: jobs) {

                if (!host.hasAdditionalResources(
                        Dispatcher.CORE_POINTS_RESERVED_MIN,
                        Dispatcher.MEM_RESERVED_MIN,
                        Dispatcher.GPU_RESERVED_MIN)) {
                    return procs;
                }

                if (procs.size() >= HOST_FRAME_DISPATCH_MAX) {
                    break;
                }

                if (jobLock.getIfPresent(jobid) != null) {
                    continue;
                }

                jobLock.put(jobid, jobid);

                DispatchJob job = jobManager.getDispatchJob(jobid);
                try {
                    procs.addAll(dispatchHost(host, job));
                }
                catch (JobDispatchException e) {
                    logger.info("job dispatch exception," + e);
                }
            }

        } catch (DispatcherException e) {
            logger.warn("dispatcher exception," + e);
        }

        host.restoreGpu();

        return procs;
    }

    private Set<String> getGpuJobs(DispatchHost host, ShowInterface show) {
        Set<String> jobs = null;

        // TODO: GPU: make index with the 4 components instead of just 3, replace the just 3

        // If the host has gpu idle, first do a query to find gpu jobs
        // If no gpu jobs found remove resources to leave room for a gpu frame
        if (host.hasAdditionalResources(
                        Dispatcher.CORE_POINTS_RESERVED_DEFAULT,
                        Dispatcher.MEM_RESERVED_MIN,
                        1)) {
            if (show == null)
                jobs = dispatchSupport.findDispatchJobs(host, JOB_QUERY_MAX);
            else
                jobs = dispatchSupport.findDispatchJobs(host, show, JOB_QUERY_MAX);

            if (jobs.size() == 0) {
                host.removeGpu();
                jobs = null;
            }
        }

        return jobs;
    }

    @Override
    public List<VirtualProc> dispatchHostToAllShows(DispatchHost host) {
        Set<String> jobs = dispatchSupport.findDispatchJobsForAllShows(
                               host,
                               JOB_QUERY_MAX);

        return dispatchJobs(host, jobs);
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host) {

        Set<String> jobs = getGpuJobs(host, null);

        if (jobs == null)
            jobs = dispatchSupport.findDispatchJobs(host, JOB_QUERY_MAX);

        return dispatchJobs(host, jobs);
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, ShowInterface show) {

        Set<String> jobs = getGpuJobs(host, show);

        if (jobs == null)
            jobs = dispatchSupport.findDispatchJobs(host, show, JOB_QUERY_MAX);

        return dispatchJobs(host, jobs);
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, GroupInterface group) {

        Set<String> jobs = getGpuJobs(host, null);

        if (jobs == null)
            jobs = dispatchSupport.findDispatchJobs(host, group);

        return dispatchJobs(host, jobs);
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, JobInterface job) {

        List<VirtualProc> procs = new ArrayList<VirtualProc>();

        if (host.strandedCores == 0 &&
                dispatchSupport.isShowAtOrOverBurst(job, host)) {
            return procs;
        }

        List<DispatchFrame> frames = dispatchSupport.findNextDispatchFrames(job,
                host, FRAME_QUERY_MAX);

        logger.info("Frames found: " + frames.size() + " for host " +
                host.getName() + " " + host.idleCores + "/" + host.idleMemory +
                " on job " + job.getName());

        for (DispatchFrame frame: frames) {

            VirtualProc proc =  VirtualProc.build(host, frame);

            if (host.idleCores < frame.minCores ||
                    host.idleMemory < frame.minMemory ||
                    host.idleGpu < frame.minGpu) {
                break;
            }

            if (!dispatchSupport.isJobBookable(job, proc.coresReserved)) {
                break;
            }


            if (host.strandedCores == 0 &&
                    dispatchSupport.isShowAtOrOverBurst(job, host)) {
                return procs;
            }

            boolean success = new DispatchFrameTemplate(proc, job, frame, false) {
                public void wrapDispatchFrame() {
                    dispatch(frame, proc);
                    dispatchSummary(proc, frame, "Booking");
                    return;
                }
            }.execute();

            if (success) {
                procs.add(proc);

                DispatchSupport.bookedProcs.getAndIncrement();
                DispatchSupport.bookedCores.addAndGet(proc.coresReserved);

                if (host.strandedCores > 0) {
                    dispatchSupport.pickupStrandedCores(host);
                    break;
                }

                host.useResources(proc.coresReserved, proc.memoryReserved, proc.gpuReserved);
                if (!host.hasAdditionalResources(
                        Dispatcher.CORE_POINTS_RESERVED_MIN,
                        Dispatcher.MEM_RESERVED_MIN,
                        Dispatcher.GPU_RESERVED_MIN)) {
                    break;
                }
                else if (procs.size() >= JOB_FRAME_DISPATCH_MAX) {
                    break;
                }
                else if (procs.size() >= HOST_FRAME_DISPATCH_MAX) {
                    break;
                }
            }
        }

        return procs;

    }

    public void dispatchProcToJob(VirtualProc proc, JobInterface job)
    {

        // Do not throttle this method
        for (DispatchFrame frame:
            dispatchSupport.findNextDispatchFrames(job, proc, FRAME_QUERY_MAX)) {
            try {
                boolean success = new DispatchFrameTemplate(proc, job, frame, true) {
                    public void wrapDispatchFrame() {
                        dispatch(frame, proc);
                        dispatchSummary(proc, frame, "Dispatch");
                        return;
                    }
                }.execute();
                if (success)
                    return;
            }
            catch (DispatcherException e) {
                return;
            }
        }

        dispatchSupport.unbookProc(proc);
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, LayerInterface layer) {
        throw new RuntimeException("not implemented)");
    }

    @Override
    public List<VirtualProc> dispatchHost(DispatchHost host, FrameInterface frame) {
        throw new RuntimeException("not implemented)");
    }

    @Override
    public void dispatch(DispatchFrame frame, VirtualProc proc) {
        /*
         * The frame is reserved, the proc is created, now update
         * the frame to the running state.
         */
        dispatchSupport.startFrame(proc, frame);

        /*
         * Creates a proc to run on the specified frame.  Throws
         * a ResourceReservationFailureException if the proc
         * cannot be created due to lack of resources.
         */
        dispatchSupport.reserveProc(proc, frame);

        /*
         * Communicate with RQD to run the frame.
         */
        if (!testMode) {
            dispatchSupport.runFrame(proc,frame);
        }
    }

    @Override
    public boolean isTestMode() {
        return testMode;
    }


    @Override
    public void setTestMode(boolean enabled) {
        testMode = enabled;
    }

    /**
     * Log a summary of each dispatch.
     *
     * @param p     the VirtualProc that was used
     * @param f     the DispatchFrame that that was used
     * @param type  the type of dispatch
     */
    private void dispatchSummary(VirtualProc p, DispatchFrame f, String type) {
        String msg = type + " summary: " +
            p.coresReserved +
            " cores / " +
            CueUtil.KbToMb(p.memoryReserved) +
            " memory / " +
            p.gpuReserved +
            " gpu on " +
            p.getName() +
            " to " + f.show + "/" + f.shot;
        logger.trace(msg);
    }


    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public RqdClient getRqdClient() {
        return rqdClient;
    }

    public void setRqdClient(RqdClient rqdClient) {
        this.rqdClient = rqdClient;
    }

    private abstract class DispatchFrameTemplate {
        protected VirtualProc proc;
        protected JobInterface job;
        protected DispatchFrame frame;
        boolean procIndb = true;

        public DispatchFrameTemplate(VirtualProc p,
                                     JobInterface j,
                                     DispatchFrame f,
                                     boolean inDb) {
            proc = p;
            job = j;
            frame = f;
            procIndb = inDb;
        }

        public abstract void wrapDispatchFrame();

        public boolean execute()  {
            try {
                wrapDispatchFrame();
            } catch (FrameReservationException fre) {
                /*
                    * This usually just means another thread got the frame
                    * first, so just retry on the next frame.
                    */
                DispatchSupport.bookingRetries.incrementAndGet();
                String msg = "frame reservation error, " +
                    "dispatchProcToJob failed to book next frame, " + fre;
                logger.warn(msg);
                return false;
            }
            catch (ResourceDuplicationFailureException rrfe) {
                /*
                    * There is a resource already assigned to the
                    * frame we reserved!  Don't clear the frame,
                    * let it keep running and continue to the
                    * next frame.
                    */
                DispatchSupport.bookingErrors.incrementAndGet();
                dispatchSupport.fixFrame(frame);

                String msg = "proc update error, dispatchProcToJob failed " +
                    "to assign proc to job " + job + ", " + proc +
                    " already assigned to another frame." + rrfe;

                logger.warn(msg);
                return false;
            }
            catch (ResourceReservationFailureException rrfe) {
                /*
                    * This should technically never happen since the proc
                    * is already allocated at this point, but, if it does
                    * it should be unbooked.
                    */
                DispatchSupport.bookingErrors.incrementAndGet();
                String msg = "proc update error, " +
                    "dispatchProcToJob failed to assign proc to job " +
                    job + ", " + rrfe;
                logger.warn(msg);
                if (procIndb) {
                    dispatchSupport.unbookProc(proc);
                }
                dispatchSupport.clearFrame(frame);
                /* Throw an exception to stop booking **/
                throw new DispatcherException("host reservation error, " +
                    "dispatchHostToJob failed to allocate a new proc " + rrfe);
            }
            catch (Exception e) {
                /*
                    * Everything else means that the host/frame record was
                    * updated but another error occurred and the proc
                    * should be cleared.  It could also be running, so
                    * use the jobManagerSupprot to kill it just in case.
                    */
                DispatchSupport.bookingErrors.incrementAndGet();
                String msg = "dispatchProcToJob failed booking proc " +
                    proc + " on job " + job;
                logger.warn(msg, e);
                dispatchSupport.unbookProc(proc);
                dispatchSupport.clearFrame(frame);

                try {
                    rqdClient.killFrame(proc, "An accounting error occured " +
                            "when booking this frame.");
                } catch (RqdClientException rqde) {
                    /*
                        * Its almost expected that this will fail, as this is
                        * just a precaution if the frame did actually launch.
                        */
                }
                /* Thrown an exception to stop booking */
                throw new DispatcherException(
                        "stopped dispatching host, " + e);
            }

            return true;
        }
    }
}

