
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

package com.imageworks.spcue.test.util;

import junit.framework.TestCase;
import org.junit.Before;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.EntityException;
import com.imageworks.spcue.JobDispatchException;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dispatcher.Dispatcher;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.util.CueUtil;

/**
 * Characterization tests for {@link VirtualProc#build(DispatchHost, DispatchFrame, String...)}.
 *
 * Pin every observable branch of the current implementation. Used as a safety net for a subsequent
 * readability-only refactor of the method body.
 */
public class VirtualProcBuildTests extends TestCase {

    DispatchHost host;

    @Before
    public void setUp() throws Exception {
        host = new DispatchHost();
        host.isNimby = false;
    }

    private DispatchFrame newThreadableFrame(int minCores, long minMemory) {
        DispatchFrame frame = new DispatchFrame();
        frame.minCores = minCores;
        frame.setMinMemory(minMemory);
        frame.threadable = true;
        return frame;
    }

    // ---------- Zero / negative core requests ----------

    public void testBooksAllCoresWhenMinCoresIsZero() {
        host.cores = 800;
        host.idleCores = 800;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 0;
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(800, proc.coresReserved);
    }

    public void testBooksAllMinusNWhenMinCoresNegativeAndHostFullyIdle() {
        host.cores = 800;
        host.idleCores = 800;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = -100;
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        // host.cores + minCores = 800 + (-100) = 700.
        assertEquals(700, proc.coresReserved);
        assertTrue(proc.canHandleNegativeCoresRequest);
    }

    public void testNegativeMinCoresFlagsHostBusyWhenNotFullyIdle() {
        host.cores = 800;
        host.idleCores = 400;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = -100;
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        // coresReserved is still computed; only the flag flips off.
        assertEquals(700, proc.coresReserved);
        assertFalse(proc.canHandleNegativeCoresRequest);
    }

    // ---------- Stranded cores ----------

    public void testStrandedCoresAreAddedToReservation() {
        // strandedCores=200 pushes a 100-core request up to 300. Memory inflation via
        // getCoreSpan returns 100 (small frame relative to per-core memory), so the
        // never-below-original floor keeps the result at 300.
        host.strandedCores = 200;
        host.cores = 800;
        host.idleCores = 800;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(300, proc.coresReserved);
    }

    // ---------- Fractional idle cores ----------

    public void testFractionalIdleCoresThrowsEntityException() {
        host.cores = 800;
        host.idleCores = 50;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);

