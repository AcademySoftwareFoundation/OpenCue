
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

import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.CommentDetail;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.HostDao;
import com.imageworks.spcue.dao.criteria.HostSearchFactory;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.grpc.comment.Comment;
import com.imageworks.spcue.grpc.comment.CommentSeq;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.HostAddCommentRequest;
import com.imageworks.spcue.grpc.host.HostAddCommentResponse;
import com.imageworks.spcue.grpc.host.HostAddTagsRequest;
import com.imageworks.spcue.grpc.host.HostAddTagsResponse;
import com.imageworks.spcue.grpc.host.HostDeleteRequest;
import com.imageworks.spcue.grpc.host.HostDeleteResponse;
import com.imageworks.spcue.grpc.host.HostFindHostRequest;
import com.imageworks.spcue.grpc.host.HostFindHostResponse;
import com.imageworks.spcue.grpc.host.HostGetCommentsRequest;
import com.imageworks.spcue.grpc.host.HostGetCommentsResponse;
import com.imageworks.spcue.grpc.host.HostGetDeedRequest;
import com.imageworks.spcue.grpc.host.HostGetDeedResponse;
import com.imageworks.spcue.grpc.host.HostGetHostRequest;
import com.imageworks.spcue.grpc.host.HostGetHostResponse;
import com.imageworks.spcue.grpc.host.HostGetHostWhiteboardRequest;
import com.imageworks.spcue.grpc.host.HostGetHostWhiteboardResponse;
import com.imageworks.spcue.grpc.host.HostGetHostsRequest;
import com.imageworks.spcue.grpc.host.HostGetHostsResponse;
import com.imageworks.spcue.grpc.host.HostGetOwnerRequest;
import com.imageworks.spcue.grpc.host.HostGetOwnerResponse;
import com.imageworks.spcue.grpc.host.HostGetProcsRequest;
import com.imageworks.spcue.grpc.host.HostGetProcsResponse;
import com.imageworks.spcue.grpc.host.HostGetRenderPartitionsRequest;
import com.imageworks.spcue.grpc.host.HostGetRenderPartitionsResponse;
import com.imageworks.spcue.grpc.host.HostInterfaceGrpc;
import com.imageworks.spcue.grpc.host.HostLockRequest;
import com.imageworks.spcue.grpc.host.HostLockResponse;
import com.imageworks.spcue.grpc.host.HostRebootRequest;
import com.imageworks.spcue.grpc.host.HostRebootResponse;
import com.imageworks.spcue.grpc.host.HostRebootWhenIdleRequest;
import com.imageworks.spcue.grpc.host.HostRebootWhenIdleResponse;
import com.imageworks.spcue.grpc.host.HostRedirectToJobRequest;
import com.imageworks.spcue.grpc.host.HostRedirectToJobResponse;
import com.imageworks.spcue.grpc.host.HostRemoveTagsRequest;
import com.imageworks.spcue.grpc.host.HostRemoveTagsResponse;
import com.imageworks.spcue.grpc.host.HostRenameTagRequest;
import com.imageworks.spcue.grpc.host.HostRenameTagResponse;
import com.imageworks.spcue.grpc.host.HostSetAllocationRequest;
import com.imageworks.spcue.grpc.host.HostSetAllocationResponse;
import com.imageworks.spcue.grpc.host.HostSetHardwareStateRequest;
import com.imageworks.spcue.grpc.host.HostSetHardwareStateResponse;
import com.imageworks.spcue.grpc.host.HostSetOsRequest;
import com.imageworks.spcue.grpc.host.HostSetOsResponse;
import com.imageworks.spcue.grpc.host.HostSetThreadModeRequest;
import com.imageworks.spcue.grpc.host.HostSetThreadModeResponse;
import com.imageworks.spcue.grpc.host.HostUnlockRequest;
import com.imageworks.spcue.grpc.host.HostUnlockResponse;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.host.ProcSeq;
import com.imageworks.spcue.service.AdminManager;
import com.imageworks.spcue.service.CommentManager;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.stereotype.Component;

@Component
public class ManageHost extends HostInterfaceGrpc.HostInterfaceImplBase {

    private HostManager hostManager;
    private HostDao hostDao;
    private AdminManager adminManager;
    private CommentManager commentManager;
    private RedirectManager redirectManager;
    private JobManager jobManager;
    private Whiteboard whiteboard;
    private HostSearchFactory hostSearchFactory;

