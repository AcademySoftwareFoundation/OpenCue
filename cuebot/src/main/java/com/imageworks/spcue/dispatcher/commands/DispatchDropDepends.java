
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
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.LightweightDependency;
import com.imageworks.spcue.grpc.depend.DependTarget;
import com.imageworks.spcue.service.DependManager;

/**
 * Command for dropping depends off the specified entity.
 *
 * @category command
 */
public class DispatchDropDepends extends KeyRunnable {

    JobInterface job;
    LayerInterface layer;
    FrameInterface frame;

    DependTarget target;
    DependManager dependManager;

    public DispatchDropDepends(JobInterface job, DependTarget target, DependManager dependManager) {
        super("disp_drop_dep_job_" + job.getJobId() + "_" + target.toString());
        this.job = job;
        this.target = target;
        this.dependManager = dependManager;
    }

    public DispatchDropDepends(LayerInterface layer, DependTarget target,
            DependManager dependManager) {
        super("disp_drop_dep_layer_" + layer.getLayerId() + "_" + target.toString());
        this.layer = layer;
        this.target = target;
        this.dependManager = dependManager;
    }

    public DispatchDropDepends(FrameInterface frame, DependTarget target,
            DependManager dependManager) {
        super("disp_drop_dep_frame_" + frame.getFrameId() + "_" + target.toString());
        this.frame = frame;
        this.target = target;
        this.dependManager = dependManager;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                if (job != null) {
                    for (LightweightDependency d : dependManager.getWhatThisDependsOn(job,
                            target)) {
                        dependManager.satisfyDepend(d);
                    }
                } else if (layer != null) {
                    for (LightweightDependency d : dependManager.getWhatThisDependsOn(layer,
                            target)) {
                        dependManager.satisfyDepend(d);
                    }
                } else if (frame != null) {
                    for (LightweightDependency d : dependManager.getWhatThisDependsOn(frame,
                            target)) {
                        dependManager.satisfyDepend(d);
                    }
                }

            }
        }.execute();
    }
}
