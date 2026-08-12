
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

package com.imageworks.spcue.service;

import java.util.List;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.CannotGetJdbcConnectionException;

import io.sentry.Sentry;

import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.MaintenanceTask;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.MaintenanceDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameState;

public class MaintenanceManagerSupport {

    private static final Logger logger = LogManager.getLogger(MaintenanceManagerSupport.class);

    @Autowired
    private Environment env;

    private MaintenanceDao maintenanceDao;

    private ProcDao procDao;

    private FrameDao frameDao;

    private HostDao hostDao;

    private JobManager jobManager;

    private DispatchSupport dispatchSupport;

    private HistoricalSupport historicalSupport;

    private DepartmentManager departmentManager;

    private DependManager dependManager;

    private RqdClient rqdClient;

    private static final long WAIT_FOR_HOST_REPORTS_MS = 600000;

    private static final int CHECKPOINT_MAX_WAIT_SEC = 300;

    /**
     * Total wall-clock budget for killing and confirming the death of orphaned frames in a single
     * maintenance pass. Once spent, remaining frames are deferred to the next pass. Kept well below
     * the orphaned-frame check interval so a pass cannot overrun into the next one. Overridable via
     * the {@code maintenance.orphaned_frame_kill_budget_ms} property.
     */
    private static final long DEFAULT_ORPHANED_FRAME_KILL_BUDGET_MS = 10000;

    /**
     * Per-frame ceiling on how long to wait for a single orphaned frame's render to confirm dead.
     * Bounds one slow-to-exit render so it cannot monopolize the whole pass budget; the frame is
     * deferred to the next pass instead. Overridable via the
     * {@code maintenance.orphaned_frame_confirm_timeout_ms} property.
     */
    private static final long DEFAULT_ORPHANED_FRAME_CONFIRM_TIMEOUT_MS = 5000;

    /**
     * How long a frame may stay orphaned-and-unconfirmable (measured from its last update) before
     * it is failed closed (DEAD) instead of being deferred again. This bounds deferral so a frame
     * that can never be confirmed dead eventually surfaces for manual retry rather than lingering
     * RUNNING forever. Overridable via the {@code maintenance.orphaned_frame_max_defer_ms}
     * property.
     */
    private static final long DEFAULT_ORPHANED_FRAME_MAX_DEFER_MS = 3600000;

    /**
     * Maximum number of orphaned frames to process in a single pass. Bounds the work of a
     * fleet-wide event; the remainder is picked up on subsequent passes. Overridable via the
     * {@code maintenance.orphaned_frame_batch_size} property.
     */
    private static final int DEFAULT_ORPHANED_FRAME_BATCH_SIZE = 100;

    /** How long to wait between polls of RQD while confirming an orphaned frame is dead. */
    private static final long ORPHAN_KILL_POLL_INTERVAL_MS = 500;

    /**
     * Maximum number of orphaned procs to process in a single hardware-state pass. The orphan query
     * returns oldest-ping first, so when the orphan set exceeds this batch the longest-stale procs
     * are always the ones retried; procs whose release keeps being deferred occupy the batch until
     * they are released or hit the deferral bound ({@code dispatcher.lost_proc_max_defer_ms}).
     * Overridable via the {@code maintenance.orphaned_proc_batch_size} property.
     */
    private static final int DEFAULT_ORPHANED_PROC_BATCH_SIZE = 100;

    /**
     * Outcome of attempting to confirm an orphaned frame's render is dead.
     */
    private enum OrphanKillResult {
        /** The render is confirmed gone (or the frame never ran): safe to reset to WAITING. */
        CONFIRMED_DEAD,
        /**
         * The host could not be reached to confirm: fail closed (DEAD) rather than risk a rebook.
         */
        UNREACHABLE,
        /** Reachable but still running within the per-frame timeout: defer to the next pass. */
        STILL_RUNNING
    }

    private long dbConnectionFailureTime = 0;

