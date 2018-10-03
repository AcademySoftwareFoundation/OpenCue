

package com.imageworks.spcue.servant;

import org.apache.log4j.Logger;
import io.grpc.stub.StreamObserver;


import com.imageworks.spcue.CueGrpc.RqdReportStaticGrpc;
import com.imageworks.spcue.CueGrpc.Empty;
import com.imageworks.spcue.CueGrpc.BootReport;
import com.imageworks.spcue.CueGrpc.HostReport;
import com.imageworks.spcue.CueGrpc.FrameCompleteReport;

import com.imageworks.spcue.dispatcher.FrameCompleteHandler;
import com.imageworks.spcue.dispatcher.HostReportHandler;


public class RqdReportStatic extends RqdReportStaticGrpc.RqdReportStaticImplBase {

    private FrameCompleteHandler frameCompleteHandler;
    private HostReportHandler hostReportHandler;

    @SuppressWarnings("unused")

    public RqdReportStatic() {  }

    @Override
    public void reportRqdStartup(final BootReport report, StreamObserver<Empty> responseObserver) {
        hostReportHandler.queueBootReport(report);
    }

    @Override
    public void reportRunningFrameCompletion(final FrameCompleteReport report, StreamObserver<Empty> responseObserver) {
        frameCompleteHandler.handleFrameCompleteReport(report);
    }

    @Override
    public void reportStatus(final HostReport report, StreamObserver<Empty> responseObserver) {
        hostReportHandler.queueHostReport(report);
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