    @Override
    public void getHosts(HostGetHostsRequest request, StreamObserver<HostGetHostsResponse> responseObserver) {
        responseObserver.onNext(HostGetHostsResponse.newBuilder()
                .setHosts(whiteboard.getHosts(hostSearchFactory.create(request.getR())))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getHostWhiteboard(HostGetHostWhiteboardRequest request,
                                  StreamObserver<HostGetHostWhiteboardResponse> responseObserver) {
        responseObserver.onNext(HostGetHostWhiteboardResponse.newBuilder()
                .setNestedHosts(whiteboard.getHostWhiteboard())
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void findHost(HostFindHostRequest request,
                                  StreamObserver<HostFindHostResponse> responseObserver) {
        responseObserver.onNext(HostFindHostResponse.newBuilder()
                .setHost(whiteboard.findHost(request.getName()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getHost(HostGetHostRequest request,
                         StreamObserver<HostGetHostResponse> responseObserver) {
        responseObserver.onNext(HostGetHostResponse.newBuilder()
                .setHost(whiteboard.findHost(request.getId()))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void lock(HostLockRequest request, StreamObserver<HostLockResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.setHostLock(host, LockState.LOCKED, new Source(request.toString()));
        responseObserver.onNext(HostLockResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void unlock(HostUnlockRequest request, StreamObserver<HostUnlockResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.setHostLock(host, LockState.OPEN, new Source(request.toString()));
        responseObserver.onNext(HostUnlockResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void rebootWhenIdle(HostRebootWhenIdleRequest request,
                               StreamObserver<HostRebootWhenIdleResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.rebootWhenIdle(host);
        responseObserver.onNext(HostRebootWhenIdleResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void delete(HostDeleteRequest request, StreamObserver<HostDeleteResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.deleteHost(host);
        responseObserver.onNext(HostDeleteResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void reboot(HostRebootRequest request, StreamObserver<HostRebootResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.rebootNow(host);
        responseObserver.onNext(HostRebootResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setAllocation(HostSetAllocationRequest request,
                              StreamObserver<HostSetAllocationResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.setAllocation(host,
                adminManager.getAllocationDetail(request.getAllocationId()));
        responseObserver.onNext(HostSetAllocationResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void addTags(HostAddTagsRequest request, StreamObserver<HostAddTagsResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.addTags(host, request.getTagsList().toArray(new String[0]));
        responseObserver.onNext(HostAddTagsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void removeTags(HostRemoveTagsRequest request, StreamObserver<HostRemoveTagsResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.removeTags(host, request.getTagsList().toArray(new String[0]));
        responseObserver.onNext(HostRemoveTagsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void renameTag(HostRenameTagRequest request, StreamObserver<HostRenameTagResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostManager.renameTag(host, request.getOldTag(), request.getNewTag());
        responseObserver.onNext(HostRenameTagResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void addComment(HostAddCommentRequest request, StreamObserver<HostAddCommentResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        CommentDetail c = new CommentDetail();
        Comment newComment = request.getNewComment();
        c.message = newComment.getMessage();
        c.subject = newComment.getSubject();
        c.user = newComment.getUser();
        c.timestamp = null;
        commentManager.addComment(host, c);
        responseObserver.onNext(HostAddCommentResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getComments(HostGetCommentsRequest request, StreamObserver<HostGetCommentsResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        CommentSeq commentSeq = whiteboard.getComments(host);
        responseObserver.onNext(HostGetCommentsResponse.newBuilder()
                .setComments(commentSeq)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getProcs(HostGetProcsRequest request, StreamObserver<HostGetProcsResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        ProcSeq procs = whiteboard.getProcs(host);
        responseObserver.onNext(HostGetProcsResponse.newBuilder()
                .setProcs(procs)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void setThreadMode(HostSetThreadModeRequest request, StreamObserver<HostSetThreadModeResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostDao.updateThreadMode(host, request.getMode());
        responseObserver.onNext(HostSetThreadModeResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void setHardwareState(HostSetHardwareStateRequest request, StreamObserver<HostSetHardwareStateResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostDao.updateHostState(host, request.getState());
        responseObserver.onNext(HostSetHardwareStateResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void getOwner(HostGetOwnerRequest request, StreamObserver<HostGetOwnerResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        responseObserver.onNext(HostGetOwnerResponse.newBuilder()
                .setOwner(whiteboard.getOwner(host))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getDeed(HostGetDeedRequest request, StreamObserver<HostGetDeedResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        responseObserver.onNext(HostGetDeedResponse.newBuilder()
                .setDeed(whiteboard.getDeed(host))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getRenderPartitions(HostGetRenderPartitionsRequest request,
                                    StreamObserver<HostGetRenderPartitionsResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        responseObserver.onNext(HostGetRenderPartitionsResponse.newBuilder()
                .setRenderPartitions(whiteboard.getRenderPartitions(host))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void redirectToJob(HostRedirectToJobRequest request, StreamObserver<HostRedirectToJobResponse> responseObserver) {

        List<VirtualProc> virtualProcs = new ArrayList<>();
        for (String procName: request.getProcNamesList()) {
            virtualProcs.add(hostManager.getVirtualProc(procName));
        }
        boolean value = redirectManager.addRedirect(virtualProcs,
                jobManager.getJob(request.getJobId()),
                new Source(request.toString()));
        responseObserver.onNext(HostRedirectToJobResponse.newBuilder()
                .setValue(value)
                .build());
        responseObserver.onCompleted();
    }


    @Override
    public void setOs(HostSetOsRequest request, StreamObserver<HostSetOsResponse> responseObserver) {
        HostInterface host = getHostInterface(request.getHost());
        hostDao.updateHostOs(host, request.getOs());
        responseObserver.onNext(HostSetOsResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public HostManager getHostManager() {
        return hostManager;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public AdminManager getAdminManager() {
        return adminManager;
    }

    public void setAdminManager(AdminManager adminManager) {
        this.adminManager = adminManager;
    }

    public CommentManager getCommentManager() {
        return commentManager;
    }

    public void setCommentManager(CommentManager commentManager) {
        this.commentManager = commentManager;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public HostDao getHostDao() {
        return hostDao;
    }

    public void setHostDao(HostDao hostDao) {
        this.hostDao = hostDao;
    }

    public RedirectManager getRedirectManager() {
        return redirectManager;
    }

    public void setRedirectManager(RedirectManager redirectManager) {
        this.redirectManager = redirectManager;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public HostSearchFactory getHostSearchFactory() {
        return hostSearchFactory;
    }

    public void setHostSearchFactory(HostSearchFactory hostSearchFactory) {
        this.hostSearchFactory = hostSearchFactory;
    }

    private HostInterface getHostInterface(Host host) {
        return hostManager.getHost(host.getId());
    }
}

