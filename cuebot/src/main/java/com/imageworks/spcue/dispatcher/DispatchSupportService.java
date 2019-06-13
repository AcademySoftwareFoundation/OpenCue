
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

import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.AllocationInterface;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.FacilityInterface;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ProcInterface;
import com.imageworks.spcue.ResourceUsage;
import com.imageworks.spcue.ShowInterface;
import com.imageworks.spcue.StrandedCores;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.BookingDao;
import com.imageworks.spcue.dao.DispatcherDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.SubscriptionDao;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.rqd.RunFrame;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.service.BookingManager;
import com.imageworks.spcue.service.DependManager;

@Service
@Transactional(propagation = Propagation.REQUIRED)
public class DispatchSupportService implements DispatchSupport {
    private static final Logger logger = Logger.getLogger(DispatchSupportService.class);

    @Autowired
    private JobDao jobDao;

    @Autowired
    private FrameDao frameDao;

    @Autowired
    private LayerDao layerDao;

    @Autowired
    private ProcDao procDao;

    @Autowired
    private HostDao hostDao;

    @Autowired
    private ShowDao showDao;

    @Autowired
    private DispatcherDao dispatcherDao;

    @Autowired
    private DependManager dependManager;

    @Autowired
    private SubscriptionDao subscriptionDao;

    @Autowired
    private RqdClient rqdClient;

    @Autowired
    private RedirectManager redirectManager;

    @Autowired
    private BookingManager bookingManager;

    @Autowired
    private BookingDao bookingDao;

    private ConcurrentHashMap<String, StrandedCores> strandedCores =
        new ConcurrentHashMap<String, StrandedCores>();

    @Override
    public void pickupStrandedCores(DispatchHost host) {
        logger.info(host + "picked up stranded cores");
        pickedUpCoresCount.getAndIncrement();
        strandedCores.remove(host.getHostId());
    }

    @Override
    public boolean hasStrandedCores(HostInterface host) {
        StrandedCores stranded = strandedCores.get(host.getHostId());
        if (stranded == null) {
            return false;
        }
        if (stranded.isExpired()) {
            return false;
        }

        return true;
    }

    @Override
    public void strandCores(DispatchHost host, int cores) {
        logger.info(host + " found " + cores + ", stranded cores");
        host.strandedCores  = cores;
        if (host.threadMode != ThreadMode.VARIABLE.getNumber()) {
            host.threadMode = ThreadMode.ALL.getNumber();
        }
        strandedCores.putIfAbsent(host.getHostId(), new StrandedCores(cores));
        strandedCoresCount.getAndIncrement();
    }

    @Transactional(readOnly = true)
    public List<DispatchFrame> findNextDispatchFrames(JobInterface job, VirtualProc proc, int limit) {
        return dispatcherDao.findNextDispatchFrames(job, proc, limit);
    }

    @Transactional(readOnly = true)
    public List<DispatchFrame> findNextDispatchFrames(JobInterface job, DispatchHost host, int limit) {
        return dispatcherDao.findNextDispatchFrames(job, host, limit);
    }

    @Override
    @Transactional(readOnly = true)
    public List<DispatchFrame> findNextDispatchFrames(LayerInterface layer,
            DispatchHost host, int limit) {
        return dispatcherDao.findNextDispatchFrames(layer, host, limit);
    }

    @Override
    @Transactional(readOnly = true)
    public List<DispatchFrame> findNextDispatchFrames(LayerInterface layer,
            VirtualProc proc, int limit) {
        return dispatcherDao.findNextDispatchFrames(layer, proc, limit);
    }

    @Transactional(readOnly = true)
    public boolean findUnderProcedJob(JobInterface excludeJob, VirtualProc proc) {
        return dispatcherDao.findUnderProcedJob(excludeJob, proc);
    }

    @Transactional(readOnly = true)
    public boolean higherPriorityJobExists(JobDetail baseJob, VirtualProc proc) {
        return dispatcherDao.higherPriorityJobExists(baseJob, proc);
    }

