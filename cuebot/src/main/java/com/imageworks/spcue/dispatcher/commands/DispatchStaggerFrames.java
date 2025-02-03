
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

import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.service.JobManagerSupport;

public class DispatchStaggerFrames extends KeyRunnable {

    private JobInterface job = null;
    private LayerInterface layer = null;
    private String range;
    private int stagger;
    private JobManagerSupport jobManagerSupport;

    public DispatchStaggerFrames(JobInterface job, String range, int stagger,
            JobManagerSupport jobManagerSupport) {
        super("disp_stag_frames_" + job.getJobId() + "_" + range);
        this.job = job;
        this.range = range;
        this.stagger = stagger;
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchStaggerFrames(LayerInterface layer, String range, int stagger,
            JobManagerSupport jobManagerSupport) {
        super("disp_stag_frames_" + layer.getLayerId() + "_" + range);
        this.layer = layer;
        this.range = range;
        this.stagger = stagger;
        this.jobManagerSupport = jobManagerSupport;
    }

    @Override
    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                if (job != null) {
                    jobManagerSupport.staggerJob(job, range, stagger);
                } else if (layer != null) {
                    jobManagerSupport.staggerJob(layer, range, stagger);
                }
            }
        }.execute();
    }
}
