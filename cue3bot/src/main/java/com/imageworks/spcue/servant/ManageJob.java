
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



package com.imageworks.spcue.servant;

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.dao.criteria.JobSearch;
import com.imageworks.spcue.depend.JobOnFrame;
import com.imageworks.spcue.depend.JobOnJob;
import com.imageworks.spcue.depend.JobOnLayer;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.commands.*;
import com.imageworks.spcue.grpc.comment.Comment;
import com.imageworks.spcue.grpc.job.*;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.UpdatedFrameCheckResult;
import com.imageworks.spcue.grpc.renderpartition.RenderPartition;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionType;
import com.imageworks.spcue.service.*;
import com.imageworks.spcue.util.Convert;
import com.imageworks.util.FileSequence.FrameSet;
import io.grpc.stub.StreamObserver;
import io.grpc.Status;

public class ManageJob extends JobInterfaceGrpc.JobInterfaceImplBase {

    private Whiteboard whiteboard;
    private JobManager jobManager;
    private GroupManager groupManager;
    private JobManagerSupport jobManagerSupport;
    private JobDao jobDao;
    private DependManager dependManager;
    private CommentManager commentManager;
    private DispatchQueue manageQueue;
    private Dispatcher localDispatcher;
    private LocalBookingSupport localBookingSupport;
    private FilterManager filterManager;

    private com.imageworks.spcue.JobInterface job;

    private void setupJobData(Job jobData) {
        setJobManager(jobManagerSupport.getJobManager());
        setDependManager(jobManagerSupport.getDependManager());
        job = jobManager.getJob(jobData.getId());
    }

