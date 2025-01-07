
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

package com.imageworks.spcue.dispatcher.commands;

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.DispatchSupport;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

/**
 * A runnable to communicate with rqd requesting for a frame to be killed due to memory issues.
 * <p>
 * Before killing a frame, the database is updated to mark the frame status as
 * EXIT_STATUS_MEMORY_FAILURE, this allows the FrameCompleteHandler to possibly retry the frame
 * after increasing its memory requirements
 */
public class DispatchRqdKillFrameMemory extends KeyRunnable {

    private static final Logger logger = LogManager.getLogger(DispatchRqdKillFrameMemory.class);

    private String message;
    private String hostname;
    private DispatchSupport dispatchSupport;
    private final RqdClient rqdClient;
    private final boolean isTestMode;

    private FrameInterface frame;

    public DispatchRqdKillFrameMemory(String hostname, FrameInterface frame, String message,
            RqdClient rqdClient, DispatchSupport dispatchSupport, boolean isTestMode) {
        super("disp_rqd_kill_frame_" + frame.getFrameId() + "_" + rqdClient.toString());
        this.frame = frame;
        this.hostname = hostname;
        this.message = message;
        this.rqdClient = rqdClient;
        this.dispatchSupport = dispatchSupport;
        this.isTestMode = isTestMode;
    }

    @Override
    public void run() {
        long startTime = System.currentTimeMillis();
        try {
            if (dispatchSupport.updateFrameMemoryError(frame) && !isTestMode) {
                rqdClient.killFrame(hostname, frame.getFrameId(), message);
            } else {
                logger.warn("Could not update frame " + frame.getFrameId()
                        + " status to EXIT_STATUS_MEMORY_FAILURE. Canceling kill request!");
            }
        } catch (RqdClientException e) {
            logger.warn("Failed to contact host " + hostname + ", " + e);
        } finally {
            long elapsedTime = System.currentTimeMillis() - startTime;
            logger.info("RQD communication with " + hostname + " took " + elapsedTime + "ms");
        }
    }
}
