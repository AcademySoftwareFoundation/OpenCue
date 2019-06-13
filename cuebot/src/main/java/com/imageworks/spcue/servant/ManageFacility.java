package com.imageworks.spcue.servant;

import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.grpc.facility.FacilityCreateRequest;
import com.imageworks.spcue.grpc.facility.FacilityCreateResponse;
import com.imageworks.spcue.grpc.facility.FacilityDeleteRequest;
import com.imageworks.spcue.grpc.facility.FacilityDeleteResponse;
import com.imageworks.spcue.grpc.facility.FacilityGetRequest;
import com.imageworks.spcue.grpc.facility.FacilityGetResponse;
import com.imageworks.spcue.grpc.facility.FacilityInterfaceGrpc;
import com.imageworks.spcue.grpc.facility.FacilityRenameRequest;
import com.imageworks.spcue.grpc.facility.FacilityRenameResponse;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class ManageFacility extends FacilityInterfaceGrpc.FacilityInterfaceImplBase {

    @Autowired
    private AdminManager adminManager;

    @Autowired
    private Whiteboard whiteboard;

    public ManageFacility() {}

    // TODO(bcipriano) Add error handling. (Issue #59)

    @Override
    public void create(FacilityCreateRequest request, StreamObserver<FacilityCreateResponse> responseObserver) {
        adminManager.createFacility(request.getName());
        FacilityCreateResponse response = FacilityCreateResponse.newBuilder()
                .setFacility(whiteboard.getFacility(request.getName()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void get(FacilityGetRequest request, StreamObserver<FacilityGetResponse> responseObserver) {
        FacilityGetResponse response = FacilityGetResponse.newBuilder()
                .setFacility(whiteboard.getFacility(request.getName()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void rename(FacilityRenameRequest request, StreamObserver<FacilityRenameResponse> responseObserver) {
        adminManager.setFacilityName(
                adminManager.getFacility(request.getFacility().getName()),
                request.getNewName());
        responseObserver.onNext(FacilityRenameResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void delete(FacilityDeleteRequest request, StreamObserver<FacilityDeleteResponse> responseObserver) {
        adminManager.deleteFacility(adminManager.getFacility(request.getName()));
        responseObserver.onNext(FacilityDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }
}
