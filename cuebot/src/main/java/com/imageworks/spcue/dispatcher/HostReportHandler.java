
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

import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadPoolExecutor;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.dao.DataAccessException;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobEntity;
import com.imageworks.spcue.LayerEntity;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHost;
import com.imageworks.spcue.dispatcher.commands.DispatchBookHostLocal;
import com.imageworks.spcue.dispatcher.commands.DispatchHandleHostReport;
import com.imageworks.spcue.dispatcher.commands.DispatchRqdKillFrame;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.report.BootReport;
import com.imageworks.spcue.grpc.report.CoreDetail;
import com.imageworks.spcue.grpc.report.HostReport;
import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.service.BookingManager;
import com.imageworks.spcue.service.CommentManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.util.CueExceptionUtil;
import com.imageworks.spcue.util.CueUtil;

import static com.imageworks.spcue.dispatcher.Dispatcher.*;

public class HostReportHandler {

    private static final Logger logger = LogManager.getLogger(HostReportHandler.class);

    private BookingManager bookingManager;
    private HostManager hostManager;
    private BookingQueue bookingQueue;
    private ThreadPoolExecutor reportQueue;
    private ThreadPoolExecutor killQueue;
    private DispatchSupport dispatchSupport;
    private Dispatcher dispatcher;
    private Dispatcher localDispatcher;
    private RqdClient rqdClient;
    private JobManager jobManager;
    private JobDao jobDao;
    private LayerDao layerDao;
    @Autowired
    private Environment env;
    @Autowired
    private CommentManager commentManager;
    // Comment constants
    private static final String SUBJECT_COMMENT_FULL_TEMP_DIR = "Host set to REPAIR for not having enough storage " +
            "space on the temporary directory (mcp)";
    private static final String CUEBOT_COMMENT_USER = "cuebot";

    /**
     * Boolean to toggle if this class is accepting data or not.
     */
    public boolean shutdown = false;

    /**
     * Return true if this handler is not accepting packets anymore.
     * @return
     */
    public boolean isShutdown() {
        return shutdown;
    }

    /**
     * Shutdown this handler so it no longer accepts packets.  Any
     * call to queue a host report will throw an exception.
     */
    public synchronized void shutdown() {
        logger.info("Shutting down HostReportHandler.");
        shutdown = true;
    }

    /**
     * Queues up the given boot report.
     *
     * @param report
     */
    public void queueBootReport(BootReport report) {
        if (isShutdown()) {
            throw new RqdRetryReportException(
                    "Error processing host report. Cuebot not " +
                    "accepting packets.");
        }
        reportQueue.execute(new DispatchHandleHostReport(report, this));
    }

    /**
     * Queues up the given host report.
     *
     * @param report
     */
    public void queueHostReport(HostReport report) {
        if (isShutdown()) {
            throw new RqdRetryReportException(
                    "Error processing host report. Cuebot not " +
                    "accepting packets.");
        }
        reportQueue.execute(new DispatchHandleHostReport(report, this));
    }


