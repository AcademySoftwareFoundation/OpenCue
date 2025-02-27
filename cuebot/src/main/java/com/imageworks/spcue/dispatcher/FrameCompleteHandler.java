
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

package com.imageworks.spcue.dispatcher;

import java.sql.Timestamp;
import java.util.EnumSet;
import java.util.Random;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHost;
import com.imageworks.spcue.dispatcher.commands.DispatchNextFrame;
import com.imageworks.spcue.dispatcher.commands.KeyRunnable;
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

import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.ServiceDao;
import com.imageworks.spcue.grpc.service.Service;
import com.imageworks.spcue.grpc.service.ServiceOverride;

/**
 * The FrameCompleteHandler encapsulates all logic necessary for processing FrameComplete reports
 * from RQD.
 */
public class FrameCompleteHandler {

    private static final Logger logger = LogManager.getLogger(FrameCompleteHandler.class);

    private static final Random randomNumber = new Random();

    private HostManager hostManager;
    private JobManager jobManager;
    private RedirectManager redirectManager;
    private BookingManager bookingManager;
    private DispatchQueue dispatchQueue;
    private BookingQueue bookingQueue;
    private Dispatcher dispatcher;
    private Dispatcher localDispatcher;
    private JobManagerSupport jobManagerSupport;
    private DispatchSupport dispatchSupport;
    private JmsMover jsmMover;

    private WhiteboardDao whiteboardDao;
    private ServiceDao serviceDao;
    private ShowDao showDao;
    private Environment env;

    /*
     * The last time a proc was unbooked for subscription or job balancing. Since there are so many
     * more dispatch threads than booking threads, the dispatcher will over compensate and unbook
     * too many cores if an imbalance occurs. Its better to keep cores running the same place for
     * cache coherence.
     */
    private final AtomicLong lastUnbook = new AtomicLong(0);

    /*
     * The amount of time to wait before unbooking another proc for subscription or job balancing.
     */
    private static final int UNBOOK_EXPIRE_MS = 2500;

    /**
     * Boolean to toggle if this class is accepting data or not.
     */
    private boolean shutdown = false;

    /**
     * Whether or not to satisfy dependents (*_ON_FRAME and *_ON_LAYER) only on Frame success
     */
    private boolean satisfyDependOnlyOnFrameSuccess;

    public boolean getSatisfyDependOnlyOnFrameSuccess() {
        return satisfyDependOnlyOnFrameSuccess;
    }

    public void setSatisfyDependOnlyOnFrameSuccess(boolean satisfyDependOnlyOnFrameSuccess) {
        this.satisfyDependOnlyOnFrameSuccess = satisfyDependOnlyOnFrameSuccess;
    }

    @Autowired
    public FrameCompleteHandler(Environment env) {
        this.env = env;
        satisfyDependOnlyOnFrameSuccess =
                env.getProperty("depend.satisfy_only_on_frame_success", Boolean.class, true);
    }

