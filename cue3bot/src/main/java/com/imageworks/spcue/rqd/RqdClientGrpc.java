
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

package com.imageworks.spcue.rqd;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;
import org.apache.log4j.Logger;

import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.grpc.rqd.RqdInterfaceGrpc;
import com.imageworks.spcue.grpc.rqd.RqdStaticGetRunFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticGetRunFrameResponse;
import com.imageworks.spcue.grpc.rqd.RqdStaticKillRunningFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticLaunchFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticRebootIdleRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticRebootNowRequest;
import com.imageworks.spcue.grpc.rqd.RunFrame;
import com.imageworks.spcue.grpc.rqd.RunningFrameGrpc;
import com.imageworks.spcue.grpc.rqd.RunningFrameStatusRequest;
import com.imageworks.spcue.grpc.rqd.RunningFrameStatusResponse;

public final class RqdClientGrpc implements RqdClient {
    private static final Logger logger = Logger.getLogger(RqdClientGrpc.class);

    private final int rqdServerPort;

    private boolean testMode = false;

    public RqdClientGrpc(int rqdServerPort) {
        this.rqdServerPort = rqdServerPort;
    }

    private RqdInterfaceGrpc.RqdInterfaceBlockingStub getStub(String host) {
        ManagedChannelBuilder channelBuilder = ManagedChannelBuilder.forAddress(host, rqdServerPort).usePlaintext();
        ManagedChannel channel = channelBuilder.build();
        return RqdInterfaceGrpc.newBlockingStub(channel);
    }

    private RunningFrameGrpc.RunningFrameBlockingStub getRunningFrameStub(String host) {
        ManagedChannelBuilder channelBuilder = ManagedChannelBuilder.forAddress(host, rqdServerPort).usePlaintext();
        ManagedChannel channel = channelBuilder.build();
        return RunningFrameGrpc.newBlockingStub(channel);
    }

    public void rebootNow(HostInterface host) {
        if (testMode) {
            return;
        }

        try {
            getStub(host.getName()).rebootNow(RqdStaticRebootNowRequest.newBuilder().build());
        } catch (StatusRuntimeException e) {
            throw new RqdClientException("failed to reboot host: " + host.getName(), e);
        }
    }

    public void rebootWhenIdle(HostInterface host) {
        if (testMode) {
            return;
        }

        try {
            getStub(host.getName()).rebootIdle(RqdStaticRebootIdleRequest.newBuilder().build());
        } catch (StatusRuntimeException e) {
            throw new RqdClientException("failed to reboot host: " + host.getName(),e);
        }
    }

    public void killFrame(VirtualProc proc, String message) {
        killFrame(proc.hostName, proc.frameId, message);
    }

    public void killFrame(String host, String frameId, String message) {
        if (testMode) {
            return;
        }

        try {
            logger.info("killing frame on " + host + ", source: " + message);
            getStub(host).killRunningFrame(RqdStaticKillRunningFrameRequest.newBuilder().setFrameId(frameId).build());
        } catch(StatusRuntimeException e) {
            throw new RqdClientException("failed to kill frame " + frameId + ", " + e);
        }
    }

    public RunningFrameInfo getFrameStatus(VirtualProc proc) {
        try {
            RqdStaticGetRunFrameResponse getRunFrameResponse = getStub(proc.hostName).getRunFrame(RqdStaticGetRunFrameRequest.newBuilder().setFrameId(proc.frameId).build());
            RunningFrameStatusResponse frameStatusResponse = getRunningFrameStub(proc.hostName).status(RunningFrameStatusRequest.newBuilder().setRunFrame(getRunFrameResponse.getRunFrame()).build());
            return frameStatusResponse.getRunningFrameInfo();
        } catch(StatusRuntimeException e) {
            throw new RqdClientException("failed to obtain status for frame " + proc.frameId);
        }
    }

    public void launchFrame(final RunFrame frame, final VirtualProc proc) {
        if (testMode) {
            return;
        }
        try {
            getStub(proc.hostName).launchFrame(RqdStaticLaunchFrameRequest.newBuilder().setRunFrame(frame).build());
        } catch (StatusRuntimeException e) {
            throw new RqdClientException("RQD comm error" + e,e);
        }
    }

    @Override
    public void setTestMode(boolean tests) {
        this.testMode = tests;
    }
}

