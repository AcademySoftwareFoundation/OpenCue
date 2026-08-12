
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

import com.imageworks.spcue.grpc.rqd.RqdInterfaceGrpc;
import com.imageworks.spcue.grpc.rqd.RqdStaticKillRunningFrameRequest;
import com.imageworks.spcue.grpc.rqd.RqdStaticKillRunningFrameResponse;
import com.imageworks.spcue.rqd.RqdClientException;
import com.imageworks.spcue.rqd.RqdClientGrpc;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

/**
 * Tests for {@link RqdClientGrpc#killFrame} status handling, exercised against a real gRPC server
 * on an ephemeral localhost port so the actual status-code classification runs. RQD answers
 * NOT_FOUND when it does not track the frame (already reaped, or the host restarted since
 * dispatch): that is definitive proof the render is not running, so the kill must report success
 * rather than an error -- otherwise callers like lostProc defer releasing a provably dead frame.
 */
public class RqdClientGrpcTests {

    private Server server;
    private RqdClientGrpc client;

    /** Status the fake RQD responds to kills with; null means a normal successful kill. */
    private volatile Status killResponseStatus = null;
    private volatile String lastKillFrameId = null;

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
}
