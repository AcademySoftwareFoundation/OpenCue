
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



package com.imageworks.spcue.dispatcher.commands;

import com.imageworks.spcue.Frame;
import com.imageworks.spcue.Job;
import com.imageworks.spcue.Layer;
import com.imageworks.spcue.dao.criteria.FrameSearch;
import com.imageworks.spcue.service.JobManagerSupport;

/**
 * A command to satisfy any type of dependencies.
 *
 * @category command
 */
public class DispatchSatisfyDepends implements Runnable {

    private Job job = null;
    private Layer layer = null;
    private Frame frame = null;
    private FrameSearch search;
    private JobManagerSupport jobManagerSupport;

    public DispatchSatisfyDepends(Job job, JobManagerSupport jobManagerSupport) {
        this.job = job;
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchSatisfyDepends(Layer layer, JobManagerSupport jobManagerSupport) {
        this.layer = layer;
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchSatisfyDepends(Frame frame, JobManagerSupport jobManagerSupport) {
        this.frame = frame;
        this.jobManagerSupport = jobManagerSupport;
    }

    public DispatchSatisfyDepends(FrameSearch search, JobManagerSupport jobManagerSupport) {
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

