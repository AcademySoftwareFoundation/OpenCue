
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

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Collectors;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.service.JobManager;

/**
 * Single-threaded planner: one Cuebot holds a Postgres advisory lock and plans each tick while the
 * rest idle as warm standbys. Placement is serial so decisions never race; only the per-host plan
 * reads fan out on a pool, and every booking for a tick commits in one batched transaction.
 * Persistent reservations hold hosts for blocked wide layers until enough cores free up.
 *
 * Gated by scheduler.enabled (default false). See Scheduler.md for the full model.
 */
public class Scheduler extends JdbcDaoSupport {

    private static final Logger logger = LogManager.getLogger(Scheduler.class);

    // Postgres advisory-lock key, shared by every Cuebot on the database. ASCII "OpenCue".
    private static final long SCHEDULER_LOCK_KEY = 0x4F70656E437565L;

    // placementScore (E-PVM) dimension weights: relative importance on the util-fraction scale.
    // GPUs weighted up so a GPU layer prefers the host where it strands the least GPU capacity.
    private static final double W_CORES = 1.0;
    private static final double W_MEM = 1.0;
    private static final double W_GPUS = 4.0;
    private static final double W_GPU_MEM = 1.0;

    // Locality bonus: subtracted from a host's score when it already runs the candidate's layer, so
    // a freed core is refilled by the same layer next tick. Bounded, below the fit/reservation
    // gates.
    private volatile double localityBonus = 8.0;
    private volatile boolean localityEnabled = true;

    // Cache-warmth window: a decayed locality pull kept on vacated (host, layer) pairs, aged by
    // foreign frames booked since (displacement, not wall clock), not seconds. 0 disables. See doc.
    private volatile int localityWindowFrames = 64;
    // host|layer -> host's booking-odometer reading when the layer last completed there.
    private final Map<String, Long> warmthByHostLayer = new HashMap<String, Long>();
    // host -> booking odometer, incremented per frame booked on the host.
    private final Map<String, Long> bookingsByHost = new HashMap<String, Long>();

    // Seat bonus for host-based licenses (one checkout per machine): subtracted per seated pool so
    // placement packs licensed work onto the fewest hosts. Sized above the E-PVM spread. See doc.
    private volatile double licenseSeatBonus = 16.0;

    // Live application-license availability, null until the first tick builds it. See
    // LicenseSource.
    private volatile LicenseSource licenseSource;

    // Spring config; scheduler.* properties read once in startSchedulerPoolsIfNeeded().
    @Autowired
    private Environment env;

    // Backs txTemplate (atomic resource-delta flushes).
    @Autowired
    private PlatformTransactionManager transactionManager;

    // Wraps each resource-delta flush so its several UPDATEs commit atomically. Built lazily.
    private volatile TransactionTemplate txTemplate;

    private TransactionTemplate txTemplate() {
        TransactionTemplate t = txTemplate;
        if (t == null) {
            t = new TransactionTemplate(transactionManager);
            txTemplate = t;
        }
        return t;
    }

    // Plans one host's next bookable frames via planHost() (legacy per-host dispatch path).
    private Dispatcher dispatcher;

    // Applies frame completions; drives the stage-0 drain (drainResolvedCompletions).
    private FrameCompleteHandler frameCompleteHandler;

    // Records each tick's stats to Prometheus via recordTick (runTick).
    private SchedulerMetrics schedulerMetrics;

    // The in-progress tick's stats, handed to schedulerMetrics at tick end.
    private SchedulerMetrics.TickStats lastTickStats;

    // Max completions applied per drain transaction (bounds the stop/delete/refund lock footprint).
    private static final int DRAIN_CHUNK = 2000;

    // Batched commit, orphan sweep, frame stop/unbook, and RQD launch of committed frames.
    private DispatchSupport dispatchSupport;

    // Resolves a host id to a DispatchHost for the plan reads (planBookings).
    private HostManager hostManager;

    // Resolves a layer id to a LayerInterface for the plan reads (planBookings).
    private JobManager jobManager;

    // Kills the frame whose post-commit launch failed (by frame id); see launchCommitted.
    private RqdClient rqdClient;

    // Reentrancy latch: a slow tick makes the next firing skip instead of overlapping (runTick).
    private final AtomicBoolean tickInFlight = new AtomicBoolean(false);

    // This Cuebot's planning-leadership lock connection, or null when standby. Sticky and raw (not
    // pooled, so Hikari cannot reap it and drop the lock). See Scheduler.md for the failover model.
    private volatile Connection leaderConn = null;

    // Live host reservations, persistent across ticks: host id -> claiming (layer, priority).
    // Planner-thread only (single-writer); empty after failover. See Scheduler.md for the model.
    private final Map<String, Reservation> reservations = new HashMap<>();

    // ---- plan / batch-commit / launch -------------------------------------
    // Placement only records (host, layer) pairings; after it, planHost reads each pairing's frames
    // and one batched transaction commits them all, then RQD launches fire on a small pool.

    // Per-tick placements to commit, host id -> layer ids. Planner-thread only; cleared each tick.
    private final Map<String, List<String>> plannedByHost = new LinkedHashMap<>();

    // Layers already placed this tick, across all groups: stops a permissive layer being re-planned
    // per group (the copies would race for the same frames). Keyed on placement, not candidacy.
    private final Set<String> placedLayerIds = new HashSet<>();

    // Tick-scoped planning scratch (planner-thread only, reset each tick by clearTickScratch). Held
    // as fields so the phase methods share them without threading a dozen parameters.
    private final Map<String, Integer> jobCoresUsed = new HashMap<>();
    private final Map<String, Integer> showCoresUsed = new HashMap<>();
    private final Map<String, Integer> limitUsed = new HashMap<>();
    private final Map<String, Integer> folderUsed = new HashMap<>();
    private final Map<String, Integer> folderMaxCp = new HashMap<>();
    private final Map<String, Integer> folderRunSeed = new HashMap<>();
    private final Map<String, String> jobFolderCap = new HashMap<>();
    private final Map<String, List<String>> layerLicenses = new HashMap<>();
    private final Map<String, LicenseSource.LicenseBudget> licenseBudgets = new HashMap<>();
    private final Map<String, Integer> licenseUsed = new HashMap<>();
    private final Map<String, Set<String>> licenseSeats = new HashMap<>();
    private final Set<String> seenLayerIds = new HashSet<>();
    private final List<ReservationRequest> reservationReqs = new ArrayList<>();
    // host -> seconds until it frees enough cores for a reserving layer (backfill deadline).
    // Read fresh each tick (reassigned, not cleared).
    private Map<String, Integer> tReadyByHost = new HashMap<>();

    // host -> layer ids it currently runs, the locality/affinity signal. Read fresh each tick.
    private Map<String, Set<String>> hostLayerAffinity = new HashMap<>();

    // Layer-placements planned this tick, for the tick-breakdown log line.
    private int lastPlacements;

    // Consecutive ticks a layer was planned but planHost's commit-time read found zero frames: the
    // signature of a planner-vs-dispatch eligibility mismatch. Warns at plan_zero_warn_ticks.
    private final Map<String, Integer> planZeroStreak = new ConcurrentHashMap<>();

    // Small bounded pool for post-commit RQD launches (one gRPC per frame); a full queue drops
    // the launch (launchDropped) rather than blocking the planner.
    private volatile ExecutorService launchPool;

    // Launches dropped because the launch queue was full; the frame is RUNNING in the DB, reconcile
    // recovers it.
    private final java.util.concurrent.atomic.AtomicLong launchDropped =
            new java.util.concurrent.atomic.AtomicLong(0);

    // Pool for the plan phase: per-host plan reads (planHost) run in parallel, one task per host
    // (serial within a host so the capacity decrement is correct). Commit is still single/batched.
    private volatile ExecutorService readPool;

    // Max frames one commit books per layer (property dispatcher.job_frame_dispatch_max).
    private volatile int jobFrameDispatchMax;
    // When false, the planner ignores reservations entirely (no claims, none enforced): the bare
    // placement core, for isolating core scheduling from the reservation logic.
    private volatile boolean reservationsEnabled = true;

    // Time gate: blocked-time a layer must accrue before it may reserve (wall-clock).
    // Property scheduler.reservation_block_seconds. See Scheduler.md for the reservation model.
    private volatile long reservationBlockMs = 300_000; // 5 minutes
    // Capacity gate: reservations hold at most this fraction of the hosts that fit a given layer.
    private volatile double reservationMaxFraction = 0.5;

    // Width gate (always on): a layer may reserve only if its per-frame cores are at least this
    // fraction of the largest host in its group.
    private static final double RESERVATION_MIN_HOST_FRACTION = 0.5;

    // EASY backfill: let a lower-priority frame run on a reserved host's free cores, but only if it
    // finishes before the host frees enough for the reserving layer, so the reservation is
    // undelayed.
    private volatile boolean backfillEnabled = true;

    // Per-layer leaky bucket of net blocked time (ms): grows while blocked, decays while placing.
    // A layer qualifies to reserve once its debt reaches reservationBlockMs.
    private final Map<String, Long> blockedDebtMs = new HashMap<>();
    // Per-layer last-seen tick time, for the inter-tick delta that feeds blockedDebtMs.
    private final Map<String, Long> lastSeenMs = new HashMap<>();

    // ---- log throttling + per-window stat line -----------------------------
    // Per-tick detail goes to DEBUG; INFO gets one consolidated stat line per statIntervalMs, a
    // full
    // snapshot for bug reports, emitted on every tick attempt (leader or standby) as a heartbeat.

    // Core points per whole core: OpenCue stores host/proc cores as cores * 100.
    private static final int CORE_POINTS_PER_CORE = 100;

    // Stat-line interval (scheduler.stat_interval_seconds, default 5 min).
    private volatile long statIntervalMs = 300_000;
    private long lastSummaryMs = 0;

    // Window accumulators, planner-thread only except summarySkipped (bumped by the CAS-loser
    // trigger thread, hence atomic). maybeLogStat emits the consolidated line and resets the
    // window.
    private int summaryTicks = 0; // ticks this Cuebot won and planned
    private long summaryDispatched = 0; // procs committed (won the version race)
    private long summaryTickMs = 0; // summed tick wall time (for the mean)
    private long summaryMaxTickMs = 0; // slowest single tick in the window
    private int summaryLockLost = 0; // attempts another Cuebot held the lock
    private long summaryPlanned = 0; // frames the plan phase produced
    private int summaryGranted = 0; // new reservations granted
    private int summaryBackfilled = 0; // frames placed onto a reserved host
    private long summaryBackfilledCores = 0; // core-points placed via EASY backfill
    private long summaryDrained = 0; // completion reports drained at tick start
    private long summaryLicenseBooked = 0; // frames booked against a license pool
    private long summaryLicenseHeld = 0; // candidates held back by a license pool
    private long summaryLicenseTrimmed = 0; // planned frames a pool could not cover
    private long summaryLaunchDroppedAt = 0; // launchDropped count at window start
    private final java.util.concurrent.atomic.AtomicInteger summarySkipped =
            new java.util.concurrent.atomic.AtomicInteger(0);
    // Farm fill for the stat line, captured in snapshotFarmFill (stage 1) before placement
    // decrements the in-memory idle counts.
    private int lastHosts = 0; // schedulable hosts
    private int lastIdleHosts = 0; // hosts with >= reservable-min idle
    private long lastCoresTotalCp = 0; // total cores, core points
    private long lastCoresIdleCp = 0; // idle cores, core points
    private int lastGroups = 0; // host-spec groups (stage 2)
    private int lastReservationReqs = 0; // reservation requests, set later in grantReservations
    // Per-tick outputs set by doTick(), folded into the window by runTick().
    private long tickPlanned = 0;
    private int tickGranted = 0;
    private int tickBackfilled = 0;
    private long tickBackfilledCores = 0;
    // Live licensing: frames booked against a license pool, and candidates a pool
    // held back this tick (out of seats, or its sample was too stale to spend).
    private int tickLicenseBooked = 0;
    private int tickLicenseHeld = 0;
    // Planned frames dropped at commit time because a pool could not cover them
    // (the plan read has no license clause; see the trim in doTick).
    private int tickLicenseTrimmed = 0;
    // Warn threshold: a group count near the host count means near-per-host fragmentation.
    // See warnIfGroupsFragmented.
    private static final int GROUP_COUNT_WARN_THRESHOLD = 100;
    private static final long GROUP_WARN_INTERVAL_MS = 300_000; // at most every 5 min
    private long lastGroupWarnMs = 0;
    // Throttle for the candidate-query-failure WARN below (same 5 min policy).
    private long lastCandidateErrWarnMs = 0;

    // ---- batched resource accounting --------------------------------------
    // The legacy per-proc resource UPDATEs serialize on a few hot rows and dominate commit cost at
    // scale. Instead the planner records per-row deltas and flushes one UPDATE per row after the
    // batch commit. Off only when scheduler_manages_resources is true (the Rust scheduler owns the
    // resource tables then). Set in startSchedulerPoolsIfNeeded. See Scheduler.md section 5.
    private volatile boolean batchResourceAccounting = true;
    // Per-row delta buffers: value is {cores, gpus}. Written on the planner
    // thread when the batch commit's winners are accounted, then drained in
    // flushResourceDeltas right after the commit.
    // subDeltas key: pkShow + '\t' + pkAlloc
    // layerDeltas key: pkLayer
    // jobDeltas key: pkJob (drives job_resource, folder_resource, point)
    private final Map<String, long[]> subDeltas = new ConcurrentHashMap<>();
    private final Map<String, long[]> layerDeltas = new ConcurrentHashMap<>();
    private final Map<String, long[]> jobDeltas = new ConcurrentHashMap<>();

    /**
     * Lazy launch-pool init on the first runTick. Avoids touching Spring XML wiring for an
     * init-method, and Cuebot is well past startup by the time scheduler.enabled is flipped on.
     */
    private synchronized void startSchedulerPoolsIfNeeded() {
        if (launchPool != null)
            return;
        int launchSize = env.getProperty("scheduler.launch_pool_size", Integer.class, 8);
        jobFrameDispatchMax =
                env.getProperty("dispatcher.job_frame_dispatch_max", Integer.class, 8);
        reservationsEnabled =
                env.getProperty("scheduler.reservations_enabled", Boolean.class, true);
        reservationBlockMs =
                1000L * env.getProperty("scheduler.reservation_block_seconds", Integer.class, 300);
        reservationMaxFraction =
                env.getProperty("scheduler.reservation_max_fraction", Double.class, 0.5);
        backfillEnabled = env.getProperty("scheduler.backfill_enabled", Boolean.class, true);
        localityEnabled = env.getProperty("scheduler.locality_enabled", Boolean.class, true);
        localityBonus = env.getProperty("scheduler.locality_bonus", Double.class, 8.0);
        localityWindowFrames =
                env.getProperty("scheduler.locality_window_frames", Integer.class, 64);
        // Property name kept from the per-host-limit feature this supersedes, so
        // any site already setting it keeps its value.
        licenseSeatBonus = env.getProperty("scheduler.host_limit_seat_bonus", Double.class, 16.0);
        // Live application licenses. Started here rather than wired as a bean so its poll thread's
        // life matches the planner's; layers without CUE_LICENSES simply never consult it.
        LicenseSource ls = new LicenseSource(env, getJdbcTemplate());
        ls.start();
        licenseSource = ls;
        // Cadence of the consolidated INFO stat line (see maybeLogStat). Default
        // 5 minutes; lower it for a live incident, raise it to quiet the log.
        statIntervalMs =
                1000L * env.getProperty("scheduler.stat_interval_seconds", Integer.class, 300);
        // Batch resource accounting unless the Rust scheduler owns those tables
        // via its periodic recompute (scheduler_manages_resources). In that mode
        // procCreated writes nothing and we must not either.
        batchResourceAccounting =
                !env.getProperty("dispatcher.scheduler_manages_resources", Boolean.class, false);
        // Bounded pool so launches never run on the tick thread (a slow RQD sink would stall the
        // tick). On a full queue we drop the launch and count it: the frame is already running in
        // the DB, so RQD report reconciliation recovers it, and the tick never waits on RQD.
        int launchQueueSize = env.getProperty("scheduler.launch_queue_size", Integer.class, 16384);
        ThreadPoolExecutor pool = new ThreadPoolExecutor(launchSize, launchSize, 0L,
                TimeUnit.MILLISECONDS, new LinkedBlockingQueue<>(launchQueueSize), r -> {
                    Thread t = new Thread(r);
                    t.setName("Scheduler-launch-" + t.getId());
                    t.setDaemon(true);
                    return t;
                }, (r, ex) -> {
                    long n = launchDropped.incrementAndGet();
                    if (n % 1000 == 1) {
                        logger.warn("Scheduler: launch queue full, dropping launch"
                                + " (total dropped=" + n + "); RQD reconciliation will recover");
                    }
                });
        launchPool = pool;
        // Read pool for the parallel plan phase. Reads are DB-bound (they block
        // on Postgres, not the CPU), so sizing above the core count is fine.
        int readSize = env.getProperty("scheduler.read_pool_size", Integer.class, launchSize);
        readPool = Executors.newFixedThreadPool(readSize, r -> {
            Thread t = new Thread(r);
            t.setName("Scheduler-read-" + t.getId());
            t.setDaemon(true);
            return t;
        });
        logger.info("Scheduler: launch pool started with " + launchSize
                + " workers, read pool with " + readSize + " workers");
    }

