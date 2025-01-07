
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
import com.imageworks.spcue.grpc.job.Order;
import com.imageworks.spcue.service.JobManagerSupport;
import com.imageworks.spcue.util.FrameSet;

public class DispatchReorderFrames extends KeyRunnable {

    private JobInterface job = null;
    private LayerInterface layer = null;
    private FrameSet frameSet;
    private Order order;
    private JobManagerSupport jobManagerSupport;

    public DispatchReorderFrames(JobInterface job, FrameSet frameSet, Order order,
            JobManagerSupport jobManagerSupport) {
        super("disp_reorder_frames_job_" + job.getJobId() + "_" + jobManagerSupport.toString());
        this.job = job;
        this.frameSet = frameSet;
        this.order = order;
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchReorderFrames(LayerInterface layer, FrameSet frameSet, Order order,
            JobManagerSupport jobManagerSupport) {
        super("disp_reorder_frames_layer_" + layer.getLayerId() + "_"
                + jobManagerSupport.toString());
        this.layer = layer;
        this.frameSet = frameSet;
        this.order = order;
        this.jobManagerSupport = jobManagerSupport;
    }

    @Override
    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                if (job != null) {
                    jobManagerSupport.reorderJob(job, frameSet, order);
                } else if (layer != null) {
                    jobManagerSupport.reorderLayer(layer, frameSet, order);
                }
            }
        }.execute();
    }
}
