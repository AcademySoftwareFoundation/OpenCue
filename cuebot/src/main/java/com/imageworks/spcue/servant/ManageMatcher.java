
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

import com.imageworks.spcue.MatcherEntity;
import com.imageworks.spcue.grpc.filter.Matcher;
import com.imageworks.spcue.grpc.filter.MatcherCommitRequest;
import com.imageworks.spcue.grpc.filter.MatcherCommitResponse;
import com.imageworks.spcue.grpc.filter.MatcherDeleteRequest;
import com.imageworks.spcue.grpc.filter.MatcherDeleteResponse;
import com.imageworks.spcue.grpc.filter.MatcherGetParentFilterRequest;
import com.imageworks.spcue.grpc.filter.MatcherGetParentFilterResponse;
import com.imageworks.spcue.grpc.filter.MatcherInterfaceGrpc;
import com.imageworks.spcue.service.FilterManager;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageMatcher extends MatcherInterfaceGrpc.MatcherInterfaceImplBase {

    @Autowired
    private FilterManager filterManager;

    @Autowired
    private Whiteboard whiteboard;

    public void delete(MatcherDeleteRequest request, StreamObserver<MatcherDeleteResponse> responseObserver) {
        filterManager.deleteMatcher(filterManager.getMatcher(request.getMatcher().getId()));
        responseObserver.onNext(MatcherDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public void getParentFilter(MatcherGetParentFilterRequest request,
                                StreamObserver<MatcherGetParentFilterResponse> responseObserver) {
        MatcherEntity matcherEntity = filterManager.getMatcher(request.getMatcher().getId());
        MatcherGetParentFilterResponse response = MatcherGetParentFilterResponse.newBuilder()
                .setFilter(whiteboard.getFilter(matcherEntity))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    public void commit(MatcherCommitRequest request, StreamObserver<MatcherCommitResponse> responseObserver) {
        Matcher newMatcherData = request.getMatcher();
        String id = newMatcherData.getId();
        MatcherEntity oldMatcher = filterManager.getMatcher(id);
        MatcherEntity newMatcher = MatcherEntity.build(filterManager.getFilter(oldMatcher), newMatcherData, id);
        filterManager.updateMatcher(newMatcher);
        responseObserver.onNext(MatcherCommitResponse.newBuilder().build());
        responseObserver.onCompleted();
    }
}

