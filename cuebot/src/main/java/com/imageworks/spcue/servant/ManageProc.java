
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
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;

import com.imageworks.spcue.GroupInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.Source;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.dao.criteria.ProcSearchFactory;
import com.imageworks.spcue.dao.criteria.ProcSearchInterface;
import com.imageworks.spcue.dispatcher.RedirectManager;
import com.imageworks.spcue.grpc.host.Proc;
import com.imageworks.spcue.grpc.host.ProcClearRedirectRequest;
import com.imageworks.spcue.grpc.host.ProcClearRedirectResponse;
import com.imageworks.spcue.grpc.host.ProcGetFrameRequest;
import com.imageworks.spcue.grpc.host.ProcGetFrameResponse;
import com.imageworks.spcue.grpc.host.ProcGetHostRequest;
import com.imageworks.spcue.grpc.host.ProcGetHostResponse;
import com.imageworks.spcue.grpc.host.ProcGetJobRequest;
import com.imageworks.spcue.grpc.host.ProcGetJobResponse;
import com.imageworks.spcue.grpc.host.ProcGetLayerRequest;
import com.imageworks.spcue.grpc.host.ProcGetLayerResponse;
import com.imageworks.spcue.grpc.host.ProcGetProcsRequest;
import com.imageworks.spcue.grpc.host.ProcGetProcsResponse;
import com.imageworks.spcue.grpc.host.ProcInterfaceGrpc;
import com.imageworks.spcue.grpc.host.ProcKillRequest;
import com.imageworks.spcue.grpc.host.ProcKillResponse;
import com.imageworks.spcue.grpc.host.ProcRedirectToGroupRequest;
import com.imageworks.spcue.grpc.host.ProcRedirectToGroupResponse;
import com.imageworks.spcue.grpc.host.ProcRedirectToJobRequest;
import com.imageworks.spcue.grpc.host.ProcRedirectToJobResponse;
import com.imageworks.spcue.grpc.host.ProcUnbookProcsRequest;
import com.imageworks.spcue.grpc.host.ProcUnbookProcsResponse;
import com.imageworks.spcue.grpc.host.ProcUnbookRequest;
import com.imageworks.spcue.grpc.host.ProcUnbookResponse;
import com.imageworks.spcue.grpc.host.ProcUnbookToGroupRequest;
import com.imageworks.spcue.grpc.host.ProcUnbookToGroupResponse;
import com.imageworks.spcue.grpc.host.ProcUnbookToJobRequest;
import com.imageworks.spcue.grpc.host.ProcUnbookToJobResponse;
import com.imageworks.spcue.grpc.job.Frame;
import com.imageworks.spcue.grpc.job.Job;
import com.imageworks.spcue.service.GroupManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.stereotype.Component;

@Component
public class ManageProc extends ProcInterfaceGrpc.ProcInterfaceImplBase {

    @Autowired
    private ProcDao procDao;

    @Autowired
    private Whiteboard whiteboard;

    @Autowired
    private JobManagerSupport jobManagerSupport;

    @Autowired
    private JobManager jobManager;

    @Autowired
    private GroupManager groupManager;

    @Autowired
    private RedirectManager redirectManager;

    @Autowired
    private ProcSearchFactory procSearchFactory;

