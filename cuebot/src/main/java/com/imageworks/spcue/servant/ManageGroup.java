
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

import java.util.ArrayList;
import java.util.List;

import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.GroupDetail;
import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.Inherit;
import com.imageworks.spcue.dao.GroupDao;
import com.imageworks.spcue.dao.JobDao;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.grpc.job.Group;
import com.imageworks.spcue.grpc.job.GroupCreateSubGroupRequest;
import com.imageworks.spcue.grpc.job.GroupCreateSubGroupResponse;
import com.imageworks.spcue.grpc.job.GroupDeleteRequest;
import com.imageworks.spcue.grpc.job.GroupDeleteResponse;
import com.imageworks.spcue.grpc.job.GroupFindGroupRequest;
import com.imageworks.spcue.grpc.job.GroupFindGroupResponse;
import com.imageworks.spcue.grpc.job.GroupGetGroupRequest;
import com.imageworks.spcue.grpc.job.GroupGetGroupResponse;
import com.imageworks.spcue.grpc.job.GroupGetGroupsRequest;
import com.imageworks.spcue.grpc.job.GroupGetGroupsResponse;
import com.imageworks.spcue.grpc.job.GroupGetJobsRequest;
import com.imageworks.spcue.grpc.job.GroupGetJobsResponse;
import com.imageworks.spcue.grpc.job.GroupInterfaceGrpc;
import com.imageworks.spcue.grpc.job.GroupReparentGroupsRequest;
import com.imageworks.spcue.grpc.job.GroupReparentGroupsResponse;
import com.imageworks.spcue.grpc.job.GroupReparentJobsRequest;
import com.imageworks.spcue.grpc.job.GroupReparentJobsResponse;
import com.imageworks.spcue.grpc.job.GroupSeq;
import com.imageworks.spcue.grpc.job.GroupSetDefJobMaxCoresRequest;
import com.imageworks.spcue.grpc.job.GroupSetDefJobMaxCoresResponse;
import com.imageworks.spcue.grpc.job.GroupSetDefJobMinCoresRequest;
import com.imageworks.spcue.grpc.job.GroupSetDefJobMinCoresResponse;
import com.imageworks.spcue.grpc.job.GroupSetDefJobPriorityRequest;
import com.imageworks.spcue.grpc.job.GroupSetDefJobPriorityResponse;
import com.imageworks.spcue.grpc.job.GroupSetDeptRequest;
import com.imageworks.spcue.grpc.job.GroupSetDeptResponse;
import com.imageworks.spcue.grpc.job.GroupSetGroupRequest;
import com.imageworks.spcue.grpc.job.GroupSetGroupResponse;
import com.imageworks.spcue.grpc.job.GroupSetMaxCoresRequest;
import com.imageworks.spcue.grpc.job.GroupSetMaxCoresResponse;
import com.imageworks.spcue.grpc.job.GroupSetMinCoresRequest;
import com.imageworks.spcue.grpc.job.GroupSetMinCoresResponse;
import com.imageworks.spcue.grpc.job.GroupSetNameRequest;
import com.imageworks.spcue.grpc.job.GroupSetNameResponse;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.grpc.job.JobSeq;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.Whiteboard;
import com.imageworks.spcue.util.Convert;
import org.springframework.stereotype.Component;

@Component
public class ManageGroup extends GroupInterfaceGrpc.GroupInterfaceImplBase {

    private GroupDao groupDao;
    private JobDao jobDao;
    private GroupManager groupManager;
    private AdminManager adminManager;
    private Whiteboard whiteboard;
    private DispatchQueue manageQueue;