    public void handleHostReport(HostReport report, boolean isBoot) {
        long startTime = System.currentTimeMillis();
        try {

            long swapOut = 0;
            if (report.getHost().getAttributesMap().containsKey("swapout")) {
                swapOut = Integer.parseInt(report.getHost().getAttributesMap().get("swapout"));
                if (swapOut > 0)
                    logger.info(report.getHost().getName() + " swapout: " +
                                report.getHost().getAttributesMap().get("swapout"));
            }

            DispatchHost host;
            RenderHost rhost = report.getHost();
            try {
                host = hostManager.findDispatchHost(rhost.getName());
                hostManager.setHostStatistics(host,
                        rhost.getTotalMem(), rhost.getFreeMem(),
                        rhost.getTotalSwap(), rhost.getFreeSwap(),
                        rhost.getTotalMcp(), rhost.getFreeMcp(),
                        rhost.getTotalGpuMem(), rhost.getFreeGpuMem(),
                        rhost.getLoad(), new Timestamp(rhost.getBootTime() * 1000l),
                        rhost.getAttributesMap().get("SP_OS"));

                changeHardwareState(host, report.getHost().getState(), isBoot, report.getHost().getFreeMcp());
                changeNimbyState(host, report.getHost());

                /**
                 * This should only happen at boot time or it will
                 * fight with the dispatcher over row locks.
                 */
                if (isBoot) {
                    hostManager.setHostResources(host, report);
                }

                dispatchSupport.determineIdleCores(host, report.getHost().getLoad());

            } catch (DataAccessException dae) {
                logger.warn("Unable to find host " + rhost.getName() + ","
                        + dae + " , creating host.");
                // TODO: Skip adding it if the host name is over 30 characters

                host = hostManager.createHost(report);
            }
            catch (Exception e) {
                logger.warn("Error processing HostReport, " + e);
                return;
            }

            /*
             * Verify all the frames in the report are valid.
             * Frames that are not valid are removed.
             */
            verifyRunningFrameInfo(report);

            /*
             * Updates memory usage for the proc, frames,
             * jobs, and layers. And LLU time for the frames.
             */
            updateMemoryUsageAndLluTime(report.getFramesList());

            /*
             * kill frames that have over run.
             */
            killTimedOutFrames(report);

            /*
             * Prevent OOM (Out-Of-Memory) issues on the host and manage frame reserved memory
             */
            handleMemoryUsage(host, report);

            /*
             * The checks are done in order of least CPU intensive to
             * most CPU intensive, saving checks that hit the DB for last.
             *
             * These are done so we don't populate the booking queue with
             * a bunch of hosts that can't be booked.
             */
            String msg = null;
            boolean hasLocalJob = bookingManager.hasLocalHostAssignment(host);

            if (hasLocalJob) {
                List<LocalHostAssignment> lcas =
                    bookingManager.getLocalHostAssignment(host);
                for (LocalHostAssignment lca : lcas) {
                    bookingManager.removeInactiveLocalHostAssignment(lca);
                }
            }

            // The minimum amount of free space in the temporary directory to book a host
            Long minBookableFreeTempDir = env.getRequiredProperty("dispatcher.min_bookable_free_temp_dir_kb", Long.class);

            if (minBookableFreeTempDir != -1 && report.getHost().getFreeMcp() < minBookableFreeTempDir) {
                msg = String.format("%s doens't have enough free space in the temporary directory (mcp), %dMB needs %dMB",
                        host.name, (report.getHost().getFreeMcp()/1024),  (minBookableFreeTempDir/1024));
            }
            else if (host.idleCores < Dispatcher.CORE_POINTS_RESERVED_MIN) {
                msg = String.format("%s doesn't have enough idle cores, %d needs %d",
                    host.name,  host.idleCores, Dispatcher.CORE_POINTS_RESERVED_MIN);
            }
            else if (host.idleMemory < Dispatcher.MEM_RESERVED_MIN) {
                msg = String.format("%s doesn't have enough idle memory, %d needs %d",
                        host.name,  host.idleMemory,  Dispatcher.MEM_RESERVED_MIN);
            }
            else if (report.getHost().getFreeMem() < CueUtil.MB512) {
                msg = String.format("%s doens't have enough free system mem, %d needs %d",
                        host.name, report.getHost().getFreeMem(), Dispatcher.MEM_RESERVED_MIN);
            }
            else if(!host.hardwareState.equals(HardwareState.UP)) {
                msg = host + " is not in the Up state.";
            }
            else if (host.lockState.equals(LockState.LOCKED)) {
                msg = host + " is locked.";
            }
            else if (report.getHost().getNimbyLocked()) {
                if (!hasLocalJob) {
                    msg = host + " is NIMBY locked.";
                }
            }
            else if (!dispatchSupport.isCueBookable(host)) {
                msg = "The cue has no pending jobs";
            }

            /*
             * If a message was set, the host is not bookable.  Log
             * the message and move on.
             */
            if (msg != null) {
                logger.trace(msg);
            }
            else {

                // check again. The dangling local host assignment could be removed.
                hasLocalJob = bookingManager.hasLocalHostAssignment(host);

                /*
                 * Check to see if a local job has been assigned.
                 */
                if (hasLocalJob) {
                    if (!bookingManager.hasResourceDeficit(host)) {
                        bookingQueue.execute(
                                new DispatchBookHostLocal(
                                        host, localDispatcher));
                    }
                    return;
                }

                /*
                 * Check if the host prefers a show.  If it does , dispatch
                 * to that show first.
                 */
                if (hostManager.isPreferShow(host)) {
                    bookingQueue.execute(new DispatchBookHost(
                            host, hostManager.getPreferredShow(host), dispatcher));
                    return;
                }

                bookingQueue.execute(new DispatchBookHost(host, dispatcher));
            }

        } finally {
            if (reportQueue.getQueue().size() > 0 ||
                    System.currentTimeMillis() - startTime > 100) {
                /*
                 * Write a log if the host report takes a long time to process.
                 */
                CueUtil.logDuration(startTime, "host report " +
                        report.getHost().getName() + " with " +
                        report.getFramesCount() +
                        " running frames, waiting: " +
                        reportQueue.getQueue().size());
            }
        }
    }

