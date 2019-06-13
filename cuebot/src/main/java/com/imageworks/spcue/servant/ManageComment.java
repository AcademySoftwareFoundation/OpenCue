
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

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.grpc.comment.CommentDeleteRequest;
import com.imageworks.spcue.grpc.comment.CommentDeleteResponse;
import com.imageworks.spcue.grpc.comment.CommentInterfaceGrpc;
import com.imageworks.spcue.grpc.comment.CommentSaveRequest;
import com.imageworks.spcue.grpc.comment.CommentSaveResponse;
import com.imageworks.spcue.service.CommentManager;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageComment extends CommentInterfaceGrpc.CommentInterfaceImplBase {

    @Autowired
    private CommentManager commentManager;

    @Override
    public void delete(CommentDeleteRequest request, StreamObserver<CommentDeleteResponse> responseObserver) {
        commentManager.deleteComment(request.getComment().getId());
        responseObserver.onNext(CommentDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void save(CommentSaveRequest request, StreamObserver<CommentSaveResponse> responseObserver) {
        CommentDetail c = new CommentDetail();
        c.id = request.getComment().getId();
        c.message = request.getComment().getMessage();
        c.subject = request.getComment().getSubject();
        commentManager.saveComment(c);
        CommentSaveResponse response = CommentSaveResponse.newBuilder().build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }
}

