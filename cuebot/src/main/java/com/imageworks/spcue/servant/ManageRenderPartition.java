
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

import com.imageworks.spcue.LocalHostAssignment;
import com.imageworks.spcue.grpc.renderpartition.RenderPartDeleteRequest;
import com.imageworks.spcue.grpc.renderpartition.RenderPartDeleteResponse;
import com.imageworks.spcue.grpc.renderpartition.RenderPartSetMaxResourcesRequest;
import com.imageworks.spcue.grpc.renderpartition.RenderPartSetMaxResourcesResponse;
import com.imageworks.spcue.grpc.renderpartition.RenderPartition;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionInterfaceGrpc;
import com.imageworks.spcue.service.BookingManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageRenderPartition extends RenderPartitionInterfaceGrpc.RenderPartitionInterfaceImplBase {

    @Autowired
    private BookingManager bookingManager;

    @Override
    public void delete(RenderPartDeleteRequest request, StreamObserver<RenderPartDeleteResponse> responseObserver) {
        bookingManager.deactivateLocalHostAssignment(getLocalHostAssignment(request.getRenderPartition()));
        responseObserver.onNext(RenderPartDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMaxResources(RenderPartSetMaxResourcesRequest request,
                                StreamObserver<RenderPartSetMaxResourcesResponse> responseObserver) {
        LocalHostAssignment localJobAssign = getLocalHostAssignment(request.getRenderPartition());
        bookingManager.setMaxResources(localJobAssign, request.getCores(), request.getMemory(), request.getGpu());
        responseObserver.onNext(RenderPartSetMaxResourcesResponse.newBuilder().build());
        responseObserver.onCompleted();
    }


    public BookingManager getBookingManager() {
        return bookingManager;
    }

    public void setBookingManager(BookingManager bookingManager) {
        this.bookingManager = bookingManager;
    }

    private LocalHostAssignment getLocalHostAssignment(RenderPartition renderPartition) {
        return bookingManager.getLocalHostAssignment(renderPartition.getId());
    }
}

