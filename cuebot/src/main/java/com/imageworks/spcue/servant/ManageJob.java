
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



package com.imageworks.spcue.servant;

import java.util.ArrayList;
import java.util.List;

import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.apache.log4j.Logger;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.BuildableJob;
import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.JobDetail;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.JobSearchInterface;
import com.imageworks.spcue.dao.criteria.JobSearchFactory;
import com.imageworks.spcue.depend.JobOnFrame;
import com.imageworks.spcue.depend.JobOnJob;
import com.imageworks.spcue.depend.JobOnLayer;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.dispatcher.commands.DispatchDropDepends;
import com.imageworks.spcue.dispatcher.commands.DispatchEatFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchJobComplete;
import com.imageworks.spcue.dispatcher.commands.DispatchKillFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchReorderFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchRetryFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchSatisfyDepends;
import com.imageworks.spcue.dispatcher.commands.DispatchStaggerFrames;
import com.imageworks.spcue.grpc.comment.Comment;
import com.imageworks.spcue.grpc.job.FrameSeq;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.JobAddCommentRequest;
import com.imageworks.spcue.grpc.job.JobAddCommentResponse;
import com.imageworks.spcue.grpc.job.JobAddRenderPartRequest;
import com.imageworks.spcue.grpc.job.JobAddRenderPartResponse;
import com.imageworks.spcue.grpc.job.JobCreateDependencyOnFrameRequest;
import com.imageworks.spcue.grpc.job.JobCreateDependencyOnFrameResponse;
import com.imageworks.spcue.grpc.job.JobCreateDependencyOnJobRequest;
import com.imageworks.spcue.grpc.job.JobCreateDependencyOnJobResponse;
import com.imageworks.spcue.grpc.job.JobCreateDependencyOnLayerRequest;
import com.imageworks.spcue.grpc.job.JobCreateDependencyOnLayerResponse;
import com.imageworks.spcue.grpc.job.JobDropDependsRequest;
import com.imageworks.spcue.grpc.job.JobDropDependsResponse;
import com.imageworks.spcue.grpc.job.JobEatFramesRequest;
import com.imageworks.spcue.grpc.job.JobEatFramesResponse;
import com.imageworks.spcue.grpc.job.JobFindJobRequest;
import com.imageworks.spcue.grpc.job.JobFindJobResponse;
import com.imageworks.spcue.grpc.job.JobGetCommentsRequest;
import com.imageworks.spcue.grpc.job.JobGetCommentsResponse;
import com.imageworks.spcue.grpc.job.JobGetCurrentRequest;
import com.imageworks.spcue.grpc.job.JobGetCurrentResponse;
import com.imageworks.spcue.grpc.job.JobGetDependsRequest;
import com.imageworks.spcue.grpc.job.JobGetDependsResponse;
import com.imageworks.spcue.grpc.job.JobGetFramesRequest;
import com.imageworks.spcue.grpc.job.JobGetFramesResponse;
import com.imageworks.spcue.grpc.job.JobGetJobNamesRequest;
import com.imageworks.spcue.grpc.job.JobGetJobNamesResponse;
import com.imageworks.spcue.grpc.job.JobGetJobRequest;
import com.imageworks.spcue.grpc.job.JobGetJobResponse;
import com.imageworks.spcue.grpc.job.JobGetJobsRequest;
import com.imageworks.spcue.grpc.job.JobGetJobsResponse;
import com.imageworks.spcue.grpc.job.JobGetLayersRequest;
import com.imageworks.spcue.grpc.job.JobGetLayersResponse;
import com.imageworks.spcue.grpc.job.JobGetUpdatedFramesRequest;
import com.imageworks.spcue.grpc.job.JobGetUpdatedFramesResponse;
import com.imageworks.spcue.grpc.job.JobGetWhatDependsOnThisRequest;
import com.imageworks.spcue.grpc.job.JobGetWhatDependsOnThisResponse;
import com.imageworks.spcue.grpc.job.JobGetWhatThisDependsOnRequest;
import com.imageworks.spcue.grpc.job.JobGetWhatThisDependsOnResponse;
import com.imageworks.spcue.grpc.job.JobInterfaceGrpc;
import com.imageworks.spcue.grpc.job.JobIsJobPendingRequest;
import com.imageworks.spcue.grpc.job.JobIsJobPendingResponse;
import com.imageworks.spcue.grpc.job.JobKillFramesRequest;
import com.imageworks.spcue.grpc.job.JobKillFramesResponse;
import com.imageworks.spcue.grpc.job.JobKillRequest;
import com.imageworks.spcue.grpc.job.JobKillResponse;
import com.imageworks.spcue.grpc.job.JobLaunchSpecAndWaitRequest;
import com.imageworks.spcue.grpc.job.JobLaunchSpecAndWaitResponse;
import com.imageworks.spcue.grpc.job.JobLaunchSpecRequest;
import com.imageworks.spcue.grpc.job.JobLaunchSpecResponse;
import com.imageworks.spcue.grpc.job.JobMarkAsWaitingRequest;
import com.imageworks.spcue.grpc.job.JobMarkAsWaitingResponse;
import com.imageworks.spcue.grpc.job.JobMarkDoneFramesRequest;
import com.imageworks.spcue.grpc.job.JobMarkDoneFramesResponse;
import com.imageworks.spcue.grpc.job.JobPauseRequest;
import com.imageworks.spcue.grpc.job.JobPauseResponse;
import com.imageworks.spcue.grpc.job.JobReorderFramesRequest;
import com.imageworks.spcue.grpc.job.JobReorderFramesResponse;
import com.imageworks.spcue.grpc.job.JobResumeRequest;
import com.imageworks.spcue.grpc.job.JobResumeResponse;
import com.imageworks.spcue.grpc.job.JobRetryFramesRequest;
import com.imageworks.spcue.grpc.job.JobRetryFramesResponse;
import com.imageworks.spcue.grpc.job.JobRunFiltersRequest;
import com.imageworks.spcue.grpc.job.JobRunFiltersResponse;
import com.imageworks.spcue.grpc.job.JobSearchCriteria;
import com.imageworks.spcue.grpc.job.JobSeq;
import com.imageworks.spcue.grpc.job.JobSetAutoEatRequest;
import com.imageworks.spcue.grpc.job.JobSetAutoEatResponse;
import com.imageworks.spcue.grpc.job.JobSetGroupRequest;
import com.imageworks.spcue.grpc.job.JobSetGroupResponse;
import com.imageworks.spcue.grpc.job.JobSetMaxCoresRequest;
import com.imageworks.spcue.grpc.job.JobSetMaxCoresResponse;
import com.imageworks.spcue.grpc.job.JobSetMaxGpusRequest;
import com.imageworks.spcue.grpc.job.JobSetMaxGpusResponse;
import com.imageworks.spcue.grpc.job.JobSetMaxRetriesRequest;
import com.imageworks.spcue.grpc.job.JobSetMaxRetriesResponse;
import com.imageworks.spcue.grpc.job.JobSetMinCoresRequest;
import com.imageworks.spcue.grpc.job.JobSetMinCoresResponse;
import com.imageworks.spcue.grpc.job.JobSetMinGpusRequest;
import com.imageworks.spcue.grpc.job.JobSetMinGpusResponse;
import com.imageworks.spcue.grpc.job.JobSetPriorityRequest;
import com.imageworks.spcue.grpc.job.JobSetPriorityResponse;
import com.imageworks.spcue.grpc.job.JobStaggerFramesRequest;
import com.imageworks.spcue.grpc.job.JobStaggerFramesResponse;
import com.imageworks.spcue.grpc.job.LayerSeq;
import com.imageworks.spcue.grpc.job.UpdatedFrameCheckResult;
import com.imageworks.spcue.grpc.renderpartition.RenderPartition;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionType;
import com.imageworks.spcue.service.CommentManager;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.JobLauncher;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.JobSpec;
import com.imageworks.spcue.service.LocalBookingSupport;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.FrameSet;

