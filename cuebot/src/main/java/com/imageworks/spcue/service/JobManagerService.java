
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

import com.google.common.collect.Sets;
import org.apache.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.imageworks.spcue.BuildableDependency;
import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.BuildableLayer;
import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.EntityRetrievalException;
import com.imageworks.spcue.ExecutionSummary;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.FrameStateTotals;
import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.JobLaunchException;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.ShowEntity;
import com.imageworks.spcue.ThreadStats;
import com.imageworks.spcue.dao.FacilityDao;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.ShowDao;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.job.CheckpointState;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.job.JobState;
import com.imageworks.spcue.grpc.job.Order;
import com.imageworks.spcue.util.CueUtil;
import com.imageworks.spcue.util.FrameSet;
import com.imageworks.spcue.util.JobLogUtil;

@Service
@Transactional
public class JobManagerService implements JobManager {

    private static final Logger logger = Logger.getLogger(JobManagerService.class);

    @Autowired
    private JobDao jobDao;

    @Autowired
    private ShowDao showDao;

    @Autowired
    private FrameDao frameDao;

    @Autowired
    private LayerDao layerDao;

    @Autowired
    private HostDao hostDao;

    @Autowired
    private DependManager dependManager;

    @Autowired
    private FilterManager filterManager;

    @Autowired
    private GroupDao groupDao;