    /**
     * Checks the cue for down hosts. If there are any down they are cleared of procs. Additionally
     * the orphaned proc check is done.
     *
     * If a DB Connection exception is thrown, its caught and the current time is noted. Once the DB
     * comes back up, down proc checks will not resume for WAIT_FOR_HOST_REPORTS_MS milliseconds.
     * This is to give procs a chance to report back in.
     *
     */
    public void checkHardwareState() {
        try {

            if (!maintenanceDao.lockTask(MaintenanceTask.LOCK_HARDWARE_STATE_CHECK)) {
                return;
            }
            try {
                if (dbConnectionFailureTime > 0) {
                    if (System.currentTimeMillis()
                            - dbConnectionFailureTime < WAIT_FOR_HOST_REPORTS_MS) {
                        logger.warn(
                                "NOT running checkHardwareState, waiting for hosts to report in.");
                        return;
                    }
                    dbConnectionFailureTime = 0;
                }

                int hosts = maintenanceDao.setUpHostsToDown();
                if (hosts > 0) {
                    clearDownProcs();

                    boolean autoDeleteDownHosts = env.getProperty(
                            "maintenance.auto_delete_down_hosts", Boolean.class, false);
                    if (autoDeleteDownHosts) {
                        hostDao.deleteDownHosts();
                    }
                }
                clearOrphanedProcs();
            } finally {
                maintenanceDao.unlockTask(MaintenanceTask.LOCK_HARDWARE_STATE_CHECK);
            }
        } catch (Exception e) {
            // This catch could be more specific using CannotGetJdbcConnectionException, but
            // we need
            // to catch a wider range of exceptions from HikariPool.
            // HikariPool will log this message very frequently with error level, the
            // following check
            // avoids polluting the logs by logging it twice
            if (!e.getMessage().contains("Exception during pool initialization")) {
                logger.warn("Error obtaining DB connection for hardware state check", e);
            }
            // If this fails, then the network went down, set the current time.
            dbConnectionFailureTime = System.currentTimeMillis();
        }
    }

    public void archiveFinishedJobs() {
        if (!maintenanceDao.lockTask(MaintenanceTask.LOCK_HISTORICAL_TRANSFER)) {
            return;
        }
        try {
            historicalSupport.archiveHistoricalJobData();
        } catch (Exception e) {
            logger.warn("failed to archive finished jobs: " + e);
        } finally {
            maintenanceDao.unlockTask(MaintenanceTask.LOCK_HISTORICAL_TRANSFER);
        }
    }

    private void clearOrphanedProcs() {
        int batchSize = env.getProperty("maintenance.orphaned_proc_batch_size", Integer.class,
                DEFAULT_ORPHANED_PROC_BATCH_SIZE);
        List<VirtualProc> procs = procDao.findOrphanedVirtualProcs(batchSize);
        for (VirtualProc proc : procs) {
            try {
                // Only report a cleanup when the proc was actually released; lostProc may defer the
                // release (leaving the proc intact) to avoid double-booking a flapping host.
                if (dispatchSupport.lostProc(proc, "Removed by maintenance, orphaned",
                        Dispatcher.EXIT_STATUS_FRAME_ORPHAN)) {
                    Sentry.withScope(scope -> {
                        scope.setExtra("frame_id", proc.getFrameId());
                        scope.setExtra("host_id", proc.getHostId());
                        scope.setExtra("name", proc.getName());
                        Sentry.captureMessage("Manager cleaning orphan procs");
                    });
                }
            } catch (Exception e) {
                logger.info("failed to clear orphaned proc: " + proc.getName() + " " + e);
            }
        }
    }

    /**
     * Clears orphaned frames (RUNNING with no proc).
     *
     * Runs on its own Quartz trigger under {@link MaintenanceTask#LOCK_ORPHANED_FRAME_CHECK} so it
     * neither shares nor starves the hardware-state check's budget or lock. Gated by
     * {@code maintenance.orphaned_frame_check_enabled} (default true).
     */
    public void clearOrphanedFrames() {
        if (!env.getProperty("maintenance.orphaned_frame_check_enabled", Boolean.class, true)) {
            return;
        }
        // Take a task lock so multiple Cuebots in a cluster don't run the sweep concurrently.
        if (!maintenanceDao.lockTask(MaintenanceTask.LOCK_ORPHANED_FRAME_CHECK)) {
            return;
        }
        try {
            doClearOrphanedFrames();
        } catch (Exception e) {
            logger.warn("failed to clear orphaned frames: " + e);
        } finally {
            maintenanceDao.unlockTask(MaintenanceTask.LOCK_ORPHANED_FRAME_CHECK);
        }
    }

