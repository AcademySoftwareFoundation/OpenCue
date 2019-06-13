
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

import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.FrameEntity;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.FrameDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.depend.FrameOnFrame;
import com.imageworks.spcue.depend.FrameOnJob;
import com.imageworks.spcue.depend.FrameOnLayer;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.commands.DispatchDropDepends;
import com.imageworks.spcue.dispatcher.commands.DispatchEatFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchKillFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchRetryFrames;
import com.imageworks.spcue.grpc.depend.Depend;
import com.imageworks.spcue.grpc.job.Frame;
import com.imageworks.spcue.grpc.job.FrameAddRenderPartitionRequest;
import com.imageworks.spcue.grpc.job.FrameAddRenderPartitionResponse;
import com.imageworks.spcue.grpc.job.FrameCreateDependencyOnFrameRequest;
import com.imageworks.spcue.grpc.job.FrameCreateDependencyOnFrameResponse;
import com.imageworks.spcue.grpc.job.FrameCreateDependencyOnJobRequest;
import com.imageworks.spcue.grpc.job.FrameCreateDependencyOnJobResponse;
import com.imageworks.spcue.grpc.job.FrameCreateDependencyOnLayerRequest;
import com.imageworks.spcue.grpc.job.FrameCreateDependencyOnLayerResponse;
import com.imageworks.spcue.grpc.job.FrameDropDependsRequest;
import com.imageworks.spcue.grpc.job.FrameDropDependsResponse;
import com.imageworks.spcue.grpc.job.FrameEatRequest;
import com.imageworks.spcue.grpc.job.FrameEatResponse;
import com.imageworks.spcue.grpc.job.FrameFindFrameRequest;
import com.imageworks.spcue.grpc.job.FrameFindFrameResponse;
import com.imageworks.spcue.grpc.job.FrameGetFrameRequest;
import com.imageworks.spcue.grpc.job.FrameGetFrameResponse;
import com.imageworks.spcue.grpc.job.FrameGetFramesRequest;
import com.imageworks.spcue.grpc.job.FrameGetFramesResponse;
import com.imageworks.spcue.grpc.job.FrameGetWhatDependsOnThisRequest;
import com.imageworks.spcue.grpc.job.FrameGetWhatDependsOnThisResponse;
import com.imageworks.spcue.grpc.job.FrameGetWhatThisDependsOnRequest;
import com.imageworks.spcue.grpc.job.FrameGetWhatThisDependsOnResponse;
import com.imageworks.spcue.grpc.job.FrameInterfaceGrpc;
import com.imageworks.spcue.grpc.job.FrameKillRequest;
import com.imageworks.spcue.grpc.job.FrameKillResponse;
import com.imageworks.spcue.grpc.job.FrameMarkAsDependRequest;
import com.imageworks.spcue.grpc.job.FrameMarkAsDependResponse;
import com.imageworks.spcue.grpc.job.FrameMarkAsWaitingRequest;
import com.imageworks.spcue.grpc.job.FrameMarkAsWaitingResponse;
import com.imageworks.spcue.grpc.job.FrameRetryRequest;
import com.imageworks.spcue.grpc.job.FrameRetryResponse;
import com.imageworks.spcue.grpc.job.FrameSetCheckpointStateRequest;
import com.imageworks.spcue.grpc.job.FrameSetCheckpointStateResponse;
import com.imageworks.spcue.grpc.renderpartition.RenderPartition;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionType;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.LocalBookingSupport;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageFrame extends FrameInterfaceGrpc.FrameInterfaceImplBase {

    @Autowired
    private JobManager jobManager;

    @Autowired
    private DependManager dependManager;

    @Autowired
    private JobManagerSupport jobManagerSupport;

    @Autowired
    private FrameDao frameDao;

    @Autowired
    private DispatchQueue manageQueue;

    @Autowired
    private Whiteboard whiteboard;

    @Autowired
    private LocalBookingSupport localBookingSupport;

    @Autowired
    private FrameSearchFactory frameSearchFactory;

    @Override
    public void findFrame(FrameFindFrameRequest request, StreamObserver<FrameFindFrameResponse> responseObserver) {
        responseObserver.onNext(FrameFindFrameResponse.newBuilder()
                .setFrame(whiteboard.findFrame(request.getJob(), request.getLayer(), request.getFrame()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getFrame(FrameGetFrameRequest request, StreamObserver<FrameGetFrameResponse> responseObserver) {
        responseObserver.onNext(FrameGetFrameResponse.newBuilder()
                .setFrame(whiteboard.getFrame(request.getId()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getFrames(FrameGetFramesRequest request, StreamObserver<FrameGetFramesResponse> responseObserver) {
        responseObserver.onNext(FrameGetFramesResponse.newBuilder()
                .setFrames(
                        whiteboard.getFrames(
                                frameSearchFactory.create(jobManager.findJob(request.getJob()),
                                        request.getR())))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void eat(FrameEatRequest request, StreamObserver<FrameEatResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        manageQueue.execute(
                new DispatchEatFrames(
                        frameSearchFactory.create(frame),
                        new Source(request.toString()),
                        jobManagerSupport));
        responseObserver.onNext(FrameEatResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void kill(FrameKillRequest request, StreamObserver<FrameKillResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        manageQueue.execute(
                new DispatchKillFrames(
                        frameSearchFactory.create(frame),
                        new Source(request.toString()),
                        jobManagerSupport));
        responseObserver.onNext(FrameKillResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void retry(FrameRetryRequest request, StreamObserver<FrameRetryResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        manageQueue.execute(
                new DispatchRetryFrames(
                        frameSearchFactory.create(frame),
                        new Source(request.toString()),
                        jobManagerSupport));
        responseObserver.onNext(FrameRetryResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnFrame(FrameCreateDependencyOnFrameRequest request,
                                        StreamObserver<FrameCreateDependencyOnFrameResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        FrameOnFrame depend = new FrameOnFrame(frame,
                jobManager.getFrameDetail(request.getDependOnFrame().getId()));
        dependManager.createDepend(depend);
        Depend dependency = whiteboard.getDepend(depend);
        responseObserver.onNext(FrameCreateDependencyOnFrameResponse.newBuilder()
                .setDepend(dependency)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnJob(FrameCreateDependencyOnJobRequest request,
                                      StreamObserver<FrameCreateDependencyOnJobResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        FrameOnJob depend = new FrameOnJob(frame, jobManager.getJobDetail(request.getJob().getId()));
        dependManager.createDepend(depend);
        Depend dependency = whiteboard.getDepend(depend);
        responseObserver.onNext(FrameCreateDependencyOnJobResponse.newBuilder()
                .setDepend(dependency)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnLayer(FrameCreateDependencyOnLayerRequest request,
                                        StreamObserver<FrameCreateDependencyOnLayerResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        FrameOnLayer depend = new FrameOnLayer(frame, jobManager.getLayerDetail(request.getLayer().getId()));
        dependManager.createDepend(depend);
        Depend dependency = whiteboard.getDepend(depend);
        responseObserver.onNext(FrameCreateDependencyOnLayerResponse.newBuilder()
                .setDepend(dependency)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getWhatDependsOnThis(FrameGetWhatDependsOnThisRequest request,
                                     StreamObserver<FrameGetWhatDependsOnThisResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        responseObserver.onNext(FrameGetWhatDependsOnThisResponse.newBuilder()
                .setDepends(whiteboard.getWhatDependsOnThis(frame))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getWhatThisDependsOn(FrameGetWhatThisDependsOnRequest request,
                                     StreamObserver<FrameGetWhatThisDependsOnResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        responseObserver.onNext(FrameGetWhatThisDependsOnResponse.newBuilder()
                .setDepends(whiteboard.getWhatThisDependsOn(frame))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void markAsDepend(FrameMarkAsDependRequest request,
                             StreamObserver<FrameMarkAsDependResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        jobManager.markFrameAsDepend(frame);
        responseObserver.onNext(FrameMarkAsDependResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void markAsWaiting(FrameMarkAsWaitingRequest request, StreamObserver<FrameMarkAsWaitingResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        jobManager.markFrameAsWaiting(frame);
        responseObserver.onNext(FrameMarkAsWaitingResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void dropDepends(FrameDropDependsRequest request, StreamObserver<FrameDropDependsResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        manageQueue.execute(new DispatchDropDepends(frame, request.getTarget(), dependManager));
        responseObserver.onNext(FrameDropDependsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void addRenderPartition(FrameAddRenderPartitionRequest request,
                                   StreamObserver<FrameAddRenderPartitionResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        LocalHostAssignment lha = new LocalHostAssignment();
        lha.setFrameId(frame.id);
        lha.setThreads(request.getThreads());
        lha.setMaxCoreUnits(request.getMaxCores() * 100);
        lha.setMaxMemory(request.getMaxMemory());
        lha.setMaxGpu(request.getMaxGpu());
        lha.setType(RenderPartitionType.FRAME_PARTITION);

        if (localBookingSupport.bookLocal(frame, request.getHost(), request.getUsername(), lha)) {
            RenderPartition partition = whiteboard.getRenderPartition(lha);

            responseObserver.onNext(FrameAddRenderPartitionResponse.newBuilder()
                    .setRenderPartition(partition)
                    .build());
            responseObserver.onCompleted();
        }
        responseObserver.onError(Status.INTERNAL
                .withDescription("Failed to find suitable frames.")
                .augmentDescription("customException()")
                .asRuntimeException());
    }

    @Override
    public void setCheckpointState(FrameSetCheckpointStateRequest request,
                                   StreamObserver<FrameSetCheckpointStateResponse> responseObserver) {
        FrameEntity frame = getFrameEntity(request.getFrame());
        jobManager.updateCheckpointState(frame, request.getState());
        responseObserver.onNext(FrameSetCheckpointStateResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue dispatchQueue) {
        this.manageQueue = dispatchQueue;
    }

    public FrameDao getFrameDao() {
        return frameDao;
    }

    public void setFrameDao(FrameDao frameDao) {
        this.frameDao = frameDao;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public LocalBookingSupport getLocalBookingSupport() {
        return localBookingSupport;
    }

    public void setLocalBookingSupport(LocalBookingSupport localBookingSupport) {
        this.localBookingSupport = localBookingSupport;
    }

    private FrameEntity getFrameEntity(Frame frame) {
        return frameDao.getFrameDetail(frame.getId());
    }

    public FrameSearchFactory getFrameSearchFactory() {
        return frameSearchFactory;
    }

    public void setFrameSearchFactory(FrameSearchFactory frameSearchFactory) {
        this.frameSearchFactory = frameSearchFactory;
    }
}