    /**
     * Update the hardware state property.
     *
     * If a host pings in with a different hardware state than what
     * is currently in the DB, the state is updated.  If the hardware
     * state is Rebooting or RebootWhenIdle, then state can only be
     * updated with a boot report.  If the state is Repair, then state is
     * never updated via RQD.
     *
     *
     * Prevent cue frames from booking on hosts with full temporary directories.
     *
     * Change host state to REPAIR or UP according the amount of free space
     * in the temporary directory:
     * - Set the host state to REPAIR, when the amount of free space in the
     * temporary directory is less than the minimum required. Add a comment with
     * subject: SUBJECT_COMMENT_FULL_TEMP_DIR
     * - Set the host state to UP, when the amount of free space in the temporary directory
     * is greater or equals to the minimum required and the host has a comment with
     * subject: SUBJECT_COMMENT_FULL_TEMP_DIR
     *
     * @param host
     * @param reportState
     * @param isBoot
     * @param freeTempDir
     */
    private void changeHardwareState(DispatchHost host, HardwareState reportState, boolean isBoot, long freeTempDir) {

        // The minimum amount of free space in the temporary directory to book a host
        Long minBookableFreeTempDir = env.getRequiredProperty("dispatcher.min_bookable_free_temp_dir_kb", Long.class);

        // Prevent cue frames from booking on hosts with full temporary directories
        if (minBookableFreeTempDir != -1) {
            if (host.hardwareState == HardwareState.UP && freeTempDir < minBookableFreeTempDir) {

                // Insert a comment indicating that the Host status = Repair with reason = Full temporary directory
                CommentDetail c = new CommentDetail();
                c.subject = SUBJECT_COMMENT_FULL_TEMP_DIR;
                c.user = CUEBOT_COMMENT_USER;
                c.timestamp = null;
                c.message = "Host " + host.getName() + " marked as REPAIR. The current amount of free space in the " +
                        "temporary directory (mcp) is " + (freeTempDir/1024) + "MB. It must have at least "
                        + (minBookableFreeTempDir/1024) + "MB of free space in temporary directory";
                commentManager.addComment(host, c);

                // Set the host state to REPAIR
                hostManager.setHostState(host, HardwareState.REPAIR);
                host.hardwareState = HardwareState.REPAIR;

                return;
            } else if (host.hardwareState == HardwareState.REPAIR && freeTempDir >= minBookableFreeTempDir) {
                // Check if the host with REPAIR status has comments with subject=SUBJECT_COMMENT_FULL_TEMP_DIR and
                // user=CUEBOT_COMMENT_USER and delete the comments, if they exists
                boolean commentsDeleted = commentManager.deleteCommentByHostUserAndSubject(host,
                        CUEBOT_COMMENT_USER, SUBJECT_COMMENT_FULL_TEMP_DIR);

                if (commentsDeleted) {
                    // Set the host state to UP
                    hostManager.setHostState(host, HardwareState.UP);
                    host.hardwareState = HardwareState.UP;
                    return;
                }
            }
        }

        // If the states are the same there is no reason to do this update.
        if (host.hardwareState.equals(reportState)) {
            return;
        }

        switch (host.hardwareState) {
            case DOWN:
                hostManager.setHostState(host, HardwareState.UP);
                host.hardwareState = HardwareState.UP;
                break;
            case REBOOTING:
            case REBOOT_WHEN_IDLE:
                // Rebooting hosts only change to UP when processing a boot report
                if (isBoot) {
                    hostManager.setHostState(host, HardwareState.UP);
                    host.hardwareState = HardwareState.UP;
                }
                break;
            case REPAIR:
                // Do not change the state of the host if its in a repair state.
                break;
            default:
                hostManager.setHostState(host, reportState);
                host.hardwareState = reportState;
                break;

        }
    }

