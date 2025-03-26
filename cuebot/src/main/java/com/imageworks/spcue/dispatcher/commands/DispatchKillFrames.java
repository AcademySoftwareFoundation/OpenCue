
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

import com.imageworks.spcue.Source;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.service.JobManagerSupport;

/**
 * A command for killing a list of frames
 *
 * @category command
 */
public class DispatchKillFrames extends KeyRunnable {

    private FrameSearchInterface search;
    private JobManagerSupport jobManagerSupport;
    private Source source;

    public DispatchKillFrames(FrameSearchInterface search, Source source,
            JobManagerSupport jobManagerSupport) {
        super("disp_kill_frames_" + source.toString() + "_" + jobManagerSupport.hashCode());
        this.search = search;
        this.source = source;
        this.jobManagerSupport = jobManagerSupport;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                jobManagerSupport.killProcs(search, source, true);
            }
        }.execute();
    }
}
