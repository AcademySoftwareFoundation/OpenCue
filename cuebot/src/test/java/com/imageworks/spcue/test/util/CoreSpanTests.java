
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
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.util.CueUtil;

public class CoreSpanTests extends TestCase {

    DispatchHost host;

    @Before
    public void setUp() throws Exception {
        host = new DispatchHost();
        host.isNimby = false;
    }

    /**
     * The coreSpan calculation finds out how many cores a frames's requested memory covers and
     * gives more cores when the requested memory spans more than 1 core.
     */
    public void testCoreSpan() {

        /* 8 gigs and 7 cores idle, request 7g */
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;
        host.cores = 800;
        host.idleCores = 700;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 100;
        frame.setMinMemory(CueUtil.GB * 7);
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(700, proc.coresReserved);
    }

    public void testCoreSpanTest1() {

        /* 4 gigs and 1 cores idle, request 1g */
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB4;
        host.cores = 800;
        host.idleCores = 100;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 100;
        frame.setMinMemory(CueUtil.GB);

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(100, proc.coresReserved);
    }

    public void testCoreSpanTest2() {
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB4;
        host.cores = 800;
        host.idleCores = 200;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 100;
        frame.setMinMemory(CueUtil.GB4);
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(200, proc.coresReserved);
    }

    public void testCoreSpanTest3() {
        host.memory = CueUtil.GB8;
        host.idleMemory = CueUtil.GB8;
        host.cores = 800;
        host.idleCores = 780;
        // Hardcoded value of dispatcher.memory.mem_reserved_default
        // to avoid having to read opencue.properties on a test setting
        long memReservedDefault = 3355443;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 100;
        frame.setMinMemory(memReservedDefault);
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(300, proc.coresReserved);
    }

    public void testCoreSpanTest4() {
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB16;
        host.cores = 800;
        host.idleCores = 200;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 100;
        frame.setMinMemory(CueUtil.GB * 8);
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(200, proc.coresReserved);

    }

    /**
     * Test that maxCores is respected when the memory-per-core guideline would allocate more cores
     * than allowed. Reproduces the bug where high memory (80G) but low maxCores (e.g. 1 core)
     * caused getCoreSpan to ignore the core limits.
     */
    public void testCoreSpanRespectsMaxCores() {
        // 48-core host with 256G memory, all idle
        host.memory = CueUtil.GB * 256;
        host.idleMemory = CueUtil.GB * 256;
        host.cores = 4800;
        host.idleCores = 4800;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 100; // 1 core
        frame.maxCores = 100; // max 1 core
        frame.setMinMemory(CueUtil.GB * 80);
        frame.threadable = true;

        // Without the fix, getCoreSpan would calculate ~15 cores based on
        // memory (80G / (256G/48) ≈ 15). With the fix, maxCores=100 is respected.
        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(100, proc.coresReserved);
    }

    public void testCoreSpanRespectsMaxCoresMultiCore() {
        // Same host, frame requesting 2 cores max with high memory
        host.memory = CueUtil.GB * 256;
        host.idleMemory = CueUtil.GB * 256;
        host.cores = 4800;
        host.idleCores = 4800;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 200; // 2 cores
        frame.maxCores = 200; // max 2 cores
        frame.setMinMemory(CueUtil.GB * 80);
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(200, proc.coresReserved);
    }

    public void testCoreSpanNoMaxCoresStillInflates() {
        // When maxCores is 0 (no limit), the memory-based inflation should
        // still apply as before.
        host.memory = CueUtil.GB * 256;
        host.idleMemory = CueUtil.GB * 256;
        host.cores = 4800;
        host.idleCores = 4800;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 100; // 1 core
        frame.maxCores = 0; // no limit
        frame.setMinMemory(CueUtil.GB * 80);
        frame.threadable = true;

        // getCoreSpan should inflate based on memory: 80G / (256G/48) ≈ 15 cores
        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(1500, proc.coresReserved);
    }

    public void testCoreSpanMaxCoresWithHighCoreRequest() {
        // When maxCores >= getCoreSpan result, getCoreSpan result is used
        host.memory = CueUtil.GB * 256;
        host.idleMemory = CueUtil.GB * 256;
        host.cores = 4800;
        host.idleCores = 4800;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 1000; // 10 cores
        frame.maxCores = 2000; // max 20 cores
        frame.setMinMemory(CueUtil.GB * 80);
        frame.threadable = true;

        // getCoreSpan calculates ~15 cores, which is between min (10) and max (20)
        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(1500, proc.coresReserved);
    }

    public void testGetCoreSpanWithMaxCores() {
        host.memory = CueUtil.GB * 256;
        host.idleMemory = CueUtil.GB * 256;
        host.cores = 4800;
        host.idleCores = 4800;

        // Without maxCores constraint: 80G / (256G/48) ≈ 15 cores = 1500
        assertEquals(1500, VirtualProc.getCoreSpan(host, CueUtil.GB * 80));

        // With maxCores = 100 (1 core): capped to 100
        assertEquals(100, VirtualProc.getCoreSpan(host, CueUtil.GB * 80, 100));

        // With maxCores = 500 (5 cores): capped to 500
        assertEquals(500, VirtualProc.getCoreSpan(host, CueUtil.GB * 80, 500));

        // With maxCores = 0 (no limit): same as without maxCores
        assertEquals(1500, VirtualProc.getCoreSpan(host, CueUtil.GB * 80, 0));

        // With maxCores higher than getCoreSpan result: no cap applied
        assertEquals(1500, VirtualProc.getCoreSpan(host, CueUtil.GB * 80, 2000));
    }

    public void testBuildVirtualProc() {
        VirtualProc proc;

        DispatchHost host = new DispatchHost();
        host.threadMode = ThreadMode.ALL_VALUE;
        /* 8 gigs and 7 cores idle, request 7g */
        host.memory = CueUtil.GB8;
        host.idleMemory = CueUtil.GB8;
        host.cores = 800;
        host.idleCores = 800;
        // Hardcoded value of dispatcher.memory.mem_reserved_default
        // to avoid having to read opencue.properties on a test setting
        long memReservedDefault = 3355443;

        DispatchFrame frame = new DispatchFrame();
        frame.minCores = 100;
        frame.setMinMemory(memReservedDefault);
        frame.threadable = true;

        proc = VirtualProc.build(host, frame);
        assertEquals(800, proc.coresReserved);

        host.threadMode = ThreadMode.AUTO_VALUE;
        proc = VirtualProc.build(host, frame);
        assertEquals(300, proc.coresReserved);
    }
}
