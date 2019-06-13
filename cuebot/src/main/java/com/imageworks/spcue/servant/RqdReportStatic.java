

package com.imageworks.spcue.servant;

import io.grpc.stub.StreamObserver;

import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.HostReportHandler;
import com.imageworks.spcue.grpc.report.RqdReportInterfaceGrpc;
import com.imageworks.spcue.grpc.report.RqdReportRqdStartupRequest;
import com.imageworks.spcue.grpc.report.RqdReportRqdStartupResponse;
import com.imageworks.spcue.grpc.report.RqdReportRunningFrameCompletionRequest;
import com.imageworks.spcue.grpc.report.RqdReportRunningFrameCompletionResponse;
import com.imageworks.spcue.grpc.report.RqdReportStatusRequest;
import com.imageworks.spcue.grpc.report.RqdReportStatusResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;


@Component
public class RqdReportStatic extends RqdReportInterfaceGrpc.RqdReportInterfaceImplBase {

    @Autowired
    private FrameCompleteHandler frameCompleteHandler;

    @Autowired
    private HostReportHandler hostReportHandler;

    @SuppressWarnings("unused")

    @Override
    public void reportRqdStartup(RqdReportRqdStartupRequest request,
                                 StreamObserver<RqdReportRqdStartupResponse> responseObserver) {
        hostReportHandler.queueBootReport(request.getBootReport());
        responseObserver.onNext(RqdReportRqdStartupResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void reportRunningFrameCompletion(RqdReportRunningFrameCompletionRequest request,
                                             StreamObserver<RqdReportRunningFrameCompletionResponse> responseObserver) {
        frameCompleteHandler.handleFrameCompleteReport(request.getFrameCompleteReport());
        responseObserver.onNext(RqdReportRunningFrameCompletionResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    @Override
    public void reportStatus(RqdReportStatusRequest request, StreamObserver<RqdReportStatusResponse> responseObserver) {
        hostReportHandler.queueHostReport(request.getHostReport());
        responseObserver.onNext(RqdReportStatusResponse.newBuilder().build());
        responseObserver.onCompleted();
    }

    public FrameCompleteHandler getFrameCompleteHandler() {
        return frameCompleteHandler;
    }

    public void setFrameCompleteHandler(FrameCompleteHandler frameCompleteHandler) {
        this.frameCompleteHandler = frameCompleteHandler;
    }

    public HostReportHandler getHostReportHandler() {
        return hostReportHandler;
    }

    public void setHostReportHandler(HostReportHandler hostReportHandler) {
        this.hostReportHandler = hostReportHandler;
    }
}