    /**
     * Kills and clears orphaned frames within this pass's budget.
     *
     * A frame is orphaned when its proc was removed while RQD was still rendering. Before clearing
     * one we kill it on its last-known host and confirm the render is dead; only then is it reset
     * to WAITING (auto-retry). We never reset an unconfirmed frame, because rebooking it while the
     * original render may still be alive causes double booking. The outcomes are:
     *
     * <ul>
     * <li><b>Confirmed dead</b> (or the frame never ran): reset to WAITING for auto-retry.</li>
     * <li><b>Reachable but not dead yet</b>, or this pass's budget ran out before we could confirm:
     * the frame is deferred -- left RUNNING after a best-effort kill -- so the next pass retries
     * it. Because the kill was already sent, the next pass typically confirms death on its first
     * poll. This is safe against double booking (the dispatcher never books a RUNNING frame) and,
     * unlike DEAD, destroys no work. A single slow-to-exit render can no longer consume the whole
     * pass: a per-frame timeout ({@code maintenance.orphaned_frame_confirm_timeout_ms}) caps its
     * wait and defers it.</li>
     * <li><b>Host unreachable</b>, or the frame has been orphaned-and-unconfirmable longer than
     * {@code maintenance.orphaned_frame_max_defer_ms}: failed closed (DEAD) so it surfaces for a
     * manual retry rather than lingering RUNNING forever.</li>
     * </ul>
     *
     * The pass is bounded by {@code maintenance.orphaned_frame_kill_budget_ms} and
     * {@code maintenance.orphaned_frame_batch_size} so a fleet-wide event cannot stall maintenance
     * or be handled all at once.
     */
    private void doClearOrphanedFrames() {
        long killBudgetMs = env.getProperty("maintenance.orphaned_frame_kill_budget_ms", Long.class,
                DEFAULT_ORPHANED_FRAME_KILL_BUDGET_MS);
        long confirmTimeoutMs = env.getProperty("maintenance.orphaned_frame_confirm_timeout_ms",
                Long.class, DEFAULT_ORPHANED_FRAME_CONFIRM_TIMEOUT_MS);
        long maxDeferMs = env.getProperty("maintenance.orphaned_frame_max_defer_ms", Long.class,
                DEFAULT_ORPHANED_FRAME_MAX_DEFER_MS);
        int batchSize = env.getProperty("maintenance.orphaned_frame_batch_size", Integer.class,
                DEFAULT_ORPHANED_FRAME_BATCH_SIZE);
        long phaseDeadlineMs = System.currentTimeMillis() + killBudgetMs;
        int failedUnconfirmed = 0;
        int deferred = 0;

        List<FrameDetail> frames = frameDao.getOrphanedFrames(batchSize);
        for (FrameDetail frame : frames) {
            try {
                // Re-check orphanhood right before acting: between getOrphanedFrames() and this
                // frame's turn in the batch, a late FrameCompleteReport can finalize the frame and
                // the dispatcher can rebook it -- possibly onto the same host -- and the kill RPC
                // is fenced only by frameId, so killing without re-checking could kill the new
                // legitimate run.
                if (!frameDao.isOrphan(frame)) {
                    logger.info("frame " + frame.getName() + " is no longer orphaned; skipping.");
                    continue;
                }

                if (System.currentTimeMillis() >= phaseDeadlineMs) {
                    // Budget exhausted: no time to confirm death this pass. Still send a
                    // best-effort, non-blocking kill so the render is asked to stop, then defer the
                    // frame to the next pass. A frame that never ran (null host) has no render to
                    // confirm and is safe to reset now.
                    if (killFrameBestEffort(frame) == null) {
                        resetOrphanedFrame(frame, FrameState.WAITING);
                    } else if (isDeferExpired(frame, maxDeferMs)) {
                        if (resetOrphanedFrame(frame, FrameState.DEAD)) {
                            failedUnconfirmed++;
                        }
                    } else {
                        deferred++;
                    }
                    continue;
                }

                // Cap this frame's confirm wait at the per-frame timeout, but never past the pass
                // budget, so one slow render cannot starve the frames behind it.
                long frameDeadlineMs =
                        Math.min(System.currentTimeMillis() + confirmTimeoutMs, phaseDeadlineMs);
                switch (killAndConfirmDead(frame, frameDeadlineMs)) {
                    case CONFIRMED_DEAD:
                        resetOrphanedFrame(frame, FrameState.WAITING);
                        break;
                    case UNREACHABLE:
                        if (resetOrphanedFrame(frame, FrameState.DEAD)) {
                            failedUnconfirmed++;
                        }
                        break;
                    case STILL_RUNNING:
                    default:
                        // Reachable but not dead yet. Defer to the next pass unless it has been
                        // orphaned-and-unconfirmable too long, in which case fail it closed.
                        if (isDeferExpired(frame, maxDeferMs)) {
                            if (resetOrphanedFrame(frame, FrameState.DEAD)) {
                                failedUnconfirmed++;
                            }
                        } else {
                            deferred++;
                        }
                        break;
                }
            } catch (Exception e) {
                logger.info("failed to clear orphaned frame: " + frame.getName() + " " + e);
            }
        }

        if (deferred > 0) {
            logger.info(deferred + " orphaned frame(s) could not be confirmed dead within this "
                    + "pass's kill budget; they were left RUNNING (after a best-effort kill) and "
                    + "will be retried next pass.");
        }
        if (failedUnconfirmed > 0) {
            logger.warn(failedUnconfirmed + " orphaned frame(s) were marked DEAD because the "
                    + "original render could not be confirmed dead (host unreachable, or still "
                    + "unconfirmable after " + maxDeferMs
                    + "ms); they need a manual retry. Marking "
                    + "DEAD avoids double-booking them.");
        }
    }

