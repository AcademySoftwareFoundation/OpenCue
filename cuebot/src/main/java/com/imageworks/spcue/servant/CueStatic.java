
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License
 * is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
 * or implied. See the License for the specific language governing permissions and limitations under
 * the License.
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

public class CueStatic extends CueInterfaceGrpc.CueInterfaceImplBase {

    private Whiteboard whiteboard;
    private DispatchQueue manageQueue;
    private DispatchQueue dispatchQueue;
    private HostReportQueue reportQueue;
    private BookingQueue bookingQueue;
    private DispatchSupport dispatchSupport;

    @Override
    public void getSystemStats(CueGetSystemStatsRequest request,
            StreamObserver<CueGetSystemStatsResponse> responseObserver) {
        SystemStats stats = SystemStats.newBuilder()
                .setDispatchThreads(dispatchQueue.getActiveCount())
                .setDispatchWaiting(dispatchQueue.getSize())
                .setDispatchRemainingCapacity(dispatchQueue.getRemainingCapacity())
                .setDispatchExecuted(dispatchQueue.getCompletedTaskCount())
                .setDispatchRejected(dispatchQueue.getRejectedTaskCount())

                .setManageThreads(manageQueue.getActiveCount())
                .setManageWaiting(manageQueue.getSize())
                .setManageRemainingCapacity(manageQueue.getRemainingCapacity())
                .setManageExecuted(manageQueue.getCompletedTaskCount())
                .setManageRejected(manageQueue.getRejectedTaskCount())

                .setReportThreads(reportQueue.getActiveCount())
                .setReportWaiting(reportQueue.getQueue().size())
                .setReportRemainingCapacity(reportQueue.getQueue().remainingCapacity())
                .setReportExecuted(reportQueue.getTaskCount())
                .setReportRejected(reportQueue.getRejectedTaskCount())

                .setBookingWaiting(bookingQueue.getSize())
                .setBookingRemainingCapacity(bookingQueue.getRemainingCapacity())
                .setBookingThreads(bookingQueue.getActiveCount())
                .setBookingExecuted(bookingQueue.getCompletedTaskCount())
                .setBookingRejected(bookingQueue.getRejectedTaskCount()).setBookingSleepMillis(0)

                .setHostBalanceSuccess(DispatchSupport.balanceSuccess.get())
                .setHostBalanceFailed(DispatchSupport.balanceFailed.get())
                .setKilledOffenderProcs(DispatchSupport.killedOffenderProcs.get())
                .setKilledOomProcs(DispatchSupport.killedOomProcs.get())
                .setClearedProcs(DispatchSupport.clearedProcs.get())
                .setBookingRetries(DispatchSupport.bookingRetries.get())
                .setBookingErrors(DispatchSupport.bookingErrors.get())
                .setBookedProcs(DispatchSupport.bookedProcs.get())

                // TODO(gregdenton) Reimplement these with gRPC. (Issue #69)
                // .setReqForData(IceServer.dataRequests.get())
                // .setReqForFunction(IceServer.rpcRequests.get())
                // .setReqErrors(IceServer.errors.get())

                .setUnbookedProcs(DispatchSupport.unbookedProcs.get())
                .setPickedUpCores(DispatchSupport.pickedUpCoresCount.get())
                .setStrandedCores(DispatchSupport.strandedCoresCount.get()).build();
        responseObserver.onNext(CueGetSystemStatsResponse.newBuilder().setStats(stats).build());
        responseObserver.onCompleted();
    }

    public boolean isDispatchQueueHealthy() {
        return this.dispatchQueue.isHealthy();
    }

    public boolean isManageQueueHealthy() {
        return this.manageQueue.isHealthy();
    }

    public boolean isReportQueueHealthy() {
        return this.reportQueue.isHealthy();
    }

    public boolean isBookingQueueHealthy() {
        return this.bookingQueue.isHealthy();
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
}
