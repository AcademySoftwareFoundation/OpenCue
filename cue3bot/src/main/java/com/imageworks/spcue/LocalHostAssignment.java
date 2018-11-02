
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
    private long idleGpu;

    private long maxMemory;
    private long maxGpu;
    private int maxCoreUnits;

    private int threads;

    private String hostId;
    private String jobId = null;
    private String layerId = null;
    private String frameId = null;

    private RenderPartitionType type;

    public LocalHostAssignment() { }

    public LocalHostAssignment(int maxCores, int threads, long maxMemory, long maxGpu) {
        this.maxCoreUnits = maxCores;
        this.threads = threads;
        this.maxMemory = maxMemory;
        this.maxGpu = maxGpu;
    }

    @Override
    public boolean hasAdditionalResources(int minCores, long minMemory, long minGpu) {

        if (idleCoreUnits < minCores) {
            return false;
        }
        else if (idleMemory <  minMemory) {
            return false;
        }
        else if (idleGpu <  minGpu) {
            return false;
        }

        return true;
    }

    @Override
    public void useResources(int coreUnits, long memory, long gpu) {
        idleCoreUnits = idleCoreUnits - coreUnits;
        idleMemory = idleMemory - memory;
        idleGpu = idleGpu - gpu;
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

    public long getMaxGpu() {
        return maxGpu;
    }

    public void setMaxGpu(long maxGpu) {
        this.maxGpu = maxGpu;
    }

    public long getIdleGpu() {
        return this.idleGpu;
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

    public void setIdleGpu(long idleGpu) {
        this.idleGpu = idleGpu;
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

