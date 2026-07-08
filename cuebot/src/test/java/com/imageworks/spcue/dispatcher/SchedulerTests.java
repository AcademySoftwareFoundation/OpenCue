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

package com.imageworks.spcue.dispatcher;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * Unit tests for the pure, side-effect-free logic in {@link Scheduler}:
 * tag normalization, host grouping, the fit check, the per-tick frame
 * prediction, and the E-PVM placement score. These need no Spring context
 * or database; the test lives in the dispatcher package so it can reach the
 * package-private static helpers and POJOs.
 */
public class SchedulerTests {

    /** Core points per whole core (host int_cores_idle is in core points). */
    private static final int CORE = 100;
    /** One gigabyte expressed in kilobytes (host/layer mem values are in KB). */
    private static final long GB = 1024L * 1024L;

    private static Scheduler.BookableHost host(String alloc, String tags, String os,
            int coresIdle, long memIdle, int gpusIdle, long gpuMemIdle,
            int coresTotal, long memTotal, int gpusTotal, long gpuMemTotal) {
        Scheduler.BookableHost h = new Scheduler.BookableHost();
        h.hostId = "host";
        h.hostName = "host";
        h.pkAlloc = alloc;
        h.tagsRaw = tags;
        h.os = os;
        h.coresIdle = coresIdle;
        h.memIdle = memIdle;
        h.gpusIdle = gpusIdle;
        h.gpuMemIdle = gpuMemIdle;
        h.coresTotal = coresTotal;
        h.memTotal = memTotal;
        h.gpusTotal = gpusTotal;
        h.gpuMemTotal = gpuMemTotal;
        h.runningProcs = 0;
        return h;
    }

    /** Host whose idle resources equal its totals (fully free). */
    private static Scheduler.BookableHost freeHost(int cores, long mem, int gpus, long gpuMem) {
        return host("alloc", "tags", "Linux", cores, mem, gpus, gpuMem,
                cores, mem, gpus, gpuMem);
    }

    private static Scheduler.LayerCandidate layer(int coresMin, long memMin,
            int gpusMin, long gpuMemMin) {
        Scheduler.LayerCandidate c = new Scheduler.LayerCandidate();
        c.layerId = "layer";
        c.jobId = "job";
        c.showId = "show";
        c.layerCoresMin = coresMin;
        c.layerMemMin = memMin;
        c.layerGpusMin = gpusMin;
        c.layerGpuMemMin = gpuMemMin;
        c.priority = 100;
        c.jobCoresInUse = 0;
        c.jobMaxCores = Integer.MAX_VALUE;
        c.showCoresInUse = 0;
        c.showBurstCores = Integer.MAX_VALUE;
        c.waitingFrameCount = 100;
        return c;
    }

    // ---- normalizeTags ----------------------------------------------------

    @Test
    public void normalizeTagsHandlesNullAndBlank() {
        assertEquals("", Scheduler.normalizeTags(null));
        assertEquals("", Scheduler.normalizeTags(""));
        assertEquals("", Scheduler.normalizeTags("   "));
    }

    @Test
    public void normalizeTagsSortsAndCollapsesWhitespace() {
        assertEquals("desktop linux", Scheduler.normalizeTags("linux desktop"));
        assertEquals("a b c", Scheduler.normalizeTags("c   a b"));
    }

    @Test
    public void normalizeTagsIsOrderIndependent() {
        assertEquals(Scheduler.normalizeTags("linux desktop"),
                Scheduler.normalizeTags("desktop linux"));
    }

    @Test
    public void normalizeTagsDedupsAndStripsHostName() {
        // cuebot stores "general general <hostname>"; grouping must reduce
        // that to just "general" so same-spec hosts group together.
        assertEquals("general",
                Scheduler.normalizeTags("general general elk0001", "elk0001"));
        // host-name exclusion is case-insensitive.
        assertEquals("general", Scheduler.normalizeTags("general ELK0001", "elk0001"));
    }