    // ---- snapshot queries -------------------------------------------------

    /**
     * All schedulable hosts: state UP and lock state OPEN, busy or idle. Returns enough columns to
     * compute the spec key and run the per-host fit check without a second lookup. The
     * idle/min-core cut happens later, in planGroup.
     */
    private static final String SELECT_ALL_HOSTS = "SELECT " + "  h.pk_host, " + "  h.str_name, "
            + "  h.pk_alloc, " + "  a.pk_facility, " + "  h.int_thread_mode, " + "  h.int_cores, "
            + "  h.int_cores_idle, " + "  h.int_mem, " + "  h.int_mem_idle, " + "  h.int_gpus, "
            + "  h.int_gpus_idle, " + "  h.int_gpu_mem, " + "  h.int_gpu_mem_idle, "
            + "  h.int_procs, " + "  h.str_tags, " + "  hs.str_os "
            + "FROM host h, host_stat hs, alloc a " + "WHERE h.pk_host = hs.pk_host "
            + "  AND a.pk_alloc = h.pk_alloc " + "  AND hs.str_state = 'UP' "
            + "  AND h.str_lock_state = 'OPEN' ";

    /**
     * Candidate layers for a host spec group. One query per group. Filters: - job PENDING and
     * unpaused - tag regex match against the group's normalized tag string - OS match (or any if
     * the job is OS-agnostic) - job under int_max_cores - show under subscription burst on this
     * alloc - at least one WAITING, depend-resolved frame on the layer - layer.int_cores_min fits
     * the group's max host total cores (not idle, a blocked layer waiting on a reserved host stays
     * in the candidate set even when no host has it idle right now) Ranked by the priority-weighted
     * lottery (power(random(),1/priority)) and capped by LIMIT, not strictly by priority.
     * waiting_frame_count is the number of dispatchable frames on the layer at query time;
     * reconciliation uses it to decide how many hosts the layer should reserve.
     */
    private static final String SELECT_CANDIDATES_FOR_GROUP = "SELECT " + "  l.pk_layer, "
            + "  l.pk_job, " + "  j.pk_show, " + "  l.int_cores_min, " + "  l.int_mem_min, "
            + "  l.int_gpus_min, " + "  l.int_gpu_mem_min, " + "  jr.int_priority, "
            + "  jr.int_cores       AS job_cores_in_use, "
            + "  jr.int_max_cores   AS job_max_cores, "
            + "  sub.int_cores      AS show_cores_in_use, " + "  sub.int_burst      AS show_burst, "
            + "  COALESCE(ls.int_waiting_count, 0) AS waiting_frame_count, "
            + "  COALESCE(lu.int_clock_time_high, 0)     AS clock_time_high, "
            + "  COALESCE(lu.int_frame_success_count, 0) AS frame_success_count, "
            // Limit (license-cap) accounting: the layer's most-constraining limit,
            // its cap, and how many frames of that limit run farm-wide right now.
            + "  lim.pk_limit_record AS limit_id, "
            + "  COALESCE(lim.int_max_value, 0)   AS limit_max, "
            + "  COALESCE(lu2.int_sum_running, 0) AS limit_running, "
            // Folder (group/dept) core cap: the job's folder, its ceiling, and the
            // folder's current running cores (ground truth = SUM of the folder's jobs).
            + "  j.pk_folder AS folder_id, " + "  COALESCE(fr.int_max_cores, -1) AS folder_max, "
            // Application licenses the layer declares (CUE_LICENSES), comma
            // separated, NULL when it declares none.
            + "  le.str_value AS licenses, " + "  COALESCE(fu.folder_cores, 0)   AS folder_running "
            + "FROM   layer l " + "JOIN   job j           ON j.pk_job  = l.pk_job "
            + "JOIN   job_resource jr ON jr.pk_job = j.pk_job "
            + "JOIN   show sh         ON sh.pk_show = j.pk_show "
            + "JOIN   subscription sub ON sub.pk_show = j.pk_show AND sub.pk_alloc = ? "
            + "LEFT JOIN layer_usage lu ON lu.pk_layer = l.pk_layer "
            + "LEFT JOIN layer_stat  ls ON ls.pk_layer = l.pk_layer "
            // The layer's most-constraining limit (smallest cap), one row per layer.
            + "LEFT JOIN LATERAL (" + "    SELECT ll.pk_limit_record, lr.int_max_value "
            + "    FROM   layer_limit ll "
            + "    JOIN   limit_record lr ON lr.pk_limit_record = ll.pk_limit_record "
            + "    WHERE  ll.pk_layer = l.pk_layer "
            + "    ORDER BY lr.int_max_value LIMIT 1) lim ON true "
            // Farm-wide running count per limit (computed once, not per row).
            + "LEFT JOIN ("
            + "    SELECT ll2.pk_limit_record, SUM(ls2.int_running_count) AS int_sum_running "
            + "    FROM   layer_limit ll2 "
            + "    JOIN   layer_stat ls2 ON ls2.pk_layer = ll2.pk_layer "
            + "    GROUP BY ll2.pk_limit_record) lu2 "
            + "  ON lu2.pk_limit_record = lim.pk_limit_record "
            // Folder core ceiling + the folder's current running cores. Derived from
            // layer_stat.int_running_count (running frames x per-frame cores), the
            // same trigger-maintained counter the limit cap uses. It is robust to frame
            // completion (int_running_count drops automatically) and, at a tick
            // boundary, equals SUM(job_resource.int_cores) (one proc per running
            // frame), the figure the folder cap is measured against. Computed once,
            // not per row.
            + "LEFT JOIN folder_resource fr ON fr.pk_folder = j.pk_folder " + "LEFT JOIN ("
            + "    SELECT j2.pk_folder, "
            + "           SUM(ls2.int_running_count * l2.int_cores_min) AS folder_cores "
            + "    FROM   job j2 "
            // Only aggregate capped folders (int_max_cores <> -1). Every job has a
            // folder but almost none are capped, so without this join the subquery
            // would sum layer_stat across the whole farm every candidate query; this
            // keeps it empty (free) when no folder has a ceiling.
            + "    JOIN   folder_resource fr2 ON fr2.pk_folder = j2.pk_folder "
            + "                               AND fr2.int_max_cores <> -1 "
            + "    JOIN   layer l2      ON l2.pk_job = j2.pk_job "
            + "    JOIN   layer_stat ls2 ON ls2.pk_layer = l2.pk_layer "
            + "    WHERE  j2.str_state = 'PENDING' "
            + "    GROUP BY j2.pk_folder) fu ON fu.pk_folder = j.pk_folder "
            // Live application licenses, carried on the candidate row so the
            // planner needs no second round trip for them. Joined on pk_layer,
            // which layer_env is indexed on (i_layer_env_pk_layer); asking the
            // other way round, "which layers declare CUE_LICENSES", has no index
            // to use and would scan every environment variable on the farm once
            // per tick. At most one row per layer, so this cannot multiply
            // candidates or disturb the ranking below.
            + "LEFT JOIN layer_env le ON le.pk_layer = l.pk_layer AND le.str_key = ? "
            + "WHERE  j.str_state = 'PENDING' " + "  AND  j.b_paused  = false "
            // A host may advertise several OSes, comma-separated in
            // host_stat.str_os ("rhel7,rhel9" on mid-migration boxes). The
            // legacy dispatcher expands that into str_os IN ('rhel7','rhel9');
            // an exact string compare here silently starved every os-pinned
            // job on such hosts (the PARITY verify scenario's parity_os
            // archetype). Match any advertised value, exactly like legacy.
            + "  AND  (j.str_os IS NULL OR j.str_os = '' "
            + "        OR j.str_os = ANY(string_to_array(?, ','))) "
            // Jobs run only in their own facility. The legacy dispatcher binds
            // job.pk_facility in every job-finding query; without this the
            // planner books cross-facility (PARITY's parity_facother archetype)
            // because the frame-level plan read never re-checks facility.
            + "  AND  j.pk_facility = ? "
            // ThreadMode.ALL hosts run only threadable layers (bind 1 for ALL
            // groups, 0 otherwise), exactly the legacy dispatcher's clause.
            // Without it the planner parks non-threadable layers on ALL hosts
            // (idle NIMBY workstations score best), planHost's re-check finds
            // zero frames, and the layer burns its one commit per tick forever.
            + "  AND  (CASE WHEN l.b_threadable = true THEN 1 ELSE 0 END) >= ? "
            + "  AND  ? ~* ('(?x)' || l.str_tags || '\\y') "
            + "  AND  jr.int_cores  < jr.int_max_cores " + "  AND  sub.int_cores < sub.int_burst "
            + "  AND  l.int_cores_min <= ? "
            // Dispatchable-frame test and waiting_frame_count both come from
            // layer_stat.int_waiting_count (maintained by core trigger
            // trigger__update_frame_status_counts; WAITING frames are depend-resolved,
            // DEPEND is a separate state). Backed by the partial index
            // idx_layer_stat_waiting (V44). Replaces a correlated COUNT(*) + EXISTS
            // over frame that scanned every frame of each candidate layer per tick.
            + "  AND  COALESCE(ls.int_waiting_count, 0) > 0 "
            // Skip layers whose limit (license cap) is already full farm-wide. Their
            // frames get filtered out downstream by findNextDispatchFrames anyway, so
            // scoring a host + running the plan read for them only burns a cycle that
            // returns nothing (it surfaces as raceLost). A limit-less layer (NULL)
            // always passes. Not a correctness gate, purely an efficiency
            // filter: the downstream query still enforces the cap.
            + "  AND (lim.pk_limit_record IS NULL "
            + "       OR COALESCE(lu2.int_sum_running, 0) < lim.int_max_value) "
            // Skip jobs whose folder (group/dept) core ceiling is already reached
            // (folder_resource.int_max_cores, another core cap the legacy dispatcher
            // enforces; -1 = unlimited). Same rationale as the limit filter: purely an
            // efficiency gate (don't plan bookings a full folder can't take). The exact
            // ceiling is enforced by the post-plan folder trim in doTick, which,
            // unlike this filter, also binds the frames planHost books in the tick
            // that crosses the cap.
            + "  AND (COALESCE(fr.int_max_cores, -1) = -1 "
            + "       OR COALESCE(fu.folder_cores, 0) + l.int_cores_min <= fr.int_max_cores) "
            // Progressive rollout: in 'managed' mode only shows flagged
            // b_scheduler_managed are planned here (the legacy dispatch query excludes
            // exactly those, so the two partition); in 'facility' mode the bound flag
            // is true and this short-circuits to plan every show.
            + "  AND (? OR sh.b_scheduler_managed = true) "
            // Priority-weighted lottery, not a strict priority sort: each layer gets key
            // random()^(1/priority) (Efraimidis-Spirakis) and we take the top LIMIT, so a
            // low-priority layer keeps a share proportional to its priority instead of being
            // starved by a higher-priority stream. GREATEST(...,1) floors the weight for priority
            // <= 0. Reservation granting stays strict priority-first. See Scheduler.md section 3.5.
            + "ORDER BY power(random(), 1.0 / GREATEST(jr.int_priority, 1)) DESC " + "LIMIT  ? ";

    // ---- row mappers ------------------------------------------------------

    private static final RowMapper<BookableHost> HOST_MAPPER = new RowMapper<BookableHost>() {
        public BookableHost mapRow(ResultSet rs, int i) throws SQLException {
            BookableHost h = new BookableHost();
            h.hostId = rs.getString("pk_host");
            h.hostName = rs.getString("str_name");
            h.pkAlloc = rs.getString("pk_alloc");
            h.pkFacility = rs.getString("pk_facility");
            h.threadMode = rs.getInt("int_thread_mode");
            h.coresTotal = rs.getInt("int_cores");
            h.coresIdle = rs.getInt("int_cores_idle");
            h.memTotal = rs.getLong("int_mem");
            h.memIdle = rs.getLong("int_mem_idle");
            h.gpusTotal = rs.getInt("int_gpus");
            h.gpusIdle = rs.getInt("int_gpus_idle");
            h.gpuMemTotal = rs.getLong("int_gpu_mem");
            h.gpuMemIdle = rs.getLong("int_gpu_mem_idle");
            h.runningProcs = rs.getInt("int_procs");
            h.tagsRaw = rs.getString("str_tags");
            h.os = rs.getString("str_os");
            return h;
        }
    };

    private static final RowMapper<LayerCandidate> CANDIDATE_MAPPER =
            new RowMapper<LayerCandidate>() {
                public LayerCandidate mapRow(ResultSet rs, int i) throws SQLException {
                    LayerCandidate c = new LayerCandidate();
                    c.layerId = rs.getString("pk_layer");
                    c.jobId = rs.getString("pk_job");
                    c.showId = rs.getString("pk_show");
                    c.layerCoresMin = rs.getInt("int_cores_min");
                    c.layerMemMin = rs.getLong("int_mem_min");
                    c.layerGpusMin = rs.getInt("int_gpus_min");
                    c.layerGpuMemMin = rs.getLong("int_gpu_mem_min");
                    c.priority = rs.getInt("int_priority");
                    c.jobCoresInUse = rs.getInt("job_cores_in_use");
                    c.jobMaxCores = rs.getInt("job_max_cores");
                    c.showCoresInUse = rs.getInt("show_cores_in_use");
                    c.showBurstCores = rs.getInt("show_burst");
                    c.waitingFrameCount = rs.getInt("waiting_frame_count");
                    c.clockTimeHighSec = rs.getInt("clock_time_high");
                    c.frameSuccessCount = rs.getInt("frame_success_count");
                    c.limitId = rs.getString("limit_id"); // null when no limit
                    c.limitMax = rs.getInt("limit_max");
                    c.limitRunning = rs.getInt("limit_running");
                    c.folderId = rs.getString("folder_id");
                    c.folderMax = rs.getInt("folder_max"); // -1 = unlimited
                    c.folderRunning = rs.getInt("folder_running"); // core-points
                    // Application licenses the layer declares, or null when none.
                    // Kept null rather than an empty list so the placement loop
                    // skips all license work with one reference check.
                    List<String> lics = LicenseSource.splitNames(rs.getString("licenses"));
                    c.licenses = lics.isEmpty() ? null : lics;
                    return c;
                }
            };

    // ---- tick -------------------------------------------------------------

    /**
     * Quartz entry point, fired every few seconds on every Cuebot. A thin harness around doTick: it
     * skips when disabled, guards against overlapping ticks with tickInFlight so a slow tick makes
     * the next firing skip rather than stack, starts the scheduler pools on first use, times the
     * pass, and folds the leader's per-tick counters into the window summary maybeLogStat emits.
     *
     * The work, the drain and the planning, lives in doTick. It returns the procs dispatched, or -1
     * when this Cuebot is a standby that drained but did not plan; a standby therefore contributes
     * no planning stats, only its drain count and the heartbeat stat line.
     */
    public void runTick() {
        if (!isEnabled())
            return;
        if (!tickInFlight.compareAndSet(false, true)) {
            logger.debug("Scheduler: previous tick still running, skipping");
            summarySkipped.incrementAndGet();
            return;
        }
        startSchedulerPoolsIfNeeded();
        long t0 = System.currentTimeMillis();
        try {
            int dispatched = doTick();
            if (dispatched >= 0) {
                long ms = System.currentTimeMillis() - t0;
                // Per-tick detail at DEBUG; INFO gets one consolidated stat line per
                // window (maybeLogStat, called in the finally below).
                logger.debug("Scheduler tick: dispatched " + dispatched + " procs, " + ms
                        + " ms, reservations=" + reservations.size());
                summaryTicks++;
                summaryDispatched += dispatched;
                summaryTickMs += ms;
                if (ms > summaryMaxTickMs)
                    summaryMaxTickMs = ms;
                summaryPlanned += tickPlanned;
                summaryGranted += tickGranted;
                summaryBackfilled += tickBackfilled;
                summaryBackfilledCores += tickBackfilledCores;
                summaryLicenseBooked += tickLicenseBooked;
                summaryLicenseHeld += tickLicenseHeld;
                summaryLicenseTrimmed += tickLicenseTrimmed;
                if (schedulerMetrics != null && lastTickStats != null) {
                    lastTickStats.tickDurationMs = ms;
                    schedulerMetrics.recordTick(lastTickStats);
                }
            }
        } catch (RuntimeException e) {
            logger.error("Scheduler tick failed", e);
        } finally {
            // One consolidated stat line per window, on every tick attempt (leader or
            // standby) so a standby Cuebot still emits a heartbeat. Reached only by the
            // thread that held tickInFlight (the CAS loser returned earlier), so the plain
            // summary fields stay single-writer.
            maybeLogStat();
            tickInFlight.set(false);
        }
    }