    /**
     * Changes the NIMBY lock state.  If the DB indicates a NIMBY lock
     * but RQD does not, then the host is unlocked.  If the DB indicates
     * the host is not locked but RQD indicates it is, the host is locked.
     *
     * @param host
     * @param rh
     */
    private void changeNimbyState(DispatchHost host, RenderHost rh) {
        if (rh.getNimbyLocked()) {
            if (host.lockState.equals(LockState.OPEN)) {
                host.lockState = LockState.NIMBY_LOCKED;
                hostManager.setHostLock(host,LockState.NIMBY_LOCKED, new Source("NIMBY"));
            }
        }
        else {
            if (host.lockState.equals(LockState.NIMBY_LOCKED)) {
                host.lockState = LockState.OPEN;
                hostManager.setHostLock(host,LockState.OPEN, new Source("NIMBY"));
            }
        }
    }

    /**
     * Changes the Lock state of the host. Looks at the number of locked cores and sets host to
     * locked if all cores are locked.
     *
     * @param host DispatchHost
     * @param coreInfo CoreDetail
     */
    private void changeLockState(DispatchHost host, CoreDetail coreInfo) {
        if (host.lockState == LockState.LOCKED) {
            if (coreInfo.getLockedCores() < coreInfo.getTotalCores()) {
                host.lockState = LockState.OPEN;
                hostManager.setHostLock(host, LockState.OPEN, new Source("cores"));
            }
        } else if (coreInfo.getLockedCores() >= coreInfo.getTotalCores()) {
            host.lockState = LockState.LOCKED;
            hostManager.setHostLock(host, LockState.LOCKED, new Source("cores"));
        }
    }

    /**
     * Prevent host from entering an OOM state where oom-killer might start killing important OS processes.
     * The kill logic will kick in one of the following conditions is met:
     *   - Host has less than OOM_MEMORY_LEFT_THRESHOLD_PERCENT memory available
     *   - A frame is taking more than OOM_FRAME_OVERBOARD_PERCENT of what it had reserved
     * For frames that are using more than they had reserved but not above the threshold, negotiate expanding
     * the reservations with other frames on the same host
     * @param host
     * @param report
     */
    private void handleMemoryUsage(final DispatchHost host, final HostReport report) {
        RenderHost renderHost = report.getHost();
        List<RunningFrameInfo> runningFrames = report.getFramesList();

        boolean memoryWarning = renderHost.getTotalMem() > 0 &&
                ((double)renderHost.getFreeMem()/renderHost.getTotalMem() <
                        (1.0 - OOM_MAX_SAFE_USED_MEMORY_THRESHOLD));

        if (memoryWarning) {
            VirtualProc killedProc = killWorstMemoryOffender(host);
            long memoryAvailable = renderHost.getFreeMem();
            long minSafeMemoryAvailable = (long)(renderHost.getTotalMem() * (1.0 - OOM_MAX_SAFE_USED_MEMORY_THRESHOLD));
            // Some extra protection for this possibly unbound loop
            int unboundProtectionLimit = 10;
            while (killedProc != null && unboundProtectionLimit > 0) {
                memoryAvailable = memoryAvailable + killedProc.memoryUsed;

                // If killing this proc solved the memory issue, stop the attack
                if (memoryAvailable >= minSafeMemoryAvailable) {
                    break;
                }
                killedProc = killWorstMemoryOffender(host);
                unboundProtectionLimit -= 1;
            }
        } else {
            // When no mass cleaning was required, check for frames going overboard
            // if frames didn't go overboard, manage its reservations trying to increase
            // them accordingly
            for (final RunningFrameInfo frame : runningFrames) {
                if (OOM_FRAME_OVERBOARD_ALLOWED_THRESHOLD > 0 && isFrameOverboard(frame)) {
                    if (!killFrameOverusingMemory(frame, host.getName())) {
                        logger.warn("Frame " + frame.getJobName() + "." + frame.getFrameName() +
                                " is overboard but could not be killed");
                    }
                } else {
                    handleMemoryReservations(frame);
                }
            }
        }
    }