    /**
     * Handle the given FrameCompleteReport from RQD.
     *
     * @param report
     */
    public void handleFrameCompleteReport(final FrameCompleteReport report) {

        /*
         * A boolean we're going to set to true if we can detect a corrupted data block in Oracle.
         */
        if (isShutdown()) {
            throw new RqdRetryReportException("Error processing the frame complete report, "
                    + "cuebot not accepting packets.");
        }

        try {
            final VirtualProc proc = hostManager.getVirtualProc(report.getFrame().getResourceId());
            final DispatchJob job = jobManager.getDispatchJob(proc.getJobId());
            final LayerDetail layer = jobManager.getLayerDetail(report.getFrame().getLayerId());
            final FrameDetail frameDetail =
                    jobManager.getFrameDetail(report.getFrame().getFrameId());
            final DispatchFrame frame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
            final FrameState newFrameState = determineFrameState(job, layer, frame, report);
            final String key = proc.getJobId() + "_" + report.getFrame().getLayerId() + "_"
                    + report.getFrame().getFrameId();

            // rqd is currently not able to report exit_signal=9 when a frame is killed by
            // the OOM logic. The current solution sets exitStatus to
            // Dispatcher.EXIT_STATUS_MEMORY_FAILURE before killing the frame, this enables
            // auto-retrying frames affected by the logic when they report with a
            // frameCompleteReport. This status retouch ensures a frame complete report is
            // not able to override what has been set by the previous logic.
            int exitStatus = report.getExitStatus();
            if (frameDetail.exitStatus == Dispatcher.EXIT_STATUS_MEMORY_FAILURE) {
                exitStatus = frameDetail.exitStatus;
            }

            if (dispatchSupport.stopFrame(frame, newFrameState, exitStatus,
                    report.getFrame().getMaxRss())) {
                if (dispatcher.isTestMode()) {
                    // Database modifications on a threadpool cannot be captured by the test thread
                    handlePostFrameCompleteOperations(proc, report, job, frame, newFrameState,
                            frameDetail);
                } else {
                    dispatchQueue.execute(new KeyRunnable(key) {
                        @Override
                        public void run() {
                            try {
                                handlePostFrameCompleteOperations(proc, report, job, frame,
                                        newFrameState, frameDetail);
                            } catch (Exception e) {
                                logger.warn("Exception during handlePostFrameCompleteOperations "
                                        + "in handleFrameCompleteReport"
                                        + CueExceptionUtil.getStackTrace(e));
                            }
                        }
                    });
                }
            } else {
                /*
                 * First check if we have a redirect. When a user retries a frame the proc is
                 * redirected back to the same job without checking any other properties.
                 */
                if (redirectManager.hasRedirect(proc)) {
                    dispatchQueue.execute(new KeyRunnable(key) {
                        @Override
                        public void run() {
                            try {
                                redirectManager.redirect(proc);
                            } catch (Exception e) {
                                logger.warn("Exception during redirect in handleFrameCompleteReport"
                                        + CueExceptionUtil.getStackTrace(e));
                            }
                        }
                    });
                } else {
                    dispatchQueue.execute(new KeyRunnable(key) {
                        @Override
                        public void run() {
                            try {
                                dispatchSupport.unbookProc(proc);
                            } catch (Exception e) {
                                logger.warn(
                                        "Exception during unbookProc in handleFrameCompleteReport"
                                                + CueExceptionUtil.getStackTrace(e));
                            }
                        }
                    });
                }
            }
        } catch (EmptyResultDataAccessException e) {
            /*
             * Do not propagate this exception to RQD. This usually means the cue lost connectivity
             * to the host and cleared out the record of the proc. If this is propagated back to
             * RQD, RQD will keep retrying the operation forever.
             */
            logger.info("failed to acquire data needed to " + "process completed frame: "
                    + report.getFrame().getFrameName() + " in job " + report.getFrame().getJobName()
                    + "," + e);
        } catch (Exception e) {

            /*
             * Everything else we kick back to RQD.
             */
            logger.info("failed to acquire data needed " + "to process completed frame: "
                    + report.getFrame().getFrameName() + " in job " + report.getFrame().getJobName()
                    + "," + e);

            throw new RqdRetryReportException("error processing the frame complete "
                    + "report, sending retry message to RQD " + e, e);
        }
    }

