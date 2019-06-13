
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



package com.imageworks.spcue.service;

import java.util.List;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.CannotGetJdbcConnectionException;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.MaintenanceTask;
import com.imageworks.spcue.PointDetail;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.MaintenanceDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameState;
import org.springframework.stereotype.Service;

@Service
public class MaintenanceManagerSupport {

    private static final Logger logger = Logger.getLogger(MaintenanceManagerSupport.class);

    @Autowired
    private MaintenanceDao maintenanceDao;

    @Autowired
    private ProcDao procDao;

    @Autowired
    private FrameDao frameDao;

    @Autowired
    private JobManager jobManager;

    @Autowired
    private DispatchSupport dispatchSupport;

    @Autowired
    private HistoricalSupport historicalSupport;

    private static final long WAIT_FOR_HOST_REPORTS_MS = 600000;

    private static final int CHECKPOINT_MAX_WAIT_SEC = 300;

    private long dbConnectionFailureTime = 0;

    /**
     * Checks the cue for down hosts. If there are any down they are cleared of
     * procs. Additionally the orphaned proc check is done.
     *
     * If a DB Connection exception is thrown, its caught and the current time
     * is noted. Once the DB comes back up, down proc checks will not resume for
     * WAIT_FOR_HOST_REPORTS_MS milliseconds. This is to give procs a chance to
     * report back in.
     *
     */
    public void checkHardwareState() {
        try {

            if (!maintenanceDao
                    .lockTask(MaintenanceTask.LOCK_HARDWARE_STATE_CHECK)) {
                return;
            }
            try {
                if (dbConnectionFailureTime > 0) {
                    if (System.currentTimeMillis() - dbConnectionFailureTime < WAIT_FOR_HOST_REPORTS_MS) {
                        logger.warn("NOT running checkHardwareState, waiting for hosts to report in.");
                        return;
                    }
                    dbConnectionFailureTime = 0;
                }

                int hosts = maintenanceDao.setUpHostsToDown();
                if (hosts > 0) {
                    clearDownProcs();
                }
                clearOrphanedProcs();
            } finally {
                maintenanceDao
                        .unlockTask(MaintenanceTask.LOCK_HARDWARE_STATE_CHECK);
            }
        } catch (CannotGetJdbcConnectionException db) {
            logger.warn("error obtaining DB connection for hardware state check");
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
        List<VirtualProc> procs = procDao.findOrphanedVirtualProcs(100);
        for (VirtualProc proc: procs) {
            try {
                dispatchSupport.lostProc(proc,
                        "Removed by maintenance, orphaned",
                        Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
            } catch (Exception e) {
                logger.info("failed to clear orphaned proc: " + proc.getName() + " " + e);
            }
        }

        List<FrameInterface> frames = frameDao.getOrphanedFrames();
        for (FrameInterface frame: frames) {
            try {
                frameDao.updateFrameStopped(frame, FrameState.WAITING,
                        Dispatcher.EXIT_STATUS_FRAME_ORPHAN);
            } catch (Exception e) {
                logger.info("failed to clear orphaned frame: " +
                        frame.getName() + " " + e);
            }
        }
    }

    private void clearDownProcs() {
        List<VirtualProc> procs = procDao.findVirtualProcs(HardwareState.DOWN);
        logger.warn("found " + procs.size() + " that are down.");
        for (VirtualProc proc: procs) {
            try {
                dispatchSupport.lostProc(proc,
                        proc.getName() + " was marked as down.",
                        Dispatcher.EXIT_STATUS_DOWN_HOST);
            } catch (Exception e) {
                logger.info("failed to down  proc: " + proc.getName() + " " + e);
            }
        }
    }

    public void clearStaleCheckpoints() {
        logger.info("Checking for stale checkpoint frames.");
        if (!maintenanceDao.lockTask(MaintenanceTask.LOCK_STALE_CHECKPOINT)) { return; }
        try {
            List<FrameInterface> frames = jobManager.getStaleCheckpoints(CHECKPOINT_MAX_WAIT_SEC);
            logger.warn("found " + frames.size() + " frames that failed to checkpoint");
            for (FrameInterface frame: frames) {
                jobManager.updateCheckpointState(frame, CheckpointState.DISABLED);
                jobManager.updateFrameState(frame, FrameState.WAITING);
            }
        } catch (Exception e) {
            logger.warn("failed to unlock stale checkpoint " + e);
        } finally {
            maintenanceDao.unlockTask(MaintenanceTask.LOCK_STALE_CHECKPOINT);
        }
    }

    public FrameDao getFrameDao() {
        return frameDao;
    }

    public void setFrameDao(FrameDao frameDao) {
        this.frameDao = frameDao;
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

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

}

