
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

import java.util.Enumeration;

import org.junit.Test;
import org.springframework.mock.env.MockEnvironment;

import io.prometheus.client.Collector;
import io.prometheus.client.CollectorRegistry;

import static org.junit.Assert.assertEquals;

/**
 * Unit tests for {@link SchedulerMetrics}. Metrics are static and shared across the JVM, so
 * counters use before/after deltas and gauges use show labels unique to each test to stay
 * order-independent.
 */
public class SchedulerMetricsTests {

    private static SchedulerMetrics enabledMetrics() {
        MockEnvironment env = new MockEnvironment();
        env.setProperty("metrics.prometheus.collector", "true");
        return new SchedulerMetrics(env);
    }

    /** Sum every sample of {@code name} whose {@code labelName} equals {@code labelValue}. */
    private static double sample(String name, String labelName, String labelValue) {
        double sum = 0.0;
        Enumeration<Collector.MetricFamilySamples> mfs =
                CollectorRegistry.defaultRegistry.metricFamilySamples();
        while (mfs.hasMoreElements()) {
            for (Collector.MetricFamilySamples.Sample s : mfs.nextElement().samples) {
                if (!s.name.equals(name))
                    continue;
                int idx = s.labelNames.indexOf(labelName);
                if (idx >= 0 && labelValue.equals(s.labelValues.get(idx)))
                    sum += s.value;
            }
        }
        return sum;
    }

    /** Sum every sample of {@code name}; for a single-series metric this is its value. */
    private static double sum(String name) {
        double total = 0.0;
        Enumeration<Collector.MetricFamilySamples> mfs =
                CollectorRegistry.defaultRegistry.metricFamilySamples();
        while (mfs.hasMoreElements()) {
            for (Collector.MetricFamilySamples.Sample s : mfs.nextElement().samples) {
                if (s.name.equals(name))
                    total += s.value;
            }
        }
        return total;
    }

    @Test
    public void recordTickPublishesEveryMetric() {
        SchedulerMetrics m = enabledMetrics();
        String pass = "cue_scheduler_group_pass_total";
        String frames = "cue_scheduler_frames_dispatched_total";
        double bookedBefore = sample(pass, "reason", "booked");
        double noFitBefore = sample(pass, "reason", "no fit");
        double noWorkBefore = sample(pass, "reason", "no work");
        double errBefore = sample(pass, "reason", "query error");
        double framesBefore = sample(frames, "show", "smtest_pub");
        double durCountBefore = sum("cue_scheduler_tick_duration_seconds_count");

        SchedulerMetrics.TickStats s = new SchedulerMetrics.TickStats();
        s.groups = 5;
        s.farmCores = 1000;
        s.booked = 3;
        s.noFit = 2;
        s.noWork = 4;
        s.queryError = 1;
        s.tickDurationMs = 250;
        s.runningFrames = 42;
        s.coresByShow.put("smtest_pub", 30.0);
        s.framesByShow.put("smtest_pub", 7);
        m.recordTick(s);

        assertEquals(5.0, sum("cue_scheduler_groups_total"), 0.0001);
        assertEquals(1000.0, sum("cue_scheduler_farm_cores_total"), 0.0001);
        assertEquals(42.0, sum("cue_scheduler_running_frames"), 0.0001);
        assertEquals(bookedBefore + 3.0, sample(pass, "reason", "booked"), 0.0001);
        assertEquals(noFitBefore + 2.0, sample(pass, "reason", "no fit"), 0.0001);
        assertEquals(noWorkBefore + 4.0, sample(pass, "reason", "no work"), 0.0001);
        assertEquals(errBefore + 1.0, sample(pass, "reason", "query error"), 0.0001);
        assertEquals(framesBefore + 7.0, sample(frames, "show", "smtest_pub"), 0.0001);
        assertEquals(30.0, sample("cue_scheduler_show_cores", "show", "smtest_pub"), 0.0001);
        // Histogram observed exactly one tick.
        assertEquals(durCountBefore + 1.0, sum("cue_scheduler_tick_duration_seconds_count"),
                0.0001);
    }

