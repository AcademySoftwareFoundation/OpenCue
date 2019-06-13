
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

import com.imageworks.spcue.ActionEntity;
import com.imageworks.spcue.FilterEntity;
import com.imageworks.spcue.grpc.filter.Action;
import com.imageworks.spcue.grpc.filter.ActionCommitRequest;
import com.imageworks.spcue.grpc.filter.ActionCommitResponse;
import com.imageworks.spcue.grpc.filter.ActionDeleteRequest;
import com.imageworks.spcue.grpc.filter.ActionDeleteResponse;
import com.imageworks.spcue.grpc.filter.ActionGetParentFilterRequest;
import com.imageworks.spcue.grpc.filter.ActionGetParentFilterResponse;
import com.imageworks.spcue.grpc.filter.ActionInterfaceGrpc;
import com.imageworks.spcue.grpc.filter.Filter;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageAction extends ActionInterfaceGrpc.ActionInterfaceImplBase {

    @Autowired
    private FilterManager filterManager;

    @Autowired
    private Whiteboard whiteboard;

    @Override
    public void delete(ActionDeleteRequest request, StreamObserver<ActionDeleteResponse> responseObserver) {
        filterManager.deleteAction(ActionEntity.build(request.getAction()));
        responseObserver.onNext(ActionDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getParentFilter(ActionGetParentFilterRequest request,
                                StreamObserver<ActionGetParentFilterResponse> responseObserver) {
        Filter filter = whiteboard.getFilter(ActionEntity.build(request.getAction()));
        responseObserver.onNext(ActionGetParentFilterResponse.newBuilder().setFilter(filter).build());
        responseObserver.onCompleted();
    }

    @Override
    public void commit(ActionCommitRequest request, StreamObserver<ActionCommitResponse> responseObserver) {
        Action requestAction = request.getAction();
        ActionEntity requestEntity = ActionEntity.build(requestAction);
        FilterEntity filterEntity = filterManager.getFilter(requestEntity);
        ActionEntity newAction = ActionEntity.build(filterEntity, requestAction, requestAction.getId());
        filterManager.updateAction(newAction);
        responseObserver.onNext(ActionCommitResponse.newBuilder().build());
        responseObserver.onCompleted();
    }
}

