
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

import java.time.Duration;
import java.util.EnumSet;
import java.util.Map;
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
import com.imageworks.spcue.ExecutionSummary;
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

import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.WhiteboardDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.ServiceDao;
import com.imageworks.spcue.grpc.service.Service;
import com.imageworks.spcue.grpc.service.ServiceOverride;
import com.imageworks.spcue.monitoring.KafkaEventPublisher;
import com.imageworks.spcue.monitoring.MonitoringEventBuilder;
import com.imageworks.spcue.grpc.monitoring.EventType;
import com.imageworks.spcue.grpc.monitoring.FrameEvent;
import com.imageworks.spcue.grpc.monitoring.LayerEvent;
import com.imageworks.spcue.PrometheusMetricsCollector;

/**
 * The FrameCompleteHandler encapsulates all logic necessary for processing FrameComplete reports
 * from RQD.
 */
public class FrameCompleteHandler {

    private static final Logger logger = LogManager.getLogger(FrameCompleteHandler.class);

    private static final Random randomNumber = new Random();

    private static final int DEPEND_MAX_RETRIES = 3;
    private static final long DEPEND_INITIAL_BACKOFF_MS = 100;

    /**
     * What should happen to the proc once the completed frame has been accounted for.
     */
    private enum ProcHealth {
        /** The proc is healthy and can keep running frames. */
        KEEP,
        /** The proc must be unbooked. */
        UNBOOK,
        /** The proc was redirected to another job; nothing else to do. */
        REDIRECTED
    }

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
    private JmsMover jmsMover;

    private WhiteboardDao whiteboardDao;
    private ServiceDao serviceDao;
    private ShowDao showDao;
    private LayerDao layerDao;
    private Environment env;
    private KafkaEventPublisher kafkaEventPublisher;
    private MonitoringEventBuilder monitoringEventBuilder;
    private PrometheusMetricsCollector prometheusMetrics;

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

    /**
     * Exit statuses that defer the whole layer's booking instead of consuming a retry or killing
     * the frame, mapped to how long the layer is deferred. Parsed at startup from
     * dispatcher.layer_delay.rules; empty (the default) disables the automatic backoff.
     */
    private volatile Map<Integer, Duration> delayRules;

    public boolean getSatisfyDependOnlyOnFrameSuccess() {
        return satisfyDependOnlyOnFrameSuccess;
    }

    public void setSatisfyDependOnlyOnFrameSuccess(boolean satisfyDependOnlyOnFrameSuccess) {
        this.satisfyDependOnlyOnFrameSuccess = satisfyDependOnlyOnFrameSuccess;
    }

    public Map<Integer, Duration> getDelayRules() {
        return delayRules;
    }

    /**
     * Replaces the parsed dispatcher.layer_delay.rules. Cuebot sets these once from configuration
     * at startup; this exists so tests can exercise a rule set without standing up a second
     * application context.
     */
    public void setDelayRules(Map<Integer, Duration> delayRules) {
        this.delayRules = delayRules;
    }

    @Autowired
    public FrameCompleteHandler(Environment env) {
        this.env = env;
        satisfyDependOnlyOnFrameSuccess =
                env.getProperty("depend.satisfy_only_on_frame_success", Boolean.class, true);
        delayRules = LayerDelayRules.parse(env.getProperty("dispatcher.layer_delay.rules", ""));
    }

