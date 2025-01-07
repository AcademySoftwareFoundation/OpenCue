
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

import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.Dispatcher;

/**
 * A command dispatching the next frame in a job.
 *
 * @category command
 */
public class DispatchNextFrame extends KeyRunnable {

    private VirtualProc proc;
    private DispatchJob job;
    private Dispatcher dispatcher;

    public DispatchNextFrame(DispatchJob j, VirtualProc p, Dispatcher d) {
        super("disp_next_frame_" + j.getJobId() + "_" + p.getProcId());
        this.job = j;
        this.proc = p;
        this.dispatcher = d;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                dispatcher.dispatchProcToJob(proc, job);
            }
        }.execute();
    }
}