    @Test
    public void showCoresIsSetLiveNotAccumulated() {
        SchedulerMetrics m = enabledMetrics();
        String metric = "cue_scheduler_show_cores";

        SchedulerMetrics.TickStats s1 = new SchedulerMetrics.TickStats();
        s1.coresByShow.put("smtest_live", 40.0);
        m.recordTick(s1);
        m.recordTick(s1); // SET each tick, not summed -> still 40, not 80
        assertEquals(40.0, sample(metric, "show", "smtest_live"), 0.0001);

        SchedulerMetrics.TickStats s2 = new SchedulerMetrics.TickStats();
        s2.coresByShow.put("smtest_live", 30.0); // live read fell to 30
        m.recordTick(s2);
        assertEquals(30.0, sample(metric, "show", "smtest_live"), 0.0001);

        // A show with no procs this tick drops to 0, not its last value.
        m.recordTick(new SchedulerMetrics.TickStats());
        assertEquals(0.0, sample(metric, "show", "smtest_live"), 0.0001);
    }

    @Test
    public void waitlistIsSetPerReasonAndZeroedWhenAbsent() {
        SchedulerMetrics m = enabledMetrics();
        String metric = "cue_scheduler_waiting_frames";

        SchedulerMetrics.TickStats s = new SchedulerMetrics.TickStats();
        s.waitingFramesByReason.put("flowing", 120L);
        s.waitingFramesByReason.put("limit", 45L);
        m.recordTick(s);
        m.recordTick(s); // gauge is SET each tick, not summed -> still 45, not 90
        assertEquals(120.0, sample(metric, "reason", "flowing"), 0.0001);
        assertEquals(45.0, sample(metric, "reason", "limit"), 0.0001);
        // Absent reasons read 0, not stale.
        assertEquals(0.0, sample(metric, "reason", "capacity"), 0.0001);
        assertEquals(0.0, sample(metric, "reason", "no fit"), 0.0001);
        assertEquals(0.0, sample(metric, "reason", "no license"), 0.0001);
        assertEquals(0.0, sample(metric, "reason", "held"), 0.0001);

        // A cause that clears drops to 0 on the next tick, not its last value.
        m.recordTick(new SchedulerMetrics.TickStats());
        assertEquals(0.0, sample(metric, "reason", "limit"), 0.0001);
        assertEquals(0.0, sample(metric, "reason", "flowing"), 0.0001);
    }

    @Test
    public void groupsByStateSplitsActiveAndInactive() {
        SchedulerMetrics m = enabledMetrics();
        String metric = "cue_scheduler_groups_by_state";

        SchedulerMetrics.TickStats s = new SchedulerMetrics.TickStats();
        s.groups = 8;
        s.booked = 2; // had work, placed
        s.noFit = 1; // had work, farm full -> still active
        s.noWork = 5; // no eligible work -> inactive
        m.recordTick(s);

        assertEquals(3.0, sample(metric, "state", "active"), 0.0001); // booked + no fit
        assertEquals(5.0, sample(metric, "state", "inactive"), 0.0001); // no work
    }

    @Test
    public void disabledCollectorIsNoOp() {
        SchedulerMetrics m = new SchedulerMetrics(new MockEnvironment()); // collector defaults off
        SchedulerMetrics.TickStats s = new SchedulerMetrics.TickStats();
        s.coresByShow.put("smtest_off", 25.0);
        s.framesByShow.put("smtest_off", 9);
        m.recordTick(s);
        assertEquals(0.0, sample("cue_scheduler_show_cores", "show", "smtest_off"), 0.0001);
        assertEquals(0.0, sample("cue_scheduler_frames_dispatched_total", "show", "smtest_off"),
                0.0001);
    }
}
