
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

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.jdbc.core.JdbcTemplate;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.grpc.report.RunningFrameInfo;

/**
 * Applies {@link LicenseSource} budgets to the legacy (Cuebot) booking path.
 *
 * The dispatch queries in {@code DispatchQuery} are deliberately not touched: license state lives
 * in this process (a poll of the license server), not in the database, so the gate runs in Java on
 * the candidate frames those queries return. A frame whose layer declares licenses (via the
 * {@code CUE_LICENSES} layer environment) is only dispatched while every pool it lists has a free
 * seat; everything else passes through untouched and pays only a cache lookup.
 *
 * Two entry points:
 *
 * <ul>
 * <li>{@link Session}: per dispatch pass, filters candidate {@code DispatchFrame}s against a
 * budget snapshot, with pass-local accounting so one pass cannot book fifty frames against ten
 * seats. Cross-Cuebot and cross-host races are absorbed by the in-flight correction inside
 * {@link LicenseSource} (booked frames are RUNNING in the DB immediately) plus headroom, and the
 * license-denied requeue in {@code FrameCompleteHandler} catches the remainder.</li>
 * <li>the packing helpers ({@link #hostBasedLicensesRunning}, {@link #findPackableJobs}), used by
 * {@code HostReportHandler} to steer layers that need a host-based license onto hosts already
 * holding that license.</li>
 * </ul>
 */
public class LicenseBookingGate {

    private static final Logger logger = LogManager.getLogger(LicenseBookingGate.class);

    /**
     * How long a layer's license declaration is remembered. Layer environments are written at
     * launch and effectively immutable afterwards, so this only bounds memory, not correctness.
     */
    private static final long LAYER_CACHE_EXPIRE_MINUTES = 10;
    private static final long LAYER_CACHE_MAX_SIZE = 100_000;

    /** Hard bound on rows the pack-job query may return, regardless of pending backlog. */
    private static final int MAX_PACK_QUERY_ROWS = 500;

    private final JdbcTemplate jdbc;
    private final LicenseSource licenseSource;

    /** layerId -> license names it declares; an empty list means unlicensed (the common case). */
    private final Cache<String, List<String>> layerLicenses =
            CacheBuilder.newBuilder().maximumSize(LAYER_CACHE_MAX_SIZE)
                    .expireAfterWrite(LAYER_CACHE_EXPIRE_MINUTES, TimeUnit.MINUTES).build();

    public LicenseBookingGate(JdbcTemplate jdbc, LicenseSource licenseSource) {
        this.jdbc = jdbc;
        this.licenseSource = licenseSource;
    }

    /**
     * License names the given layer declares, lowercased; empty when the layer is unlicensed.
     *
     * Returns null when the lookup itself failed, which callers must treat as "hold the frame":
     * booking a layer whose requirements could not be read is the blind run this gate exists to
     * prevent. A DB failure here means dispatch is failing anyway.
     */
    public List<String> licensesForLayer(String layerId) {
        try {
            return layerLicenses.get(layerId, () -> {
                List<String> values = jdbc.queryForList(
                        "SELECT str_value FROM layer_env WHERE pk_layer = ? AND str_key = ?",
                        String.class, layerId, licenseSource.getEnvKey());
                if (values.isEmpty()) {
                    return Collections.emptyList();
                }
                return LicenseSource.splitNames(values.get(0));
            });
        } catch (Exception e) {
            logger.warn("LicenseBookingGate: failed to read licenses for layer " + layerId
                    + ", holding its frames: " + e);
            return null;
        }
    }

    /** A gate session for one dispatch pass onto one host. */
    public Session newSession(String hostname) {
        return new Session(hostname);
    }

    /**
     * Pass-local license accounting for one dispatch pass onto one host.
     *
     * The budget snapshot is taken lazily, on the first licensed frame the pass meets, so passes
     * over unlicensed work never touch {@link LicenseSource}. Within the pass, floating seats are
     * decremented per booked frame and host-based seats taken on this host are remembered, so the
     * pass stays inside the budget it started with.
     */
    public final class Session {

        /** Lowercased, to match {@link LicenseSource}'s host normalization. */
        private final String host;

        /** Budgets fetched so far; grows as new license names are encountered. */
        private final Map<String, LicenseSource.LicenseBudget> budgets = new HashMap<>();

        /** Floating seats consumed by frames booked in this pass, per license. */
        private final Map<String, Integer> floatingUsed = new HashMap<>();

        /** Working copy of each host-based license's seat set, including seats this pass took. */
        private final Map<String, Set<String>> seats = new HashMap<>();

        private Session(String hostname) {
            this.host = hostname == null ? "" : hostname.toLowerCase();
        }

        /**
         * May a frame of this layer be booked on this session's host right now? True for unlicensed
         * layers. A licensed layer needs a seat in EVERY pool it lists; a stale or unknown pool
         * holds it (fail closed).
         */
        public boolean canBook(String layerId) {
            List<String> names = licensesForLayer(layerId);
            if (names == null) {
                return false;
            }
            if (names.isEmpty()) {
                return true;
            }
            ensureBudgets(names);
            for (String name : names) {
                LicenseSource.LicenseBudget budget = budgets.get(name);
                if (budget == null || budget.stale) {
                    return false;
                }
                if (budget.hostBased) {
                    // Free on a host already holding the license; a fresh host
                    // must fit under the seat cap.
                    Set<String> seated = seats.get(name);
                    if (!seated.contains(host) && seated.size() >= budget.seatCap) {
                        return false;
                    }
                } else {
                    if (budget.usable - floatingUsed.getOrDefault(name, 0) < 1) {
                        return false;
                    }
                }
            }
            return true;
        }