    /**
     * Handles frame complete operations other than the actual frame completing.
     *
     * Updates proc time usage counters. Drops dependencies. Sets jobs to the finished state.
     * Optimizes layer memory requirements. Checks for other jobs that might need procs. Unbook proc
     * if it needs to be moved. Check show subscription values.
     *
     * If the proc is not unbooked and moved, its re-dispatched onto the same job.
     *
     * @param proc
     * @param report
     * @param job
     * @param frame
     * @param newFrameState
     */
    public void handlePostFrameCompleteOperations(VirtualProc proc, FrameCompleteReport report,
            DispatchJob job, DispatchFrame frame, FrameState newFrameState,
            FrameDetail frameDetail) {
        try {

            /*
             * The default behavior is to keep the proc on the same job.
             */
            boolean unbookProc = proc.unbooked;

            dispatchSupport.updateUsageCounters(frame, report.getExitStatus());

            boolean isLayerComplete = false;

            if (newFrameState.equals(FrameState.SUCCEEDED) || (!satisfyDependOnlyOnFrameSuccess
                    && newFrameState.equals(FrameState.EATEN))) {
                jobManagerSupport.satisfyWhatDependsOn(frame);
                isLayerComplete = jobManager.isLayerComplete(frame);
                if (isLayerComplete) {
                    jobManagerSupport.satisfyWhatDependsOn((LayerInterface) frame);
                }
            }

            if (newFrameState.equals(FrameState.SUCCEEDED) && !isLayerComplete) {
                /*
                 * If the layer meets some specific criteria then try to update the minimum memory
                 * and tags so it can run on a wider variety of cores, namely older hardware.
                 */
                jobManager.optimizeLayer(frame, report.getFrame().getNumCores(),
                        report.getFrame().getMaxRss(), report.getRunTime());
            }

            /*
             * The final frame can either be Succeeded or Eaten. If you only check if the frame is
             * Succeeded before doing an isJobComplete check, then jobs that finish with the
             * auto-eat flag enabled will not leave the cue.
             */
            if (newFrameState.equals(FrameState.SUCCEEDED)
                    || newFrameState.equals(FrameState.EATEN)) {
                if (jobManager.isJobComplete(job)) {
                    job.state = JobState.FINISHED;
                    jobManagerSupport.queueShutdownJob(job, new Source("natural"), false);
                }
            }

            /*
             * Some exit statuses indicate that a frame was killed by the application due to a
             * memory issue and should be retried. In this case, disable the optimizer and raise the
             * memory by what is specified in the show's service override, service or 2GB.
             */
            if (report.getExitStatus() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
                    || report.getExitSignal() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
                    || frameDetail.exitStatus == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
                    || report.getExitStatus() == Dispatcher.DOCKER_EXIT_STATUS_MEMORY_FAILURE) {
                long increase = CueUtil.GB2;

                // since there can be multiple services, just going for the
                // first service (primary)
                String serviceName = "";
                try {
                    serviceName = frame.services.split(",")[0];
                    ServiceOverride showService = whiteboardDao
                            .getServiceOverride(showDao.findShowDetail(frame.show), serviceName);
                    // increase override is stored in Kb format so convert to Mb
                    // for easier reading. Note: Kb->Mb conversion uses 1024 blocks
                    increase = showService.getData().getMinMemoryIncrease();
                    logger.info("Using " + serviceName + " service show "
                            + "override for memory increase: " + Math.floor(increase / 1024)
                            + "Mb.");
                } catch (NullPointerException e) {
                    logger.info("Frame has no associated services");
                } catch (EmptyResultDataAccessException e) {
                    logger.info(frame.show + " has no service override for " + serviceName + ".");
                    Service service = whiteboardDao.findService(serviceName);
                    increase = service.getMinMemoryIncrease();
                    logger.info("Using service default for mem increase: "
                            + Math.floor(increase / 1024) + "Mb.");
                }

                unbookProc = true;
                jobManager.enableMemoryOptimizer(frame, false);
                jobManager.increaseLayerMemoryRequirement(frame, proc.memoryReserved + increase);
                logger.info("Increased mem usage to: " + (proc.memoryReserved + increase));
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
             * An exit status of FAILED_LAUNCH (256) indicates that the frame could not be launched
             * due to some unforeseen unrecoverable error that is not checked when the launch
             * command is given. The most common cause of this is when the job log directory is
             * removed before the job is complete.
             *
             * Frames that return a 256 are put Frame back into WAITING status
             */

            else if (report.getExitStatus() == FrameExitStatus.FAILED_LAUNCH_VALUE) {
                logger.info("unbooking " + proc + " frame status was failed frame launch.");
                unbookProc = true;
            }

            else if (report.getHost().getNimbyLocked()) {

                if (!proc.isLocalDispatch) {
                    logger.info("unbooking " + proc + " was NIMBY locked.");
                    unbookProc = true;
                }

                /* Update the NIMBY locked state */
                hostManager.setHostLock(proc, LockState.NIMBY_LOCKED, new Source("NIMBY"));
            } else if (report.getHost().getFreeMem() < CueUtil.MB512) {
                /*
                 * Unbook anything on a proc that has only 512MB of free memory left.
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
                    logger.info("the proc " + proc + " is not in the open state.");
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
             * Check to see if the job the proc is currently assigned is still dispatchable.
             */
            if (job.state.equals(JobState.FINISHED)
                    || !dispatchSupport.isJobDispatchable(job, proc.isLocalDispatch)) {

                logger.info("The " + job + " is no longer dispatchable.");
                dispatchSupport.unbookProc(proc);

                /*
                 * Only rebook whole cores that have not been locally dispatched. Rebooking
                 * fractional can cause storms of booking requests that don't have a chance of
                 * finding a suitable frame to run.
                 */
                if (!proc.isLocalDispatch && proc.coresReserved >= 100
                        && dispatchSupport.isCueBookable(job)) {

                    bookingQueue.execute(new DispatchBookHost(
                            hostManager.getDispatchHost(proc.getHostId()), dispatcher, env));
                }

                if (job.state.equals(JobState.FINISHED)) {
                    jsmMover.send(job);
                }
                return;
            }

            /*
             * If the job is marked unbookable and its over its minimum value, we check to see if
             * the proc can be moved to a job that hasn't reached its minimum proc yet.
             *
             * This will handle show balancing in the future.
             */

            if (!proc.isLocalDispatch && randomNumber.nextInt(100) <= Dispatcher.UNBOOK_FREQUENCY
                    && System.currentTimeMillis() > lastUnbook.get()) {

                // First make sure all jobs have their min cores
                // Then check for higher priority jobs
                // If not, rebook this job
                if (job.autoUnbook && proc.coresReserved >= 100) {
                    if (jobManager.isOverMinCores(job)) {
                        try {

                            boolean unbook = dispatchSupport.findUnderProcedJob(job, proc);

                            if (!unbook) {
                                JobDetail jobDetail = jobManager.getJobDetail(job.id);
                                unbook = dispatchSupport.higherPriorityJobExists(jobDetail, proc);
                            }

                            if (unbook) {

                                // Set a new time to allow unbooking.
                                lastUnbook.set(System.currentTimeMillis() + UNBOOK_EXPIRE_MS);

                                logger.info("Transfering " + proc);
                                dispatchSupport.unbookProc(proc);

                                DispatchHost host = hostManager.getDispatchHost(proc.getHostId());

                                bookingQueue.execute(new DispatchBookHost(host, dispatcher, env));
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
                if (!proc.isLocalDispatch && dispatchSupport.hasStrandedCores(proc)
                        && jobManager.isLayerThreadable(frame)
                        && dispatchSupport.isJobBookable(job)) {

                    int stranded_cores = hostManager.getStrandedCoreUnits(proc);
                    if (stranded_cores >= 100) {

                        DispatchHost host = hostManager.getDispatchHost(proc.getHostId());
                        dispatchSupport.strandCores(host, stranded_cores);
                        dispatchSupport.unbookProc(proc);
                        bookingQueue.execute(new DispatchBookHost(host, job, dispatcher, env));
                        return;
                    }
                }

                // Book the next frame of this job on the same proc
                if (proc.isLocalDispatch) {
                    dispatchQueue.execute(new DispatchNextFrame(job, proc, localDispatcher));
                } else {
                    dispatchQueue.execute(new DispatchNextFrame(job, proc, dispatcher));
                }
            } else {
                dispatchSupport.unbookProc(proc, "frame state was " + newFrameState.toString());
            }
        } catch (Exception e) {
            /*
             * At this point, the proc has no place to go. Since we've run into an error its best to
             * just unbook it. You can't handle this with a roll back because the record existed
             * before any transactions started.
             */
            logger.warn("An error occured when procssing " + "frame complete message, "
                    + CueExceptionUtil.getStackTrace(e));
            try {
                dispatchSupport.unbookProc(proc,
                        "an error occured when procssing frame complete message.");
            } catch (EmptyResultDataAccessException ee) {
                logger.info("Failed to find proc to unbook after frame " + "complete message "
                        + CueExceptionUtil.getStackTrace(ee));
            }
        }
    }

    /**
     * Determines the new FrameState for a frame based on values contained in the
     * FrameCompleteReport
     *
     * If the frame is Waiting or Eaten, then it was manually set to that status before the frame
     * was killed. In that case whatever the current state in the DB is the one we want to use.
     *
     * If the frame status is dead or the frame.exitStatus is a non-zero value, and the frame has
     * been retried job.maxRetries times, then the frame is Dead. If the frame has an exit status of
     * 256, that is a non-retry status, the frame is dead.
     *
     * Assuming the two previous checks are not true, then a non-zero exit status sets the frame
     * back to Waiting, while a zero status sets the frame to Succeeded.
     *
     * @param job
     * @param frame
     * @param report
     * @return
     */
    public static final FrameState determineFrameState(DispatchJob job, LayerDetail layer,
            DispatchFrame frame, FrameCompleteReport report) {

        if (EnumSet.of(FrameState.WAITING, FrameState.EATEN).contains(frame.state)) {
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

            long r = System.currentTimeMillis() / 1000;
            long lastUpdate = (r - report.getFrame().getLluTime()) / 60;

            FrameState newState = FrameState.WAITING;
            if (report.getExitStatus() == FrameExitStatus.SKIP_RETRY_VALUE
                    || (job.maxRetries != 0 && report.getExitSignal() == 119)) {
                report = FrameCompleteReport.newBuilder(report)
                        .setExitStatus(FrameExitStatus.SKIP_RETRY_VALUE).build();
                newState = FrameState.WAITING;
                // exemption code 256
            } else if ((report.getExitStatus() == FrameExitStatus.FAILED_LAUNCH_VALUE
                    || report.getExitSignal() == FrameExitStatus.FAILED_LAUNCH_VALUE)
                    && (frame.retries < job.maxRetries)) {
                report = FrameCompleteReport.newBuilder(report)
                        .setExitStatus(report.getExitStatus()).build();
                newState = FrameState.WAITING;
            } else if (job.autoEat) {
                newState = FrameState.EATEN;
                // ETC Time out and LLU timeout
            } else if (layer.timeout_llu != 0 && report.getFrame().getLluTime() != 0
                    && lastUpdate > (layer.timeout_llu - 1)) {
                newState = FrameState.DEAD;
            } else if (layer.timeout != 0 && report.getRunTime() > layer.timeout * 60) {
                newState = FrameState.DEAD;
            } else if (report.getRunTime() > Dispatcher.FRAME_TIME_NO_RETRY) {
                newState = FrameState.DEAD;
            } else if (frame.retries >= job.maxRetries) {
                if (!(report.getExitStatus() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
                        || report.getExitSignal() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
                        || report.getExitStatus() == Dispatcher.DOCKER_EXIT_STATUS_MEMORY_FAILURE))
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

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public RedirectManager getRedirectManager() {
        return redirectManager;
    }

    public void setRedirectManager(RedirectManager redirectManager) {
        this.redirectManager = redirectManager;
    }

    public DispatchQueue getDispatchQueue() {
        return dispatchQueue;
    }

    public void setDispatchQueue(DispatchQueue dispatchQueue) {
        this.dispatchQueue = dispatchQueue;
    }

    public BookingQueue getBookingQueue() {
        return bookingQueue;
    }

    public void setBookingQueue(BookingQueue bookingQueue) {
        this.bookingQueue = bookingQueue;
    }

    public Dispatcher getDispatcher() {
        return dispatcher;
    }

    public void setDispatcher(Dispatcher dispatcher) {
        this.dispatcher = dispatcher;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public Dispatcher getLocalDispatcher() {
        return localDispatcher;
    }

    public void setLocalDispatcher(Dispatcher localDispatcher) {
        this.localDispatcher = localDispatcher;
    }

    public BookingManager getBookingManager() {
        return bookingManager;
    }

    public void setBookingManager(BookingManager bookingManager) {
        this.bookingManager = bookingManager;
    }

    public JmsMover getJmsMover() {
        return jsmMover;
    }

    public void setJmsMover(JmsMover jsmMover) {
        this.jsmMover = jsmMover;
    }

    public WhiteboardDao getWhiteboardDao() {
        return whiteboardDao;
    }

    public void setWhiteboardDao(WhiteboardDao whiteboardDao) {
        this.whiteboardDao = whiteboardDao;
    }

    public ServiceDao getServiceDao() {
        return serviceDao;
    }

    public void setServiceDao(ServiceDao serviceDao) {
        this.serviceDao = serviceDao;
    }

    public ShowDao getShowDao() {
        return showDao;
    }

    public void setShowDao(ShowDao showDao) {
        this.showDao = showDao;
    }

}
