package com.imageworks.spcue.servant;

import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.grpc.limit.LimitCreateRequest;
import com.imageworks.spcue.grpc.limit.LimitCreateResponse;
import com.imageworks.spcue.grpc.limit.LimitDeleteRequest;
import com.imageworks.spcue.grpc.limit.LimitDeleteResponse;
import com.imageworks.spcue.grpc.limit.LimitFindRequest;
import com.imageworks.spcue.grpc.limit.LimitFindResponse;
import com.imageworks.spcue.grpc.limit.LimitGetRequest;
import com.imageworks.spcue.grpc.limit.LimitGetResponse;
import com.imageworks.spcue.grpc.limit.LimitGetAllRequest;
import com.imageworks.spcue.grpc.limit.LimitGetAllResponse;
import com.imageworks.spcue.grpc.limit.LimitInterfaceGrpc;
import com.imageworks.spcue.grpc.limit.LimitRenameRequest;
import com.imageworks.spcue.grpc.limit.LimitRenameResponse;
import com.imageworks.spcue.grpc.limit.LimitSetMaxValueRequest;
import com.imageworks.spcue.grpc.limit.LimitSetMaxValueResponse;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.Whiteboard;


public class ManageLimit extends LimitInterfaceGrpc.LimitInterfaceImplBase {
    private AdminManager adminManager;
    private Whiteboard whiteboard;

    @Override
    public void create(LimitCreateRequest request, StreamObserver<LimitCreateResponse> responseObserver) {
        String limitId = adminManager.createLimit(request.getName(), request.getMaxValue());
        LimitCreateResponse response = LimitCreateResponse.newBuilder()
                .setLimit(whiteboard.getLimit(limitId))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void delete(LimitDeleteRequest request, StreamObserver<LimitDeleteResponse> responseObserver) {
        adminManager.deleteLimit(adminManager.findLimit(request.getName()));
        responseObserver.onNext(LimitDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void find(LimitFindRequest request, StreamObserver<LimitFindResponse> responseObserver) {
        LimitFindResponse response = LimitFindResponse.newBuilder()
                .setLimit(whiteboard.findLimit(request.getName()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void get(LimitGetRequest request, StreamObserver<LimitGetResponse> responseObserver) {
        LimitGetResponse response = LimitGetResponse.newBuilder()
                .setLimit(whiteboard.getLimit(request.getId()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getAll(LimitGetAllRequest request,
                          StreamObserver<LimitGetAllResponse> responseObserver) {
        responseObserver.onNext(LimitGetAllResponse.newBuilder()
                .addAllLimits(whiteboard.getLimits())
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void rename(LimitRenameRequest request, StreamObserver<LimitRenameResponse> responseObserver) {
        adminManager.setLimitName(
                adminManager.findLimit(request.getOldName()),
                request.getNewName());
        responseObserver.onNext(LimitRenameResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMaxValue(LimitSetMaxValueRequest request, StreamObserver<LimitSetMaxValueResponse> responseObserver) {
        adminManager.setLimitMaxValue(
                adminManager.findLimit(request.getName()),
                request.getMaxValue());
        responseObserver.onNext(LimitSetMaxValueResponse.newBuilder().build());
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
}