    @Override
    public void findJob(JobFindJobRequest request, StreamObserver<JobFindJobResponse> responseObserver) {
        responseObserver.onNext(JobFindJobResponse.newBuilder()
                .setJob(whiteboard.findJob(request.getName()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getJob(JobGetJobRequest request, StreamObserver<JobGetJobResponse> responseObserver) {
        responseObserver.onNext(JobGetJobResponse.newBuilder()
                .setJob(whiteboard.getJob(request.getId()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getJobs(JobGetJobsRequest request, StreamObserver<JobGetJobsResponse> responseObserver) {
        responseObserver.onNext(JobGetJobsResponse.newBuilder()
                .setJobs(whiteboard.getJobs(new JobSearch(request.getR())))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getJobNames(JobGetJobNamesRequest request, StreamObserver<JobGetJobNamesResponse> responseObserver) {
        responseObserver.onNext(JobGetJobNamesResponse.newBuilder()
                .addAllNames(whiteboard.getJobNames(new JobSearch(request.getR())))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void isJobPending(JobIsJobPendingRequest request, StreamObserver<JobIsJobPendingResponse> responseObserver) {
        responseObserver.onNext(JobIsJobPendingResponse.newBuilder()
                .setValue(whiteboard.isJobPending(request.getName()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getFrames(JobGetFramesRequest request, StreamObserver<JobGetFramesResponse> responseObserver) {
        setupJobData(request.getJob());
        FrameSeq frameSeq = whiteboard.getFrames(new FrameSearch(job, request.getReq()));
        responseObserver.onNext(JobGetFramesResponse.newBuilder()
                .setFrames(frameSeq)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getLayers(JobGetLayersRequest request, StreamObserver<JobGetLayersResponse> responseObserver) {
        setupJobData(request.getJob());
        LayerSeq layerSeq = whiteboard.getLayers(job);
        responseObserver.onNext(JobGetLayersResponse.newBuilder()
                .setLayers(layerSeq)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void kill(JobKillRequest request, StreamObserver<JobKillResponse> responseObserver) {
        setupJobData(request.getJob());
        manageQueue.execute(new DispatchJobComplete(job,
                new Source(request.toString()), true, jobManagerSupport));
        responseObserver.onNext(JobKillResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void pause(JobPauseRequest request, StreamObserver<JobPauseResponse> responseObserver) {
        setupJobData(request.getJob());
        jobManager.setJobPaused(job, true);
        responseObserver.onNext(JobPauseResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void resume(JobResumeRequest request, StreamObserver<JobResumeResponse> responseObserver) {
        setupJobData(request.getJob());
        jobManager.setJobPaused(job, false);
        responseObserver.onNext(JobResumeResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMaxCores(JobSetMaxCoresRequest request, StreamObserver<JobSetMaxCoresResponse> responseObserver) {
        setupJobData(request.getJob());
        jobDao.updateMaxCores(job, Convert.coresToWholeCoreUnits(request.getVal()));
        responseObserver.onNext(JobSetMaxCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMinCores(JobSetMinCoresRequest request, StreamObserver<JobSetMinCoresResponse> responseObserver) {
        setupJobData(request.getJob());
        jobDao.updateMinCores(job, Convert.coresToWholeCoreUnits(request.getVal()));
        responseObserver.onNext(JobSetMinCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setPriority(JobSetPriorityRequest request, StreamObserver<JobSetPriorityResponse> responseObserver) {
        setupJobData(request.getJob());
        jobDao.updatePriority(job, request.getVal());
        responseObserver.onNext(JobSetPriorityResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getCurrent(JobGetCurrentRequest request, StreamObserver<JobGetCurrentResponse> responseObserver) {
        setupJobData(request.getJob());
        Job currentJob = whiteboard.getJob(job.getId());
        responseObserver.onNext(JobGetCurrentResponse.newBuilder()
                .setJob(currentJob)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void eatFrames(JobEatFramesRequest request, StreamObserver<JobEatFramesResponse> responseObserver) {
        setupJobData(request.getJob());
        manageQueue.execute(
                new DispatchEatFrames(new FrameSearch(job, request.getReq()),
                        new Source(request.toString()), jobManagerSupport));
        responseObserver.onNext(JobEatFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void killFrames(JobKillFramesRequest request, StreamObserver<JobKillFramesResponse> responseObserver) {
        setupJobData(request.getJob());
        manageQueue.execute(new DispatchKillFrames(
                new FrameSearch(job, request.getReq()),
                new Source(request.toString()), jobManagerSupport));
        responseObserver.onNext(JobKillFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void markDoneFrames(JobMarkDoneFramesRequest request,
                               StreamObserver<JobMarkDoneFramesResponse> responseObserver) {
        setupJobData(request.getJob());
        manageQueue.execute(new DispatchSatisfyDepends(new FrameSearch(job, request.getReq()), jobManagerSupport));
        responseObserver.onNext(JobMarkDoneFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void retryFrames(JobRetryFramesRequest request, StreamObserver<JobRetryFramesResponse> responseObserver) {
        setupJobData(request.getJob());
        manageQueue.execute(
                new DispatchRetryFrames(new FrameSearch(job, request.getReq()),
                        new Source(request.toString()), jobManagerSupport));
        responseObserver.onNext(JobRetryFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setAutoEat(JobSetAutoEatRequest request, StreamObserver<JobSetAutoEatResponse> responseObserver) {
        setupJobData(request.getJob());
        jobDao.updateAutoEat(job, request.getValue());
        responseObserver.onNext(JobSetAutoEatResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnFrame(JobCreateDependencyOnFrameRequest request,
                                        StreamObserver<JobCreateDependencyOnFrameResponse> responseObserver) {
        setupJobData(request.getJob());
        JobOnFrame depend = new JobOnFrame(job,
                jobManager.getFrameDetail(request.getFrame().getId()));
        dependManager.createDepend(depend);
        responseObserver.onNext(JobCreateDependencyOnFrameResponse.newBuilder()
                .setDepend(whiteboard.getDepend(depend))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnJob(JobCreateDependencyOnJobRequest request,
                                      StreamObserver<JobCreateDependencyOnJobResponse> responseObserver) {
        setupJobData(request.getJob());
        JobOnJob depend = new JobOnJob(job,
                jobManager.getJobDetail(request.getOnJob().getId()));
        dependManager.createDepend(depend);
        responseObserver.onNext(JobCreateDependencyOnJobResponse.newBuilder()
                .setDepend(whiteboard.getDepend(depend))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnLayer(JobCreateDependencyOnLayerRequest request,
                                        StreamObserver<JobCreateDependencyOnLayerResponse> responseObserver) {
        setupJobData(request.getJob());
        JobOnLayer depend = new JobOnLayer(job,
                jobManager.getLayerDetail(request.getLayer().getId()));
        dependManager.createDepend(depend);
        responseObserver.onNext(JobCreateDependencyOnLayerResponse.newBuilder()
                .setDepend(whiteboard.getDepend(depend))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getWhatDependsOnThis(JobGetWhatDependsOnThisRequest request, StreamObserver<JobGetWhatDependsOnThisResponse> responseObserver) {
        setupJobData(request.getJob());
        responseObserver.onNext(JobGetWhatDependsOnThisResponse.newBuilder()
                .setDepends(whiteboard.getWhatDependsOnThis(job))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getWhatThisDependsOn(JobGetWhatThisDependsOnRequest request,
                                     StreamObserver<JobGetWhatThisDependsOnResponse> responseObserver) {
        setupJobData(request.getJob());
        responseObserver.onNext(JobGetWhatThisDependsOnResponse.newBuilder()
                .setDepends(whiteboard.getWhatThisDependsOn(job))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getDepends(JobGetDependsRequest request, StreamObserver<JobGetDependsResponse> responseObserver) {
        setupJobData(request.getJob());
        responseObserver.onNext(JobGetDependsResponse.newBuilder()
                .setDepends(whiteboard.getDepends(job))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getUpdatedFrames(JobGetUpdatedFramesRequest request, StreamObserver<JobGetUpdatedFramesResponse> responseObserver) {
        setupJobData(request.getJob());
        UpdatedFrameCheckResult result = whiteboard.getUpdatedFrames(job,
                ServantUtil.convertLayerFilterList(request.getLayerFilter()), request.getLastCheck());
        responseObserver.onNext(JobGetUpdatedFramesResponse.newBuilder()
                .setUpdatedFrames(result.getUpdatedFrames())
                .setServerTime(result.getServerTime())
                .setState(result.getState())
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMaxRetries(JobSetMaxRetriesRequest request, StreamObserver<JobSetMaxRetriesResponse> responseObserver) {
        setupJobData(request.getJob());
        jobDao.updateMaxFrameRetries(job, request.getMaxRetries());
        responseObserver.onNext(JobSetMaxRetriesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void addComment(JobAddCommentRequest request, StreamObserver<JobAddCommentResponse> responseObserver) {
        setupJobData(request.getJob());
        Comment newComment = request.getNewComment();
        CommentDetail c = new CommentDetail();
        c.message = newComment.getMessage();
        c.subject = newComment.getSubject();
        c.user = newComment.getUser();
        c.timestamp = null;
        commentManager.addComment(job, c);
        responseObserver.onNext(JobAddCommentResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getComments(JobGetCommentsRequest request, StreamObserver<JobGetCommentsResponse> responseObserver) {
        setupJobData(request.getJob());
        responseObserver.onNext(JobGetCommentsResponse.newBuilder()
                .setComments(whiteboard.getComments(job))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void dropDepends(JobDropDependsRequest request, StreamObserver<JobDropDependsResponse> responseObserver) {
        setupJobData(request.getJob());
        manageQueue.execute(new DispatchDropDepends(job, request.getTarget(), dependManager));
        responseObserver.onNext(JobDropDependsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setGroup(JobSetGroupRequest request, StreamObserver<JobSetGroupResponse> responseObserver) {
        setupJobData(request.getJob());
        jobDao.updateParent(job, groupManager.getGroupDetail(request.getGroupId()));
        responseObserver.onNext(JobSetGroupResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void markAsWaiting(JobMarkAsWaitingRequest request,
                              StreamObserver<JobMarkAsWaitingResponse> responseObserver) {
        setupJobData(request.getJob());
        jobManagerSupport.markFramesAsWaiting(new FrameSearch(job, request.getReq()),
                new Source(request.toString()));
        responseObserver.onNext(JobMarkAsWaitingResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void reorderFrames(JobReorderFramesRequest request,
                              StreamObserver<JobReorderFramesResponse> responseObserver) {
        setupJobData(request.getJob());
        manageQueue.execute(new DispatchReorderFrames(job,
                new FrameSet(request.getRange()), request.getOrder(), jobManagerSupport));
        responseObserver.onNext(JobReorderFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void staggerFrames(JobStaggerFramesRequest request,
                              StreamObserver<JobStaggerFramesResponse> responseObserver) {
        setupJobData(request.getJob());
        manageQueue.execute(
                new DispatchStaggerFrames(job, request.getRange(), request.getStagger(), jobManagerSupport));
        responseObserver.onNext(JobStaggerFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void addRenderPartition(JobAddRenderPartRequest request, StreamObserver<JobAddRenderPartResponse> responseObserver) {
        setupJobData(request.getJob());
        LocalHostAssignment lha = new LocalHostAssignment();
        lha.setJobId(job.getId());
        lha.setThreads(request.getThreads());
        lha.setMaxCoreUnits(request.getMaxCores() * 100);
        lha.setMaxMemory(request.getMaxMemory());
        lha.setMaxGpu(request.getMaxGpu());
        lha.setType(RenderPartitionType.JOB_PARTITION);

        if (localBookingSupport.bookLocal(job, request.getHost(), request.getUsername(), lha)) {
            RenderPartition renderPart = whiteboard.getRenderPartition(lha);
            responseObserver.onNext(JobAddRenderPartResponse.newBuilder()
                    .setRenderPartition(renderPart)
                    .build());
            responseObserver.onCompleted();
        }
        responseObserver.onError(Status.INTERNAL
                .withDescription("Failed to find suitable frames.")
                .asRuntimeException());
    }

    @Override
    public void runFilters(JobRunFiltersRequest request, StreamObserver<JobRunFiltersResponse> responseObserver) {
        setupJobData(request.getJob());
        JobDetail jobDetail = jobManager.getJobDetail(job.getJobId());
        filterManager.runFiltersOnJob(jobDetail);
        responseObserver.onNext(JobRunFiltersResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue dispatchQueue) {
        this.manageQueue = dispatchQueue;
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    public CommentManager getCommentManager() {
        return commentManager;
    }

    public void setCommentManager(CommentManager commentManager) {
        this.commentManager = commentManager;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public GroupManager getGroupManager() {
        return groupManager;
    }

    public void setGroupManager(GroupManager groupManager) {
        this.groupManager = groupManager;
    }

    public Dispatcher getLocalDispatcher() {
        return localDispatcher;
    }

    public void setLocalDispatcher(Dispatcher localDispatcher) {
        this.localDispatcher = localDispatcher;
    }

    public LocalBookingSupport getLocalBookingSupport() {
        return localBookingSupport;
    }

    public void setLocalBookingSupport(LocalBookingSupport localBookingSupport) {
        this.localBookingSupport = localBookingSupport;
    }

    public FilterManager getFilterManager() {
        return filterManager;
    }

    public void setFilterManager(FilterManager filterManager) {
        this.filterManager = filterManager;
    }
}

