
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

import com.imageworks.spcue.dispatcher.ResourceContainer;
import com.imageworks.spcue.grpc.renderpartition.RenderPartitionType;

/**
 * Contains information about local desktop cores a user has
 * assigned to the given job.
 *
 * The local-only option, if true, means the job will only dispatch
 * a user's local cores.  If false, the job will dispatch cores from
 * both the user's machine and the render farm.
 */
public class LocalHostAssignment extends Entity
    implements ResourceContainer {

    private int idleCoreUnits;
    private long idleMemory;
    private int idleGpuUnits;
    private long idleGpuMemory;

    private long maxMemory;
    private long maxGpuMemory;
    private int maxCoreUnits;
    private int maxGpuUnits;

    private int threads;

    private String hostId;
    private String jobId = null;
    private String layerId = null;
    private String frameId = null;

    private RenderPartitionType type;

    public LocalHostAssignment() { }

    public LocalHostAssignment(int maxCores, int threads, long maxMemory, int maxGpus, long maxGpuMemory) {
        this.maxCoreUnits = maxCores;
        this.threads = threads;
        this.maxMemory = maxMemory;
        this.maxGpuUnits = maxGpus;
        this.maxGpuMemory = maxGpuMemory;
    }

    @Override
    public boolean hasAdditionalResources(int minCores, long minMemory, int minGpus, long minGpuMemory) {

        if (idleCoreUnits < minCores) {
            return false;
        }
        else if (idleMemory <  minMemory) {
            return false;
        }
        else if (idleGpuUnits < minGpus) {
            return false;
        }
        else if (idleGpuMemory <  minGpuMemory) {
            return false;
        }

        return true;
    }

    @Override
    public void useResources(int coreUnits, long memory, int gpuUnits, long gpuMemory) {
        idleCoreUnits = idleCoreUnits - coreUnits;
        idleMemory = idleMemory - memory;
        idleGpuUnits = idleGpuUnits - gpuUnits;
        idleGpuMemory = idleGpuMemory - gpuMemory;
    }

    public int getThreads() {
        return threads;
    }

    public void setThreads(int threads) {
        this.threads = threads;
    }

    public long getMaxMemory() {
        return maxMemory;
    }

    public void setMaxMemory(long maxMemory) {
        this.maxMemory = maxMemory;
    }

    public int getMaxCoreUnits() {
        return maxCoreUnits;
    }

    public void setMaxCoreUnits(int maxCoreUnits) {
        this.maxCoreUnits = maxCoreUnits;
    }

    public long getIdleMemory() {
        return this.idleMemory;
    }

    public int getMaxGpuUnits() {
        return maxGpuUnits;
    }

    public void setMaxGpuUnits(int maxGpuUnits) {
        this.maxGpuUnits = maxGpuUnits;
    }

    public long getMaxGpuMemory() {
        return maxGpuMemory;
    }

    public void setMaxGpuMemory(long maxGpuMemory) {
        this.maxGpuMemory = maxGpuMemory;
    }

    public long getIdleGpuMemory() {
        return this.idleGpuMemory;
    }

    public int getIdleCoreUnits() {
        return this.idleCoreUnits;
    }

    public void setIdleCoreUnits(int idleCoreUnits) {
        this.idleCoreUnits = idleCoreUnits;
    }

    public void setIdleMemory(long idleMemory) {
        this.idleMemory = idleMemory;
    }

    public int getIdleGpuUnits() {
        return this.idleGpuUnits;
    }

    public void setIdleGpuUnits(int idleGpuUnits) {
        this.idleGpuUnits = idleGpuUnits;
    }

    public void setIdleGpuMemory(long idleGpuMemory) {
        this.idleGpuMemory = idleGpuMemory;
    }

    public String getHostId() {
        return hostId;
    }

    public void setHostId(String hostId) {
        this.hostId = hostId;
    }

    public String getJobId() {
        return jobId;
    }

    public void setJobId(String jobId) {
        this.jobId = jobId;
    }

    public String getLayerId() {
        return layerId;
    }

    public void setLayerId(String layerId) {
        this.layerId = layerId;
    }

    public String getFrameId() {
        return frameId;
    }

    public void setFrameId(String frameId) {
        this.frameId = frameId;
    }

    public RenderPartitionType getType() {
        return type;
    }

    public void setType(RenderPartitionType type) {
        this.type = type;
    }
}