    /**
     * Handle the given FrameCompleteReport from RQD.
     *
     * Stops the frame and queues the post-completion bookkeeping. When the frame was already
     * stopped by another thread the report is stale, and the proc is redirected or unbooked
     * instead. When the proc itself no longer exists the frame may be orphaned; see
     * {@link #finalizeOrphanedFrameComplete}.
     *
     * @param report
     */
    public void handleFrameCompleteReport(final FrameCompleteReport report) {
        if (isShutdown()) {
            throw new RqdRetryReportException("Error processing the frame complete report, "
                    + "cuebot not accepting packets.");
        }

        try {
            final VirtualProc proc;
            try {
                proc = hostManager.getVirtualProc(report.getFrame().getResourceId());
            } catch (EmptyResultDataAccessException e) {
                finalizeOrphanedFrameComplete(report);
                return;
            }

            final String key = proc.getJobId() + "_" + report.getFrame().getLayerId() + "_"
                    + report.getFrame().getFrameId();

            /*
             * Ownership fence: a report may only stop the run of the frame it describes. Stopping a
             * frame clears its proc's assignment in the same transaction, so a reporting proc that
             * no longer holds the reported frame means that run has been superseded: the frame was
             * freed by another actor (retry, eat, lostProc, orphan reaper) and may already be
             * RUNNING again under a different proc. Applying the report anyway would stop the
             * current run and free the frame for yet another booking, sustaining a kill -> report
             * -> free -> rebook cascade. The int_version fence on stopFrame cannot catch this, as
             * it is read fresh below and only covers concurrent writers, not a report from an older
             * run.
             */
            if (proc.frameId == null || !proc.frameId.equals(report.getFrame().getFrameId())) {
                logger.info("Diverting superseded frame complete report for "
                        + report.getFrame().getFrameName() + "; proc " + proc.getProcId() + " on "
                        + proc.hostName + " no longer owns the frame ("
                        + (proc.frameId == null ? "no frame assigned" : "now on " + proc.frameId)
                        + ").");
                if (prometheusMetrics != null) {
                    prometheusMetrics.incrementFrameCompleteSuperseded(
                            proc.frameId == null ? "no_owner" : "other_frame");
                }
                handleStaleReport(proc, report, key);
                return;
            }

            final DispatchJob job = jobManager.getDispatchJob(proc.getJobId());
            final LayerDetail layer = jobManager.getLayerDetail(report.getFrame().getLayerId());
            final FrameDetail frameDetail =
                    jobManager.getFrameDetail(report.getFrame().getFrameId());
            final DispatchFrame frame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
            final FrameState newFrameState =
                    determineFrameState(job, layer, frame, report, frameDetail, delayRules);

            int exitStatus = resolveExitStatus(report, frameDetail);

            if (dispatchSupport.stopFrame(frame, newFrameState, exitStatus,
                    report.getFrame().getMaxRss())) {
                if (dispatcher.isTestMode()) {
                    // Database modifications on a threadpool cannot be captured by the test thread
                    handlePostFrameCompleteOperations(proc, report, job, frame, newFrameState,
                            frameDetail);
                } else {
                    queueDispatchTask(key, "handlePostFrameCompleteOperations",
                            () -> handlePostFrameCompleteOperations(proc, report, job, frame,
                                    newFrameState, frameDetail));
                }
            } else {
                handleStaleReport(proc, report, key);
            }
        } catch (EmptyResultDataAccessException e) {
            /*
             * Do not propagate this exception to RQD. This usually means the cue lost connectivity
             * to the host and cleared out the record of the proc. If this is propagated back to
             * RQD, RQD will keep retrying the operation forever.
             */
            logger.info("failed to acquire data needed to process completed frame: "
                    + report.getFrame().getFrameName() + " in job " + report.getFrame().getJobName()
                    + "," + e);
        } catch (Exception e) {
            /*
             * Everything else we kick back to RQD.
             */
            logger.info("failed to acquire data needed to process completed frame: "
                    + report.getFrame().getFrameName() + " in job " + report.getFrame().getJobName()
                    + "," + e);
            throw new RqdRetryReportException("error processing the frame complete "
                    + "report, sending retry message to RQD " + e, e);
        }
    }

    /**
     * Handles a report whose frame was already stopped by another thread. When a user retries a
     * frame the proc is redirected back to the same job without checking any other properties;
     * otherwise the proc is unbooked.
     *
     * A proc already assigned to a different frame means the report is a resent duplicate of one
     * that was fully processed, and the proc has since booked its next frame; unbooking it here
     * would orphan that frame, so the report is dropped instead. A proc with no frame assignment
     * still goes through redirect/unbook: stopping a frame clears its proc's assignment, so this is
     * the normal state for a proc whose frame was stopped by another actor (eat, retry, kill) and
     * that now needs to be released.
     *
     * The release itself is deferred to {@link #releaseStaleProc}, which re-reads the proc
     * immediately before releasing it and drops the report when that read shows a newer run. A
     * report that gets past the duplicate check is discarded on every path, so it is counted (and a
     * successful report flagged as a lost render result) here, before the release is queued.
     */
    private void handleStaleReport(VirtualProc proc, FrameCompleteReport report, String key) {
        if (proc.frameId != null && !proc.frameId.equals(report.getFrame().getFrameId())) {
            logger.info("Ignoring duplicate frame complete report for "
                    + report.getFrame().getFrameName() + "; proc " + proc.getProcId()
                    + " has already moved on to frame " + proc.frameId + ".");
            return;
        }

        FrameDetail frameDetail = null;
        try {
            frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
        } catch (EmptyResultDataAccessException e) {
            // The frame row is gone; fall through and release the proc.
        }

        /*
         * Past the duplicate check above the report is discarded without being applied to its
         * frame, no matter which branch below disposes of the proc, so it is counted (and a
         * successful result flagged as lost) before any of them return.
         */
        if (prometheusMetrics != null) {
            prometheusMetrics.incrementFrameCompleteDropped(report.getExitStatus());
        }
        if (report.getExitStatus() == 0 && frameDetail != null
                && frameDetail.state != FrameState.SUCCEEDED
                && frameDetail.state != FrameState.EATEN) {
            logger.warn("A successful frame complete report for " + report.getFrame().getFrameName()
                    + " in job " + report.getFrame().getJobName() + " from host " + proc.hostName
                    + " could not be applied; the frame is " + frameDetail.state
                    + " and the result of this render is being discarded.");
        }

        queueDispatchTask(key, "releaseStaleProc", () -> releaseStaleProc(proc, report));
    }

