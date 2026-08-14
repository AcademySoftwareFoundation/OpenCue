
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
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import io.prometheus.client.Counter;
import io.prometheus.client.Gauge;
import io.prometheus.client.Histogram;

/**
 * Central home for the in-process Scheduler's Prometheus metrics, mirroring the Rust scheduler's
 * metrics module. The Scheduler tallies a plain {@link TickStats} during a tick and hands it over
 * once via {@link #recordTick}; all Prometheus wiring lives here and never throws into the tick.
 * Recording is a no-op unless {@code metrics.prometheus.collector} is enabled.
 */
@Component
public class SchedulerMetrics {

    private static final Logger logger = LogManager.getLogger(SchedulerMetrics.class);

    // Per-group tick outcome (Rust pass_terminated_reason_total). "Produced no
    // work" is 'no work' (nothing eligible) + 'no fit' (farm saturated).
    private static final Counter groupPass = Counter.build().name("cue_scheduler_group_pass_total")
            .help("Scheduler per-group tick outcomes by reason: booked; "
                    + "'no fit' (work waiting, farm saturated); 'no work' (nothing eligible); "
                    + "'query error' (candidate query failed, usually a bad tag)")
            .labelNames("env", "cuebot_host", "reason").register();

    // Host-spec groups seen this tick (Rust clusters_total).
    private static final Gauge groups = Gauge.build().name("cue_scheduler_groups_total")
            .help("Host-spec groups seen in the most recent scheduler tick")
            .labelNames("env", "cuebot_host").register();

    // The same groups split by whether they had eligible WORK this tick:
    // 'active' = candidates present (booked or no fit), 'inactive' = none (no work).
    // Makes spec/tag fragmentation legible at a glance -- how many pools are
    // engaged vs sitting idle with no matching work. Sums to groups_total.
    private static final Gauge groupsByState = Gauge.build()
            .name("cue_scheduler_groups_by_state")
            .help("Host-spec groups by demand this tick: 'active' (has eligible work: "
                    + "booked or no fit) vs 'inactive' (no work)")
            .labelNames("env", "cuebot_host", "state").register();

    // Total whole cores in the farm this tick; the denominator that turns
    // fragmented cores into a share of the farm.
    private static final Gauge farmCores = Gauge.build().name("cue_scheduler_farm_cores_total")
            .help("Total whole cores in the farm in the most recent scheduler tick")
            .labelNames("env", "cuebot_host").register();

    // Cores in use per show, SET each tick from a live sum of the procs (never
    // accumulated), so it tracks the farm and cannot drift above it.
    private static final Gauge showCores = Gauge.build().name("cue_scheduler_show_cores")
            .help("Whole cores in use per show, summed live from the procs each tick")
            .labelNames("env", "cuebot_host", "show").register();

    // Frames booked per show (Rust frames_dispatched_total); rate() = throughput.
    private static final Counter framesDispatched =
            Counter.build().name("cue_scheduler_frames_dispatched_total")
                    .help("Frames booked by the scheduler per show; apply rate() for throughput")
                    .labelNames("env", "cuebot_host", "show").register();

    // Tick wall-clock (Rust recompute_cycle_duration_seconds).
    private static final Histogram tickDuration =
            Histogram.build().name("cue_scheduler_tick_duration_seconds")
                    .help("Scheduler tick wall-clock duration in seconds")
                    .buckets(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30)
                    .labelNames("env", "cuebot_host").register();

    // Fragmentation: idle cores stranded on WORKING hosts (at least one core in
    // use) that no ready frame could take this tick, by the cause. cores = the
    // leftover idle was too few on any one host for a waiting frame (wide layers);
    // memory/gpu = idle cores whose host lacked the RAM/GPU the waiting work needs;
    // held = idle cores on a host reserved for a wide job; license = idle cores a
    // license shortage blocks; quota = idle cores a job/show/limit/folder cap holds
    // back. Empty hosts are not fragmented (one free block), so they are skipped;
    // the panel shows this over the whole farm, so a busy host's leftover reads as
    // a small share and the number only grows when the waste is farm-wide.
    private static final String[] FRAG_REASONS =
            {"cores", "memory", "gpu", "held", "license", "quota"};
    private static final Gauge fragmentedCores =
            Gauge.build().name("cue_scheduler_fragmented_cores")
                    .help("Idle cores stranded on working hosts this tick, by cause "
                            + "(cores, memory, gpu, held, license, quota)")
                    .labelNames("env", "cuebot_host", "reason").register();

