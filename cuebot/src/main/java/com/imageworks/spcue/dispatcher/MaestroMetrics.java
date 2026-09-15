
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
 * Central home for the in-process Maestro's Prometheus metrics, mirroring the Rust scheduler's
 * metrics module. Maestro tallies a plain {@link TickStats} during a tick and hands it over once
 * via {@link #recordTick}; all Prometheus wiring lives here and never throws into the tick.
 * Recording is a no-op unless {@code metrics.prometheus.collector} is enabled.
 */
@Component
public class MaestroMetrics {

    private static final Logger logger = LogManager.getLogger(MaestroMetrics.class);

    // Per-group tick outcome (Rust pass_terminated_reason_total). "Produced no
    // work" is 'no work' (nothing eligible) + 'no fit' (farm saturated).
    private static final Counter groupPass = Counter.build().name("cue_maestro_group_pass_total")
            .help("Maestro per-group tick outcomes by reason: booked; "
                    + "'no fit' (work waiting, farm saturated); 'no work' (nothing eligible); "
                    + "'query error' (candidate query failed, usually a bad tag)")
            .labelNames("env", "cuebot_host", "reason").register();

    // Host-spec groups seen this tick (Rust clusters_total).
    private static final Gauge groups = Gauge.build().name("cue_maestro_groups_total")
            .help("Host-spec groups seen in the most recent scheduler tick")
            .labelNames("env", "cuebot_host").register();

    // The same groups split by whether they had eligible WORK this tick:
    // 'active' = candidates present (booked or no fit), 'inactive' = none (no work).
    // Makes spec/tag fragmentation legible at a glance -- how many pools are
    // engaged vs sitting idle with no matching work. Sums to groups_total.
    private static final Gauge groupsByState = Gauge.build().name("cue_maestro_groups_by_state")
            .help("Host-spec groups by demand this tick: 'active' (has eligible work: "
                    + "booked or no fit) vs 'inactive' (no work)")
            .labelNames("env", "cuebot_host", "state").register();

    // Total whole cores in the farm this tick; the denominator that turns
    // fragmented cores into a share of the farm.
    private static final Gauge farmCores = Gauge.build().name("cue_maestro_farm_cores_total")
            .help("Total whole cores in the farm in the most recent scheduler tick")
            .labelNames("env", "cuebot_host").register();

    // Cores in use per show, SET each tick from a live sum of the procs (never
    // accumulated), so it tracks the farm and cannot drift above it.
    private static final Gauge showCores = Gauge.build().name("cue_maestro_show_cores")
            .help("Whole cores in use per show, summed live from the procs each tick")
            .labelNames("env", "cuebot_host", "show").register();

    // Frames booked per show (Rust frames_dispatched_total); rate() = throughput.
    private static final Counter framesDispatched =
            Counter.build().name("cue_maestro_frames_dispatched_total")
                    .help("Frames booked by the scheduler per show; apply rate() for throughput")
                    .labelNames("env", "cuebot_host", "show").register();

    // Tick wall-clock (Rust recompute_cycle_duration_seconds).
    private static final Histogram tickDuration =
            Histogram.build().name("cue_maestro_tick_duration_seconds")
                    .help("Maestro tick wall-clock duration in seconds")
                    .buckets(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30)
                    .labelNames("env", "cuebot_host").register();

    // The waitlist: waiting frames on the last tick's candidate layers, split by why
    // they cannot run. Every waiting frame the tick weighed lands in exactly one
    // bucket, so the panel's blocked shares are each bucket over the sum, and all
    // zero means everything flows. Loop-only by design (no extra query): a job the
    // candidate query filters out at its cap shows up only on the ticks churn
    // re-admits it.
    // Frames on procs right now, from the live ledger (booked minus drained). The
    // denominator that turns the waitlist's blocked counts into a share of ALL
    // frames the farm handles, so a small blocked slice reads small on the panel.
    private static final Gauge runningFrames = Gauge.build().name("cue_maestro_running_frames")
            .help("Frames on procs right now, from the live booking/drain ledger")
            .labelNames("env", "cuebot_host").register();

    // Farm health from the live report ledger, sliced two ways: by='group' is the
    // host-spec group (normalized tags|os), by='hwtype' the hardware shape (e.g.
    // 128c/112g). Swap is a fraction of capacity so it reads as a percent; a host
    // counts as swapping above 5% of its swap in use. Kernel time comes from the
    // report attribute sysTime and reads 0 where agents do not send it.
    private static final Gauge farmSwapFrac = Gauge.build().name("cue_farm_health_swap_used_frac")
            .help("Swap in use as a fraction of swap capacity across the label's hosts; "
                    + "by='group' slices by host-spec group, by='hwtype' by hardware shape")
            .labelNames("env", "cuebot_host", "by", "name").register();
    private static final Gauge farmHostsSwapping =
            Gauge.build().name("cue_farm_health_hosts_swapping")
                    .help("Hosts with more than 5% of their swap in use, per slice")
                    .labelNames("env", "cuebot_host", "by", "name").register();
    private static final Gauge farmSysTime = Gauge.build().name("cue_farm_health_system_time_pct")
            .help("Mean percent of CPU spent in the kernel across the slice's reporting "
                    + "hosts (report attribute sysTime; 0 when agents do not send it)")
            .labelNames("env", "cuebot_host", "by", "name").register();
    private static final Gauge farmSysTimeMax =
            Gauge.build().name("cue_farm_health_system_time_pct_max")
                    .help("Worst single host's kernel-time percent in the slice")
                    .labelNames("env", "cuebot_host", "by", "name").register();

    // The locality dial, counted in frames at the booking decision. One
    // metric answers both localities: live_warm is locality in space (the
    // chosen host runs the layer right now), cache_warm is locality in time
    // (the layer left the host but few foreign frames displaced its caches
    // since), cold is neither. Warm share = warm kinds over the sum.
    private static final Counter bookedLocality =
            Counter.build().name("cue_maestro_booked_frames_locality_total")
                    .help("Frames booked by cache locality of the chosen host: "
                            + "live_warm (host already runs the layer), "
                            + "cache_warm (layer recently left the host, caches likely intact), "
                            + "cold (no local data; the asset fetch is paid again)")
                    .labelNames("env", "cuebot_host", "kind").register();

    // The physical counterpart of waiting_frames{reason='no fit'}: idle cores
    // that exist but that no waiting frame can buy, usually because co-resident
    // frames ate the host's memory first. SET each tick from the post-plan
    // snapshot; sustained high values mean the farm's idle is the wrong shape.
    private static final Gauge farmStrandedCores =
            Gauge.build().name("cue_farm_health_stranded_cores")
                    .help("Whole cores idle after planning that no waiting frame can buy "
                            + "(cores, memory or gpu blocks every candidate on that host)")
                    .labelNames("env", "cuebot_host").register();

    private static final String[] WAIT_REASONS =
            {"flowing", "capacity", "no fit", "limit", "no license", "held"};
    private static final Gauge waitingFrames = Gauge.build().name("cue_maestro_waiting_frames")
            .help("Waiting frames on the last tick's candidate layers, by why they cannot run: "
                    + "flowing (layer booked this tick, backlog is moving); "
                    + "capacity (farm simply full: idle cores cannot cover one frame); "
                    + "'no fit' (idle exists but none fits: slivers, memory or gpu); "
                    + "limit (job, show, limit or folder cap); "
                    + "'no license' (pool exhausted or stale); "
                    + "held (every fitting host is reserved)")
            .labelNames("env", "cuebot_host", "reason").register();

    private final boolean enabled;
    private final String env;
    private final String host;
    // Shows published last tick, so a show that drops to zero procs gets set to 0
    // this tick rather than pinning its last value.
    private final Set<String> lastShows = new HashSet<>();
    // Health slices published last tick ("by|name"), zeroed when absent for the
    // same reason.
    private final Set<String> lastHealth = new HashSet<>();

    @Autowired
    public MaestroMetrics(Environment springEnv) {
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
            runningFrames.labels(env, host).set(s.runningFrames);
            farmStrandedCores.labels(env, host).set(s.strandedCores);
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
            for (Map.Entry<String, Long> e : s.bookedFramesByLocality.entrySet())
                if (e.getValue() > 0)
                    bookedLocality.labels(env, host, e.getKey()).inc(e.getValue());
            // Set every reason each tick (0 when absent) so a cause that clears
            // reads 0 rather than pinning its last value.
            for (String reason : WAIT_REASONS)
                waitingFrames.labels(env, host, reason)
                        .set(s.waitingFramesByReason.getOrDefault(reason, 0L));
            publishHealth(s);
        } catch (RuntimeException e) {
            logger.warn("recordTick failed: " + e.getMessage());
        }
    }

    /** SET the four health gauges per slice, zeroing slices that vanished. */
    private void publishHealth(TickStats s) {
        Set<String> seen = new HashSet<>();
        for (String by : new String[] {"group", "hwtype"}) {
            Map<String, HealthAgg> slice = by.equals("group") ? s.healthByGroup : s.healthByHwtype;
            for (Map.Entry<String, HealthAgg> e : slice.entrySet()) {
                HealthAgg a = e.getValue();
                String name = e.getKey();
                farmSwapFrac.labels(env, host, by, name)
                        .set(a.swapTotalKb > 0 ? (double) a.swapUsedKb / a.swapTotalKb : 0.0);
                farmHostsSwapping.labels(env, host, by, name).set(a.hostsSwapping);
                farmSysTime.labels(env, host, by, name).set(a.sysN > 0 ? a.sysSum / a.sysN : 0.0);
                farmSysTimeMax.labels(env, host, by, name).set(a.sysMax);
                seen.add(by + "|" + name);
            }
        }
        for (String prev : lastHealth) {
            if (seen.contains(prev))
                continue;
            int cut = prev.indexOf('|');
            String by = prev.substring(0, cut), name = prev.substring(cut + 1);
            farmSwapFrac.labels(env, host, by, name).set(0.0);
            farmHostsSwapping.labels(env, host, by, name).set(0.0);
            farmSysTime.labels(env, host, by, name).set(0.0);
            farmSysTimeMax.labels(env, host, by, name).set(0.0);
        }
        lastHealth.clear();
        lastHealth.addAll(seen);
    }

    private void incReason(String reason, int count) {
        if (count > 0)
            groupPass.labels(env, host, reason).inc(count);
    }

    /**
     * Plain per-tick tallies Maestro fills during a tick and hands to {@link #recordTick}. Cores
     * are whole cores. No Prometheus types, so scheduler logic stays decoupled.
     */
    public static final class TickStats {
        public int groups;
        public int farmCores;
        public int booked;
        public int noFit;
        public int noWork;
        public int queryError;
        public long runningFrames;
        public long strandedCores;
        public long tickDurationMs;
        public final Map<String, Double> coresByShow = new HashMap<>();
        public final Map<String, Integer> framesByShow = new HashMap<>();
        public final Map<String, Long> bookedFramesByLocality = new HashMap<>();
        public final Map<String, Long> waitingFramesByReason = new HashMap<>();
        public final Map<String, HealthAgg> healthByGroup = new HashMap<>();
        public final Map<String, HealthAgg> healthByHwtype = new HashMap<>();
    }

    /**
     * Swap and kernel-time aggregate over one health slice's hosts. Kernel time is fed only by
     * hosts whose reports carry it; a host counts as swapping above 5% of its swap in use.
     */
    public static final class HealthAgg {
        public long swapTotalKb;
        public long swapUsedKb;
        public int hostsSwapping;
        public int hosts;
        public double sysSum;
        public double sysMax;
        public int sysN;

        public void add(long swapTotal, long swapFree, double sysTimePct) {
            hosts++;
            long used = Math.max(0, swapTotal - swapFree);
            swapTotalKb += swapTotal;
            swapUsedKb += used;
            if (swapTotal > 0 && used > swapTotal / 20)
                hostsSwapping++;
            if (sysTimePct >= 0) {
                sysSum += sysTimePct;
                sysMax = Math.max(sysMax, sysTimePct);
                sysN++;
            }
        }
    }
}