    /**
     * Redirects or unbooks a proc whose frame complete report was stale, unless the proc is holding
     * a live run.
     *
     * The proc snapshot handed to {@link #handleStaleReport} can be stale by the time the release
     * decision is made: the dispatcher may since have assigned the proc a newer run, either the
     * reported frame again (stopped and re-dispatched onto this same proc between this report being
     * generated and handled) or a different frame entirely. Releasing the proc deletes its row with
     * no fence on the current assignment, which would orphan that live run, so the proc is re-read
     * here and the report is dropped whenever the fresh read shows any frame assigned; the newer
     * run's own report will release the proc when it ends.
     *
     * The re-read runs on the dispatch queue, immediately before the release it guards, rather than
     * on the report thread: the delete is not fenced on the assignment read, so this narrows the
     * window to the gap between the read and the delete instead of leaving it open for however long
     * the release sat queued. It does not eliminate the window; a proc that books a new frame
     * inside that gap can still be released out from under it.
     */
    private void releaseStaleProc(VirtualProc proc, FrameCompleteReport report) {
        VirtualProc currentProc;
        try {
            currentProc = hostManager.getVirtualProc(proc.getProcId());
        } catch (EmptyResultDataAccessException e) {
            // The proc row is gone; there is nothing left to redirect or unbook.
            return;
        }
        if (currentProc.frameId != null) {
            logger.info("Dropping stale frame complete report for "
                    + report.getFrame().getFrameName() + "; proc " + proc.getProcId()
                    + (report.getFrame().getFrameId().equals(currentProc.frameId)
                            ? " is running a newer instance of the same frame."
                            : " has moved on to frame " + currentProc.frameId + "."));
            return;
        }

        if (redirectManager.hasRedirect(proc)) {
            redirectManager.redirect(proc);
        } else {
            dispatchSupport.unbookProc(proc);
        }
    }

