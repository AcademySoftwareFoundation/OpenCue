
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



package com.imageworks.spcue;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import com.imageworks.spcue.grpc.job.LayerType;

public class LayerDetail extends LayerEntity implements LayerInterface {
    public String command;
    public String range;
    public LayerType type;
    public int minimumCores;
    public int maximumCores;
    public int minimumGpu;
    public int maximumGpu;
    public boolean isThreadable;
    public long minimumMemory;
    public long minimumGpuMemory;
    public int chunkSize;
    public int dispatchOrder;
    public int totalFrameCount;

    public Set<String> tags = new LinkedHashSet<String>();
    public Set<String> services = new LinkedHashSet<String>();
    public Set<String> limits = new LinkedHashSet<String>();

    /*
     *
     */
    public List<String> getServices() {
        return new ArrayList<String>(services);
    }

    public String getCommand() {
        return command;
    }

    public void setCommand(String command) {
        this.command = command;
    }

    public String getRange() {
        return range;
    }

    public void setRange(String range) {
        this.range = range;
    }

    public LayerType getType() {
        return type;
    }

    public void setType(LayerType type) {
        this.type = type;
    }

    public int getMinimumCores() {
        return minimumCores;
    }

    public void setMinimumCores(int minimumCores) {
        this.minimumCores = minimumCores;
    }

    public int getMinimumGpu() {
        return minimumGpu;
    }

    public void setMinimumGpu(int minimumGpu) {
        this.minimumGpu = minimumGpu;
    }

    public boolean isThreadable() {
        return isThreadable;
    }

    public void setThreadable(boolean isThreadable) {
        this.isThreadable = isThreadable;
    }

    public long getMinimumMemory() {
        return minimumMemory;
    }

    public void setMinimumMemory(long minimumMemory) {
        this.minimumMemory = minimumMemory;
    }

    public long getMinimumGpuMemory() {
        return minimumGpuMemory;
    }

    public void setMinimumGpuMemory(long minimumGpuMemory) {
        this.minimumGpuMemory = minimumGpuMemory;
    }

    public int getChunkSize() {
        return chunkSize;
    }

    public void setChunkSize(int chunkSize) {
        this.chunkSize = chunkSize;
    }

    public int getDispatchOrder() {
        return dispatchOrder;
    }

    public void setDispatchOrder(int dispatchOrder) {
        this.dispatchOrder = dispatchOrder;
    }

    public int getTotalFrameCount() {
        return totalFrameCount;
    }

    public void setTotalFrameCount(int totalFrameCount) {
        this.totalFrameCount = totalFrameCount;
    }

    public Set<String> getTags() {
        return tags;
    }

    public void setTags(Set<String> tags) {
        this.tags = tags;
    }
}

