
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

import java.util.Collection;
import java.util.List;

import org.apache.log4j.Logger;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.dispatcher.commands.DispatchJobComplete;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.FrameStateSeq;
import com.imageworks.spcue.grpc.job.Order;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.util.CueExceptionUtil;
import com.imageworks.spcue.util.FrameSet;

/**
 * A non-transaction support class for managing jobs.
 */
public class JobManagerSupport {
    private static final Logger logger = Logger.getLogger(JobManagerSupport.class);

    private JobManager jobManager;
    private DependManager dependManager;
    private HostManager hostManager;
    private RqdClient rqdClient;
    private DepartmentManager departmentManager;
    private DispatchSupport dispatchSupport;
    private DispatchQueue manageQueue;
    private RedirectManager redirectManager;
    private EmailSupport emailSupport;
    private FrameSearchFactory frameSearchFactory;

    public void queueShutdownJob(JobInterface job, Source source, boolean isManualKill) {
        manageQueue.execute(new DispatchJobComplete(job, source, isManualKill, this));
    }

    public boolean shutdownJob(JobInterface job, Source source, boolean isManualKill) {

        if (jobManager.shutdownJob(job)) {

            /*
             * Satisfy any dependencies on just the
             * job record, not layers or frames.
             */
            satisfyWhatDependsOn(job);

            if (departmentManager.isManaged(job)) {
                departmentManager.syncJobsWithTask(job);
            }

            if (isManualKill) {

                logger.info(job.getName() + "/" + job.getId() +
                        " is being manually killed by " + source.toString());

                /**
                 * Sleep a bit here in case any frames were
                 * dispatched during the job shutdown process.
                 */
                try {
                    Thread.sleep(3000);
                } catch (InterruptedException e1) {
                    logger.info(job.getName() + "/" + job.getId() +
                            " shutdown thread was interrupted.");
                    Thread.currentThread().interrupt();
                }

                FrameSearchInterface search = frameSearchFactory.create(job);
                FrameSearchCriteria newCriteria = search.getCriteria();
                FrameStateSeq states = newCriteria.getStates().toBuilder()
                        .addFrameStates(FrameState.RUNNING)
                        .build();
                search.setCriteria(newCriteria.toBuilder().setStates(states).build());

                for (FrameInterface frame: jobManager.findFrames(search)) {

                    VirtualProc proc = null;
                    try {
                        proc = hostManager.findVirtualProc(frame);
                    }
                    catch (DataAccessException e) {
                        logger.warn("Unable to find proc to kill frame " + frame +
                                " on job shutdown operation, " + e);
                    }

                    if (manualStopFrame(frame, FrameState.WAITING)) {
                        try {
                            if (proc != null) {
                                kill(proc, source);
                            }
                        } catch (DataAccessException e) {
                            logger.warn("Failed to kill frame " + frame +
                                    " on job shutdown operation, " + e);
                        }
                        catch (Exception e) {
                            logger.warn("error killing frame: " + frame);
                        }
                    }
                }
            }

            /*
             * Send mail after all frames have been stopped or else the email
             * will have inaccurate numbers.
             */
            emailSupport.sendShutdownEmail(job);

            return true;
        }

        return false;
    }

    public void reorderJob(JobInterface job, FrameSet frameSet, Order order) {
        List<LayerInterface> layers = jobManager.getLayers(job);
        for (LayerInterface layer: layers) {
            jobManager.reorderLayer(layer, frameSet, order);
        }
    }

    public void reorderLayer(LayerInterface layer, FrameSet frameSet, Order order) {
        jobManager.reorderLayer(layer, frameSet, order);
    }

    public void staggerJob(JobInterface job, String range, int stagger) {
        List<LayerInterface> layers = jobManager.getLayers(job);
        for (LayerInterface layer: layers) {
            jobManager.staggerLayer(layer, range, stagger);
        }
    }

    public void staggerLayer(LayerInterface layer, String range, int stagger) {
        jobManager.staggerLayer(layer, range, stagger);
    }

    public void satisfyWhatDependsOn(FrameInterface frame) {
        List<LightweightDependency> depends = dependManager.getWhatDependsOn(frame);
        logger.info("satisfying " + depends.size() +
                " depends that are waiting on frame " + frame.getName());
        for (LightweightDependency depend: depends) {
            dependManager.satisfyDepend(depend);
        }
    }

    public void satisfyWhatDependsOn(LayerInterface layer) {
        List<LightweightDependency> depends = dependManager.getWhatDependsOn(layer);
        logger.info("satisfying " + depends.size() +
                " depends that are waiting on layer " + layer.getName());
        for (LightweightDependency depend: dependManager.getWhatDependsOn(layer)) {
            dependManager.satisfyDepend(depend);
        }
    }

    public void satisfyWhatDependsOn(JobInterface job) {
        List<LightweightDependency> depends = dependManager.getWhatDependsOn(job);
        logger.info("satisfying " + depends.size() +
                " depends that are waiting on job " + job.getName());
        for (LightweightDependency depend: dependManager.getWhatDependsOn(job)) {
            dependManager.satisfyDepend(depend);
        }
    }