    private final boolean enabled;
    private final String env;
    private final String host;
    // Shows published last tick, so a show that drops to zero procs gets set to 0
    // this tick rather than pinning its last value.
    private final Set<String> lastShows = new HashSet<>();

    @Autowired
    public SchedulerMetrics(Environment springEnv) {
        this.enabled = springEnv.getProperty("metrics.prometheus.collector", Boolean.class, false);
        String envKey =
                springEnv.getProperty("metrics.prometheus.environment_id.environment_variable",
                        String.class, "DEPLOYMENT_ENVIRONMENT");
        String de = System.getenv(envKey);
        this.env = de != null ? de : "undefined";
        this.host = hostFromEnv();
    }

    private static String hostFromEnv() {
        for (String key : new String[] {"NODE_HOSTNAME", "HOSTNAME", "HOST"}) {
            String value = System.getenv(key);
            if (value != null)
                return value;
        }
        return "undefined";
    }

    public boolean isEnabled() {
        return enabled;
    }

    /**
     * Publish one tick's tallies. Never throws into the caller.
     */
    public void recordTick(TickStats s) {
        if (!enabled || s == null)
            return;
        try {
            groups.labels(env, host).set(s.groups);
            // Demand split (has-work cut): active = had candidates (booked or no
            // fit), inactive = no eligible work. Derived from the per-tick outcome
            // tallies, so it always agrees with the group-pass reasons.
            groupsByState.labels(env, host, "active").set((double) (s.booked + s.noFit));
            groupsByState.labels(env, host, "inactive").set((double) s.noWork);
            farmCores.labels(env, host).set(s.farmCores);
            incReason("booked", s.booked);
            incReason("no fit", s.noFit);
            incReason("no work", s.noWork);
            incReason("query error", s.queryError);
            tickDuration.labels(env, host).observe(s.tickDurationMs / 1000.0);
            // Cores per show: SET from this tick's live read, then zero any show
            // that was present last tick but has no procs now, so a drained show
            // drops to 0 instead of pinning its last value.
            for (Map.Entry<String, Double> e : s.coresByShow.entrySet())
                showCores.labels(env, host, e.getKey()).set(e.getValue());
            for (String prev : lastShows)
                if (!s.coresByShow.containsKey(prev))
                    showCores.labels(env, host, prev).set(0.0);
            lastShows.clear();
            lastShows.addAll(s.coresByShow.keySet());
            for (Map.Entry<String, Integer> e : s.framesByShow.entrySet())
                framesDispatched.labels(env, host, e.getKey()).inc(e.getValue());
            // Set every reason each tick (0 when absent) so a cause that clears
            // reads 0 rather than pinning its last value.
            for (String reason : FRAG_REASONS)
                fragmentedCores.labels(env, host, reason)
                        .set(s.fragByReason.getOrDefault(reason, 0.0));
        } catch (RuntimeException e) {
            logger.warn("recordTick failed: " + e.getMessage());
        }
    }

    private void incReason(String reason, int count) {
        if (count > 0)
            groupPass.labels(env, host, reason).inc(count);
    }

    /**
     * Plain per-tick tallies the Scheduler fills during a tick and hands to {@link #recordTick}.
     * Cores are whole cores. No Prometheus types, so scheduler logic stays decoupled.
     */
    public static final class TickStats {
        public int groups;
        public int farmCores;
        public int booked;
        public int noFit;
        public int noWork;
        public int queryError;
        public long tickDurationMs;
        public final Map<String, Double> coresByShow = new HashMap<>();
        public final Map<String, Integer> framesByShow = new HashMap<>();
        public final Map<String, Double> fragByReason = new HashMap<>();
    }
}
