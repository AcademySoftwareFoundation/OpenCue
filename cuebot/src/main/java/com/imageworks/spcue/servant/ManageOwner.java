
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

import com.imageworks.spcue.OwnerEntity;
import com.imageworks.spcue.grpc.host.OwnerDeleteRequest;
import com.imageworks.spcue.grpc.host.OwnerDeleteResponse;
import com.imageworks.spcue.grpc.host.OwnerGetDeedsRequest;
import com.imageworks.spcue.grpc.host.OwnerGetDeedsResponse;
import com.imageworks.spcue.grpc.host.OwnerGetHostsRequest;
import com.imageworks.spcue.grpc.host.OwnerGetHostsResponse;
import com.imageworks.spcue.grpc.host.OwnerGetOwnerRequest;
import com.imageworks.spcue.grpc.host.OwnerGetOwnerResponse;
import com.imageworks.spcue.grpc.host.OwnerInterfaceGrpc;
import com.imageworks.spcue.grpc.host.OwnerSetShowRequest;
import com.imageworks.spcue.grpc.host.OwnerSetShowResponse;
import com.imageworks.spcue.grpc.host.OwnerTakeOwnershipRequest;
import com.imageworks.spcue.grpc.host.OwnerTakeOwnershipResponse;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.OwnerManager;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageOwner extends OwnerInterfaceGrpc.OwnerInterfaceImplBase {

    @Autowired
    private HostManager hostManager;

    @Autowired
    private OwnerManager ownerManager;

    @Autowired
    private Whiteboard whiteboard;

    @Autowired
    private AdminManager adminManager;

    @Override
    public void getOwner(OwnerGetOwnerRequest request, StreamObserver<OwnerGetOwnerResponse> responseObserver) {
        responseObserver.onNext(OwnerGetOwnerResponse.newBuilder()
                .setOwner(whiteboard.getOwner(request.getName()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void delete(OwnerDeleteRequest request, StreamObserver<OwnerDeleteResponse> responseObserver) {
        OwnerEntity owner = getOwnerById(request.getOwner().getId());
        ownerManager.deleteOwner((owner));
        OwnerDeleteResponse response = OwnerDeleteResponse.newBuilder().build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getDeeds(OwnerGetDeedsRequest request, StreamObserver<OwnerGetDeedsResponse> responseObserver) {
        OwnerEntity owner = getOwnerById(request.getOwner().getId());
        OwnerGetDeedsResponse response = OwnerGetDeedsResponse.newBuilder()
                .setDeeds(whiteboard.getDeeds(owner))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getHosts(OwnerGetHostsRequest request, StreamObserver<OwnerGetHostsResponse> responseObserver) {
        OwnerEntity owner = getOwnerById(request.getOwner().getId());
        OwnerGetHostsResponse response = OwnerGetHostsResponse.newBuilder()
                .setHosts(whiteboard.getHosts(owner))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void takeOwnership(OwnerTakeOwnershipRequest request,
                              StreamObserver<OwnerTakeOwnershipResponse> responseObserver) {
        OwnerEntity owner = getOwnerById(request.getOwner().getId());
        ownerManager.takeOwnership(owner, hostManager.findHost(request.getHost()));
        responseObserver.onNext(OwnerTakeOwnershipResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setShow(OwnerSetShowRequest request, StreamObserver<OwnerSetShowResponse> responseObserver) {
        OwnerEntity owner = getOwnerById(request.getOwner().getId());
        ownerManager.setShow(owner, adminManager.findShowEntity(request.getShow()));
        responseObserver.onNext(OwnerSetShowResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public OwnerManager getOwnerManager() {
        return ownerManager;
    }

    public void setOwnerManager(OwnerManager ownerManager) {
        this.ownerManager = ownerManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    private OwnerEntity getOwnerById(String id) {
        return ownerManager.getOwner(id);
    }
}

