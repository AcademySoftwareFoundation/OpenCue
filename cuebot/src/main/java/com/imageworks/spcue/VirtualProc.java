
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

import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.ThreadMode;

public class VirtualProc extends FrameEntity implements ProcInterface {

    public String hostId;
    public String allocationId;
    public String frameId;
    public String hostName;
    public String os;

    public int coresReserved;
    public int gpuReserved;
    public long memoryReserved;
    public long memoryUsed;
    public long memoryMax;
    public long virtualMemoryUsed;
    public long virtualMemoryMax;
    public long gpuMemoryReserved;

    public boolean unbooked;
    public boolean usageRecorded = false;
    public boolean isLocalDispatch = false;

    public String getProcId() {
        return id;
    }

    public String getHostId() {
        return hostId;
    }

    public String getAllocationId() {
        return allocationId;
    }

    public String getFrameId() {
        return frameId;
    }

    public String getName() {
        return hostName;
    }

    /**
     * Build and return a proc in either fast or efficient mode.
     *
     * Efficient mode tries to assign one core per frame, but may upgrade the
     * number of cores based on memory usage.
     *
     * Fast mode books all the idle cores on the the host at one time.
     *
     * @param host
     * @param frame
     * @return
     */
    public static final VirtualProc build(DispatchHost host, DispatchFrame frame) {
        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.getAllocationId();
        proc.hostId = host.getHostId();
        proc.frameId = null;
        proc.layerId = frame.getLayerId();
        proc.jobId = frame.getJobId();
        proc.showId = frame.getShowId();
        proc.facilityId = frame.getFacilityId();
        proc.os = host.os;

        proc.hostName = host.getName();
        proc.unbooked = false;
        proc.isLocalDispatch = host.isLocalDispatch;

        proc.coresReserved = frame.minCores;
        proc.gpuReserved = frame.minGpu;
        proc.memoryReserved = frame.minMemory;
        proc.gpuMemoryReserved = frame.minGpuMemory;

        /*
         * Frames that are announcing cores less than 100 are not multi-threaded
         * so there is no reason for the frame to span more than a single core.
         *
         * If we are in "fast mode", we just book all the cores If the host is
         * nimby, desktops are automatically fast mode.
         */

        if (host.strandedCores > 0) {
            proc.coresReserved = proc.coresReserved + host.strandedCores;
        }

        if (proc.coresReserved >= 100) {

            int originalCores = proc.coresReserved;

            /*
             * wholeCores could be 0 if we have a fraction of a core, we can
             * just throw a re
             */
            int wholeCores = (int) (Math.floor(host.idleCores / 100.0));
            if (wholeCores == 0) {
                throw new EntityException(
                        "The host had only a fraction of a core remaining "
                                + "but the frame required " + frame.minCores);
            }

            // if (host.threadMode == ThreadMode.Variable.value() &&
            // CueUtil.isDayTime()) {
            if (host.threadMode == ThreadMode.ALL_VALUE) {
                proc.coresReserved = wholeCores * 100;
            } else {
                if (frame.threadable) {
                    if (host.idleMemory - frame.minMemory
                            <= Dispatcher.MEM_STRANDED_THRESHHOLD) {
                        proc.coresReserved = wholeCores * 100;
                    } else {
                        proc.coresReserved = getCoreSpan(host, frame.minMemory);
                    }

                    if (host.threadMode == ThreadMode.VARIABLE_VALUE
                            && proc.coresReserved <= 200) {
                        proc.coresReserved = 200;
                        if (proc.coresReserved > host.idleCores) {
                            // Do not allow threadable frame running on 1 core.
                            throw new JobDispatchException(
                                    "Do not allow threadable frame running one core on a ThreadMode.Variable host.");
                        }
                    }
                }
            }

            /*
             * Sanity checks to ensure coreUnits are not to high or to low.
             */
            if (proc.coresReserved < 100) {
                proc.coresReserved = 100;
            }

            /*
             * If the core value is changed it can never fall below the
             * original.
             */
            if (proc.coresReserved < originalCores) {
                proc.coresReserved = originalCores;
            }

            /*
             * Check to ensure we haven't exceeded max cores.
             */
            if (frame.maxCores > 0 && proc.coresReserved >= frame.maxCores) {
                proc.coresReserved = frame.maxCores;
            }

            if (proc.coresReserved > host.idleCores) {
                if (host.threadMode == ThreadMode.VARIABLE_VALUE
                        && frame.threadable && wholeCores == 1) {
                    throw new JobDispatchException(
                            "Do not allow threadable frame running one core on a ThreadMode.Variable host.");
                }
                proc.coresReserved = wholeCores * 100;
            }
        }

        /*
         * Don't thread non-threadable layers, no matter what people put for the
         * number of cores.
         */
        if (!frame.threadable && proc.coresReserved > 100) {
            proc.coresReserved = 100;
        }

        return proc;
    }

    public static final VirtualProc build(DispatchHost host,
            DispatchFrame frame, LocalHostAssignment lja) {

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.getAllocationId();
        proc.hostId = host.getHostId();
        proc.frameId = null;
        proc.layerId = frame.getLayerId();
        proc.jobId = frame.getJobId();
        proc.showId = frame.getShowId();
        proc.facilityId = frame.getFacilityId();
        proc.os = host.os;

        proc.hostName = host.getName();
        proc.unbooked = false;
        proc.isLocalDispatch = host.isLocalDispatch;

        proc.coresReserved = lja.getThreads() * 100;
        proc.memoryReserved = frame.minMemory;
        proc.gpuMemoryReserved = frame.minGpuMemory;

        int wholeCores = (int) (Math.floor(host.idleCores / 100.0));
        if (wholeCores == 0) {
            throw new EntityException(
                    "The host had only a fraction of a core remaining "
                            + "but the frame required " + frame.minCores);
        }

        if (proc.coresReserved > host.idleCores) {
            proc.coresReserved = wholeCores * 100;
        }

        return proc;

    }

    /**
     * Allocates additional cores when the frame is using more 50% more than a
     * single cores worth of memory.
     *
     * @param host
     * @param minMemory
     * @return
     */
    public static int getCoreSpan(DispatchHost host, long minMemory) {
        int totalCores = (int) (Math.floor(host.cores / 100.0));
        int idleCores = (int) (Math.floor(host.idleCores / 100.0));
        if (idleCores < 1) {
            return 100;
        }

        long memPerCore = host.idleMemory / totalCores;
        double procs = minMemory / (double) memPerCore;
        int reserveCores = (int) (Math.round(procs)) * 100;

        return reserveCores;
    }
}