    private boolean killFrameOverusingMemory(RunningFrameInfo frame, String hostname) {
        try {
            VirtualProc proc = hostManager.getVirtualProc(frame.getResourceId());

            // Don't mess with localDispatch procs
            if (proc.isLocalDispatch) {
                return false;
            }

            logger.info("Killing frame on " + frame.getJobName() + "." + frame.getFrameName() +
                    ", using too much memory.");
            return killProcForMemory(proc, hostname, "This frame is using way more than it had reserved.");
        } catch (EmptyResultDataAccessException e) {
            return false;
        }
    }

    private boolean killProcForMemory(VirtualProc proc, String hostname, String reason) {
        try {
            FrameInterface frame = jobManager.getFrame(proc.frameId);

            if (dispatcher.isTestMode()) {
                // For testing, don't run on a different threadpool, as different threads don't share
                // the same database state
                (new DispatchRqdKillFrameMemory(proc.hostName, frame, reason, rqdClient,
                        dispatchSupport, dispatcher.isTestMode())).run();
            } else {
                killQueue.execute(new DispatchRqdKillFrameMemory(proc.hostName, frame, reason, rqdClient,
                        dispatchSupport, dispatcher.isTestMode()));
                prometheusMetrics.incrementFrameOomKilledCounter(hostname);
            }
            DispatchSupport.killedOffenderProcs.incrementAndGet();
            return true;
        } catch (TaskRejectedException e) {
            logger.warn("Unable to queue RQD kill, task rejected, " + e);
            return false;
        }
    }

    /**
     * Kill proc with the worst user/reserved memory ratio.
     *
     * @param host
     * @return killed proc, or null if none could be found or failed to be killed
     */
    private VirtualProc killWorstMemoryOffender(final DispatchHost host) {
        try {
            VirtualProc proc = hostManager.getWorstMemoryOffender(host);
            logger.info("Killing frame on " + proc.getName() + ", host is under stress.");

            if (!killProcForMemory(proc, host.getName(), "The host was dangerously low on memory and swapping.")) {
                // Returning null will prevent the caller from overflowing the kill queue with more messages
                proc = null;
            }
            return proc;
        }
        catch (EmptyResultDataAccessException e) {
            logger.error(host.name + " is under OOM and no proc is running on it.");
            return null;
        }
    }

    /**
     * Check frame memory usage comparing the amount used with the amount it had reserved
     * @param frame
     * @return
     */
    private boolean isFrameOverboard(final RunningFrameInfo frame) {
        double rss = (double)frame.getRss();
        double maxRss = (double)frame.getMaxRss();
        final double MAX_RSS_OVERBOARD_THRESHOLD = OOM_FRAME_OVERBOARD_ALLOWED_THRESHOLD * 2;
        final double RSS_AVAILABLE_FOR_MAX_RSS_TRIGGER = 0.1;

        try {
            VirtualProc proc = hostManager.getVirtualProc(frame.getResourceId());
            double reserved = (double)proc.memoryReserved;

            // Last memory report is higher than the threshold
            if (isOverboard(rss, reserved, OOM_FRAME_OVERBOARD_ALLOWED_THRESHOLD)) {
                return true;
            }
            // If rss is not overboard, handle the situation where the frame might be going overboard from
            // time to time but the last report wasn't during a spike. For this case, consider a combination
            // of rss and maxRss. maxRss > 2 * threshold and rss > 0.9
            else {
                return isOverboard(maxRss, reserved, MAX_RSS_OVERBOARD_THRESHOLD) &&
                        isOverboard(rss, reserved, -RSS_AVAILABLE_FOR_MAX_RSS_TRIGGER);
            }
        } catch (EmptyResultDataAccessException e) {
            logger.info("HostReportHandler(isFrameOverboard): Virtual proc for frame " +
                    frame.getFrameName() + " on job " + frame.getJobName() + " doesn't exist on the database");
            // Not able to mark the frame overboard is it couldn't be found on the db.
            // Proc accounting (verifyRunningProc) should take care of it
            return false;
        }
    }

