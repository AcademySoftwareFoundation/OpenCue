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

import java.lang.reflect.Field;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

import org.junit.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.transaction.PlatformTransactionManager;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.DispatchJob;
import com.imageworks.spcue.FrameDetail;
import com.imageworks.spcue.LayerDetail;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.grpc.job.FrameState;
import com.imageworks.spcue.grpc.report.FrameCompleteReport;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.service.JobManager;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdLaunchUnknownOutcomeException;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;
import com.imageworks.spcue.util.CueUtil;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for the pure, side-effect-free logic in {@link Maestro}: tag normalization, host
 * grouping, the fit check, the per-tick frame prediction, and the E-PVM placement score. These need
 * no Spring context or database; the test lives in the dispatcher package so it can reach the
 * package-private static helpers and POJOs.
 */
public class MaestroTests {

    /** Core points per whole core (host int_cores_idle is in core points). */
    private static final int CORE = 100;
    /** One gigabyte expressed in kilobytes (host/layer mem values are in KB). */
    private static final long GB = 1024L * 1024L;

    private static Maestro.BookableHost host(String alloc, String tags, String os, int coresIdle,
            long memIdle, int gpusIdle, long gpuMemIdle, int coresTotal, long memTotal,
            int gpusTotal, long gpuMemTotal) {
        Maestro.BookableHost h = new Maestro.BookableHost();
        h.hostId = "host";
        h.hostName = "host";
        h.pkAlloc = alloc;
        h.pkFacility = "facility0";
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
    private static Maestro.BookableHost freeHost(int cores, long mem, int gpus, long gpuMem) {
        return host("alloc", "tags", "Linux", cores, mem, gpus, gpuMem, cores, mem, gpus, gpuMem);
    }

    private static Maestro.LayerCandidate layer(int coresMin, long memMin, int gpusMin,
            long gpuMemMin) {
        Maestro.LayerCandidate c = new Maestro.LayerCandidate();
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
        assertEquals("", Maestro.normalizeTags(null));
        assertEquals("", Maestro.normalizeTags(""));
        assertEquals("", Maestro.normalizeTags("   "));
    }

    @Test
    public void normalizeTagsSortsAndCollapsesWhitespace() {
        assertEquals("desktop linux", Maestro.normalizeTags("linux desktop"));
        assertEquals("a b c", Maestro.normalizeTags("c   a b"));
    }

    @Test
    public void normalizeTagsIsOrderIndependent() {
        assertEquals(Maestro.normalizeTags("linux desktop"),
                Maestro.normalizeTags("desktop linux"));
    }

    @Test
    public void normalizeTagsDedupsAndStripsHostName() {
        // cuebot stores "general general <hostname>"; grouping must reduce
        // that to just "general" so same-spec hosts group together.
        assertEquals("general", Maestro.normalizeTags("general general elk0001", "elk0001"));
        // host-name exclusion is case-insensitive.
        assertEquals("general", Maestro.normalizeTags("general ELK0001", "elk0001"));
    }

    @Test
    public void groupByHostSpecCollapsesHostsThatDifferOnlyByNameTag() {
        // Two hosts, identical spec, each carrying its own name as a tag.
        Maestro.BookableHost a =
                host("alloc", "general a-host", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        a.hostName = "a-host";
        Maestro.BookableHost b =
                host("alloc", "general b-host", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        b.hostName = "b-host";

        Map<Maestro.HostSpecKey, List<Maestro.BookableHost>> groups =
                Maestro.groupByHostSpec(Arrays.asList(a, b));

        assertEquals(1, groups.size());
        assertEquals(2, groups.values().iterator().next().size());
    }

    // ---- groupByHostSpec --------------------------------------------------

    @Test
    public void groupByHostSpecUsesGpuTotalsNotIdle() {
        // A fully-booked GPU host (gpusIdle == 0) must still group as a GPU
        // host: GPU presence is static hardware, keyed off totals. This is
        // the regression guard for the idle-vs-total grouping fix.
        Maestro.BookableHost gpuFullyBooked =
                host("a", "t", "Linux", 100, GB, 0, 0, 200, 2 * GB, 2, 8 * GB);
        Maestro.BookableHost cpuOnly = host("a", "t", "Linux", 100, GB, 0, 0, 200, 2 * GB, 0, 0);

        Map<Maestro.HostSpecKey, List<Maestro.BookableHost>> groups =
                Maestro.groupByHostSpec(Arrays.asList(gpuFullyBooked, cpuOnly));

        assertEquals(2, groups.size());

        boolean gpuKeyHasGpu = false;
        boolean cpuKeyHasGpu = true;
        for (Map.Entry<Maestro.HostSpecKey, List<Maestro.BookableHost>> e : groups.entrySet()) {
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
        Maestro.BookableHost a = host("a", "linux desktop", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        Maestro.BookableHost b = host("a", "desktop linux", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);

        Map<Maestro.HostSpecKey, List<Maestro.BookableHost>> groups =
                Maestro.groupByHostSpec(Arrays.asList(a, b));

        assertEquals(1, groups.size());
        assertEquals(2, groups.values().iterator().next().size());
    }

    @Test
    public void groupByHostSpecSeparatesFacility() {
        // The candidate query binds the group's facility (jobs run only in
        // their own facility, like the legacy job.pk_facility clause), so the
        // key must honor it even though in practice facility follows alloc.
        Maestro.BookableHost facA = host("a1", "t", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        Maestro.BookableHost facB = host("a1", "t", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        facB.pkFacility = "facility1";

        Map<Maestro.HostSpecKey, List<Maestro.BookableHost>> groups =
                Maestro.groupByHostSpec(Arrays.asList(facA, facB));

        assertEquals(2, groups.size());
    }

    @Test
    public void groupByHostSpecSeparatesAllocAndOs() {
        Maestro.BookableHost alloc1 = host("a1", "t", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        Maestro.BookableHost alloc2 = host("a2", "t", "Linux", 100, GB, 0, 0, 100, GB, 0, 0);
        Maestro.BookableHost otherOs = host("a1", "t", "Windows", 100, GB, 0, 0, 100, GB, 0, 0);

        Map<Maestro.HostSpecKey, List<Maestro.BookableHost>> groups =
                Maestro.groupByHostSpec(Arrays.asList(alloc1, alloc2, otherOs));

        assertEquals(3, groups.size());
    }

    // ---- fitsOnHost -------------------------------------------------------

    @Test
    public void fitsOnHostAcceptsExactFit() {
        assertTrue(Maestro.fitsOnHost(layer(CORE, GB, 0, 0), freeHost(CORE, GB, 0, 0)));
        assertTrue(Maestro.fitsOnHost(layer(CORE, GB, 1, GB), freeHost(CORE, GB, 1, GB)));
    }

    @Test
    public void fitsOnHostRejectsWhenAnyDimensionShort() {
        Maestro.LayerCandidate cpu = layer(CORE, GB, 0, 0);
        assertFalse(Maestro.fitsOnHost(cpu, freeHost(CORE - 1, GB, 0, 0)));
        assertFalse(Maestro.fitsOnHost(cpu, freeHost(CORE, GB - 1, 0, 0)));

        Maestro.LayerCandidate gpu = layer(CORE, GB, 1, GB);
        assertFalse(Maestro.fitsOnHost(gpu, freeHost(CORE, GB, 0, GB)));
        assertFalse(Maestro.fitsOnHost(gpu, freeHost(CORE, GB, 1, GB - 1)));
    }

    // ---- classifyFragmentation --------------------------------------------

    @Test
    public void classifyFragmentationSplitsByFirstFailingGate() {
        // cores: an 8-core layer, but no host has more than 4 idle cores.
        List<Maestro.BookableHost> small = Arrays.asList(freeHost(4 * CORE, 100 * GB, 0, 0),
                freeHost(4 * CORE, 100 * GB, 0, 0));
        assertEquals("cores", Maestro.classifyFragmentation(layer(8 * CORE, GB, 0, 0), small));

        // memory: cores fit, but no host has the RAM the layer needs.
        List<Maestro.BookableHost> lowMem = Arrays.asList(freeHost(8 * CORE, 2 * GB, 0, 0));
        assertEquals("memory", Maestro.classifyFragmentation(layer(CORE, 8 * GB, 0, 0), lowMem));

        // gpu: cores and RAM fit, but the layer needs a GPU no host has.
        List<Maestro.BookableHost> noGpu = Arrays.asList(freeHost(8 * CORE, 100 * GB, 0, 0));
        assertEquals("gpu", Maestro.classifyFragmentation(layer(CORE, GB, 1, GB), noGpu));

        // fit: a host fits the layer fully, so it was gated (reservation or license
        // seat); the caller resolves that into held/license.
        List<Maestro.BookableHost> roomy = Arrays.asList(freeHost(8 * CORE, 100 * GB, 2, 4 * GB));
        assertEquals("fit", Maestro.classifyFragmentation(layer(CORE, GB, 1, GB), roomy));
    }

    // ---- strandedWholeCores -----------------------------------------------

    @Test
    public void strandedCountsIdleCoresNoWaiterCanBuy() {
        // Memory-stranded host: 8 cores idle but 1G left, so the waiting
        // 1-core/4G layer cannot buy them. The balanced host next to it sells.
        Maestro.BookableHost stranded = loadedHost(32 * CORE, 128 * GB, 8 * CORE, 1 * GB);
        Maestro.BookableHost roomy = loadedHost(32 * CORE, 128 * GB, 8 * CORE, 64 * GB);
        assertEquals(8, Maestro.strandedWholeCores(Arrays.asList(stranded, roomy),
                Arrays.asList(layer(CORE, 4 * GB, 0, 0))));
    }

    @Test
    public void strandedIsZeroWithoutDemand() {
        // Idle without anything waiting is just idle, and a candidate whose
        // backlog drained this tick no longer counts as demand.
        Maestro.BookableHost hungry = loadedHost(32 * CORE, 128 * GB, 8 * CORE, 1 * GB);
        assertEquals(0, Maestro.strandedWholeCores(Arrays.asList(hungry), new ArrayList<>()));
        Maestro.LayerCandidate drained = layer(CORE, 4 * GB, 0, 0);
        drained.waitingFrameCount = 0;
        assertEquals(0, Maestro.strandedWholeCores(Arrays.asList(hungry), Arrays.asList(drained)));
    }

    @Test
    public void strandedSkipsSubMinimumSlivers() {
        // Below CORE_POINTS_RESERVED_MIN nothing can ever be reserved; such
        // crumbs are a full host's round-off, not stranding.
        Maestro.BookableHost sliver = loadedHost(32 * CORE, 128 * GB, 5, 1 * GB);
        assertEquals(0, Maestro.strandedWholeCores(Arrays.asList(sliver),
                Arrays.asList(layer(CORE, 4 * GB, 0, 0))));
    }

    // ---- computeMaxMore ---------------------------------------------------

    @Test
    public void computeMaxMoreIsBoundedByThePhysicalDimension() {
        // 10 cores idle, 1-core layer, ample memory: 9 additional frames fit.
        assertEquals(9L,
                Maestro.computeMaxMore(freeHost(10 * CORE, 100 * GB, 0, 0), layer(CORE, GB, 0, 0)));
    }

    @Test
    public void computeMaxMoreRespectsJobMaxCores() {
        Maestro.LayerCandidate c = layer(CORE, GB, 0, 0);
        c.jobMaxCores = 3 * CORE; // room for 3 cores total
        // first frame consumes 1 core, leaving room for 2 more.
        assertEquals(2L, Maestro.computeMaxMore(freeHost(10 * CORE, 100 * GB, 0, 0), c));
    }

    @Test
    public void computeMaxMoreRespectsShowBurst() {
        Maestro.LayerCandidate c = layer(CORE, GB, 0, 0);
        c.showBurstCores = 2 * CORE; // room for 2 cores total
        assertEquals(1L, Maestro.computeMaxMore(freeHost(10 * CORE, 100 * GB, 0, 0), c));
    }

    // ---- placementScore ---------------------------------------------------
    //
    // Real E-PVM: score is the marginal rise of a convex cost
    // sum_D W_D * ( e^(after_D/total_D) - e^(before_D/total_D) )
    // with before_D = total_D - idle_D and after_D = before_D + layer.min_D.
    // Lower is better. Weights cores=1, mem=1, gpus=4, gpu_mem=1.

    /** Host with explicit idle resources (idle <= total). */
    private static Maestro.BookableHost loadedHost(int cores, long mem, int coresIdle,
            long memIdle) {
        return host("alloc", "tags", "Linux", coresIdle, memIdle, 0, 0, cores, mem, 0, 0);
    }

    @Test
    public void placementScoreOnEmptyHostIsExpFractionPerDimension() {
        // 4-core/4GB layer on an empty 4-core/4GB host: each dimension goes
        // 0 -> full, so its term is e^1 - 1; cores + mem give 2*(e-1).
        Maestro.LayerCandidate c = layer(4 * CORE, 4 * GB, 0, 0);
        double term = Math.exp(1.0) - 1.0;
        assertEquals(2 * term, Maestro.placementScore(freeHost(4 * CORE, 4 * GB, 0, 0), c), 1e-9);
    }

    @Test
    public void placementScorePrefersLargerEmptyHostForSameFrame() {
        // E-PVM is load-balancing: the same frame is a smaller fraction of a
        // bigger host, so an empty 64-core/64GB host scores LOWER (is filled
        // first) than an empty 4-core/4GB host. This is what stops big hosts
        // from sitting idle under the old absolute-stranding score.
        Maestro.LayerCandidate c = layer(4 * CORE, 4 * GB, 0, 0);
        double small = Maestro.placementScore(freeHost(4 * CORE, 4 * GB, 0, 0), c);
        double big = Maestro.placementScore(freeHost(64 * CORE, 64 * GB, 0, 0), c);
        assertTrue("bigger empty host should score lower", big < small);
        // Exact: 2*(e^(4/64) - 1) on the 64-core host.
        assertEquals(2 * (Math.exp(4.0 / 64.0) - 1.0), big, 1e-9);
    }

    @Test
    public void placementScoreRisesAsAHostFillsUp() {
        // Convexity: adding the same frame to a host that is already loaded
        // costs more than adding it to the same-size empty host, so work
        // spreads across hosts instead of piling onto one.
        Maestro.LayerCandidate c = layer(CORE, GB, 0, 0);
        double empty = Maestro.placementScore(loadedHost(8 * CORE, 8 * GB, 8 * CORE, 8 * GB), c);
        double loaded = Maestro.placementScore(loadedHost(8 * CORE, 8 * GB, 2 * CORE, 2 * GB), c);
        assertTrue("loaded host should score higher than empty", loaded > empty);
    }

    @Test
    public void placementScoreTreatsMemorySaturatedHostAsFull() {
        // A host with idle cores but nearly saturated memory sits high on the
        // memory axis, so its marginal cost is dominated by the steep e^x
        // region, far higher than a balanced host with the same idle cores.
        Maestro.LayerCandidate c = layer(CORE, GB, 0, 0);
        double balanced = Maestro.placementScore(loadedHost(8 * CORE, 8 * GB, 4 * CORE, 4 * GB), c);
        double memTight = Maestro.placementScore(loadedHost(8 * CORE, 8 * GB, 4 * CORE, 1 * GB), c);
        assertTrue("memory-tight host should score higher", memTight > balanced);
    }

    @Test
    public void placementScoreWeightsGpuDimensions() {
        // 1-core/1GB/1-gpu/1GB-gpumem layer on an empty 1-core/1GB/2-gpu/4GB
        // host. Each dimension's term is e^(add/total) - 1:
        // cores : e^1 - 1
        // mem : e^1 - 1
        // gpus : (e^0.5 - 1) * 4 (W_GPUS = 4)
        // gpu_mem : (e^0.25 - 1) * 1
        Maestro.LayerCandidate gpu = layer(CORE, GB, 1, GB);
        double expected = (Math.exp(1.0) - 1.0) + (Math.exp(1.0) - 1.0)
                + 4.0 * (Math.exp(0.5) - 1.0) + 1.0 * (Math.exp(0.25) - 1.0);
        assertEquals(expected, Maestro.placementScore(freeHost(CORE, GB, 2, 4 * GB), gpu), 1e-9);
    }

    @Test
    public void placementScoreDoesNotPenalizeGpuSurplusForNonGpuLayer() {
        // A non-GPU layer adds nothing on the GPU dimensions (add <= 0), so a
        // GPU host's idle GPUs contribute 0 to its score: GPU hosts are
        // protected from non-GPU work by grouping (has_gpu in the spec key),
        // not by the score. The score equals the cores+mem terms only.
        Maestro.LayerCandidate cpu = layer(CORE, GB, 0, 0);
        double expected = 2 * (Math.exp(1.0) - 1.0);
        assertEquals(expected, Maestro.placementScore(freeHost(CORE, GB, 4, 16 * GB), cpu), 1e-9);
    }

    // ---- EASY backfill: hostReadySeconds ----------------------------------

    @Test
    public void hostReadySecondsIsZeroWhenNoCoresNeeded() {
        // The host already has enough free cores for its reserving layer.
        assertEquals(0, Maestro.hostReadySeconds(0, Arrays.asList(new int[] {100, 30})));
        assertEquals(0, Maestro.hostReadySeconds(-100, null));
    }

    @Test
    public void hostReadySecondsReturnsCrossingProcsFinishTime() {
        // Need 2 cores' worth (200 points). Procs free at 10s (1 core) and 30s
        // (1 core); the second crosses the threshold, so the host is ready at 30s.
        List<int[]> procs = Arrays.asList(new int[] {100, 30}, new int[] {100, 10});
        assertEquals(30, Maestro.hostReadySeconds(200, procs));
    }

    @Test
    public void hostReadySecondsStopsAtFirstSufficientProc() {
        // One big proc frees 4 cores at 20s; that alone covers the 3-core need.
        List<int[]> procs = Arrays.asList(new int[] {400, 20}, new int[] {100, 5});
        assertEquals(20, Maestro.hostReadySeconds(300, procs));
    }

    @Test
    public void hostReadySecondsUnknownWhenProcsCannotFreeEnough() {
        // Procs free only 2 cores total but 5 are needed -> never ready.
        List<int[]> procs = Arrays.asList(new int[] {100, 10}, new int[] {100, 20});
        assertEquals(Integer.MAX_VALUE, Maestro.hostReadySeconds(500, procs));
    }

    @Test
    public void hostReadySecondsUnknownWhenNoProcs() {
        assertEquals(Integer.MAX_VALUE, Maestro.hostReadySeconds(100, null));
    }

    @Test
    public void hostReadySecondsUnknownWhenANeededProcHasNoEstimate() {
        // First proc (10s) frees 1 core; the next needed proc has an unknown
        // finish (MAX_VALUE) so the host's ready time is unknown, not optimistic.
        List<int[]> procs = Arrays.asList(new int[] {100, 10}, new int[] {100, Integer.MAX_VALUE});
        assertEquals(Integer.MAX_VALUE, Maestro.hostReadySeconds(200, procs));
    }

    // ---- EASY backfill: backfillFits --------------------------------------

    @Test
    public void backfillFitsWhenFrameFinishesBeforeHostIsNeeded() {
        // Worst-case frame runtime 30s, host free for its owner in 60s -> safe.
        assertTrue(Maestro.backfillFits(true, 30, 60));
        // Exactly equal is allowed (<=).
        assertTrue(Maestro.backfillFits(true, 60, 60));
    }

    @Test
    public void backfillRefusedWhenFrameOutlastsTheReservation() {
        assertFalse(Maestro.backfillFits(true, 90, 60));
    }

    @Test
    public void backfillRefusedWithoutRuntimeHistory() {
        // No estimate -> cannot bound the frame, never borrow a reserved host.
        assertFalse(Maestro.backfillFits(false, 10, 10_000));
    }

    @Test
    public void backfillRefusedWhenHostReadyTimeIsUnknown() {
        assertFalse(Maestro.backfillFits(true, 1, Integer.MAX_VALUE));
    }

    // ---- rss-driven resize: resizeFromLiveMem + LayerLiveMem --------------

    private static final long MPC = 4L * CueUtil.GB; // the 4G/core metric

    /** A ledger that has seen {@code n} frames of the layer at the given rss values. */
    private static LayerLiveMem seen(String layerId, long... rssKbs) {
        LayerLiveMem mem = new LayerLiveMem();
        int i = 0;
        for (long kb : rssKbs) {
            mem.record(Arrays.asList(RunningFrameInfo.newBuilder().setLayerId(layerId)
                    .setFrameId("f" + (i++)).setMaxRss(kb).setRss(kb).build()));
        }
        return mem;
    }

    private static Maestro.LayerCandidate grantLayer(String layerId, boolean threadable,
            int coresMin, int coresMax, long memMinKb) {
        Maestro.LayerCandidate c = layer(coresMin, memMinKb, 0, 0);
        c.layerId = layerId;
        c.threadable = threadable;
        c.layerCoresMax = coresMax;
        return c;
    }

    private static Map<String, long[]> resize(Maestro.LayerCandidate c, LayerLiveMem mem) {
        Map<String, long[]> out = new java.util.HashMap<>();
        Maestro.resizeFromLiveMem(Arrays.asList(c), mem, MPC, out);
        return out;
    }

    @Test
    public void resizeUsesTheMedianOfRecentFrames() {
        // Four frames near 18G: the layer really is an 18G layer -> 5 cores,
        // and the memory Maestro packs with is the observed figure.
        long g18 = 18L * CueUtil.GB;
        Maestro.LayerCandidate c = grantLayer("hog", true, 100, 0, 4L * CueUtil.GB);
        Map<String, long[]> out = resize(c, seen("hog", g18, g18, g18, g18));
        assertEquals(500, c.layerCoresMin);
        assertEquals(g18, c.layerMemMin);
        assertTrue(c.rssProven);
        assertEquals(500, out.get("hog")[0]);
    }

    @Test
    public void oneHaywireProcessCannotResizeTheLayer() {
        // Seven honest 2G frames and one 60G leaker: the median stays 2G, the
        // layer stays at its ask. The leaker is the OOM machinery's problem.
        long g2 = 2L * CueUtil.GB;
        Maestro.LayerCandidate c = grantLayer("leak", true, 100, 0, g2);
        LayerLiveMem mem = seen("leak", g2, g2, g2, g2, g2, g2, g2, 60L * CueUtil.GB);
        resize(c, mem);
        assertEquals(100, c.layerCoresMin);
        assertTrue(c.rssProven);
    }

    @Test
    public void resizeWaitsForEnoughSamples() {
        // Three frames seen (under MIN_SAMPLES): no resize, probe gate armed.
        long g18 = 18L * CueUtil.GB;
        Maestro.LayerCandidate c = grantLayer("young", true, 100, 0, g18);
        resize(c, seen("young", g18, g18, g18));
        assertEquals(100, c.layerCoresMin);
        assertFalse(c.rssProven);
    }

    @Test
    public void resizeNeverTouchesNonThreadable() {
        long g18 = 18L * CueUtil.GB;
        Maestro.LayerCandidate c = grantLayer("ctrl", false, 100, 0, g18);
        resize(c, seen("ctrl", g18, g18, g18, g18));
        assertEquals(100, c.layerCoresMin);
        assertTrue(c.rssProven); // non-threadable is never probed either
    }

    @Test
    public void resizeStopsAtTheLayersMaxCores() {
        long g18 = 18L * CueUtil.GB;
        Maestro.LayerCandidate c = grantLayer("capped", true, 100, 200, g18);
        resize(c, seen("capped", g18, g18, g18, g18));
        assertEquals(200, c.layerCoresMin);
    }

    @Test
    public void wideAskAboveTheMetricIsPreserved() {
        long g18 = 18L * CueUtil.GB;
        Maestro.LayerCandidate c = grantLayer("wide", true, 800, 0, g18);
        resize(c, seen("wide", g18, g18, g18, g18));
        assertEquals(800, c.layerCoresMin);
    }

    @Test
    public void ledgerFoldsPerFramePeaksAndForgetsUnknownLayers() {
        long g18 = 18L * CueUtil.GB;
        LayerLiveMem mem = seen("hog", g18, g18, g18, g18);
        // The same frame reporting a lower rss later must not add a new sample.
        mem.record(Arrays.asList(RunningFrameInfo.newBuilder().setLayerId("hog").setFrameId("f0")
                .setMaxRss(1L * CueUtil.GB).build()));
        assertEquals(g18, mem.typicalRssKb("hog"));
        assertEquals(0, mem.typicalRssKb("never-seen"));
    }

    @Test
    public void oneCoreAskIsGatedRegardlessOfDeclaredMemory() {
        // cores=1 means "let the system decide": with no evidence the layer
        // probes, whatever its declaration claims (declarations are untrusted).
        Maestro.LayerCandidate c = grantLayer("comp", true, 100, 0, 2L * CueUtil.GB);
        resize(c, new LayerLiveMem());
        assertEquals(100, c.layerCoresMin);
        assertFalse(c.rssProven);
    }

    @Test
    public void explicitAskAboveOneBooksAtFullSpeed() {
        // Someone sized this layer (2 cores): never gated, corrected later
        // only upward when evidence arrives.
        Maestro.LayerCandidate c = grantLayer("sized", true, 200, 0, 18L * CueUtil.GB);
        resize(c, new LayerLiveMem());
        assertEquals(200, c.layerCoresMin);
        assertTrue(c.rssProven);
    }

    @Test
    public void metricDerivesFromTheGroupsOwnHosts() {
        // 16 cores / 56G usable = 3.5G per core; an 18G layer sizes to 5.
        long metric =
                Maestro.memPerWholeCoreKb(Arrays.asList(freeHost(1600, 56L * CueUtil.GB, 0, 0)));
        assertEquals(56L * CueUtil.GB / 16, metric);
        long g18 = 18L * CueUtil.GB;
        Maestro.LayerCandidate c = grantLayer("hog", true, 100, 0, g18);
        Map<String, long[]> out = new java.util.HashMap<>();
        Maestro.resizeFromLiveMem(Arrays.asList(c), seen("hog", g18, g18, g18, g18), metric, out);
        assertEquals(500, c.layerCoresMin);
    }

    @Test
    public void fastLayerIsReleasedAfterProbeCompletions() {
        // Memory-heavy but its frames complete faster than the report cycle:
        // a probe's worth of successes with no samples releases the hold.
        Maestro.LayerCandidate c = grantLayer("fast", true, 100, 0, 18L * CueUtil.GB);
        c.frameSuccessCount = 8;
        resize(c, new LayerLiveMem());
        assertEquals(100, c.layerCoresMin);
        assertTrue(c.rssProven);
    }

    // ---- subscription identity --------------------------------------------

    @Test
    public void showCapIsKeyedOnTheSubscriptionNotTheShow() {
        // A show with two allocations holds two subscriptions, each with its own
        // burst and its own int_cores. Sharing one in-tick counter between them
        // let whichever allocation planned first decide the other's cap.
        assertFalse("two allocations of one show must not share a key",
                Maestro.subKey("show", "allocA").equals(Maestro.subKey("show", "allocB")));
        // Same subscription, same key: the in-tick cap and the mirror agree.
        assertEquals(Maestro.subKey("show", "allocA"), Maestro.subKey("show", "allocA"));
        // Different shows on one allocation stay separate too.
        assertFalse(Maestro.subKey("showA", "alloc").equals(Maestro.subKey("showB", "alloc")));
    }

    // ---- tick liveness ----------------------------------------------------

    /**
     * A Maestro whose environment holds a malformed scheduler.* number, so the lazy pool startup on
     * the first tick throws while converting it.
     */
    private static Maestro schedulerWithBadPoolProperty() throws Exception {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("maestro.enabled", "facility");
        env.setProperty("maestro.launch_pool_size", "not-a-number");
        Maestro s = new Maestro();
        Field f = Maestro.class.getDeclaredField("env");
        f.setAccessible(true);
        f.set(s, env);
        return s;
    }

    /** Reads the private tick latch; a stuck one is the failure this guards. */
    private static boolean tickLatchHeld(Maestro s) throws Exception {
        Field flag = Maestro.class.getDeclaredField("tickInFlight");
        flag.setAccessible(true);
        return ((AtomicBoolean) flag.get(s)).get();
    }

    @Test
    public void failedPoolStartupStillReleasesTheTick() throws Exception {
        // Pool startup runs inside the tick's try, so a bad property is caught and
        // the finally clears tickInFlight. Before that, the throw escaped runTick
        // with the flag still set, and every later tick returned at the CAS: the
        // scheduler stopped booking, and stopped logging, for the life of the JVM.
        Maestro s = schedulerWithBadPoolProperty();
        s.runTick();
        assertFalse("a failed tick must leave the latch clear", tickLatchHeld(s));
    }

    @Test
    public void aLaterTickStillRunsAfterAFailedOne() throws Exception {
        // The liveness consequence: tick N+1 must still reach its work and leave
        // the latch clear in turn.
        Maestro s = schedulerWithBadPoolProperty();
        s.runTick();
        s.runTick();
        assertFalse("the latch must stay clear across repeated failures", tickLatchHeld(s));
    }

    // ---- pins ---------------------------------------------------------------

    private static Maestro.BookableHost specHost(String id, String tags) {
        Maestro.BookableHost h = host("alloc", tags + " host" + id, "rhel9", 8 * CORE, 32 * GB, 0,
                0, 8 * CORE, 32 * GB, 0, 0);
        h.hostId = id;
        h.hostName = "host" + id;
        h.pkFacility = "fac";
        return h;
    }

    private static Maestro.LayerCandidate pinnedLayer(String layerId, int waiting) {
        Maestro.LayerCandidate c = layer(CORE, 512L << 10, 0, 0);
        c.layerId = layerId;
        c.waitingFrameCount = waiting;
        return c;
    }

    private static Maestro.PinRow pinRow(String layerId, String hostId, String tags) {
        return new Maestro.PinRow(pinnedLayer(layerId, 30), hostId, tags);
    }

    @Test
    public void attachPinsFilesEachLayerUnderTheGroupsOfItsHosts() {
        Maestro.BookableHost a = specHost("a", "general capa");
        Maestro.BookableHost b = specHost("b", "general capa");
        Maestro.BookableHost c = specHost("c", "general capb");
        Map<String, Maestro.BookableHost> byId = new HashMap<>();
        for (Maestro.BookableHost h : Arrays.asList(a, b, c))
            byId.put(h.hostId, h);
        Set<String> spec = new HashSet<>(Arrays.asList("general", "capa", "capb"));
        Map<String, String> reason = new HashMap<>();
        Map<String, Integer> frames = new HashMap<>();
        List<Maestro.PinRow> rows = Arrays.asList(pinRow("L1", "a", "hosta | hostb | hostc"),
                pinRow("L1", "b", "hosta | hostb | hostc"),
                pinRow("L1", "c", "hosta | hostb | hostc"), pinRow("L2", null, "nosuchhost"),
                pinRow("L3", null, "general | nosuchhost"), pinRow("L4", "zz", "hostzz"));
        Map<Maestro.HostSpecKey, List<Maestro.LayerCandidate>> out =
                Maestro.attachPins(rows, byId, spec, reason, frames);

        // L1 spans two specs: one candidate per group, each with that group's pins.
        List<Maestro.LayerCandidate> inA = out.get(Maestro.hostSpecKey(a));
        List<Maestro.LayerCandidate> inC = out.get(Maestro.hostSpecKey(c));
        assertEquals(1, inA.size());
        assertEquals(Arrays.asList(a, b), inA.get(0).pinnedHosts);
        assertTrue(inA.get(0).pinnedIds.containsAll(Arrays.asList("a", "b")));
        assertEquals(1, inC.size());
        assertEquals(Arrays.asList(c), inC.get(0).pinnedHosts);
        assertEquals(2, out.size());
        // A dead pin waits with its reason; a spec-tagged layer is a group candidate, not dead;
        // a host outside the tick's snapshot resolves nothing.
        assertEquals("no host", reason.get("L2"));
        assertEquals(Integer.valueOf(30), frames.get("L2"));
        assertNull(reason.get("L3"));
        assertEquals("no host", reason.get("L4"));
    }

    @Test
    public void addPinnedSkipsLayersTheGroupHasAndVisitsOnlyIdlePins() {
        Maestro.BookableHost a = specHost("a", "general");
        Maestro.BookableHost b = specHost("b", "general");
        b.coresIdle = 0;
        Maestro.LayerCandidate already = pinnedLayer("L1", 10);
        List<Maestro.LayerCandidate> candidates = new ArrayList<>(Arrays.asList(already));
        Maestro.LayerCandidate dup = pinnedLayer("L1", 10);
        Maestro.LayerCandidate pinned = pinnedLayer("L4", 10);
        for (Maestro.LayerCandidate c : Arrays.asList(dup, pinned)) {
            c.pinnedHosts = new ArrayList<>(Arrays.asList(a, b));
            c.pinnedIds = new HashSet<>(Arrays.asList("a", "b"));
        }
        Maestro.addPinned(candidates, Arrays.asList(dup, pinned), Arrays.asList(a));
        assertEquals(2, candidates.size());
        assertSame(already, candidates.get(0));
        assertSame(pinned, candidates.get(1));
        assertEquals(Arrays.asList(a), pinned.pinnedIdle);
        assertNull(already.pinnedIdle);
        // A pinned candidate wants only its own hosts; an unpinned one wants any.
        Maestro.BookableHost other = specHost("z", "general");
        assertTrue(Maestro.pinsAllow(pinned, a));
        assertFalse(Maestro.pinsAllow(pinned, other));
        assertTrue(Maestro.pinsAllow(already, other));
        assertTrue(
                Maestro.namesSpecTag("general | hosta", new HashSet<>(Arrays.asList("general"))));
        assertFalse(Maestro.namesSpecTag("hosta | hostb", new HashSet<>(Arrays.asList("general"))));
    }

    // ---- the slot draw and the tick-wide backlog --------------------------

    private static Maestro.LayerCandidate candidate(String layerId, int priority, int waiting) {
        Maestro.LayerCandidate c = new Maestro.LayerCandidate();
        c.layerId = layerId;
        c.priority = priority;
        c.waitingFrameCount = waiting;
        return c;
    }

    @Test
    public void aSlotGoesToTheCandidateWhoseWeightBandHoldsTheDraw() {
        // Bands laid end to end in list order: [0,100) [100,400) [400,401); a
        // priority of zero weighs one, like the query's GREATEST, and a draw
        // past the last band stays on the last candidate.
        List<Maestro.LayerCandidate> active =
                Arrays.asList(candidate("a", 100, 1), candidate("b", 300, 1), candidate("c", 0, 1));
        assertEquals(0, Maestro.drawSlot(active, 0));
        assertEquals(0, Maestro.drawSlot(active, 99));
        assertEquals(1, Maestro.drawSlot(active, 100));
        assertEquals(1, Maestro.drawSlot(active, 399));
        assertEquals(2, Maestro.drawSlot(active, 400));
        assertEquals(2, Maestro.drawSlot(active, 1000));
    }

    @Test
    public void aLayerPlannedInAnEarlierGroupKeepsOnlyItsRemainder() {
        Maestro.LayerCandidate planned = candidate("a", 100, 10);
        planned.placedThisTick = true;
        Maestro.LayerCandidate fresh = candidate("b", 100, 7);
        Map<String, Integer> plannedByLayer = new HashMap<>();
        plannedByLayer.put("a", 4);
        Set<String> seen = new HashSet<>();
        Maestro.takeTickWideRemainder(Arrays.asList(planned, fresh), plannedByLayer, seen);
        assertEquals("the frames planned in the earlier group are gone", 6,
                planned.waitingFrameCount);
        assertEquals("an unplanned layer keeps its whole backlog", 7, fresh.waitingFrameCount);
        assertFalse("the placement flag starts the group clear", planned.placedThisTick);
        assertEquals(new HashSet<>(Arrays.asList("a", "b")), seen);
    }

    // ---- the commit chunks and the leader ---------------------------------

    private static FrameBooking bookingOn(String hostId) {
        VirtualProc p = new VirtualProc();
        p.hostId = hostId;
        return new FrameBooking(new DispatchFrame(), p);
    }

    @Test
    public void aChunkNeverSplitsAHost() {
        // 3 on host a, 499 on host b, 2 on host c: the cut at COMMIT_CHUNK_FRAMES
        // falls inside host b and moves to its last booking.
        List<FrameBooking> planned = new ArrayList<>();
        for (int i = 0; i < 3; i++)
            planned.add(bookingOn("a"));
        for (int i = 0; i < 499; i++)
            planned.add(bookingOn("b"));
        for (int i = 0; i < 2; i++)
            planned.add(bookingOn("c"));
        int end = Maestro.chunkEnd(planned, 0);
        assertEquals(502, end);
        assertEquals("the next chunk starts on a new host", "c", planned.get(end).proc.hostId);
        assertEquals(504, Maestro.chunkEnd(planned, end));
    }

    private static void set(Maestro s, String field, Object value) throws Exception {
        Field f = Maestro.class.getDeclaredField(field);
        f.setAccessible(true);
        f.set(s, value);
    }

    /**
     * A Maestro whose lock connection is the given one and whose transaction template runs its
     * callbacks straight through a mocked manager, so a chunk that reaches the commit really calls
     * the batch start.
     */
    private static Maestro schedulerWithLeaderConn(Connection conn) throws Exception {
        Maestro s = new Maestro();
        set(s, "leaderConn", conn);
        set(s, "transactionManager", mock(PlatformTransactionManager.class));
        return s;
    }

    @Test
    public void aLeaderThatLostTheLockCommitsNoFurtherChunk() throws Exception {
        Connection lost = mock(Connection.class);
        // A closed connection is a definite loss: the session, and with it the
        // advisory lock, is gone. No probe tolerance applies.
        when(lost.isClosed()).thenReturn(true);
        when(lost.isValid(anyInt())).thenReturn(false);
        when(lost.prepareStatement(anyString())).thenReturn(mock(PreparedStatement.class));
        Maestro s = schedulerWithLeaderConn(lost);
        DispatchSupport support = mock(DispatchSupport.class);
        s.setDispatchSupport(support);
        List<FrameBooking> committed = s.commitInChunks(Arrays.asList(bookingOn("a")));
        assertTrue("nothing commits without the lock", committed.isEmpty());
        verify(support, never()).startFramesAndProcsBatch(any());
    }

    @Test
    public void aLeaderThatHoldsTheLockCommitsTheChunk() throws Exception {
        Connection held = mock(Connection.class);
        when(held.isValid(anyInt())).thenReturn(true);
        Maestro s = schedulerWithLeaderConn(held);
        DispatchSupport support = mock(DispatchSupport.class);
        s.setDispatchSupport(support);
        s.commitInChunks(Arrays.asList(bookingOn("a")));
        verify(support).startFramesAndProcsBatch(any());
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> map(Maestro s, String field) throws Exception {
        Field f = Maestro.class.getDeclaredField(field);
        f.setAccessible(true);
        return (Map<String, Object>) f.get(s);
    }

    @Test
    public void aLostLockTakesThePlannersMemoryWithIt() throws Exception {
        Maestro s = schedulerWithLeaderConn(null);
        String[] fields = {"reservations", "blockedDebtMs", "lastSeenMs", "warmthByHostLayer",
                "bookingsByHost"};
        for (String f : fields)
            map(s, f).put("stale", f.equals("reservations") ? null : Long.valueOf(1L));
        s.demote();
        for (String f : fields)
            assertTrue(f + " must not outlive the lock", map(s, f).isEmpty());
    }

    // ---- the launch of one booking ----------------------------------------

    @Test
    public void anUnknownLaunchOutcomeIsResolvedBeforeAnyRelease() {
        Maestro s = new Maestro();
        DispatchSupport support = mock(DispatchSupport.class);
        RqdClient rqd = mock(RqdClient.class);
        s.setDispatchSupport(support);
        s.setRqdClient(rqd);
        FrameBooking fb = bookingOn("a");
        doThrow(new RqdLaunchUnknownOutcomeException("deadline", null)).when(support)
                .runFrame(any(), any());
        s.launchOne(fb);
        verify(support).resolveUnknownLaunchOutcome(fb.proc, fb.frame);
        verify(support, never()).unbookProc(any());
        verify(support, never()).clearFrame(any());
        verify(rqd, never()).killFrame(any(VirtualProc.class), any());
    }

    @Test
    public void aDefiniteLaunchFailureRollsTheBookingBack() {
        Maestro s = new Maestro();
        DispatchSupport support = mock(DispatchSupport.class);
        RqdClient rqd = mock(RqdClient.class);
        s.setDispatchSupport(support);
        s.setRqdClient(rqd);
        FrameBooking fb = bookingOn("a");
        doThrow(new DispatcherException("refused")).when(support).runFrame(any(), any());
        when(support.clearFrame(fb.frame)).thenReturn(true);
        s.launchOne(fb);
        verify(support, never()).resolveUnknownLaunchOutcome(any(), any());
        InOrder release = inOrder(support, rqd);
        release.verify(support).unbookProc(fb.proc);
        release.verify(support).clearFrame(fb.frame);
        release.verify(rqd).killFrame(eq(fb.proc), any());
    }

    // ---- the second review pass: each finding with the test that failed first ----

    @SuppressWarnings("unchecked")
    private static Map<String, long[]> deltas(Maestro s, String field) throws Exception {
        Field f = Maestro.class.getDeclaredField(field);
        f.setAccessible(true);
        return (Map<String, long[]>) f.get(s);
    }

    @Test
    public void aFailedChunkLeavesNoDeltasForTheNext() throws Exception {
        // A flush that throws inside the chunk's transaction leaves the deltas
        // it had not drained in the buffers; they must not be credited by the
        // next chunk to procs that never existed.
        Connection held = mock(Connection.class);
        when(held.isValid(anyInt())).thenReturn(true);
        Maestro s = schedulerWithLeaderConn(held);
        DispatchSupport support = mock(DispatchSupport.class);
        when(support.startFramesAndProcsBatch(any()))
                .thenThrow(new RuntimeException("flush deadlock"));
        s.setDispatchSupport(support);
        String[] buffers = {"subDeltas", "layerDeltas", "jobDeltas"};
        for (String b : buffers)
            deltas(s, b).put("left by the failed flush", new long[] {1, 2});
        assertTrue(s.commitInChunks(Arrays.asList(bookingOn("a"))).isEmpty());
        for (String b : buffers)
            assertTrue(b + " must not reach the next chunk", deltas(s, b).isEmpty());
    }

    @Test
    @SuppressWarnings("unchecked")
    public void aLockLostBetweenChunksStopsAtTheBoundaryAndDemotes() throws Exception {
        Connection conn = mock(Connection.class);
        // The connection closes between the chunks: a definite loss, which
        // demotes at the next boundary with no probe tolerance.
        when(conn.isClosed()).thenReturn(false, true);
        when(conn.isValid(anyInt())).thenReturn(true, false);
        when(conn.prepareStatement(anyString())).thenReturn(mock(PreparedStatement.class));
        Maestro s = schedulerWithLeaderConn(conn);
        DispatchSupport support = mock(DispatchSupport.class);
        s.setDispatchSupport(support);
        map(s, "reservations").put("stale", null);
        List<FrameBooking> planned = new ArrayList<>();
        for (int i = 0; i < 3; i++)
            planned.add(bookingOn("a"));
        for (int i = 0; i < 499; i++)
            planned.add(bookingOn("b"));
        for (int i = 0; i < 2; i++)
            planned.add(bookingOn("c"));
        s.commitInChunks(planned);
        ArgumentCaptor<List<FrameBooking>> chunk = ArgumentCaptor.forClass(List.class);
        verify(support, times(1)).startFramesAndProcsBatch(chunk.capture());
        assertEquals("the first chunk, whole, before the lock went", 502, chunk.getValue().size());
        assertTrue("the memory went with the lock", map(s, "reservations").isEmpty());
    }

    @Test
    public void aSingleProbeMissKeepsTheLockAndTheMemory() throws Exception {
        // isValid times out once on a loaded server, then recovers. One blip
        // must not cost the leadership and every live reservation.
        Connection conn = mock(Connection.class);
        when(conn.isValid(anyInt())).thenReturn(false, true);
        Maestro s = schedulerWithLeaderConn(conn);
        DispatchSupport support = mock(DispatchSupport.class);
        s.setDispatchSupport(support);
        map(s, "reservations").put("mine", null);
        List<FrameBooking> planned = new ArrayList<>();
        for (int i = 0; i < 500; i++)
            planned.add(bookingOn("a"));
        planned.add(bookingOn("b"));
        s.commitInChunks(planned);
        verify(support, times(2)).startFramesAndProcsBatch(any());
        assertEquals("one miss keeps the planner's memory", 1, map(s, "reservations").size());
    }

    @Test
    public void twoConsecutiveProbeMissesDemote() throws Exception {
        Connection conn = mock(Connection.class);
        when(conn.isValid(anyInt())).thenReturn(false, false);
        when(conn.prepareStatement(anyString())).thenReturn(mock(PreparedStatement.class));
        Maestro s = schedulerWithLeaderConn(conn);
        DispatchSupport support = mock(DispatchSupport.class);
        s.setDispatchSupport(support);
        map(s, "reservations").put("stale", null);
        List<FrameBooking> planned = new ArrayList<>();
        for (int i = 0; i < 500; i++)
            planned.add(bookingOn("a"));
        planned.add(bookingOn("b"));
        s.commitInChunks(planned);
        verify(support, times(1)).startFramesAndProcsBatch(any());
        assertTrue("the second consecutive miss demotes", map(s, "reservations").isEmpty());
    }

    @Test
    public void onShutdownLeavesThePlannersMemoryToTheTickThread() throws Exception {
        Maestro s = schedulerWithLeaderConn(null);
        map(s, "reservations").put("mine", null);
        s.onShutdown();
        assertEquals("the shutdown thread never touches the tick's maps", 1,
                map(s, "reservations").size());
    }

    @Test
    public void onShutdownWaitsForTheTickInFlight() throws Exception {
        Maestro s = schedulerWithLeaderConn(null);
        Field f = Maestro.class.getDeclaredField("tickInFlight");
        f.setAccessible(true);
        AtomicBoolean inFlight = (AtomicBoolean) f.get(s);
        inFlight.set(true);
        Thread tick = new Thread(() -> {
            try {
                Thread.sleep(300);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            inFlight.set(false);
        });
        long t0 = System.currentTimeMillis();
        tick.start();
        s.onShutdown();
        assertFalse("shutdown returned only after the tick ended", inFlight.get());
        assertTrue("shutdown waited for the tick to end", System.currentTimeMillis() - t0 >= 250);
        tick.join();
    }

    @Test
    public void aTickThatRacesTheShutdownTakesNoLeadership() throws Exception {
        // The shutdown thread released the lock; the tick in flight must not
        // take it back on a fresh connection and commit into the JVM going down.
        Connection fresh = mock(Connection.class);
        when(fresh.isValid(anyInt())).thenReturn(true);
        when(fresh.prepareStatement(anyString())).thenReturn(mock(PreparedStatement.class));
        Maestro s = schedulerWithLeaderConn(null);
        DispatchSupport support = mock(DispatchSupport.class);
        s.setDispatchSupport(support);
        s.onShutdown();
        assertFalse("no leadership while shutting down", s.ensureLeadership());
        set(s, "leaderConn", fresh);
        assertTrue(s.commitInChunks(Arrays.asList(bookingOn("a"))).isEmpty());
        verify(support, never()).startFramesAndProcsBatch(any());
    }

    @Test
    public void anUnknownLaunchOutcomeWhoseResolutionFailsKeepsTheBooking() {
        Maestro s = new Maestro();
        DispatchSupport support = mock(DispatchSupport.class);
        RqdClient rqd = mock(RqdClient.class);
        s.setDispatchSupport(support);
        s.setRqdClient(rqd);
        FrameBooking fb = bookingOn("a");
        doThrow(new RqdLaunchUnknownOutcomeException("deadline", null)).when(support)
                .runFrame(any(), any());
        doThrow(new RuntimeException("rqd unreachable")).when(support)
                .resolveUnknownLaunchOutcome(any(), any());
        s.launchOne(fb);
        verify(support, never()).unbookProc(any());
        verify(support, never()).clearFrame(any());
        verify(rqd, never()).killFrame(any(VirtualProc.class), any());
    }

    @Test
    public void aLaunchThatWaitedTooLongIsRolledBackUnsent() {
        // Past half the orphan age the maintenance pass may have released the
        // proc and the frame may run elsewhere: never sent, never killed.
        Maestro s = new Maestro();
        DispatchSupport support = mock(DispatchSupport.class);
        RqdClient rqd = mock(RqdClient.class);
        s.setDispatchSupport(support);
        s.setRqdClient(rqd);
        FrameBooking fb = bookingOn("a");
        when(support.clearFrame(fb.frame)).thenReturn(true);
        fb.committedMs = System.currentTimeMillis() - Maestro.LAUNCH_MAX_AGE_MS - 1000;
        s.launchOne(fb);
        verify(support, never()).runFrame(any(), any());
        verify(support).unbookProc(fb.proc);
        verify(support).clearFrame(fb.frame);
        verify(rqd, never()).killFrame(any(VirtualProc.class), any());
        assertTrue("the bound stays inside the orphan age",
                Maestro.LAUNCH_MAX_AGE_MS < ProcDao.ORPHAN_AGE_SECONDS * 1000L);
    }

    @Test
    public void aRollbackWhoseClearMissedNeverKills() {
        // The clear matched no row: the frame moved on to another run, and a
        // kill addressed by host and frame would hit that run.
        Maestro s = new Maestro();
        DispatchSupport support = mock(DispatchSupport.class);
        RqdClient rqd = mock(RqdClient.class);
        s.setDispatchSupport(support);
        s.setRqdClient(rqd);
        FrameBooking fb = bookingOn("a");
        doThrow(new DispatcherException("refused")).when(support).runFrame(any(), any());
        when(support.clearFrame(fb.frame)).thenReturn(false);
        s.launchOne(fb);
        verify(support).unbookProc(fb.proc);
        verify(rqd, never()).killFrame(any(VirtualProc.class), any());
    }

    @Test
    public void aCutOnAHostBoundaryDoesNotExtend() {
        List<FrameBooking> planned = new ArrayList<>();
        for (int i = 0; i < Maestro.COMMIT_CHUNK_FRAMES; i++)
            planned.add(bookingOn("a"));
        planned.add(bookingOn("b"));
        assertEquals(Maestro.COMMIT_CHUNK_FRAMES, Maestro.chunkEnd(planned, 0));
        List<FrameBooking> one = new ArrayList<>();
        for (int i = 0; i < 1200; i++)
            one.add(bookingOn("a"));
        assertEquals("one host is one chunk however large", 1200, Maestro.chunkEnd(one, 0));
    }

    @Test
    public void aLayerThatBookedItsWholeBacklogEntersWithNothing() {
        Maestro.LayerCandidate c = candidate("a", 100, 10);
        Map<String, Integer> plannedByLayer = new HashMap<>();
        plannedByLayer.put("a", 10);
        Maestro.takeTickWideRemainder(Arrays.asList(c), plannedByLayer, new HashSet<>());
        assertEquals(0, c.waitingFrameCount);
    }

    private static QueuedFrameCompletion completionOn(String hostId, String layerId) {
        VirtualProc p = new VirtualProc();
        p.hostId = hostId;
        p.layerId = layerId;
        p.coresReserved = 100;
        DispatchFrame f = new DispatchFrame();
        f.show = "show";
        return new QueuedFrameCompletion(FrameCompleteReport.getDefaultInstance(), p,
                new DispatchJob(), new LayerDetail(), new FrameDetail(), f, FrameState.SUCCEEDED,
                0);
    }

    /** A Maestro whose drain wins every stop and hands the post-ops to a mocked handler. */
    private static Maestro drainingScheduler(Connection conn) throws Exception {
        Maestro s = schedulerWithLeaderConn(conn);
        DispatchSupport support = mock(DispatchSupport.class);
        when(support.stopFramesBatch(any())).thenAnswer(i -> {
            boolean[] won = new boolean[((List<?>) i.getArgument(0)).size()];
            java.util.Arrays.fill(won, true);
            return won;
        });
        s.setDispatchSupport(support);
        s.setFrameCompleteHandler(mock(FrameCompleteHandler.class));
        set(s, "localityWindowFrames", 64);
        return s;
    }

    @Test
    public void aStandbyDrainStampsNoWarmth() throws Exception {
        MaestroCompletionQueue.drain();
        Maestro s = drainingScheduler(null);
        MaestroCompletionQueue.offer(completionOn("h", "l"));
        s.drainResolvedCompletions();
        assertTrue("a standby has no odometer to stamp against",
                map(s, "warmthByHostLayer").isEmpty());
    }

    @Test
    public void theLeadersDrainStampsWarmth() throws Exception {
        MaestroCompletionQueue.drain();
        Maestro s = drainingScheduler(mock(Connection.class));
        MaestroCompletionQueue.offer(completionOn("h", "l"));
        s.drainResolvedCompletions();
        assertTrue(map(s, "warmthByHostLayer").containsKey("h|l"));
    }

    @Test
    @SuppressWarnings("unchecked")
    public void aDeletedLayerCostsOnlyItsOwnSlice() throws Exception {
        // Two layers vanish mid-tick on the host: the third still plans, and
        // the two failures are counted once for the tick, not warned per layer.
        Maestro s = new Maestro();
        set(s, "env", new MockEnvironment());
        ExecutorService pool = Executors.newFixedThreadPool(1);
        set(s, "readPool", pool);
        try {
            HostManager hosts = mock(HostManager.class);
            when(hosts.getDispatchHost("host1")).thenReturn(new DispatchHost());
            JobManager jobs = mock(JobManager.class);
            LayerInterface good = mock(LayerInterface.class);
            when(jobs.getLayer("gone")).thenThrow(new RuntimeException("no such layer"));
            when(jobs.getLayer("gone2")).thenThrow(new RuntimeException("no such layer"));
            when(jobs.getLayer("good")).thenReturn(good);
            Dispatcher dispatcher = mock(Dispatcher.class);
            when(dispatcher.planHost(any(), eq(good), anyInt(), anyLong(), anyInt(), anyInt()))
                    .thenReturn(Arrays.asList(bookingOn("host1")));
            s.setHostManager(hosts);
            s.setJobManager(jobs);
            s.setDispatcher(dispatcher);
            ((Map<String, List<String>>) (Map<?, ?>) map(s, "plannedByHost")).put("host1",
                    new ArrayList<>(Arrays.asList("gone", "good", "gone2")));
            List<FrameBooking> planned = s.planBookings();
            assertEquals("the host's other layer stands", 1, planned.size());
            Field f = Maestro.class.getDeclaredField("summaryPlanFailures");
            f.setAccessible(true);
            assertEquals("both failures counted for the tick's one report", 2, f.getInt(s));
        } finally {
            pool.shutdownNow();
        }
    }
}
