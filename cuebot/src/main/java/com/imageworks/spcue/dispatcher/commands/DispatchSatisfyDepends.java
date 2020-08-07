
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

import com.imageworks.spcue.FrameInterface;
import com.imageworks.spcue.JobInterface;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.dao.criteria.FrameSearchInterface;
import com.imageworks.spcue.service.JobManagerSupport;

/**
 * A command to satisfy any type of dependencies.
 *
 * @category command
 */
public class DispatchSatisfyDepends implements Runnable {

    private JobInterface job = null;
    private LayerInterface layer = null;
    private FrameInterface frame = null;
    private FrameSearchInterface search;
    private JobManagerSupport jobManagerSupport;

    public DispatchSatisfyDepends(JobInterface job, JobManagerSupport jobManagerSupport) {
        this.job = job;
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchSatisfyDepends(LayerInterface layer, JobManagerSupport jobManagerSupport) {
        this.layer = layer;
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchSatisfyDepends(FrameInterface frame, JobManagerSupport jobManagerSupport) {
        this.frame = frame;
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchSatisfyDepends(FrameSearchInterface search, JobManagerSupport jobManagerSupport) {
        this.search = search;
        this.jobManagerSupport = jobManagerSupport;
    }

    public void run() {
        new DispatchCommandTemplate() {
            public void wrapDispatchCommand() {
                if (search != null) {
                    jobManagerSupport.satisfyWhatDependsOn(search);
                } else if (frame != null) {
                    jobManagerSupport.satisfyWhatDependsOn(frame);
                } else if (layer != null) {
                    jobManagerSupport.satisfyWhatDependsOn(layer);
                } else {
                    jobManagerSupport.satisfyWhatDependsOn(job);
                }
            }
        }.execute();
    }
}