        try {
            VirtualProc.build(host, frame);
            fail("Expected EntityException for fractional idle cores");
        } catch (EntityException expected) {
            // ok
        }
    }

    // ---------- ThreadMode.ALL ----------

    public void testThreadModeAllBooksAllWholeIdleCores() {
        host.threadMode = ThreadMode.ALL_VALUE;
        host.cores = 800;
        host.idleCores = 750;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);

        VirtualProc proc = VirtualProc.build(host, frame);
        // floor(750/100) * 100 = 700
        assertEquals(700, proc.coresReserved);
    }

    // ---------- Selfish service short-circuit ----------

    public void testSelfishServiceBooksAllWholeCores() {
        host.threadMode = ThreadMode.AUTO_VALUE;
        host.cores = 800;
        host.idleCores = 700;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB16;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);
        frame.services = "shell,arnold";

        VirtualProc proc = VirtualProc.build(host, frame, "arnold");
        // wholeCores * 100 = 7 * 100 = 700
        assertEquals(700, proc.coresReserved);
    }

    public void testNonSelfishServiceFallsThroughToMemoryBranch() {
        host.threadMode = ThreadMode.AUTO_VALUE;
        host.cores = 800;
        host.idleCores = 700;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB16;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);
        frame.services = "shell";

        // No selfish match. idleMemory(GB16) - minMemory(GB) = GB15, well above the
        // stranded threshold, so getCoreSpan drives the result: memPerCore = GB16/8 =
        // GB2, procs = GB/GB2 = 0.5, rounds to 1, reserveCores = 100.
        VirtualProc proc = VirtualProc.build(host, frame, "arnold");
        assertEquals(100, proc.coresReserved);
    }

    public void testSelfishWithNullServicesDoesNotShortCircuit() {
        host.threadMode = ThreadMode.AUTO_VALUE;
        host.cores = 800;
        host.idleCores = 700;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB16;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);
        // frame.services left null.

        VirtualProc proc = VirtualProc.build(host, frame, "arnold");
        // Same getCoreSpan result as above.
        assertEquals(100, proc.coresReserved);
    }

    // ---------- Memory stranded threshold ----------

    public void testMemoryStrandedThresholdBooksAllWholeCores() {
        // idleMemory - minMemory = GB8 - GB7 = GB, which is <= MEM_STRANDED_THRESHHOLD
        // (GB + MB512).
        host.threadMode = ThreadMode.AUTO_VALUE;
        host.cores = 800;
        host.idleCores = 700;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;
        assertTrue(host.idleMemory - (CueUtil.GB * 7) <= Dispatcher.MEM_STRANDED_THRESHHOLD);

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB * 7);

        VirtualProc proc = VirtualProc.build(host, frame);
        // wholeCores * 100 = 7 * 100 = 700
        assertEquals(700, proc.coresReserved);
    }

    public void testMemoryProportionalSpanWhenNotStranded() {
        // idleMemory(GB8) - minMemory(~3.2GB) ≈ 4.8GB > threshold, so getCoreSpan runs.
        host.threadMode = ThreadMode.AUTO_VALUE;
        host.cores = 800;
        host.idleCores = 780;
        host.memory = CueUtil.GB8;
        host.idleMemory = CueUtil.GB8;
        long minMemory = 3355443L; // ~3.2 GB

        DispatchFrame frame = newThreadableFrame(100, minMemory);

        VirtualProc proc = VirtualProc.build(host, frame);
        // memPerCore = GB8/8 = GB; procs = 3355443/GB ≈ 3.2; round=3; reserveCores=300.
        assertEquals(300, proc.coresReserved);
    }

    // ---------- ThreadMode.VARIABLE ----------

    public void testVariableThreadModeFloorsAtTwoCores() {
        // Base reservation lands at or below 200 (memory-proportional with tiny
        // minMemory yields 0), so the VARIABLE floor pushes to 200.
        host.threadMode = ThreadMode.VARIABLE_VALUE;
        host.cores = 800;
        host.idleCores = 400;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB32;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.MB128);

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(200, proc.coresReserved);
    }

    public void testVariableThreadModeFloorThrowsWhenIdleBelowTwoCores() {
        // wholeCores == 1, memory-stranded path lands at 100, floor bumps to 200,
        // 200 > idleCores(150) -> first JobDispatchException raise site.
        host.threadMode = ThreadMode.VARIABLE_VALUE;
        host.cores = 800;
        host.idleCores = 150;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);

        try {
            VirtualProc.build(host, frame);
            fail("Expected JobDispatchException from the VARIABLE floor + idle check");
        } catch (JobDispatchException expected) {
            // ok
        }
    }

    public void testVariableThreadModeFinalClampThrowsWhenSingleCoreHost() {
        // wholeCores == 1, getCoreSpan returns 400 (> 200, skipping the floor), then
        // the final >idleCores clamp triggers the second JobDispatchException raise.
        host.threadMode = ThreadMode.VARIABLE_VALUE;
        host.cores = 800;
        host.idleCores = 100;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB16;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB * 8);

        try {
            VirtualProc.build(host, frame);
            fail("Expected JobDispatchException from the final idle-cores clamp");
        } catch (JobDispatchException expected) {
            // ok
        }
    }

    // ---------- Sanity / never-below-original / maxCores ----------

    public void testNeverFallsBelowOriginalRequest() {
        // originalCores = 400, getCoreSpan would return 100, but the never-below-original
        // floor bumps the result back to 400.
        host.threadMode = ThreadMode.AUTO_VALUE;
        host.cores = 800;
        host.idleCores = 800;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;

        DispatchFrame frame = newThreadableFrame(400, CueUtil.GB);

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(400, proc.coresReserved);
    }

    public void testMaxCoresCapsReservation() {
        // ThreadMode.ALL would book all 800 cores; maxCores=200 clamps the result.
        host.threadMode = ThreadMode.ALL_VALUE;
        host.cores = 800;
        host.idleCores = 800;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);
        frame.maxCores = 200;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(200, proc.coresReserved);
    }

    public void testFinalClampWhenExceedsIdleCores() {
        // getCoreSpan returns 400 but idleCores only allows 200, so the final clamp
        // overrides via wholeCores * 100.
        host.threadMode = ThreadMode.AUTO_VALUE;
        host.cores = 800;
        host.idleCores = 200;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB16;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB * 8);

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(200, proc.coresReserved);
    }

    public void testSanityFloorYieldsAtLeastHundredWhenSpanReturnsZero() {
        // Tiny minMemory makes getCoreSpan round to 0; the <100 sanity floor and the
        // never-below-original floor both push the result back to 100 (the entry
        // condition requires originalCores >= 100, so the two floors converge here).
        host.threadMode = ThreadMode.AUTO_VALUE;
        host.cores = 800;
        host.idleCores = 800;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB16;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.MB128);

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(100, proc.coresReserved);
    }

    // ---------- Non-threadable cap ----------

    public void testNonThreadableCappedAtHundred() {
        host.threadMode = ThreadMode.ALL_VALUE;
        host.cores = 800;
        host.idleCores = 800;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 400;
        frame.setMinMemory(CueUtil.GB);
        frame.threadable = false;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(100, proc.coresReserved);
    }

    // ---------- Field propagation ----------

    public void testFieldsArePropagatedFromHostAndFrame() {
        host.id = "host-id-1";
        host.name = "host-name-1";
        host.allocationId = "alloc-id-1";
        host.isLocalDispatch = true;
        host.cores = 800;
        host.idleCores = 800;
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;
        host.threadMode = ThreadMode.ALL_VALUE;

        DispatchFrame frame = newThreadableFrame(100, CueUtil.GB);
        frame.layerId = "layer-id-1";
        frame.jobId = "job-id-1";
        frame.showId = "show-id-1";
        frame.facilityId = "facility-id-1";
        frame.os = "linux";
        frame.minGpus = 2;
        frame.minGpuMemory = CueUtil.GB2;

        VirtualProc proc = VirtualProc.build(host, frame);

        assertEquals("host-id-1", proc.hostId);
        assertEquals("host-name-1", proc.hostName);
        assertEquals("alloc-id-1", proc.allocationId);
        assertTrue(proc.isLocalDispatch);
        assertNull(proc.frameId);
        assertEquals("layer-id-1", proc.layerId);
        assertEquals("job-id-1", proc.jobId);
        assertEquals("show-id-1", proc.showId);
        assertEquals("facility-id-1", proc.facilityId);
        assertEquals("linux", proc.os);
        assertEquals(CueUtil.GB, proc.memoryReserved);
        assertEquals(2, proc.gpusReserved);
        assertEquals(CueUtil.GB2, proc.gpuMemoryReserved);
        assertFalse(proc.unbooked);
    }
}