    /**
     * Apply the frame completions queued since the last tick, as a single writer in tick order,
     * before any planning. Runs on every Cuebot (leader and standby). Batches of
     * {@link #DRAIN_CHUNK}: a batch that throws falls back to per-report so one bad completion
     * cannot drop the rest. A won completion queues its post-ops and, when locality is on, stamps
     * the host/layer cache-warmth entry (this host just ran this layer, so its caches are hot) with
     * the host's booking odometer; a lost one is handled as stale. Returns the number drained.
     */
    private int drainResolvedCompletions() {
        if (frameCompleteHandler == null)
            return 0;
        List<QueuedFrameCompletion> resolved = SchedulerCompletionQueue.drain();
        int drained = resolved.size();
        long tDrain0 = System.currentTimeMillis();
        for (int from = 0; from < resolved.size(); from += DRAIN_CHUNK) {
            List<QueuedFrameCompletion> chunk =
                    resolved.subList(from, Math.min(from + DRAIN_CHUNK, resolved.size()));
            long tChunk0 = System.currentTimeMillis();
            try {
                boolean[] won = dispatchSupport.stopFramesBatch(chunk);
                long tChunk = System.currentTimeMillis() - tChunk0;
                if (tChunk > 500) {
                    logger.info("Scheduler drain: stopFramesBatch(" + chunk.size() + ") took "
                            + tChunk + "ms");
                }
                for (int i = 0; i < won.length; i++) {
                    QueuedFrameCompletion c = chunk.get(i);
                    if (won[i]) {
                        if (localityEnabled && localityWindowFrames > 0
                                && c.proc.getLayerId() != null) {
                            warmthByHostLayer.put(c.proc.getHostId() + "|" + c.proc.getLayerId(),
                                    bookingsByHost.getOrDefault(c.proc.getHostId(), 0L));
                        }
                        frameCompleteHandler.queuePostOps(c);
                    } else {
                        frameCompleteHandler.handleStaleCompletion(c.proc,
                                c.proc.getName() + "/" + c.frame.getName());
                    }
                }
            } catch (RuntimeException e) {
                logger.warn("Scheduler drain: batch of " + chunk.size()
                        + " completions failed, retrying per-report: " + e);
                for (QueuedFrameCompletion c : chunk) {
                    try {
                        frameCompleteHandler.processReportNow(c.report);
                    } catch (RuntimeException e2) {
                        logger.warn("Scheduler drain: completion for frame " + c.frame.getName()
                                + " failed: " + e2);
                    }
                }
            }
        }
        long tDrain = System.currentTimeMillis() - tDrain0;
        if (tDrain > 1000) {
            logger.info("Scheduler drain: " + drained + " completions in " + tDrain + "ms");
        }
        return drained;
    }

    /**
     * Expire cache-warmth entries displaced by a window's worth of foreign frames on their host.
     * Idle hosts' entries never expire because nothing displaced them.
     */
    private void expireDisplacedWarmth() {
        if (warmthByHostLayer.isEmpty())
            return;
        warmthByHostLayer.entrySet()
                .removeIf(e -> bookingsByHost
                        .getOrDefault(e.getKey().substring(0, e.getKey().indexOf('|')), 0L)
                        - e.getValue() >= localityWindowFrames);
    }

    /**
     * Emit the consolidated per-window stat line at most once per {@link #statIntervalMs}, then
     * reset the window accumulators. A full snapshot for a bug report, grouped as: health/HA
     * (window seconds, ticks won, skipped when a tick fired while the previous still ran, lockLost
     * when this Cuebot was a standby, avgTick/maxTick); farm (the last planned tick's host/core
     * fill and host-spec group count, where a count near the host count is the tag-leak the
     * guardrail warns on); flow (committed procs, frames planned, the gap lost to the frame-version
     * race, RQD launches dropped); resv (reservations held and the cores they hold, newly granted,
     * requested last tick, and frames EASY-backfilled onto reserved hosts); and lic, only when
     * licenses are in play (frames booked against a pool, candidates a pool held back, and planned
     * frames trimmed at commit because a pool could not cover them).
     *
     * Called from runTick's finally on the thread that held tickInFlight, so the plain fields are
     * single-writer (summarySkipped is atomic, bumped by the CAS loser from another thread).
     */
    private void maybeLogStat() {
        long nowMs = System.currentTimeMillis();
        if (lastSummaryMs == 0) { // first call: start the window, do not emit
            lastSummaryMs = nowMs;
            summaryLaunchDroppedAt = launchDropped.get();
            return;
        }
        if (nowMs - lastSummaryMs < statIntervalMs)
            return;

        long win = (nowMs - lastSummaryMs) / 1000;
        long coresTotal = lastCoresTotalCp / CORE_POINTS_PER_CORE;
        long idleCores = lastCoresIdleCp / CORE_POINTS_PER_CORE;
        double util = lastCoresTotalCp > 0
                ? 100.0 * (lastCoresTotalCp - lastCoresIdleCp) / lastCoresTotalCp
                : 0.0;
        long avgTick = summaryTicks > 0 ? summaryTickMs / summaryTicks : 0;
        long raceLost = Math.max(0, summaryPlanned - summaryDispatched);
        long dropNow = launchDropped.get();
        long droppedInWindow = dropNow - summaryLaunchDroppedAt;
        int skipped = summarySkipped.getAndSet(0);

        // Cores currently held by the wide-job reservation feature: the sum of the
        // reserved layers' per-frame core requirement across all live reservations.
        // A point-in-time level (like held), not a window flow, so it is summed
        // here from the reservations map rather than accumulated per tick.
        long reservedCp = 0;
        for (Reservation r : reservations.values()) {
            reservedCp += r.layerCoresMin;
        }

        // Licensing section, only when a license pool is actually in play, so the
        // line stays as it was on the many farms that use no live licenses.
        String lic = "";
        if (summaryLicenseBooked > 0 || summaryLicenseHeld > 0) {
            lic = String.format(" | lic booked=%d held=%d trimmed=%d", summaryLicenseBooked,
                    summaryLicenseHeld, summaryLicenseTrimmed);
        }

        logger.info(String.format(
                "Scheduler stat: win=%ds ticks=%d skipped=%d lockLost=%d avgTick=%dms maxTick=%dms"
                        + " | farm hosts=%d idleHosts=%d cores=%d idleCores=%d util=%.1f%% groups=%d"
                        + " | flow committed=%d planned=%d raceLost=%d launchDropped=%d drained=%d"
                        + " | resv held=%d reservedCores=%d granted=%d reqs=%d backfilled=%d backfilledCores=%d%s",
                win, summaryTicks, skipped, summaryLockLost, avgTick, summaryMaxTickMs, lastHosts,
                lastIdleHosts, coresTotal, idleCores, util, lastGroups, summaryDispatched,
                summaryPlanned, raceLost, droppedInWindow, summaryDrained, reservations.size(),
                reservedCp / CORE_POINTS_PER_CORE, summaryGranted, lastReservationReqs,
                summaryBackfilled, summaryBackfilledCores / CORE_POINTS_PER_CORE, lic));

        lastSummaryMs = nowMs;
        summaryTicks = 0;
        summaryDispatched = 0;
        summaryTickMs = 0;
        summaryMaxTickMs = 0;
        summaryLockLost = 0;
        summaryPlanned = 0;
        summaryGranted = 0;
        summaryBackfilled = 0;
        summaryBackfilledCores = 0;
        summaryDrained = 0;
        summaryLicenseBooked = 0;
        summaryLicenseHeld = 0;
        summaryLicenseTrimmed = 0;
        summaryLaunchDroppedAt = dropNow;
    }

    /**
     * Zero the per-tick stat outputs before any early return, so a host-less tick contributes zero
     * to the window rather than carrying last tick's values.
     */
    private void resetTickOutputs() {
        tickPlanned = 0;
        tickGranted = 0;
        tickBackfilled = 0;
        tickBackfilledCores = 0;
        tickLicenseBooked = 0;
        tickLicenseHeld = 0;
        tickLicenseTrimmed = 0;
    }

    /**
     * Record the farm's host/core fill for the per-window stat line, taken before this tick's
     * placement mutates the in-memory idle counts (placement decrements h.coresIdle). Core points;
     * maybeLogStat converts to whole cores.
     */
    private void snapshotFarmFill(List<BookableHost> allHosts) {
        lastHosts = allHosts.size();
        lastIdleHosts = 0;
        lastCoresTotalCp = 0;
        lastCoresIdleCp = 0;
        for (BookableHost h : allHosts) {
            lastCoresTotalCp += h.coresTotal;
            lastCoresIdleCp += h.coresIdle;
            if (h.coresIdle >= Dispatcher.CORE_POINTS_RESERVED_MIN)
                lastIdleHosts++;
        }
    }

    /**
     * Warn (throttled) when the host-spec group count approaches the host count: the spec key is
     * fragmenting per host (usually a host name leaked into the tag set), which collapses planning
     * into one candidate query per host, the query storm grouping exists to avoid.
     */
    private void warnIfGroupsFragmented(int groupCount, int hostCount) {
        if (groupCount < GROUP_COUNT_WARN_THRESHOLD)
            return;
        long nowMs = System.currentTimeMillis();
        if (nowMs - lastGroupWarnMs < GROUP_WARN_INTERVAL_MS)
            return;
        lastGroupWarnMs = nowMs;
        logger.warn("Scheduler: " + groupCount + " host-spec groups for " + hostCount
                + " hosts (a handful is expected). A count near the host count means hosts are"
                + " fragmenting into near-per-host groups, commonly a host name leaking into the"
                + " tag set, which collapses planning into one candidate query per host, the very"
                + " query storm the scheduler avoids. Check tag normalization (normalizeTags /"
                + " groupByHostSpec).");
    }

    /**
     * Hold every capped folder to its ceiling. The plan read has no folder clause, so a batch can
     * carry more of a capped folder than int_max_cores allows; walk the frames in plan order and
     * drop any that would cross the cap, counting up from the folder's running cores at tick start.
     * Folders with no cap are never touched. Returns the kept bookings.
     */
    private List<FrameBooking> trimOverFolderCeiling(List<FrameBooking> planned,
            Map<String, Integer> folderMaxCp, Map<String, Integer> folderRunSeed,
            Map<String, String> jobFolderCap) {
        if (folderMaxCp.isEmpty() || planned.isEmpty())
            return planned;
        Map<String, Integer> folderCommit = new HashMap<>(folderRunSeed);
        List<FrameBooking> keep = new ArrayList<>(planned.size());
        int folderTrimmed = 0;
        for (FrameBooking b : planned) {
            String fid = jobFolderCap.get(b.proc.getJobId());
            if (fid == null) {
                keep.add(b);
                continue;
            }
            int cap = folderMaxCp.get(fid);
            int used = folderCommit.getOrDefault(fid, 0);
            int cp = b.proc.coresReserved;
            if (used + cp <= cap) {
                folderCommit.put(fid, used + cp);
                keep.add(b);
            } else {
                folderTrimmed++;
            }
        }
        if (folderTrimmed == 0)
            return planned;
        logger.debug("Scheduler: folder ceiling trimmed " + folderTrimmed
                + " planned frame(s) over cap this tick");
        return keep;
    }

    /**
     * Hold every live application-license pool to its availability. Same gap as the folder ceiling:
     * the plan read is license-blind, so this trim is what actually holds the line. Floating pools
     * count frames against budget.usable; host-based pools charge a seat only for hosts not already
     * seated, and a frame's pools are spent only once it is certain to be kept (so a frame rejected
     * by its second license never consumes a seat in its first). Dropped frames stay WAITING for
     * the next tick. Returns the kept bookings.
     */
    private List<FrameBooking> trimOverLicensePools(List<FrameBooking> planned,
            Map<String, LicenseSource.LicenseBudget> licenseBudgets,
            Map<String, List<String>> layerLicenses) {
        if (licenseBudgets.isEmpty() || layerLicenses.isEmpty() || planned.isEmpty())
            return planned;
        Map<String, Integer> committedByLicense = new HashMap<>();
        Map<String, Set<String>> seatsByLicense = new HashMap<>();
        List<FrameBooking> keep = new ArrayList<>(planned.size());
        int licTrimmed = 0;
        for (FrameBooking b : planned) {
            List<String> names = layerLicenses.get(b.proc.getLayerId());
            if (names == null) {
                keep.add(b);
                continue;
            }
            String hostName = b.proc.hostName == null ? "" : b.proc.hostName.toLowerCase();
            boolean fits = true;
            for (String name : names) {
                LicenseSource.LicenseBudget bd = licenseBudgets.get(name);
                if (bd == null || bd.stale) {
                    fits = false;
                    break;
                }
                if (bd.hostBased) {
                    Set<String> seats =
                            seatsByLicense.computeIfAbsent(name, k -> new HashSet<>(bd.seats));
                    if (!seats.contains(hostName) && seats.size() >= bd.seatCap) {
                        fits = false;
                        break;
                    }
                } else if (committedByLicense.getOrDefault(name, 0) + 1 > bd.usable) {
                    fits = false;
                    break;
                }
            }
            if (!fits) {
                licTrimmed++;
                continue;
            }
            for (String name : names) {
                LicenseSource.LicenseBudget bd = licenseBudgets.get(name);
                if (bd.hostBased) {
                    seatsByLicense.get(name).add(hostName);
                } else {
                    committedByLicense.merge(name, 1, Integer::sum);
                }
            }
            keep.add(b);
        }
        if (licTrimmed == 0)
            return planned;
        tickLicenseTrimmed += licTrimmed;
        logger.debug("Scheduler: license pools trimmed " + licTrimmed
                + " planned frame(s) over live availability this tick");
        return keep;
    }

    /**
     * Drop reservation and blocked-debt state for layers that left the dispatchable set this tick,
     * so a layer that disappears and returns starts its block timer fresh.
     */
    private void sweepStaleReservationState(Set<String> seenLayerIds) {
        reservations.entrySet().removeIf(e -> !seenLayerIds.contains(e.getValue().layerId));
        blockedDebtMs.keySet().removeIf(id -> !seenLayerIds.contains(id));
        lastSeenMs.keySet().removeIf(id -> !seenLayerIds.contains(id));
    }

    /**
     * Grant reservations highest priority first (then widest job), so the scarce budget lands on
     * work that cannot fit on its own. Existing reservers are always reconciled (refresh or release
     * promptly); new qualifiers get at most scheduler.reservation_max_grantees grants this tick,
     * the rest qualify again next tick.
     */
    private void grantReservations(List<ReservationRequest> reservationReqs) {
        int reservationMaxGrantees =
                env.getProperty("scheduler.reservation_max_grantees", Integer.class, 8);
        reservationReqs.sort(Comparator.<ReservationRequest>comparingInt(r -> -r.candidate.priority)
                .thenComparingInt(r -> -r.candidate.layerCoresMin));
        logReservationTick(reservationReqs, reservationMaxGrantees);
        int newGrantees = 0;
        for (ReservationRequest r : reservationReqs) {
            if (layerHoldsReservation(r.candidate.layerId)) {
                reconcileReservationsForLayer(r.candidate, r.fullHosts);
            } else if (newGrantees < reservationMaxGrantees) {
                reconcileReservationsForLayer(r.candidate, r.fullHosts);
                newGrantees++;
            }
        }
        if (newGrantees > 0) {
            logger.info("Scheduler resv-grant: newGrantees=" + newGrantees + " totalHeld="
                    + reservations.size());
        }
        tickGranted = newGrantees;
        lastReservationReqs = reservationReqs.size();
    }

    /**
     * DEBUG-only per-tick reservation summary, guarded so the string is never built when DEBUG is
     * off. INFO sees only actual new grants and the held count in the minute heartbeat.
     */
    private void logReservationTick(List<ReservationRequest> reservationReqs, int cap) {
        if (!logger.isDebugEnabled() || (reservationReqs.isEmpty() && reservations.isEmpty()))
            return;
        StringBuilder sb = new StringBuilder();
        sb.append("Scheduler resv-tick: requests=").append(reservationReqs.size()).append(" cap=")
                .append(cap).append(" held=").append(reservations.size())
                .append(" blockThresholdMs=").append(reservationBlockMs);
        if (!reservationReqs.isEmpty()) {
            sb.append(" top=[");
            int show = Math.min(3, reservationReqs.size());
            for (int i = 0; i < show; i++) {
                ReservationRequest rr = reservationReqs.get(i);
                long debt = blockedDebtMs.getOrDefault(rr.candidate.layerId, 0L);
                sb.append("layer=").append(rr.candidate.layerId).append("(cores=")
                        .append(rr.candidate.layerCoresMin).append(",waiting=")
                        .append(rr.candidate.waitingFrameCount).append(",debt=").append(debt)
                        .append("ms)");
                if (i < show - 1)
                    sb.append(", ");
            }
            sb.append("]");
        }
        logger.debug(sb.toString());
    }