    private boolean isOverboard(double value, double total, double threshold) {
        return value/total >= (1 + threshold);
    }

    /**
     * Handle memory reservations for the given frame
     *
     * @param frame
     */
    private void handleMemoryReservations(final RunningFrameInfo frame) {
        VirtualProc proc = null;
        try {
            proc = hostManager.getVirtualProc(frame.getResourceId());

            if (proc.isLocalDispatch) {
                return;
            }

            if (dispatchSupport.increaseReservedMemory(proc, frame.getRss())) {
                proc.memoryReserved = frame.getRss();
                logger.info("frame " + frame.getFrameName() + " on job " + frame.getJobName()
                        + " increased its reserved memory to " +
                        CueUtil.KbToMb(frame.getRss()));
            }
        } catch (ResourceReservationFailureException e) {
            if (proc != null) {
                long memNeeded = frame.getRss() - proc.memoryReserved;
                logger.info("frame " + frame.getFrameName() + " on job " + frame.getJobName()
                        + "was unable to reserve an additional " + CueUtil.KbToMb(memNeeded)
                        + "on proc " + proc.getName() + ", " + e);
                try {
                    if (dispatchSupport.balanceReservedMemory(proc, memNeeded)) {
                        proc.memoryReserved = frame.getRss();
                        logger.info("was able to balance host: " + proc.getName());
                    } else {
                        logger.info("failed to balance host: " + proc.getName());
                    }
                } catch (Exception ex) {
                    logger.warn("failed to balance host: " + proc.getName() + ", " + e);
                }
            } else {
                logger.info("frame " + frame.getFrameName() + " on job " + frame.getJobName()
                        + "was unable to reserve an additional memory. Proc could not be found");
            }
        } catch (EmptyResultDataAccessException e) {
            logger.info("HostReportHandler: Memory reservations for frame " + frame.getFrameName() +
                    " on job " + frame.getJobName() + " proc could not be found");
        }
    }

    /**
     *  Kill frames that over run.
     *
     * @param rFrames
     */
    private void killTimedOutFrames(HostReport report) {

        final Map<String, LayerDetail> layers = new HashMap<String, LayerDetail>(5);

        for (RunningFrameInfo frame: report.getFramesList()) {
            String layerId = frame.getLayerId();
            LayerDetail layer = layerDao.getLayerDetail(layerId);
            long runtimeMinutes = ((System.currentTimeMillis() - frame.getStartTime()) / 1000l) / 60;

            if (layer.timeout != 0 && runtimeMinutes > layer.timeout){
                try {
                    killQueue.execute(new DispatchRqdKillFrame(report.getHost().getName(),
                            frame.getFrameId(),
                            "This frame has reached it timeout.",
                            rqdClient));
                    } catch (TaskRejectedException e) {
                        logger.warn("Unable to queue  RQD kill, task rejected, " + e);
                }
            }

            if (layer.timeout_llu == 0){
                continue;
            }

            if (frame.getLluTime() == 0){
                continue;
            }

            long r = System.currentTimeMillis() / 1000;
            long lastUpdate = (r - frame.getLluTime()) / 60;

            if (layer.timeout_llu != 0 && lastUpdate > (layer.timeout_llu -1)){
                try {
                    killQueue.execute(new DispatchRqdKillFrame(report.getHost().getName(),
                            frame.getFrameId(),
                            "This frame has reached it LLU timeout.",
                            rqdClient));
                    } catch (TaskRejectedException e) {
                        logger.warn("Unable to queue  RQD kill, task rejected, " + e);
                }
            }
        }
    }

