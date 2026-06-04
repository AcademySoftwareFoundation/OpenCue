
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

/**
 * Per-allocation core counts used to measure memory-stranded cores: idle cores that cannot be
 * booked because their host has run out of memory.
 *
 * All core values are in units of 100 (the same units stored in the host table, where 100 == one
 * physical core).
 */
public class StrandedCoreStats {

    /** Name of the allocation these counts belong to. */
    public final String allocName;

    /** Total cores on UP and OPEN hosts in the allocation. */
    public final long totalCores;

    /** Idle cores on UP and OPEN hosts in the allocation. */
    public final long idleCores;

    /**
     * Idle cores on UP and OPEN hosts in the allocation whose idle memory is at or below
     * {@code Dispatcher.MEM_STRANDED_THRESHHOLD}, i.e. cores stranded by memory exhaustion.
     */
    public final long strandedCores;

    public StrandedCoreStats(String allocName, long totalCores, long idleCores,
            long strandedCores) {
        this.allocName = allocName;
        this.totalCores = totalCores;
        this.idleCores = idleCores;
        this.strandedCores = strandedCores;
    }
}
