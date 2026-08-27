
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

import com.imageworks.spcue.HostInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.grpc.rqd.RunFrame;

public interface RqdClient {

    /**
     * Setting to true pretends all remote procedures execute perfectly.
     *
     * @param tests
     */
    public void setTestMode(boolean tests);

    /**
     * Returns a RunningFrameInfo
     *
     * @param proc
     * @return
     */
    RunningFrameInfo getFrameStatus(VirtualProc proc);

    /**
     * Sets the host lock to the provided state.
     *
     * @param host
     * @param lock
     */
    public void setHostLock(HostInterface host, LockState lock);

    /**
     * Locks the host.
     *
     * @param host
     */
    public void lockHost(HostInterface host);

    /**
     * Unlocks the host.
     *
     * @param host
     */
    public void unlockHost(HostInterface host);

    /**
     * Reboots the host now.
     *
     * @param host
     */
    public void rebootNow(HostInterface host);

    /**
     * Reboots the host when idle
     *
     * @param host
     */
    public void rebootWhenIdle(HostInterface host);

    /**
     * Attempts to launch a frame
     *
     * A failure is classified by what it proves about the frame's state: a plain
     * {@link RqdClientException} means RQD rejected the launch or the request was never sent, so
     * the frame is known not to be running; a {@link RqdLaunchUnknownOutcomeException} means the
     * call failed without proving that (deadline, dropped connection), so the frame may be running
     * on the host and the caller must not release the booking without confirming.
     *
     * @param frame
     * @param resource
     * @return RunningFramePrx
     */
    void launchFrame(RunFrame frame, VirtualProc proc);

    /**
     * Kills a running frame by resource
     *
     * Returning normally means the frame is no longer running on the host: either the kill was
     * delivered, or RQD answered NOT_FOUND (it does not track the frame, e.g. after a host
     * restart), which is definitive proof the render is not running there. An
     * {@link RqdClientException} is raised only when the frame's state remains unknown (host
     * unreachable, deadline exceeded, etc.).
     *
     * @param resource
     */
    void killFrame(VirtualProc Proc, String message);

    /**
     * Kills a running frame
     *
     * Same contract as {@link #killFrame(VirtualProc, String)}: NOT_FOUND counts as
     * confirmed-stopped, only an unknown outcome throws.
     *
     * @param hostName
     * @param frameId
     */
    void killFrame(String hostName, String frameId, String message);

    /**
     * Returns whether the given frame is still running on the given host.
     *
     * Used to confirm a frame's render is dead before its frame record is cleared. A {@code false}
     * result means RQD no longer tracks the frame (it has been reaped). A communication failure
     * with the host (i.e. anything other than the frame being absent) is raised as an
     * {@link RqdClientException} so callers can distinguish "confirmed gone" from "could not
     * reach".
     *
     * @param hostName
     * @param frameId
     * @return true if the frame is still running on the host, false if RQD reports it is gone
     */
    boolean isFrameRunning(String hostName, String frameId);
}
