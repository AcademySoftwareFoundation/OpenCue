
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

import java.sql.Timestamp;
import java.util.Optional;

import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.job.FrameState;

public class DispatchFrame extends FrameEntity implements FrameInterface {

    public int retries;
    public FrameState state;

    // ts_updated of the frame as read by the dispatch query, i.e. when it last
    // entered WAITING. Used to compute time-to-book at booking. Every query
    // feeding DISPATCH_FRAME_MAPPER MUST select ts_updated: the mapper reads the
    // column unconditionally, so omitting it throws SQLException and breaks
    // dispatch entirely (it does not silently leave this null).
    public Timestamp dateUpdated;

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

    // Memory requirement for this frame in Kb
    private long minMemory;

    // Soft limit to be enforced for this frame in Kb
    public long softMemoryLimit;

    // Hard limit to be enforced for this frame in Kb
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
