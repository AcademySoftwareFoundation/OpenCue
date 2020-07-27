
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
import org.apache.log4j.Logger;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.grpc.depend.DependGetDependRequest;
import com.imageworks.spcue.grpc.depend.DependGetDependResponse;
import com.imageworks.spcue.grpc.depend.DependInterfaceGrpc;
import com.imageworks.spcue.grpc.depend.DependSatisfyRequest;
import com.imageworks.spcue.grpc.depend.DependSatisfyResponse;
import com.imageworks.spcue.grpc.depend.DependUnsatisfyRequest;
import com.imageworks.spcue.grpc.depend.DependUnsatisfyResponse;
import com.imageworks.spcue.service.DependManager;
import com.imageworks.spcue.service.Whiteboard;

public class ManageDepend extends DependInterfaceGrpc.DependInterfaceImplBase {

    private static final Logger logger = Logger.getLogger(ManageDepend.class);

    private DependManager dependManager;
    private DispatchQueue manageQueue;
    private Whiteboard whiteboard;

    @Override
    public void getDepend(DependGetDependRequest request, StreamObserver<DependGetDependResponse> responseObserver) {
        try {
            responseObserver.onNext(DependGetDependResponse.newBuilder()
                    .setDepend(whiteboard.getDepend(request.getId()))
                    .build());
            responseObserver.onCompleted();
        } catch (EmptyResultDataAccessException e) {
            responseObserver.onError(Status.NOT_FOUND
                    .withDescription(e.getMessage())
                    .withCause(e)
                    .asRuntimeException());
        }
    }

    public void satisfy(DependSatisfyRequest request, StreamObserver<DependSatisfyResponse> responseObserver) {

        LightweightDependency depend = dependManager.getDepend(request.getDepend().getId());
        manageQueue.execute(new Runnable() {
            public void run() {
                try {
                    logger.info("dropping dependency: " + depend.id);
                    dependManager.satisfyDepend(depend);
                } catch (Exception e) {
                    logger.error("error satisfying dependency: "
                            + depend.getId() + " , " + e);
                }
            }
        });
        responseObserver.onNext(DependSatisfyResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public void unsatisfy(DependUnsatisfyRequest request, StreamObserver<DependUnsatisfyResponse> responseObserver) {
        LightweightDependency depend = dependManager.getDepend(request.getDepend().getId());
        dependManager.unsatisfyDepend(depend);
        responseObserver.onNext(DependUnsatisfyResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public DependManager getDependManager() {
        return dependManager;
    }

    public void setDependManager(DependManager dependManager) {
        this.dependManager = dependManager;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }
}

