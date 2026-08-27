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

/**
 * A frame launch RPC failed in a way that does not prove RQD never started the frame: the request
 * may have been delivered and the render may be running even though the call failed on this side
 * (deadline expired waiting for the response, connection dropped mid-call, etc).
 *
 * Callers must not assume the frame is not running. Releasing the booking without confirming the
 * frame's state re-queues a frame that may already be rendering, double-booking it onto a second
 * host. A plain {@link RqdClientException} from a launch, by contrast, means RQD answered and
 * rejected the launch (or the request was provably never sent), so that launch started nothing. The
 * one rejection that does not mean the frame is idle is RQD refusing a frame it is already running;
 * see the launch classification in {@link RqdClientGrpc} for why that case is safe to roll back
 * anyway.
 */
@SuppressWarnings("serial")
public class RqdLaunchUnknownOutcomeException extends RqdClientException {

    public RqdLaunchUnknownOutcomeException(String message, Throwable cause) {
        super(message, cause);
    }
}
