
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

import java.util.Date;

import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.Host;
import com.imageworks.spcue.grpc.host.LockState;

public class HostEntity extends Entity implements HostInterface {

    public String facilityId;
    public String allocId;
    public HardwareState state;
    public LockState lockState;
    public boolean nimbyEnabled;

    public int procs;
    public int cores;
    public int gpu;
    public int idleCores;
    public int idleGpu;
    public int memory;
    public int idleMemory;
    public int gpuMemory;
    public int idleGpuMemory;

    public boolean unlockAtBoot;

    public Date dateCreated;
    public Date datePinged;
    public Date dateBooted;

    public HostEntity() {}

    public HostEntity(Host grpcHost) {
        this.id = grpcHost.getId();
        this.allocId = grpcHost.getAllocName();
        this.state = grpcHost.getState();
        this.lockState = grpcHost.getLockState();
        this.nimbyEnabled = grpcHost.getNimbyEnabled();
        this.cores = (int) grpcHost.getCores();
        this.idleCores = (int) grpcHost.getIdleCores();
        this.gpu = (int) grpcHost.getGpu();
        this.idleGpu = (int) grpcHost.getIdleGpu();
        this.memory = (int) grpcHost.getMemory();
        this.idleMemory = (int) grpcHost.getIdleMemory();
        this.gpuMemory = (int) grpcHost.getGpuMemory();
        this.idleGpuMemory = (int) grpcHost.getIdleGpuMemory();
    }

    public String getHostId() {
        return id;
    }

    public String getAllocationId() {
        return allocId;
    }

    public String getFacilityId() {
        return facilityId;
    }
}

