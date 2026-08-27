
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

package com.imageworks.spcue.test.rqd;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.rqd.RqdInterfaceGrpc;
import com.imageworks.spcue.grpc.rqd.RqdStaticKillRunningFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticKillRunningFrameResponse;
import com.imageworks.spcue.grpc.rqd.RqdStaticLaunchFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticLaunchFrameResponse;
import com.imageworks.spcue.grpc.rqd.RunFrame;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.rqd.RqdClientGrpc;
import com.imageworks.spcue.rqd.RqdLaunchUnknownOutcomeException;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.fail;

/**
 * Tests for {@link RqdClientGrpc#killFrame} and {@link RqdClientGrpc#launchFrame} status handling,
 * exercised against a real gRPC server on an ephemeral localhost port so the actual status-code
 * classification runs. RQD answers NOT_FOUND when it does not track the frame (already reaped, or
 * the host restarted since dispatch): that is definitive proof the render is not running, so the
 * kill must report success rather than an error -- otherwise callers like lostProc defer releasing
 * a provably dead frame. A launch failure, conversely, must distinguish RQD rejecting the launch
 * (frame known not running) from a transport failure where the frame may be running.
 */
public class RqdClientGrpcTests {

    private Server server;
    private RqdClientGrpc client;

    /** Status the fake RQD responds to kills with; null means a normal successful kill. */
    private volatile Status killResponseStatus = null;
    private volatile String lastKillFrameId = null;

    /** Status the fake RQD responds to launches with; null means a normal successful launch. */
    private volatile Status launchResponseStatus = null;
    /** Delay before the fake RQD answers a launch, to force DEADLINE_EXCEEDED on the client. */
    private volatile long launchDelayMs = 0;

    private class FakeRqdServant extends RqdInterfaceGrpc.RqdInterfaceImplBase {
        @Override
        public void killRunningFrame(RqdStaticKillRunningFrameRequest request,
                StreamObserver<RqdStaticKillRunningFrameResponse> responseObserver) {
            lastKillFrameId = request.getFrameId();
            if (killResponseStatus == null) {
                responseObserver.onNext(RqdStaticKillRunningFrameResponse.newBuilder().build());
                responseObserver.onCompleted();
            } else {
                responseObserver.onError(killResponseStatus.asRuntimeException());
            }
        }

        @Override
        public void launchFrame(RqdStaticLaunchFrameRequest request,
                StreamObserver<RqdStaticLaunchFrameResponse> responseObserver) {
            if (launchDelayMs > 0) {
                try {
                    Thread.sleep(launchDelayMs);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
            if (launchResponseStatus == null) {
                responseObserver.onNext(RqdStaticLaunchFrameResponse.newBuilder().build());
                responseObserver.onCompleted();
            } else {
                responseObserver.onError(launchResponseStatus.asRuntimeException());
            }
        }
    }

    @Before
    public void setup() throws Exception {
        server = ServerBuilder.forPort(0).addService(new FakeRqdServant()).build().start();
        client = new RqdClientGrpc(server.getPort(), 10, 5, 1, 5);
    }

    @After
    public void teardown() {
        client.shutdown();
        server.shutdownNow();
    }

    @Test
    public void killFrameSucceedsWhenRqdKillsTheFrame() {
        client.killFrame("localhost", "frame-id", "test kill");

        assertEquals("frame-id", lastKillFrameId);
    }

    @Test
    public void killFrameTreatsNotFoundAsConfirmedStopped() {
        killResponseStatus = Status.NOT_FOUND;

        // Must not throw: the frame is confirmed not running on the host.
        client.killFrame("localhost", "frame-id", "test kill");

        assertEquals("frame-id", lastKillFrameId);
    }

    @Test
    public void killFrameThrowsWhenOutcomeUnknown() {
        killResponseStatus = Status.UNAVAILABLE;

        try {
            client.killFrame("localhost", "frame-id", "test kill");
            fail("expected RqdClientException for an unknown kill outcome");
        } catch (RqdClientException expected) {
            // The frame's state is unknown; callers must not treat this as confirmed-stopped.
        }
    }

    private VirtualProc launchProc() {
        VirtualProc proc = new VirtualProc();
        proc.hostName = "localhost";
        proc.frameId = "frame-id";
        return proc;
    }

    @Test
    public void launchFrameSucceeds() {
        client.launchFrame(RunFrame.newBuilder().setFrameId("frame-id").build(), launchProc());
    }

    @Test
    public void launchFrameThrowsPlainExceptionWhenRqdRejectsTheLaunch() {
        // RQD rejects launches with ABORTED (nimby locked, reservation failed): the frame is
        // proven not running and the caller may release the booking immediately.
        launchResponseStatus = Status.ABORTED;

        try {
            client.launchFrame(RunFrame.newBuilder().setFrameId("frame-id").build(), launchProc());
            fail("expected RqdClientException for a rejected launch");
        } catch (RqdClientException e) {
            assertFalse(
                    "a launch rejection proves the frame is not running and must not be "
                            + "classified as unknown-outcome",
                    e instanceof RqdLaunchUnknownOutcomeException);
        }
    }

    @Test
    public void launchFrameThrowsUnknownOutcomeOnTransportFailure() {
        launchResponseStatus = Status.UNAVAILABLE;

        try {
            client.launchFrame(RunFrame.newBuilder().setFrameId("frame-id").build(), launchProc());
            fail("expected RqdLaunchUnknownOutcomeException for a transport failure");
        } catch (RqdLaunchUnknownOutcomeException expected) {
            // The request may have been delivered; the frame may be running.
        }
    }

    @Test
    public void launchFrameThrowsUnknownOutcomeWhenDeadlineExpires() {
        // A 1 second task deadline against a server that answers in 2: the request was delivered
        // (and the frame may be spawning) but the response never arrives in time.
        RqdClientGrpc slowClient = new RqdClientGrpc(server.getPort(), 10, 5, 1, 1);
        launchDelayMs = 2000;

        try {
            slowClient.launchFrame(RunFrame.newBuilder().setFrameId("frame-id").build(),
                    launchProc());
            fail("expected RqdLaunchUnknownOutcomeException when the deadline expires");
        } catch (RqdLaunchUnknownOutcomeException expected) {
            // The frame may be running on the host even though the call failed here.
        } finally {
            slowClient.shutdown();
        }
    }
}
