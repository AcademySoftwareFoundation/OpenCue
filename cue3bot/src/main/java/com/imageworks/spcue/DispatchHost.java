
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

import com.imageworks.spcue.CueIce.LockState;
import com.imageworks.spcue.dispatcher.ResourceContainer;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.util.CueUtil;

public class DispatchHost extends Entity
    implements Host, FacilityInterface, ResourceContainer {

    public String facilityId;
    public String allocationId;
    public LockState lockState;
    public HardwareState hardwareState;

    public int cores;
    public int idleCores;

    // Basically an 0 = auto, 1 = all.
    public int threadMode;

    public long memory;
    public long idleMemory;
    public long gpu;
    public long idleGpu;
    public String tags;
    public String os;

    public boolean isNimby;
    public boolean isLocalDispatch = false;

    /**
     * Number of cores that will be added to the first proc
     * booked to this host.
     */
    public int strandedCores = 0;

    // To reserve resources for future gpu job
    long idleMemoryOrig = 0;
    int idleCoresOrig = 0;
    long idleGpuOrig = 0;

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
    public boolean hasAdditionalResources(int minCores, long minMemory, long minGpu) {

        if (idleCores < minCores) {
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
        idleCores = idleCores - coreUnits;
        idleMemory = idleMemory - memory;
        idleGpu = idleGpu - gpu;
    }

    /**
     * If host has idle gpu, remove enough resources to book a gpu frame later.
     *
     */
    public void removeGpu() {
        if (idleGpu > 0 && idleGpuOrig == 0) {
            idleMemoryOrig = idleMemory;
            idleCoresOrig = idleCores;
            idleGpuOrig = idleGpu;

            idleMemory = (long) idleMemory - Math.min(CueUtil.GB4, idleMemory);
            idleCores = (int) idleCores - Math.min(100, idleCores);
            idleGpu = 0;
        }
    }

    /**
     * If host had idle gpu removed, restore the host to the origional state.
     *
     */
    public void restoreGpu() {
        if (idleGpuOrig > 0) {
            idleMemory = idleMemoryOrig;
            idleCores = idleCoresOrig;
            idleGpu = idleGpuOrig;

            idleMemoryOrig = 0;
            idleCoresOrig = 0;
            idleGpuOrig = 0;
        }
    }
}