    @Test
    public void groupByHostSpecCollapsesHostsThatDifferOnlyByNameTag() {
        // Two hosts, identical spec, each carrying its own name as a tag.
        Scheduler.BookableHost a =
                host("alloc", "general a-host", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        a.hostName = "a-host";
        Scheduler.BookableHost b =
                host("alloc", "general b-host", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        b.hostName = "b-host";

        Map<Scheduler.HostSpecKey, List<Scheduler.BookableHost>> groups =
                Scheduler.groupByHostSpec(Arrays.asList(a, b));

        assertEquals(1, groups.size());
        assertEquals(2, groups.values().iterator().next().size());
    }

    // ---- groupByHostSpec --------------------------------------------------

    @Test
    public void groupByHostSpecUsesGpuTotalsNotIdle() {
        // A fully-booked GPU host (gpusIdle == 0) must still group as a GPU
        // host: GPU presence is static hardware, keyed off totals. This is
        // the regression guard for the idle-vs-total grouping fix.
        Scheduler.BookableHost gpuFullyBooked =
                host("a", "t", "Linux", 100, GB, 0, 0, 200, 2 * GB, 2, 8 * GB);
        Scheduler.BookableHost cpuOnly =
                host("a", "t", "Linux", 100, GB, 0, 0, 200, 2 * GB, 0, 0);

        Map<Scheduler.HostSpecKey, List<Scheduler.BookableHost>> groups =
                Scheduler.groupByHostSpec(Arrays.asList(gpuFullyBooked, cpuOnly));

        assertEquals(2, groups.size());

        boolean gpuKeyHasGpu = false;
        boolean cpuKeyHasGpu = true;
        for (Map.Entry<Scheduler.HostSpecKey, List<Scheduler.BookableHost>> e : groups.entrySet()) {
            if (e.getValue().contains(gpuFullyBooked)) {
                gpuKeyHasGpu = e.getKey().hasGpu;
            }
            if (e.getValue().contains(cpuOnly)) {
                cpuKeyHasGpu = e.getKey().hasGpu;
            }
        }
        assertTrue("fully-booked GPU host must group as GPU host", gpuKeyHasGpu);
        assertFalse("CPU-only host must not group as GPU host", cpuKeyHasGpu);
    }

    @Test
    public void groupByHostSpecMergesEquivalentTagOrderings() {
        Scheduler.BookableHost a =
                host("a", "linux desktop", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        Scheduler.BookableHost b =
                host("a", "desktop linux", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);

        Map<Scheduler.HostSpecKey, List<Scheduler.BookableHost>> groups =
                Scheduler.groupByHostSpec(Arrays.asList(a, b));

        assertEquals(1, groups.size());
        assertEquals(2, groups.values().iterator().next().size());
    }

    @Test
    public void groupByHostSpecSeparatesAllocAndOs() {
        Scheduler.BookableHost alloc1 =
                host("a1", "t", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        Scheduler.BookableHost alloc2 =
                host("a2", "t", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        Scheduler.BookableHost otherOs =
                host("a1", "t", "Windows", 100, GB, 0, 0, 100, GB, 0, 0);

        Map<Scheduler.HostSpecKey, List<Scheduler.BookableHost>> groups =
                Scheduler.groupByHostSpec(Arrays.asList(alloc1, alloc2, otherOs));

        assertEquals(3, groups.size());
    }

    // ---- fitsOnHost -------------------------------------------------------

    @Test
    public void fitsOnHostAcceptsExactFit() {
        assertTrue(Scheduler.fitsOnHost(layer(CORE, GB, 0, 0), freeHost(CORE, GB, 0, 0)));
        assertTrue(Scheduler.fitsOnHost(layer(CORE, GB, 1, GB), freeHost(CORE, GB, 1, GB)));
    }

    @Test
    public void fitsOnHostRejectsWhenAnyDimensionShort() {
        Scheduler.LayerCandidate cpu = layer(CORE, GB, 0, 0);
        assertFalse(Scheduler.fitsOnHost(cpu, freeHost(CORE - 1, GB, 0, 0)));
        assertFalse(Scheduler.fitsOnHost(cpu, freeHost(CORE, GB - 1, 0, 0)));

        Scheduler.LayerCandidate gpu = layer(CORE, GB, 1, GB);
        assertFalse(Scheduler.fitsOnHost(gpu, freeHost(CORE, GB, 0, GB)));
        assertFalse(Scheduler.fitsOnHost(gpu, freeHost(CORE, GB, 1, GB - 1)));
    }

    // ---- computeMaxMore ---------------------------------------------------

    @Test
    public void computeMaxMoreIsBoundedByThePhysicalDimension() {
        // 10 cores idle, 1-core layer, ample memory: 9 additional frames fit.
        assertEquals(9L,
                Scheduler.computeMaxMore(freeHost(10 * CORE, 100 * GB, 0, 0), layer(CORE, GB, 0, 0)));
    }

    @Test
    public void computeMaxMoreRespectsJobMaxCores() {
        Scheduler.LayerCandidate c = layer(CORE, GB, 0, 0);
        c.jobMaxCores = 3 * CORE;            // room for 3 cores total
        // first frame consumes 1 core, leaving room for 2 more.
        assertEquals(2L,
                Scheduler.computeMaxMore(freeHost(10 * CORE, 100 * GB, 0, 0), c));
    }

    @Test
    public void computeMaxMoreRespectsShowBurst() {
        Scheduler.LayerCandidate c = layer(CORE, GB, 0, 0);
        c.showBurstCores = 2 * CORE;         // room for 2 cores total
        assertEquals(1L,
                Scheduler.computeMaxMore(freeHost(10 * CORE, 100 * GB, 0, 0), c));
    }

    // ---- placementScore ---------------------------------------------------
    //
    // Real E-PVM: score is the marginal rise of a convex cost
    //   sum_D W_D * ( e^(after_D/total_D) - e^(before_D/total_D) )
    // with before_D = total_D - idle_D and after_D = before_D + layer.min_D.
    // Lower is better. Weights cores=1, mem=1, gpus=4, gpu_mem=1.

    /** Host with explicit idle resources (idle <= total). */
    private static Scheduler.BookableHost loadedHost(int cores, long mem,
            int coresIdle, long memIdle) {
        return host("alloc", "tags", "Linux", coresIdle, memIdle, 0, 0,
                cores, mem, 0, 0);
    }

    @Test
    public void placementScoreOnEmptyHostIsExpFractionPerDimension() {
        // 4-core/4GB layer on an empty 4-core/4GB host: each dimension goes
        // 0 -> full, so its term is e^1 - 1; cores + mem give 2*(e-1).
        Scheduler.LayerCandidate c = layer(4 * CORE, 4 * GB, 0, 0);
        double term = Math.exp(1.0) - 1.0;
        assertEquals(2 * term, Scheduler.placementScore(freeHost(4 * CORE, 4 * GB, 0, 0), c), 1e-9);
    }

    @Test
    public void placementScorePrefersLargerEmptyHostForSameFrame() {
        // E-PVM is load-balancing: the same frame is a smaller fraction of a
        // bigger host, so an empty 64-core/64GB host scores LOWER (is filled
        // first) than an empty 4-core/4GB host. This is what stops big hosts
        // from sitting idle under the old absolute-stranding score.
        Scheduler.LayerCandidate c = layer(4 * CORE, 4 * GB, 0, 0);
        double small = Scheduler.placementScore(freeHost(4 * CORE, 4 * GB, 0, 0), c);
        double big   = Scheduler.placementScore(freeHost(64 * CORE, 64 * GB, 0, 0), c);
        assertTrue("bigger empty host should score lower", big < small);
        // Exact: 2*(e^(4/64) - 1) on the 64-core host.
        assertEquals(2 * (Math.exp(4.0 / 64.0) - 1.0), big, 1e-9);
    }

    @Test
    public void placementScoreRisesAsAHostFillsUp() {
        // Convexity: adding the same frame to a host that is already loaded
        // costs more than adding it to the same-size empty host, so work
        // spreads across hosts instead of piling onto one.
        Scheduler.LayerCandidate c = layer(CORE, GB, 0, 0);
        double empty  = Scheduler.placementScore(loadedHost(8 * CORE, 8 * GB, 8 * CORE, 8 * GB), c);
        double loaded = Scheduler.placementScore(loadedHost(8 * CORE, 8 * GB, 2 * CORE, 2 * GB), c);
        assertTrue("loaded host should score higher than empty", loaded > empty);
    }

    @Test
    public void placementScoreTreatsMemorySaturatedHostAsFull() {
        // A host with idle cores but nearly saturated memory sits high on the
        // memory axis, so its marginal cost is dominated by the steep e^x
        // region, far higher than a balanced host with the same idle cores.
        Scheduler.LayerCandidate c = layer(CORE, GB, 0, 0);
        double balanced  = Scheduler.placementScore(loadedHost(8 * CORE, 8 * GB, 4 * CORE, 4 * GB), c);
        double memTight  = Scheduler.placementScore(loadedHost(8 * CORE, 8 * GB, 4 * CORE, 1 * GB), c);
        assertTrue("memory-tight host should score higher", memTight > balanced);
    }

    @Test
    public void placementScoreWeightsGpuDimensions() {
        // 1-core/1GB/1-gpu/1GB-gpumem layer on an empty 1-core/1GB/2-gpu/4GB
        // host. Each dimension's term is e^(add/total) - 1:
        //   cores   : e^1   - 1
        //   mem     : e^1   - 1
        //   gpus    : (e^0.5 - 1) * 4   (W_GPUS = 4)
        //   gpu_mem : (e^0.25 - 1) * 1
        Scheduler.LayerCandidate gpu = layer(CORE, GB, 1, GB);
        double expected = (Math.exp(1.0) - 1.0)
                        + (Math.exp(1.0) - 1.0)
                        + 4.0 * (Math.exp(0.5) - 1.0)
                        + 1.0 * (Math.exp(0.25) - 1.0);
        assertEquals(expected, Scheduler.placementScore(freeHost(CORE, GB, 2, 4 * GB), gpu), 1e-9);
    }

    @Test
    public void placementScoreDoesNotPenalizeGpuSurplusForNonGpuLayer() {
        // A non-GPU layer adds nothing on the GPU dimensions (add <= 0), so a
        // GPU host's idle GPUs contribute 0 to its score: GPU hosts are
        // protected from non-GPU work by grouping (has_gpu in the spec key),
        // not by the score. The score equals the cores+mem terms only.
        Scheduler.LayerCandidate cpu = layer(CORE, GB, 0, 0);
        double expected = 2 * (Math.exp(1.0) - 1.0);
        assertEquals(expected, Scheduler.placementScore(freeHost(CORE, GB, 4, 16 * GB), cpu), 1e-9);
    }

    // ---- EASY backfill: hostReadySeconds ----------------------------------

    @Test
    public void hostReadySecondsIsZeroWhenNoCoresNeeded() {
        // The host already has enough free cores for its reserving layer.
        assertEquals(0, Scheduler.hostReadySeconds(0, Arrays.asList(new int[] {100, 30})));
        assertEquals(0, Scheduler.hostReadySeconds(-100, null));
    }

    @Test
    public void hostReadySecondsReturnsCrossingProcsFinishTime() {
        // Need 2 cores' worth (200 points). Procs free at 10s (1 core) and 30s
        // (1 core); the second crosses the threshold, so the host is ready at 30s.
        List<int[]> procs = Arrays.asList(new int[] {100, 30}, new int[] {100, 10});
        assertEquals(30, Scheduler.hostReadySeconds(200, procs));
    }

    @Test
    public void hostReadySecondsStopsAtFirstSufficientProc() {
        // One big proc frees 4 cores at 20s; that alone covers the 3-core need.
        List<int[]> procs = Arrays.asList(new int[] {400, 20}, new int[] {100, 5});
        assertEquals(20, Scheduler.hostReadySeconds(300, procs));
    }

    @Test
    public void hostReadySecondsUnknownWhenProcsCannotFreeEnough() {
        // Procs free only 2 cores total but 5 are needed -> never ready.
        List<int[]> procs = Arrays.asList(new int[] {100, 10}, new int[] {100, 20});
        assertEquals(Integer.MAX_VALUE, Scheduler.hostReadySeconds(500, procs));
    }

    @Test
    public void hostReadySecondsUnknownWhenNoProcs() {
        assertEquals(Integer.MAX_VALUE, Scheduler.hostReadySeconds(100, null));
    }

    @Test
    public void hostReadySecondsUnknownWhenANeededProcHasNoEstimate() {
        // First proc (10s) frees 1 core; the next needed proc has an unknown
        // finish (MAX_VALUE) so the host's ready time is unknown, not optimistic.
        List<int[]> procs = Arrays.asList(
                new int[] {100, 10}, new int[] {100, Integer.MAX_VALUE});
        assertEquals(Integer.MAX_VALUE, Scheduler.hostReadySeconds(200, procs));
    }

    // ---- EASY backfill: backfillFits --------------------------------------

    @Test
    public void backfillFitsWhenFrameFinishesBeforeHostIsNeeded() {
        // Worst-case frame runtime 30s, host free for its owner in 60s -> safe.
        assertTrue(Scheduler.backfillFits(true, 30, 60));
        // Exactly equal is allowed (<=).
        assertTrue(Scheduler.backfillFits(true, 60, 60));
    }

    @Test
    public void backfillRefusedWhenFrameOutlastsTheReservation() {
        assertFalse(Scheduler.backfillFits(true, 90, 60));
    }

    @Test
    public void backfillRefusedWithoutRuntimeHistory() {
        // No estimate -> cannot bound the frame, never borrow a reserved host.
        assertFalse(Scheduler.backfillFits(false, 10, 10_000));
    }

    @Test
    public void backfillRefusedWhenHostReadyTimeIsUnknown() {
        assertFalse(Scheduler.backfillFits(true, 1, Integer.MAX_VALUE));
    }
}
