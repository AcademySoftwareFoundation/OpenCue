
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

package com.imageworks.spcue;

import java.util.Optional;

import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.job.FrameState;

public class DispatchFrame extends FrameEntity implements FrameInterface {

    public int retries;
    public FrameState state;

    public String show;
    public String shot;
    public String owner;
    public Optional<Integer> uid;
    public String logDir;
    public String command;
    public String range;
    public int chunkSize;

    public String layerName;
    public String jobName;

    public int minCores;
    public int maxCores;
    public boolean threadable;
    public int minGpus;
    public int maxGpus;
    public long minGpuMemory;

    // A comma separated list of services
    public String services;

    // The Operational System this frame is expected to run in
    public String os;

    // Memory requirement for this frame in bytes
    private long minMemory;

    // Soft limit to be enforced for this frame in bytes
    public long softMemoryLimit;

    // Hard limit to be enforced for this frame in bytes
    public long hardMemoryLimit;

    public void setMinMemory(long minMemory) {
        this.minMemory = minMemory;
        this.softMemoryLimit = (long) (((double) minMemory) * Dispatcher.SOFT_MEMORY_MULTIPLIER);
        this.hardMemoryLimit = (long) (((double) minMemory) * Dispatcher.HARD_MEMORY_MULTIPLIER);
    }

    public long getMinMemory() {
        return this.minMemory;
    }

    // Parameters to tell rqd whether or not to use Loki for frame logs and which base url to use
    public String lokiURL;
}
