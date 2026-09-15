
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

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.springframework.stereotype.Component;

import com.imageworks.spcue.grpc.report.RenderHost;

/**
 * Live farm-health ledger fed by every RQD host report, so health metrics come straight from the
 * report stream with no database read. {@link HostReportHandler} records each report as it lands;
 * the scheduler joins this ledger with its tick snapshot and publishes swap and kernel-time
 * aggregates per host-spec group and per hardware shape. A host that stops reporting ages out, so a
 * dead machine leaves the aggregates instead of pinning its last values.
 *
 * Kernel time arrives in the report's free-form attributes map under {@code sysTime} (percent of
 * CPU spent in system, the same channel the legacy {@code swapout} hint uses). Agents that do not
 * send it simply contribute no kernel-time sample; swap totals are first-class report fields and
 * are always present.
 */
@Component
public class FarmHealth {

    /** One host's latest health sample. {@code sysTimePct} is -1 when the agent omits it. */
    static final class HostHealth {
        final long swapTotalKb;
        final long swapFreeKb;
        final double sysTimePct;
        final long atMs;

        HostHealth(long swapTotalKb, long swapFreeKb, double sysTimePct, long atMs) {
            this.swapTotalKb = swapTotalKb;
            this.swapFreeKb = swapFreeKb;
            this.sysTimePct = sysTimePct;
            this.atMs = atMs;
        }
    }

    private static final long EXPIRE_MS = 10 * 60 * 1000L;

    private final Map<String, HostHealth> byHostName = new ConcurrentHashMap<>();

    /** Record one host report. Never throws into the report path. */
    public void record(RenderHost host) {
        try {
            double sys = -1;
            String s = host.getAttributesMap().get("sysTime");
            if (s != null)
                sys = Double.parseDouble(s);
            byHostName.put(host.getName().toLowerCase(), new HostHealth(host.getTotalSwap(),
                    host.getFreeSwap(), sys, System.currentTimeMillis()));
        } catch (RuntimeException ignored) {
            // a malformed report must never disturb report handling
        }
    }

    /** Copy of the ledger with stale hosts dropped (and evicted as a side effect). */
    Map<String, HostHealth> snapshot() {
        long cut = System.currentTimeMillis() - EXPIRE_MS;
        Map<String, HostHealth> out = new HashMap<>();
        for (Map.Entry<String, HostHealth> e : byHostName.entrySet()) {
            if (e.getValue().atMs < cut)
                byHostName.remove(e.getKey());
            else
                out.put(e.getKey(), e.getValue());
        }
        return out;
    }
}
