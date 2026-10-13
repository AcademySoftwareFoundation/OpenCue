
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

import org.junit.Test;

import com.imageworks.spcue.grpc.report.RenderHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;

import static org.junit.Assert.assertEquals;

public class FarmHealthTests {

    private static RunningFrameInfo frame(String pcpu) {
        RunningFrameInfo.Builder frame = RunningFrameInfo.newBuilder().setFrameId("f" + pcpu);
        if (pcpu != null)
            frame.putAttributes("pcpu", pcpu);
        return frame.build();
    }

    @Test
    public void aMalformedPcpuSkipsOnlyItsFrame() {
        FarmHealth health = new FarmHealth();
        RenderHost host = RenderHost.newBuilder().setName("Host1").setTotalSwap(8).build();
        health.record(host, Arrays.asList(frame("70.5"), frame("abc"), frame("NaN"),
                frame("Infinity"), frame("-3"), frame(null), frame("229.5")));
        FarmHealth.HostHealth sample = health.snapshot().get("host1");
        assertEquals(300, sample.busyCorePoints);
        assertEquals(8, sample.swapTotalKb);
    }
}