    /**
     * Reset all tick-scoped planning scratch to empty. Defensive: a tick that throws mid-placement
     * leaves stale (host, layer) pairings and half-filled cap maps behind, and the next tick must
     * plan against a clean slate. The two read-fresh maps (tReadyByHost, hostLayerAffinity) are
     * reassigned in doTick, not cleared here.
     */
    private void clearTickScratch() {
        plannedByHost.clear();
        placedLayerIds.clear();
        jobCoresUsed.clear();
        showCoresUsed.clear();
        limitUsed.clear();
        folderUsed.clear();
        folderMaxCp.clear();
        folderRunSeed.clear();
        jobFolderCap.clear();
        layerLicenses.clear();
        licenseBudgets.clear();
        licenseUsed.clear();
        licenseSeats.clear();
        seenLayerIds.clear();
        reservationReqs.clear();
    }

    /**
     * Plan one host-spec group: run its single candidate query (a malformed layer tag fails only
     * this group, not the whole tick), seed the capped-folder trim data and this group's license
     * budgets, then dispatch-and-reconcile in priority order. Placement uses the group's idle
     * subset (hosts with the minimum reservable cores free); reservations use the full group so a
     * blocked layer can hold a busy host. Candidates are filtered against max host total cores, not
     * idle, so a layer blocked on a partially-loaded reserved host stays a candidate and its
     * reservation survives the end-of-tick sweep. Returns the frames booked for the group and bumps
     * the matching stats counter (queryError / noWork / booked / noFit).
     */
    private int planGroup(HostSpecKey spec, List<BookableHost> fullGroup,
            SchedulerMetrics.TickStats stats) {
        List<BookableHost> idleGroup = new ArrayList<>();
        for (BookableHost h : fullGroup) {
            if (h.coresIdle >= Dispatcher.CORE_POINTS_RESERVED_MIN)
                idleGroup.add(h);
        }
        int maxCoresTotalInGroup = fullGroup.stream().mapToInt(h -> h.coresTotal).max().orElse(0);

        List<LayerCandidate> candidates;
        try {
            candidates = readLayerCandidatesForGroup(spec, maxCoresTotalInGroup);
        } catch (RuntimeException e) {
            long nowMs = System.currentTimeMillis();
            if (nowMs - lastCandidateErrWarnMs >= GROUP_WARN_INTERVAL_MS) {
                lastCandidateErrWarnMs = nowMs;
                logger.warn("Scheduler: candidate query failed for " + spec
                        + "; skipping the group this tick. A malformed layer tag regex is"
                        + " the usual cause; the database error names the layer's tags: "
                        + e.getMessage());
            }
            stats.queryError++;
            return 0;
        }
        if (logger.isDebugEnabled())
            logGroupCandidates(spec, fullGroup, idleGroup, candidates, maxCoresTotalInGroup);
        if (candidates.isEmpty()) {
            stats.noWork++;
            return 0;
        }
        for (LayerCandidate lc : candidates) {
            if (lc.folderMax >= 0) {
                folderMaxCp.putIfAbsent(lc.folderId, lc.folderMax);
                folderRunSeed.putIfAbsent(lc.folderId, lc.folderRunning);
                jobFolderCap.putIfAbsent(lc.jobId, lc.folderId);
            }
        }
        resolveLicenseBudgets(candidates, layerLicenses, licenseBudgets);
        int booked = dispatchGroupWithScoring(idleGroup, fullGroup, candidates, seenLayerIds,
                jobCoresUsed, showCoresUsed, limitUsed, folderUsed, reservationReqs, tReadyByHost,
                hostLayerAffinity, licenseBudgets, licenseUsed, licenseSeats);
        if (booked > 0)
            stats.booked++;
        else
            stats.noFit++;
        return booked;
    }

    /**
     * DEBUG per-group candidate summary, logged before the empty-continue so a group that sits idle
     * with zero candidates (the classic "farm idle, nothing books" incident) is visible, with the
     * per-gate explain naming what excluded each pending layer.
     */
    private void logGroupCandidates(HostSpecKey spec, List<BookableHost> fullGroup,
            List<BookableHost> idleGroup, List<LayerCandidate> candidates,
            int maxCoresTotalInGroup) {
        int wideCount = 0;
        for (LayerCandidate lc : candidates)
            if (lc.layerCoresMin > 100)
                wideCount++;
        logger.debug("Scheduler group: " + spec + " hosts=" + fullGroup.size() + " idle="
                + idleGroup.size() + " maxCoresTotal=" + maxCoresTotalInGroup + " candidates="
                + candidates.size() + " wide(>100cores)=" + wideCount);
        if (candidates.isEmpty())
            explainGroupExclusions(spec, maxCoresTotalInGroup);
    }

    /**
     * One full scheduling pass. Runs on every Cuebot; only the leader plans.
     *
     * The stages: 0. drain the frame-completions queued since the last tick (every Cuebot, before
     * the leadership gate, so planning sees finished frames already stopped and never races an
     * in-flight completion); 1. snapshot every schedulable host (UP + OPEN), busy and idle, before
     * placement mutates the in-memory idle counts; 2. group the hosts by spec (allocation,
     * facility, tags, OS, GPU, thread mode) and record farm-fill and per-show cores for the stat
     * line; 3. plan each group in priority order against one candidate query per group, placing
     * into the idle subset while a layer that cannot fit collects a reservation request; 4. grant
     * reservations, plan the bookings in parallel, trim to the folder and license limits, commit
     * the survivors in one batch, and launch them. See Scheduler.md for the full model.
     *
     * @return frames committed this tick, or -1 for a standby that drained but did not plan.
     */
    private int doTick() {
        // 0. DRAIN the queued frame-completions (every Cuebot, leader and standby), then expire the
        // cache-warmth entries a window of foreign frames displaced on their host.
        summaryDrained += drainResolvedCompletions();
        expireDisplacedWarmth();

        // Leadership gate: a backup has now drained and idles here; only the leader plans below.
        if (!ensureLeadership()) {
            logger.debug("Scheduler: another Cuebot holds the planning lock");
            summaryLockLost++;
            return -1;
        }

        long tStart = System.currentTimeMillis();
        SchedulerMetrics.TickStats stats = new SchedulerMetrics.TickStats();
        lastTickStats = stats;
        resetTickOutputs();
        try {
            dispatchSupport.sweepOrphanedProcs(10);
        } catch (RuntimeException e) {
            logger.warn("Scheduler: orphan sweep failed: " + e);
        }
        clearTickScratch();

        // 1. SNAPSHOT all schedulable hosts (UP + OPEN), busy and idle.
        List<BookableHost> allHosts = readAllHosts();
        if (allHosts.isEmpty())
            return 0;
        snapshotFarmFill(allHosts);

        // 2. GROUP the hosts by spec.
        Map<HostSpecKey, List<BookableHost>> groups = groupByHostSpec(allHosts);
        lastGroups = groups.size();
        stats.groups = groups.size();
        stats.farmCores = (int) (lastCoresTotalCp / CORE_POINTS_PER_CORE);
        if (schedulerMetrics != null && schedulerMetrics.isEnabled())
            stats.coresByShow.putAll(readShowCores());
        warnIfGroupsFragmented(groups.size(), allHosts.size());

        // Tick-scoped snapshots: hostById is local; tReadyByHost and hostLayerAffinity are
        // read fresh into their fields; the cap/license/reservation scratch fields were reset
        // in clearTickScratch.
        Map<String, BookableHost> hostById = new HashMap<>();
        for (BookableHost h : allHosts)
            hostById.put(h.hostId, h);
        tReadyByHost = computeHostReadySeconds(hostById);
        hostLayerAffinity = readHostLayerAffinity();

        // 3. PLAN each host-spec group in priority order.
        int dispatched = 0;
        for (Map.Entry<HostSpecKey, List<BookableHost>> g : groups.entrySet())
            dispatched += planGroup(g.getKey(), g.getValue(), stats);

        grantReservations(reservationReqs);

        // 4. PLAN bookings in parallel, then trim to the exact folder + license limits.
        long tPlan = System.currentTimeMillis();
        List<FrameBooking> planned = planBookings();
        if (planned == null)
            return dispatched; // interrupted mid-plan; abort before committing
        planned = trimOverFolderCeiling(planned, folderMaxCp, folderRunSeed, jobFolderCap);
        planned = trimOverLicensePools(planned, licenseBudgets, layerLicenses);
        long tRead = System.currentTimeMillis();
        tickPlanned = planned.size();

        // 4b. COMMIT the survivors in one batch, then account and launch them.
        List<FrameBooking> committed =
                planned.isEmpty() ? java.util.Collections.<FrameBooking>emptyList()
                        : dispatchSupport.startFramesAndProcsBatch(planned);
        long tCommit = System.currentTimeMillis();
        recordCommitted(committed, stats);
        launchCommitted(committed);
        int dispatchedNow = committed.size();
        long tFlush = System.currentTimeMillis();
        if (tFlush - tStart > 1000) {
            logger.info("Scheduler tick breakdown: place=" + (tPlan - tStart) + "ms, read="
                    + (tRead - tPlan) + "ms, batchCommit=" + (tCommit - tRead) + "ms, flush+launch="
                    + (tFlush - tCommit) + "ms | placements=" + lastPlacements + " planned="
                    + planned.size() + " committed=" + dispatchedNow);
        }
        dispatched = dispatchedNow;

        sweepStaleReservationState(seenLayerIds);
        return dispatched;
    }

    /**
     * Read each planned placement's next frames and build procs in memory (no DB writes),
     * parallelized across hosts on the bounded read pool, the dominant tick cost as the farm fills.
     * One task per host (not one thread), run at scheduler.read_pool_size concurrency: a host is
     * booked serially within its task because planHost decrements that host's idle fields as it
     * books, so a later layer sees what an earlier one took, and two tasks on one host would
     * double-book it; different hosts run concurrently. A layer that plans but yields zero bookable
     * frames for plan_zero_warn_ticks ticks in a row is warned (a commit-time gate the planner does
     * not model is silently rejecting it, which would otherwise starve in silence). Returns the
     * planned bookings, or null if the wait was interrupted (the caller then aborts the tick before
     * committing).
     */
    private List<FrameBooking> planBookings() {
        int planZeroWarnTicks =
                env.getProperty("scheduler.plan_zero_warn_ticks", Integer.class, 40);
        lastPlacements = 0;
        Set<String> plannedLayerIds = new HashSet<>();
        for (List<String> ls : plannedByHost.values()) {
            lastPlacements += ls.size();
            plannedLayerIds.addAll(ls);
        }
        List<Callable<List<FrameBooking>>> tasks = new ArrayList<>(plannedByHost.size());
        for (Map.Entry<String, List<String>> e : plannedByHost.entrySet()) {
            final String hostId = e.getKey();
            final List<String> layerIds = e.getValue();
            tasks.add(() -> {
                List<FrameBooking> out = new ArrayList<>();
                DispatchHost host = hostManager.getDispatchHost(hostId);
                for (String layerId : layerIds) {
                    LayerInterface layer = jobManager.getLayer(layerId);
                    List<FrameBooking> got = dispatcher.planHost(host, layer);
                    if (got.isEmpty()) {
                        int streak = planZeroStreak.merge(layerId, 1, Integer::sum);
                        if (streak % planZeroWarnTicks == 0) {
                            logger.warn("Scheduler: layer " + layerId + " planned " + streak
                                    + " consecutive ticks (last host " + host.getName()
                                    + ") but planHost found 0 bookable frames each time."
                                    + " A dispatch-query gate the planner does not model is"
                                    + " rejecting it (thread mode, limit, local booking, ...):"
                                    + " enable DEBUG on this class and read the 'Scheduler"
                                    + " unplaced'/'explain' lines for the candidate-side view.");
                        }
                    } else {
                        planZeroStreak.remove(layerId);
                    }
                    out.addAll(got);
                }
                return out;
            });
        }
        plannedByHost.clear();

        List<FrameBooking> planned = new ArrayList<>();
        try {
            for (Future<List<FrameBooking>> f : readPool.invokeAll(tasks)) {
                try {
                    planned.addAll(f.get());
                } catch (ExecutionException ee) {
                    logger.debug("Scheduler: plan task failed: "
                            + (ee.getCause() != null ? ee.getCause().getMessage()
                                    : ee.getMessage()));
                }
            }
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            return null;
        }
        // Streaks matter only while the planner keeps choosing the layer; drop entries for
        // layers not planned this tick so the map tracks live pathologies, not vanished work.
        planZeroStreak.keySet().retainAll(plannedLayerIds);
        return planned;
    }

    /**
     * Fold the committed bookings into the per-show throughput tally, then apply their resource
     * accounting deltas and flush one UPDATE per changed row. Per-show cores are not accumulated
     * here (they are read live from the procs each tick, see readShowCores, so the gauge cannot
     * drift); only the per-show frame count for the rate is merged.
     */
    private void recordCommitted(List<FrameBooking> committed, SchedulerMetrics.TickStats stats) {
        for (FrameBooking b : committed) {
            stats.framesByShow.merge(b.frame.show, 1, Integer::sum);
        }
        if (batchResourceAccounting && !committed.isEmpty()) {
            List<VirtualProc> procs = new ArrayList<>(committed.size());
            for (FrameBooking b : committed)
                procs.add(b.proc);
            accumulateResourceDeltas(procs);
        }
        flushResourceDeltas();
    }

    /**
     * Launch the committed bookings: fire each one's RQD launch on the launch pool. A launch that
     * fails post-commit unbooks the proc, returns the frame to WAITING, and kills it on RQD, all on
     * the launch thread so the tick is never blocked.
     *
     * This is also where locality cache-warmth is stamped, since the committed set is in hand:
     * every commit advances its host's odometer (displacing older cache), and a layer returning to
     * its own warm host re-stamps its entry instead of displacing it.
     */
    private void launchCommitted(List<FrameBooking> committed) {
        if (localityEnabled && localityWindowFrames > 0) {
            for (FrameBooking b : committed) {
                long odo = bookingsByHost.merge(b.proc.getHostId(), 1L, Long::sum);
                if (b.proc.getLayerId() != null) {
                    String key = b.proc.getHostId() + "|" + b.proc.getLayerId();
                    if (warmthByHostLayer.containsKey(key)) {
                        warmthByHostLayer.put(key, odo);
                    }
                }
            }
        }
        for (FrameBooking b : committed) {
            final FrameBooking fb = b;
            launchPool.execute(() -> {
                try {
                    dispatchSupport.runFrame(fb.proc, fb.frame);
                } catch (RuntimeException e) {
                    logger.warn("Scheduler: RQD launch failed for " + fb.proc.getName()
                            + " on frame " + fb.frame.getFrameId() + ": " + e.getMessage()
                            + ", unbooking and clearing frame");
                    try {
                        dispatchSupport.unbookProc(fb.proc);
                        dispatchSupport.clearFrame(fb.frame);
                        rqdClient.killFrame(fb.proc, "launch failed during scheduler dispatch");
                    } catch (RuntimeException ce) {
                        logger.debug("Scheduler: launch-failure cleanup partial for "
                                + fb.frame.getFrameId() + ": " + ce.getMessage());
                    }
                }
            });
        }
    }

    // ---- leader lock ------------------------------------------------------

    /**
     * Ensure this Cuebot holds planning leadership, acquiring it once and keeping it (sticky).
     * Returns true if we are the leader this tick.
     *
     * If we are already leader (leaderConn set), confirm the lock connection is still alive. If it
     * is, we still hold the session-scoped advisory lock, so do not re-acquire it (the lock is
     * re-entrant and would then need matching unlocks). If the connection died, Postgres already
     * auto-released the lock, so demote to standby and re-probe next tick.
     *
     * If we are a standby (leaderConn null), try to take the lock on a fresh dedicated connection.
     * Winning makes us the sticky leader; losing means another Cuebot leads and we idle.
     *
     * The isValid() ping each tick doubles as a keepalive, so an otherwise-idle lock connection is
     * never dropped by a firewall/NAT idle timeout.
     */
    private boolean ensureLeadership() {
        Connection held = leaderConn;
        if (held != null) {
            try {
                if (held.isValid(1)) {
                    return true;
                }
            } catch (SQLException e) {
                // treated as dead below
            }
            logger.warn("Scheduler: planning-lock connection lost; demoting to standby");
            closeLeaderConn();
            return false;
        }
        Connection conn = null;
        try {
            conn = openLeaderConnection();
            if (acquireLeaderLock(conn)) {
                leaderConn = conn;
                logger.info("Scheduler: acquired planning leadership (sticky)");
                return true;
            }
            conn.close();
            return false;
        } catch (SQLException e) {
            logger.warn("Scheduler: leadership probe failed: " + e.getMessage());
            if (conn != null) {
                try {
                    conn.close();
                } catch (SQLException ignore) {
                    // best effort
                }
            }
            return false;
        }
    }