    /**
     *  Update memory usage and LLU time for the given list of frames.
     *
     * @param rFrames
     */
    private void updateMemoryUsageAndLluTime(List<RunningFrameInfo> rFrames) {

        for (RunningFrameInfo rf: rFrames) {

            FrameInterface frame = jobManager.getFrame(rf.getFrameId());

            dispatchSupport.updateFrameMemoryUsageAndLluTime(frame,
                    rf.getRss(), rf.getMaxRss(), rf.getLluTime());

            dispatchSupport.updateProcMemoryUsage(frame, rf.getRss(), rf.getMaxRss(),
                    rf.getVsize(), rf.getMaxVsize(), rf.getUsedGpuMemory(),
                    rf.getMaxUsedGpuMemory(), rf.getChildren().toByteArray());
        }

        updateJobMemoryUsage(rFrames);
        updateLayerMemoryUsage(rFrames);
    }

    /**
     * Update job memory using for the given list of frames.
     *
     * @param frames
     */
    private void updateJobMemoryUsage(List<RunningFrameInfo> frames) {

        final Map<JobEntity, Long> jobs =
            new HashMap<JobEntity, Long>(frames.size());

        for (RunningFrameInfo frame: frames) {
            JobEntity job = new JobEntity(frame.getJobId());
            if (jobs.containsKey(job)) {
                if (jobs.get(job) < frame.getMaxRss()) {
                    jobs.put(job, frame.getMaxRss());
                }
            }
            else {
                jobs.put(job, frame.getMaxRss());
            }
        }

        for (Map.Entry<JobEntity,Long> set: jobs.entrySet()) {
            jobDao.updateMaxRSS(set.getKey(), set.getValue());
        }
    }

    /**
     * Update layer memory usage for the given list of frames.
     *
     * @param frames
     */
    private void updateLayerMemoryUsage(List<RunningFrameInfo> frames) {

        final Map<LayerEntity, Long> layers =
            new HashMap<LayerEntity, Long>(frames.size());

        for (RunningFrameInfo frame: frames) {
            LayerEntity layer = new LayerEntity(frame.getLayerId());
            if (layers.containsKey(layer)) {
                if (layers.get(layer) < frame.getMaxRss()) {
                    layers.put(layer, frame.getMaxRss());
                }
            }
            else {
                layers.put(layer, frame.getMaxRss());
            }
        }

        /* Attempt to update the max RSS value for the job **/
        for (Map.Entry<LayerEntity,Long> set: layers.entrySet()) {
            layerDao.increaseLayerMinMemory(set.getKey(), set.getValue());
            layerDao.updateLayerMaxRSS(set.getKey(), set.getValue(), false);
        }
    }

    /**
     * Number of seconds before running frames have to exist before being
     * verified against the DB.
     */
    private static final long FRAME_VERIFICATION_GRACE_PERIOD_SECONDS = 120;

