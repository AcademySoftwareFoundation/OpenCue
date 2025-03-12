
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

import com.imageworks.spcue.SpcueRuntimeException;
import io.grpc.stub.StreamObserver;

import org.springframework.dao.EmptyResultDataAccessException;
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

public class ManageAction extends ActionInterfaceGrpc.ActionInterfaceImplBase {

    private FilterManager filterManager;
    private Whiteboard whiteboard;

    @Override
    public void delete(ActionDeleteRequest request,
            StreamObserver<ActionDeleteResponse> responseObserver) {
        Action requestAction = request.getAction();
        ActionEntity existingAction = filterManager.getAction(requestAction.getId());
        FilterEntity filterEntity = filterManager.getFilter(existingAction);
        ActionEntity actionToDelete =
                ActionEntity.build(filterEntity, requestAction, requestAction.getId());
        filterManager.deleteAction(actionToDelete);
        responseObserver.onNext(ActionDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getParentFilter(ActionGetParentFilterRequest request,
            StreamObserver<ActionGetParentFilterResponse> responseObserver) {
        Filter filter = whiteboard.getFilter(ActionEntity.build(request.getAction()));
        responseObserver
                .onNext(ActionGetParentFilterResponse.newBuilder().setFilter(filter).build());
        responseObserver.onCompleted();
    }

    @Override
    public void commit(ActionCommitRequest request,
            StreamObserver<ActionCommitResponse> responseObserver) {
        Action requestAction = request.getAction();
        // Getting an action to have filterId populated from the DB
        try {
            ActionEntity persistedAction = filterManager.getAction(requestAction.getId());
            ActionEntity newAction =
                    ActionEntity.build(persistedAction, requestAction, requestAction.getId());
            filterManager.updateAction(newAction);
            responseObserver.onNext(ActionCommitResponse.newBuilder().build());
            responseObserver.onCompleted();
        } catch (EmptyResultDataAccessException e) {
            throw new SpcueRuntimeException(
                    "Invalid actionId on Action commit: " + requestAction.getId());
        }
    }

    public FilterManager getFilterManager() {
        return filterManager;
    }

    public void setFilterManager(FilterManager filterManager) {
        this.filterManager = filterManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }
}
