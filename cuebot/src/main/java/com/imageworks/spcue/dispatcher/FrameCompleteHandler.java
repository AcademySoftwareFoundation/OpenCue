
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

import java.util.EnumSet;
import java.util.Random;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHost;
import com.imageworks.spcue.dispatcher.commands.DispatchNextFrame;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.job.FrameExitStatus;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.service.BookingManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JmsMover;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.util.CueExceptionUtil;
import com.imageworks.spcue.util.CueUtil;
import org.springframework.stereotype.Component;

/**
 * The FrameCompleteHandler encapsulates all logic necessary for processing
 * FrameComplete reports from RQD.
 */
@Component
public class FrameCompleteHandler {

    private static final Logger logger = Logger.getLogger(FrameCompleteHandler.class);

    private static final Random randomNumber = new Random();

    @Autowired
    private HostManager hostManager;

    @Autowired
    private JobManager jobManager;

    @Autowired
    private RedirectManager redirectManager;

    @Autowired
    private BookingManager bookingManager;

    @Autowired
    private DispatchQueue dispatchQueue;

    @Autowired
    private BookingQueue bookingQueue;

    @Autowired
    private Dispatcher dispatcher;

    @Autowired
    private Dispatcher localDispatcher;

    @Autowired
    private JobManagerSupport jobManagerSupport;

    @Autowired
    private DispatchSupport dispatchSupport;

    @Autowired
    private JmsMover jsmMover;

    /*
     * The last time a proc was unbooked for subscription or job balancing.
     * Since there are so many more dispatch threads than booking threads, the
     * dispatcher will over compensate and unbook too many cores if an imbalance
     * occurs. Its better to keep cores running the same place for cache
     * coherence.
     */
    private final AtomicLong lastUnbook = new AtomicLong(0);

    /*
     * The amount of time to wait before unbooking another proc for subscription
     * or job balancing.
     */
    private static final int UNBOOK_EXPIRE_MS = 2500;

    /**
     * Boolean to toggle if this class is accepting data or not.
     */
    private boolean shutdown = false;