    /**
     * Open a dedicated Postgres connection for the leadership lock, outside the HikariCP pool. A
     * pooled connection would be reaped on idle-timeout or flagged by the leak-detection threshold
     * while we hold it across ticks, silently releasing the advisory lock. Built straight from the
     * configured JDBC url/credentials so the scheduler stays pool-implementation agnostic.
     */
    private Connection openLeaderConnection() throws SQLException {
        String url = env.getProperty("datasource.cue-data-source.jdbc-url");
        String user = env.getProperty("datasource.cue-data-source.username");
        String pass = env.getProperty("datasource.cue-data-source.password");
        Connection c = java.sql.DriverManager.getConnection(url, user, pass);
        c.setAutoCommit(true);
        return c;
    }

    /** Release (if the connection is still alive) and close the leadership connection. */
    private void closeLeaderConn() {
        Connection held = leaderConn;
        leaderConn = null;
        if (held != null) {
            releaseLeaderLock(held);
            try {
                held.close();
            } catch (SQLException ignore) {
                // best effort
            }
        }
    }

    /**
     * Bean lifecycle: give up leadership promptly on shutdown so a standby can take over without
     * waiting for the OS to tear down the socket.
     */
    public void onShutdown() {
        closeLeaderConn();
        LicenseSource ls = licenseSource;
        if (ls != null)
            ls.stop();
    }

