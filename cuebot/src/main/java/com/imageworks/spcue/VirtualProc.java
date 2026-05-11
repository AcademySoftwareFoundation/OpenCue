
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

import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.ThreadMode;

import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.LogManager;

public class VirtualProc extends FrameEntity implements ProcInterface {

    private static final Logger logger = LogManager.getLogger(VirtualProc.class);

    public String hostId;
    public String allocationId;
    public String frameId;
    public String hostName;
    public String os;
    public byte[] childProcesses;

    public boolean canHandleNegativeCoresRequest;
    public int coresReserved;
    public long memoryReserved;
    public long memoryUsed;
    public long memoryMax;
    public long virtualMemoryUsed;
    public long virtualMemoryMax;

    public int gpusReserved;
    public long gpuMemoryReserved;
    public long gpuMemoryUsed;
    public long gpuMemoryMax;

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
     * Efficient mode tries to assign one core per frame, but may upgrade the number of cores based
     * on memory usage.
     *
     * Fast mode books all the idle cores on the the host at one time.
     */
    public static final VirtualProc build(DispatchHost host, DispatchFrame frame,
            String... selfishServices) {
        VirtualProc proc = seedProc(host, frame);

        // Give away all existing stranded cores to drift host back to a balanced state
        // Read "docs > User Guides > Stranded Cores in Cuebot" for more info
        if (host.strandedCores > 0) {
            proc.coresReserved += host.strandedCores;
        }
        proc.canHandleNegativeCoresRequest =
                host.canHandleNegativeCoresRequest(proc.coresReserved);

        int requested = proc.coresReserved;
        if (requested == 0) {
            logger.debug("Reserving all cores");
            proc.coresReserved = host.cores;
        } else if (requested < 0) {
            logger.debug("Reserving all cores minus " + requested);
            proc.coresReserved = host.cores + requested;
        } else if (requested >= 100) {
            proc.coresReserved =
                    computeMultiCoreReservation(host, frame, requested, selfishServices);
        }

        if (!frame.threadable && proc.coresReserved > 100) {
            proc.coresReserved = 100;
        }
        return proc;
    }

    private static VirtualProc seedProc(DispatchHost host, DispatchFrame frame) {
        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.getAllocationId();
        proc.hostId = host.getHostId();
        proc.frameId = null;
        proc.layerId = frame.getLayerId();
        proc.jobId = frame.getJobId();
        proc.showId = frame.getShowId();
        proc.facilityId = frame.getFacilityId();
        proc.os = frame.os;

        proc.hostName = host.getName();
        proc.unbooked = false;
        proc.isLocalDispatch = host.isLocalDispatch;

        proc.coresReserved = frame.minCores;
        proc.memoryReserved = frame.getMinMemory();
        proc.gpusReserved = frame.minGpus;
        proc.gpuMemoryReserved = frame.minGpuMemory;
        return proc;
    }

    private static int computeMultiCoreReservation(DispatchHost host, DispatchFrame frame,
            int requested, String[] selfishServices) {
        int wholeCores = wholeIdleCores(host);
        requireWholeCore(wholeCores, frame);

        int cores = baseReservationByMode(host, frame, wholeCores, requested, selfishServices);
        cores = enforceVariableFloor(host, frame, cores);
        cores = applySanityBounds(cores, requested, frame.maxCores);
        cores = clampToIdle(host, frame, cores, wholeCores);
        return cores;
    }

    private static int wholeIdleCores(DispatchHost host) {
        return (int) Math.floor(host.idleCores / 100.0);
    }

    private static void requireWholeCore(int wholeCores, DispatchFrame frame) {
        if (wholeCores == 0) {
            throw new EntityException("The host had only a fraction of a core remaining "
                    + "but the frame required " + frame.minCores);
        }
    }

    private static int baseReservationByMode(DispatchHost host, DispatchFrame frame,
            int wholeCores, int requested, String[] selfishServices) {
        if (host.threadMode == ThreadMode.ALL_VALUE) {
            return wholeCores * 100;
        }
        if (!frame.threadable) {
            return requested;
        }
        if (isSelfishService(frame, selfishServices)) {
            return wholeCores * 100;
        }
        if (host.idleMemory - frame.getMinMemory() <= Dispatcher.MEM_STRANDED_THRESHHOLD) {
            return wholeCores * 100;
        }
        return getCoreSpan(host, frame.getMinMemory(), frame.maxCores);
    }