    /**
     * Verify all running frames in the given report against
     * the DB.  Frames that have not been running for at least
     * FRAME_VERIFICATION_GRACE_PERIOD_SECONDS are skipped.
     *
     * If a frame->proc mapping is not verified then the record
     * for the proc is pulled from the DB.  If the proc doesn't
     * exist at all, then the frame is killed with the message:
     * "but the DB did not reflect this"
     *
     * The main reason why a proc no longer exists is that the cue
     * though the host went down and cleared out all running frames.
     *
     * @param report
     */
    public void verifyRunningFrameInfo(HostReport report) {

        List<RunningFrameInfo> runningFrames = new
            ArrayList<RunningFrameInfo>(report.getFramesCount());

        for (RunningFrameInfo runningFrame: report.getFramesList()) {

            long runtimeSeconds = (System.currentTimeMillis() -
                runningFrame.getStartTime()) / 1000l;

            // Don't test frames that haven't been running long enough.
            if (runtimeSeconds < FRAME_VERIFICATION_GRACE_PERIOD_SECONDS) {
                logger.info("verified " + runningFrame.getJobName() +
                        "/" + runningFrame.getFrameName() + " on " +
                        report.getHost().getName() + " by grace period " +
                        runtimeSeconds + " seconds.");
                runningFrames.add(runningFrame);
                continue;
            }


            if (!hostManager.verifyRunningProc(runningFrame.getResourceId(),
                    runningFrame.getFrameId())) {

                /*
                 * The frame this proc is running is no longer
                 * assigned to this proc.   Don't ever touch
                 * the frame record.  If we make it here that means
                 * the proc has been running for over 2 min.
                 */

                String msg;
                VirtualProc proc = null;

                try {
                    proc = hostManager.getVirtualProc(runningFrame.getResourceId());
                    msg = "Virutal proc " + proc.getProcId() +
                        "is assigned to " + proc.getFrameId() +
                        " not " + runningFrame.getFrameId();
                }
                catch (Exception e) {
                    /*
                     * This will happen if the host goes off line and then
                     * comes back.  In this case, we don't touch the frame
                     * since it might already be running somewhere else.  We
                     * do however kill the proc.
                     */
                    msg = "Virtual proc did not exist.";
                }

                logger.info("warning, the proc " +
                        runningFrame.getResourceId() + " on host " +
                        report.getHost().getName() + " was running for " +
                        (runtimeSeconds / 60.0f) + " minutes " +
                        runningFrame.getJobName() + "/" + runningFrame.getFrameName() +
                        "but the DB did not " +
                        "reflect this " +
                        msg);

                DispatchSupport.accountingErrors.incrementAndGet();

                try {
                    /*
                     * If the proc did exist unbook it if we can't
                     * verify its running something.
                     */
                    boolean rqd_kill = false;
                    if (proc != null) {

                        /*
                         * Check to see if the proc is an orphan.
                         */
                        if (hostManager.isOprhan(proc)) {
                            dispatchSupport.clearVirtualProcAssignement(proc);
                            dispatchSupport.unbookProc(proc);
                            rqd_kill = true;
                        }
                    }
                    else {
                        /* Proc doesn't exist so a kill won't hurt */
                        rqd_kill = true;
                    }

                    if (rqd_kill) {
                        try {
                        killQueue.execute(new DispatchRqdKillFrame(report.getHost().getName(),
                                runningFrame.getFrameId(),
                                "OpenCue could not verify this frame.",
                                rqdClient));
                        } catch (TaskRejectedException e) {
                            logger.warn("Unable to queue  RQD kill, task rejected, " + e);
                        }
                    }

                } catch (RqdClientException rqde) {
                    logger.warn("failed to kill " +
                            runningFrame.getJobName() + "/" +
                            runningFrame.getFrameName() +
                            " when trying to clear a failed " +
                            " frame verification, " + rqde);

                } catch (Exception e) {
                    CueExceptionUtil.logStackTrace("failed", e);
                    logger.warn("failed to verify " +
                            runningFrame.getJobName() + "/" +
                            runningFrame.getFrameName() +
                            " was running but the frame was " +
                            " unable to be killed, " + e);
                }
            }
            else {
                runningFrames.add(runningFrame);
            }
        }
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public BookingQueue getBookingQueue() {
        return bookingQueue;
    }

    public void setBookingQueue(BookingQueue bookingQueue) {
        this.bookingQueue = bookingQueue;
    }

    public ThreadPoolExecutor getReportQueue() {
        return reportQueue;
    }

    public void setReportQueue(ThreadPoolExecutor reportQueue) {
        this.reportQueue = reportQueue;
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public Dispatcher getDispatcher() {
        return dispatcher;
    }

    public void setDispatcher(Dispatcher dispatcher) {
        this.dispatcher = dispatcher;
    }

    public RqdClient getRqdClient() {
        return rqdClient;
    }

    public void setRqdClient(RqdClient rqdClient) {
        this.rqdClient = rqdClient;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    public LayerDao getLayerDao() {
        return layerDao;
    }

    public void setLayerDao(LayerDao layerDao) {
        this.layerDao = layerDao;
    }

    public BookingManager getBookingManager() {
        return bookingManager;
    }

    public void setBookingManager(BookingManager bookingManager) {
        this.bookingManager = bookingManager;
    }

    public Dispatcher getLocalDispatcher() {
        return localDispatcher;
    }

    public void setLocalDispatcher(Dispatcher localDispatcher) {
        this.localDispatcher = localDispatcher;
    }
    public ThreadPoolExecutor getKillQueue() {
        return killQueue;
    }

    public void setKillQueue(ThreadPoolExecutor killQueue) {
        this.killQueue = killQueue;
    }
}

