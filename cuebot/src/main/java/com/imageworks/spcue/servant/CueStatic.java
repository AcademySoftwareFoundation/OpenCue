
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

import com.imageworks.spcue.dispatcher.BookingQueue;
import com.imageworks.spcue.dispatcher.DispatchQueue;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.dispatcher.HostReportQueue;
import com.imageworks.spcue.grpc.cue.CueGetSystemStatsRequest;
import com.imageworks.spcue.grpc.cue.CueGetSystemStatsResponse;
import com.imageworks.spcue.grpc.cue.CueInterfaceGrpc;
import com.imageworks.spcue.grpc.cue.SystemStats;
import com.imageworks.spcue.service.Whiteboard;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

@Component
public class CueStatic extends CueInterfaceGrpc.CueInterfaceImplBase {

    @Autowired
    private Whiteboard whiteboard;

    @Autowired
    private DispatchQueue manageQueue;

    @Autowired
    private DispatchQueue dispatchQueue;

    @Autowired
    private HostReportQueue reportQueue;

    @Autowired
    private BookingQueue bookingQueue;

    @Autowired
    private DispatchSupport dispatchSupport;

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

                // TODO(gregdenton) Reimplement these with gRPC. (Issue #69)
                //  .setReqForData(IceServer.dataRequests.get())
                //  .setReqForFunction(IceServer.rpcRequests.get())
                //  .setReqErrors(IceServer.errors.get())

                .setUnbookedProcs(DispatchSupport.unbookedProcs.get())
                .setPickedUpCores(DispatchSupport.pickedUpCoresCount.get())
                .setStrandedCores(DispatchSupport.strandedCoresCount.get())
                .build();
        responseObserver.onNext(CueGetSystemStatsResponse.newBuilder()
                .setStats(stats)
                .build());
        responseObserver.onCompleted();
    }
}

