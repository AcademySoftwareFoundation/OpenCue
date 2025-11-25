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

package com.imageworks.spcue.servant;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;

import com.imageworks.spcue.grpc.monitoring.GetFarmStatisticsRequest;
import com.imageworks.spcue.grpc.monitoring.GetFarmStatisticsResponse;
import com.imageworks.spcue.grpc.monitoring.GetFrameHistoryRequest;
import com.imageworks.spcue.grpc.monitoring.GetFrameHistoryResponse;
import com.imageworks.spcue.grpc.monitoring.GetHostHistoryRequest;
import com.imageworks.spcue.grpc.monitoring.GetHostHistoryResponse;
import com.imageworks.spcue.grpc.monitoring.GetJobHistoryRequest;
import com.imageworks.spcue.grpc.monitoring.GetJobHistoryResponse;
import com.imageworks.spcue.grpc.monitoring.GetLayerHistoryRequest;
import com.imageworks.spcue.grpc.monitoring.GetLayerHistoryResponse;
import com.imageworks.spcue.grpc.monitoring.GetLayerMemoryHistoryRequest;
import com.imageworks.spcue.grpc.monitoring.GetLayerMemoryHistoryResponse;
import com.imageworks.spcue.grpc.monitoring.HistoricalFrame;
import com.imageworks.spcue.grpc.monitoring.HistoricalJob;
import com.imageworks.spcue.grpc.monitoring.HistoricalLayer;
import com.imageworks.spcue.grpc.monitoring.LayerMemoryRecord;
import com.imageworks.spcue.grpc.monitoring.MonitoringInterfaceGrpc;
import com.imageworks.spcue.grpc.monitoring.Pagination;
import com.imageworks.spcue.service.HistoricalManager;

import io.grpc.stub.StreamObserver;

/**
 * gRPC servant for the MonitoringInterface service. Provides access to historical render farm
 * statistics.
 */
public class ManageMonitoring extends MonitoringInterfaceGrpc.MonitoringInterfaceImplBase {

    @Autowired
    private HistoricalManager historicalManager;

    @Override
    public void getJobHistory(GetJobHistoryRequest request,
            StreamObserver<GetJobHistoryResponse> responseObserver) {
        try {
            List<HistoricalJob> jobs = historicalManager.getJobHistory(request.getShowsList(),
                    request.getUsersList(), request.getShotsList(), request.getJobNameRegexList(),
                    request.getStatesList(),
                    request.hasTimeRange() ? request.getTimeRange().getStartTime() : 0,
                    request.hasTimeRange() ? request.getTimeRange().getEndTime() : 0,
                    request.getPage(), request.getPageSize(), request.getMaxResults());

            GetJobHistoryResponse response = GetJobHistoryResponse.newBuilder().addAllJobs(jobs)
                    .setPagination(Pagination.newBuilder().setPage(request.getPage())
                            .setPageSize(request.getPageSize()).setTotalRecords(jobs.size())
                            .build())
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            responseObserver.onError(io.grpc.Status.INTERNAL
                    .withDescription("Error fetching job history: " + e.getMessage())
                    .asRuntimeException());
        }
    }

    @Override
    public void getFrameHistory(GetFrameHistoryRequest request,
            StreamObserver<GetFrameHistoryResponse> responseObserver) {
        try {
            List<HistoricalFrame> frames = historicalManager.getFrameHistory(request.getJobId(),
                    request.getJobName(), request.getLayerNamesList(), request.getStatesList(),
                    request.hasTimeRange() ? request.getTimeRange().getStartTime() : 0,
                    request.hasTimeRange() ? request.getTimeRange().getEndTime() : 0,
                    request.getPage(), request.getPageSize());

            GetFrameHistoryResponse response =
                    GetFrameHistoryResponse.newBuilder().addAllFrames(frames)
                            .setPagination(Pagination.newBuilder().setPage(request.getPage())
                                    .setPageSize(request.getPageSize())
                                    .setTotalRecords(frames.size()).build())
                            .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            responseObserver.onError(io.grpc.Status.INTERNAL
                    .withDescription("Error fetching frame history: " + e.getMessage())
                    .asRuntimeException());
        }
    }

    @Override
    public void getLayerHistory(GetLayerHistoryRequest request,
            StreamObserver<GetLayerHistoryResponse> responseObserver) {
        try {
            List<HistoricalLayer> layers =
                    historicalManager.getLayerHistory(request.getJobId(), request.getJobName(),
                            request.hasTimeRange() ? request.getTimeRange().getStartTime() : 0,
                            request.hasTimeRange() ? request.getTimeRange().getEndTime() : 0,
                            request.getPage(), request.getPageSize());

            GetLayerHistoryResponse response =
                    GetLayerHistoryResponse.newBuilder().addAllLayers(layers)
                            .setPagination(Pagination.newBuilder().setPage(request.getPage())
                                    .setPageSize(request.getPageSize())
                                    .setTotalRecords(layers.size()).build())
                            .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            responseObserver.onError(io.grpc.Status.INTERNAL
                    .withDescription("Error fetching layer history: " + e.getMessage())
                    .asRuntimeException());
        }
    }

    @Override
    public void getHostHistory(GetHostHistoryRequest request,
            StreamObserver<GetHostHistoryResponse> responseObserver) {
        try {
            // Host history is typically fetched from Elasticsearch
            // For now, return an empty response
            GetHostHistoryResponse response =
                    GetHostHistoryResponse.newBuilder()
                            .setPagination(Pagination.newBuilder().setPage(request.getPage())
                                    .setPageSize(request.getPageSize()).setTotalRecords(0).build())
                            .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            responseObserver.onError(io.grpc.Status.INTERNAL
                    .withDescription("Error fetching host history: " + e.getMessage())
                    .asRuntimeException());
        }
    }

    @Override
    public void getFarmStatistics(GetFarmStatisticsRequest request,
            StreamObserver<GetFarmStatisticsResponse> responseObserver) {
        try {
            // Farm statistics are typically fetched from Prometheus/Elasticsearch
            // For now, return an empty response
            GetFarmStatisticsResponse response = GetFarmStatisticsResponse.newBuilder().build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            responseObserver.onError(io.grpc.Status.INTERNAL
                    .withDescription("Error fetching farm statistics: " + e.getMessage())
                    .asRuntimeException());
        }
    }

    @Override
    public void getLayerMemoryHistory(GetLayerMemoryHistoryRequest request,
            StreamObserver<GetLayerMemoryHistoryResponse> responseObserver) {
        try {
            List<LayerMemoryRecord> records = historicalManager.getLayerMemoryHistory(
                    request.getLayerName(), request.getShowsList(),
                    request.hasTimeRange() ? request.getTimeRange().getStartTime() : 0,
                    request.hasTimeRange() ? request.getTimeRange().getEndTime() : 0,
                    request.getMaxResults());

            GetLayerMemoryHistoryResponse response =
                    GetLayerMemoryHistoryResponse.newBuilder().addAllRecords(records).build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (Exception e) {
            responseObserver.onError(io.grpc.Status.INTERNAL
                    .withDescription("Error fetching layer memory history: " + e.getMessage())
                    .asRuntimeException());
        }
    }

    public HistoricalManager getHistoricalManager() {
        return historicalManager;
    }

    public void setHistoricalManager(HistoricalManager historicalManager) {
        this.historicalManager = historicalManager;
    }
}
