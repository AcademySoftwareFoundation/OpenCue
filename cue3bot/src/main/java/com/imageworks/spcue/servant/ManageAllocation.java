package com.imageworks.spcue.servant;

import com.imageworks.spcue.AllocationEntity;
import com.imageworks.spcue.HostEntity;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.dao.AllocationDao;
import com.imageworks.spcue.dao.criteria.HostSearch;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.commands.ManageReparentHosts;
import com.imageworks.spcue.grpc.facility.*;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.HostSearchCriteria;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.CueUtil;
import io.grpc.stub.StreamObserver;

import java.util.List;
import java.util.stream.Collectors;

public class ManageAllocation extends AllocationInterfaceGrpc.AllocationInterfaceImplBase {
    private AllocationDao allocationDao;
    private DispatchQueue manageQueue;
    private Whiteboard whiteboard;
    private AdminManager adminManager;
    private HostManager hostManager;

    public ManageAllocation() {}

    @Override
    public void create(
            AllocCreateRequest request, StreamObserver<AllocCreateResponse> responseObserver) {
        String new_name = request.getName();
        // If they pass name in the format <facility>.<name>, just remove the facility.
        if (CueUtil.verifyAllocationNameFormat(request.getName())) {
            new_name = CueUtil.splitAllocationName(request.getName())[1];
        }

        AllocationEntity detail = new AllocationEntity();
        detail.name = new_name;
        detail.tag = request.getTag();
        adminManager.createAllocation(
                adminManager.getFacility(request.getFacility().getName()), detail);

        responseObserver.onNext(
                AllocCreateResponse.newBuilder()
                        .setAllocation(whiteboard.getAllocation(detail.id))
                        .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getAll(
            AllocGetAllRequest request, StreamObserver<AllocGetAllResponse> responseObserver) {
        responseObserver.onNext(
                AllocGetAllResponse.newBuilder()
                    .setAllocations(
                        AllocationSeq.newBuilder()
                                .addAllAllocations(whiteboard.getAllocations())
                                .build())
                    .build());
        responseObserver.onCompleted();
    }

    @Override
    public void find(
            AllocFindRequest request, StreamObserver<AllocFindResponse> responseObserver) {
        responseObserver.onNext(
                AllocFindResponse.newBuilder()
                        .setAllocation(whiteboard.findAllocation(request.getName()))
                        .build());
        responseObserver.onCompleted();
    }

    @Override
    public void get(AllocGetRequest request, StreamObserver<AllocGetResponse> responseObserver) {
        responseObserver.onNext(
                AllocGetResponse.newBuilder()
                    .setAllocation(whiteboard.findAllocation(request.getId()))
                    .build());
        responseObserver.onCompleted();
    }

    @Override
    public void delete(
            AllocDeleteRequest request, StreamObserver<AllocDeleteResponse> responseObserver) {
        AllocationEntity alloc = adminManager.findAllocationDetail(
                request.getAllocation().getFacility(), request.getAllocation().getName());
        adminManager.deleteAllocation(alloc);
        responseObserver.onNext(AllocDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void findHosts(
            AllocFindHostsRequest request,
            StreamObserver<AllocFindHostsResponse> responseObserver) {
        HostSearchCriteria searchCriteria = request.getR().toBuilder()
                .addAllocs(request.getAllocation().getId())
                .build();
        responseObserver.onNext(AllocFindHostsResponse.newBuilder()
                .setHosts(whiteboard.getHosts(new HostSearch(searchCriteria)))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getHosts(
            AllocGetHostsRequest request, StreamObserver<AllocGetHostsResponse> responseObserver) {
        AllocationEntity allocEntity = toAllocationEntity(request.getAllocation());
        responseObserver.onNext(AllocGetHostsResponse.newBuilder()
                .setHosts(whiteboard.getHosts(HostSearch.byAllocation(allocEntity)))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getSubscriptions(
            AllocGetSubscriptionsRequest request,
            StreamObserver<AllocGetSubscriptionsResponse> responseObserver) {
        AllocationEntity allocEntity = toAllocationEntity(request.getAllocation());
        responseObserver.onNext(AllocGetSubscriptionsResponse.newBuilder()
                .setSubscriptions(whiteboard.getSubscriptions(allocEntity))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void reparentHosts(
            AllocReparentHostsRequest request,
            StreamObserver<AllocReparentHostsResponse> responseObserver) {
        AllocationEntity allocEntity = toAllocationEntity(request.getAllocation());
        List<Host> hosts = request.getHosts().getHostsList();
        List<HostInterface> hostEntities = hosts.stream()
                .map(HostEntity::new)
                .collect(Collectors.toList());
        manageQueue.execute(new ManageReparentHosts(allocEntity, hostEntities, hostManager));
    }

    @Override
    public void setBillable(
            AllocSetBillableRequest request,
            StreamObserver<AllocSetBillableResponse> responseObserver) {
        AllocationEntity alloc = adminManager.findAllocationDetail(
                request.getAllocation().getFacility(), request.getAllocation().getName());
        adminManager.setAllocationBillable(alloc, request.getValue());
        responseObserver.onNext(AllocSetBillableResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setName(
            AllocSetNameRequest request, StreamObserver<AllocSetNameResponse> responseObserver) {
        AllocationEntity alloc = adminManager.findAllocationDetail(
                request.getAllocation().getFacility(), request.getAllocation().getName());
        adminManager.setAllocationName(alloc, request.getName());
        responseObserver.onNext(AllocSetNameResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setTag(
            AllocSetTagRequest request, StreamObserver<AllocSetTagResponse> responseObserver) {
        AllocationEntity alloc = adminManager.findAllocationDetail(
                request.getAllocation().getFacility(), request.getAllocation().getName());
        adminManager.setAllocationTag(alloc, request.getTag());
        responseObserver.onNext(AllocSetTagResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public AllocationDao getAllocationDao() {
        return allocationDao;
    }

    public void setAllocationDao(AllocationDao allocationDao) {
        this.allocationDao = allocationDao;
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

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    private AllocationEntity toAllocationEntity(Allocation allocGrpc) {
        AllocationEntity allocEntity = new AllocationEntity();
        allocEntity.id = allocGrpc.getId();
        allocEntity.name = allocGrpc.getName();
        allocEntity.tag = allocGrpc.getTag();
        allocEntity.facilityId = allocGrpc.getFacility();
        return allocEntity;
    }
}
