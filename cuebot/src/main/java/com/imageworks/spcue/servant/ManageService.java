
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

import java.util.LinkedHashSet;

import com.google.common.collect.Sets;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.grpc.service.Service;
import com.imageworks.spcue.grpc.service.ServiceCreateServiceRequest;
import com.imageworks.spcue.grpc.service.ServiceCreateServiceResponse;
import com.imageworks.spcue.grpc.service.ServiceDeleteRequest;
import com.imageworks.spcue.grpc.service.ServiceDeleteResponse;
import com.imageworks.spcue.grpc.service.ServiceGetDefaultServicesRequest;
import com.imageworks.spcue.grpc.service.ServiceGetDefaultServicesResponse;
import com.imageworks.spcue.grpc.service.ServiceGetServiceRequest;
import com.imageworks.spcue.grpc.service.ServiceGetServiceResponse;
import com.imageworks.spcue.grpc.service.ServiceInterfaceGrpc;
import com.imageworks.spcue.grpc.service.ServiceUpdateRequest;
import com.imageworks.spcue.grpc.service.ServiceUpdateResponse;
import com.imageworks.spcue.service.ServiceManager;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.stereotype.Component;

@Component
public class ManageService extends ServiceInterfaceGrpc.ServiceInterfaceImplBase {

    @Autowired
    private ServiceManager serviceManager;

    @Autowired
    private Whiteboard whiteboard;

    @Override
    public void createService(ServiceCreateServiceRequest request,
                              StreamObserver<ServiceCreateServiceResponse> responseObserver) {
        ServiceEntity service = new ServiceEntity();
        service.name = request.getData().getName();
        service.minCores = request.getData().getMinCores();
        service.maxCores = request.getData().getMaxCores();
        service.minMemory = request.getData().getMinMemory();
        service.minGpu = request.getData().getMinGpu();
        service.tags = Sets.newLinkedHashSet(request.getData().getTagsList());
        service.threadable = request.getData().getThreadable();
        serviceManager.createService(service);
        responseObserver.onNext(ServiceCreateServiceResponse.newBuilder()
                .setService(whiteboard.getService(service.getId()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getDefaultServices(ServiceGetDefaultServicesRequest request,
                                   StreamObserver<ServiceGetDefaultServicesResponse> responseObserver) {
        responseObserver.onNext(ServiceGetDefaultServicesResponse.newBuilder()
                .setServices(whiteboard.getDefaultServices())
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getService(ServiceGetServiceRequest request,
                           StreamObserver<ServiceGetServiceResponse> responseObserver) {
        try {
            responseObserver.onNext(ServiceGetServiceResponse.newBuilder()
                    .setService(whiteboard.getService(request.getName()))
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
    public void delete(ServiceDeleteRequest request, StreamObserver<ServiceDeleteResponse> responseObserver) {
        serviceManager.deleteService(toServiceEntity(request.getService()));
        responseObserver.onNext(ServiceDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void update(ServiceUpdateRequest request, StreamObserver<ServiceUpdateResponse> responseObserver) {
        serviceManager.updateService(toServiceEntity(request.getService()));
        responseObserver.onNext(ServiceUpdateResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public ServiceManager getServiceManager() {
        return serviceManager;
    }

    public void setServiceManager(ServiceManager serviceManager) {
        this.serviceManager = serviceManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    private ServiceEntity toServiceEntity(Service service) {
        ServiceEntity entity = new ServiceEntity();
        entity.id = service.getId();
        entity.name = service.getName();
        entity.minCores = service.getMinCores();
        entity.maxCores = service.getMaxCores();
        entity.minMemory = service.getMinMemory();
        entity.minGpu = service.getMinGpu();
        entity.tags = new LinkedHashSet<> (service.getTagsList());
        entity.threadable = service.getThreadable();
        return entity;
    }
}