        /**
         * Record a successful booking of a frame of this layer, consuming this pass's budget:
         * floating pools lose a seat per frame, host-based pools gain this host as a seat.
         */
        public void booked(String layerId) {
            List<String> names = licensesForLayer(layerId);
            if (names == null || names.isEmpty()) {
                return;
            }
            for (String name : names) {
                LicenseSource.LicenseBudget budget = budgets.get(name);
                if (budget == null || budget.stale) {
                    continue;
                }
                if (budget.hostBased) {
                    seats.get(name).add(host);
                } else {
                    floatingUsed.merge(name, 1, Integer::sum);
                }
            }
        }

        private void ensureBudgets(List<String> names) {
            Set<String> missing = new HashSet<>();
            for (String name : names) {
                if (!budgets.containsKey(name)) {
                    missing.add(name);
                }
            }
            if (missing.isEmpty()) {
                return;
            }
            Map<String, LicenseSource.LicenseBudget> fetched =
                    licenseSource.snapshotBudgets(missing);
            budgets.putAll(fetched);
            for (LicenseSource.LicenseBudget budget : fetched.values()) {
                if (budget.hostBased) {
                    seats.put(budget.name, new HashSet<>(budget.seats));
                }
            }
        }
    }

    // ---- packing (HostReportHandler) --------------------------------------

    /**
     * Cheap packing pre-check for the report thread: does any of these running frames declare
     * licenses at all? Costs only layer-cache lookups (an indexed single-row query per layer per
     * cache period), never a budget snapshot. False when no provider is configured, because then
     * there is nothing to pack against.
     */
    public boolean anyLicensedLayers(List<RunningFrameInfo> runningFrames) {
        if (!licenseSource.hasProvider()) {
            return false;
        }
        for (RunningFrameInfo frame : runningFrames) {
            List<String> names = licensesForLayer(frame.getLayerId());
            if (names != null && !names.isEmpty()) {
                return true;
            }
        }
        return false;
    }

    /**
     * Host-based licenses held by any of the given running frames, per the current sample. This is
     * the packing trigger: a host already holding such a license can run more frames that need it
     * for free. Floating licenses are excluded (a seat is spent per frame, nothing to pack), as are
     * stale pools (the gate would hold their layers anyway).
     */
    public Set<String> hostBasedLicensesRunning(List<RunningFrameInfo> runningFrames) {
        if (!licenseSource.hasProvider() || runningFrames.isEmpty()) {
            return Collections.emptySet();
        }
        Set<String> names = new HashSet<>();
        for (RunningFrameInfo frame : runningFrames) {
            List<String> layerNames = licensesForLayer(frame.getLayerId());
            if (layerNames != null) {
                names.addAll(layerNames);
            }
        }
        if (names.isEmpty()) {
            return Collections.emptySet();
        }
        Set<String> out = new HashSet<>();
        for (LicenseSource.LicenseBudget budget : licenseSource.snapshotBudgets(names).values()) {
            if (budget.hostBased && !budget.stale) {
                out.add(budget.name);
            }
        }
        return out;
    }

    /**
     * Ids of pending jobs with waiting frames on layers that need one of the given licenses,
     * highest priority first, filtered to jobs this host could run (facility and OS; tags,
     * resources, subscription burst and the license budgets themselves are all re-checked by the
     * normal dispatch path). License matching is done in Java on the layer's declaration --
     * deliberately no new predicates in the sensitive dispatch queries.
     */
    public List<String> findPackableJobs(Set<String> licenses, DispatchHost host, int limit) {
        if (licenses.isEmpty() || limit <= 0) {
            return Collections.emptyList();
        }
        Set<String> hostOs = new HashSet<>(Arrays.asList(host.getOs()));
        List<String> jobIds = new ArrayList<>();
        // The SQL LIMIT is a hard bound on rows examined (one row per licensed
        // layer with waiting frames), generous because OS/license filtering
        // happens in Java below; `limit` caps the jobs actually returned.
        jdbc.query("SELECT DISTINCT job.pk_job, job.str_os, le.str_value, jr.int_priority "
                + "FROM layer_env le " + "JOIN layer l ON l.pk_layer = le.pk_layer "
                + "JOIN layer_stat lst ON lst.pk_layer = le.pk_layer "
                + "JOIN job ON job.pk_job = l.pk_job "
                + "JOIN job_resource jr ON jr.pk_job = job.pk_job " + "WHERE le.str_key = ? "
                + "AND lst.int_waiting_count > 0 " + "AND job.str_state = 'PENDING' "
                + "AND job.b_paused = false " + "AND job.pk_facility = ? "
                + "ORDER BY jr.int_priority DESC LIMIT " + MAX_PACK_QUERY_ROWS, rs -> {
                    if (jobIds.size() >= limit) {
                        return;
                    }
                    String jobOs = rs.getString("str_os");
                    if (jobOs != null && !jobOs.isEmpty() && !hostOs.contains(jobOs)) {
                        return;
                    }
                    boolean wantsOne = false;
                    for (String name : LicenseSource.splitNames(rs.getString("str_value"))) {
                        if (licenses.contains(name)) {
                            wantsOne = true;
                            break;
                        }
                    }
                    String jobId = rs.getString("pk_job");
                    if (wantsOne && !jobIds.contains(jobId)) {
                        jobIds.add(jobId);
                    }
                }, licenseSource.getEnvKey(), host.getFacilityId());
        return jobIds;
    }
}
