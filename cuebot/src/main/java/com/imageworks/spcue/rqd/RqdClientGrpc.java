
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

import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;
import org.apache.log4j.Logger;

import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.google.common.cache.RemovalListener;
import com.google.common.cache.RemovalNotification;
import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.grpc.rqd.RqdInterfaceGrpc;
import com.imageworks.spcue.grpc.rqd.RqdStaticGetRunFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticGetRunFrameResponse;
import com.imageworks.spcue.grpc.rqd.RqdStaticKillRunningFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticLockAllRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticUnlockAllRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticLaunchFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticRebootIdleRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticRebootNowRequest;
import com.imageworks.spcue.grpc.rqd.RunFrame;
import com.imageworks.spcue.grpc.rqd.RunningFrameGrpc;
import com.imageworks.spcue.grpc.rqd.RunningFrameStatusRequest;
import com.imageworks.spcue.grpc.rqd.RunningFrameStatusResponse;

public final class RqdClientGrpc implements RqdClient {
    private static final Logger logger = Logger.getLogger(RqdClientGrpc.class);

    private final int rqdCacheSize;
    private final int rqdCacheExpiration;
    private final int rqdServerPort;
    private LoadingCache<String, ManagedChannel> channelCache;

    private boolean testMode = false;


    public RqdClientGrpc(int rqdServerPort, int rqdCacheSize, int rqdCacheExpiration) {
        this.rqdServerPort = rqdServerPort;
        this.rqdCacheSize = rqdCacheSize;
        this.rqdCacheExpiration = rqdCacheExpiration;
    }

    private void buildChannelCache() {
        this.channelCache = CacheBuilder.newBuilder()
                .maximumSize(rqdCacheSize)
                .expireAfterAccess(rqdCacheExpiration, TimeUnit.MINUTES)
                .removalListener(new RemovalListener<String, ManagedChannel>() {
                    @Override
                    public void onRemoval(RemovalNotification<String, ManagedChannel> removal){
                        ManagedChannel conn = removal.getValue();
                        conn.shutdown();
                    }
                })
                .build(
                        new CacheLoader<String, ManagedChannel>() {
                            @Override
                            public ManagedChannel load(String host) throws Exception {
                                ManagedChannelBuilder channelBuilder = ManagedChannelBuilder.forAddress(
                                        host, rqdServerPort).usePlaintext();
                                return channelBuilder.build();
                            }
                        });
    }

    private RqdInterfaceGrpc.RqdInterfaceBlockingStub getStub(String host) throws ExecutionException {
        if (channelCache == null) {
            buildChannelCache();
        }
        ManagedChannel channel = channelCache.get(host);
        return RqdInterfaceGrpc.newBlockingStub(channel);
    }

    private RunningFrameGrpc.RunningFrameBlockingStub getRunningFrameStub(String host) throws ExecutionException {
        if (channelCache == null) {
            buildChannelCache();
        }
        ManagedChannel channel = channelCache.get(host);
        return RunningFrameGrpc.newBlockingStub(channel);
    }

    public void setHostLock(HostInterface host, LockState lock) {
        if (lock == LockState.OPEN) {
            logger.debug("Unlocking RQD host");
            unlockHost(host);
        } else if (lock == LockState.LOCKED) {
            logger.debug("Locking RQD host");
            lockHost(host);
        } else {
            logger.debug("Unkown LockState passed to setHostLock.");
        }
    }

    public void lockHost(HostInterface host) {
        RqdStaticLockAllRequest request = RqdStaticLockAllRequest.newBuilder().build();

        try {
            getStub(host.getName()).lockAll(request);
        } catch (StatusRuntimeException | ExecutionException e) {
            throw new RqdClientException("failed to lock host: " + host.getName(), e);
        }
    }

    public void unlockHost(HostInterface host) {
        RqdStaticUnlockAllRequest request = RqdStaticUnlockAllRequest.newBuilder().build();

        try {
            getStub(host.getName()).unlockAll(request);
        } catch (StatusRuntimeException | ExecutionException e) {
            throw new RqdClientException("failed to unlock host: " + host.getName(), e);
        }
    }

    public void rebootNow(HostInterface host) {
        RqdStaticRebootNowRequest request = RqdStaticRebootNowRequest.newBuilder().build();

        try {
            getStub(host.getName()).rebootNow(request);
        } catch (StatusRuntimeException | ExecutionException e) {
            throw new RqdClientException("failed to reboot host: " + host.getName(), e);
        }
    }

    public void rebootWhenIdle(HostInterface host) {
        RqdStaticRebootIdleRequest request = RqdStaticRebootIdleRequest.newBuilder().build();

        if (testMode) {
            return;
        }

        try {
            getStub(host.getName()).rebootIdle(request);
        } catch (StatusRuntimeException | ExecutionException e) {
            throw new RqdClientException("failed to reboot host: " + host.getName(), e);
        }
    }

    public void killFrame(VirtualProc proc, String message) {
        killFrame(proc.hostName, proc.frameId, message);
    }

    public void killFrame(String host, String frameId, String message) {
        RqdStaticKillRunningFrameRequest request =
                RqdStaticKillRunningFrameRequest.newBuilder()
                .setFrameId(frameId)
                .setMessage(message)
                .build();

        if (testMode) {
            return;
        }

        try {
            logger.info("killing frame on " + host + ", source: " + message);
            getStub(host).killRunningFrame(request);
        } catch(StatusRuntimeException | ExecutionException e) {
            throw new RqdClientException("failed to kill frame " + frameId, e);
        }
    }

    public RunningFrameInfo getFrameStatus(VirtualProc proc) {
        try {
            RqdStaticGetRunFrameResponse getRunFrameResponse =
                    getStub(proc.hostName)
                            .getRunFrame(
                                    RqdStaticGetRunFrameRequest.newBuilder()
                                            .setFrameId(proc.frameId)
                                            .build());
            RunningFrameStatusResponse frameStatusResponse =
                    getRunningFrameStub(proc.hostName)
                            .status(RunningFrameStatusRequest.newBuilder()
                                    .setRunFrame(getRunFrameResponse.getRunFrame())
                                    .build());
            return frameStatusResponse.getRunningFrameInfo();
        } catch(StatusRuntimeException | ExecutionException e) {
            throw new RqdClientException("failed to obtain status for frame " + proc.frameId, e);
        }
    }

    public void launchFrame(final RunFrame frame, final VirtualProc proc) {
        RqdStaticLaunchFrameRequest request =
                RqdStaticLaunchFrameRequest.newBuilder().setRunFrame(frame).build();

        if (testMode) {
            return;
        }

        try {
            getStub(proc.hostName).launchFrame(request);
        } catch (StatusRuntimeException | ExecutionException e) {
            throw new RqdClientException("failed to launch frame", e);
        }
    }

    @Override
    public void setTestMode(boolean testMode) {
        this.testMode = testMode;
    }
}