    @Transactional(readOnly = true)
    public Set<String> findDispatchJobsForAllShows(DispatchHost host, int numJobs) {
        return dispatcherDao.findDispatchJobsForAllShows(host, numJobs);
    }

    @Transactional(readOnly = true)
    public Set<String> findDispatchJobs(DispatchHost host, int numJobs) {
        return dispatcherDao.findDispatchJobs(host, numJobs);
    }

    @Transactional(readOnly = true)
    public Set<String> findDispatchJobs(DispatchHost host, GroupInterface g) {
        return dispatcherDao.findDispatchJobs(host, g);
    }

    @Override
    @Transactional(readOnly = true)
    public Set<String> findLocalDispatchJobs(DispatchHost host) {
        return dispatcherDao.findLocalDispatchJobs(host);
    }

    @Override
    @Transactional(readOnly = true)
    public Set<String> findDispatchJobs(DispatchHost host, ShowInterface show,
            int numJobs) {
        return dispatcherDao.findDispatchJobs(host, show, numJobs);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public boolean increaseReservedMemory(ProcInterface p, long value) {
        return procDao.increaseReservedMemory(p, value);
    }

    @Override
    public boolean clearVirtualProcAssignement(ProcInterface proc) {
        return procDao.clearVirtualProcAssignment(proc);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public boolean balanceReservedMemory(ProcInterface targetProc, long targetMem) {
        boolean result = procDao.balanceUnderUtilizedProcs(targetProc, targetMem);
        if (result) {
            DispatchSupport.balanceSuccess.incrementAndGet();
        }
        else {
            DispatchSupport.balanceFailed.incrementAndGet();
        }
        return result;
    }

    @Transactional(propagation = Propagation.NEVER)
    public void runFrame(VirtualProc proc, DispatchFrame frame) {
        try {
            rqdClient.launchFrame(prepareRqdRunFrame(proc, frame), proc);
            dispatchedProcs.getAndIncrement();
        }
        catch (Exception e) {
            throw new DispatcherException(proc.getName() +
                    " could not be booked on " + frame.getName() + ", " + e);
        }
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isCueBookable(FacilityInterface f) {
        return jobDao.cueHasPendingJobs(f);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isJobDispatchable(JobInterface job, boolean local) {

        if (!jobDao.hasPendingFrames(job)) {
            return false;
        }

        if (!local && jobDao.isOverMaxCores(job)) {
            return false;
        }

        return true;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isJobBookable(JobInterface job) {

        if (!jobDao.hasPendingFrames(job)) {
            return false;
        }

        if (jobDao.isAtMaxCores(job)) {
            return false;
        }

        return true;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isJobBookable(JobInterface job, int coreUnits) {

        if (!jobDao.hasPendingFrames(job)) {
            return false;
        }

        if (jobDao.isOverMaxCores(job, coreUnits)) {
            return false;
        }

        return true;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean hasPendingFrames(JobInterface job) {

        if (!jobDao.hasPendingFrames(job)) {
            return false;
        }

        return true;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean hasPendingFrames(LayerInterface layer) {
        return layerDao.isLayerDispatchable(layer);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isShowOverBurst(VirtualProc proc) {
        return subscriptionDao.isShowOverBurst((ShowInterface) proc, (AllocationInterface) proc, 0);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isShowOverBurst(ShowInterface show, AllocationInterface alloc, int coreUnits) {
        return subscriptionDao.isShowOverBurst(show, alloc, coreUnits);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isShowAtOrOverBurst(ShowInterface show, AllocationInterface alloc) {
        return subscriptionDao.isShowAtOrOverBurst(show, alloc);
    }


    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isShowOverSize(VirtualProc proc) {
        return subscriptionDao.isShowOverSize(proc);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public boolean stopFrame(FrameInterface frame, FrameState state,
                             int exitStatus) {
        logger.trace("stopping frame " + frame);
        if (frameDao.updateFrameStopped(frame, state, exitStatus)) {
            procDao.clearVirtualProcAssignment(frame);
            return true;
        }

        return false;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public boolean stopFrame(FrameInterface frame, FrameState state,
                             int exitStatus, long maxRss) {
        logger.trace("stopping frame: " + frame);
        if (frameDao.updateFrameStopped(frame, state,
                exitStatus, maxRss)) {
            // Update max rss up the chain.
            layerDao.updateLayerMaxRSS(frame, maxRss, false);
            jobDao.updateMaxRSS(frame, maxRss);

            procDao.clearVirtualProcAssignment(frame);
            return true;
        }

        return false;
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void clearFrame(DispatchFrame frame) {
        logger.trace("clearing frame: " + frame);
        frameDao.updateFrameCleared(frame);
    }

    @Transactional(propagation = Propagation.SUPPORTS)
    public RunFrame prepareRqdRunFrame(VirtualProc proc, DispatchFrame frame) {
        int threads =  proc.coresReserved / 100;
        if (threads < 1) {
            threads = 1;
        }

        int frameNumber = Integer.valueOf(frame.name.substring(0,frame.name.indexOf("-")));
        String zFrameNumber = String.format("%04d", frameNumber);

        return RunFrame.newBuilder()
                .setShot(frame.shot)
                .setShow(frame.show)
                .setUserName(frame.owner)
                .setUid(frame.uid)
                .setLogDir(frame.logDir)
                .setJobId(frame.jobId)
                .setJobName(frame.jobName)
                .setFrameId(frame.id)
                .setFrameName(frame.name)
                .setLayerId(frame.getLayerId())
                .setResourceId(proc.getProcId())
                .setNumCores(proc.coresReserved)
                .setStartTime(System.currentTimeMillis())
                .setIgnoreNimby(proc.isLocalDispatch)
                .putAllEnvironment(jobDao.getEnvironment(frame))
                .putAllEnvironment(layerDao.getLayerEnvironment(frame))
                .putEnvironment("CUE3", "1")
                .putEnvironment("CUE_THREADS", String.valueOf(threads))
                .putEnvironment("CUE_MEMORY", String.valueOf(proc.memoryReserved))
                .putEnvironment("CUE_LOG_PATH", frame.logDir)
                .putEnvironment("CUE_RANGE", frame.range)
                .putEnvironment("CUE_CHUNK", String.valueOf(frame.chunkSize))
                .putEnvironment("CUE_IFRAME", String.valueOf(frameNumber))
                .putEnvironment("CUE_LAYER", frame.layerName)
                .putEnvironment("CUE_JOB", frame.jobName)
                .putEnvironment("CUE_FRAME", frame.name)
                .putEnvironment("CUE_SHOW", frame.show)
                .putEnvironment("CUE_SHOT", frame.shot)
                .putEnvironment("CUE_USER", frame.owner)
                .putEnvironment("CUE_JOB_ID", frame.jobId)
                .putEnvironment("CUE_LAYER_ID", frame.layerId)
                .putEnvironment("CUE_FRAME_ID", frame.id)
                .putEnvironment("CUE_THREADABLE", frame.threadable ? "1" : "0")
                .setCommand(
                        frame.command
                                .replaceAll("#ZFRAME#", zFrameNumber)
                                .replaceAll("#IFRAME#",  String.valueOf(frameNumber))
                                .replaceAll("#LAYER#", frame.layerName)
                                .replaceAll("#JOB#",  frame.jobName)
                                .replaceAll("#FRAME#",  frame.name))
                .build();
    }


    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void startFrame(VirtualProc proc, DispatchFrame frame) {
        logger.trace("starting frame: " + frame);
        frameDao.updateFrameStarted(proc, frame);
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void fixFrame(DispatchFrame frame) {
        long numFixed = DispatchSupport.fixedFrames.incrementAndGet();

        logger.trace("fixing frame #: " + numFixed + " ," + frame);

        VirtualProc proc = null;
        try {
            proc = procDao.findVirtualProc(frame);
        }
        catch (Exception e) {
            // Can't even find the damn proc, which i'm
            logger.info("attempted to fix a frame but the proc " +
                    "wasn't found!");
            return;
        }

        if (frameDao.updateFrameFixed(proc, frame)){
            logger.info("the frame " + frame.getId() + " was fixed.");
        }
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void updateUsageCounters(FrameInterface frame, int exitStatus) {
        try {
            ResourceUsage usage = frameDao.getResourceUsage(frame);
            showDao.updateFrameCounters(frame, exitStatus);
            jobDao.updateUsage(frame, usage, exitStatus);
            layerDao.updateUsage(frame, usage, exitStatus);
        } catch (Exception e) {
            logger.info("Unable to find and update resource usage for " +
                    "frame, " + frame + " while updating frame with " +
                    "exit status " + exitStatus + ","  + e);
        }
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void reserveProc(VirtualProc proc, DispatchFrame frame) {

        proc.jobId = frame.getJobId();
        proc.frameId = frame.getFrameId();
        proc.layerId = frame.getLayerId();
        proc.showId = frame.getShowId();

        if (proc.isNew()) {
            logger.info("creating proc " + proc.getName() + " for " +
                    frame.getName());
            procDao.insertVirtualProc(proc);
        }
        else {
            logger.info("updated proc " + proc.getName() + " for " +
                    frame.getName());
            procDao.updateVirtualProcAssignment(proc);
        }
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void unbookProc(VirtualProc proc) {
        unbookProc(proc, "was unbooked");
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void unbookProc(VirtualProc proc,  String reason) {
        if (proc == null) { return; }
        if (proc.isNew()) { return; }
        proc.unbooked = true;
        procDao.deleteVirtualProc(proc);
        DispatchSupport.unbookedProcs.getAndIncrement();
        logger.info(proc + " " + reason);

        /*
         * Remove the local dispatch record if it has gone inactive.
         */
        if (proc.isLocalDispatch) {
            try {
                bookingManager.removeInactiveLocalHostAssignment(
                    bookingDao.getLocalJobAssignment(proc.getHostId(), proc.getJobId()));
            }
            catch (EmptyResultDataAccessException e) {
                // Eat the exception.
            }
        }
    }

    @Override
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void lostProc(VirtualProc proc, String reason, int exitStatus) {
        long numCleared = clearedProcs.incrementAndGet();

        unbookProc(proc,"proc " + proc.getName() +
                " is #" + numCleared + " cleared: " + reason);

        if (proc.frameId != null) {
            FrameInterface f = frameDao.getFrame(proc.frameId);
            /*
             * Set the checkpoint state to disabled before stopping the
             * the frame because it will go to the checkpoint state.
             * This is not desirable when we're clearing off processes
             * that were lost due to a machine crash.
             */
            frameDao.updateFrameCheckpointState(f, CheckpointState.DISABLED);
            /*
             * If the proc has a frame, stop the frame.  Frames
             * can only be stopped that are running, so if the frame
             * is not running it will remain untouched.
             */
            if (frameDao.updateFrameStopped(f,
                    FrameState.WAITING, exitStatus)) {
                updateUsageCounters(proc, exitStatus);
            }
        }
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void updateProcMemoryUsage(FrameInterface frame, long rss, long maxRss,
                                      long vsize, long maxVsize) {
        procDao.updateProcMemoryUsage(frame, rss, maxRss, vsize, maxVsize);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void updateFrameMemoryUsage(FrameInterface frame, long rss, long maxRss) {

        try {
            frameDao.updateFrameMemoryUsage(frame, maxRss, rss);
        }
        catch (FrameReservationException ex) {
            // Eat this, the frame was not in the correct state or
            // was locked by another thread. The only reason it would
            // be locked by another thread would be if the state is
            // changing.
            logger.warn("failed to update memory stats for frame: " + frame);
        }
    }

    @Override
    public void determineIdleCores(DispatchHost host, int load) {
        int maxLoad = host.cores + ((host.cores / 100) *
                Dispatcher.CORE_LOAD_THRESHOLD);

        int idleCores = maxLoad - load;
        if (idleCores < host.idleCores) {
            host.idleCores = idleCores;
        }
    }
}

