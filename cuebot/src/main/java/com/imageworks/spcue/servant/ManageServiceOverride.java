
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

import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.ServiceEntity;
import com.imageworks.spcue.grpc.service.Service;
import com.imageworks.spcue.grpc.service.ServiceOverrideDeleteRequest;
import com.imageworks.spcue.grpc.service.ServiceOverrideDeleteResponse;
import com.imageworks.spcue.grpc.service.ServiceOverrideInterfaceGrpc;
import com.imageworks.spcue.grpc.service.ServiceOverrideUpdateRequest;
import com.imageworks.spcue.grpc.service.ServiceOverrideUpdateResponse;
import com.imageworks.spcue.service.ServiceManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageServiceOverride extends ServiceOverrideInterfaceGrpc.ServiceOverrideInterfaceImplBase {

    @Autowired
    private ServiceManager serviceManager;

    @Override
    public void delete(ServiceOverrideDeleteRequest request,
                       StreamObserver<ServiceOverrideDeleteResponse> responseObserver) {
        serviceManager.deleteService(toServiceEntity(request.getService()));
        responseObserver.onNext(ServiceOverrideDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void update(ServiceOverrideUpdateRequest request,
                       StreamObserver<ServiceOverrideUpdateResponse> responseObserver) {
        serviceManager.updateService(toServiceEntity(request.getService()));
        responseObserver.onNext(ServiceOverrideUpdateResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public ServiceManager getServiceManager() {
        return serviceManager;
    }

    public void setServiceManager(ServiceManager serviceManager) {
        this.serviceManager = serviceManager;
    }

    private ServiceEntity toServiceEntity(Service service) {
        ServiceEntity entity = new ServiceEntity();
        entity.id = service.getId();
        entity.name = service.getName();
        entity.minCores = service.getMinCores();
        entity.maxCores = service.getMaxCores();
        entity.minMemory = service.getMinMemory();
        entity.minGpu = service.getMinGpu();
        entity.tags = new LinkedHashSet<>(service.getTagsList());
        entity.threadable = service.getThreadable();
        return entity;
    }
}
