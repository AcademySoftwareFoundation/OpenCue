
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
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.util.CueUtil;

public class DispatchHost extends Entity
    implements HostInterface, FacilityInterface, ResourceContainer {

    public String facilityId;
    public String allocationId;
    public LockState lockState;
    public HardwareState hardwareState;

    public int cores;
    public int idleCores;

    public int gpu;
    public int idleGpu;

    // Basically an 0 = auto, 1 = all.
    public int threadMode;

    public long memory;
    public long idleMemory;
    public long gpuMemory;
    public long idleGpuMemory;
    public String tags;
    public String os;

    public boolean isNimby;
    public boolean isLocalDispatch = false;

    /**
     * Number of cores that will be added to the first proc
     * booked to this host.
     */
    public int strandedCores = 0;
    public int strandedGpu = 0;

    // To reserve resources for future gpu job
    int idleCoresOrig = 0;
    long idleMemoryOrig = 0;
    int idleGpuOrig = 0;
    long idleGpuMemoryOrig = 0;

    public String getHostId() {
        return id;
    }

    public String getAllocationId() {
        return allocationId;
    }

    public String getFacilityId() {
        return facilityId;
    }

    @Override
    public boolean hasAdditionalResources(int minCores, int minGpu, long minMemory, long minGpuMemory) {

        if (idleCores < minCores) {
            return false;
        } else if (idleGpu < minGpu) {
            return false;
        } else if (idleMemory <  minMemory) {
            return false;
        } else if (idleGpuMemory <  minGpuMemory) {
            return false;
        }

        return true;
    }

    @Override
    public void useResources(int coreUnits, int gpu, long memory, long gpuMemory) {
        idleCores = idleCores - coreUnits;
        idleMemory = idleMemory - memory;
        idleGpu = idleGpu - gpu;
        idleGpuMemory = idleGpuMemory - gpuMemory;
    }

    /**
     * If host has idle gpu, remove enough resources to book a gpu frame later.
     *
     */
    public void removeGpu() {
        if (idleGpuMemory > 0 && idleGpuMemoryOrig == 0) {
            idleMemoryOrig = idleMemory;
            idleCoresOrig = idleCores;
            idleGpuOrig = idleGpu;
            idleGpuMemoryOrig = idleGpuMemory;

            idleMemory = (long) idleMemory - Math.min(CueUtil.GB4, idleMemory);
            idleCores = (int) idleCores - Math.min(100, idleCores);
            idleGpu = (int) idleGpu - idleGpu;
            idleGpuMemory = 0;
        }
    }

    /**
     * If host had idle gpu removed, restore the host to the origional state.
     *
     */
    public void restoreGpu() {
        if (idleGpuMemoryOrig > 0) {
            idleMemory = idleMemoryOrig;
            idleCores = idleCoresOrig;
            idleGpu = idleGpuOrig;
            idleGpuMemory = idleGpuMemoryOrig;

            idleMemoryOrig = 0;
            idleCoresOrig = 0;
            idleGpuOrig = 0;
            idleGpuMemoryOrig = 0;
        }
    }
}