public class ManageJob extends JobInterfaceGrpc.JobInterfaceImplBase {
    private static final Logger logger = Logger.getLogger(ManageJob.class);
    private Whiteboard whiteboard;
    private JobManager jobManager;
    private GroupManager groupManager;
    private JobManagerSupport jobManagerSupport;
    private JobDao jobDao;
    private JobLauncher jobLauncher;
    private DependManager dependManager;
    private CommentManager commentManager;
    private DispatchQueue manageQueue;
    private Dispatcher localDispatcher;
    private LocalBookingSupport localBookingSupport;
    private FilterManager filterManager;
    private JobInterface job;
    private FrameSearchFactory frameSearchFactory;
    private JobSearchFactory jobSearchFactory;

    @Override
    public void findJob(JobFindJobRequest request, StreamObserver<JobFindJobResponse> responseObserver) {
        try {
            responseObserver.onNext(JobFindJobResponse.newBuilder()
                    .setJob(whiteboard.findJob(request.getName()))
                    .build());
            responseObserver.onCompleted();
        } catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.NOT_FOUND
                    .withDescription(e.getMessage())
                    .withCause(e)
                    .asRuntimeException());
        }
    }

    @Override
    public void getJob(JobGetJobRequest request, StreamObserver<JobGetJobResponse> responseObserver) {
        try {
            responseObserver.onNext(JobGetJobResponse.newBuilder()
                    .setJob(whiteboard.getJob(request.getId()))
                    .build());
            responseObserver.onCompleted();
        } catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.NOT_FOUND
                    .withDescription(e.getMessage())
                    .withCause(e)
                    .asRuntimeException());
        }
    }

    @Override
    public void getJobs(JobGetJobsRequest request, StreamObserver<JobGetJobsResponse> responseObserver) {
        responseObserver.onNext(JobGetJobsResponse.newBuilder()
                .setJobs(whiteboard.getJobs(jobSearchFactory.create(request.getR())))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getJobNames(JobGetJobNamesRequest request, StreamObserver<JobGetJobNamesResponse> responseObserver) {
        responseObserver.onNext(JobGetJobNamesResponse.newBuilder()
                .addAllNames(whiteboard.getJobNames(jobSearchFactory.create(request.getR())))
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
        try {
            setupJobData(request.getJob());
            FrameSeq frameSeq = whiteboard.getFrames(frameSearchFactory.create(job, request.getReq()));
            responseObserver.onNext(JobGetFramesResponse.newBuilder()
                    .setFrames(frameSeq)
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void getLayers(JobGetLayersRequest request, StreamObserver<JobGetLayersResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            LayerSeq layerSeq = whiteboard.getLayers(job);
            responseObserver.onNext(JobGetLayersResponse.newBuilder()
                    .setLayers(layerSeq)
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void kill(JobKillRequest request, StreamObserver<JobKillResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            manageQueue.execute(new DispatchJobComplete(job,
                    new Source(request.toString()), true, jobManagerSupport));
            responseObserver.onNext(JobKillResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void launchSpecAndWait(JobLaunchSpecAndWaitRequest request,
                                  StreamObserver<JobLaunchSpecAndWaitResponse> responseObserver) {
        try {
            JobSpec spec = jobLauncher.parse(request.getSpec());
            jobLauncher.launch(spec);
            JobSeq.Builder jobSeqBuilder = JobSeq.newBuilder();
            for (BuildableJob j : spec.getJobs()) {
                jobSeqBuilder.addJobs(whiteboard.findJob(j.detail.name));
            }
            responseObserver.onNext(JobLaunchSpecAndWaitResponse.newBuilder()
                    .setJobs(jobSeqBuilder.build())
                    .build());
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Failed to launch and add job.", e);
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to launch and add job: " + e.getMessage())
                    .withCause(e)
                    .asRuntimeException());
        }
    }

    @Override
    public void launchSpec(JobLaunchSpecRequest request, StreamObserver<JobLaunchSpecResponse> responseObserver) {
        try {
            JobSpec spec = jobLauncher.parse(request.getSpec());
            List<String> result = new ArrayList<String>(8);
            for (BuildableJob j : spec.getJobs()) {
                result.add(j.detail.name);
            }
            jobLauncher.queueAndLaunch(spec);
            responseObserver.onNext(JobLaunchSpecResponse.newBuilder()
                    .addAllNames(result)
                    .build());
            responseObserver.onCompleted();
        } catch (Exception e) {
            logger.error("Failed to add job to launch queue.", e);
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to add job to launch queue: " + e.getMessage())
                    .withCause(e)
                    .asRuntimeException());
        }
    }

    @Override
    public void pause(JobPauseRequest request, StreamObserver<JobPauseResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            jobManager.setJobPaused(job, true);
            responseObserver.onNext(JobPauseResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void resume(JobResumeRequest request, StreamObserver<JobResumeResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            jobManager.setJobPaused(job, false);
            responseObserver.onNext(JobResumeResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void setMaxCores(JobSetMaxCoresRequest request, StreamObserver<JobSetMaxCoresResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            jobDao.updateMaxCores(job, Convert.coresToWholeCoreUnits(request.getVal()));
            responseObserver.onNext(JobSetMaxCoresResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void setMinCores(JobSetMinCoresRequest request, StreamObserver<JobSetMinCoresResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            jobDao.updateMinCores(job, Convert.coresToWholeCoreUnits(request.getVal()));
            responseObserver.onNext(JobSetMinCoresResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void setMaxGpus(JobSetMaxGpusRequest request, StreamObserver<JobSetMaxGpusResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            jobDao.updateMaxGpus(job, request.getVal());
            responseObserver.onNext(JobSetMaxGpusResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void setMinGpus(JobSetMinGpusRequest request, StreamObserver<JobSetMinGpusResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            jobDao.updateMinGpus(job, request.getVal());
            responseObserver.onNext(JobSetMinGpusResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void setPriority(JobSetPriorityRequest request, StreamObserver<JobSetPriorityResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            jobDao.updatePriority(job, request.getVal());
            responseObserver.onNext(JobSetPriorityResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void getCurrent(JobGetCurrentRequest request, StreamObserver<JobGetCurrentResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            Job currentJob = whiteboard.getJob(job.getId());
            responseObserver.onNext(JobGetCurrentResponse.newBuilder()
                    .setJob(currentJob)
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void eatFrames(JobEatFramesRequest request, StreamObserver<JobEatFramesResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            manageQueue.execute(
                    new DispatchEatFrames(
                            frameSearchFactory.create(job, request.getReq()),
                            new Source(request.toString()),
                            jobManagerSupport));
            responseObserver.onNext(JobEatFramesResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void killFrames(JobKillFramesRequest request, StreamObserver<JobKillFramesResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            manageQueue.execute(
                    new DispatchKillFrames(
                            frameSearchFactory.create(job, request.getReq()),
                            new Source(request.toString()),
                            jobManagerSupport));
            responseObserver.onNext(JobKillFramesResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void markDoneFrames(JobMarkDoneFramesRequest request,
                               StreamObserver<JobMarkDoneFramesResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            manageQueue.execute(
                    new DispatchSatisfyDepends(
                            frameSearchFactory.create(job, request.getReq()), jobManagerSupport));
            responseObserver.onNext(JobMarkDoneFramesResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void retryFrames(JobRetryFramesRequest request, StreamObserver<JobRetryFramesResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            manageQueue.execute(
                    new DispatchRetryFrames(
                            frameSearchFactory.create(job, request.getReq()),
                            new Source(request.toString()),
                            jobManagerSupport));
            responseObserver.onNext(JobRetryFramesResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void setAutoEat(JobSetAutoEatRequest request, StreamObserver<JobSetAutoEatResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            jobDao.updateAutoEat(job, request.getValue());
            responseObserver.onNext(JobSetAutoEatResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void createDependencyOnFrame(JobCreateDependencyOnFrameRequest request,
                                        StreamObserver<JobCreateDependencyOnFrameResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            JobOnFrame depend = new JobOnFrame(job,
                    jobManager.getFrameDetail(request.getFrame().getId()));
            dependManager.createDepend(depend);
            responseObserver.onNext(JobCreateDependencyOnFrameResponse.newBuilder()
                    .setDepend(whiteboard.getDepend(depend))
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void createDependencyOnJob(JobCreateDependencyOnJobRequest request,
                                      StreamObserver<JobCreateDependencyOnJobResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            JobOnJob depend = new JobOnJob(job,
                    jobManager.getJobDetail(request.getOnJob().getId()));
            dependManager.createDepend(depend);
            responseObserver.onNext(JobCreateDependencyOnJobResponse.newBuilder()
                    .setDepend(whiteboard.getDepend(depend))
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void createDependencyOnLayer(JobCreateDependencyOnLayerRequest request,
                                        StreamObserver<JobCreateDependencyOnLayerResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            JobOnLayer depend = new JobOnLayer(job,
                    jobManager.getLayerDetail(request.getLayer().getId()));
            dependManager.createDepend(depend);
            responseObserver.onNext(JobCreateDependencyOnLayerResponse.newBuilder()
                    .setDepend(whiteboard.getDepend(depend))
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void getWhatDependsOnThis(JobGetWhatDependsOnThisRequest request, StreamObserver<JobGetWhatDependsOnThisResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            responseObserver.onNext(JobGetWhatDependsOnThisResponse.newBuilder()
                    .setDepends(whiteboard.getWhatDependsOnThis(job))
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void getWhatThisDependsOn(JobGetWhatThisDependsOnRequest request,
                                     StreamObserver<JobGetWhatThisDependsOnResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            responseObserver.onNext(JobGetWhatThisDependsOnResponse.newBuilder()
                    .setDepends(whiteboard.getWhatThisDependsOn(job))
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void getDepends(JobGetDependsRequest request, StreamObserver<JobGetDependsResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            responseObserver.onNext(JobGetDependsResponse.newBuilder()
                    .setDepends(whiteboard.getDepends(job))
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void getUpdatedFrames(JobGetUpdatedFramesRequest request, StreamObserver<JobGetUpdatedFramesResponse> responseObserver) {
        try{
            setupJobData(request.getJob());
            UpdatedFrameCheckResult result = whiteboard.getUpdatedFrames(job,
                    ServantUtil.convertLayerFilterList(request.getLayerFilter()), request.getLastCheck());
            responseObserver.onNext(JobGetUpdatedFramesResponse.newBuilder()
                    .setUpdatedFrames(result.getUpdatedFrames())
                    .setServerTime(result.getServerTime())
                    .setState(result.getState())
                    .build());
            responseObserver.onCompleted();

        } catch (java.lang.IllegalArgumentException e) {
            System.out.println(e);
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void setMaxRetries(JobSetMaxRetriesRequest request, StreamObserver<JobSetMaxRetriesResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            jobDao.updateMaxFrameRetries(job, request.getMaxRetries());
            responseObserver.onNext(JobSetMaxRetriesResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void addComment(JobAddCommentRequest request, StreamObserver<JobAddCommentResponse> responseObserver) {
        try {
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
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void getComments(JobGetCommentsRequest request, StreamObserver<JobGetCommentsResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            responseObserver.onNext(JobGetCommentsResponse.newBuilder()
                    .setComments(whiteboard.getComments(job))
                    .build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void dropDepends(JobDropDependsRequest request, StreamObserver<JobDropDependsResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            manageQueue.execute(new DispatchDropDepends(job, request.getTarget(), dependManager));
            responseObserver.onNext(JobDropDependsResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void setGroup(JobSetGroupRequest request, StreamObserver<JobSetGroupResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            jobDao.updateParent(job, groupManager.getGroupDetail(request.getGroupId()));
            responseObserver.onNext(JobSetGroupResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void markAsWaiting(JobMarkAsWaitingRequest request,
                              StreamObserver<JobMarkAsWaitingResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            jobManagerSupport.markFramesAsWaiting(
                    frameSearchFactory.create(job, request.getReq()), new Source(request.toString()));
            responseObserver.onNext(JobMarkAsWaitingResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void reorderFrames(JobReorderFramesRequest request,
                              StreamObserver<JobReorderFramesResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            manageQueue.execute(new DispatchReorderFrames(job,
                    new FrameSet(request.getRange()), request.getOrder(), jobManagerSupport));
            responseObserver.onNext(JobReorderFramesResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void staggerFrames(JobStaggerFramesRequest request,
                              StreamObserver<JobStaggerFramesResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            manageQueue.execute(
                    new DispatchStaggerFrames(job, request.getRange(), request.getStagger(), jobManagerSupport));
            responseObserver.onNext(JobStaggerFramesResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void addRenderPartition(JobAddRenderPartRequest request, StreamObserver<JobAddRenderPartResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            LocalHostAssignment lha = new LocalHostAssignment();
            lha.setJobId(job.getId());
            lha.setThreads(request.getThreads());
            lha.setMaxCoreUnits(request.getMaxCores() * 100);
            lha.setMaxMemory(request.getMaxMemory());
            lha.setMaxGpuUnits(request.getMaxGpus());
            lha.setMaxGpuMemory(request.getMaxGpuMemory());
            lha.setType(RenderPartitionType.JOB_PARTITION);

            if (localBookingSupport.bookLocal(job, request.getHost(), request.getUsername(), lha)) {
                try {
                    RenderPartition renderPart = whiteboard.getRenderPartition(lha);
                    responseObserver.onNext(JobAddRenderPartResponse.newBuilder()
                            .setRenderPartition(renderPart)
                            .build());
                    responseObserver.onCompleted();
                } catch (EmptyResultDataAccessException e) {
                    responseObserver.onError(Status.INTERNAL
                            .withDescription("Failed to allocate render partition to host.")
                            .asRuntimeException());
                }
            } else {
                responseObserver.onError(Status.INTERNAL
                        .withDescription("Failed to find suitable frames.")
                        .asRuntimeException());
            }
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
    }

    @Override
    public void runFilters(JobRunFiltersRequest request, StreamObserver<JobRunFiltersResponse> responseObserver) {
        try {
            setupJobData(request.getJob());
            JobDetail jobDetail = jobManager.getJobDetail(job.getJobId());
            filterManager.runFiltersOnJob(jobDetail);
            responseObserver.onNext(JobRunFiltersResponse.newBuilder().build());
            responseObserver.onCompleted();
        }
        catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find job data")
                    .asRuntimeException());
        }
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

    public JobLauncher getJobLauncher() {
        return jobLauncher;
    }

    public void setJobLauncher(JobLauncher jobLauncher) {
        this.jobLauncher = jobLauncher;
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

    private void setupJobData(Job jobData) {
        setJobManager(jobManagerSupport.getJobManager());
        setDependManager(jobManagerSupport.getDependManager());
        job = jobManager.getJob(jobData.getId());
    }

    public FrameSearchFactory getFrameSearchFactory() {
        return frameSearchFactory;
    }

    public void setFrameSearchFactory(FrameSearchFactory frameSearchFactory) {
        this.frameSearchFactory = frameSearchFactory;
    }

    public JobSearchFactory getJobSearchFactory() {
        return jobSearchFactory;
    }

    public void setJobSearchFactory(JobSearchFactory jobSearchFactory) {
        this.jobSearchFactory = jobSearchFactory;
    }
}

