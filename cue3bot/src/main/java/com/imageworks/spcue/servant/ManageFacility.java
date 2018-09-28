package com.imageworks.spcue.servant;

import com.imageworks.spcue.CueGrpc.Empty;
import com.imageworks.spcue.CueGrpc.Facility;
import com.imageworks.spcue.CueGrpc.FacilityCreateRequest;
import com.imageworks.spcue.CueGrpc.FacilityDeleteRequest;
import com.imageworks.spcue.CueGrpc.FacilityGetRequest;
import com.imageworks.spcue.CueGrpc.FacilityInterfaceGrpc;
import com.imageworks.spcue.CueGrpc.FacilityRenameRequest;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.Whiteboard;
import io.grpc.stub.StreamObserver;

public class ManageFacility extends FacilityInterfaceGrpc.FacilityInterfaceImplBase {
    private AdminManager adminManager;
    private Whiteboard whiteboard;

    public ManageFacility() {}

    // TODO(cipriano) Add error handling.

    @Override
    public void create(FacilityCreateRequest request, StreamObserver<Facility> responseObserver) {
        adminManager.createFacility(request.getName());
        responseObserver.onNext(whiteboard.getFacility(request.getName()));
        responseObserver.onCompleted();
    }

    @Override
    public void get(FacilityGetRequest request, StreamObserver<Facility> responseObserver) {
        responseObserver.onNext(whiteboard.getFacility(request.getName()));
        responseObserver.onCompleted();
    }

    @Override
    public void rename(FacilityRenameRequest request, StreamObserver<Empty> responseObserver) {
        adminManager.setFacilityName(
                adminManager.getFacility(request.getFacility().getName()),
                request.getNewName());
        responseObserver.onNext(Empty.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void delete(FacilityDeleteRequest request, StreamObserver<Empty> responseObserver) {
        adminManager.deleteFacility(adminManager.getFacility(request.getName()));
        responseObserver.onNext(Empty.newBuilder().build());
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
