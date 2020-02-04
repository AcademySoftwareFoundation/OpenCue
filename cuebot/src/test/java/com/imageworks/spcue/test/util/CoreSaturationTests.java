
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



package com.imageworks.spcue.test.util;


import junit.framework.TestCase;
import org.junit.Before;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.util.CueUtil;

public class CoreSaturationTests extends TestCase {

    DispatchHost host;

    @Before
    public void setUp() throws Exception {
        host = new DispatchHost();
        host.isNimby = false;
    }

    public void testCoreAndMemorySaturation1() {
        host.memory = CueUtil.GB32;
        host.idleMemory = CueUtil.GB8;
        host.cores = 800;
        host.idleCores = 700;

        DispatchFrame frame = new DispatchFrame();
        frame.services = "NOTarnold";
        frame.minCores = 100;
        frame.minMemory = CueUtil.GB * 7;
        frame.threadable = true;

        VirtualProc proc = VirtualProc.build(host, frame);
        assertEquals(700, proc.coresReserved);
        assertEquals(CueUtil.GB * 7, proc.memoryReserved);
    }
}