    /**
     * Handle the given FrameCompleteReport from RQD.
     *
     * @param report
     */
    public void handleFrameCompleteReport(final FrameCompleteReport report) {

        /*
         * A boolean we're going to set to true if we can detect
         * a corrupted data block in Oracle.
         */
        if (isShutdown()) {
            throw new RqdRetryReportException(
                    "Error processing the frame complete report, " +
                    "cuebot not accepting packets.");
        }

        try {

            final VirtualProc proc;

            try {

                proc = hostManager.getVirtualProc(
                        report.getFrame().getResourceId());
            }
            catch (EmptyResultDataAccessException e) {
                /*
                 * Do not propagate this exception to RQD.  This
                 * usually means the cue lost connectivity to
                 * the host and cleared out the record of the proc.
                 * If this is propagated back to RQD, RQD will
                 * keep retrying the operation forever.
                 */
                logger.info("failed to acquire data needed to " +
                        "process completed frame: " +
                        report.getFrame().getFrameName() + " in job " +
                        report.getFrame().getJobName() + "," + e);
                return;
            }

            final DispatchJob job = jobManager.getDispatchJob(proc.getJobId());
            final DispatchFrame frame = jobManager.getDispatchFrame(
                    report.getFrame().getFrameId());
            final FrameState newFrameState = determineFrameState(job,
                    frame, report);

            if (dispatchSupport.stopFrame(frame, newFrameState, report.getExitStatus(),
                    report.getFrame().getMaxRss())) {
                dispatchQueue.execute(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            handlePostFrameCompleteOperations(proc, report, job, frame,
                                    newFrameState);
                        } catch (Exception e) {
                            logger.warn("Exception during handlePostFrameCompleteOperations " +
                                    "in handleFrameCompleteReport" + CueExceptionUtil.getStackTrace(e));
                        }
                    }
                });
            }
            else {
                /*
                 * First check if we have a redirect.  When a user
                 * retries a frame the proc is redirected back
                 * to the same job without checking any other
                 * properties.
                 */
                if (redirectManager.hasRedirect(proc)) {
                    dispatchQueue.execute(new Runnable() {
                        @Override
                        public void run() {
                            try {
                                redirectManager.redirect(proc);
                            } catch (Exception e) {
                                logger.warn("Exception during redirect in handleFrameCompleteReport" +
                                        CueExceptionUtil.getStackTrace(e));
                            }
                        }
                    });
                }
                else {
                    dispatchQueue.execute(new Runnable() {
                        @Override
                        public void run() {
                            try {
                                dispatchSupport.unbookProc(proc);
                            } catch (Exception e) {
                                logger.warn("Exception during unbookProc in handleFrameCompleteReport" +
                                        CueExceptionUtil.getStackTrace(e));
                            }
                        }
                    });
                }
            }
        }
        catch (Exception e) {

            /*
             * Everything else we kick back to RQD.
             */
            logger.info("failed to acquire data needed " +
                    "to process completed frame: " +
                    report.getFrame().getFrameName() + " in job " +
                    report.getFrame().getJobName() + "," + e);

            throw new RqdRetryReportException("error processing the frame complete " +
                    "report, sending retry message to RQD " + e, e);
        }
    }

    /**
     * Handles frame complete operations other than the actual frame
     * completing.
     *
     * Updates proc time usage counters.
     * Drops dependencies.
     * Sets jobs to the finished state.
     * Optimizes layer memory requirements.
     * Checks for other jobs that might need procs.
     * Unbook proc if it needs to be moved.
     * Check show subscription values.
     *
     * If the proc is not unbooked and moved, its re-dispatched onto the same job.
     *
     * @param proc
     * @param report
     * @param job
     * @param frame
     * @param newFrameState
     */
    public void handlePostFrameCompleteOperations(VirtualProc proc,
            FrameCompleteReport report, DispatchJob job, DispatchFrame frame,
            FrameState newFrameState) {
        try {

            /*
             * The default behavior is to keep the proc on the same.
             */
            boolean unbookProc = proc.unbooked;

            dispatchSupport.updateUsageCounters(frame, report.getExitStatus());

            if (newFrameState.equals(FrameState.SUCCEEDED)) {
                jobManagerSupport.satisfyWhatDependsOn(frame);
                if (jobManager.isLayerComplete(frame)) {
                    jobManagerSupport.satisfyWhatDependsOn((LayerInterface) frame);
                } else {
                    /*
                     * If the layer meets some specific criteria then try to
                     * update the minimum memory and tags so it can run on a
                     * wider variety of cores, namely older hardware.
                     */
                    jobManager.optimizeLayer(frame, report.getFrame().getNumCores(),
                            report.getFrame().getMaxRss(), report.getRunTime());
                }
            }

            /*
             * The final frame can either be Succeeded or Eaten. If you only
             * check if the frame is Succeeded before doing an isJobComplete
             * check, then jobs that finish with the auto-eat flag enabled will
             * not leave the cue.
             */
            if (newFrameState.equals(FrameState.SUCCEEDED)
                    || newFrameState.equals(FrameState.EATEN)) {
                if (jobManager.isJobComplete(job)) {
                    job.state = JobState.FINISHED;
                    jobManagerSupport.queueShutdownJob(job, new Source(
                            "natural"), false);
                }
            }

            /*
             * An exit status of 33 indicates that the frame was killed by the
             * application due to a memory issue and should be retried. In this
             * case, disable the optimizer and raise the memory by 2GB.
             */
            if (report.getExitStatus() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
                    || report.getExitSignal() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE) {
                unbookProc = true;
                jobManager.enableMemoryOptimizer(frame, false);
                jobManager.increaseLayerMemoryRequirement(frame,
                        proc.memoryReserved + CueUtil.GB2);
            }

            /*
             * Check for local dispatching.
             */

            if (proc.isLocalDispatch) {

                if (!bookingManager.hasLocalHostAssignment(proc)) {
                    logger.info("the proc " + proc + " no longer has a local assignment.");
                    unbookProc = true;
                }
            }

            /*
             * An exit status of NO_RETRY (256) indicates that the frame could
             * not be launched due to some unforeseen unrecoverable error that
             * is not checked when the launch command is given. The most common
             * cause of this is when the job log directory is removed before the
             * job is complete.
             *
             * Frames that return a 256 are not automatically retried.
             */

            else if (report.getExitStatus() == FrameExitStatus.NO_RETRY_VALUE) {
                logger.info("unbooking " + proc + " frame status was no-retry.");
                unbookProc = true;
            }

            else if (report.getHost().getNimbyLocked()) {

                if (!proc.isLocalDispatch) {
                    logger.info("unbooking " + proc + " was NIMBY locked.");
                    unbookProc = true;
                }

                /* Update the NIMBY locked state */
                hostManager.setHostLock(proc, LockState.NIMBY_LOCKED,
                        new Source("NIMBY"));
            } else if (report.getHost().getFreeMem() < CueUtil.MB512) {
                /*
                 * Unbook anything on a proc that has only 512MB of free memory
                 * left.
                 */
                logger.info("unbooking" + proc + " was low was memory ");
                unbookProc = true;
            } else if (dispatchSupport.isShowOverBurst(proc)) {
                /*
                 * Unbook the proc if the show is over burst.
                 */
                logger.info("show using proc " + proc + " is over burst.");
                unbookProc = true;
            } else if (!hostManager.isHostUp(proc)) {

                logger.info("the proc " + proc + " is not in the update state.");
                unbookProc = true;
            } else if (hostManager.isLocked(proc)) {
                if (!proc.isLocalDispatch) {
                    logger.info("the proc " + proc
                            + " is not in the open state.");
                    unbookProc = true;
                }
            } else if (redirectManager.hasRedirect(proc)) {

                logger.info("the proc " + proc + " has been redirected.");

                if (redirectManager.redirect(proc)) {
                    return;
                }
            }

            /*
             * If the proc is unbooked at this point, then unbook it and return.
             */
            if (unbookProc) {
                dispatchSupport.unbookProc(proc);
                return;
            }

            /*
             * Check to see if the job the proc is currently assigned is still
             * dispatchable.
             */
            if (job.state.equals(JobState.FINISHED)
                    || !dispatchSupport.isJobDispatchable(job,
                            proc.isLocalDispatch)) {

                logger.info("The " + job + " is no longer dispatchable.");
                dispatchSupport.unbookProc(proc);

                /*
                 * Only rebook whole cores that have not been locally
                 * dispatched. Rebooking fractional can cause storms of booking
                 * requests that don't have a chance of finding a suitable frame
                 * to run.
                 */
                if (!proc.isLocalDispatch && proc.coresReserved >= 100
                        && dispatchSupport.isCueBookable(job)) {

                    bookingQueue.execute(new DispatchBookHost(hostManager
                            .getDispatchHost(proc.getHostId()), dispatcher));
                }

                if (job.state.equals(JobState.FINISHED)) {
                    jsmMover.send(job);
                }
                return;
            }

            /*
             * If the job is marked unbookable and its over its minimum value,
             * we check to see if the proc can be moved to a job that hasn't
             * reached its minimum proc yet.
             *
             * This will handle show balancing in the future.
             */

            if (!proc.isLocalDispatch
                    && randomNumber.nextInt(100) <= Dispatcher.UNBOOK_FREQUENCY
                    && System.currentTimeMillis() > lastUnbook.get()) {

                // First make sure all jobs have their min cores
                // Then check for higher priority jobs
                // If not, rebook this job
                if (job.autoUnbook && proc.coresReserved >= 100) {
                    if (jobManager.isOverMinCores(job)) {
                        try {

                            boolean unbook =
                                    dispatchSupport.findUnderProcedJob(job, proc);

                            if (!unbook) {
                                JobDetail jobDetail = jobManager.getJobDetail(job.id);
                                unbook = dispatchSupport.higherPriorityJobExists(jobDetail, proc);
                            }

                            if (unbook) {

                                // Set a new time to allow unbooking.
                                lastUnbook.set(System.currentTimeMillis()
                                        + UNBOOK_EXPIRE_MS);

                                logger.info("Transfering " + proc);
                                dispatchSupport.unbookProc(proc);

                                DispatchHost host =
                                        hostManager.getDispatchHost(proc.getHostId());

                                bookingQueue.execute(
                                        new DispatchBookHost(host, dispatcher));
                                return;
                            }
                        } catch (JobLookupException e) {
                            // wasn't able to find new job
                        }
                    }
                }
            }

            if (newFrameState.equals(FrameState.WAITING)
                    || newFrameState.equals(FrameState.SUCCEEDED)) {

                /*
                 * Check for stranded cores on the host.
                 */
                if (!proc.isLocalDispatch
                        && dispatchSupport.hasStrandedCores(proc)
                        && jobManager.isLayerThreadable(frame)
                        && dispatchSupport.isJobBookable(job)) {

                    int stranded_cores = hostManager.getStrandedCoreUnits(proc);
                    if (stranded_cores >= 100) {

                        DispatchHost host =
                                hostManager.getDispatchHost(proc.getHostId());
                        dispatchSupport.strandCores(host, stranded_cores);
                        dispatchSupport.unbookProc(proc);
                        bookingQueue.execute(new DispatchBookHost(host, job,
                                dispatcher));
                        return;
                    }
                }

                // Book the next frame of this job on the same proc
                if (proc.isLocalDispatch) {
                    dispatchQueue.execute(new DispatchNextFrame(job, proc,
                            localDispatcher));
                } else {
                    dispatchQueue.execute(new DispatchNextFrame(job, proc,
                            dispatcher));
                }
            } else {
                dispatchSupport.unbookProc(proc, "frame state was "
                        + newFrameState.toString());
            }

        } catch (Exception e) {
            /*
             * At this point, the proc has no place to go. Since we've run into
             * an error its best to just unbook it. You can't handle this with a
             * roll back because the record existed before any transactions
             * started.
             */
            logger.warn("An error occured when procssing "
                    + "frame complete message, "
                    + CueExceptionUtil.getStackTrace(e));
            try {
                dispatchSupport.unbookProc(proc,
                        "an error occured when procssing frame complete message.");
            } catch (EmptyResultDataAccessException ee) {
                logger.info("Failed to find proc to unbook after frame "
                        + "complete message " + CueExceptionUtil.getStackTrace(ee));
            }
        }
    }

    /**
     * Determines the new FrameState for a frame based on values contained in
     * the FrameCompleteReport
     *
     * If the frame is Waiting or Eaten, then it was manually set to that status
     * before the frame was killed. In that case whatever the current state in
     * the DB is the one we want to use.
     *
     * If the frame status is dead or the frame.exitStatus is a non-zero value,
     * and the frame has been retried job.maxRetries times, then the frame is
     * Dead. If the frame has an exit status of 256, that is a non-retry status,
     * the frame is dead.
     *
     * Assuming the two previous checks are not true, then a non-zero exit
     * status sets the frame back to Waiting, while a zero status sets the frame
     * to Succeeded.
     *
     * @param job
     * @param frame
     * @param report
     * @return
     */
    public static final FrameState determineFrameState(DispatchJob job, DispatchFrame frame, FrameCompleteReport report) {

        if (EnumSet.of(FrameState.WAITING, FrameState.EATEN).contains(
                frame.state)) {
            return frame.state;
        }
        // Checks for frames that have reached max retries.
        else if (frame.state.equals(FrameState.DEAD)) {
            if (job.autoEat) {
                return FrameState.EATEN;
            } else {
                return FrameState.DEPEND;
            }
        } else if (report.getExitStatus() != 0) {

            FrameState newState = FrameState.WAITING;
            if (report.getExitStatus() == FrameExitStatus.SKIP_RETRY_VALUE
                    || (job.maxRetries != 0 && report.getExitSignal() == 119)) {
                report = FrameCompleteReport.newBuilder(report).setExitStatus(FrameExitStatus.SKIP_RETRY_VALUE).build();
                newState = FrameState.WAITING;
            } else if (job.autoEat) {
                newState = FrameState.EATEN;
            } else if (report.getRunTime() > Dispatcher.FRAME_TIME_NO_RETRY) {
                newState = FrameState.DEAD;
            } else if (frame.retries >= job.maxRetries) {
                if (!(report.getExitStatus() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE || report.getExitSignal() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE))
                    newState = FrameState.DEAD;
            }

            return newState;
        } else {
            return FrameState.SUCCEEDED;
        }
    }

    public boolean isShutdown() {
        return shutdown;
    }

    public synchronized void shutdown() {
        logger.info("Shutting down FrameCompleteHandler.");
        shutdown = true;
    }
}

