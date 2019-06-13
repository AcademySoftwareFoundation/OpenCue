
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

import java.util.HashSet;

import com.google.protobuf.Descriptors;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.LayerDao;
import com.imageworks.spcue.dao.criteria.FrameSearchFactory;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.depend.FrameByFrame;
import com.imageworks.spcue.depend.LayerOnFrame;
import com.imageworks.spcue.depend.LayerOnJob;
import com.imageworks.spcue.depend.LayerOnLayer;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.commands.DispatchDropDepends;
import com.imageworks.spcue.dispatcher.commands.DispatchEatFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchKillFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchReorderFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchRetryFrames;
import com.imageworks.spcue.dispatcher.commands.DispatchSatisfyDepends;
import com.imageworks.spcue.dispatcher.commands.DispatchStaggerFrames;
import com.imageworks.spcue.grpc.job.FrameSearchCriteria;
import com.imageworks.spcue.grpc.job.FrameSeq;
import com.imageworks.spcue.grpc.job.Layer;
import com.imageworks.spcue.grpc.job.LayerAddRenderPartitionRequest;
import com.imageworks.spcue.grpc.job.LayerAddRenderPartitionResponse;
import com.imageworks.spcue.grpc.job.LayerCreateDependOnFrameRequest;
import com.imageworks.spcue.grpc.job.LayerCreateDependOnFrameResponse;
import com.imageworks.spcue.grpc.job.LayerCreateDependOnJobRequest;
import com.imageworks.spcue.grpc.job.LayerCreateDependOnJobResponse;
import com.imageworks.spcue.grpc.job.LayerCreateDependOnLayerRequest;
import com.imageworks.spcue.grpc.job.LayerCreateDependOnLayerResponse;
import com.imageworks.spcue.grpc.job.LayerCreateFrameByFrameDependRequest;
import com.imageworks.spcue.grpc.job.LayerCreateFrameByFrameDependResponse;
import com.imageworks.spcue.grpc.job.LayerDropDependsRequest;
import com.imageworks.spcue.grpc.job.LayerDropDependsResponse;
import com.imageworks.spcue.grpc.job.LayerEatFramesRequest;
import com.imageworks.spcue.grpc.job.LayerEatFramesResponse;
import com.imageworks.spcue.grpc.job.LayerEnableMemoryOptimizerRequest;
import com.imageworks.spcue.grpc.job.LayerEnableMemoryOptimizerResponse;
import com.imageworks.spcue.grpc.job.LayerFindLayerRequest;
import com.imageworks.spcue.grpc.job.LayerFindLayerResponse;
import com.imageworks.spcue.grpc.job.LayerGetFramesRequest;
import com.imageworks.spcue.grpc.job.LayerGetFramesResponse;
import com.imageworks.spcue.grpc.job.LayerGetLayerRequest;
import com.imageworks.spcue.grpc.job.LayerGetLayerResponse;
import com.imageworks.spcue.grpc.job.LayerGetOutputPathsRequest;
import com.imageworks.spcue.grpc.job.LayerGetOutputPathsResponse;
import com.imageworks.spcue.grpc.job.LayerGetWhatDependsOnThisRequest;
import com.imageworks.spcue.grpc.job.LayerGetWhatDependsOnThisResponse;
import com.imageworks.spcue.grpc.job.LayerGetWhatThisDependsOnRequest;
import com.imageworks.spcue.grpc.job.LayerGetWhatThisDependsOnResponse;
import com.imageworks.spcue.grpc.job.LayerInterfaceGrpc;
import com.imageworks.spcue.grpc.job.LayerKillFramesRequest;
import com.imageworks.spcue.grpc.job.LayerKillFramesResponse;
import com.imageworks.spcue.grpc.job.LayerMarkdoneFramesRequest;
import com.imageworks.spcue.grpc.job.LayerMarkdoneFramesResponse;
import com.imageworks.spcue.grpc.job.LayerRegisterOutputPathRequest;
import com.imageworks.spcue.grpc.job.LayerRegisterOutputPathResponse;
import com.imageworks.spcue.grpc.job.LayerReorderFramesRequest;
import com.imageworks.spcue.grpc.job.LayerReorderFramesResponse;
import com.imageworks.spcue.grpc.job.LayerRetryFramesRequest;
import com.imageworks.spcue.grpc.job.LayerRetryFramesResponse;
import com.imageworks.spcue.grpc.job.LayerSetMaxCoresRequest;
import com.imageworks.spcue.grpc.job.LayerSetMaxCoresResponse;
import com.imageworks.spcue.grpc.job.LayerSetMinCoresRequest;
import com.imageworks.spcue.grpc.job.LayerSetMinCoresResponse;
import com.imageworks.spcue.grpc.job.LayerSetMinGpuRequest;
import com.imageworks.spcue.grpc.job.LayerSetMinGpuResponse;
import com.imageworks.spcue.grpc.job.LayerSetMinMemoryRequest;
import com.imageworks.spcue.grpc.job.LayerSetMinMemoryResponse;
import com.imageworks.spcue.grpc.job.LayerSetTagsRequest;
import com.imageworks.spcue.grpc.job.LayerSetTagsResponse;
import com.imageworks.spcue.grpc.job.LayerSetThreadableRequest;
import com.imageworks.spcue.grpc.job.LayerSetThreadableResponse;
import com.imageworks.spcue.grpc.job.LayerStaggerFramesRequest;
import com.imageworks.spcue.grpc.job.LayerStaggerFramesResponse;
import com.imageworks.spcue.grpc.renderpartition.RenderPartition;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionType;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.LocalBookingSupport;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;
import com.imageworks.spcue.util.FrameSet;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageLayer extends LayerInterfaceGrpc.LayerInterfaceImplBase {

    private LayerDetail layer;
    private FrameSearchInterface frameSearch;

    @Autowired
    private JobManager jobManager;

    @Autowired
    private DependManager dependManager;

    @Autowired
    private JobManagerSupport jobManagerSupport;

    @Autowired
    private LayerDao layerDao;

    @Autowired
    private DispatchQueue manageQueue;

    @Autowired
    private Whiteboard whiteboard;

    @Autowired
    private LocalBookingSupport localBookingSupport;

    @Autowired
    private FrameSearchFactory frameSearchFactory;

    @Override
    public void findLayer(LayerFindLayerRequest request, StreamObserver<LayerFindLayerResponse> responseObserver) {
        responseObserver.onNext(LayerFindLayerResponse.newBuilder()
                .setLayer(whiteboard.findLayer(request.getJob(), request.getLayer()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getLayer(LayerGetLayerRequest request, StreamObserver<LayerGetLayerResponse> responseObserver) {
        responseObserver.onNext(LayerGetLayerResponse.newBuilder()
                .setLayer(whiteboard.getLayer(request.getId()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void eatFrames(LayerEatFramesRequest request, StreamObserver<LayerEatFramesResponse> responseObserver) {
        updateLayer(request.getLayer());
        manageQueue.execute(new DispatchEatFrames(frameSearch,
                new Source(request.toString()), jobManagerSupport));
        responseObserver.onNext(LayerEatFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getFrames(LayerGetFramesRequest request, StreamObserver<LayerGetFramesResponse> responseObserver) {
        updateLayer(request.getLayer());
        FrameSearchCriteria searchCriteria = request.getS();
        Descriptors.FieldDescriptor layerDescriptor = searchCriteria.getDescriptorForType().findFieldByName("layer");
        searchCriteria = searchCriteria.toBuilder()
                .clearField(layerDescriptor).build();
        FrameSeq frames = whiteboard.getFrames(frameSearchFactory.create(layer, searchCriteria));
        responseObserver.onNext(LayerGetFramesResponse.newBuilder()
                .setFrames(frames)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void killFrames(LayerKillFramesRequest request, StreamObserver<LayerKillFramesResponse> responseObserver) {
        updateLayer(request.getLayer());
        manageQueue.execute(new DispatchKillFrames(frameSearch,
                new Source(request.toString()), jobManagerSupport));
        responseObserver.onNext(LayerKillFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void markdoneFrames(LayerMarkdoneFramesRequest request,
                               StreamObserver<LayerMarkdoneFramesResponse> responseObserver) {
        updateLayer(request.getLayer());
        manageQueue.execute(new DispatchSatisfyDepends(layer, jobManagerSupport));
        responseObserver.onNext(LayerMarkdoneFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void retryFrames(LayerRetryFramesRequest request,
                            StreamObserver<LayerRetryFramesResponse> responseObserver) {
        updateLayer(request.getLayer());
        manageQueue.execute(new DispatchRetryFrames(frameSearch,
                new Source(request.toString()), jobManagerSupport));
        responseObserver.onNext(LayerRetryFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setTags(LayerSetTagsRequest request, StreamObserver<LayerSetTagsResponse> responseObserver) {
        updateLayer(request.getLayer());
        layerDao.updateLayerTags(layer, new HashSet<>(request.getTagsList()));
        responseObserver.onNext(LayerSetTagsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMinCores(LayerSetMinCoresRequest request, StreamObserver<LayerSetMinCoresResponse> responseObserver) {
        updateLayer(request.getLayer());
        jobManager.setLayerMinCores(layer, Convert.coresToCoreUnits(request.getCores()));
        responseObserver.onNext(LayerSetMinCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMinMemory(LayerSetMinMemoryRequest request, StreamObserver<LayerSetMinMemoryResponse> responseObserver) {
        updateLayer(request.getLayer());
        layerDao.updateLayerMinMemory(layer, request.getMemory());
        responseObserver.onNext(LayerSetMinMemoryResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMinGpu(LayerSetMinGpuRequest request, StreamObserver<LayerSetMinGpuResponse> responseObserver) {
        updateLayer(request.getLayer());
        layerDao.updateLayerMinGpu(layer, request.getGpu());
        responseObserver.onNext(LayerSetMinGpuResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnFrame(LayerCreateDependOnFrameRequest request,
                                        StreamObserver<LayerCreateDependOnFrameResponse> responseObserver) {
        updateLayer(request.getLayer());
        LayerOnFrame depend = new LayerOnFrame(layer, jobManager.getFrameDetail(request.getFrame().getId()));
        dependManager.createDepend(depend);
        responseObserver.onNext(LayerCreateDependOnFrameResponse.newBuilder()
                .setDepend(whiteboard.getDepend(depend))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnJob(LayerCreateDependOnJobRequest request,
                                      StreamObserver<LayerCreateDependOnJobResponse> responseObserver) {
        updateLayer(request.getLayer());
        LayerOnJob depend = new LayerOnJob(layer, jobManager.getJobDetail(request.getJob().getId()));
        dependManager.createDepend(depend);
        responseObserver.onNext(LayerCreateDependOnJobResponse.newBuilder()
                .setDepend(whiteboard.getDepend(depend))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createDependencyOnLayer(LayerCreateDependOnLayerRequest request,
                                        StreamObserver<LayerCreateDependOnLayerResponse> responseObserver) {
        updateLayer(request.getLayer());
        LayerOnLayer depend = new LayerOnLayer(layer, jobManager.getLayerDetail(request.getDependOnLayer().getId()));
        dependManager.createDepend(depend);
        responseObserver.onNext(LayerCreateDependOnLayerResponse.newBuilder()
                .setDepend(whiteboard.getDepend(depend))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void createFrameByFrameDependency(LayerCreateFrameByFrameDependRequest request,
                                             StreamObserver<LayerCreateFrameByFrameDependResponse> responseObserver) {
        updateLayer(request.getLayer());
        FrameByFrame depend = new FrameByFrame(layer, jobManager.getLayerDetail(request.getDependLayer().getId()));
        dependManager.createDepend(depend);
        responseObserver.onNext(LayerCreateFrameByFrameDependResponse.newBuilder()
                .setDepend(whiteboard.getDepend(depend))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getWhatDependsOnThis(LayerGetWhatDependsOnThisRequest request,
                                     StreamObserver<LayerGetWhatDependsOnThisResponse> responseObserver) {
        updateLayer(request.getLayer());
        responseObserver.onNext(LayerGetWhatDependsOnThisResponse.newBuilder()
                .setDepends(whiteboard.getWhatDependsOnThis(layer))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getWhatThisDependsOn(LayerGetWhatThisDependsOnRequest request,
                                     StreamObserver<LayerGetWhatThisDependsOnResponse> responseObserver) {
        updateLayer(request.getLayer());
        responseObserver.onNext(LayerGetWhatThisDependsOnResponse.newBuilder()
                .setDepends(whiteboard.getWhatThisDependsOn(layer))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void dropDepends(LayerDropDependsRequest request,
                            StreamObserver<LayerDropDependsResponse> responseObserver) {
        updateLayer(request.getLayer());
        manageQueue.execute(new DispatchDropDepends(layer, request.getTarget(), dependManager));
        responseObserver.onNext(LayerDropDependsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void reorderFrames(LayerReorderFramesRequest request,
                              StreamObserver<LayerReorderFramesResponse> responseObserver) {
        updateLayer(request.getLayer());
        manageQueue.execute(new DispatchReorderFrames(layer, new FrameSet(request.getRange()), request.getOrder(),
                jobManagerSupport));
        responseObserver.onNext(LayerReorderFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void staggerFrames(LayerStaggerFramesRequest request,
                              StreamObserver<LayerStaggerFramesResponse> responseObserver) {
        updateLayer(request.getLayer());
        manageQueue.execute(new DispatchStaggerFrames(layer, request.getRange(), request.getStagger(),
                jobManagerSupport));
        responseObserver.onNext(LayerStaggerFramesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setThreadable(LayerSetThreadableRequest request, StreamObserver<LayerSetThreadableResponse> responseObserver) {
        updateLayer(request.getLayer());
        layerDao.updateThreadable(layer, request.getThreadable());
        responseObserver.onNext(LayerSetThreadableResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void addRenderPartition(LayerAddRenderPartitionRequest request,
                                   StreamObserver<LayerAddRenderPartitionResponse> responseObserver) {
        updateLayer(request.getLayer());
        LocalHostAssignment lha = new LocalHostAssignment();
        lha.setThreads(request.getThreads());
        lha.setMaxCoreUnits(request.getMaxCores() * 100);
        lha.setMaxMemory(request.getMaxMemory());
        lha.setMaxGpu(request.getMaxGpu());
        lha.setType(RenderPartitionType.LAYER_PARTITION);
        if (localBookingSupport.bookLocal(layer, request.getHost(), request.getUsername(), lha)) {
            RenderPartition partition = whiteboard.getRenderPartition(lha);
            responseObserver.onNext(LayerAddRenderPartitionResponse.newBuilder()
                    .setRenderPartition(partition)
                    .build());
            responseObserver.onCompleted();
        } else {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to find suitable frames.")
                    .asRuntimeException());
        }

    }

    @Override
    public void registerOutputPath(LayerRegisterOutputPathRequest request,
                                   StreamObserver<LayerRegisterOutputPathResponse> responseObserver) {
        updateLayer(request.getLayer());
        jobManager.registerLayerOutput(layer, request.getSpec());
        responseObserver.onNext(LayerRegisterOutputPathResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getOutputPaths(LayerGetOutputPathsRequest request, StreamObserver<LayerGetOutputPathsResponse> responseObserver) {
        updateLayer(request.getLayer());
        responseObserver.onNext(LayerGetOutputPathsResponse.newBuilder()
                .addAllOutputPaths(jobManager.getLayerOutputs(layer))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void enableMemoryOptimizer(LayerEnableMemoryOptimizerRequest request,
                                      StreamObserver<LayerEnableMemoryOptimizerResponse> responseObserver) {
        updateLayer(request.getLayer());
        jobManager.enableMemoryOptimizer(layer, request.getValue());
        responseObserver.onNext(LayerEnableMemoryOptimizerResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMaxCores(LayerSetMaxCoresRequest request, StreamObserver<LayerSetMaxCoresResponse> responseObserver) {
        updateLayer(request.getLayer());
        jobManager.setLayerMaxCores(layer, Convert.coresToWholeCoreUnits(request.getCores()));
        responseObserver.onNext(LayerSetMaxCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    private void updateLayer(Layer layerData) {
        layer = layerDao.getLayerDetail(layerData.getId());
        frameSearch = frameSearchFactory.create(layer);
    }
}

