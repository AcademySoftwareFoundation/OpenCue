
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