    @Override
    public void getProcs(ProcGetProcsRequest request, StreamObserver<ProcGetProcsResponse> responseObserver) {
        responseObserver.onNext(ProcGetProcsResponse.newBuilder()
                .setProcs(whiteboard.getProcs(procSearchFactory.create(request.getR())))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void unbookProcs(ProcUnbookProcsRequest request, StreamObserver<ProcUnbookProcsResponse> responseObserver) {
        ProcSearchInterface procSearch = procSearchFactory.create(request.getR());
        procSearch.sortByBookedTime();
        responseObserver.onNext(ProcUnbookProcsResponse.newBuilder()
                .setNumProcs(
                        jobManagerSupport.unbookProcs(
                                procSearch, request.getKill(), new Source(request.toString())))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void unbookToGroup(ProcUnbookToGroupRequest request, StreamObserver<ProcUnbookToGroupResponse> responseObserver) {
        if (request.getR().getMaxResultsCount() == 0) {
            throw new RuntimeException(
                    "You must specify the number of procs to unbook " +
                            "within the ProcSearchCriteria.");
        }

        GroupInterface g = groupManager.getGroup(request.getGroup().getId());
        List<VirtualProc> procs = redirectManager.addRedirect(request.getR(),
                g, request.getKill(), new Source(request.toString()));
        responseObserver.onNext(ProcUnbookToGroupResponse.newBuilder()
                .setNumProcs(procs.size())
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void unbookToJob(ProcUnbookToJobRequest request, StreamObserver<ProcUnbookToJobResponse> responseObserver) {
        if (request.getR().getMaxResultsCount() == 0) {
            throw new RuntimeException(
                    "You must specify the number of procs to unbook " +
                            "within the ProcSearchCriteria.");
        }

        List<JobInterface> jobs = new ArrayList<JobInterface>(request.getJobs().getJobsCount());

        for (Job job: request.getJobs().getJobsList()) {
            try {
                jobs.add(jobManager.getJob(job.getId()));
            }
            catch (EmptyResultDataAccessException e) {
                // just eat it, just eat it.
                // Open up your mouth and feed it.
                // Have a banana. Have a whole bunch.
                // It doesn't matter, when you had lunch.
                // just eat it, just eat it
                // get yourself and egg and beat it
            }
        }

        int returnVal;
        if (jobs.size() == 0) {
            returnVal = 0;
        } else {
            List<VirtualProc> procs = redirectManager.addRedirect(request.getR(),
                    jobs, request.getKill(), new Source(request.toString()));

            returnVal = procs.size();
        }
        responseObserver.onNext(ProcUnbookToJobResponse.newBuilder()
                .setNumProcs(returnVal)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getFrame(ProcGetFrameRequest request, StreamObserver<ProcGetFrameResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        Frame frame = whiteboard.getFrame(procDao.getCurrentFrameId(proc));
        ProcGetFrameResponse response = ProcGetFrameResponse.newBuilder()
                .setFrame(frame)
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getHost(ProcGetHostRequest request, StreamObserver<ProcGetHostResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        ProcGetHostResponse response = ProcGetHostResponse.newBuilder()
                .setHost(whiteboard.getHost(proc.getHostId()))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getJob(ProcGetJobRequest request, StreamObserver<ProcGetJobResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        ProcGetJobResponse response = ProcGetJobResponse.newBuilder()
                .setJob(whiteboard.getJob(procDao.getCurrentJobId(proc)))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void getLayer(ProcGetLayerRequest request, StreamObserver<ProcGetLayerResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        ProcGetLayerResponse response = ProcGetLayerResponse.newBuilder()
                .setLayer(whiteboard.getLayer(procDao.getCurrentLayerId(proc)))
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void kill(ProcKillRequest request, StreamObserver<ProcKillResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        String message = "Kill Proc on " + proc.getProcId();
        jobManagerSupport.unbookProc(procDao.getVirtualProc(proc.getProcId()),
                true, new Source(message));
        responseObserver.onNext(ProcKillResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void unbook(ProcUnbookRequest request, StreamObserver<ProcUnbookResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        procDao.unbookProc(proc);
        if (request.getKill()) {
            String message = "Kill Proc on " + proc.getProcId();
            jobManagerSupport.unbookProc(procDao.getVirtualProc(proc.getProcId()),
                    true, new Source(message));
        }
        responseObserver.onNext(ProcUnbookResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void redirectToGroup(ProcRedirectToGroupRequest request,
                                StreamObserver<ProcRedirectToGroupResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        VirtualProc p = procDao.getVirtualProc(proc.getId());
        GroupInterface g = groupManager.getGroup(request.getGroupId());
        String message = "redirectToGroup called on " + proc.getProcId() + " with Group " + g.getGroupId();
        boolean value = redirectManager.addRedirect(p, g, request.getKill(), new Source(message));
        responseObserver.onNext(ProcRedirectToGroupResponse.newBuilder().setValue(value).build());
        responseObserver.onCompleted();
    }

    @Override
    public void redirectToJob(ProcRedirectToJobRequest request,
                              StreamObserver<ProcRedirectToJobResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        VirtualProc p = procDao.getVirtualProc(proc.getId());
        JobInterface j = jobManager.getJob(request.getJobId());
        String message = "redirectToJob called on " + proc.getProcId() + " with Job " + j.getJobId();
        boolean value = redirectManager.addRedirect(p, j, request.getKill(), new Source(message));
        responseObserver.onNext(ProcRedirectToJobResponse.newBuilder().setValue(value).build());
        responseObserver.onCompleted();
    }

    @Override
    public void clearRedirect(ProcClearRedirectRequest request,
                              StreamObserver<ProcClearRedirectResponse> responseObserver) {
        VirtualProc proc = getVirtualProc(request.getProc());
        procDao.setUnbookState(proc, false);
        boolean value = redirectManager.removeRedirect(proc);
        responseObserver.onNext(ProcClearRedirectResponse.newBuilder().setValue(value).build());
        responseObserver.onCompleted();
    }

    public ProcDao getProcDao() {
        return procDao;
    }

    public void setProcDao(ProcDao procDao) {
        this.procDao = procDao;
    }

    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public JobManagerSupport getJobManagerSupport() {
        return jobManagerSupport;
    }

    public void setJobManagerSupport(JobManagerSupport jobManagerSupport) {
        this.jobManagerSupport = jobManagerSupport;
    }

    public JobManager getJobManager() {
        return jobManager;
    }

    public void setJobManager(JobManager jobManager) {
        this.jobManager = jobManager;
    }

    public GroupManager getGroupManager() {
        return groupManager;
    }

    public void setGroupManager(GroupManager groupManager) {
        this.groupManager = groupManager;
    }

    public RedirectManager getRedirectManager() {
        return redirectManager;
    }

    public void setRedirectManager(RedirectManager redirectManager) {
        this.redirectManager = redirectManager;
    }

    private VirtualProc getVirtualProc(Proc proc) {
        return procDao.getVirtualProc(proc.getId());
    }

    public ProcSearchFactory getProcSearchFactory() {
        return procSearchFactory;
    }

    public void setProcSearchFactory(ProcSearchFactory procSearchFactory) {
        this.procSearchFactory = procSearchFactory;
    }
}