    @Override
    public void getGroup(GroupGetGroupRequest request, StreamObserver<GroupGetGroupResponse> responseObserver) {
        responseObserver.onNext(GroupGetGroupResponse.newBuilder()
                .setGroup(whiteboard.getGroup(request.getId()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void findGroup(GroupFindGroupRequest request, StreamObserver<GroupFindGroupResponse> responseObserver) {
        responseObserver.onNext(GroupFindGroupResponse.newBuilder()
                .setGroup(whiteboard.findGroup(request.getShow(), request.getName()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void reparentGroups(GroupReparentGroupsRequest request,
                               StreamObserver<GroupReparentGroupsResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        GroupSeq groupSeq = request.getGroups();
        List<String> groupIds = new ArrayList<String>(groupSeq.getGroupsCount());
        for (Group g: groupSeq.getGroupsList()) {
            groupIds.add(g.getId());
        }
        groupManager.reparentGroupIds(group, groupIds);
        responseObserver.onNext(GroupReparentGroupsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void reparentJobs(GroupReparentJobsRequest request, StreamObserver<GroupReparentJobsResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        final GroupDetail gDetail = groupDao.getGroupDetail(group.getId());
        for (Job job: request.getJobs().getJobsList()) {
            groupManager.reparentJob(
                    jobDao.getJob(job.getId()),
                    gDetail,
                    new Inherit[] { Inherit.All });
        }
        responseObserver.onNext(GroupReparentJobsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void createSubGroup(GroupCreateSubGroupRequest request, StreamObserver<GroupCreateSubGroupResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        GroupDetail newGroup = new GroupDetail();
        newGroup.name = request.getName();
        newGroup.parentId = group.getId();
        newGroup.showId = group.getShowId();
        groupManager.createGroup(newGroup, group);
        Group subgroup = whiteboard.getGroup(newGroup.id);
        responseObserver.onNext(GroupCreateSubGroupResponse.newBuilder()
                .setGroup(subgroup)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void delete(GroupDeleteRequest request, StreamObserver<GroupDeleteResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        try {
            groupManager.deleteGroup(group);
        } catch (Exception e) {
            responseObserver.onError(Status.INTERNAL
                    .withDescription("Failed to remove group, be sure that there are no " +
                            "jobs or filter actions pointing at the group.")
                    .withCause(e)
                    .asRuntimeException());
        }
        responseObserver.onNext(GroupDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setDefaultJobMaxCores(GroupSetDefJobMaxCoresRequest request,
                                      StreamObserver<GroupSetDefJobMaxCoresResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        groupManager.setGroupDefaultJobMaxCores(group, Convert.coresToWholeCoreUnits(request.getMaxCores()));
        responseObserver.onNext(GroupSetDefJobMaxCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setDefaultJobMinCores(GroupSetDefJobMinCoresRequest request, StreamObserver<GroupSetDefJobMinCoresResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        groupManager.setGroupDefaultJobMinCores(group, Convert.coresToWholeCoreUnits(request.getMinCores()));
        responseObserver.onNext(GroupSetDefJobMinCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setName(GroupSetNameRequest request, StreamObserver<GroupSetNameResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        groupDao.updateName(group, request.getName());
        responseObserver.onNext(GroupSetNameResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setGroup(GroupSetGroupRequest request, StreamObserver<GroupSetGroupResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        GroupInterface parentGroup = groupDao.getGroup(request.getParentGroup().getId());
        groupManager.setGroupParent(group, groupDao.getGroupDetail(parentGroup.getGroupId()));
        responseObserver.onNext(GroupSetGroupResponse.newBuilder().build());
        responseObserver.onCompleted();
    }
    
    @Override
    public void setDefaultJobPriority(GroupSetDefJobPriorityRequest request, StreamObserver<GroupSetDefJobPriorityResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        groupManager.setGroupDefaultJobPriority(group, request.getPriority());
        responseObserver.onNext(GroupSetDefJobPriorityResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getGroups(GroupGetGroupsRequest request, StreamObserver<GroupGetGroupsResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        GroupSeq groupSeq = whiteboard.getGroups(group);
        responseObserver.onNext(GroupGetGroupsResponse.newBuilder()
                .setGroups(groupSeq)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getJobs(GroupGetJobsRequest request, StreamObserver<GroupGetJobsResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        JobSeq jobSeq = whiteboard.getJobs(group);
        responseObserver.onNext(GroupGetJobsResponse.newBuilder()
                .setJobs(jobSeq)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMaxCores(GroupSetMaxCoresRequest request,
                            StreamObserver<GroupSetMaxCoresResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        groupManager.setGroupMaxCores(group,
                Convert.coresToWholeCoreUnits(request.getMaxCores()));
        responseObserver.onNext(GroupSetMaxCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setMinCores(GroupSetMinCoresRequest request,
                            StreamObserver<GroupSetMinCoresResponse> responseObserver) {
        GroupInterface group = getGroupInterface(request.getGroup());
        groupManager.setGroupMinCores(group,
                Convert.coresToWholeCoreUnits(request.getMinCores()));
        responseObserver.onNext(GroupSetMinCoresResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public GroupDao getGroupDao() {
        return groupDao;
    }

    public void setGroupDao(GroupDao groupDao) {
        this.groupDao = groupDao;
    }

    public GroupManager getGroupManager() {
        return groupManager;
    }

    public void setGroupManager(GroupManager groupManager) {
        this.groupManager = groupManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public JobDao getJobDao() {
        return jobDao;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public void setJobDao(JobDao jobDao) {
        this.jobDao = jobDao;
    }

    private GroupInterface getGroupInterface(Group group) {
        return groupDao.getGroup(group.getId());
    }
}