    /**
     * Stops an orphaned frame into the given state. Returns whether the update actually applied:
     * the update is version-fenced, so {@code false} means a concurrent
     * {@code finalizeOrphanedFrameComplete} (or another actor) got to the frame first, in which
     * case the frame is no longer this pass's responsibility and must not be counted as failed.
     */
    private boolean resetOrphanedFrame(FrameDetail frame, FrameState state) {
        boolean applied =
                frameDao.updateFrameStopped(frame, state, Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
        if (!applied) {
            logger.info("orphaned frame " + frame.getName()
                    + " was concurrently finalized (version changed); not marking " + state + ".");
        }
        return applied;
    }

    /**
     * Returns whether an orphaned frame has been unconfirmable long enough to be failed closed
     * instead of deferred again. Age is measured from the frame's last update ({@code ts_updated}),
     * which stops advancing once the render's proc is gone, so it tracks how long the frame has
     * been orphaned. A frame with no recorded update timestamp is treated as not-yet-expired so the
     * non-destructive deferral path is preferred.
     */
    private boolean isDeferExpired(FrameDetail frame, long maxDeferMs) {
        if (frame.dateUpdated == null) {
            return false;
        }
        return System.currentTimeMillis() - frame.dateUpdated.getTime() > maxDeferMs;
    }

    /**
     * Kills an orphaned frame on its last-known host and waits, within the given deadline, for RQD
     * to confirm the frame is no longer running.
     *
     * The frame has no proc, so the host is recovered from the frame's last resource string.
     * Returns {@link OrphanKillResult#CONFIRMED_DEAD} when the render is gone (or the frame never
     * ran, so there is nothing to kill), {@link OrphanKillResult#UNREACHABLE} when the host cannot
     * be reached to confirm, and {@link OrphanKillResult#STILL_RUNNING} when the render is
     * reachable but has not exited by the deadline.
     */
    private OrphanKillResult killAndConfirmDead(FrameDetail frame, long deadlineMs) {
        String host = killFrameBestEffort(frame);
        // A null host means the frame never ran, so there is no render alive to confirm dead.
        if (host == null) {
            return OrphanKillResult.CONFIRMED_DEAD;
        }

        // do/while so we always poll at least once even when the deadline is already tight.
        do {
            try {
                if (!rqdClient.isFrameRunning(host, frame.getFrameId())) {
                    return OrphanKillResult.CONFIRMED_DEAD;
                }
            } catch (RqdClientException e) {
                logger.info("could not confirm orphaned frame " + frame.getName() + " is dead on "
                        + host + ", " + e);
                return OrphanKillResult.UNREACHABLE;
            }
            if (System.currentTimeMillis() >= deadlineMs) {
                break;
            }
            try {
                Thread.sleep(ORPHAN_KILL_POLL_INTERVAL_MS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return OrphanKillResult.STILL_RUNNING;
            }
        } while (System.currentTimeMillis() < deadlineMs);
        return OrphanKillResult.STILL_RUNNING;
    }

    /**
     * Sends a best-effort, non-blocking kill for an orphaned frame on its last-known host. Does not
     * wait for or confirm the render is dead, so it is safe to call even when the kill budget is
     * exhausted. Returns the host the kill was sent to, or {@code null} when the frame never ran
     * (nothing to kill).
     */
    private String killFrameBestEffort(FrameDetail frame) {
        // lastResource is "host/cores/gpus" (see FrameDaoJdbc.FRAME_DETAIL_MAPPER); empty if the
        // frame never ran, in which case there is no render alive to kill.
        if (frame.lastResource == null || frame.lastResource.isEmpty()) {
            return null;
        }
        String host = frame.lastResource.split("/")[0];
        if (host.isEmpty()) {
            return null;
        }

        try {
            rqdClient.killFrame(host, frame.getFrameId(),
                    "kill-before-reset: clearing orphaned frame");
        } catch (Exception e) {
            // Best effort: the host may already be gone. Any confirmation is left to the caller.
            logger.info(
                    "kill-before-reset failed for orphaned frame " + frame.getName() + ", " + e);
        }
        return host;
    }

    private void clearDownProcs() {
        List<VirtualProc> procs = procDao.findVirtualProcs(HardwareState.DOWN);
        logger.warn("found " + procs.size() + " that are down.");
        for (VirtualProc proc : procs) {
            try {
                dispatchSupport.lostProc(proc, proc.getName() + " was marked as down.",
                        Dispatcher.EXIT_STATUS_DOWN_HOST);
                FrameInterface f = frameDao.getFrame(proc.frameId);
                FrameDetail frameDetail = frameDao.getFrameDetail(f);
                Sentry.configureScope(scope -> {
                    scope.setExtra("host", proc.getName());
                    scope.setExtra("procId", proc.getProcId());
                    scope.setExtra("frame Name", frameDetail.getName());
                    scope.setExtra("frame Exit Status", String.valueOf(frameDetail.exitStatus));
                    scope.setExtra("Frame Job ID", frameDetail.getJobId());
                    Sentry.captureMessage("MaintenanceManager proc removed due to host offline");
                });
            } catch (Exception e) {
                logger.info("failed to down  proc: " + proc.getName() + " " + e);
            }
        }
    }

    public void clearStaleCheckpoints() {
        logger.info("Checking for stale checkpoint frames.");
        if (!maintenanceDao.lockTask(MaintenanceTask.LOCK_STALE_CHECKPOINT)) {
            return;
        }
        try {
            List<FrameInterface> frames = jobManager.getStaleCheckpoints(CHECKPOINT_MAX_WAIT_SEC);
            logger.warn("found " + frames.size() + " frames that failed to checkpoint");
            for (FrameInterface frame : frames) {
                jobManager.updateCheckpointState(frame, CheckpointState.DISABLED);
                jobManager.updateFrameState(frame, FrameState.WAITING);
            }
        } catch (Exception e) {
            logger.warn("failed to unlock stale checkpoint " + e);
        } finally {
            maintenanceDao.unlockTask(MaintenanceTask.LOCK_STALE_CHECKPOINT);
        }
    }

    public void updateTaskValues() {
        if (!maintenanceDao.lockTask(MaintenanceTask.LOCK_TASK_UPDATE, 700)) {
            return;
        }
        try {
            logger.info("running task updates");
            for (PointDetail pd : departmentManager.getManagedPointConfs()) {
                departmentManager.updateManagedTasks(pd);
            }
        } catch (Exception e) {
            logger.warn("failed to archive finished jobs: " + e);
        } finally {
            maintenanceDao.unlockTask(MaintenanceTask.LOCK_TASK_UPDATE);
        }
    }

    /**
     * Recalculates subscription core usage values to fix accountability issues that can occur at
     * large scale. This calls the recalculate_subs() database function that was added in PR #1380.
     */
    public void recalculateSubscriptions() {
        if (!maintenanceDao.lockTask(MaintenanceTask.LOCK_SUBSCRIPTION_RECALCULATION)) {
            return;
        }
        try {
            logger.info("running subscription recalculation");
            maintenanceDao.recalculateSubscriptions();
            logger.info("subscription recalculation completed");
        } catch (Exception e) {
            logger.warn("failed to recalculate subscriptions: " + e);
        } finally {
            maintenanceDao.unlockTask(MaintenanceTask.LOCK_SUBSCRIPTION_RECALCULATION);
        }
    }

    /**
     * Recovers frames stuck in DEPEND state due to transient failures during dependency
     * satisfaction. Runs in two phases:
     *
     * Phase 1: Finds active depends whose depended-on entity is already complete and satisfies them
     * through the normal code path (handles composite depends and publishes events). Each
     * {@code satisfyDepend} call runs in its own transaction via {@code DependManagerService}'s
     * {@code @Transactional}, providing per-depend isolation.
     *
     * Phase 2: Fixes frames still stuck in DEPEND by resetting int_depend_count to 0 where no
     * active depends target them. The DB trigger {@code update_frame_dep_to_wait} handles the
     * DEPEND to WAITING transition. This UPDATE auto-commits as a single statement transaction.
     */
    public void recoverStuckDependencies() {
        if (!env.getProperty("maintenance.stuck_dependency_recovery_enabled", Boolean.class,
                true)) {
            return;
        }

        // Use a MaintenanceTask lock to prevent multiple instances from racing each other
        if (!maintenanceDao.lockTask(MaintenanceTask.LOCK_STUCK_DEPENDENCY_RECOVERY)) {
            return;
        }
        try {
            int batchSize = env.getProperty("maintenance.stuck_dependency_recovery_batch_size",
                    Integer.class, 1000);
            // Mirror FrameCompleteHandler's runtime behavior: when this flag is true (default)
            // EATEN frames must not satisfy dependencies, so they are excluded from the sweep.
            boolean satisfyOnlyOnFrameSuccess =
                    env.getProperty("depend.satisfy_only_on_frame_success", Boolean.class, true);

            // Phase 1: Satisfy stale active depends through normal code path
            List<String> staleDependIds =
                    maintenanceDao.findStaleDependIds(batchSize, !satisfyOnlyOnFrameSuccess);
            int satisfiedCount = 0;
            for (String dependId : staleDependIds) {
                try {
                    LightweightDependency depend = dependManager.getDepend(dependId);
                    dependManager.satisfyDepend(depend);
                    satisfiedCount++;
                } catch (Exception e) {
                    logger.warn("failed to satisfy stale depend " + dependId + ": " + e);
                }
            }
            if (satisfiedCount > 0) {
                logger.info("recovered " + satisfiedCount + " stale active depends");
            }

            // Phase 2: Fix count mismatches via SQL
            int fixedFrames = maintenanceDao.fixStuckDependCounts(batchSize);
            if (fixedFrames > 0) {
                logger.info("fixed depend counts for " + fixedFrames + " stuck frames");
            }
        } catch (Exception e) {
            logger.warn("failed to recover stuck dependencies: " + e);
        } finally {
            maintenanceDao.unlockTask(MaintenanceTask.LOCK_STUCK_DEPENDENCY_RECOVERY);
        }
    }

    public FrameDao getFrameDao() {
        return frameDao;
    }

    public void setFrameDao(FrameDao frameDao) {
        this.frameDao = frameDao;
    }

    public void setHostDao(HostDao hostDao) {
        this.hostDao = hostDao;
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public MaintenanceDao getMaintenanceDao() {
        return maintenanceDao;
    }

    public void setMaintenanceDao(MaintenanceDao maintenanceDao) {
        this.maintenanceDao = maintenanceDao;
    }

    public ProcDao getProcDao() {
        return procDao;
    }

    public void setProcDao(ProcDao procDao) {
        this.procDao = procDao;
    }

    public HistoricalSupport getHistoricalSupport() {
        return historicalSupport;
    }

    public void setHistoricalSupport(HistoricalSupport historicalSupport) {
        this.historicalSupport = historicalSupport;
    }

    public DepartmentManager getDepartmentManager() {
        return departmentManager;
    }

    public void setDepartmentManager(DepartmentManager departmentManager) {
        this.departmentManager = departmentManager;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public RqdClient getRqdClient() {
        return rqdClient;
    }

    public void setRqdClient(RqdClient rqdClient) {
        this.rqdClient = rqdClient;
    }

}
