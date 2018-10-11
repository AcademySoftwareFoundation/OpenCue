
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

import com.imageworks.spcue.*;
import com.imageworks.spcue.dao.criteria.*;
import com.imageworks.spcue.dispatcher.*;
import com.imageworks.spcue.grpc.cue.*;
import com.imageworks.spcue.grpc.job.JobSearchCriteria;
import com.imageworks.spcue.grpc.cue.SystemStats;
import com.imageworks.spcue.service.*;
import io.grpc.stub.StreamObserver;

import java.util.ArrayList;
import java.util.List;

public class CueStatic extends CueInterfaceGrpc.CueInterfaceImplBase {

    private Whiteboard whiteboard;
    private DispatchQueue manageQueue;
    private DispatchQueue dispatchQueue;
    private HostReportQueue reportQueue;
    private BookingQueue bookingQueue;
    private DispatchSupport dispatchSupport;
    private JobLauncher jobLauncher;

    @Override
    public void launchSpecAndWait(CueLaunchSpecAndWaitRequest request,
                    StreamObserver<CueLaunchSpecAndWaitResponse> responseObserver) {
        JobSpec spec = jobLauncher.parse(request.getSpec());
        jobLauncher.launch(spec);
        JobSearchCriteria r = JobSearch.criteriaFactory();
        JobSearchCriteria.Builder builder = r.toBuilder();
        for (BuildableJob job: spec.getJobs()) {
            builder.addIds((job.detail.id)).build();
        }
        r = builder.build();
        responseObserver.onNext(CueLaunchSpecAndWaitResponse.newBuilder()
                .setJobs(whiteboard.getJobs(new JobSearch(r)))
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void launchSpec(CueLaunchSpecRequest request, StreamObserver<CueLaunchSpecResponse> responseObserver) {
        JobSpec spec = jobLauncher.parse(request.getSpec());
        List<String> result = new ArrayList<String>(8);
        for (BuildableJob j: spec.getJobs()) {
            result.add(j.detail.name);
        }
        jobLauncher.queueAndLaunch(spec);
        responseObserver.onNext(CueLaunchSpecResponse.newBuilder()
                .addAllNames(result)
                .build());
        responseObserver.onCompleted();
    }

    @Override
    public void getSystemStats(CueGetSystemStatsRequest request,
                               StreamObserver<CueGetSystemStatsResponse> responseObserver) {
        SystemStats stats = SystemStats.newBuilder()
                .setDispatchThreads(dispatchQueue.getActiveThreadCount())
                .setDispatchWaiting(dispatchQueue.getWaitingCount())
                .setDispatchRemainingCapacity(dispatchQueue.getRemainingCapacity())
                .setDispatchExecuted(dispatchQueue.getTotalDispatched())
                .setDispatchRejected(dispatchQueue.getTotalRejected())

                .setManageThreads(manageQueue.getActiveThreadCount())
                .setManageWaiting(manageQueue.getWaitingCount())
                .setManageRemainingCapacity(manageQueue.getRemainingCapacity())
                .setManageExecuted(manageQueue.getTotalDispatched())
                .setManageRejected(manageQueue.getTotalRejected())

                .setReportThreads(reportQueue.getActiveCount())
                .setReportWaiting(reportQueue.getQueue().size())
                .setReportRemainingCapacity(reportQueue.getQueue().remainingCapacity())
                .setReportExecuted(reportQueue.getTaskCount())
                .setReportRejected(reportQueue.getRejectedTaskCount())

                .setBookingWaiting(bookingQueue.getQueue().size())
                .setBookingRemainingCapacity(bookingQueue.getQueue().remainingCapacity())
                .setBookingThreads(bookingQueue.getActiveCount())
                .setBookingExecuted(bookingQueue.getCompletedTaskCount())
                .setBookingRejected(bookingQueue.getRejectedTaskCount())
                .setBookingSleepMillis(bookingQueue.sleepTime())

                .setHostBalanceSuccess(DispatchSupport.balanceSuccess.get())
                .setHostBalanceFailed(DispatchSupport.balanceFailed.get())
                .setKilledOffenderProcs(DispatchSupport.killedOffenderProcs.get())
                .setKilledOomProcs(DispatchSupport.killedOomProcs.get())
                .setClearedProcs(DispatchSupport.clearedProcs.get())
                .setBookingRetries(DispatchSupport.bookingRetries.get())
                .setBookingErrors(DispatchSupport.bookingErrors.get())
                .setBookedProcs( DispatchSupport.bookedProcs.get())

                // TODO: (gdenton) reimplement these with gRPC
//                .setReqForData(IceServer.dataRequests.get())
//                .setReqForFunction(IceServer.rpcRequests.get())
//                .setReqErrors(IceServer.errors.get())

                .setUnbookedProcs(DispatchSupport.unbookedProcs.get())
                .setPickedUpCores(DispatchSupport.pickedUpCoresCount.get())
                .setStrandedCores(DispatchSupport.strandedCoresCount.get())
                .build();
        responseObserver.onNext(CueGetSystemStatsResponse.newBuilder()
                .setStats(stats)
                .build());
        responseObserver.onCompleted();
    }


    public Whiteboard getWhiteboard() {
        return whiteboard;
    }

    public void setWhiteboard(Whiteboard whiteboard) {
        this.whiteboard = whiteboard;
    }

    public DispatchQueue getManageQueue() {
        return manageQueue;
    }

    public void setManageQueue(DispatchQueue manageQueue) {
        this.manageQueue = manageQueue;
    }

    public DispatchQueue getDispatchQueue() {
        return dispatchQueue;
    }

    public void setDispatchQueue(DispatchQueue dispatchQueue) {
        this.dispatchQueue = dispatchQueue;
    }

    public HostReportQueue getReportQueue() {
        return reportQueue;
    }

    public void setReportQueue(HostReportQueue reportQueue) {
        this.reportQueue = reportQueue;
    }

    public BookingQueue getBookingQueue() {
        return bookingQueue;
    }

    public void setBookingQueue(BookingQueue bookingQueue) {
        this.bookingQueue = bookingQueue;
    }

    public DispatchSupport getDispatchSupport() {
        return dispatchSupport;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public JobLauncher getJobLauncher() {
        return jobLauncher;
    }

    public void setJobLauncher(JobLauncher jobLauncher) {
        this.jobLauncher = jobLauncher;
    }
}

