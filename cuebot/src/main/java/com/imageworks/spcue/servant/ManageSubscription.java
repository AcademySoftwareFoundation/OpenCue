
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

import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.springframework.dao.EmptyResultDataAccessException;

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


public class ManageSubscription extends SubscriptionInterfaceGrpc.SubscriptionInterfaceImplBase {

    private AdminManager adminManager;
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
            throws CueGrpcException{
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
        } catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.NOT_FOUND
                    .withDescription("A subscription to " + name + " was not found.")
                    .withCause(e)
                    .asRuntimeException());
        }
    }

    @Override
    public void get(SubscriptionGetRequest request, StreamObserver<SubscriptionGetResponse> responseObserver) {
        try {
            SubscriptionGetResponse response = SubscriptionGetResponse.newBuilder()
                    .setSubscription(whiteboard.getSubscription(request.getId()))
                    .build();
            responseObserver.onNext(response);
            responseObserver.onCompleted();
        } catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.NOT_FOUND
                    .withDescription(e.getMessage())
                    .withCause(e)
                    .asRuntimeException());
        }
    }

    @Override
    public void setBurst(SubscriptionSetBurstRequest request,
                         StreamObserver<SubscriptionSetBurstResponse> responseObserver) {
        adminManager.setSubscriptionBurst(
                getSubscriptionDetail(request.getSubscription()),
                request.getBurst());
        responseObserver.onNext(SubscriptionSetBurstResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setSize(SubscriptionSetSizeRequest request,
                        StreamObserver<SubscriptionSetSizeResponse> responseObserver) {
        adminManager.setSubscriptionSize(
                getSubscriptionDetail(request.getSubscription()),
                request.getNewSize());
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