    private boolean acquireLeaderLock(Connection conn) throws SQLException {
        try (PreparedStatement ps = conn.prepareStatement("SELECT pg_try_advisory_lock(?)")) {
            ps.setLong(1, SCHEDULER_LOCK_KEY);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() && rs.getBoolean(1);
            }
        }
    }

    private void releaseLeaderLock(Connection conn) {
        try (PreparedStatement ps = conn.prepareStatement("SELECT pg_advisory_unlock(?)")) {
            ps.setLong(1, SCHEDULER_LOCK_KEY);
            ps.execute();
        } catch (SQLException e) {
            // If the connection dropped, the backend session ended and the
            // lock was released automatically.
            logger.debug("Scheduler: pg_advisory_unlock failed (probably connection drop): "
                    + e.getMessage());
        }
    }

    // ---- snapshot reads ---------------------------------------------------

    /**
     * All schedulable hosts (UP + OPEN), busy or idle. The idle subset used for placement is
     * derived per group in doTick().
     */
    /* package for tests */ List<BookableHost> readAllHosts() {
        return getJdbcTemplate().query(SELECT_ALL_HOSTS, HOST_MAPPER);
    }

    // Cores actually running per show, summed straight from the live procs. This
    // is the ground truth OpenCue itself uses to recompute subscriptions, so the
    // show_cores gauge is set from it each tick rather than event-sourced: no
    // drift, no missed-decrement bookkeeping. Non-local procs only, matching how
    // farm cores are counted elsewhere.
    private static final String SELECT_SHOW_CORES =
            "SELECT sh.str_name AS show_name, SUM(p.int_cores_reserved) AS cores "
                    + "FROM proc p JOIN show sh ON sh.pk_show = p.pk_show "
                    + "WHERE p.b_local = false GROUP BY sh.str_name";

    /** Whole cores running per show right now, read live from the procs. */
    /* package for tests */ Map<String, Double> readShowCores() {
        Map<String, Double> byShow = new HashMap<>();
        getJdbcTemplate().query(SELECT_SHOW_CORES, rs -> {
            byShow.put(rs.getString("show_name"),
                    rs.getLong("cores") / (double) CORE_POINTS_PER_CORE);
        });
        return byShow;
    }

    /**
     * Host->layer affinity: which layers currently have at least one proc booked on each host.
     * Drives the locality bonus (see {@link #localityBonus}). A proc carries pk_layer directly, so
     * no join is needed. A just-completed proc has been unbooked (row deleted), so only live
     * placements appear.
     */
    private Map<String, Set<String>> readHostLayerAffinity() {
        Map<String, Set<String>> affinity = new HashMap<>();
        if (!localityEnabled)
            return affinity;
        getJdbcTemplate().query("SELECT pk_host, pk_layer FROM proc WHERE pk_layer IS NOT NULL",
                rs -> {
                    affinity.computeIfAbsent(rs.getString("pk_host"), k -> new HashSet<>())
                            .add(rs.getString("pk_layer"));
                });
        return affinity;
    }

    // Max pending layers the "why nothing books" explain logs per group, highest priority first.
    private static final int EXPLAIN_LIMIT = 20;

    /**
     * DEBUG-only "why is nothing booking" explain: the candidate query's WHERE clauses recast as
     * per-layer boolean columns, so when a group yields zero candidates one tick of DEBUG logging
     * names the exact gate that excluded each pending layer (the first false column). Keeps every
     * eligibility rule in one visible line instead of hand-written SQL against a live incident. The
     * subscription join is LEFT here (unlike the real query) precisely so a missing subscription
     * shows up as hasSub=false instead of an invisible row; each column mirrors its production
     * clause (os = ANY of the host's comma-separated list, facility bind, smallest-cap limit).
     */
    private static final String EXPLAIN_GROUP_EXCLUSIONS = "SELECT " + "  j.str_name AS job_name, "
            + "  l.str_name AS layer_name, " + "  l.str_tags, " + "  jr.int_priority, "
            + "  (? ~* ('(?x)' || l.str_tags || '\\y'))               AS tag_ok, "
            + "  (j.str_os IS NULL OR j.str_os = '' "
            + "   OR j.str_os = ANY(string_to_array(?, ',')))         AS os_ok, "
            + "  (j.pk_facility = ?)                                  AS fac_ok, "
            + "  ((CASE WHEN l.b_threadable = true THEN 1 ELSE 0 END) >= ?) AS thread_ok, "
            + "  (sub.pk_subscription IS NOT NULL)                    AS has_sub, "
            + "  (sub.int_cores < sub.int_burst)                      AS under_burst, "
            + "  (jr.int_cores < jr.int_max_cores)                    AS under_job_cap, "
            + "  (l.int_cores_min <= ?)                               AS fits_cores, "
            + "  (COALESCE(ls.int_waiting_count, 0) > 0)              AS has_waiting, "
            + "  (NOT EXISTS (" + "     SELECT 1 FROM layer_limit ll "
            + "     JOIN limit_record lr ON lr.pk_limit_record = ll.pk_limit_record "
            + "     WHERE ll.pk_layer = l.pk_layer "
            + "       AND (SELECT COALESCE(SUM(ls2.int_running_count), 0) FROM layer_limit ll2 "
            + "            JOIN layer_stat ls2 ON ls2.pk_layer = ll2.pk_layer "
            + "            WHERE ll2.pk_limit_record = lr.pk_limit_record) >= lr.int_max_value)) "
            + "                                                       AS limit_ok, "
            + "  (COALESCE(fr.int_max_cores, -1) = -1 "
            + "   OR (SELECT COALESCE(SUM(ls3.int_running_count * l3.int_cores_min), 0) "
            + "       FROM job j3 JOIN layer l3 ON l3.pk_job = j3.pk_job "
            + "       JOIN layer_stat ls3 ON ls3.pk_layer = l3.pk_layer "
            + "       WHERE j3.pk_folder = j.pk_folder AND j3.str_state = 'PENDING') "
            + "      + l.int_cores_min <= fr.int_max_cores)           AS folder_ok, "
            + "  (? OR sh.b_scheduler_managed = true)                 AS managed_ok "
            + "FROM layer l " + "JOIN job j            ON j.pk_job = l.pk_job "
            + "JOIN job_resource jr  ON jr.pk_job = j.pk_job "
            + "JOIN show sh          ON sh.pk_show = j.pk_show "
            + "LEFT JOIN subscription sub ON sub.pk_show = j.pk_show AND sub.pk_alloc = ? "
            + "LEFT JOIN layer_stat ls    ON ls.pk_layer = l.pk_layer "
            + "LEFT JOIN folder_resource fr ON fr.pk_folder = j.pk_folder "
            + "WHERE j.str_state = 'PENDING' AND j.b_paused = false "
            + "ORDER BY jr.int_priority DESC " + "LIMIT " + EXPLAIN_LIMIT;

    /** Log the explain rows for a group that produced no candidates. DEBUG-gated by the caller. */
    private void explainGroupExclusions(HostSpecKey spec, int maxCoresTotalInGroup) {
        getJdbcTemplate().query(EXPLAIN_GROUP_EXCLUSIONS, rs -> {
            logger.debug("Scheduler explain " + spec + ": job=" + rs.getString("job_name")
                    + " layer=" + rs.getString("layer_name") + " prio=" + rs.getInt("int_priority")
                    + " tags='" + rs.getString("str_tags") + "' tagOk=" + rs.getBoolean("tag_ok")
                    + " osOk=" + rs.getBoolean("os_ok") + " facOk=" + rs.getBoolean("fac_ok")
                    + " threadOk=" + rs.getBoolean("thread_ok") + " hasSub="
                    + rs.getBoolean("has_sub") + " underBurst=" + rs.getBoolean("under_burst")
                    + " underJobCap=" + rs.getBoolean("under_job_cap") + " fitsCores="
                    + rs.getBoolean("fits_cores") + " hasWaiting=" + rs.getBoolean("has_waiting")
                    + " limitOk=" + rs.getBoolean("limit_ok") + " folderOk="
                    + rs.getBoolean("folder_ok") + " managedOk=" + rs.getBoolean("managed_ok"));
        }, spec.tagsNormalized, spec.os, spec.pkFacility, spec.allThreadMode ? 1 : 0,
                maxCoresTotalInGroup, SchedulerMode.facility(env), spec.pkAlloc);
    }

    /**
     * Record which of these candidates need application licenses, and make sure a budget exists for
     * every pool they name.
     *
     * The license names already arrived on the candidate rows (the candidate query carries them),
     * so this costs nothing but a walk of the list. Budgets are the part that touches the database
     * (the in-flight term), so they are derived once per license per tick: a pool named by an
     * earlier group is reused by every later one, which also keeps the numbers consistent across
     * groups within a tick. Both maps are tick-scoped and planner-thread only.
     */
    private void resolveLicenseBudgets(List<LayerCandidate> candidates,
            Map<String, List<String>> layerLicenses,
            Map<String, LicenseSource.LicenseBudget> licenseBudgets) {
        Set<String> fresh = null;
        for (LayerCandidate c : candidates) {
            if (c.licenses == null)
                continue;
            layerLicenses.put(c.layerId, c.licenses);
            for (String name : c.licenses) {
                if (!licenseBudgets.containsKey(name)) {
                    if (fresh == null)
                        fresh = new HashSet<>();
                    fresh.add(name);
                }
            }
        }
        if (fresh == null)
            return;
        LicenseSource ls = licenseSource;
        if (ls == null) {
            // No source at all (a tick before init). Hold rather than run blind.
            for (String name : fresh) {
                licenseBudgets.put(name, new LicenseSource.LicenseBudget(name, false, 0, 0,
                        Collections.emptySet(), true));
            }
            return;
        }
        licenseBudgets.putAll(ls.snapshotBudgets(fresh));
    }

    /**
     * May this host take a frame of a layer whose licenses include host-based pools?
     *
     * Yes when, for every such pool, the host either already holds a seat (extra frames there are
     * free, they share the one checkout) or the pool still has an unused seat. The seat set
     * includes seats the license server reports held by machines outside the cue, so an artist's
     * workstation occupies a seat here just as a render node does.
     */
    private static boolean licenseSeatsAllow(List<LicenseSource.LicenseBudget> pools,
            Map<String, Set<String>> licenseSeats, BookableHost h) {
        String hostName = h.hostName.toLowerCase();
        for (LicenseSource.LicenseBudget b : pools) {
            Set<String> seats = licenseSeats.get(b.name);
            if (seats.contains(hostName))
                continue;
            if (seats.size() >= b.seatCap)
                return false;
        }
        return true;
    }

    /* package for tests */ List<LayerCandidate> readLayerCandidatesForGroup(HostSpecKey spec,
            int maxIdleInGroup) {
        int limit =
                env.getProperty("scheduler.layer_candidates_per_group_max", Integer.class, 2000);
        LicenseSource ls = licenseSource;
        String licenseKey = (ls != null) ? ls.getEnvKey() : "CUE_LICENSES";
        List<LayerCandidate> rows =
                getJdbcTemplate().query(SELECT_CANDIDATES_FOR_GROUP, CANDIDATE_MAPPER, spec.pkAlloc,
                        licenseKey, spec.os, spec.pkFacility, spec.allThreadMode ? 1 : 0,
                        spec.tagsNormalized, maxIdleInGroup, SchedulerMode.facility(env), limit);
        // Defensive dedupe: nothing in the schema forbids two layer_env rows
        // with the same key, and a duplicated row would clone its candidate
        // (double placement per tick). First row per layer wins.
        Set<String> seen = new HashSet<>(rows.size() * 2);
        List<LayerCandidate> out = new ArrayList<>(rows.size());
        for (LayerCandidate c : rows) {
            if (seen.add(c.layerId))
                out.add(c);
        }
        return out;
    }

    /**
     * EASY backfill deadline per reserved host: seconds from now until the host is projected to
     * have freed enough cores for its reserving (wide) layer.
     *
     * For each reserved host, the running procs are projected to finish at
     * {@code avg_layer_runtime - elapsed} (avg = layer_usage.int_clock_time_success /
     * int_frame_success_count). Procs are taken soonest-first and their cores accumulated until the
     * reserving layer's core deficit is covered; that proc's projected finish is the host's ready
     * time. The deadline is the bar a borrowed frame must beat (see {@link #backfillAllows}).
     *
     * Conservative by construction. A host whose needed procs lack a runtime estimate maps to
     * {@link Integer#MAX_VALUE} (unknown, so never backfill). Ready time uses the procs' average
     * finish while the borrowed frame is bounded by its worst case (int_clock_time_high); requiring
     * worst(frame) <= avg(host-ready) heavily biases against delaying the reserved job (high is
     * typically well above avg).
     *
     * Cores-only: cores are the binding dimension for the wide-job stranding this targets;
     * memory/GPU readiness is not modelled here.
     *
     * Uses the snapshot's idle values, so it must run before the tick mutates them. Empty when
     * backfill is off or there are no reservations.
     */
    private Map<String, Integer> computeHostReadySeconds(Map<String, BookableHost> hostById) {
        Map<String, Integer> ready = new HashMap<>();
        if (!backfillEnabled || reservations.isEmpty())
            return ready;

        List<String> hostIds = new ArrayList<>(reservations.keySet());
        String in = hostIds.stream().map(x -> "?").collect(Collectors.joining(","));
        String sql = "SELECT p.pk_host AS pk_host, p.int_cores_reserved AS cores, "
                + "EXTRACT(EPOCH FROM (now() - p.ts_dispatched))::int AS elapsed_sec, "
                + "CASE WHEN lu.int_frame_success_count > 0 "
                + "     THEN lu.int_clock_time_success / lu.int_frame_success_count "
                + "     ELSE -1 END AS avg_sec " + "FROM proc p "
                + "LEFT JOIN layer_usage lu ON lu.pk_layer = p.pk_layer " + "WHERE p.pk_host IN ("
                + in + ")";

        // Per host: list of {coresFreed, secondsUntilFree} for each running proc.
        Map<String, List<int[]>> procsByHost = new HashMap<>();
        getJdbcTemplate().query(sql, rs -> {
            String hid = rs.getString("pk_host");
            int cores = rs.getInt("cores");
            int elapsed = rs.getInt("elapsed_sec");
            int avg = rs.getInt("avg_sec");
            int remaining = (avg < 0) ? Integer.MAX_VALUE : Math.max(0, avg - elapsed);
            procsByHost.computeIfAbsent(hid, k -> new ArrayList<>())
                    .add(new int[] {cores, remaining});
        }, hostIds.toArray());

        for (Map.Entry<String, Reservation> e : reservations.entrySet()) {
            String hid = e.getKey();
            BookableHost h = hostById.get(hid);
            if (h == null)
                continue; // reserved host not in this tick's snapshot
            int need = e.getValue().layerCoresMin - h.coresIdle;
            ready.put(hid, hostReadySeconds(need, procsByHost.get(hid)));
        }
        return ready;
    }

    // ---- grouping ---------------------------------------------------------

    static Map<HostSpecKey, List<BookableHost>> groupByHostSpec(List<BookableHost> hosts) {
        Map<HostSpecKey, List<BookableHost>> groups = new LinkedHashMap<>();
        for (BookableHost h : hosts) {
            HostSpecKey k = new HostSpecKey(h.pkAlloc, h.pkFacility,
                    // Cuebot auto-adds each host's own name as a tag. Drop it
                    // from the grouping key, otherwise every host falls into a
                    // group of one and the per-group candidate query runs once
                    // per host instead of once per real spec.
                    normalizeTags(h.tagsRaw, h.hostName), h.os,
                    // GPU presence is a static hardware property: use totals,
                    // not idle. A fully-booked GPU host (gpusIdle == 0) must
                    // still group as a GPU host so its candidate query filters
                    // for GPU layers and the GPU-weighted score protects it.
                    h.gpusTotal > 0 || h.gpuMemTotal > 0, h.threadMode == ThreadMode.ALL_VALUE);
            groups.computeIfAbsent(k, x -> new ArrayList<>()).add(h);
        }
        return groups;
    }

    /**
     * Normalize a host's whitespace-separated tag string so equivalent sets ("linux desktop" and
     * "desktop linux") group together. Duplicate tags are collapsed.
     */
    static String normalizeTags(String raw) {
        return normalizeTags(raw, null);
    }

    /**
     * As {@link #normalizeTags(String)}, but also drops any tag equal to {@code excludeName}
     * (case-insensitive), used to strip a host's auto-added name tag so it doesn't fracture the
     * grouping.
     */
    static String normalizeTags(String raw, String excludeName) {
        if (raw == null || raw.trim().isEmpty())
            return "";
        return Arrays.stream(raw.trim().split("\\s+")).filter(t -> !t.equalsIgnoreCase(excludeName))
                .distinct().sorted().collect(Collectors.joining(" "));
    }

    // ---- placement: layer-driven, best-fit -------------------------------

    /**
     * Layer-driven placement with persistent reservations. For each candidate in priority order:
     *
     * 1. Dispatch loop: score every fitting host (respecting reservations) with
     * {@link #placementScore} and pick the one with the lowest score. Dispatch via
     * {@code dispatcher.dispatchHost(host, layer)}. If the chosen host carried a lower-priority
     * reservation, override it to c. Loop until no fitting host, no waiting frames, or the job/show
     * cap is reached. 2. Reconcile: c's reservation count should equal c.waitingFrameCount
     * (decremented as we dispatched). Drop excess; claim more if short.
     *
     * Layer ids are recorded in {@code seenLayerIds} so the end-of-tick sweep can drop reservations
     * for layers that left the dispatchable set.
     */
    private int dispatchGroupWithScoring(List<BookableHost> hosts, List<BookableHost> fullHosts,
            List<LayerCandidate> candidates, Set<String> seenLayerIds,
            Map<String, Integer> jobCoresUsed, Map<String, Integer> showCoresUsed,
            Map<String, Integer> limitUsed, Map<String, Integer> folderUsed,
            List<ReservationRequest> reservationReqs, Map<String, Integer> tReadyByHost,
            Map<String, Set<String>> hostLayerAffinity,
            Map<String, LicenseSource.LicenseBudget> licenseBudgets,
            Map<String, Integer> licenseUsed, Map<String, Set<String>> licenseSeats) {
        int dispatched = 0;
        boolean metricsFrag = schedulerMetrics != null && schedulerMetrics.isEnabled();
        // Largest host in this group, for the reservation width gate below: a
        // layer may reserve only if its per-frame cores are a big enough fraction
        // of this. Uses fullHosts (idle + busy) so the bar reflects the class's
        // real top-end capacity, not just what happens to be idle this tick.
        int maxGroupHostCores = 0;
        for (BookableHost h : fullHosts) {
            if (h.coresTotal > maxGroupHostCores)
                maxGroupHostCores = h.coresTotal;
        }
        // Cause the highest-priority layer that wanted work could not place; the
        // idle cores it strands are charged to it once per group after the loop.
        String fragReason = null;
        for (LayerCandidate c : candidates) {
            seenLayerIds.add(c.layerId);

            // Cross-group dedup: skip a layer already placed in an earlier host-spec group this
            // tick, whose per-host plan read would pull the same waiting frames and lose the
            // commit-time frame.int_version race. Placed after seenLayerIds.add (so the sweep still
            // sees the layer) and before any host/cap mutation. Keyed on placement, so a layer
            // capped or unfit in an earlier group is still tried here.
            if (placedLayerIds.contains(c.layerId))
                continue;

            // Sync this candidate's job/show usage with the tick-wide totals
            // before any cap check: seed from the DB snapshot the first time
            // a job/show is seen, then read back the accumulated value so
            // earlier dispatches of the same job/show (here or in another
            // group) count against this candidate's caps.
            c.jobCoresInUse = jobCoresUsed.computeIfAbsent(c.jobId, k -> c.jobCoresInUse);
            c.showCoresInUse = showCoresUsed.computeIfAbsent(c.showId, k -> c.showCoresInUse);
            // Seed this limit's tick-wide running count from the farm-wide count
            // the first time it is seen this tick (candidate query already
            // excluded limits that were full at query time; this catches a limit
            // filling during the tick as sibling layers book against it).
            int limitInUse =
                    (c.limitId != null) ? limitUsed.computeIfAbsent(c.limitId, k -> c.limitRunning)
                            : 0;

            // Live application licenses: a layer needs a seat in every pool it
            // declares. Floating pools allow the minimum of their remaining counts;
            // host-based pools are enforced per host in the scoring loop. A
            // stale or unreported pool holds the layer, never runs it blind.
            int licenseUsable = Integer.MAX_VALUE;
            boolean licenseHeld = false;
            List<LicenseSource.LicenseBudget> licenseSeatPools = null;
            if (c.licenses != null) {
                for (String licName : c.licenses) {
                    LicenseSource.LicenseBudget b = licenseBudgets.get(licName);
                    if (b == null || b.stale) {
                        licenseHeld = true;
                        break;
                    }
                    if (b.hostBased) {
                        if (licenseSeatPools == null)
                            licenseSeatPools = new ArrayList<>(2);
                        licenseSeatPools.add(b);
                        licenseSeats.computeIfAbsent(licName, k -> new HashSet<>(b.seats));
                    } else {
                        int remaining = b.usable - licenseUsed.computeIfAbsent(licName, k -> 0);
                        if (remaining < licenseUsable)
                            licenseUsable = remaining;
                    }
                }
            }
            // Same for the folder core ceiling (cores, not frames). Only tracked
            // when the folder actually has a cap (folderMax >= 0; -1 = unlimited).
            int folderInUse = (c.folderMax >= 0)
                    ? folderUsed.computeIfAbsent(c.folderId, k -> c.folderRunning)
                    : 0;

            // A capped layer (job/show cap, full limit, folder ceiling) must
            // not dispatch but must still reconcile, dropping reservations it
            // can no longer use so other work can take those hosts.
            boolean capped = c.jobCoresInUse + c.layerCoresMin > c.jobMaxCores
                    || c.showCoresInUse + c.layerCoresMin > c.showBurstCores
                    || (c.limitId != null && limitInUse >= c.limitMax)
                    || (c.folderMax >= 0 && folderInUse + c.layerCoresMin > c.folderMax)
                    || licenseHeld || licenseUsable <= 0;
            if (c.licenses != null && (licenseHeld || licenseUsable <= 0))
                tickLicenseHeld++;

            boolean placed = false;
            while (!capped) {
                BookableHost best = null;
                double bestScore = Double.POSITIVE_INFINITY;
                for (BookableHost h : hosts) {
                    if (!fitsOnHost(c, h))
                        continue;
                    // Same gate for a host-based license pool, but keyed by host
                    // name (what a license server reports) and against the live
                    // seat count rather than a typed-in cap: this host is
                    // eligible only if it already holds a seat in every such
                    // pool, or the pool still has a seat to give out.
                    if (licenseSeatPools != null
                            && !licenseSeatsAllow(licenseSeatPools, licenseSeats, h))
                        continue;
                    // A reserved host is off-limits unless EASY backfill can
                    // borrow it without delaying the reservation's owner.
                    if (!reservationAllows(h, c)) {
                        if (!backfillAllows(h, c, tReadyByHost))
                            continue;
                    }
                    double score = placementScore(h, c);
                    // Locality bonus: prefer a host already running this layer so
                    // a freed core is refilled by the same layer (same-machine
                    // locality, formerly the reactive DispatchNextFrame path).
                    if (localityEnabled) {
                        Set<String> layersHere = hostLayerAffinity.get(h.hostId);
                        if (layersHere != null && layersHere.contains(c.layerId)) {
                            score -= localityBonus;
                        } else if (localityWindowFrames > 0) {
                            // Cache warmth: the host ran this layer and few
                            // foreign frames displaced its cache since, so
                            // pull the layer back with a decayed bonus. Never
                            // larger than the live bonus; fit/reservations
                            // are filtered before scoring.
                            Long seen = warmthByHostLayer.get(h.hostId + "|" + c.layerId);
                            if (seen != null) {
                                long foreign = bookingsByHost.getOrDefault(h.hostId, 0L) - seen;
                                if (foreign >= 0 && foreign < localityWindowFrames) {
                                    score -= localityBonus
                                            * (1.0 - (double) foreign / localityWindowFrames);
                                }
                            }
                        }
                    }
                    // Seat bonus for host-based license pools: packing onto an
                    // already-seated machine consumes no new seat, which is the
                    // whole point when seats are the scarce resource. Applied per
                    // pool, so a host seated in all of the layer's pools outranks
                    // one seated in only some. Stacks with the locality bonus.
                    if (licenseSeatPools != null) {
                        String hName = h.hostName.toLowerCase();
                        for (LicenseSource.LicenseBudget b : licenseSeatPools) {
                            if (licenseSeats.get(b.name).contains(hName))
                                score -= licenseSeatBonus;
                        }
                    }
                    if (score < bestScore) {
                        bestScore = score;
                        best = h;
                    }
                }
                if (best == null)
                    break; // no host can fit this layer

                // Estimate how many frames this commit will book. The
                // dispatcher books up to job_frame_dispatch_max per call,
                // bounded by the same fit checks placementScore uses.
                long maxMore = computeMaxMore(best, c);
                int estFrames = (int) Math.min(jobFrameDispatchMax, maxMore + 1);
                // Never dispatch more frames than the layer has waiting, or
                // the batch commit gets padded with bookings that find
                // nothing.
                if (estFrames > c.waitingFrameCount)
                    estFrames = c.waitingFrameCount;
                if (estFrames <= 0)
                    break;
                // Cap the commit to the limit's remaining headroom. The tick-wide
                // count is authoritative: sibling layers of the same limit may
                // already have booked against it this tick. If it is now full,
                // stop booking this layer (its later frames would find nothing).
                if (c.limitId != null) {
                    int limHeadroom = c.limitMax - limitUsed.get(c.limitId);
                    if (limHeadroom <= 0)
                        break;
                    if (estFrames > limHeadroom)
                        estFrames = limHeadroom;
                }
                // Cap the commit to the licenses' remaining seats. licenseUsable is
                // the minimum across the layer's floating pools and is decremented as
                // this tick books, so sibling layers sharing a pool cannot each
                // spend it. One frame is one seat.
                if (licenseUsable != Integer.MAX_VALUE) {
                    if (licenseUsable <= 0)
                        break;
                    if (estFrames > licenseUsable)
                        estFrames = licenseUsable;
                }
                // Cap the commit to the folder's remaining core headroom (this cap
                // is in cores, not frames). If one more frame's cores won't fit,
                // stop booking this layer this tick.
                if (c.folderMax >= 0) {
                    int folderHeadroom = c.folderMax - folderUsed.get(c.folderId);
                    if (folderHeadroom < c.layerCoresMin)
                        break;
                    int maxByFolder = folderHeadroom / c.layerCoresMin;
                    if (estFrames > maxByFolder)
                        estFrames = maxByFolder;
                }

                int estCores = estFrames * c.layerCoresMin;
                long estMem = (long) estFrames * c.layerMemMin;
                int estGpus = estFrames * c.layerGpusMin;
                long estGpuMem = (long) estFrames * c.layerGpuMemMin;

                best.coresIdle -= estCores;
                best.memIdle -= estMem;
                best.gpusIdle -= estGpus;
                best.gpuMemIdle -= estGpuMem;
                c.jobCoresInUse += estCores;
                c.showCoresInUse += estCores;
                c.waitingFrameCount -= estFrames;
                // Publish back so other candidates of the same job/show this
                // tick see the updated usage.
                jobCoresUsed.put(c.jobId, c.jobCoresInUse);
                showCoresUsed.put(c.showId, c.showCoresInUse);
                if (c.limitId != null)
                    limitUsed.merge(c.limitId, estFrames, Integer::sum);
                if (c.folderMax >= 0)
                    folderUsed.merge(c.folderId, estCores, Integer::sum);
                // Spend the licenses: a frame is a seat in each floating pool, and
                // this host now holds a seat in each host-based one. Both are
                // tick-wide so every later candidate of the same pool, in any
                // group, sees the spend.
                if (c.licenses != null) {
                    if (licenseUsable != Integer.MAX_VALUE)
                        licenseUsable -= estFrames;
                    for (String licName : c.licenses) {
                        LicenseSource.LicenseBudget b = licenseBudgets.get(licName);
                        if (b == null)
                            continue;
                        if (b.hostBased) {
                            Set<String> seats = licenseSeats.get(licName);
                            if (seats.add(best.hostName.toLowerCase())) {
                                logger.info("Scheduler license: new seat " + seats.size() + "/"
                                        + b.seatCap + " on host " + best.hostName + " for license "
                                        + licName);
                            }
                        } else {
                            licenseUsed.merge(licName, estFrames, Integer::sum);
                        }
                    }
                    tickLicenseBooked += estFrames;
                }

                // Count an EASY-backfill borrow for the stat line: this host
                // is reserved for someone else and only backfillAllows let us
                // in.
                if (!reservationAllows(best, c)) {
                    tickBackfilled++;
                    tickBackfilledCores += estCores;
                }

                // If the host carried a lower-priority reservation,
                // take ownership. A reservation by c or by anyone equal
                // or higher is preserved (the second case can't happen
                // here because reservationAllows already excluded it).
                Reservation existing = reservations.get(best.hostId);
                if (existing != null && existing.priority < c.priority) {
                    reservations.put(best.hostId,
                            new Reservation(c.layerId, c.priority, c.layerCoresMin));
                }

                submitCommit(best.hostId, c.layerId);
                dispatched += estFrames;
                placed = true;

                // One commit per layer per tick: parallel per-host plan reads
                // would otherwise grab the same frames (version collisions).
                // A layer spreads across hosts over a few ticks instead.
                break;
            }

            // Why-not trace: one DEBUG line per candidate that wanted work but
            // placed nothing this tick, naming the binding constraint in the
            // same precedence the cap check uses. With the group summary and
            // the zero-candidate explain, one DEBUG tick tells the whole story
            // of a layer that books under the legacy dispatcher but not here.
            if (logger.isDebugEnabled() && !placed && c.waitingFrameCount > 0) {
                String why;
                if (c.jobCoresInUse + c.layerCoresMin > c.jobMaxCores)
                    why = "jobMaxCores";
                else if (c.showCoresInUse + c.layerCoresMin > c.showBurstCores)
                    why = "showBurst";
                else if (c.limitId != null && limitInUse >= c.limitMax)
                    why = "limitFull(" + limitInUse + "/" + c.limitMax + ")";
                else if (c.folderMax >= 0 && folderInUse + c.layerCoresMin > c.folderMax)
                    why = "folderCap(" + folderInUse + "/" + c.folderMax + ")";
                else if (licenseHeld)
                    why = "licenseHeld(stale or unreported pool: " + c.licenses + ")";
                else if (licenseUsable <= 0)
                    why = "licenseNoFloatingSeats(" + c.licenses + ")";
                else if (licenseSeatPools != null)
                    why = "noFittingIdleHost(seat-gated pools present)";
                else
                    why = "noFittingIdleHost";
                logger.debug("Scheduler unplaced: layer=" + c.layerId + " prio=" + c.priority
                        + " cores=" + c.layerCoresMin + " memKb=" + c.layerMemMin + " waiting="
                        + c.waitingFrameCount + " why=" + why);
            }

            // Fragmentation cause: the first layer (priority order) that wanted work
            // but could not place names why the group's idle cores are stranded. A
            // job/show/limit/folder cap is `quota`; an exhausted license pool is
            // `license`; otherwise the first fit gate no host clears (cores/memory/
            // gpu), or a fitting host held by a reservation (`held`) or a host-based
            // seat (`license`). The cores it strands are summed once below (supply),
            // not the layer's backlog, so the metric stays bounded by the farm.
            if (metricsFrag && fragReason == null && !placed && c.waitingFrameCount > 0) {
                boolean quotaCap = c.jobCoresInUse + c.layerCoresMin > c.jobMaxCores
                        || c.showCoresInUse + c.layerCoresMin > c.showBurstCores
                        || (c.limitId != null && limitInUse >= c.limitMax)
                        || (c.folderMax >= 0 && folderInUse + c.layerCoresMin > c.folderMax);
                if (quotaCap) {
                    fragReason = "quota";
                } else if (licenseHeld || licenseUsable <= 0) {
                    fragReason = "license";
                } else {
                    fragReason = classifyFragmentation(c, hosts);
                    if ("fit".equals(fragReason))
                        fragReason = fitGateReason(c, hosts, licenseSeatPools, licenseSeats);
                }
            }

            if (reservationsEnabled) {
                // Blocked = waiting frames, not capped, placed nothing. A layer
                // at its seat cap counts as capped, not blocked: reserving new
                // hosts could never help it, so it must not accrue debt.
                boolean blocked = !capped && !placed && c.waitingFrameCount > 0;
                long now = System.currentTimeMillis();
                long dt = now - lastSeenMs.getOrDefault(c.layerId, now);
                lastSeenMs.put(c.layerId, now);
                long debt = blockedDebtMs.getOrDefault(c.layerId, 0L);
                debt = blocked ? debt + dt : Math.max(0, debt - dt);
                blockedDebtMs.put(c.layerId, debt);

                // Request a reservation if the layer already holds some (keep
                // maintaining them until the job drains) or it newly qualifies:
                // blocked past the threshold and wide enough. The width gate
                // keeps the small-frame stream out of the wide-job budget.
                boolean wideEnough = maxGroupHostCores > 0
                        && c.layerCoresMin >= RESERVATION_MIN_HOST_FRACTION * maxGroupHostCores;
                boolean qualified = blocked && debt >= reservationBlockMs && wideEnough;
                boolean holdsResv = layerHoldsReservation(c.layerId);
                if (holdsResv || qualified) {
                    reservationReqs.add(new ReservationRequest(c, fullHosts));
                }
                // Trace reservation decisions for every candidate so we can
                // see why wide-job layers never accumulate enough debt.
                if (logger.isDebugEnabled()) {
                    logger.debug("Scheduler resv-candidate: layer=" + c.layerId + " coresMin="
                            + c.layerCoresMin + " waiting=" + c.waitingFrameCount + " capped="
                            + capped + " placed=" + placed + " blocked=" + blocked + " debt=" + debt
                            + "ms threshold=" + reservationBlockMs + "ms" + " wide=" + wideEnough
                            + " (coresMin=" + c.layerCoresMin + " gate="
                            + (RESERVATION_MIN_HOST_FRACTION * maxGroupHostCores) + ")" + " holds="
                            + holdsResv + " qualifies=" + (holdsResv || qualified));
                }
            }
        }

        // Stranded idle cores: when this group could not place work it wanted to
        // run, the idle cores left on its working hosts are wasted capacity, charged
        // to that cause. Only hosts with a core already in use can be fragmented (a
        // wholly-empty host is one free block, not a stranded sliver), so empty
        // hosts are skipped. The panel normalizes this against the whole farm, so a
        // little waste on one busy host reads as a tiny share, and the number only
        // climbs when the waste is farm-wide.
        if (metricsFrag && fragReason != null) {
            long idleCp = 0;
            for (BookableHost h : hosts)
                if (h.coresIdle < h.coresTotal)
                    idleCp += h.coresIdle;
            if (idleCp > 0)
                lastTickStats.fragByReason.merge(fragReason, idleCp / 100.0, Double::sum);
        }
        return dispatched;
    }

    /** True if any host is currently reserved for this layer. */
    private boolean layerHoldsReservation(String layerId) {
        for (Reservation r : reservations.values()) {
            if (r.layerId.equals(layerId))
                return true;
        }
        return false;
    }

    /** Whether host h has enough total capacity to run a frame of c when idle. */
    private static boolean hostCanEverFit(LayerCandidate c, BookableHost h) {
        return h.coresTotal >= c.layerCoresMin && h.memTotal >= c.layerMemMin
                && h.gpusTotal >= c.layerGpusMin && h.gpuMemTotal >= c.layerGpuMemMin;
    }

    /** How many frames of c fit on a fully-idle host h (min over dimensions). */
    private static int framesThatFit(LayerCandidate c, BookableHost h) {
        long f = Long.MAX_VALUE;
        if (c.layerCoresMin > 0)
            f = Math.min(f, h.coresTotal / c.layerCoresMin);
        if (c.layerMemMin > 0)
            f = Math.min(f, h.memTotal / c.layerMemMin);
        if (c.layerGpusMin > 0)
            f = Math.min(f, h.gpusTotal / c.layerGpusMin);
        if (c.layerGpuMemMin > 0)
            f = Math.min(f, h.gpuMemTotal / c.layerGpuMemMin);
        return (f == Long.MAX_VALUE) ? 1 : (int) f; // unconstrained -> 1
    }

    /**
     * Frames of c that fit on one reservation-eligible host, taken as the minimum across fitting
     * hosts so we never under-reserve (the dangerous direction, too few reserved hosts and the
     * layer stays starved). Returns 0 when no host can fit c (caller then falls back to a per-frame
     * count).
     */
    private static int framesPerFittingHost(LayerCandidate c, List<BookableHost> hosts) {
        int min = 0;
        for (BookableHost h : hosts) {
            if (!hostCanEverFit(c, h))
                continue;
            int f = framesThatFit(c, h);
            if (f > 0 && (min == 0 || f < min))
                min = f;
        }
        return min;
    }

    /**
     * A host's reservation lets c through if there is no reservation, the reservation belongs to c,
     * or the existing reservation is strictly lower priority (in which case c may override on
     * successful dispatch).
     */
    private boolean reservationAllows(BookableHost h, LayerCandidate c) {
        if (!reservationsEnabled)
            return true;
        Reservation r = reservations.get(h.hostId);
        return r == null || r.layerId.equals(c.layerId) || r.priority < c.priority;
    }

    /**
     * EASY backfill (Lifka 1995): may c borrow reserved host h without delaying its owner? Yes iff
     * c's worst-case runtime (layer_usage.int_clock_time_high) finishes before h is projected to
     * free enough cores for its reserving layer ({@link #computeHostReadySeconds}). Borrowing never
     * takes ownership, the dispatch loop's override only fires for strictly-lower-priority
     * reservations, which this host is not.
     *
     * Refuses to backfill when c has no runtime history (cannot bound its occupancy) or the host's
     * ready time is unknown, keeping the no-delay guarantee conservative under soft (non-killed)
     * estimates.
     *
     * The time check is the whole guarantee; do not also gate on "host already has enough idle for
     * the owner". That guard makes backfill dead: once idle covers the owner, the higher-priority
     * owner books the host itself, so the only moment backfill can place anything is while the host
     * is still draining, exactly what such a guard forbids. The sub-owner-width idle on reserved
     * hosts would then strand instead of being backfilled.
     */
    private boolean backfillAllows(BookableHost h, LayerCandidate c,
            Map<String, Integer> tReadyByHost) {
        if (!backfillEnabled)
            return false;
        Integer tReady = tReadyByHost.get(h.hostId);
        if (tReady == null)
            return false;
        return backfillFits(c.hasRuntimeEstimate(), c.clockTimeHighSec, tReady);
    }

    /**
     * The EASY no-delay test, factored out for testing: a frame may backfill iff its layer has a
     * runtime estimate, the host's ready time is known (not {@link Integer#MAX_VALUE}), and the
     * frame's worst-case runtime finishes at or before that ready time.
     */
    static boolean backfillFits(boolean hasEstimate, int clockTimeHighSec, int tReadySeconds) {
        if (!hasEstimate)
            return false;
        if (tReadySeconds == Integer.MAX_VALUE)
            return false;
        return clockTimeHighSec <= tReadySeconds;
    }

    /**
     * Seconds until a host frees {@code needCores} cores, given its running procs as
     * {@code {coresFreed, secondsUntilFree}} pairs. Procs finish soonest-first; the crossing proc's
     * time is the answer. Returns 0 when no cores are needed and {@link Integer#MAX_VALUE} when the
     * cores can never be freed from the known procs (too few, or a needed proc has an unknown
     * finish time, encoded as {@link Integer#MAX_VALUE}). Factored out of
     * {@link #computeHostReadySeconds} for testing.
     */
    static int hostReadySeconds(int needCores, List<int[]> procs) {
        if (needCores <= 0)
            return 0;
        if (procs == null || procs.isEmpty())
            return Integer.MAX_VALUE;
        List<int[]> sorted = new ArrayList<>(procs);
        sorted.sort(Comparator.comparingInt(p -> p[1]));
        int freed = 0;
        for (int[] p : sorted) {
            if (p[1] == Integer.MAX_VALUE)
                break; // unknown proc needed
            freed += p[0];
            if (freed >= needCores)
                return p[1];
        }
        return Integer.MAX_VALUE;
    }

    /**
     * Ensure c holds the right number of reservations. The target count is:
     *
     * 1. Frames the layer could still run: waiting frames, clamped by the job and show core caps (a
     * capped layer must not hold hosts it cannot legally use, which would block lower-priority
     * work). 2. Made capacity-aware: a fitting host runs several frames of the layer (e.g. two
     * 64-core frames on a 128-core host), so the number of hosts needed is frames /
     * frames-per-host, not one host per frame. 3. Bounded by the per-class cap: reservations (this
     * layer's plus any already held by others on hosts that fit c) may cover at most
     * reservationMaxFraction of the hosts that can fit c, so the class can never be fully reserved.
     * Callers grant priority-first then widest-job, so the cap fills for high-priority wide jobs
     * before narrow ones are considered.
     *
     * Drops excess reservations (frames dispatched, layer capped, or cap shrunk) or claims more via
     * {@link #pickReservationTarget}.
     */
    private void reconcileReservationsForLayer(LayerCandidate c, List<BookableHost> hosts) {
        List<String> mine = new ArrayList<>();
        for (Map.Entry<String, Reservation> e : reservations.entrySet()) {
            if (e.getValue().layerId.equals(c.layerId))
                mine.add(e.getKey());
        }

        int have = mine.size();
        int framesNeed = Math.max(0, c.waitingFrameCount);
        if (c.layerCoresMin > 0) {
            int jobFramesLeft = Math.max(0, (c.jobMaxCores - c.jobCoresInUse) / c.layerCoresMin);
            int showFramesLeft =
                    Math.max(0, (c.showBurstCores - c.showCoresInUse) / c.layerCoresMin);
            framesNeed = Math.min(framesNeed, Math.min(jobFramesLeft, showFramesLeft));
        }

        // Capacity-aware: how many hosts does framesNeed actually require?
        // Use the smallest fitting host's capacity so we never under-reserve.
        int framesPerHost = framesPerFittingHost(c, hosts);
        int need = framesPerHost > 0 ? (framesNeed + framesPerHost - 1) / framesPerHost // ceil
                : framesNeed;

        // Per-class cap: at most reservationMaxFraction of the hosts that can
        // fit c may be reserved at once. Count fitting hosts and how many of
        // them are already reserved by other layers; c may use the remainder.
        int fittingTotal = 0, reservedByOthers = 0;
        for (BookableHost h : hosts) {
            if (!hostCanEverFit(c, h))
                continue;
            fittingTotal++;
            Reservation r = reservations.get(h.hostId);
            if (r != null && !r.layerId.equals(c.layerId))
                reservedByOthers++;
        }
        int capTotal = (int) Math.floor(reservationMaxFraction * fittingTotal);
        int capForC = Math.max(0, capTotal - reservedByOthers);
        need = Math.min(need, capForC);

        if (have > need) {
            for (String hostId : mine.subList(need, have)) {
                reservations.remove(hostId);
            }
        } else if (have < need) {
            int want = need - have;
            for (int i = 0; i < want; i++) {
                BookableHost t = pickReservationTarget(c, hosts);
                if (t == null)
                    break; // no more eligible host
                Reservation existing = reservations.get(t.hostId);
                if (existing != null && existing.priority < c.priority) {
                    logger.info("Scheduler: override reservation host=" + t.hostName + " layer="
                            + existing.layerId + "(p=" + existing.priority + ") -> " + c.layerId
                            + "(p=" + c.priority + ")");
                }
                reservations.put(t.hostId, new Reservation(c.layerId, c.priority, c.layerCoresMin));
            }
        }
    }

    /**
     * Pick the host most likely to become available for c soonest, expressed as "host with the
     * fewest running procs": fewer running frames means fewer to wait on before the host frees up
     * enough cores for c. The host must (a) be tag/OS-compatible (granted by group membership), (b)
     * have enough total capacity for c when fully idle, (c) not already be reserved by c (reconcile
     * only expands the set, never re-claims), and (d) not be reserved at equal or higher priority
     * for a different layer.
     */
    private BookableHost pickReservationTarget(LayerCandidate c, List<BookableHost> hosts) {
        BookableHost best = null;
        int bestProcs = Integer.MAX_VALUE;
        for (BookableHost h : hosts) {
            if (!hostCanEverFit(c, h))
                continue;
            Reservation r = reservations.get(h.hostId);
            // Skip hosts c already owns: they are counted in 'have' by
            // reconcileReservationsForLayer and must not be re-claimed.
            // Without this check, reservationAllows returns true for
            // c's own reservations and the loop re-picks the same best
            // host on every iteration, never actually expanding the set.
            if (r != null && r.layerId.equals(c.layerId))
                continue;
            // Skip hosts held by an equal- or higher-priority layer.
            if (r != null && r.priority >= c.priority)
                continue;
            if (h.runningProcs < bestProcs) {
                bestProcs = h.runningProcs;
                best = h;
            }
        }
        return best;
    }

    /**
     * Placement score for a (host, layer) pair; lower is better. Callers must fitsOnHost first,
     * this assumes the layer fits.
     *
     * The score is E-PVM marginal cost (Amir et al. 2000): the weighted sum over the resource
     * dimensions of each dimension's convex cost rise from adding one frame (see deltaCost).
     * Because the terms are e^(used/total), an already-full dimension (idle cores behind saturated
     * memory) costs far more, and the utilization-fraction exponent keeps the score size-unbiased
     * so big hosts are not starved. We pick the host with the smallest score. See Scheduler.md for
     * the derivation and the farm-balancing properties.
     *
     * One-step lookahead: the cost adds just this frame, not an end-of-tick projection. The
     * dispatch loop decrements h.*Idle after each commit, so the next frame sees a steeper delta on
     * its own, with no computeMaxMore pile-up estimate needed here.
     */
    static double placementScore(BookableHost h, LayerCandidate c) {
        return W_CORES * deltaCost(h.coresTotal, h.coresIdle, c.layerCoresMin)
                + W_MEM * deltaCost(h.memTotal, h.memIdle, c.layerMemMin)
                + W_GPUS * deltaCost(h.gpusTotal, h.gpusIdle, c.layerGpusMin)
                + W_GPU_MEM * deltaCost(h.gpuMemTotal, h.gpuMemIdle, c.layerGpuMemMin);
    }

    /**
     * Marginal rise of one resource dimension's convex cost term when a reservation of {@code add}
     * is placed on a host that has {@code idle} free out of {@code total}. Returns 0 when the layer
     * does not use the dimension (add &lt;= 0) or the host has no capacity there.
     */
    private static double deltaCost(double total, double idle, double add) {
        if (add <= 0 || total <= 0)
            return 0;
        double usedBefore = total - idle;
        double usedAfter = usedBefore + add;
        return Math.exp(usedAfter / total) - Math.exp(usedBefore / total);
    }

    /**
     * Predict the number of additional frames of c (beyond the first) that could be dispatched to h
     * within this tick. Shared by placementScore (which uses it to compute stranding) and the
     * dispatch loop (which uses it to estimate the frames a single commit will book).
     *
     * Caps applied (mirroring the dispatcher's per-frame fit checks): physical fit on each
     * dimension, job int_max_cores (matches isJobBookable), and show int_burst (matches
     * isShowAtOrOverBurst).
     *
     * The per-call caps host_frame_dispatch_max and job_frame_dispatch_max are not applied here
     * because they bound a single dispatch call, not the per-tick total. The dispatch loop applies
     * job_frame_dispatch_max when estimating a single commit's worth of frames.
     */
    static long computeMaxMore(BookableHost h, LayerCandidate c) {
        long remCores = h.coresIdle - c.layerCoresMin;
        long remMem = h.memIdle - c.layerMemMin;
        long remGpus = h.gpusIdle - c.layerGpusMin;
        long remGpuMem = h.gpuMemIdle - c.layerGpuMemMin;

        long maxMore = Long.MAX_VALUE;
        if (c.layerCoresMin > 0)
            maxMore = Math.min(maxMore, remCores / c.layerCoresMin);
        if (c.layerMemMin > 0)
            maxMore = Math.min(maxMore, remMem / c.layerMemMin);
        if (c.layerGpusMin > 0)
            maxMore = Math.min(maxMore, remGpus / c.layerGpusMin);
        if (c.layerGpuMemMin > 0)
            maxMore = Math.min(maxMore, remGpuMem / c.layerGpuMemMin);

        if (c.layerCoresMin > 0) {
            long jobRem = (long) c.jobMaxCores - c.jobCoresInUse - c.layerCoresMin;
            if (jobRem < 0)
                jobRem = 0;
            maxMore = Math.min(maxMore, jobRem / c.layerCoresMin);
        }
        if (c.layerCoresMin > 0) {
            long showRem = (long) c.showBurstCores - c.showCoresInUse - c.layerCoresMin;
            if (showRem < 0)
                showRem = 0;
            maxMore = Math.min(maxMore, showRem / c.layerCoresMin);
        }
        if (maxMore == Long.MAX_VALUE)
            maxMore = 0;
        return maxMore;
    }

    // ---- plan / batch-commit: submission ----------------------------------

    /**
     * Record a (host, layer) placement to commit at the end of this tick. Planner-thread only;
     * doTick drains plannedByHost via planHost + startFramesAndProcsBatch.
     */
    private void submitCommit(String hostId, String layerId) {
        plannedByHost.computeIfAbsent(hostId, k -> new ArrayList<>()).add(layerId);
        placedLayerIds.add(layerId);
    }

    // ---- batched resource accounting: accumulate + flush ------------------

    /**
     * Record the resource deltas for the procs the batch commit just booked. Called on the planner
     * thread right after startFramesAndProcsBatch. The passed list is the batch's winners (only
     * successfully committed procs), so rolled-back bookings are never counted. Local dispatches
     * keep their own accounting path and are skipped here.
     */
    private void accumulateResourceDeltas(List<VirtualProc> procs) {
        if (procs == null || procs.isEmpty()) {
            return;
        }
        for (VirtualProc p : procs) {
            if (p.isLocalDispatch) {
                continue;
            }
            long cores = p.coresReserved;
            long gpus = p.gpusReserved;
            addDelta(subDeltas, p.getShowId() + "\t" + p.getAllocationId(), cores, gpus);
            addDelta(layerDeltas, p.getLayerId(), cores, gpus);
            addDelta(jobDeltas, p.getJobId(), cores, gpus);
        }
    }

    private static void addDelta(Map<String, long[]> buf, String key, long cores, long gpus) {
        buf.merge(key, new long[] {cores, gpus}, (a, b) -> {
            a[0] += b[0];
            a[1] += b[1];
            return a;
        });
    }

    /**
     * Apply this tick's accumulated resource deltas as one UPDATE per row. Runs on the planner
     * thread right after the batch commit, so no accumulation races it. On a SQL error the deltas
     * are merged back so the next tick retries them rather than silently dropping accounting.
     * Subscription/layer rows missing (deleted mid-tick) simply update zero rows; folder/point use
     * the job subquery and likewise no-op if the job is gone.
     */
    private void flushResourceDeltas() {
        if (!batchResourceAccounting) {
            return;
        }
        flushSubDeltas();
        flushLayerDeltas();
        flushJobDeltas();
    }

    private void flushSubDeltas() {
        if (subDeltas.isEmpty()) {
            return;
        }
        Map<String, long[]> snap = drain(subDeltas);
        List<Object[]> batch = new ArrayList<>(snap.size());
        for (Map.Entry<String, long[]> e : snap.entrySet()) {
            String[] k = e.getKey().split("\t", 2);
            long[] d = e.getValue();
            batch.add(new Object[] {(int) d[0], (int) d[1], k[0], k[1]});
        }
        try {
            txTemplate().execute(status -> {
                getJdbcTemplate().batchUpdate(
                        "UPDATE subscription SET int_cores = int_cores + ?, "
                                + "int_gpus = int_gpus + ? WHERE pk_show = ? AND pk_alloc = ?",
                        batch);
                return null;
            });
        } catch (RuntimeException ex) {
            logger.warn("Scheduler: subscription delta flush failed, retrying next tick: "
                    + ex.getMessage());
            for (Map.Entry<String, long[]> e : snap.entrySet()) {
                addDelta(subDeltas, e.getKey(), e.getValue()[0], e.getValue()[1]);
            }
        }
    }

    private void flushLayerDeltas() {
        if (layerDeltas.isEmpty()) {
            return;
        }
        Map<String, long[]> snap = drain(layerDeltas);
        List<Object[]> batch = new ArrayList<>(snap.size());
        for (Map.Entry<String, long[]> e : snap.entrySet()) {
            long[] d = e.getValue();
            batch.add(new Object[] {(int) d[0], (int) d[1], e.getKey()});
        }
        try {
            txTemplate().execute(status -> {
                getJdbcTemplate()
                        .batchUpdate("UPDATE layer_resource SET int_cores = int_cores + ?, "
                                + "int_gpus = int_gpus + ? WHERE pk_layer = ?", batch);
                return null;
            });
        } catch (RuntimeException ex) {
            logger.warn("Scheduler: layer_resource delta flush failed, retrying next tick: "
                    + ex.getMessage());
            for (Map.Entry<String, long[]> e : snap.entrySet()) {
                addDelta(layerDeltas, e.getKey(), e.getValue()[0], e.getValue()[1]);
            }
        }
    }

    private void flushJobDeltas() {
        if (jobDeltas.isEmpty()) {
            return;
        }
        Map<String, long[]> snap = drain(jobDeltas);
        List<Object[]> jobBatch = new ArrayList<>(snap.size());
        List<Object[]> pointBatch = new ArrayList<>(snap.size());
        for (Map.Entry<String, long[]> e : snap.entrySet()) {
            long[] d = e.getValue();
            int cores = (int) d[0];
            int gpus = (int) d[1];
            String jobId = e.getKey();
            jobBatch.add(new Object[] {cores, gpus, jobId});
            pointBatch.add(new Object[] {cores, gpus, jobId, jobId});
        }
        try {
            // One transaction for all three UPDATEs: on a mid-flush error the whole
            // set rolls back, so the retry (which re-queues the drained deltas) can
            // never double-apply a sub-batch that had already committed.
            txTemplate().execute(status -> {
                getJdbcTemplate().batchUpdate("UPDATE job_resource SET int_cores = int_cores + ?, "
                        + "int_gpus = int_gpus + ? WHERE pk_job = ?", jobBatch);
                getJdbcTemplate().batchUpdate(
                        "UPDATE folder_resource SET int_cores = int_cores + ?, "
                                + "int_gpus = int_gpus + ? "
                                + "WHERE pk_folder = (SELECT pk_folder FROM job WHERE pk_job = ?)",
                        jobBatch);
                getJdbcTemplate().batchUpdate(
                        "UPDATE point SET int_cores = int_cores + ?, int_gpus = int_gpus + ? "
                                + "WHERE pk_dept = (SELECT pk_dept FROM job WHERE pk_job = ?) "
                                + "AND pk_show = (SELECT pk_show FROM job WHERE pk_job = ?)",
                        pointBatch);
                return null;
            });
        } catch (RuntimeException ex) {
            logger.warn("Scheduler: job/folder/point delta flush failed, retrying next tick: "
                    + ex.getMessage());
            for (Map.Entry<String, long[]> e : snap.entrySet()) {
                addDelta(jobDeltas, e.getKey(), e.getValue()[0], e.getValue()[1]);
            }
        }
    }

    /** Copy out the current deltas and clear the buffer for the next tick. */
    private static Map<String, long[]> drain(Map<String, long[]> buf) {
        Map<String, long[]> snap = new HashMap<>();
        for (Iterator<Map.Entry<String, long[]>> it = buf.entrySet().iterator(); it.hasNext();) {
            Map.Entry<String, long[]> e = it.next();
            snap.put(e.getKey(), e.getValue());
            it.remove();
        }
        return snap;
    }

    static boolean fitsOnHost(LayerCandidate c, BookableHost h) {
        if (h.coresIdle < c.layerCoresMin)
            return false;
        if (h.memIdle < c.layerMemMin)
            return false;
        if (h.gpusIdle < c.layerGpusMin)
            return false;
        if (h.gpuMemIdle < c.layerGpuMemMin)
            return false;
        return true;
    }

    /**
     * Why an unplaced layer could not fit on any of {@code hosts}, as a fragmentation reason by the
     * first gate no host clears (gates mirror {@link #fitsOnHost}): {@code cores} (no host had
     * enough idle cores for one frame), {@code memory} (cores fit somewhere but not the RAM),
     * {@code gpu} (cores and RAM fit but not the GPU), or {@code fit} (some host fit fully, so the
     * layer was gated by a reservation or a host-based license seat -- the caller resolves that
     * into held/license).
     */
    static String classifyFragmentation(LayerCandidate c, List<BookableHost> hosts) {
        boolean anyCores = false;
        boolean anyMem = false;
        for (BookableHost h : hosts) {
            if (h.coresIdle < c.layerCoresMin)
                continue;
            anyCores = true;
            if (h.memIdle < c.layerMemMin)
                continue;
            anyMem = true;
            if (h.gpusIdle >= c.layerGpusMin && h.gpuMemIdle >= c.layerGpuMemMin)
                return "fit";
        }
        if (!anyCores)
            return "cores";
        if (!anyMem)
            return "memory";
        return "gpu";
    }

    /**
     * Resolve a {@code fit} fragmentation (some host fit the layer fully, yet it did not book) into
     * the gate that held it: {@code license} when a fitting host's host-based seat is taken, else
     * {@code held} (a reservation is draining that host for a wide job).
     */
    private String fitGateReason(LayerCandidate c, List<BookableHost> hosts,
            List<LicenseSource.LicenseBudget> licenseSeatPools,
            Map<String, Set<String>> licenseSeats) {
        if (licenseSeatPools != null) {
            for (BookableHost h : hosts) {
                if (fitsOnHost(c, h) && !licenseSeatsAllow(licenseSeatPools, licenseSeats, h))
                    return "license";
            }
        }
        return "held";
    }

    // ---- config -----------------------------------------------------------

    private boolean isEnabled() {
        return SchedulerMode.enabled(env);
    }

    // ---- POJOs ------------------------------------------------------------

    static final class BookableHost {
        String hostId;
        String hostName;
        String pkAlloc;
        String pkFacility;
        int threadMode;
        // Total capacity. Used by pickReservationTarget to check whether the
        // host could fit a layer when fully idle, independent of the host's
        // current load.
        int coresTotal;
        long memTotal;
        int gpusTotal;
        long gpuMemTotal;
        // Current idle resources. Decremented as we dispatch within a tick.
        int coresIdle;
        long memIdle;
        int gpusIdle;
        long gpuMemIdle;
        // Current running proc count. Used as the "soonest-to-free" heuristic
        // for reservation target selection.
        int runningProcs;
        String tagsRaw;
        String os;
    }

    static final class LayerCandidate {
        String layerId;
        String jobId;
        String showId;
        int layerCoresMin;
        long layerMemMin;
        int layerGpusMin;
        long layerGpuMemMin;
        int priority;
        // Mutable in-tick accounting.
        int jobCoresInUse;
        int jobMaxCores;
        int showCoresInUse;
        int showBurstCores;
        // Number of pending dispatchable (waiting) frames. Initialized from
        // waiting_frame_count in the candidate query; decremented as the
        // layer dispatches in this tick. Reconcile keeps the layer's
        // reservation count equal to this value.
        int waitingFrameCount;
        // EASY-backfill runtime estimate (from layer_usage). clockTimeHighSec
        // is the worst single-frame wall-clock time ever recorded for the
        // layer; frameSuccessCount is how many successful frames produced it.
        // Both 0 when the layer has no history. Used only as the conservative
        // upper bound on how long a frame of this layer would occupy a host it
        // backfills onto (see backfillAllows).
        int clockTimeHighSec;
        int frameSuccessCount;
        // Limit (license-cap) accounting. limitId is the layer's most-constraining
        // limit (null = no limit); limitMax is that limit's int_max_value;
        // limitRunning is how many frames of it run farm-wide right now (seed for
        // the tick-wide limitUsed cap in dispatchGroupWithScoring).
        String limitId;
        int limitMax;
        int limitRunning;
        // Live application licenses the layer declares in CUE_LICENSES, or null
        // when it declares none (the common case). A seat is needed in every pool
        // listed. Carried on the candidate row via the layer_env join, not a second read.
        List<String> licenses;
        // Folder (group/dept) core cap. folderId is the job's folder; folderMax is
        // folder_resource.int_max_cores (-1 = unlimited, core-points); folderRunning
        // is the folder's current running cores (core-points), seed for the
        // tick-wide folderUsed cap in dispatchGroupWithScoring.
        String folderId;
        int folderMax;
        int folderRunning;

        /** Whether the layer has enough history to bound a frame's runtime. */
        boolean hasRuntimeEstimate() {
            return frameSuccessCount > 0 && clockTimeHighSec > 0;
        }
    }

    /**
     * A claim on a host by a specific layer at a specific priority. Stored by host id. Persistent
     * across ticks. The priority is what the override comparison uses; storing it on the
     * reservation (rather than looking it up from the current candidate set) means an override
     * decision works even when the owner layer doesn't appear in the current group's candidates.
     */
    static final class Reservation {
        final String layerId;
        final int priority;
        // The reserving layer's per-frame core requirement, so a host's
        // earliest-ready time can be estimated (how many running procs must
        // finish to free this many cores) without re-finding the owner layer.
        final int layerCoresMin;

        Reservation(String layerId, int priority, int layerCoresMin) {
            this.layerId = layerId;
            this.priority = priority;
            this.layerCoresMin = layerCoresMin;
        }
    }


    /**
     * A layer that wants reservations this tick, paired with the full host set of its group.
     * Collected during placement and processed after all groups, sorted priority-first then
     * widest-job, so the capped reservation budget is granted to the highest-priority work that
     * cannot fit (wide jobs) rather than to the oldest layer.
     */
    static final class ReservationRequest {
        final LayerCandidate candidate;
        final List<BookableHost> fullHosts;

        ReservationRequest(LayerCandidate candidate, List<BookableHost> fullHosts) {
            this.candidate = candidate;
            this.fullHosts = fullHosts;
        }
    }

    static final class HostSpecKey {
        final String pkAlloc;
        // The alloc's facility. Part of the key because the candidate query
        // binds it (jobs may only run in their own facility, like the legacy
        // dispatcher's job.pk_facility clause); in practice it never splits a
        // group beyond pkAlloc, since an alloc belongs to exactly one facility.
        final String pkFacility;
        final String tagsNormalized;
        final String os;
        final boolean hasGpu;
        // ThreadMode.ALL hosts (NIMBY workstations by default) run only
        // threadable layers; the legacy dispatcher enforces that per host and
        // the candidate query binds it per group, so mode must split the key.
        // One bit suffices: legacy itself normalizes every other mode to AUTO.
        final boolean allThreadMode;

        HostSpecKey(String pkAlloc, String pkFacility, String tagsNormalized, String os,
                boolean hasGpu, boolean allThreadMode) {
            this.pkAlloc = pkAlloc;
            this.pkFacility = pkFacility;
            this.tagsNormalized = tagsNormalized;
            this.os = os;
            this.hasGpu = hasGpu;
            this.allThreadMode = allThreadMode;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o)
                return true;
            if (!(o instanceof HostSpecKey))
                return false;
            HostSpecKey k = (HostSpecKey) o;
            return hasGpu == k.hasGpu && allThreadMode == k.allThreadMode
                    && Objects.equals(pkAlloc, k.pkAlloc)
                    && Objects.equals(pkFacility, k.pkFacility)
                    && Objects.equals(tagsNormalized, k.tagsNormalized) && Objects.equals(os, k.os);
        }

        @Override
        public int hashCode() {
            return Objects.hash(pkAlloc, pkFacility, tagsNormalized, os, hasGpu, allThreadMode);
        }

        @Override
        public String toString() {
            return "HostSpec(alloc=" + pkAlloc + ", facility=" + pkFacility + ", tags="
                    + tagsNormalized + ", os=" + os + ", gpu=" + hasGpu + ", threadAll="
                    + allThreadMode + ")";
        }
    }

    // ---- Spring setters ---------------------------------------------------

    public void setDispatcher(Dispatcher d) {
        this.dispatcher = d;
    }

    public void setDispatchSupport(DispatchSupport d) {
        this.dispatchSupport = d;
    }

    public void setHostManager(HostManager m) {
        this.hostManager = m;
    }

    public void setJobManager(JobManager m) {
        this.jobManager = m;
    }

    public void setRqdClient(RqdClient r) {
        this.rqdClient = r;
    }

    public void setFrameCompleteHandler(FrameCompleteHandler h) {
        this.frameCompleteHandler = h;
    }

    public void setSchedulerMetrics(SchedulerMetrics m) {
        this.schedulerMetrics = m;
    }
}
