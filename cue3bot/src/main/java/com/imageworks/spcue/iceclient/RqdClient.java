
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



package com.imageworks.spcue.iceclient;

import com.imageworks.spcue.RqdIce.RunFrame;
import com.imageworks.spcue.Host;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.RqdIce.RunningFrameInfo;

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
     * Reboots the host now.
     *
     * @param host
     */
    public void rebootNow(Host host);

    /**
     * Reboots the host when idle
     *
     * @param host
     */
    public void rebootWhenIdle(Host host);

    /**
     * Attempts to launch a frame
     *
     * @param frame
     * @param resource
     * @return RunningFramePrx
     */
    void launchFrame(RunFrame frame, VirtualProc proc);

    /**
     * Kills a running frame by resource
     *
     * @param resource
     */
    void killFrame(VirtualProc Proc, String message);

    /**
     * Kills a running frame
     *
     * @param hostName
     * @param frameId
     */
    void killFrame(String hostName, String frameId, String message);
}

