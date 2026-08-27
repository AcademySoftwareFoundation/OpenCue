
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

package com.imageworks.spcue.rqd;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;

import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.Status;
import io.grpc.StatusRuntimeException;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

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
import com.imageworks.spcue.grpc.rqd.RqdStaticGetRunningFrameStatusRequest;
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
    private static final Logger logger = LogManager.getLogger(RqdClientGrpc.class);

    private final int rqdCacheSize;
    private final int rqdCacheExpiration;
    private final int rqdCacheConcurrency;
    private final int rqdServerPort;
    private final int rqdTaskDeadlineSeconds;
    private LoadingCache<String, ManagedChannel> channelCache;

    private boolean testMode = false;

    public RqdClientGrpc(int rqdServerPort, int rqdCacheSize, int rqdCacheExpiration,
            int rqdCacheConcurrency, int rqdTaskDeadline) {
        this.rqdServerPort = rqdServerPort;
        this.rqdCacheSize = rqdCacheSize;
        this.rqdCacheExpiration = rqdCacheExpiration;
        this.rqdCacheConcurrency = rqdCacheConcurrency;
        this.rqdTaskDeadlineSeconds = rqdTaskDeadline;
    }

    private void buildChannelCache() {
        this.channelCache = CacheBuilder.newBuilder().maximumSize(rqdCacheSize)
                .concurrencyLevel(rqdCacheConcurrency)
                .expireAfterAccess(rqdCacheExpiration, TimeUnit.MINUTES)
                .removalListener(new RemovalListener<String, ManagedChannel>() {
                    @Override
                    public void onRemoval(RemovalNotification<String, ManagedChannel> removal) {
                        ManagedChannel conn = removal.getValue();
                        conn.shutdown();
                    }
                }).build(new CacheLoader<String, ManagedChannel>() {
                    @Override
                    public ManagedChannel load(String host) throws Exception {
                        ManagedChannelBuilder<?> channelBuilder = ManagedChannelBuilder
                                .forAddress(host, rqdServerPort).usePlaintext();
                        return channelBuilder.build();
                    }
                });
    }

    private RqdInterfaceGrpc.RqdInterfaceBlockingStub getStub(String host)
            throws ExecutionException {
        if (channelCache == null) {
            buildChannelCache();
        }
        ManagedChannel channel = channelCache.get(host);
        return RqdInterfaceGrpc.newBlockingStub(channel).withDeadlineAfter(rqdTaskDeadlineSeconds,
                TimeUnit.SECONDS);
    }

    private RunningFrameGrpc.RunningFrameBlockingStub getRunningFrameStub(String host)
            throws ExecutionException {
        if (channelCache == null) {
            buildChannelCache();
        }
        ManagedChannel channel = channelCache.get(host);
        return RunningFrameGrpc.newBlockingStub(channel).withDeadlineAfter(rqdTaskDeadlineSeconds,
                TimeUnit.SECONDS);
    }

    public void setHostLock(HostInterface host, LockState lock) {
        if (lock == LockState.OPEN) {
            logger.debug("Unlocking RQD host");
            unlockHost(host);
        } else if (lock == LockState.LOCKED) {
            logger.debug("Locking RQD host");
            lockHost(host);
        } else {
            logger.debug("Unknown LockState passed to setHostLock.");
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
        RqdStaticKillRunningFrameRequest request = RqdStaticKillRunningFrameRequest.newBuilder()
                .setFrameId(frameId).setMessage(message).build();

        if (testMode) {
            return;
        }

        try {
            logger.info("killing frame on " + host + ", source: " + message);
            getStub(host).killRunningFrame(request);
        } catch (StatusRuntimeException e) {
            // RQD returns NOT_FOUND when the frame is not in its cache (already reaped, or the
            // host restarted since the frame was dispatched): the render is confirmed not running
            // there, which is the state the kill was meant to reach. Treat it as success so
            // callers do not mistake the strongest possible "not running" proof for a failed
            // kill (and, e.g., defer releasing a provably dead frame).
            if (e.getStatus().getCode() == Status.Code.NOT_FOUND) {
                logger.info("frame " + frameId + " is not running on " + host
                        + " (NOT_FOUND), nothing to kill");
                return;
            }
            throw new RqdClientException("failed to kill frame " + frameId, e);
        } catch (ExecutionException e) {
            throw new RqdClientException("failed to kill frame " + frameId, e);
        }
    }

    public boolean isFrameRunning(String host, String frameId) {
        if (testMode) {
            return false;
        }

        try {
            getStub(host).getRunningFrameStatus(
                    RqdStaticGetRunningFrameStatusRequest.newBuilder().setFrameId(frameId).build());
            return true;
        } catch (StatusRuntimeException e) {
            // RQD returns NOT_FOUND once it has reaped the frame: the render is confirmed gone.
            if (e.getStatus().getCode() == Status.Code.NOT_FOUND) {
                return false;
            }
            // Any other failure (host unreachable, deadline, etc.) leaves the frame's state
            // unknown; surface it so callers do not treat "could not reach" as "confirmed gone".
            throw new RqdClientException("failed to obtain status for frame " + frameId, e);
        } catch (ExecutionException e) {
            throw new RqdClientException("failed to obtain status for frame " + frameId, e);
        }
    }

    public RunningFrameInfo getFrameStatus(VirtualProc proc) {
        try {
            RqdStaticGetRunFrameResponse getRunFrameResponse = getStub(proc.hostName).getRunFrame(
                    RqdStaticGetRunFrameRequest.newBuilder().setFrameId(proc.frameId).build());
            RunningFrameStatusResponse frameStatusResponse =
                    getRunningFrameStub(proc.hostName).status(RunningFrameStatusRequest.newBuilder()
                            .setRunFrame(getRunFrameResponse.getRunFrame()).build());
            return frameStatusResponse.getRunningFrameInfo();
        } catch (StatusRuntimeException | ExecutionException e) {
            throw new RqdClientException("failed to obtain status for frame " + proc.frameId, e);
        }
    }

    /**
     * Status codes for which a failed launch call does not prove RQD never started the frame:
     * transport-level failures where the request may have been delivered and only the response was
     * lost (or never produced in time).
     *
     * Every other code is a response from the server's application layer, which means the launch
     * was processed and refused before any render was spawned. The two implementations report that
     * differently: the Rust RQD maps its launch errors to ABORTED, FAILED_PRECONDITION or
     * INVALID_ARGUMENT ({@code FrameManagerError} in rust/crates/rqd/src/frame/manager.rs), while
     * the Python RQD's servicer sets no status code, so the exception it raises surfaces as UNKNOWN
     * (rqd/rqd/rqdservicers.py). Both raise only before spawning, which is what makes "rejected"
     * equivalent to "not running" here.
     *
     * One refusal inverts that: RQD rejects a launch for a frame it is already running (Python
     * DuplicateFrameViolationException, Rust {@code FrameManagerError::AlreadyExist}), which proves
     * the frame IS rendering on that host. It still lands in the rejected branch, so the caller's
     * rollback releases the booking and kills the render. That kill goes to a host that just
     * answered, so it lands and cannot double-book -- the cost is a wasted render, not a second
     * booking.
     */
    private static final Set<Status.Code> LAUNCH_OUTCOME_UNKNOWN_CODES = Collections
            .unmodifiableSet(EnumSet.of(Status.Code.DEADLINE_EXCEEDED, Status.Code.UNAVAILABLE,
                    Status.Code.CANCELLED, Status.Code.INTERNAL, Status.Code.DATA_LOSS));

    public void launchFrame(final RunFrame frame, final VirtualProc proc) {
        RqdStaticLaunchFrameRequest request =
                RqdStaticLaunchFrameRequest.newBuilder().setRunFrame(frame).build();

        if (testMode) {
            return;
        }

        try {
            getStub(proc.hostName).launchFrame(request);
        } catch (StatusRuntimeException e) {
            if (LAUNCH_OUTCOME_UNKNOWN_CODES.contains(e.getStatus().getCode())) {
                throw new RqdLaunchUnknownOutcomeException(
                        "failed to launch frame " + frame.getFrameId() + " on " + proc.hostName
                                + ", outcome unknown: the frame may be running",
                        e);
            }
            throw new RqdClientException("failed to launch frame", e);
        } catch (ExecutionException e) {
            // The channel could not even be created; the request was never sent.
            throw new RqdClientException("failed to launch frame", e);
        }
    }

    @Override
    public void setTestMode(boolean testMode) {
        this.testMode = testMode;
    }

    public void shutdown() {
        if (channelCache != null) {
            logger.info("Shutting down RqdClientGrpc channel cache");
            channelCache.invalidateAll();
        }
    }
}