    private static int enforceVariableFloor(DispatchHost host, DispatchFrame frame, int cores) {
        if (host.threadMode != ThreadMode.VARIABLE_VALUE || !frame.threadable || cores > 200) {
            return cores;
        }
        if (200 > host.idleCores) {
            // Do not allow threadable frame running on 1 core.
            throw new JobDispatchException(
                    "Do not allow threadable frame running one core on a ThreadMode.Variable host.");
        }
        return 200;
    }

    private static int applySanityBounds(int cores, int originalCores, int maxCores) {
        if (cores < 100) {
            cores = 100;
        }
        if (cores < originalCores) {
            cores = originalCores;
        }
        if (maxCores > 0 && cores > maxCores) {
            cores = maxCores;
        }
        return cores;
    }

    private static int clampToIdle(DispatchHost host, DispatchFrame frame, int cores,
            int wholeCores) {
        if (cores <= host.idleCores) {
            return cores;
        }
        if (host.threadMode == ThreadMode.VARIABLE_VALUE && frame.threadable
                && wholeCores == 1) {
            throw new JobDispatchException(
                    "Do not allow threadable frame running one core on a ThreadMode.Variable host.");
        }
        return wholeCores * 100;
    }

    private static boolean isSelfishService(DispatchFrame frame, String[] selfishServices) {
        return selfishServices != null && frame.services != null
                && containsSelfishService(frame.services.split(","), selfishServices);
    }

    private static final boolean containsSelfishService(String[] frameServices,
            String[] selfishServices) {
        for (String frameService : frameServices) {
            for (String selfishService : selfishServices) {
                if (frameService.equals(selfishService)) {
                    return true;
                }
            }
        }
        return false;
    }

    public static final VirtualProc build(DispatchHost host, DispatchFrame frame,
            LocalHostAssignment lja) {

        VirtualProc proc = new VirtualProc();
        proc.allocationId = host.getAllocationId();
        proc.hostId = host.getHostId();
        proc.frameId = null;
        proc.layerId = frame.getLayerId();
        proc.jobId = frame.getJobId();
        proc.showId = frame.getShowId();
        proc.facilityId = frame.getFacilityId();
        proc.os = frame.os;

        proc.hostName = host.getName();
        proc.unbooked = false;
        proc.isLocalDispatch = host.isLocalDispatch;

        proc.coresReserved = lja.getThreads() * 100;
        proc.memoryReserved = frame.getMinMemory();
        proc.gpusReserved = frame.minGpus;
        proc.gpuMemoryReserved = frame.minGpuMemory;

        int wholeCores = (int) (Math.floor(host.idleCores / 100.0));
        if (wholeCores == 0) {
            throw new EntityException("The host had only a fraction of a core remaining "
                    + "but the frame required " + frame.minCores);
        }

        if (proc.coresReserved > host.idleCores) {
            proc.coresReserved = wholeCores * 100;
        }

        return proc;

    }

    /**
     * Allocates additional cores when the frame is using more than a single core's worth of memory,
     * bounded by maxCores when set.
     *
     * @param host
     * @param minMemory
     * @param maxCores maximum cores allowed in core units (using core_multiplier: 100 = 1, 0 = no
     *        limit)
     * @return
     */
    public static int getCoreSpan(DispatchHost host, long minMemory, int maxCores) {
        int totalCores = (int) (Math.floor(host.cores / 100.0));
        int idleCores = (int) (Math.floor(host.idleCores / 100.0));
        if (idleCores < 1) {
            return 100;
        }

        long memPerCore = host.idleMemory / totalCores;
        double procs = minMemory / (double) memPerCore;
        int reserveCores = (int) (Math.round(procs)) * 100;

        // Respect max cores even when the memory-per-core guideline
        // would allocate more cores than the frame is allowed to use.
        if (maxCores > 0 && reserveCores > maxCores) {
            reserveCores = maxCores;
        }

        return reserveCores;
    }
}
