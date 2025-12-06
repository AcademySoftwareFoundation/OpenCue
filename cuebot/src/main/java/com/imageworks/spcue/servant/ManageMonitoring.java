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
import com.imageworks.spcue.grpc.monitoring.MonitoringInterfaceGrpc;

import io.grpc.stub.StreamObserver;

/**
 * gRPC servant for the MonitoringInterface service.
 *
 * Historical data queries are not implemented here - historical event data is indexed to
 * Elasticsearch by the external monitoring-indexer service and should be queried directly via the
 * Elasticsearch HTTP API or Kibana.
 */
public class ManageMonitoring extends MonitoringInterfaceGrpc.MonitoringInterfaceImplBase {

    @Override
    public void getJobHistory(GetJobHistoryRequest request,
            StreamObserver<GetJobHistoryResponse> responseObserver) {
        responseObserver
                .onError(io.grpc.Status.UNIMPLEMENTED
                        .withDescription("Historical data is indexed to Elasticsearch. "
                                + "Query via Elasticsearch HTTP API or Kibana.")
                        .asRuntimeException());
    }

    @Override
    public void getFrameHistory(GetFrameHistoryRequest request,
            StreamObserver<GetFrameHistoryResponse> responseObserver) {
        responseObserver
                .onError(io.grpc.Status.UNIMPLEMENTED
                        .withDescription("Historical data is indexed to Elasticsearch. "
                                + "Query via Elasticsearch HTTP API or Kibana.")
                        .asRuntimeException());
    }

    @Override
    public void getLayerHistory(GetLayerHistoryRequest request,
            StreamObserver<GetLayerHistoryResponse> responseObserver) {
        responseObserver
                .onError(io.grpc.Status.UNIMPLEMENTED
                        .withDescription("Historical data is indexed to Elasticsearch. "
                                + "Query via Elasticsearch HTTP API or Kibana.")
                        .asRuntimeException());
    }

    @Override
    public void getHostHistory(GetHostHistoryRequest request,
            StreamObserver<GetHostHistoryResponse> responseObserver) {
        responseObserver
                .onError(io.grpc.Status.UNIMPLEMENTED
                        .withDescription("Historical data is indexed to Elasticsearch. "
                                + "Query via Elasticsearch HTTP API or Kibana.")
                        .asRuntimeException());
    }

    @Override
    public void getFarmStatistics(GetFarmStatisticsRequest request,
            StreamObserver<GetFarmStatisticsResponse> responseObserver) {
        responseObserver.onError(io.grpc.Status.UNIMPLEMENTED
                .withDescription("Farm statistics should be queried from Prometheus/Elasticsearch.")
                .asRuntimeException());
    }

    @Override
    public void getLayerMemoryHistory(GetLayerMemoryHistoryRequest request,
            StreamObserver<GetLayerMemoryHistoryResponse> responseObserver) {
        responseObserver
                .onError(io.grpc.Status.UNIMPLEMENTED
                        .withDescription("Historical data is indexed to Elasticsearch. "
                                + "Query via Elasticsearch HTTP API or Kibana.")
                        .asRuntimeException());
    }
}