    public void satisfyWhatDependsOn(JobInterface job, DependTarget target) {
        for (LightweightDependency depend: dependManager.getWhatDependsOn(job, target)) {
            dependManager.satisfyDepend(depend);
        }
    }

    public void satisfyWhatDependsOn(FrameSearchInterface request) {
        for (FrameInterface frame: jobManager.findFrames(request)) {
            for (LightweightDependency depend: dependManager.getWhatDependsOn(frame)) {
                dependManager.satisfyDepend(depend);
            }
        }
    }

    public boolean isJobComplete(JobInterface job) {
        return jobManager.isJobComplete(job);
    }

    /*
     * Destructive functions require a extra Source argument which contains
     * information about the user making the call. This information is
     * propagated down to the frame log file.
     *
     * There are three main destructive functions.
     * kill, retry, and eat.
     *
     * Before a frame is retried or eaten, the new frame state must be
     * set and committed to the DB before the call to RQD is made to
     * actually kill the frame. This will tell the dispatcher what
     * to do with the frame when RQD sends in the FrameCompleteReport.
     *
     * See RqdReportManagerService.determineFrameState
     */


    /**
     * Kill the specified frame.  If RQD throws back an
     * exception, the proc is considered lost and is
     * manually removed.
     *
     * @param p
     * @param source
     */
    public void kill(VirtualProc p, Source source) {
        try {
            rqdClient.killFrame(p, source.toString());
        }
        catch (java.lang.Throwable e) {
            dispatchSupport.lostProc(p, "clearing due to failed kill," +
                    p.getName() + "," + e, Dispatcher.EXIT_STATUS_FAILED_KILL);
        }
    }

    /**
     * Kill a list procs.  If RQD throws back an
     * exception, the proc is considered lost and is
     * manually removed.
     *
     * @param procs
     * @param source
     */
    public void kill(Collection<VirtualProc> procs, Source source) {
        for (VirtualProc p: procs) {
            try {
                rqdClient.killFrame(p, source.toString());
            }
            catch (java.lang.Throwable e) {
                dispatchSupport.lostProc(p, "clearing due to failed kill," +
                        p.getName() + "," + e, Dispatcher.EXIT_STATUS_FAILED_KILL);
            }
        }
    }

    /**
     * Kills a frame.  This is a convenience method for when you have
     * a reference to the Frame and
     *
     * @param frame
     * @param source
     */
    public void kill(FrameInterface frame, Source source) {
        kill(hostManager.findVirtualProc(frame), source);
    }

    /**
     * Unbook and optionally kill all procs that match the specified
     * search criteria.
     *
     * @param r
     * @param killProc
     * @param source
     * @return
     */
    public int unbookProcs(ProcSearchInterface r, boolean killProc, Source source) {
        List<VirtualProc> procs = hostManager.findBookedVirtualProcs(r);
        for (VirtualProc proc: procs) {
            unbookProc(proc, killProc, source);
        }
        return procs.size();
    }

    /**
     * Unbook and optionally kill all procs that match the specified
     * search criteria.
     *
     * @param proc
     * @param killProc
     * @param source
     * @return
     */
    public void unbookProc(VirtualProc proc, boolean killProc, Source source) {
        hostManager.unbookProc(proc);
        if (killProc) {
            kill(proc, source);
        }
    }

    /**
     * Kill procs and optionally unbook them as well.
     *
     * @param host
     * @param source
     * @param unbook
     */
    public void killProcs(HostInterface host, Source source, boolean unbook) {

        List<VirtualProc> procs = hostManager.findVirtualProcs(host);

        if (unbook) {
            hostManager.unbookVirtualProcs(procs);
        }

        for (VirtualProc proc: procs) {
            kill(proc, source);
        }
    }

    /**
     * Kill procs and optionally unbook them as well.
     *
     * @param r
     * @param source
     * @param unbook
     */
    public void killProcs(FrameSearchInterface r, Source source, boolean unbook) {

        FrameSearchCriteria newCriteria =
                r.getCriteria().toBuilder().setStates(FrameStateSeq.newBuilder().build()).build();
        r.setCriteria(newCriteria);

        List<VirtualProc> procs = hostManager.findVirtualProcs(r);

        if (unbook) {
            hostManager.unbookVirtualProcs(procs);
        }

        for (VirtualProc proc: procs) {
            kill(proc, source);
        }
    }

    /**
     * Kill procs and optionally unbook them as well.
     *
     * @param job
     * @param source
     * @param unbook
     */
    public void killProcs(JobInterface job, Source source, boolean unbook) {
        List<VirtualProc> procs = hostManager.findVirtualProcs(frameSearchFactory.create(job));
        if (unbook) {
            hostManager.unbookVirtualProcs(procs);
        }

        for (VirtualProc proc: procs) {
            kill(proc, source);
        }
    }

