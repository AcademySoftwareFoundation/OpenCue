
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

import com.imageworks.spcue.CueGrpcException;
import com.imageworks.spcue.EntityNotFoundException;
import com.imageworks.spcue.SubscriptionEntity;
import com.imageworks.spcue.grpc.subscription.Subscription;
import com.imageworks.spcue.grpc.subscription.SubscriptionDeleteRequest;
import com.imageworks.spcue.grpc.subscription.SubscriptionDeleteResponse;
import com.imageworks.spcue.grpc.subscription.SubscriptionFindRequest;
import com.imageworks.spcue.grpc.subscription.SubscriptionFindResponse;
import com.imageworks.spcue.grpc.subscription.SubscriptionGetRequest;
import com.imageworks.spcue.grpc.subscription.SubscriptionGetResponse;
import com.imageworks.spcue.grpc.subscription.SubscriptionInterfaceGrpc;
import com.imageworks.spcue.grpc.subscription.SubscriptionSetBurstRequest;
import com.imageworks.spcue.grpc.subscription.SubscriptionSetBurstResponse;
import com.imageworks.spcue.grpc.subscription.SubscriptionSetSizeRequest;
import com.imageworks.spcue.grpc.subscription.SubscriptionSetSizeResponse;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageSubscription extends SubscriptionInterfaceGrpc.SubscriptionInterfaceImplBase {

    @Autowired
    private AdminManager adminManager;

    @Autowired
    private Whiteboard whiteboard;

    @Override
    public void delete(SubscriptionDeleteRequest request, StreamObserver<SubscriptionDeleteResponse> responseObserver) {
        adminManager.deleteSubscription(
                getSubscriptionDetail(request.getSubscription())
        );
        responseObserver.onNext(SubscriptionDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void find(SubscriptionFindRequest request, StreamObserver<SubscriptionFindResponse> responseObserver)
            throws EntityNotFoundException, CueGrpcException{
        String name = request.getName();
        try {
            String[] parts = name.split("\\.", 3);
            if (parts.length != 3) {
                throw new CueGrpcException("Subscription names must be in the form of alloc.show");
            }
            SubscriptionFindResponse response = SubscriptionFindResponse.newBuilder()
                    .setSubscription(whiteboard.findSubscription(parts[2], parts[0] + "." + parts[1]))
                    .build();
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (org.springframework.dao.EmptyResultDataAccessException e) {
            throw new EntityNotFoundException("A subscription to " + name + " was not found.");
        }
    }

    @Override
    public void get(SubscriptionGetRequest request, StreamObserver<SubscriptionGetResponse> responseObserver) {
        SubscriptionGetResponse response = SubscriptionGetResponse.newBuilder()
                .setSubscription(whiteboard.getSubscription(request.getId()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void setBurst(SubscriptionSetBurstRequest request,
                         StreamObserver<SubscriptionSetBurstResponse> responseObserver) {
        adminManager.setSubscriptionBurst(
                getSubscriptionDetail(request.getSubscription()),
                Convert.coresToWholeCoreUnits(request.getBurst())
        );
        responseObserver.onNext(SubscriptionSetBurstResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setSize(SubscriptionSetSizeRequest request,
                        StreamObserver<SubscriptionSetSizeResponse> responseObserver) {
        adminManager.setSubscriptionSize(
                getSubscriptionDetail(request.getSubscription()),
                Convert.coresToWholeCoreUnits(request.getNewSize())
        );
        responseObserver.onNext(SubscriptionSetSizeResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    private SubscriptionEntity getSubscriptionDetail(Subscription subscription) {
        return adminManager.getSubscriptionDetail(subscription.getId());
    }
}