    @Autowired
    private FacilityDao facilityDao;

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isJobComplete(JobInterface job) {
        return jobDao.isJobComplete(job);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isLayerComplete(LayerInterface layer) {
        return layerDao.isLayerComplete(layer);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isLayerThreadable(LayerInterface layer) {
        return layerDao.isThreadable(layer);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isJobPending(String name) {
        return jobDao.exists(name);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void removeJob(JobInterface job) {
        jobDao.deleteJob(job);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public JobDetail getJobDetail(String id) {
        return jobDao.getJobDetail(id);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public JobInterface getJob(String id) {
        return jobDao.getJob(id);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public JobDetail findJobDetail(String name) {
        return jobDao.findJobDetail(name);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public JobInterface findJob(String name) {
        return jobDao.findJob(name);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public boolean isOverMinCores(JobInterface job) {
        return jobDao.isOverMinCores(job);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public DispatchJob getDispatchJob(String id) {
        return jobDao.getDispatchJob(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameInterface getFrame(String id) {
        return frameDao.getFrame(id);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameInterface findFrame(LayerInterface layer, int number) {
        return frameDao.findFrame(layer, number);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public DispatchFrame getDispatchFrame(String id) {
        return frameDao.getDispatchFrame(id);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public JobDetail findLastJob(String name) {
        return jobDao.findLastJob(name);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void setJobPaused(JobInterface job, boolean paused) {
        jobDao.updatePaused(job, paused);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void launchJobSpec(JobSpec spec) {

        for (BuildableJob job: spec.getJobs()) {

            JobDetail d = createJob(job);
            if (job.getPostJob() != null) {
                BuildableJob postJob = job.getPostJob();
                postJob.env.put("CUE_PARENT_JOB_ID", d.id);
                postJob.env.put("CUE_PARENT_JOB", d.name);
                createJob(postJob);
                jobDao.mapPostJob(job);
            }
        }

        for (BuildableDependency dep: spec.getDepends()) {
            dep.setLaunchDepend(true);
            dependManager.createDepend(dep);
        }

        for (BuildableJob job: spec.getJobs()) {
            jobDao.activateJob(job.detail, JobState.PENDING);
            if (job.getPostJob() != null) {
                jobDao.activateJob(job.getPostJob().detail, JobState.POSTED);
            }
        }
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public JobDetail createJob(BuildableJob buildableJob) {

        logger.info("creating new job: " + buildableJob.detail.name);
        long startTime = System.currentTimeMillis();

        if (jobDao.exists(buildableJob.detail.name)) {
            throw new JobLaunchException("error launching job, active job already exists: " +
                    buildableJob.detail.name);
        }

        if (buildableJob.getBuildableLayers().size() < 1) {
            throw new JobLaunchException("error launching job, there were no layers defined!");
        }

        JobDetail job = buildableJob.detail;

        try {
            /*
             * Get the last job with the same name and try to use
             * the memory settings for that job.  Do this before
             * inserting the new job we'll find this job as the last job.
             */
            JobDetail lastJob = null;
            try {
                lastJob = findLastJob(job.name);
                logger.info("Last job " + job.name + " was found as " + lastJob.name);
            } catch (Exception e) {
                logger.info("Last job " + job.name + " was NOT found");
                // don't have another version of the job in the DB.
            }

            ShowEntity show = showDao.findShowDetail(job.showName);
            if (!job.isPaused) { job.isPaused = show.paused; }

            job.showId = show.id;
            job.logDir = job.name;

            /*
             * The job gets inserted into the root group and
             * unknown department.
             */
            GroupDetail rootGroup = groupDao.getRootGroupDetail(job);
            job.groupId = rootGroup.id;
            job.deptId = rootGroup.deptId;

            resolveFacility(job);

            jobDao.insertJob(job);
            jobDao.insertEnvironment(job, buildableJob.env);

            for (BuildableLayer buildableLayer: buildableJob.getBuildableLayers()) {

                LayerDetail layer = buildableLayer.layerDetail;
                layer.jobId = job.id;
                layer.showId = show.id;

                /** Not accurate anymore */
                List<Integer> frames = CueUtil.normalizeFrameRange(layer.range,
                        layer.chunkSize);
                layer.totalFrameCount = frames.size();

                if (lastJob != null && !buildableLayer.isMemoryOverride) {
                    long pastMaxRSS = layerDao.findPastMaxRSS(lastJob, layer.name);
                    if (pastMaxRSS > 0) {
                        logger.info("found new maxRSS for layer: " + layer.name + " " + pastMaxRSS);
                        layer.minimumMemory = pastMaxRSS;
                    }
                }

                if (layer.minimumCores < Dispatcher.CORE_POINTS_RESERVED_MIN) {
                    layer.minimumCores =  Dispatcher.CORE_POINTS_RESERVED_MIN;
                }

                logger.info("creating layer " + layer.name + " range: " + layer.range);
                layerDao.insertLayerDetail(layer);
                layerDao.insertLayerEnvironment(layer, buildableLayer.env);
                frameDao.insertFrames(layer, frames);
            }

            /*
             * Finally, run any filters on the job which may set the job's
             * priority.
             */
            filterManager.runFiltersOnJob(job);

            CueUtil.logDuration(startTime, "created job " + job.getName() + " " + job.getId());
            return job;

        } catch (Exception e) {
            logger.info("error launching job: " + job.name + "," + e);
            throw new JobLaunchException("error launching job: " + job.name + "," + e, e);
        }
    }

    private void resolveFacility(JobDetail job) {
        try {
            if (job.facilityName == null) {
                job.facilityId =
                    facilityDao.getDefaultFacility().getId();
            }
            else {
                job.facilityId =
                    facilityDao.getFacility(job.facilityName).getId();
            }
        } catch (Exception e) {
            throw new EntityRetrievalException("failed to find facility: " + job.facilityName, e);
        }
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public boolean shutdownJob(JobInterface job) {
        // See JobManagerSupport
        if (jobDao.updateJobFinished(job)) {
            logger.info("shutting down job: " + job.getName());
            jobDao.activatePostJob(job);
            logger.info("activating post jobs");
            return true;
        }
        return false;
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<FrameInterface> findFrames(FrameSearchInterface r) {
        return frameDao.findFrames(r);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void updateFrameState(FrameInterface frame, FrameState state) {
        frameDao.updateFrameState(frame, state);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public LayerDetail getLayerDetail(String id) {
        return layerDao.getLayerDetail(id);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public LayerInterface getLayer(String id) {
        return layerDao.getLayer(id);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameDetail getFrameDetail(String id) {
        return frameDao.getFrameDetail(id);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void markFrameAsWaiting(FrameInterface frame) {
        frameDao.markFrameAsWaiting(frame);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void markFrameAsDepend(FrameInterface frame) {
        frameDao.markFrameAsDepend(frame);
    }

    /**
     * Creates a new job log directory.  This is only called
     * when launching a job.
     *
     * @param job
     */
    @Transactional(propagation = Propagation.NEVER)
    public void createJobLogDirectory(JobDetail job) {
        if (!JobLogUtil.createJobLogDirectory(job.logDir)) {
            throw new JobLaunchException("error launching job, unable to create log directory");
        }
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<LayerInterface> getLayers(JobInterface job) {
        return layerDao.getLayers(job);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void increaseLayerMemoryRequirement(LayerInterface layer, long memKb) {
        layerDao.increaseLayerMinMemory(layer, memKb);
    }

    @Transactional(propagation = Propagation.REQUIRED)
    public void reorderLayer(LayerInterface layer, FrameSet frameSet, Order order) {
        switch(order) {
            case FIRST:
                frameDao.reorderFramesFirst(layer, frameSet);
                break;
            case LAST:
                frameDao.reorderFramesLast(layer, frameSet);
                break;
            case REVERSE:
                frameDao.reorderLayerReverse(layer, frameSet);
                break;
        }
    }

    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public void staggerLayer(LayerInterface layer, String range, int stagger) {
        frameDao.staggerLayer(layer, range, stagger);
    }

    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<LayerDetail> getLayerDetails(JobInterface job) {
        return layerDao.getLayerDetails(job);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<ThreadStats> getThreadStats(LayerInterface layer) {
        return layerDao.getThreadStats(layer);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void optimizeLayer(LayerInterface layer, int cores, long maxRss, int runTime) {
        layerDao.balanceLayerMinMemory(layer, maxRss);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED)
    public void enableMemoryOptimizer(LayerInterface layer, boolean state) {
        layerDao.enableMemoryOptimizer(layer, state);
    }

    @Override
    public void appendLayerTag(LayerInterface layer, String tag) {
        layerDao.appendLayerTags(layer, tag);
    }

    @Override
    public void setLayerTag(LayerInterface layer, String tag) {
        layerDao.updateLayerTags(layer, Sets.newHashSet(tag));
    }

    @Override
    public void setLayerMinCores(LayerInterface layer, int coreUnits) {
        layerDao.updateLayerMinCores(layer, coreUnits);
    }

    @Override
    public void setLayerMaxCores(LayerInterface layer, int coreUnits) {
        layerDao.updateLayerMaxCores(layer, coreUnits);
    }

    @Override
    public void registerLayerOutput(LayerInterface layer, String filespec) {
        try {
            layerDao.insertLayerOutput(layer, filespec);
        } catch (DataAccessException e) {
            // Fail quietly but log it.
            logger.warn("Failed to add layer output: " + filespec + "," + e);
        }
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<String> getLayerOutputs(LayerInterface layer) {
        return layerDao.getLayerOutputs(layer);
    }

    @Override
    @Transactional(propagation = Propagation.SUPPORTS)
    public void updateCheckpointState(FrameInterface frame, CheckpointState state) {

        if (frameDao.updateFrameCheckpointState(frame, state)) {
            logger.info("Checkpoint state of frame " + frame.getId() +
                    " set to " + state.toString());
        }
        else {
            logger.warn("Failed to set checkpoint state of " + frame.getId() +
                    " to " + state.toString());
        }
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameDetail findHighestMemoryFrame(JobInterface job) {
        return frameDao.findHighestMemoryFrame(job);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameDetail findLongestFrame(JobInterface job) {
        return frameDao.findLongestFrame(job);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameDetail findLowestMemoryFrame(JobInterface job) {
        return frameDao.findLowestMemoryFrame(job);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameDetail findShortestFrame(JobInterface job) {
        return frameDao.findShortestFrame(job);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ExecutionSummary getExecutionSummary(JobInterface job) {
        return jobDao.getExecutionSummary(job);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameStateTotals getFrameStateTotals(JobInterface job) {
        return jobDao.getFrameStateTotals(job);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public ExecutionSummary getExecutionSummary(LayerInterface layer) {
        return layerDao.getExecutionSummary(layer);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public FrameStateTotals getFrameStateTotals(LayerInterface layer) {
        return layerDao.getFrameStateTotals(layer);
    }

    @Override
    @Transactional(propagation = Propagation.REQUIRED, readOnly=true)
    public List<FrameInterface> getStaleCheckpoints(int cutoffTimeSec) {
        return frameDao.getStaleCheckpoints(cutoffTimeSec);
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public FrameDao getFrameDao() {
        return frameDao;
    }

    public void setFrameDao(FrameDao frameDao) {
        this.frameDao = frameDao;
    }

    public LayerDao getLayerDao() {
        return layerDao;
    }

    public void setLayerDao(LayerDao layerDao) {
        this.layerDao = layerDao;
    }

    public ShowDao getShowDao() {
        return showDao;
    }

    public void setShowDao(ShowDao showDao) {
        this.showDao = showDao;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao workDao) {
        this.jobDao = workDao;
    }

    public FilterManager getFilterManager() {
        return filterManager;
    }

    public void setFilterManager(FilterManager filterManager) {
        this.filterManager = filterManager;
    }

    public GroupDao getGroupDao() {
        return groupDao;
    }

    public void setGroupDao(GroupDao groupDao) {
        this.groupDao = groupDao;
    }

    public FacilityDao getFacilityDao() {
        return facilityDao;
    }

    public void setFacilityDao(FacilityDao facilityDao) {
        this.facilityDao = facilityDao;
    }

    public HostDao getHostDao() {
        return hostDao;
    }

    public void setHostDao(HostDao hostDao) {
        this.hostDao = hostDao;
    }
}

