
/*
 * Copyright Contributors to the OpenCue Project
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



package com.imageworks.spcue.dispatcher.commands;

import org.apache.log4j.Logger;

import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdClientException;

public class DispatchRqdKillFrame implements Runnable {

    private static final Logger logger = Logger.getLogger(DispatchRqdKillFrame.class);

    private VirtualProc proc = null;
    private String message;

    private String hostname;
    private String frameId;

    private final RqdClient rqdClient;

    public DispatchRqdKillFrame(String hostname, String frameId, String message, RqdClient rqdClient) {
        this.hostname = hostname;
        this.frameId = frameId;
        this.message = message;
        this.rqdClient = rqdClient;
    }

    public DispatchRqdKillFrame(VirtualProc proc, String message, RqdClient rqdClient) {
        this.proc = proc;
        this.hostname = proc.hostName;
        this.message = message;
        this.rqdClient = rqdClient;
    }

    @Override
    public void run() {
        long startTime = System.currentTimeMillis();
        try {
            if (proc != null) {
                rqdClient.killFrame(proc, message);
            }
            else {
                rqdClient.killFrame(hostname, frameId, message);
            }
        } catch (RqdClientException e) {
            logger.info("Failed to contact host " + hostname + ", " + e);
        }
        finally {
            long elapsedTime =  System.currentTimeMillis() - startTime;
            logger.info("RQD communication with " + hostname +
                    " took " + elapsedTime + "ms");
        }
    }
}

