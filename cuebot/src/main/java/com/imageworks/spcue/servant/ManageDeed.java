
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

import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.DeedEntity;
import com.imageworks.spcue.grpc.host.Deed;
import com.imageworks.spcue.grpc.host.DeedDeleteRequest;
import com.imageworks.spcue.grpc.host.DeedDeleteResponse;
import com.imageworks.spcue.grpc.host.DeedGetHostRequest;
import com.imageworks.spcue.grpc.host.DeedGetHostResponse;
import com.imageworks.spcue.grpc.host.DeedGetOwnerRequest;
import com.imageworks.spcue.grpc.host.DeedGetOwnerResponse;
import com.imageworks.spcue.grpc.host.DeedInterfaceGrpc;
import com.imageworks.spcue.grpc.host.DeedSetBlackoutTimeEnabledRequest;
import com.imageworks.spcue.grpc.host.DeedSetBlackoutTimeEnabledResponse;
import com.imageworks.spcue.grpc.host.DeedSetBlackoutTimeRequest;
import com.imageworks.spcue.grpc.host.DeedSetBlackoutTimeResponse;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.Owner;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageDeed extends DeedInterfaceGrpc.DeedInterfaceImplBase {

    @Autowired
    private OwnerManager ownerManager;

    @Autowired
    private Whiteboard whiteboard;

    @Override
    public void delete(DeedDeleteRequest request, StreamObserver<DeedDeleteResponse> responseObserver) {
        ownerManager.removeDeed(toEntity(request.getDeed()));
        responseObserver.onNext(DeedDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getHost(DeedGetHostRequest request, StreamObserver<DeedGetHostResponse> responseObserver) {
        Host host = whiteboard.getHost(toEntity(request.getDeed()));
        responseObserver.onNext(DeedGetHostResponse.newBuilder().setHost(host).build());
        responseObserver.onCompleted();
    }

    @Override
    public void getOwner(DeedGetOwnerRequest request, StreamObserver<DeedGetOwnerResponse> responseObserver) {
        Owner owner = whiteboard.getOwner(toEntity(request.getDeed()));
        responseObserver.onNext(DeedGetOwnerResponse.newBuilder().setOwner(owner).build());
        responseObserver.onCompleted();
    }

    @Override
    public void setBlackoutTime(DeedSetBlackoutTimeRequest request,
                                StreamObserver<DeedSetBlackoutTimeResponse> responseObserver) {
        ownerManager.setBlackoutTime(toEntity(request.getDeed()), request.getStartTime(), request.getStopTime());
        responseObserver.onNext(DeedSetBlackoutTimeResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setBlackoutTimeEnabled(DeedSetBlackoutTimeEnabledRequest request,
                                StreamObserver<DeedSetBlackoutTimeEnabledResponse> responseObserver) {
        ownerManager.setBlackoutTimeEnabled(toEntity(request.getDeed()), request.getEnabled());
        responseObserver.onNext(DeedSetBlackoutTimeEnabledResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    private DeedEntity toEntity(Deed deed) {
        DeedEntity entity = new DeedEntity();
        entity.id = deed.getId();
        entity.host = deed.getHost();
        entity.owner = deed.getOwner();
        entity.show = deed.getShow();
        entity.isBlackoutEnabled = deed.getBlackout();
        entity.blackoutStart = deed.getBlackoutStartTime();
        entity.blackoutStop = deed.getBlackoutStopTime();
        return entity;
    }
}