    /**
     * Retry frames that match the specified FrameSearch request.
     *
     * @param request
     * @param source
     */
    public void retryFrames(FrameSearchInterface request, Source source) {
        for (FrameInterface frame: jobManager.findFrames(request)) {
            try {
                retryFrame(frame, source);
            } catch (Exception e) {
                CueExceptionUtil.logStackTrace("Failed to retry frame " + frame +
                        " from source " + source, e);
            }
        }
    }

    /**
     * Retry a single frame.
     *
     * @param frame
     * @param source
     */
    public void retryFrame(FrameInterface frame, Source source) {
        /**
         * Have to find the proc before we stop the frame.
         */
        VirtualProc proc = null;
        try {
            proc = hostManager.findVirtualProc(frame);
        } catch (EmptyResultDataAccessException e) {
            logger.info("failed to obtain information for " +
                    "proc running on frame: " + frame);
        }

        if (manualStopFrame(frame, FrameState.WAITING)) {
            if (proc != null) {
                redirectManager.addRedirect(proc, (JobInterface) proc, false, source);
                kill(proc, source);
            }
        }
        else {
            jobManager.updateFrameState(frame, FrameState.WAITING);
        }

        /**
         * If a frame is retried that was part of a dependency, that
         * dependency should become active again.
         */

        // Handle FrameOnFrame depends.
        for (LightweightDependency depend: dependManager.getWhatDependsOn(
                frame, false)) {
            dependManager.unsatisfyDepend(depend);
        }

        // Handle LayerOnLayer depends.
        for (LightweightDependency depend: dependManager.getWhatDependsOn(
                (LayerInterface) frame, false)) {
            dependManager.unsatisfyDepend(depend);
        }

        // set the job back to pending.
        jobManager.updateJobState(jobManager.getJob(frame.getJobId()), JobState.PENDING);

    }

    /**
     * Eat frames that match the specified FrameSearch.  Eaten
     * frames are considered "Succeeded" by the dispatcher.
     * A Job with all eaten frames will leave the cue.
     *
     * @param request
     * @param source
     */
    public void eatFrames(FrameSearchInterface request, Source source) {
        for (FrameInterface frame: jobManager.findFrames(request)) {
            eatFrame(frame, source);
        }
    }

    /**
     * Eat the specified frame.  Eaten frames are
     * considered "Succeeded" by the dispatcher.  A Job
     * with all eaten frames will leave the cue.
     *
     * @param frame
     * @param source
     */
    public void eatFrame(FrameInterface frame, Source source) {
        /**
         * Have to find the proc before we stop the frame.
         */
        VirtualProc proc = null;
        try {
            proc = hostManager.findVirtualProc(frame);
        } catch (EmptyResultDataAccessException e) {
            logger.info("failed to obtain information " +
                    "for proc running on frame: " + frame);
        }

        if (manualStopFrame(frame, FrameState.EATEN)) {
            if (proc != null) {
                kill(proc, source);
            }
        }
        else {
            jobManager.updateFrameState(frame, FrameState.EATEN);
        }
        if (jobManager.isJobComplete(frame)) {
            queueShutdownJob(frame, source, false);
        }
    }

    /**
     * Marks the result of the specified frame search as
     * FrameState.Waiting and decrease the depend count to 0
     * no matter how many active depends exists.
     *
     * @param request
     * @param source
     */
    public void markFramesAsWaiting(FrameSearchInterface request, Source source) {
        for (FrameInterface frame: jobManager.findFrames(request)) {
            jobManager.markFrameAsWaiting(frame);
        }
    }

    /**
     * Stops the specified frame. Return true if the call to
     * this method actually stops the frame, ie the state changes
     * from Running to the given state.  Return false if the
     * frame was already stopped.
     *
     * Stopping the frame also removes the link between the frame
     * and the proc. The proc still exists, but, its assigned
     * frame is null.
     *
     * @param frame
     * @param state
     */
    private boolean manualStopFrame(FrameInterface frame, FrameState state) {
        if (dispatchSupport.stopFrame(frame, state,
                state.ordinal() + 500)) {
            dispatchSupport.updateUsageCounters(frame,
                        state.ordinal() + 500);
            logger.info("Manually stopping frame: "+ frame);
            return true;
        }
        return false;
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public RqdClient getRqdClient() {
        return rqdClient;
    }

    public void setRqdClient(RqdClient rqdClient) {
        this.rqdClient = rqdClient;
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }

    public RedirectManager getRedirectManager() {
        return redirectManager;
    }

    public void setRedirectManager(RedirectManager redirectManager) {
        this.redirectManager = redirectManager;
    }

    public EmailSupport getEmailSupport() {
        return emailSupport;
    }

    public void setEmailSupport(EmailSupport emailSupport) {
        this.emailSupport = emailSupport;
    }

    public FrameSearchFactory getFrameSearchFactory() {
        return frameSearchFactory;
    }

    public void setFrameSearchFactory(FrameSearchFactory frameSearchFactory) {
        this.frameSearchFactory = frameSearchFactory;
    }
}