    /**
     * Runs the given task on the dispatch queue, logging instead of propagating any failure.
     */
    private void queueDispatchTask(String key, String taskName, Runnable task) {
        dispatchQueue.execute(new KeyRunnable(key) {
            @Override
            public void run() {
                try {
                    task.run();
                } catch (Exception e) {
                    logger.warn("Exception during " + taskName + " in handleFrameCompleteReport"
                            + CueExceptionUtil.getStackTrace(e));
                }
            }
        });
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
            publishFrameCompleteEvent(report, frame, frameDetail, newFrameState, proc);

            /*
             * The default behavior is to keep the proc on the same job.
             */
            boolean unbookProc = proc.unbooked;

            dispatchSupport.updateUsageCounters(frame, report.getExitStatus());

            applyLayerDelayRule(frame, resolveExitStatus(report, frameDetail), newFrameState);

            if (satisfyDependsAndCompleteLayerAndJob(job, frame, report, newFrameState)) {
                publishLayerCompletedTelemetry(frame);
            }

            if (isMemoryFailure(report, frameDetail)) {
                retryFrameWithRaisedMemory(proc, frame);
                unbookProc = true;
            }

            switch (evaluateProcHealth(proc, report)) {
                case REDIRECTED:
                    return;
                case UNBOOK:
                    unbookProc = true;
                    break;
                case KEEP:
                    break;
            }

            if (unbookProc) {
                dispatchSupport.unbookProc(proc);
                return;
            }

            if (job.state.equals(JobState.FINISHED)
                    || !dispatchSupport.isJobDispatchable(job, proc.isLocalDispatch)) {
                releaseProcFromUndispatchableJob(proc, job);
                return;
            }

            if (maybeTransferProcToNeedierJob(proc, job)) {
                return;
            }

            if (newFrameState.equals(FrameState.WAITING)
                    || newFrameState.equals(FrameState.SUCCEEDED)) {
                bookNextFrameOnProc(proc, job, frame);
            } else {
                dispatchSupport.unbookProc(proc, "frame state was " + newFrameState.toString());
            }
        } catch (Exception e) {
            /*
             * At this point, the proc has no place to go. Since we've run into an error its best to
             * just unbook it. You can't handle this with a roll back because the record existed
             * before any transactions started.
             */
            logger.warn("An error occurred when processing frame complete message, "
                    + CueExceptionUtil.getStackTrace(e));
            try {
                dispatchSupport.unbookProc(proc,
                        "an error occurred when processing frame complete message.");
            } catch (EmptyResultDataAccessException ee) {
                logger.info("Failed to find proc to unbook after frame complete message "
                        + CueExceptionUtil.getStackTrace(ee));
            }
        }
    }

    /**
     * Publishes layer-completion metrics and events. Called only on the proc-backed path; the
     * orphaned path intentionally omits it. Safe to run after
     * {@link #satisfyDependsAndCompleteLayerAndJob}: optimizeLayer is skipped when the layer is
     * complete, so nothing has mutated the layer state read here.
     */
    private void publishLayerCompletedTelemetry(DispatchFrame frame) {
        boolean kafkaEnabled = kafkaEventPublisher != null && kafkaEventPublisher.isEnabled();
        if (prometheusMetrics == null && !kafkaEnabled) {
            return;
        }
        LayerDetail layerDetail = jobManager.getLayerDetail(frame.getLayerId());

        if (prometheusMetrics != null) {
            ExecutionSummary layerSummary = jobManager.getExecutionSummary((LayerInterface) frame);
            prometheusMetrics.recordLayerMaxRuntime(layerSummary.highFrameSec, frame.show,
                    frame.shot, layerDetail.type.toString());
            if (layerSummary.highMemoryKb > 0) {
                prometheusMetrics.recordLayerMaxMemory(layerSummary.highMemoryKb * 1024L,
                        frame.show, frame.shot, layerDetail.type.toString());
            }
        }

        if (kafkaEnabled) {
            LayerEvent layerEvent = monitoringEventBuilder.buildLayerEvent(
                    EventType.LAYER_COMPLETED, layerDetail, frame.getName(), frame.show);
            kafkaEventPublisher.publishLayerEvent(layerEvent);
        }
    }

    /**
     * Whether the reported exit indicates the frame was killed by the application due to a memory
     * issue and should be retried with more memory.
     */
    private static boolean isMemoryFailure(FrameCompleteReport report) {
        return report.getExitStatus() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
                || report.getExitSignal() == Dispatcher.EXIT_STATUS_MEMORY_FAILURE
                || report.getExitStatus() == Dispatcher.DOCKER_EXIT_STATUS_MEMORY_FAILURE;
    }

    /**
     * Same as {@link #isMemoryFailure(FrameCompleteReport)}, but also honors a memory failure
     * status stored on the frame by a Cuebot-initiated memory kill (see
     * {@link #resolveExitStatus}).
     */
    private static boolean isMemoryFailure(FrameCompleteReport report, FrameDetail frameDetail) {
        return isMemoryFailure(report)
                || frameDetail.exitStatus == Dispatcher.EXIT_STATUS_MEMORY_FAILURE;
    }

    /**
     * Prepares a memory-killed frame for retry: disables the memory optimizer and raises the layer
     * memory requirement by the amount from the show's service override, the service default, or
     * 2GB.
     */
    private void retryFrameWithRaisedMemory(VirtualProc proc, DispatchFrame frame) {
        long increase = getMemoryIncrease(frame);
        jobManager.enableMemoryOptimizer(frame, false);
        jobManager.increaseLayerMemoryRequirement(frame, proc.memoryReserved + increase);
        logger.info("Increased mem usage to: " + (proc.memoryReserved + increase));
    }

    private long getMemoryIncrease(DispatchFrame frame) {
        long increase = CueUtil.GB2;
        // Since there can be multiple services, just going for the first service (primary).
        String serviceName = "";
        try {
            serviceName = frame.services.split(",")[0];
            ServiceOverride showService = whiteboardDao
                    .getServiceOverride(showDao.findShowDetail(frame.show), serviceName);
            // The increase is stored in Kb; convert to Mb for easier reading.
            increase = showService.getData().getMinMemoryIncrease();
            logger.info("Using " + serviceName + " service show " + "override for memory increase: "
                    + Math.floor(increase / 1024) + "Mb.");
        } catch (NullPointerException e) {
            logger.info("Frame has no associated services");
        } catch (EmptyResultDataAccessException e) {
            logger.info(frame.show + " has no service override for " + serviceName + ".");
            Service service = whiteboardDao.findService(serviceName);
            increase = service.getMinMemoryIncrease();
            logger.info("Using service default for mem increase: " + Math.floor(increase / 1024)
                    + "Mb.");
        }
        return increase;
    }

    /**
     * Decides whether the proc can keep running frames or must be unbooked, and applies any host
     * side effects (NIMBY lock state, redirects) along the way.
     *
     * A local dispatch proc is only checked for a valid local host assignment. All other procs are
     * unbooked when the frame failed to launch, the host is NIMBY locked, low on memory, down or
     * locked, or the show is over burst. As a last resort a pending redirect is honored.
     */
    private ProcHealth evaluateProcHealth(VirtualProc proc, FrameCompleteReport report) {
        if (proc.isLocalDispatch) {
            if (!bookingManager.hasLocalHostAssignment(proc)) {
                logger.info("the proc " + proc + " no longer has a local assignment.");
                return ProcHealth.UNBOOK;
            }
            return ProcHealth.KEEP;
        }

        /*
         * An exit status of FAILED_LAUNCH (256) indicates that the frame could not be launched due
         * to some unforeseen unrecoverable error that is not checked when the launch command is
         * given. The most common cause of this is when the job log directory is removed before the
         * job is complete. Frames that return a 256 are put back into WAITING status.
         */
        if (report.getExitStatus() == FrameExitStatus.FAILED_LAUNCH_VALUE) {
            logger.info("unbooking " + proc + " frame status was failed frame launch.");
            return ProcHealth.UNBOOK;
        }
        if (report.getHost().getNimbyLocked()) {
            logger.info("unbooking " + proc + " was NIMBY locked.");
            hostManager.setHostLock(proc, LockState.NIMBY_LOCKED, new Source("NIMBY"));
            return ProcHealth.UNBOOK;
        }
        if (report.getHost().getFreeMem() < CueUtil.MB512) {
            logger.info("unbooking " + proc + " was low on memory.");
            return ProcHealth.UNBOOK;
        }
        if (dispatchSupport.isShowOverBurst(proc)) {
            logger.info("show using proc " + proc + " is over burst.");
            return ProcHealth.UNBOOK;
        }
        if (!hostManager.isHostUp(proc)) {
            logger.info("the proc " + proc + " is not in the update state.");
            return ProcHealth.UNBOOK;
        }
        if (hostManager.isLocked(proc)) {
            logger.info("the proc " + proc + " is not in the open state.");
            return ProcHealth.UNBOOK;
        }
        if (redirectManager.hasRedirect(proc)) {
            logger.info("the proc " + proc + " has been redirected.");
            if (redirectManager.redirect(proc)) {
                return ProcHealth.REDIRECTED;
            }
        }
        return ProcHealth.KEEP;
    }

    /**
     * Unbooks a proc whose job is finished or no longer dispatchable, rebooks the host onto other
     * work when possible, and notifies JMS listeners of a finished job.
     */
    private void releaseProcFromUndispatchableJob(VirtualProc proc, DispatchJob job) {
        logger.info("The " + job + " is no longer dispatchable.");
        dispatchSupport.unbookProc(proc);

        /*
         * Only rebook whole cores that have not been locally dispatched. Rebooking fractional cores
         * can cause storms of booking requests that don't have a chance of finding a suitable frame
         * to run.
         */
        if (!proc.isLocalDispatch && proc.coresReserved >= 100
                && dispatchSupport.isCueBookable(job)) {
            bookingQueue.execute(new DispatchBookHost(hostManager.getDispatchHost(proc.getHostId()),
                    dispatcher, env));
        }

        if (job.state.equals(JobState.FINISHED)) {
            jmsMover.send(job);
        }
    }

    /**
     * Occasionally moves the proc to a job that is under its minimum cores or has higher priority.
     * Throttled through lastUnbook because there are many more dispatch threads than booking
     * threads, and unbooking too aggressively would thrash procs that are better left in place.
     *
     * @return true if the proc was unbooked and its host queued for rebooking.
     */
    private boolean maybeTransferProcToNeedierJob(VirtualProc proc, DispatchJob job) {
        if (proc.isLocalDispatch || randomNumber.nextInt(100) > Dispatcher.UNBOOK_FREQUENCY
                || System.currentTimeMillis() <= lastUnbook.get()) {
            return false;
        }
        if (!job.autoUnbook || proc.coresReserved < 100 || !jobManager.isOverMinCores(job)) {
            return false;
        }
        try {
            // First make sure all jobs have their min cores, then check for higher priority jobs.
            boolean unbook = dispatchSupport.findUnderProcedJob(job, proc);
            if (!unbook) {
                JobDetail jobDetail = jobManager.getJobDetail(job.id);
                unbook = dispatchSupport.higherPriorityJobExists(jobDetail, proc);
            }
            if (!unbook) {
                return false;
            }

            // Set a new time to allow unbooking.
            lastUnbook.set(System.currentTimeMillis() + UNBOOK_EXPIRE_MS);

            logger.info("Transferring " + proc);
            dispatchSupport.unbookProc(proc);
            bookingQueue.execute(new DispatchBookHost(hostManager.getDispatchHost(proc.getHostId()),
                    dispatcher, env));
            return true;
        } catch (JobLookupException e) {
            // Wasn't able to find a new job; keep the proc where it is.
            return false;
        }
    }

    /**
     * Books the next frame of the same job on the proc, unless the proc should be released first:
     * on scheduler-managed shows the standalone scheduler owns dispatch, and rebooking here would
     * race it and strand procs with reserved cores; and a host with a whole stranded core is
     * rebooked through the booking queue so the extra cores can be picked up.
     */
    private void bookNextFrameOnProc(VirtualProc proc, DispatchJob job, DispatchFrame frame) {
        // Local dispatches are always Cuebot-managed.
        if (!proc.isLocalDispatch && showDao.isSchedulerManaged(proc.getShowId())) {
            dispatchSupport.unbookProc(proc, "scheduler-managed show, releasing proc");
            return;
        }

        if (!proc.isLocalDispatch && dispatchSupport.hasStrandedCores(proc)
                && jobManager.isLayerThreadable(frame) && dispatchSupport.isJobBookable(job)) {
            int strandedCores = hostManager.getStrandedCoreUnits(proc);
            if (strandedCores >= 100) {
                DispatchHost host = hostManager.getDispatchHost(proc.getHostId());
                dispatchSupport.strandCores(host, strandedCores);
                dispatchSupport.unbookProc(proc);
                bookingQueue.execute(new DispatchBookHost(host, job, dispatcher, env));
                return;
            }
        }

        Dispatcher procDispatcher = proc.isLocalDispatch ? localDispatcher : dispatcher;
        dispatchQueue.execute(new DispatchNextFrame(job, proc, procDispatcher));
    }

    /**
     * Finalize a frame whose backing proc no longer exists.
     *
     * This happens when the proc was removed (unbooked/cleared) while RQD was still finishing the
     * frame, or when a delayed/duplicate report arrives after the run already ended. If the frame
     * is genuinely orphaned, still RUNNING with no proc, this report reflects the authoritative end
     * state of the run and must not be lost. Finalizing it directly records the completion instead
     * of silently dropping it and letting the orphaned-frame reaper reset a successful frame to
     * WAITING to be re-rendered. Otherwise the report is stale and is ignored.
     *
     * Two guards keep this safe: the "no proc assigned" check ensures we never stop a frame a newer
     * proc has since picked up, and stopFrame is version-fenced so a concurrent reset/rebook
     * between our read and our write results in a no-op rather than clobbering the live run.
     *
     * @param report
     */
    private void finalizeOrphanedFrameComplete(FrameCompleteReport report) {
        final DispatchFrame frame;
        final FrameDetail frameDetail;
        final DispatchJob job;
        final LayerDetail layer;
        try {
            frame = jobManager.getDispatchFrame(report.getFrame().getFrameId());
            frameDetail = jobManager.getFrameDetail(report.getFrame().getFrameId());
            job = jobManager.getDispatchJob(frame.getJobId());
            layer = jobManager.getLayerDetail(frame.getLayerId());
        } catch (EmptyResultDataAccessException e) {
            logger.info("Dropping frame complete report for " + report.getFrame().getFrameName()
                    + "; proc and frame/job/layer no longer exist.");
            return;
        }

        if (!frame.state.equals(FrameState.RUNNING)) {
            logger.info("Ignoring stale frame complete report for " + frame.getName()
                    + "; frame is no longer RUNNING (" + frame.state + ").");
            return;
        }

        /*
         * If a proc currently owns this frame, a newer run has already picked it up; this report is
         * from a superseded run and must not stop the live frame.
         */
        try {
            hostManager.findVirtualProc(frame);
            logger.info("Ignoring superseded frame complete report for " + frame.getName()
                    + "; frame is now assigned to another proc.");
            return;
        } catch (EmptyResultDataAccessException e) {
            // No proc owns the frame: it is genuinely orphaned, proceed with finalizing it.
        }

        final int exitStatus = resolveExitStatus(report, frameDetail);
        final FrameState newFrameState =
                determineFrameState(job, layer, frame, report, frameDetail, delayRules);

        if (!dispatchSupport.stopFrame(frame, newFrameState, exitStatus,
                report.getFrame().getMaxRss())) {
            logger.info("Orphaned frame " + frame.getName()
                    + " was already finalized by another thread (version changed).");
            return;
        }

        logger.info("Finalized orphaned frame " + frame.getName() + " (proc was gone) to state "
                + newFrameState + ".");

        final String key = job.getJobId() + "_" + report.getFrame().getLayerId() + "_"
                + report.getFrame().getFrameId();
        if (dispatcher.isTestMode()) {
            handleOrphanedPostFrameComplete(report, job, frame, newFrameState, exitStatus);
        } else {
            queueDispatchTask(key, "handleOrphanedPostFrameComplete",
                    () -> handleOrphanedPostFrameComplete(report, job, frame, newFrameState,
                            exitStatus));
        }
    }

    /**
     * Post-completion work for a frame finalized without a proc (see
     * {@link #finalizeOrphanedFrameComplete}). Covers only the proc-independent steps: usage
     * counters, dependency satisfaction, layer/job completion and layer optimization. Proc-specific
     * steps (unbook/rebook, memory growth, and Kafka events that require the proc) are
     * intentionally skipped since there is no proc to act on. In particular, a memory-failure frame
     * finalized here does not get its layer minimum memory raised, because the increase is based on
     * the memory the proc had reserved; the frame still auto-retries, just at the same memory
     * reservation.
     */
    private void handleOrphanedPostFrameComplete(FrameCompleteReport report, DispatchJob job,
            DispatchFrame frame, FrameState newFrameState, int exitStatus) {
        if (prometheusMetrics != null) {
            prometheusMetrics.recordFrameCompleted(newFrameState.name(), frame.show, frame.shot);
        }

        dispatchSupport.updateUsageCounters(frame, report.getExitStatus());

        applyLayerDelayRule(frame, exitStatus, newFrameState);

        satisfyDependsAndCompleteLayerAndJob(job, frame, report, newFrameState);
    }

    /**
     * Writes the layer-level backoff for an exit status configured in dispatcher.layer_delay.rules:
     * pushes the layer's start-after gate a configured duration into the future so no frame of the
     * layer re-books while the underlying condition (typically a license shortage) persists. The
     * write is conditional monotonic, so an operator-set later time survives and the burst of
     * reports from a layer's in-flight frames collapses into a single write.
     *
     * Skipped when the frame was EATEN: auto-eat wins over the delay rule, and nothing is going to
     * retry an eaten frame, so a delay would only stretch the eating out and keep the job from
     * finishing.
     *
     * Runs on the dispatch threadpool, so a queue rejection can drop the write. That is acceptable
     * and self-healing: the condition persists, the layer re-books, and the next matching report
     * writes the delay.
     */
    private void applyLayerDelayRule(DispatchFrame frame, int exitStatus,
            FrameState newFrameState) {
        if (newFrameState.equals(FrameState.EATEN)) {
            return;
        }
        Duration backoff = delayRules.get(exitStatus);
        if (backoff == null) {
            return;
        }
        boolean delayed = layerDao.delayLayerForBackoff((LayerInterface) frame, backoff,
                "Automatic backoff: exit status " + exitStatus);
        if (delayed) {
            logger.info("Delayed layer " + frame.getLayerId() + " for " + backoff.toMinutes()
                    + " minutes: exit status " + exitStatus + " on frame " + frame.getName());
            if (prometheusMetrics != null) {
                prometheusMetrics.recordLayerDelay(exitStatus);
            }
        }
    }

    /**
     * Proc-independent frame-completion bookkeeping shared by the normal and orphaned paths:
     * satisfies frame- and layer-level dependencies, optimizes the layer's resource requirements on
     * success, and shuts the job down once it has fully completed. Proc-dependent work (usage
     * counters, unbook/rebook, memory growth, and Kafka/Prometheus telemetry) is intentionally left
     * to the callers.
     *
     * @return whether the frame's layer is now complete, so a caller can run any additional
     *         layer-completion side effects it owns.
     */
    private boolean satisfyDependsAndCompleteLayerAndJob(DispatchJob job, DispatchFrame frame,
            FrameCompleteReport report, FrameState newFrameState) {
        boolean isLayerComplete = false;

        if (newFrameState.equals(FrameState.SUCCEEDED)
                || (!satisfyDependOnlyOnFrameSuccess && newFrameState.equals(FrameState.EATEN))) {
            satisfyDependsWithRetry(() -> jobManagerSupport.satisfyWhatDependsOn(frame),
                    "frame " + frame.getName() + " (id=" + frame.getFrameId() + ")", job.getName(),
                    job.getJobId());

            isLayerComplete = jobManager.isLayerComplete(frame);
            if (isLayerComplete) {
                satisfyDependsWithRetry(
                        () -> jobManagerSupport.satisfyWhatDependsOn((LayerInterface) frame),
                        "layer " + frame.getLayerId(), job.getName(), job.getJobId());
            }
        }

        if (newFrameState.equals(FrameState.SUCCEEDED) && !isLayerComplete) {
            /*
             * If the layer meets some specific criteria then try to update the minimum memory and
             * tags so it can run on a wider variety of cores, namely older hardware.
             */
            jobManager.optimizeLayer(frame, report.getFrame().getNumCores(),
                    report.getFrame().getMaxRss(), report.getRunTime());
        }

        /*
         * The final frame can either be Succeeded or Eaten. If you only check if the frame is
         * Succeeded before doing an isJobComplete check, then jobs that finish with the auto-eat
         * flag enabled will not leave the cue.
         */
        if (newFrameState.equals(FrameState.SUCCEEDED) || newFrameState.equals(FrameState.EATEN)) {
            if (jobManager.isJobComplete(job)) {
                job.state = JobState.FINISHED;
                jobManagerSupport.queueShutdownJob(job, new Source("natural"), false);
            }
        }

        return isLayerComplete;
    }

    /**
     * Selects the exit status to record for a completed frame.
     *
     * This retouch covers the Cuebot-initiated memory kill path
     * ({@link com.imageworks.spcue.dispatcher.commands.DispatchRqdKillFrameMemory}, driven by
     * {@link HostReportHandler}). There, Cuebot asks rqd to kill the frame via a generic kill
     * request, so rqd reports it as an ordinary termination (e.g. SIGTERM/SIGKILL), not as a memory
     * failure. To preserve the memory-kill intent across the report, Cuebot stores
     * {@link Dispatcher#EXIT_STATUS_MEMORY_FAILURE} on the frame before sending the kill; this
     * retouch makes that stored status win over whatever rqd reports so the frame can be
     * auto-retried with raised memory. When the stored status is present it wins, otherwise the
     * status reported by rqd is used.
     *
     * Note: rqd-initiated OOM kills are a separate path and do NOT rely on this retouch. When rqd's
     * own memory-pressure logic kills a frame, it reports
     * exit_signal={@link Dispatcher#EXIT_STATUS_MEMORY_FAILURE} directly, which the memory-retry
     * logic picks up from the report (see {@link #determineFrameState} and
     * {@link #isMemoryFailure(FrameCompleteReport)}).
     */
    public static int resolveExitStatus(FrameCompleteReport report, FrameDetail frameDetail) {
        if (frameDetail.exitStatus == Dispatcher.EXIT_STATUS_MEMORY_FAILURE) {
            return frameDetail.exitStatus;
        }
        return report.getExitStatus();
    }

    /**
     * Determines the new FrameState for a frame based on values contained in the
     * FrameCompleteReport.
     *
     * If the frame is Waiting or Eaten, then it was manually set to that status before the frame
     * was killed. In that case whatever the current state in the DB is the one we want to use.
     *
     * A frame already marked Dead reached max retries and moves on as Eaten (with auto-eat) or
     * Depend. A zero exit status means the frame Succeeded.
     *
     * For a non-zero exit status, the frame goes back to Waiting for a retry unless it is out of
     * retries or timed out, in which case it is Dead, or the job has auto-eat enabled, in which
     * case it is Eaten. Skip-retry frames, frames killed by a NIMBY lock, and memory failures
     * (reported by rqd or stored on the frame by a Cuebot-initiated memory kill, see
     * {@link #resolveExitStatus}) are retried even when the retry count is exhausted.
     *
     * An exit status configured in delayRules (dispatcher.layer_delay.rules) sends the frame back
     * to Waiting unconditionally: the layer-level start-after backoff written by the caller is what
     * prevents an immediate re-book, and the status is excluded from retry counting. Auto-eat still
     * wins over a delay rule, and a delay-rule frame is deliberately immune to the timeout checks
     * below (a matching failure exits in seconds, so timeouts are moot).
     *
     * @param job
     * @param layer
     * @param frame
     * @param report
     * @param frameDetail
     * @param delayRules exit statuses that defer the layer instead of failing the frame
     * @return
     */
    public static final FrameState determineFrameState(DispatchJob job, LayerDetail layer,
            DispatchFrame frame, FrameCompleteReport report, FrameDetail frameDetail,
            Map<Integer, Duration> delayRules) {
        if (EnumSet.of(FrameState.WAITING, FrameState.EATEN).contains(frame.state)) {
            return frame.state;
        }
        if (frame.state.equals(FrameState.DEAD)) {
            return job.autoEat ? FrameState.EATEN : FrameState.DEPEND;
        }
        if (report.getExitStatus() == 0) {
            return FrameState.SUCCEEDED;
        }

        if (report.getExitStatus() == FrameExitStatus.SKIP_RETRY_VALUE
                || (job.maxRetries != 0 && report.getExitSignal() == 119)) {
            return FrameState.WAITING;
        }
        if ((report.getExitStatus() == FrameExitStatus.FAILED_LAUNCH_VALUE
                || report.getExitSignal() == FrameExitStatus.FAILED_LAUNCH_VALUE)
                && frame.retries < job.maxRetries) {
            return FrameState.WAITING;
        }
        if (report.getHost().getNimbyLocked() && report.getExitSignal() == 15) {
            // The frame was killed by a NIMBY lock; retry even past the max retry count.
            return FrameState.WAITING;
        }
        if (job.autoEat) {
            return FrameState.EATEN;
        }
        if (delayRules.containsKey(resolveExitStatus(report, frameDetail))) {
            return FrameState.WAITING;
        }

        // Log update (LLU) and run time timeouts.
        long minutesSinceLogUpdate =
                (System.currentTimeMillis() / 1000 - report.getFrame().getLluTime()) / 60;
        if (layer.timeout_llu != 0 && report.getFrame().getLluTime() != 0
                && minutesSinceLogUpdate > (layer.timeout_llu - 1)) {
            return FrameState.DEAD;
        }
        if (layer.timeout != 0 && report.getRunTime() > layer.timeout * 60) {
            return FrameState.DEAD;
        }
        if (report.getRunTime() > Dispatcher.FRAME_TIME_NO_RETRY) {
            return FrameState.DEAD;
        }

        if (frame.retries >= job.maxRetries && !isMemoryFailure(report, frameDetail)) {
            return FrameState.DEAD;
        }
        return FrameState.WAITING;
    }

    /**
     * Retries a dependency satisfaction operation up to DEPEND_MAX_RETRIES times with exponential
     * backoff (100ms, 200ms, 400ms).
     *
     * Dependency satisfaction is critical: a transient failure (e.g. connection pool exhaustion)
     * can leave downstream frames permanently stuck in DEPEND state.
     */
    private void satisfyDependsWithRetry(Runnable operation, String entityDesc, String jobName,
            String jobId) {
        for (int attempt = 1; attempt <= DEPEND_MAX_RETRIES; attempt++) {
            try {
                operation.run();
                return;
            } catch (Exception e) {
                // Ideally DataAccessException should be the target to be caught, but pool
                // exhaustion is not categorized as such.
                // Pool exhaustion throws CannotCreateTransactionException (TransactionException)
                // which can only be caught in this context as a general Exception
                if (attempt < DEPEND_MAX_RETRIES) {
                    // Exponential backoff: 100ms, 200ms, 400ms (bit-shift doubles each attempt)
                    long backoffMs = DEPEND_INITIAL_BACKOFF_MS * (1L << (attempt - 1));
                    logger.warn("Failed to satisfy depends on " + entityDesc + " in job " + jobName
                            + " (attempt " + attempt + "/" + DEPEND_MAX_RETRIES + "), retrying in "
                            + backoffMs + "ms: " + e);
                    try {
                        // I acknowledge sleeping within a threadpool is rarely a good idea as it
                        // blocks execution and can lead to backpressure. This sleep is only
                        // triggered when there are transient issues, so it is likely the following
                        // tasks would also fail. The worst case scenario is backing up the
                        // threadpool for 700ms, which is acceptable given the circumstances
                        Thread.sleep(backoffMs);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        logger.error("Dependency Failure: Interrupted while retrying depends on "
                                + entityDesc + " in job " + jobName + " (id=" + jobId + "). "
                                + "Downstream frames may be stuck in DEPEND state.");
                        return;
                    }
                } else {
                    logger.error("Dependency Failure: Failed to satisfy depends on " + entityDesc
                            + " in job " + jobName + " (id=" + jobId + ") after "
                            + DEPEND_MAX_RETRIES + " attempts. "
                            + "Downstream frames may be stuck in DEPEND state. ", e);
                }
            }
        }
    }

    /**
     * Publishes a frame complete event to Kafka for monitoring purposes. This method is called
     * asynchronously to avoid blocking the dispatch thread.
     */
    private void publishFrameCompleteEvent(FrameCompleteReport report, DispatchFrame frame,
            FrameDetail frameDetail, FrameState newFrameState, VirtualProc proc) {
        // Record Prometheus metrics for frame completion
        if (prometheusMetrics != null) {
            prometheusMetrics.recordFrameCompleted(newFrameState.name(), frame.show, frame.shot);
        }

        // Publish to Kafka if enabled
        if (kafkaEventPublisher == null || !kafkaEventPublisher.isEnabled()) {
            return;
        }

        FrameEvent event = monitoringEventBuilder.buildFrameCompleteEvent(report, newFrameState,
                frameDetail.state, frame, proc);
        kafkaEventPublisher.publishFrameEvent(event);
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
        return jmsMover;
    }

    public void setJmsMover(JmsMover jmsMover) {
        this.jmsMover = jmsMover;
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

    public LayerDao getLayerDao() {
        return layerDao;
    }

    public void setLayerDao(LayerDao layerDao) {
        this.layerDao = layerDao;
    }

    public KafkaEventPublisher getKafkaEventPublisher() {
        return kafkaEventPublisher;
    }

    public void setKafkaEventPublisher(KafkaEventPublisher kafkaEventPublisher) {
        this.kafkaEventPublisher = kafkaEventPublisher;
    }

    public void setMonitoringEventBuilder(MonitoringEventBuilder monitoringEventBuilder) {
        this.monitoringEventBuilder = monitoringEventBuilder;
    }

    public PrometheusMetricsCollector getPrometheusMetrics() {
        return prometheusMetrics;
    }

    public void setPrometheusMetrics(PrometheusMetricsCollector prometheusMetrics) {
        this.prometheusMetrics = prometheusMetrics;
    }
}
