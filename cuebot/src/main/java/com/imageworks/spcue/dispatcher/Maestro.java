
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
import java.util.LinkedHashSet;
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
import java.util.concurrent.ThreadLocalRandom;
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

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.LayerEntity;
import com.imageworks.spcue.LayerInterface;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.postgres.DispatchQuery;
import com.imageworks.spcue.grpc.host.HardwareState;
import com.imageworks.spcue.grpc.host.LockState;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdLaunchUnknownOutcomeException;
import com.imageworks.spcue.service.JobManager;

/**
 * Single-threaded Maestro: one Cuebot holds a Postgres advisory lock and plans each tick while the
 * rest idle as warm standbys. Placement is serial so decisions never race; only the per-host plan
 * reads fan out on a pool, and every booking for a tick commits in one batched transaction.
 * Persistent reservations hold hosts for blocked wide layers until enough cores free up.
 *
 * Gated by maestro.enabled (default false). See docs/_docs/developer-guide/maestro.md for the full
 * model.
 */
public class Maestro extends JdbcDaoSupport {

    private static final Logger logger = LogManager.getLogger(Maestro.class);

    // Postgres advisory-lock key, shared by every Cuebot on the database. ASCII "OpenCue".
    private static final long SCHEDULER_LOCK_KEY = 0x4F70656E437565L;

    // placementScore (E-PVM) dimension weights: relative importance on the util-fraction scale.
    // GPUs weighted up so a GPU layer prefers the host where it strands the least GPU capacity.
    // Sourced from maestro.score_weight_* in startSchedulerPoolsIfNeeded so they can be tuned
    // per site without a rebuild.
    // Static because placementScore is static (pure helper, also unit-tested directly).
    private static volatile double wCores = 1.0;
    private static volatile double wMem = 1.0;
    private static volatile double wGpus = 4.0;
    private static volatile double wGpuMem = 1.0;

    // Locality bonus: subtracted from a host's score when it already runs the candidate's layer, so
    // a freed core is refilled by the same layer next tick. Bounded, below the fit/reservation
    // gates.
    private volatile double localityBonus = 8.0;
    private volatile boolean localityEnabled = true;

    // Cache-warmth window: a decayed locality pull kept on vacated (host, layer) pairs, aged by
    // foreign frames booked since (displacement, not wall clock), not seconds. 0 disables. See doc.
    private volatile int localityWindowFrames = 64;
    // host|layer -> host's booking-odometer reading when the layer last completed there.
    private final Map<String, Map<String, Long>> warmthByHost = new HashMap<>();
    // host -> booking odometer, incremented per frame booked on the host.
    private final Map<String, Long> bookingsByHost = new HashMap<String, Long>();

    // Per-host same-layer cap: one layer may hold at most this fraction of a host's cores,
    // never below 8 frames so small hosts still anchor a cache-warm batch. 0 disables;
    // default 0.25. Bounds the blast radius and the phase-locked IO of a hundred identical
    // frames blanketing one machine, at the price of nibbling more hosts per flood.
    volatile double layerHostMaxFrac = 0.25;

    // Rss-driven sizing (no configuration, works out of the box; see maestro.md 3.9).
    // cores=1 on a threadable layer means "let the system decide": such a layer probes at
    // PROBE_FRAMES running frames while the farm has no rss evidence for it, then every
    // later launch books round(median rss / the group's own memory-per-core) cores with
    // its true memory, so scoring, fit, caps and booking all see the real shape. An
    // explicit ask of 2+ cores books at full speed from frame one and is only ever
    // corrected upward. The metric derives from the machines themselves, never a config
    // constant. Probe size is deliberately a constant, not a property. The one exposed
    // parameter is the memory-per-core ratio (maestro.mem_per_core, KB): 0 (the
    // default, shipped) derives it from each group's own hosts, so sizing follows the
    // hardware out of the box; a studio can pin its core-selling ratio instead.
    static final int PROBE_FRAMES = 8;
    static final int COMMIT_CHUNK_FRAMES = 500; // consumed by commitInChunks()
    private volatile long memPerCoreKb = 0;

    // Seat bonus for HOST-type limits (one license checkout per machine): subtracted per seated
    // pool so placement packs limited work onto the fewest hosts. Sized above the E-PVM spread.
    private volatile double limitSeatBonus = 16.0;

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

    // consumed by planBookings()
    private Dispatcher dispatcher;

    // Applies frame completions; drives the stage-0 drain (drainResolvedCompletions).
    private FrameCompleteHandler frameCompleteHandler;

    // Records each tick's stats to Prometheus via recordTick (runTick).
    private MaestroMetrics maestroMetrics;

    // Live farm-health ledger (swap, kernel time) fed by host reports; optional so the
    // scheduler runs unchanged where the ledger bean is absent (unit tests).
    @Autowired(required = false)
    private FarmHealth farmHealth;

    // Live per-layer rss ledger (fed by host reports) that sizes the launch-time core
    // grant; optional so the scheduler runs without it (grants simply stay off).
    @Autowired(required = false)
    private LayerLiveMem layerLiveMem;

    // The in-progress tick's stats, handed to maestroMetrics at tick end.
    private MaestroMetrics.TickStats lastTickStats;

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
    // pooled, so Hikari cannot reap it and drop the lock). See maestro.md for the failover model.
    private volatile Connection leaderConn = null;

    // Live host reservations, persistent across ticks: host id -> claiming (layer, priority).
    // Maestro-thread only (single-writer); empty after failover. See maestro.md for the model.
    private final Map<String, Reservation> reservations = new HashMap<>();
    private final Map<String, Set<String>> hostsByLayer = new HashMap<>(); // consumed by reserve()

    // ---- plan / batch-commit / launch -------------------------------------
    // Placement only records (host, layer) pairings; after it, planBookings reads each layer's
    // frames
    // and one batched transaction commits them all, then RQD launches fire on a small pool.

    // Per-tick placements to commit, host id -> layer ids. Maestro-thread only; cleared each tick.
    private final Map<String, List<String>> plannedByHost = new LinkedHashMap<>();


    // Tick-scoped planning scratch (Maestro-thread only, reset each tick by clearTickScratch). Held
    // as fields so the phase methods share them without threading a dozen parameters.
    private final Map<String, Cell> jobCells = new HashMap<>(); // consumed by bindCells()
    private final Map<String, Cell> showCells = new HashMap<>(); // consumed by bindCells()
    private final Map<String, Cell> limitCells = new HashMap<>(); // consumed by bindCells()
    private final Map<String, Cell> folderCells = new HashMap<>(); // consumed by bindCells()
    private final Map<String, Integer> folderMaxCp = new HashMap<>();
    private final Map<String, Integer> folderRunSeed = new HashMap<>();
    private final Map<String, String> jobFolderCap = new HashMap<>();
    private final Map<String, List<String>> layerLimits = new HashMap<>();
    /* package for tests */ final Map<String, LimitBudget> limitBudgets = new HashMap<>();
    private final Map<String, Set<String>> limitSeats = new HashMap<>();
    // True once this tick's limit budgets are loaded; reset by clearTickScratch.
    /* package for tests */ boolean limitBudgetsResolved = false;
    private final Set<String> seenLayerIds = new HashSet<>();
    private final Map<HostSpecKey, List<LayerCandidate>> pinnedByGroup = new HashMap<>(); // consumed
                                                                                          // by
                                                                                          // planGroup()
    private final List<ReservationRequest> reservationReqs = new ArrayList<>();
    // Waitlist tally: the last outcome seen for each candidate layer that still had waiting
    // frames, and that count. tallyWaitlist folds them into the tick stats and the stat line.
    private final Map<String, String> waitReasonByLayer = new HashMap<>();
    private final Map<String, Integer> waitFramesByLayer = new HashMap<>();
    // host -> seconds until it frees enough cores for a reserving layer (backfill deadline).
    // Read fresh each tick (reassigned, not cleared).
    private Map<String, Integer> tReadyByHost = new HashMap<>();

    // host -> layer ids it currently runs, the locality/affinity signal. Read fresh each tick.
    private Map<String, Set<String>> hostLayerAffinity = new HashMap<>();
    // Frames each layer runs per host right now ("hostId|layerId" -> count), read with the
    // affinity snapshot and advanced as the plan books. Backs the per-host layer cap.
    private Map<String, Map<String, Integer>> hostLayerFrames = new HashMap<>();
    // Frames each layer runs farm-wide right now, read with the same snapshot. Backs the
    // probe gate for layers with no rss evidence yet.
    private Map<String, Integer> layerRunningFrames = new HashMap<>();
    // Probe frames planned this tick per unproven layer.
    private final Map<String, Integer> layerProbeUsed = new HashMap<>();

    // Tick-scoped frame-slice bookkeeping for same-layer multi-host planning
    // (the relax pass): frames planned per layer this tick, and each
    // (host|layer) plan's {starting offset, size} slice of the layer's
    // waiting list, so the parallel plan reads pull disjoint frames and
    // deliver exactly what the scoring accounted.
    final Map<String, Integer> plannedFramesByLayer = new HashMap<>();
    double[][] reachNeeds; // consumed by placementScore() and strandFreeFrames()
    private HostClasses classes; // consumed by placeOnce()
    private final List<LayerCandidate> alive = new ArrayList<>(); // consumed by othersWant()
    private final List<List<LayerCandidate>> needers = new ArrayList<>(); // consumed by wantedOn()
    // Layers resized from rss evidence this tick: layerId -> {effective core points,
    // effective memory KB}, read by planBookings so the commit books the same shape the
    // Maestro scored.
    private final Map<String, long[]> layerResize = new HashMap<>();

    // Layer-placements planned this tick, for the tick-breakdown log line.
    private int lastPlacements;

    // Consecutive ticks a layer was planned but the plan found zero bookable frames: the
    // signature of a Maestro-vs-dispatch eligibility mismatch. Warns at plan_zero_warn_ticks.
    private final Map<String, Integer> planZeroStreak = new ConcurrentHashMap<>();

    // Small bounded pool for post-commit RQD launches (one gRPC per frame); a full queue drops
    // the launch (launchDropped) rather than blocking Maestro.
    private volatile ExecutorService launchPool;

    // Launches dropped because the launch queue was full; the frame is RUNNING in the DB, reconcile
    // recovers it.
    private final java.util.concurrent.atomic.AtomicLong launchDropped =
            new java.util.concurrent.atomic.AtomicLong(0);

    // Pool for the plan phase: the window reads, then the per-host plans, run in parallel on it
    // (serial within a host so the capacity decrement is correct). Commit is still single/batched.
    private volatile ExecutorService readPool;

    // Max frames one commit books per layer, also the plan pull size (property
    // dispatcher.frame_query_max). The legacy job_frame_dispatch_max trickle is not used here:
    // fairness comes from the lottery and the caps, not from tiny commits.
    private volatile int frameQueryMax = 20;
    // When false, Maestro ignores reservations entirely (no claims, none enforced): the bare
    // placement core, for isolating core scheduling from the reservation logic.
    private volatile boolean reservationsEnabled = true;

    // Time gate: blocked-time a layer must accrue before it may reserve (wall-clock).
    // Property maestro.reservation_block_seconds. See maestro.md for the reservation model.
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
    static final int CORE_POINTS_PER_CORE = 100;

    // Stat-line interval (maestro.stat_interval_seconds, default 5 min).
    private volatile long statIntervalMs = 300_000;
    private long lastSummaryMs = 0;

    // Window accumulators, Maestro-thread only except summarySkipped (bumped by the CAS-loser
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
    // Waitlist peaks over the current stat window (reason -> max frames seen on any tick, plus
    // the max total). Peaks, not the last tick, so a short-lived cause (a held spike during one
    // drain) still shows on the stat line. Tick thread only; maybeLogStat prints and resets.
    private final Map<String, Long> winWaitMax = new HashMap<>();
    private long winWaitTotalMax = 0;
    // Per-tick outputs set by doTick(), folded into the window by runTick().
    private long tickPlanned = 0;
    private int tickGranted = 0;
    private int tickBackfilled = 0;
    private long tickBackfilledCores = 0;
    // Limit gating (license-style pools): frames booked against a gating limit,
    // and candidates a limit's exhausted budget held back this tick.
    private int tickLicenseBooked = 0;
    private int tickLicenseHeld = 0;
    // Planned frames dropped at commit time because a limit could not cover them
    // (the plan read is limit-blind; see the trim in doTick).
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
    // scale. Instead Maestro records per-row deltas and flushes one UPDATE per row after the
    // batch commit. See maestro.md section 5.
    // Per-row delta buffers: value is {cores, gpus}. Written on Maestro
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
     * init-method, and Cuebot is well past startup by the time maestro.enabled is flipped on.
     */
    private synchronized void startSchedulerPoolsIfNeeded() {
        if (launchPool != null)
            return;
        int launchSize = env.getProperty("maestro.launch_pool_size", Integer.class, 8);
        frameQueryMax = env.getProperty("dispatcher.frame_query_max", Integer.class, 20);
        reservationsEnabled = env.getProperty("maestro.reservations_enabled", Boolean.class, true);
        reservationBlockMs =
                1000L * env.getProperty("maestro.reservation_block_seconds", Integer.class, 300);
        reservationMaxFraction =
                env.getProperty("maestro.reservation_max_fraction", Double.class, 0.5);
        backfillEnabled = env.getProperty("maestro.backfill_enabled", Boolean.class, true);
        localityEnabled = env.getProperty("maestro.locality_enabled", Boolean.class, true);
        localityBonus = env.getProperty("maestro.locality_bonus", Double.class, 8.0);
        localityWindowFrames = env.getProperty("maestro.locality_window_frames", Integer.class, 64);
        layerHostMaxFrac = env.getProperty("maestro.layer_host_max_frac", Double.class, 0.25);
        memPerCoreKb = env.getProperty("maestro.mem_per_core", Long.class, 0L);
        // Property name kept from the per-host-limit feature this supersedes, so
        // any site already setting it keeps its value.
        limitSeatBonus = env.getProperty("maestro.host_limit_seat_bonus", Double.class, 16.0);
        wCores = env.getProperty("maestro.score_weight_cores", Double.class, 1.0);
        wMem = env.getProperty("maestro.score_weight_mem", Double.class, 1.0);
        wGpus = env.getProperty("maestro.score_weight_gpus", Double.class, 4.0);
        wGpuMem = env.getProperty("maestro.score_weight_gpu_mem", Double.class, 1.0);
        // Cadence of the consolidated INFO stat line (see maybeLogStat). Default
        // 5 minutes; lower it for a live incident, raise it to quiet the log.
        statIntervalMs =
                1000L * env.getProperty("maestro.stat_interval_seconds", Integer.class, 300);
        // A fixed pool so launches never run on the tick thread (a slow RQD sink would stall the
        // tick), over an UNBOUNDED queue: a committed booking is always launched. A tick may
        // commit a whole cold farm at once, and a dropped launch leaves a frame RUNNING in the
        // DB with no process behind it until the orphan sweep finds it minutes later; a slow
        // sink now shows as launch latency, never as lost work. The handler below can only fire
        // when the pool is shutting down.
        ThreadPoolExecutor pool = new ThreadPoolExecutor(launchSize, launchSize, 0L,
                TimeUnit.MILLISECONDS, new LinkedBlockingQueue<>(), r -> {
                    Thread t = new Thread(r);
                    t.setName("Maestro-launch-" + t.getId());
                    t.setDaemon(true);
                    return t;
                }, (r, ex) -> {
                    long n = launchDropped.incrementAndGet();
                    if (n % 1000 == 1) {
                        logger.warn("Maestro: launch rejected, pool shutting down"
                                + " (total dropped=" + n + "); RQD reconciliation will recover");
                    }
                });
        launchPool = pool;
        // Read pool for the parallel plan phase. Reads are DB-bound (they block
        // on Postgres, not the CPU), so sizing above the core count is fine.
        int readSize = env.getProperty("maestro.read_pool_size", Integer.class, launchSize);
        readPool = Executors.newFixedThreadPool(readSize, r -> {
            Thread t = new Thread(r);
            t.setName("Maestro-read-" + t.getId());
            t.setDaemon(true);
            return t;
        });
        logger.info("Maestro: launch pool started with " + launchSize + " workers, read pool with "
                + readSize + " workers");
    }

    // ---- snapshot queries -------------------------------------------------

    /**
     * All schedulable hosts: state UP and lock state OPEN, busy or idle. Returns enough columns to
     * compute the spec key and run the per-host fit check without a second lookup. The
     * idle/min-core cut happens later, in planGroup.
     */
    // spotless:off
    private static final String SELECT_ALL_HOSTS =
            "SELECT "
            + "  h.pk_host, "
            + "  h.str_name, "
            + "  h.pk_alloc, "
            + "  a.pk_facility, "
            + "  h.int_thread_mode, "
            + "  h.int_cores, "
            + "  h.int_cores_idle, "
            + "  h.int_mem, "
            + "  h.int_mem_idle, "
            + "  h.int_gpus, "
            + "  h.int_gpus_idle, "
            + "  h.int_gpu_mem, "
            + "  h.int_gpu_mem_idle, "
            + "  h.int_procs, "
            + "  h.str_tags, "
            + "  hs.str_os "
            + "FROM host h, host_stat hs, alloc a "
            + "WHERE h.pk_host = hs.pk_host "
            + "  AND a.pk_alloc = h.pk_alloc "
            + "  AND hs.str_state = 'UP' "
            + "  AND h.str_lock_state = 'OPEN' ";
    // spotless:on

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
    // spotless:off
    private static final String SELECT_CANDIDATES_FOR_GROUP =
            "SELECT "
            + "  l.pk_layer, "
            + "  l.pk_job, "
            + "  j.pk_show, "
            + "  l.int_cores_min, "
            + "  l.int_mem_min, "
            + "  l.b_threadable, "
            + "  l.int_cores_max, "
            + "  l.int_gpus_min, "
            + "  l.int_gpu_mem_min, "
            + "  jr.int_priority, "
            + "  jr.int_cores       AS job_cores_in_use, "
            + "  jr.int_max_cores   AS job_max_cores, "
            + "  sub.int_cores      AS show_cores_in_use, "
            + "  sub.int_burst      AS show_burst, "
            + "  sub.int_size       AS show_size, "
            + "  COALESCE(ls.int_waiting_count, 0) AS waiting_frame_count, "
            + "  COALESCE(lu.int_clock_time_high, 0)     AS clock_time_high, "
            + "  COALESCE(lu.int_frame_success_count, 0) AS frame_success_count, "
            // Limits bound to the layer, comma separated, NULL when none. The
            // per-limit budgets (usage, thresholds, holder hosts) are resolved
            // once per tick in resolveLimitBudgets, not per candidate row.
            + "  (SELECT string_agg(ll.pk_limit_record, ',') "
            + "     FROM layer_limit ll WHERE ll.pk_layer = l.pk_layer) AS limit_ids, "
            // Folder (group/dept) core cap: the job's folder, its ceiling, and the
            // folder's current running cores (ground truth = SUM of the folder's jobs).
            + "  j.pk_folder AS folder_id, "
            + "  COALESCE(fr.int_max_cores, -1) AS folder_max, "
            + "  COALESCE(fu.folder_cores, 0)   AS folder_running "
            + "FROM   layer l "
            + "JOIN   job j           ON j.pk_job  = l.pk_job "
            + "JOIN   job_resource jr ON jr.pk_job = j.pk_job "
            + "JOIN   show sh         ON sh.pk_show = j.pk_show "
            + "JOIN   subscription sub ON sub.pk_show = j.pk_show AND sub.pk_alloc = ? "
            + "LEFT JOIN layer_usage lu ON lu.pk_layer = l.pk_layer "
            + "LEFT JOIN layer_stat  ls ON ls.pk_layer = l.pk_layer "
            // Folder core ceiling + the folder's current running cores. Derived from
            // layer_stat.int_running_count (running frames x per-frame cores), the
            // same trigger-maintained counter the limit cap uses. It is robust to frame
            // completion (int_running_count drops automatically) and, at a tick
            // boundary, equals SUM(job_resource.int_cores) (one proc per running
            // frame), the figure the folder cap is measured against. Computed once,
            // not per row.
            + "LEFT JOIN folder_resource fr ON fr.pk_folder = j.pk_folder "
            + "LEFT JOIN ("
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
            + "WHERE  j.str_state = 'PENDING' "
            + "  AND  j.b_paused  = false "
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
            // Maestro books cross-facility (PARITY's parity_facother archetype)
            // because the frame-level plan read never re-checks facility.
            + "  AND  j.pk_facility = ? "
            // ThreadMode.ALL hosts run only threadable layers (bind 1 for ALL
            // groups, 0 otherwise), exactly the legacy dispatcher's clause.
            // Without it Maestro parks non-threadable layers on ALL hosts
            // (idle NIMBY workstations score best), planFrames' re-check finds
            // zero frames, and the layer burns its one commit per tick forever.
            + "  AND  (CASE WHEN l.b_threadable = true THEN 1 ELSE 0 END) >= ? "
            + "  AND  ? ~* ('(?x)' || l.str_tags || '\\y') "
            + "  AND  jr.int_cores  < jr.int_max_cores "
            + "  AND  sub.int_cores < sub.int_burst "
            + "  AND  l.int_cores_min <= ? "
            // Dispatchable-frame test and waiting_frame_count both come from
            // layer_stat.int_waiting_count (maintained by core trigger
            // trigger__update_frame_status_counts; WAITING frames are depend-resolved,
            // DEPEND is a separate state). Backed by the partial index
            // idx_layer_stat_waiting (V44). Replaces a correlated COUNT(*) + EXISTS
            // over frame that scanned every frame of each candidate layer per tick.
            + "  AND  COALESCE(ls.int_waiting_count, 0) > 0 "
            // Skip jobs whose folder (group/dept) core ceiling is already reached
            // (folder_resource.int_max_cores, another core cap the legacy dispatcher
            // enforces; -1 = unlimited). Same rationale as the limit filter: purely an
            // efficiency gate (don't plan bookings a full folder can't take). The exact
            // ceiling is enforced by the post-plan folder trim in doTick, which,
            // unlike this filter, also binds the frames planFrames books in the tick
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
            // <= 0. Reservation granting uses the same lottery weighting. See maestro.md 3.5.
            + "ORDER BY power(random(), 1.0 / GREATEST(jr.int_priority, 1)) DESC "
            + "LIMIT  ? ";
    // spotless:on

    // Pinned layers: the same row as the group query, one per (layer, named
    // host), for the waiting layers whose tags are not all host-spec tags.
    // The host join carries the group query's per-host predicates, so a
    // named host that is down, locked, in another facility or OS, or too
    // small yields no row; a layer none of whose names resolves yields one
    // row with a null host. Binds: thread mode ALL, the spec tags (csv,
    // lower case), the facility-mode flag, the row limit.
    // spotless:off
    private static final String SELECT_PINNED_CANDIDATES =
            "SELECT "
            + "  l.pk_layer, "
            + "  l.pk_job, "
            + "  j.pk_show, "
            + "  l.int_cores_min, "
            + "  l.int_mem_min, "
            + "  l.b_threadable, "
            + "  l.int_cores_max, "
            + "  l.int_gpus_min, "
            + "  l.int_gpu_mem_min, "
            + "  jr.int_priority, "
            + "  jr.int_cores       AS job_cores_in_use, "
            + "  jr.int_max_cores   AS job_max_cores, "
            + "  COALESCE(sub.int_cores, 0) AS show_cores_in_use, "
            + "  COALESCE(sub.int_burst, 0) AS show_burst, "
            + "  COALESCE(sub.int_size, 0)  AS show_size, "
            + "  COALESCE(ls.int_waiting_count, 0) AS waiting_frame_count, "
            + "  COALESCE(lu.int_clock_time_high, 0)     AS clock_time_high, "
            + "  COALESCE(lu.int_frame_success_count, 0) AS frame_success_count, "
            + "  (SELECT string_agg(ll.pk_limit_record, ',') "
            + "     FROM layer_limit ll WHERE ll.pk_layer = l.pk_layer) AS limit_ids, "
            + "  j.pk_folder AS folder_id, "
            + "  COALESCE(fr.int_max_cores, -1) AS folder_max, "
            + "  COALESCE(fu.folder_cores, 0)   AS folder_running, "
            + "  h.pk_host AS pin_host, "
            + "  l.str_tags "
            + "FROM   layer l "
            + "JOIN   job j           ON j.pk_job  = l.pk_job "
            + "JOIN   job_resource jr ON jr.pk_job = j.pk_job "
            + "JOIN   show sh         ON sh.pk_show = j.pk_show "
            + "LEFT JOIN layer_usage lu ON lu.pk_layer = l.pk_layer "
            + "LEFT JOIN layer_stat  ls ON ls.pk_layer = l.pk_layer "
            + "LEFT JOIN folder_resource fr ON fr.pk_folder = j.pk_folder "
            + "LEFT JOIN ("
            + "    SELECT j2.pk_folder, "
            + "           SUM(ls2.int_running_count * l2.int_cores_min) AS folder_cores "
            + "    FROM   job j2 "
            + "    JOIN   folder_resource fr2 ON fr2.pk_folder = j2.pk_folder "
            + "                               AND fr2.int_max_cores <> -1 "
            + "    JOIN   layer l2      ON l2.pk_job = j2.pk_job "
            + "    JOIN   layer_stat ls2 ON ls2.pk_layer = l2.pk_layer "
            + "    WHERE  j2.str_state = 'PENDING' "
            + "    GROUP BY j2.pk_folder) fu ON fu.pk_folder = j.pk_folder "
            + "LEFT JOIN (host h JOIN host_stat hs ON hs.pk_host = h.pk_host "
            + "                  JOIN alloc a ON a.pk_alloc = h.pk_alloc) "
            + "       ON h.str_name = ANY(string_to_array(replace(l.str_tags, ' ', ''), '|')) "
            + "      AND hs.str_state = 'UP' "
            + "      AND h.str_lock_state = 'OPEN' "
            + "      AND j.pk_facility = a.pk_facility "
            + "      AND (j.str_os IS NULL OR j.str_os = '' "
            + "           OR j.str_os = ANY(string_to_array(hs.str_os, ','))) "
            + "      AND (CASE WHEN l.b_threadable = true THEN 1 ELSE 0 END) "
            + "          >= (CASE WHEN h.int_thread_mode = ? THEN 1 ELSE 0 END) "
            + "      AND l.int_cores_min <= h.int_cores "
            + "LEFT JOIN subscription sub ON sub.pk_show = j.pk_show AND sub.pk_alloc = h.pk_alloc "
            + "WHERE  j.str_state = 'PENDING' "
            + "  AND  j.b_paused  = false "
            + "  AND  NOT (string_to_array(lower(replace(l.str_tags, ' ', '')), '|') "
            + "            <@ string_to_array(?, ',')) "
            + "  AND  (h.pk_host IS NULL "
            + "        OR (sub.pk_subscription IS NOT NULL AND sub.int_cores < sub.int_burst)) "
            + "  AND  jr.int_cores  < jr.int_max_cores "
            + "  AND  COALESCE(ls.int_waiting_count, 0) > 0 "
            + "  AND (COALESCE(fr.int_max_cores, -1) = -1 "
            + "       OR COALESCE(fu.folder_cores, 0) + l.int_cores_min <= fr.int_max_cores) "
            + "  AND (? OR sh.b_scheduler_managed = true) "
            + "ORDER BY power(random(), 1.0 / GREATEST(jr.int_priority, 1)) DESC "
            + "LIMIT  ? ";
    // spotless:on

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
                    c.threadable = rs.getBoolean("b_threadable");
                    c.layerCoresMax = rs.getInt("int_cores_max");
                    c.layerGpusMin = rs.getInt("int_gpus_min");
                    c.layerGpuMemMin = rs.getLong("int_gpu_mem_min");
                    c.priority = rs.getInt("int_priority");
                    c.jobCoresInUse = rs.getInt("job_cores_in_use");
                    c.jobMaxCores = rs.getInt("job_max_cores");
                    c.showCoresInUse = rs.getInt("show_cores_in_use");
                    c.showBurstCores = rs.getInt("show_burst");
                    c.showSizeCores = rs.getInt("show_size");
                    c.waitingFrameCount = rs.getInt("waiting_frame_count");
                    c.clockTimeHighSec = rs.getInt("clock_time_high");
                    c.frameSuccessCount = rs.getInt("frame_success_count");
                    c.folderId = rs.getString("folder_id");
                    c.folderMax = rs.getInt("folder_max"); // -1 = unlimited
                    c.folderRunning = rs.getInt("folder_running"); // core-points
                    // Limits bound to the layer, or null when none. Kept null
                    // rather than an empty list so the placement loop skips all
                    // limit work with one reference check.
                    List<String> lims = splitIds(rs.getString("limit_ids"));
                    c.limitIds = lims.isEmpty() ? null : lims;
                    return c;
                }
            };

    private static final RowMapper<PinRow> PINNED_MAPPER =
            (rs, i) -> new PinRow(CANDIDATE_MAPPER.mapRow(rs, i), rs.getString("pin_host"),
                    rs.getString("str_tags"));

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
            logger.debug("Maestro: previous tick still running, skipping");
            summarySkipped.incrementAndGet();
            return;
        }
        long t0 = System.currentTimeMillis();
        try {
            // Inside the try: pool startup parses properties and builds the license
            // source, and a throw here would otherwise skip the finally and leave
            // tickInFlight set, which stops every later tick at the CAS above.
            startSchedulerPoolsIfNeeded();
            int dispatched = doTick();
            if (dispatched >= 0) {
                long ms = System.currentTimeMillis() - t0;
                // Per-tick detail at DEBUG; INFO gets one consolidated stat line per
                // window (maybeLogStat, called in the finally below).
                logger.debug("Maestro tick: dispatched " + dispatched + " procs, " + ms
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
                if (maestroMetrics != null && lastTickStats != null) {
                    lastTickStats.tickDurationMs = ms;
                    maestroMetrics.recordTick(lastTickStats);
                }
            }
        } catch (RuntimeException e) {
            logger.error("Maestro tick failed", e);
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
        List<QueuedFrameCompletion> resolved = MaestroCompletionQueue.drain();
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
                    logger.info("Maestro drain: stopFramesBatch(" + chunk.size() + ") took "
                            + tChunk + "ms");
                }
                for (int i = 0; i < won.length; i++) {
                    QueuedFrameCompletion c = chunk.get(i);
                    // Ledger: the proc is released on both branches (stop won, or
                    // stale and unbooked), so its cores leave the show either way.
                    bumpShowCoresLive(c.frame.show,
                            -c.proc.coresReserved / (double) CORE_POINTS_PER_CORE);
                    if (runningFramesLive > 0)
                        runningFramesLive--;
                    if (won[i]) {
                        if (localityEnabled && localityWindowFrames > 0
                                && c.proc.getLayerId() != null) {
                            warmthByHost.computeIfAbsent(c.proc.getHostId(), k -> new HashMap<>())
                                    .put(c.proc.getLayerId(),
                                            bookingsByHost.getOrDefault(c.proc.getHostId(), 0L));
                        }
                        frameCompleteHandler.queuePostOps(c);
                    } else {
                        frameCompleteHandler.handleStaleCompletion(c.proc, c.report,
                                c.proc.getName() + "/" + c.frame.getName());
                    }
                }
            } catch (RuntimeException e) {
                logger.warn("Maestro drain: batch of " + chunk.size()
                        + " completions failed, retrying per-report: " + e);
                for (QueuedFrameCompletion c : chunk) {
                    try {
                        frameCompleteHandler.processReportNow(c.report);
                    } catch (RuntimeException e2) {
                        logger.warn("Maestro drain: completion for frame " + c.frame.getName()
                                + " failed: " + e2);
                    }
                }
            }
        }
        long tDrain = System.currentTimeMillis() - tDrain0;
        if (tDrain > 1000) {
            logger.info("Maestro drain: " + drained + " completions in " + tDrain + "ms");
        }
        return drained;
    }

    /**
     * Expire cache-warmth entries displaced by a window's worth of foreign frames on their host.
     * Idle hosts' entries never expire because nothing displaced them.
     *
     * Bound: O(W) once per tick.
     */
    private void expireDisplacedWarmth() {
        if (warmthByHost.isEmpty())
            return;
        for (Map.Entry<String, Map<String, Long>> h : warmthByHost.entrySet()) {
            long odo = bookingsByHost.getOrDefault(h.getKey(), 0L);
            h.getValue().values().removeIf(seen -> odo - seen >= localityWindowFrames);
        }
        warmthByHost.values().removeIf(Map::isEmpty);
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
     * gating limits are in play (frames booked against a limit, candidates a limit held back, and
     * planned frames trimmed at commit because a limit could not cover them).
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

        // Limit section, only when a gating limit is actually in play, so the
        // line stays as it was on the many farms that use no limits.
        String lic = "";
        if (summaryLicenseBooked > 0 || summaryLicenseHeld > 0) {
            lic = String.format(" | lic booked=%d held=%d trimmed=%d", summaryLicenseBooked,
                    summaryLicenseHeld, summaryLicenseTrimmed);
        }

        // Waitlist section: the window's PEAK waiting frames per cause (not the last
        // tick), so a cause that spiked for a single tick still shows here.
        String waitlist = String.format(
                " | waitlist total=%d flowing=%d capacity=%d nofit=%d limit=%d license=%d held=%d"
                        + " share=%d strand=%d nohost=%d",
                winWaitTotalMax, winWaitMax.getOrDefault("flowing", 0L),
                winWaitMax.getOrDefault("capacity", 0L), winWaitMax.getOrDefault("no fit", 0L),
                winWaitMax.getOrDefault("limit", 0L), winWaitMax.getOrDefault("no license", 0L),
                winWaitMax.getOrDefault("held", 0L), winWaitMax.getOrDefault("share", 0L),
                winWaitMax.getOrDefault("strand", 0L), winWaitMax.getOrDefault("no host", 0L));

        logger.info(String.format(
                "Maestro stat: win=%ds ticks=%d skipped=%d lockLost=%d avgTick=%dms maxTick=%dms"
                        + " | farm hosts=%d idleHosts=%d cores=%d idleCores=%d util=%.1f%% groups=%d"
                        + " | flow committed=%d planned=%d raceLost=%d launchDropped=%d drained=%d postQ=%d"
                        + " | resv held=%d reservedCores=%d granted=%d reqs=%d backfilled=%d backfilledCores=%d%s%s",
                win, summaryTicks, skipped, summaryLockLost, avgTick, summaryMaxTickMs, lastHosts,
                lastIdleHosts, coresTotal, idleCores, util, lastGroups, summaryDispatched,
                summaryPlanned, raceLost, droppedInWindow, summaryDrained,
                frameCompleteHandler == null ? 0 : frameCompleteHandler.getPostCompleteQueueDepth(),
                reservations.size(), reservedCp / CORE_POINTS_PER_CORE, summaryGranted,
                lastReservationReqs, summaryBackfilled,
                summaryBackfilledCores / CORE_POINTS_PER_CORE, lic, waitlist));

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
        winWaitMax.clear();
        winWaitTotalMax = 0;
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
        logger.warn("Maestro: " + groupCount + " host-spec groups for " + hostCount
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
        logger.debug("Maestro: folder ceiling trimmed " + folderTrimmed
                + " planned frame(s) over cap this tick");
        return keep;
    }

    /**
     * Hold every gating limit to its budget. Same gap as the folder ceiling: the plan read is
     * limit-blind, so this trim is what actually holds the line. FRAME limits count frames against
     * budget.usable; HOST limits charge a seat only for hosts not already seated, and a frame's
     * limits are spent only once it is certain to be kept (so a frame rejected by its second limit
     * never consumes a seat in its first). A limit with no budget entry does not gate (ADVISORY,
     * DISABLED, or stale report). Dropped frames stay WAITING for the next tick. Returns the kept
     * bookings.
     */
    private List<FrameBooking> trimOverLimitBudgets(List<FrameBooking> planned,
            Map<String, LimitBudget> limitBudgets, Map<String, List<String>> layerLimits) {
        if (limitBudgets.isEmpty() || layerLimits.isEmpty() || planned.isEmpty())
            return planned;
        Map<String, Integer> committedByLimit = new HashMap<>();
        Map<String, Set<String>> seatsByLimit = new HashMap<>();
        List<FrameBooking> keep = new ArrayList<>(planned.size());
        int limTrimmed = 0;
        for (FrameBooking b : planned) {
            List<String> limIds = layerLimits.get(b.proc.getLayerId());
            if (limIds == null) {
                keep.add(b);
                continue;
            }
            String hostName = shortHostName(b.proc.hostName);
            boolean fits = true;
            for (String limId : limIds) {
                LimitBudget bd = limitBudgets.get(limId);
                if (bd == null)
                    continue;
                if (bd.hostBased) {
                    Set<String> seats =
                            seatsByLimit.computeIfAbsent(limId, k -> new HashSet<>(bd.seats));
                    if (!seats.contains(hostName) && seats.size() >= bd.seatCap) {
                        fits = false;
                        break;
                    }
                } else if (committedByLimit.getOrDefault(limId, 0) + 1 > bd.usable) {
                    fits = false;
                    break;
                }
            }
            if (!fits) {
                limTrimmed++;
                continue;
            }
            for (String limId : limIds) {
                LimitBudget bd = limitBudgets.get(limId);
                if (bd == null)
                    continue;
                if (bd.hostBased) {
                    seatsByLimit.get(limId).add(hostName);
                } else {
                    committedByLimit.merge(limId, 1, Integer::sum);
                }
            }
            keep.add(b);
        }
        if (limTrimmed == 0)
            return planned;
        tickLicenseTrimmed += limTrimmed;
        logger.debug("Maestro: limit budgets trimmed " + limTrimmed
                + " planned frame(s) over availability this tick");
        return keep;
    }

    /**
     * Drop reservation and blocked-debt state for layers that left the dispatchable set this tick,
     * so a layer that disappears and returns starts its block timer fresh.
     */
    void sweepStaleReservationState(Set<String> seenLayerIds) {
        reservations.entrySet().removeIf(e -> !seenLayerIds.contains(e.getValue().layerId));
        hostsByLayer.keySet().removeIf(layerId -> !seenLayerIds.contains(layerId));
        blockedDebtMs.keySet().removeIf(id -> !seenLayerIds.contains(id));
        lastSeenMs.keySet().removeIf(id -> !seenLayerIds.contains(id));
    }

    /**
     * Grant reservations in priority-weighted lottery order (the same Efraimidis-Spirakis weighting
     * dispatch uses), so the scarce budget is shared roughly in proportion to priority and a
     * low-priority wide job still wins a grant now and then instead of being starved by a
     * higher-priority stream. Existing reservers are always reconciled (refresh or release
     * promptly); new qualifiers get at most maestro.reservation_max_grantees grants this tick, the
     * rest draw again next tick.
     */
    private void grantReservations(List<ReservationRequest> reservationReqs) {
        int reservationMaxGrantees =
                env.getProperty("maestro.reservation_max_grantees", Integer.class, 8);
        sortByPriorityLottery(reservationReqs);
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
            logger.info("Maestro resv-grant: newGrantees=" + newGrantees + " totalHeld="
                    + reservations.size());
        }
        tickGranted = newGrantees;
        lastReservationReqs = reservationReqs.size();
    }

    /**
     * Order reservation requests by a priority-weighted lottery: each draws key =
     * random()^(1/priority) (Efraimidis-Spirakis) and grants go out in descending key order. The
     * expected rank rises with priority, so high-priority work is favored, yet every request has a
     * nonzero chance of leading, which keeps a low-priority wide job from being starved of grants
     * under a steady higher-priority stream. This mirrors the dispatch lottery, so the scarce
     * reservation budget gets the same fairness with no separate anti-starvation deadline.
     */
    private void sortByPriorityLottery(List<ReservationRequest> reqs) {
        for (ReservationRequest r : reqs) {
            int pri = Math.max(1, r.candidate.priority);
            r.grantKey = Math.pow(ThreadLocalRandom.current().nextDouble(), 1.0 / pri);
        }
        reqs.sort((a, b) -> Double.compare(b.grantKey, a.grantKey));
    }

    /**
     * DEBUG-only per-tick reservation summary, guarded so the string is never built when DEBUG is
     * off. INFO sees only actual new grants and the held count in the minute heartbeat.
     */
    private void logReservationTick(List<ReservationRequest> reservationReqs, int cap) {
        if (!logger.isDebugEnabled() || (reservationReqs.isEmpty() && reservations.isEmpty()))
            return;
        StringBuilder sb = new StringBuilder();
        sb.append("Maestro resv-tick: requests=").append(reservationReqs.size()).append(" cap=")
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
        jobCells.clear();
        showCells.clear();
        limitCells.clear();
        folderCells.clear();
        folderMaxCp.clear();
        folderRunSeed.clear();
        jobFolderCap.clear();
        layerLimits.clear();
        limitBudgets.clear();
        limitSeats.clear();
        limitBudgetsResolved = false;
        seenLayerIds.clear();
        pinnedByGroup.clear();
        reservationReqs.clear();
        waitReasonByLayer.clear();
        waitFramesByLayer.clear();
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
     *
     * Bound: one candidate query, the group loop, then O(H log W) for the stranded cores.
     */
    private int planGroup(HostSpecKey spec, List<BookableHost> fullGroup,
            MaestroMetrics.TickStats stats) {
        List<BookableHost> idleGroup = new ArrayList<>();
        for (BookableHost h : fullGroup) {
            if (h.coresIdle >= Dispatcher.CORE_POINTS_RESERVED_MIN)
                idleGroup.add(h);
        }
        int maxCoresTotalInGroup = fullGroup.stream().mapToInt(h -> h.coresTotal).max().orElse(0);

        List<LayerCandidate> candidates;
        try {
            candidates = readLayerCandidatesForGroup(spec, maxCoresTotalInGroup);
            addPinned(candidates, pinnedByGroup.get(spec), idleGroup);
            // Size threadable layers from their observed rss before anything scores or
            // fits them, against the studio's memory-per-core policy ratio (or, when
            // none is set, this group's own derived one); 1-core layers with no
            // evidence yet stay unproven and get the probe gate.
            resizeFromLiveMem(candidates, layerLiveMem,
                    memPerCoreKb > 0 ? memPerCoreKb : memPerWholeCoreKb(fullGroup), layerResize);
        } catch (RuntimeException e) {
            long nowMs = System.currentTimeMillis();
            if (nowMs - lastCandidateErrWarnMs >= GROUP_WARN_INTERVAL_MS) {
                lastCandidateErrWarnMs = nowMs;
                logger.warn("Maestro: candidate query failed for " + spec
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
        resolveLimitBudgets(candidates, layerLimits, limitBudgets);
        int booked = dispatchGroupWithScoring(idleGroup, fullGroup, candidates, seenLayerIds,
                spec.pkAlloc, reservationReqs, limitSeats);
        stats.strandedCores += strandedWholeCores(fullGroup, candidates);
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
        logger.debug("Maestro group: " + spec + " hosts=" + fullGroup.size() + " idle="
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
     * the survivors in one batch, and launch them. See maestro.md for the full model.
     *
     * Bound: O(K + H) to drain and snapshot, the groups (see dispatchGroupWithScoring), one window
     * read per planned layer, O(F) procs, F frames committed in chunks and F launches queued. The
     * one product left is slots times classes of equal host state.
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
            logger.debug("Maestro: another Cuebot holds the planning lock");
            summaryLockLost++;
            return -1;
        }

        long tStart = System.currentTimeMillis();
        MaestroMetrics.TickStats stats = new MaestroMetrics.TickStats();
        lastTickStats = stats;
        resetTickOutputs();
        try {
            dispatchSupport.sweepOrphanedProcs(10);
        } catch (RuntimeException e) {
            logger.warn("Maestro: orphan sweep failed: " + e);
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
        warnIfGroupsFragmented(groups.size(), allHosts.size());

        // Tick-scoped snapshots: hostById is local; tReadyByHost and hostLayerAffinity are
        // read fresh into their fields; the cap/license/reservation scratch fields were reset
        // in clearTickScratch.
        Map<String, BookableHost> hostById = new HashMap<>();
        for (BookableHost h : allHosts)
            hostById.put(h.hostId, h);
        tReadyByHost = computeHostReadySeconds(hostById);
        hostLayerAffinity = readHostLayerAffinity();
        bindTickState(allHosts);
        readPinnedCandidates(groups, hostById);

        // 3. PLAN each host-spec group in priority order.
        int dispatched = 0;
        for (Map.Entry<HostSpecKey, List<BookableHost>> g : groups.entrySet())
            dispatched += planGroup(g.getKey(), g.getValue(), stats);
        tallyWaitlist(stats);

        grantReservations(reservationReqs);

        // 4. PLAN bookings in parallel, then trim to the exact folder + limit budgets.
        long tPlan = System.currentTimeMillis();
        List<FrameBooking> planned = planBookings(hostById);
        if (planned == null)
            return dispatched; // interrupted mid-plan; abort before committing
        planned = trimOverFolderCeiling(planned, folderMaxCp, folderRunSeed, jobFolderCap);
        planned = trimOverLimitBudgets(planned, limitBudgets, layerLimits);
        long tRead = System.currentTimeMillis();
        tickPlanned = planned.size();

        // 4b. COMMIT the survivors and their resource accounting in ONE transaction, then
        // launch them. DispatchSupportService is REQUIRED, so the batch joins this
        // transaction rather than opening its own: procs and the counters that mirror them
        // commit together or not at all. Splitting them let a crash in between leave procs
        // whose cores were never added, while the release path subtracts them regardless,
        // and four of the five mirrors have no repair job to undo that.
        List<FrameBooking> committed = commitInChunks(planned);
        long tCommit = System.currentTimeMillis();
        recordCommitted(committed, stats);
        // Publish the ledger AFTER this tick's bookings landed: at this point it
        // holds the procs alive right now (booked minus drained). Filling it at
        // tick start would sample the post-drain trough, where a fast-completing
        // farm reads as empty every time.
        if (maestroMetrics != null && maestroMetrics.isEnabled()) {
            stats.coresByShow.putAll(showCoresLive);
            stats.runningFrames = runningFramesLive;
            if (farmHealth != null)
                aggregateFarmHealth(groups, farmHealth.snapshot(), stats);
        }
        int dispatchedNow = committed.size();
        long tFlush = System.currentTimeMillis();
        if (tFlush - tStart > 1000) {
            logger.info("Maestro tick breakdown: place=" + (tPlan - tStart) + "ms, read="
                    + (tRead - tPlan) + "ms, batchCommit=" + (tCommit - tRead) + "ms, flush+launch="
                    + (tFlush - tCommit) + "ms | placements=" + lastPlacements + " planned="
                    + planned.size() + " committed=" + dispatchedNow);
        }
        dispatched = dispatchedNow;

        sweepStaleReservationState(seenLayerIds);
        return dispatched;
    }

    /**
     * Commit the planned bookings in transactions of at most COMMIT_CHUNK_FRAMES frames, cut on
     * host boundaries so a host's bookings stay in one transaction (the capacity gate is per host,
     * and planBookings emits each host's bookings together). A tick may plan a whole idle farm at
     * once; one transaction for all of it would hold every booked host row and stat row for minutes
     * and show nothing until the end. A chunk holds its locks for a bounded window, lands its procs
     * as it goes, and launches them as it goes. Each chunk commits with its own resource deltas, so
     * procs and their mirrors still land together or not at all.
     *
     * Bound: O(F) in F / COMMIT_CHUNK_FRAMES transactions.
     */
    private List<FrameBooking> commitInChunks(List<FrameBooking> planned) {
        List<FrameBooking> committed = new ArrayList<>();
        int start = 0;
        while (start < planned.size()) {
            int end = Math.min(start + COMMIT_CHUNK_FRAMES, planned.size());
            while (end < planned.size() && planned.get(end).proc.getHostId()
                    .equals(planned.get(end - 1).proc.getHostId()))
                end++;
            final List<FrameBooking> chunk = new ArrayList<>(planned.subList(start, end));
            if (!leaderAlive()) {
                logger.warn("Maestro: leadership lost mid-commit, " + (planned.size() - start)
                        + " planned frames left for the next leader");
                break;
            }
            List<FrameBooking> won = txTemplate().execute(status -> {
                List<FrameBooking> w = dispatchSupport.startFramesAndProcsBatch(chunk);
                applyResourceDeltas(w);
                return w;
            });
            // Publish and launch this chunk now, outside its transaction: a slow
            // publish never extends the lock window, and the frames start while
            // the later chunks are still committing instead of after the last.
            dispatchSupport.publishFrameStartedEvents(won);
            launchCommitted(won);
            committed.addAll(won);
            start = end;
        }
        return committed;
    }

    /**
     * Read the frames of every planned layer and build procs in memory (no DB writes), in two
     * rounds on the bounded read pool: one frame window per planned layer and thread-mode class,
     * read against one of its planned hosts (the slice query's other host terms are layer terms
     * every planned host satisfies), then one task per host that plans each pair from its range of
     * the window; a host is booked serially within its task because planFrames decrements its idle
     * fields as it books. A layer planned for plan_zero_warn_ticks ticks with zero bookable frames
     * is warned. Returns null if a wait was interrupted.
     *
     * Bound: one query per planned layer and thread-mode class, then O(F) in memory.
     */
    private List<FrameBooking> planBookings(Map<String, BookableHost> hostById) {
        int planZeroWarnTicks = env.getProperty("maestro.plan_zero_warn_ticks", Integer.class, 40);
        lastPlacements = 0;
        Set<String> plannedLayerIds = new HashSet<>();
        Map<String, WindowRead> windowReads = new HashMap<>();
        for (Map.Entry<String, List<String>> e : plannedByHost.entrySet()) {
            lastPlacements += e.getValue().size();
            BookableHost h = hostById.get(e.getKey());
            for (String layerId : e.getValue()) {
                plannedLayerIds.add(layerId);
                windowReads.putIfAbsent(windowKey(layerId, h), new WindowRead(layerId, h));
            }
        }
        Map<String, List<DispatchFrame>> windows = new ConcurrentHashMap<>();
        List<Callable<Void>> reads = new ArrayList<>(windowReads.size());
        for (Map.Entry<String, WindowRead> e : windowReads.entrySet()) {
            final String key = e.getKey();
            final WindowRead w = e.getValue();
            reads.add(() -> {
                // The window read binds the layer id only; no lookup needed.
                windows.put(key, dispatchSupport.findNextDispatchFrames(new LayerEntity(w.layerId),
                        dispatchHostOf(w.reader), plannedFramesByLayer.get(w.layerId)));
                return null;
            });
        }
        if (runAll(reads, "window reads") == null)
            return null;

        List<Callable<List<FrameBooking>>> tasks = new ArrayList<>(plannedByHost.size());
        for (Map.Entry<String, List<String>> e : plannedByHost.entrySet()) {
            final String hostId = e.getKey();
            final List<String> layerIds = e.getValue();
            tasks.add(() -> {
                List<FrameBooking> out = new ArrayList<>();
                BookableHost snap = hostById.get(hostId);
                DispatchHost host = dispatchHostOf(snap);
                for (String layerId : layerIds) {
                    // The rss resize Maestro scored with, so the commit books the
                    // same shape. {cores, memKb}; absent = book the layer's own ask.
                    long[] rz = layerResize.get(layerId);
                    List<FrameBooking> got = dispatcher.planFrames(host,
                            sliceOf(windows.get(windowKey(layerId, snap)),
                                    snap.planned.get(layerId)),
                            rz != null ? (int) rz[0] : 0, rz != null ? rz[1] : 0);
                    if (got.isEmpty()) {
                        int streak = planZeroStreak.merge(layerId, 1, Integer::sum);
                        if (streak % planZeroWarnTicks == 0) {
                            logger.warn("Maestro: layer " + layerId + " planned " + streak
                                    + " consecutive ticks (last host " + host.getName()
                                    + ") but planFrames found 0 bookable frames each time."
                                    + " A dispatch-query gate Maestro does not model is"
                                    + " rejecting it (thread mode, limit, local booking, ...):"
                                    + " enable DEBUG on this class and read the 'Maestro"
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
        List<List<FrameBooking>> got = runAll(tasks, "plan tasks");
        if (got == null)
            return null;
        List<FrameBooking> planned = new ArrayList<>();
        for (List<FrameBooking> g : got)
            planned.addAll(g);
        // Streaks matter only while Maestro keeps choosing the layer; drop entries for
        // layers not planned this tick so the map tracks live pathologies, not vanished work.
        planZeroStreak.keySet().retainAll(plannedLayerIds);
        return planned;
    }

    /** One frame window to read: a planned layer and a planned host of the thread-mode class. */
    private static final class WindowRead {
        final String layerId; // consumed by planBookings()
        final BookableHost reader; // consumed by planBookings()

        WindowRead(String layerId, BookableHost reader) {
            this.layerId = layerId;
            this.reader = reader;
        }
    }

    /**
     * The window a plan on host h for a layer reads from: the layer's, split only by the
     * thread-mode class of the host, the one host term of the slice query Maestro's groups do not
     * share.
     */
    private static String windowKey(String layerId, BookableHost h) {
        return h.threadMode == ThreadMode.ALL_VALUE ? layerId + "|all" : layerId;
    }

    /** The frames of one plan's slice {offset, size} within its layer's window, clipped to it. */
    static List<DispatchFrame> sliceOf(List<DispatchFrame> window, int[] slice) {
        if (window == null || slice == null)
            return new ArrayList<>();
        int from = Math.min(slice[0], window.size());
        int to = Math.min(slice[0] + slice[1], window.size());
        return window.subList(from, to);
    }

    /**
     * Run the tasks on the read pool and collect the results of the ones that completed; a failed
     * task is logged and skipped, an interrupted wait returns null.
     */
    private <T> List<T> runAll(List<Callable<T>> tasks, String what) {
        List<T> out = new ArrayList<>(tasks.size());
        int failed = 0;
        String firstCause = null;
        try {
            for (Future<T> f : readPool.invokeAll(tasks)) {
                try {
                    out.add(f.get());
                } catch (ExecutionException ee) {
                    failed++;
                    if (firstCause == null)
                        firstCause =
                                ee.getCause() != null ? ee.getCause().toString() : ee.toString();
                }
            }
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            return null;
        }
        if (failed > 0)
            logger.warn("Maestro: " + failed + " of " + tasks.size() + " " + what
                    + " failed this tick, first cause: " + firstCause);
        return out;
    }

    /**
     * Resize threadable candidates from the layer's observed rss BEFORE placement, so scoring, fit,
     * caps, accounting and booking all see the layer's real shape. The size is the median rss of
     * the layer's recent frames ({@link LayerLiveMem}), never the declared memory: declarations
     * lie, running processes do not, and a single haywire process is one sample and cannot resize
     * the layer. cores = round(rss / memPerCoreKb), never below the ask, never past the layer's
     * max; memory = max(declared, rss) so packing stops trusting an under-declaration too. A layer
     * with no evidence keeps its ask; when that ask is exactly 1 core ("let the system decide", the
     * shape nobody sized) it stays rssProven=false, which arms the probe gate in the dispatch loop:
     * at most {@link #PROBE_FRAMES} of its frames run until the farm has seen it (the production
     * rss-watcher script's loop, inside the scheduler). An explicit ask of 2+ cores was sized by
     * someone and books at full speed from frame one. A held layer that has already completed a
     * probe's worth of frames without ever landing in a report runs too fast to sample and is
     * released, never starved. Non-threadable layers are never resized (a single-threaded renderer
     * cannot use the cores). The metric is the group's own memory-per-core, derived from the
     * machines each tick, never configuration.
     */
    static void resizeFromLiveMem(List<LayerCandidate> candidates, LayerLiveMem liveMem,
            long memPerCoreKb, Map<String, long[]> resizeOut) {
        for (LayerCandidate c : candidates) {
            if (liveMem == null || !c.threadable || memPerCoreKb <= 0 || c.layerCoresMin <= 0) {
                c.rssProven = true;
                continue;
            }
            long typKb = liveMem.typicalRssKb(c.layerId);
            if (typKb <= 0) {
                // No evidence. Only a 1-core ask probes: nobody sized it, so nothing
                // about it can be trusted until the reports have seen it. A layer that
                // completed a probe's worth of frames unsampled is too fast to sample.
                c.rssProven = c.layerCoresMin != 100 || c.frameSuccessCount >= PROBE_FRAMES;
                continue;
            }
            c.rssProven = true;
            int eff = (int) Math.round(typKb / (double) memPerCoreKb) * 100;
            if (c.layerCoresMax > 0 && eff > c.layerCoresMax) {
                eff = c.layerCoresMax;
            }
            int cores = Math.max(c.layerCoresMin, eff);
            long memKb = Math.max(c.layerMemMin, typKb);
            if (cores != c.layerCoresMin || memKb != c.layerMemMin) {
                c.layerCoresMin = cores;
                c.layerMemMin = memKb;
                resizeOut.put(c.layerId, new long[] {cores, memKb});
            }
        }
    }

    /**
     * The group's own memory-per-core in KB (whole cores), the self-derived sizing metric: total
     * bookable memory over total cores of the group's hosts. On a 3.5G-per-core farm an 18G layer
     * sizes to 5 cores; buy different machines and the figure follows, with no configuration.
     */
    static long memPerWholeCoreKb(List<BookableHost> hosts) {
        long mem = 0;
        long cores = 0;
        for (BookableHost h : hosts) {
            mem += h.memTotal;
            cores += h.coresTotal;
        }
        long wholeCores = cores / 100;
        return wholeCores > 0 ? mem / wholeCores : 0;
    }

    /**
     * Fold the committed bookings into the per-show throughput tally and the live cores-per-show
     * ledger (the show_cores gauge's only source: stats never query the database), then apply their
     * resource accounting deltas and flush one UPDATE per changed row.
     */
    private void recordCommitted(List<FrameBooking> committed, MaestroMetrics.TickStats stats) {
        for (FrameBooking b : committed) {
            stats.framesByShow.merge(b.frame.show, 1, Integer::sum);
            bumpShowCoresLive(b.frame.show, b.proc.coresReserved / (double) CORE_POINTS_PER_CORE);
            runningFramesLive++;
        }
    }

    /**
     * Mirror the winners' cores and gpus into the subscription, layer, job, folder and point
     * counters. Called INSIDE the booking transaction, so a failure here rolls the bookings back
     * with it and there is nothing left over to retry: the procs those deltas describe never
     * existed.
     *
     * Bound: O(winners), then one update per distinct counter.
     */
    private void applyResourceDeltas(List<FrameBooking> committed) {
        if (committed.isEmpty()) {
            return;
        }
        List<VirtualProc> procs = new ArrayList<>(committed.size());
        for (FrameBooking b : committed)
            procs.add(b.proc);
        accumulateResourceDeltas(procs);
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
     *
     * Bound: O(F); the environments are read once per distinct job and layer.
     */
    private void launchCommitted(List<FrameBooking> committed) {
        if (localityEnabled && localityWindowFrames > 0) {
            for (FrameBooking b : committed) {
                long odo = bookingsByHost.merge(b.proc.getHostId(), 1L, Long::sum);
                if (b.proc.getLayerId() != null) {
                    Map<String, Long> warm = warmthByHost.get(b.proc.getHostId());
                    if (warm != null && warm.containsKey(b.proc.getLayerId()))
                        warm.put(b.proc.getLayerId(), odo);
                }
            }
        }
        LaunchEnv env = new LaunchEnv(); // consumed by runFrame()
        for (FrameBooking b : committed) {
            final FrameBooking fb = b;
            launchPool.execute(() -> {
                try {
                    dispatchSupport.runFrame(fb.proc, fb.frame, env);
                } catch (RqdLaunchUnknownOutcomeException e) {
                    // RQD may have started the frame: confirm before anything
                    // is released, else the frame could run twice.
                    dispatchSupport.resolveUnknownLaunchOutcome(fb.proc, fb.frame);
                } catch (RuntimeException e) {
                    logger.warn("Maestro: RQD launch failed for " + fb.proc.getName() + " on frame "
                            + fb.frame.getFrameId() + ": " + e.getMessage()
                            + ", unbooking and clearing frame");
                    try {
                        dispatchSupport.unbookProc(fb.proc);
                        dispatchSupport.clearFrame(fb.frame);
                        rqdClient.killFrame(fb.proc, "launch failed during scheduler dispatch");
                    } catch (RuntimeException ce) {
                        logger.warn("Maestro: launch-failure cleanup partial for "
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
            logger.warn("Maestro: planning-lock connection lost; demoting to standby");
            closeLeaderConn();
            return false;
        }
        Connection conn = null;
        try {
            conn = openLeaderConnection();
            if (acquireLeaderLock(conn)) {
                leaderConn = conn;
                logger.info("Maestro: acquired planning leadership (sticky)");
                return true;
            }
            conn.close();
            return false;
        } catch (SQLException e) {
            logger.warn("Maestro: leadership probe failed: " + e.getMessage());
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
    /** Whether this cuebot still holds the planning lock: the lock connection is alive. */
    private boolean leaderAlive() {
        Connection held = leaderConn;
        try {
            return held != null && held.isValid(1);
        } catch (SQLException e) {
            return false;
        }
    }

    private void closeLeaderConn() {
        Connection held = leaderConn;
        leaderConn = null;
        // The next leader plans from the database, not from this Maestro's
        // memory: reservations, blocked debt, warmth and odometers go with
        // the lock.
        reservations.clear();
        hostsByLayer.clear();
        blockedDebtMs.clear();
        lastSeenMs.clear();
        warmthByHost.clear();
        bookingsByHost.clear();
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
            logger.debug("Maestro: pg_advisory_unlock failed (probably connection drop): "
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

    /**
     * Live cores-per-show ledger, no SQL: stats never query the database. The scheduler is the
     * single writer for its shows, so it counts what it sees flow: plus the proc's cores when its
     * batch commit books a frame, minus when the drain applies that frame's completion (won or
     * stale, the proc is released either way). A show whose count reaches zero drops out of the
     * map, which also bounds the small leaks this bookkeeping accepts: a proc released outside the
     * drain (a lost host, a failed launch) leaks its cores only until its show drains empty. A
     * fresh leader starts the ledger empty and converges as its own bookings flow.
     */
    private final Map<String, Double> showCoresLive = new HashMap<>();

    // Live running-frame count, same ledger discipline as showCoresLive (one booking
    // is one frame on a proc; one drained completion releases it). The denominator
    // that turns the waitlist's blocked counts into a share of ALL frames the farm
    // handles right now, so a small blocked slice reads small.
    private long runningFramesLive = 0;

    /** Ledger update: {@code delta} whole cores for {@code show}; at zero the entry drops out. */
    private void bumpShowCoresLive(String show, double delta) {
        if (show == null)
            return;
        showCoresLive.compute(show, (k, v) -> {
            double next = (v == null ? 0.0 : v) + delta;
            return next < 0.001 ? null : next;
        });
    }

    /**
     * Host->layer affinity: which layers currently have at least one proc booked on each host.
     * Drives the locality bonus (see {@link #localityBonus}). A proc carries pk_layer directly, so
     * no join is needed. A just-completed proc has been unbooked (row deleted), so only live
     * placements appear.
     */
    /**
     * Hand each host its tick state, so the scan reads fields where it used to look up host-keyed
     * maps for every host of every slot: the layers it runs and their frame counts, its plan
     * slices, its cache warmth and odometer, its reservation and its ready time. Bound once per
     * tick, after the reads that fill the maps; the plan slices start empty.
     *
     * Bound: O(H).
     */
    private void bindTickState(List<BookableHost> hosts) {
        for (BookableHost h : hosts) {
            h.layersRunning = hostLayerAffinity.get(h.hostId);
            h.layerFrames = hostLayerFrames.computeIfAbsent(h.hostId, k -> new HashMap<>());
            h.planned = new HashMap<>();
            h.warmth = warmthByHost.get(h.hostId);
            h.odometer = bookingsByHost.getOrDefault(h.hostId, 0L);
            h.reservation = reservations.get(h.hostId);
            h.tReady = tReadyByHost.get(h.hostId);
            h.coresIdleAtBind = h.coresIdle;
            h.memIdleAtBind = h.memIdle;
            h.gpusIdleAtBind = h.gpusIdle;
            h.gpuMemIdleAtBind = h.gpuMemIdle;
        }
    }

    /**
     * The dispatch host the plan read books against, built from the tick's own snapshot instead of
     * re-read from the database: the same row Maestro scored, at the idle values it planned from
     * (placement decrements the live ones). The snapshot holds only UP, OPEN hosts, so those two
     * states are constants here. Saves one round trip per planned host; a host whose database row
     * moved since the snapshot is caught by the commit's guarded update.
     */
    private static DispatchHost dispatchHostOf(BookableHost h) {
        DispatchHost d = new DispatchHost();
        d.id = h.hostId;
        d.name = h.hostName;
        d.allocationId = h.pkAlloc;
        d.facilityId = h.pkFacility;
        d.threadMode = h.threadMode;
        d.cores = h.coresTotal;
        d.memory = h.memTotal;
        d.gpus = h.gpusTotal;
        d.gpuMemory = h.gpuMemTotal;
        d.idleCores = h.coresIdleAtBind;
        d.idleMemory = h.memIdleAtBind;
        d.idleGpus = h.gpusIdleAtBind;
        d.idleGpuMemory = h.gpuMemIdleAtBind;
        d.tags = h.tagsRaw;
        d.setOs(h.os);
        d.lockState = LockState.OPEN;
        d.hardwareState = HardwareState.UP;
        return d;
    }

    private Map<String, Set<String>> readHostLayerAffinity() {
        Map<String, Set<String>> affinity = new HashMap<>();
        Map<String, Map<String, Integer>> counts = new HashMap<>();
        hostLayerFrames = counts;
        layerRunningFrames = new HashMap<>();
        layerProbeUsed.clear();
        layerResize.clear();
        plannedFramesByLayer.clear();
        if (!localityEnabled && layerHostMaxFrac <= 0)
            return affinity;
        getJdbcTemplate().query("SELECT pk_host, pk_layer, COUNT(*) AS n FROM proc "
                + "WHERE pk_layer IS NOT NULL GROUP BY pk_host, pk_layer", rs -> {
                    String host = rs.getString("pk_host");
                    String layer = rs.getString("pk_layer");
                    affinity.computeIfAbsent(host, k -> new HashSet<>()).add(layer);
                    counts.computeIfAbsent(host, k -> new HashMap<>()).put(layer, rs.getInt("n"));
                    layerRunningFrames.merge(layer, rs.getInt("n"), Integer::sum);
                });
        return affinity;
    }

    /**
     * The soft cap's yield test: whether another candidate of this group could still use host h.
     * True when some other layer has waiting frames, fits the host as it stands now, is under its
     * own per-host cap there, and is not held by its job cap, show burst or a full limit, all read
     * against the tick-wide usage maps. The cap is a contention rule: while other work waits for a
     * machine, no layer takes more than its share of it; with nobody else able to use the machine,
     * holding the cap would only strand it. Candidates later in the draw count as waiting, which is
     * the point: the yield must not run ahead of their turn.
     *
     * Bound: O(live wanters of the group).
     */
    private boolean othersWant(BookableHost h, LayerCandidate c) {
        for (int i = 0; i < alive.size();) {
            LayerCandidate o = alive.get(i);
            if (o.waitingFrameCount <= 0) {
                dropAt(alive, i);
                continue;
            }
            i++;
            if (o == c || !pinsAllow(o, h) || !fitsOnHost(o, h))
                continue;
            if (layerFramesOn(h, o) >= layerHostCap(h, o))
                continue;
            if (openToPlace(o) && !hostSeatBlocked(h, o))
                return true;
        }
        return false;
    }

    /**
     * The group's waiting candidates, as one list and as one list per dimension they need. Both are
     * walked by the strand and yield tests, which drop a candidate for good once its frames are
     * gone, since waiting only falls within a group; open or closed is read live at each visit,
     * since a negative-cores placement can reopen a cap. So a walk costs the live wanters it
     * passes, not the group, and a dimension nobody waits for costs nothing.
     *
     * Bound: O(C x D).
     */
    void bindWaiting(List<LayerCandidate> candidates) {
        alive.clear();
        needers.clear();
        for (Dim d : DIMS)
            needers.add(new ArrayList<>());
        for (LayerCandidate c : candidates) {
            if (c.waitingFrameCount <= 0)
                continue;
            alive.add(c);
            for (Dim d : DIMS)
                if (d.need(c) > 0)
                    needers.get(d.ordinal()).add(c);
        }
    }

    private static void dropAt(List<LayerCandidate> list, int i) {
        list.set(i, list.get(list.size() - 1));
        list.remove(list.size() - 1);
    }

    /** Whether protecting d on a host can bound c at all: a dimension c needs is coupled to d. */
    private boolean rowCouples(Dim d, LayerCandidate c) {
        for (Dim e : DIMS)
            if (reachNeeds[d.ordinal()][e.ordinal()] > 0 && e.need(c) > 0)
                return true;
        return false;
    }

    /** Whether candidate o is held by none of its job, show or limit caps, read tick-wide. */
    static boolean openToPlace(LayerCandidate o) {
        if (o.jobCell.used + o.layerCoresMin > o.jobMaxCores)
            return false;
        if (o.showCell.used + o.layerCoresMin > o.showBurstCores)
            return false;
        if (limitFull(o))
            return false;
        return true;
    }

    /**
     * Frames of candidate c that host h can give away without lowering the reach of a resource c
     * does not need while a waiting candidate that needs it could ever fit on h. This is the
     * refusal a price cannot make: while GPU work waits, the cores and memory an idle GPU needs
     * stay with it, and every core beyond that bundle is still sold to CPU work. The bound is
     * closed-form. Reach is the least idle-over-need ratio across the dimensions that couple the
     * resource, and each frame of c takes need(c) from the dimensions c uses, so the frames that
     * keep the reach where it stands are (idle - reach * need per unit) / need(c) on each such
     * dimension, and the least of those wins. Zero puts h off-limits to c this tick; a slice on h
     * is cut to the value. "Could ever fit" rather than "fits now", so a host full of CPU work
     * drains toward the bundle as its frames finish. Nothing is protected when nobody waits for the
     * resource, and nothing bounds c when no resource on h is at stake.
     *
     * Bound: O(D), plus one wantedOn walk per coupled dimension at stake.
     */
    private int strandFreeFrames(BookableHost h, LayerCandidate c) {
        if (reachNeeds == null)
            return Integer.MAX_VALUE;
        long free = Integer.MAX_VALUE;
        for (Dim d : DIMS) {
            if (d.need(c) > 0 || d.idle(h) <= 0 || !rowCouples(d, c))
                continue;
            if (!wantedOn(d, h, c))
                continue;
            double keep = reach(d, h, c, reachNeeds, false);
            for (Dim e : DIMS) {
                double per = reachNeeds[d.ordinal()][e.ordinal()];
                if (per <= 0 || e.need(c) <= 0)
                    continue;
                free = Math.min(free,
                        (long) Math.floor((e.idle(h) - keep * per) / e.need(c) + 1e-9));
            }
        }
        return (int) Math.max(0, free);
    }

    /**
     * Whether a waiting candidate other than c needs d, could ever fit on h and is open to place.
     *
     * Bound: O(live needers of d).
     */
    boolean wantedOn(Dim d, BookableHost h, LayerCandidate c) {
        List<LayerCandidate> list = needers.get(d.ordinal());
        for (int i = 0; i < list.size();) {
            LayerCandidate o = list.get(i);
            if (o.waitingFrameCount <= 0) {
                dropAt(list, i);
                continue;
            }
            i++;
            if (o != c && pinsAllow(o, h) && hostCanEverFit(o, h) && openToPlace(o)
                    && !hostSeatBlocked(h, o))
                return true;
        }
        return false;
    }

    /** Frames of c on h as this tick sees them: booked at the read plus planned since. */
    private static int layerFramesOn(BookableHost h, LayerCandidate c) {
        return h.layerFrames.getOrDefault(c.layerId, 0);
    }

    /** Whether (h, c) already holds a plan slice this tick; a pair plans once per tick. */
    private static boolean plannedOn(BookableHost h, LayerCandidate c) {
        return h.planned.containsKey(c.layerId);
    }

    /** The odometer reading when c last left h, or null when h holds no warmth for c. */
    private static Long warmthOn(BookableHost h, LayerCandidate c) {
        return h.warmth == null ? null : h.warmth.get(c.layerId);
    }

    /**
     * Whether a FRAME limit bound to candidate o has spent its tick-wide budget, read from the
     * candidate's limit cells. A limit with no budget entry does not gate (see
     * resolveLimitBudgets); HOST limits are per host, see hostSeatBlocked.
     *
     * Bound: O(limits of o).
     */
    static boolean limitFull(LayerCandidate o) {
        if (o.limitCells == null)
            return false;
        for (int i = 0; i < o.limitCells.length; i++) {
            LimitBudget b = o.limitBound[i];
            if (b != null && !b.hostBased && o.limitCells[i].used >= b.usable)
                return true;
        }
        return false;
    }

    /**
     * Whether a HOST limit bound to candidate o keeps it off host h: the limit has no seat left and
     * h does not already hold one. The seat set is the tick's live one when the limit was gated
     * this tick, else the budget's snapshot.
     *
     * Bound: O(limits of o).
     */
    private boolean hostSeatBlocked(BookableHost h, LayerCandidate o) {
        if (o.limitBound == null)
            return false;
        for (LimitBudget b : o.limitBound) {
            if (b == null || !b.hostBased)
                continue;
            Set<String> seats = limitSeats.getOrDefault(b.id, b.seats);
            if (!seats.contains(shortHostName(h.hostName)) && seats.size() >= b.seatCap)
                return true;
        }
        return false;
    }

    /**
     * The warmth credit of candidate c on host h: the full bonus while c still runs there, the
     * bonus decayed by the foreign frames landed since while its cache is warm, else zero.
     */
    double warmCredit(BookableHost h, LayerCandidate c) {
        if (!localityEnabled)
            return 0;
        if (h.layersRunning != null && h.layersRunning.contains(c.layerId))
            return localityBonus;
        if (localityWindowFrames > 0) {
            Long seen = warmthOn(h, c);
            if (seen != null) {
                long foreign = h.odometer - seen;
                if (foreign >= 0 && foreign < localityWindowFrames)
                    return localityBonus * (1.0 - (double) foreign / localityWindowFrames);
            }
        }
        return 0;
    }

    /**
     * The warmth claims on each host of the group: the two strongest credits a waiting candidate of
     * the group would receive there, and the layer of the strongest. A placement by another layer
     * wipes that warmth, and the scan charges the strongest claim of a layer other than the one
     * placing as the price of the host, symmetric to the credit (see pickHost).
     *
     * Bound: O(W) over the hosts' running layers and warmth entries.
     */
    void bindWarmClaims(List<BookableHost> hosts, List<LayerCandidate> candidates) {
        Map<String, LayerCandidate> waiting = new HashMap<>();
        if (localityEnabled) {
            for (LayerCandidate c : candidates) {
                if (c.waitingFrameCount > 0)
                    waiting.put(c.layerId, c);
            }
        }
        for (BookableHost h : hosts) {
            h.claimLayer = null;
            h.claim = 0;
            h.claimNext = 0;
            if (waiting.isEmpty())
                continue;
            claimFrom(h, h.layersRunning, waiting);
            claimFrom(h, h.warmth == null ? null : h.warmth.keySet(), waiting);
        }
    }

    private void claimFrom(BookableHost h, Set<String> layers,
            Map<String, LayerCandidate> waiting) {
        if (layers == null)
            return;
        for (String layerId : layers) {
            LayerCandidate c = waiting.get(layerId);
            if (c == null)
                continue;
            double v = warmCredit(h, c);
            if (v > h.claim) {
                if (!layerId.equals(h.claimLayer))
                    h.claimNext = h.claim;
                h.claimLayer = layerId;
                h.claim = v;
            } else if (v > h.claimNext && !layerId.equals(h.claimLayer)) {
                h.claimNext = v;
            }
        }
    }

    /** The price of h for c: the strongest warmth claim on h of a waiting layer other than c's. */
    static double otherClaim(BookableHost h, LayerCandidate c) {
        return c.layerId.equals(h.claimLayer) ? h.claimNext : h.claim;
    }

    /**
     * Most frames of candidate c one host may hold when the per-host layer cap is on: the
     * configured fraction of the host's cores, never below 8 frames so small hosts still anchor a
     * cache-warm batch. Uncapped when the knob is 0 or the layer reserves no cores.
     */
    private int layerHostCap(BookableHost h, LayerCandidate c) {
        if (layerHostMaxFrac <= 0 || c.layerCoresMin <= 0)
            return Integer.MAX_VALUE;
        int byFrac = (int) ((layerHostMaxFrac * h.coresTotal) / c.layerCoresMin);
        return Math.max(8, byFrac);
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
     * clause (os = ANY of the host's comma-separated list, facility bind).
     */
    // spotless:off
    private static final String EXPLAIN_GROUP_EXCLUSIONS =
            "SELECT "
            + "  j.str_name AS job_name, "
            + "  l.str_name AS layer_name, "
            + "  l.str_tags, "
            + "  jr.int_priority, "
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
            // No limit column: limits no longer exclude at query level; the
            // in-memory gate names them in the why-not trace instead.
            + "  (COALESCE(fr.int_max_cores, -1) = -1 "
            + "   OR (SELECT COALESCE(SUM(ls3.int_running_count * l3.int_cores_min), 0) "
            + "       FROM job j3 JOIN layer l3 ON l3.pk_job = j3.pk_job "
            + "       JOIN layer_stat ls3 ON ls3.pk_layer = l3.pk_layer "
            + "       WHERE j3.pk_folder = j.pk_folder AND j3.str_state = 'PENDING') "
            + "      + l.int_cores_min <= fr.int_max_cores)           AS folder_ok, "
            + "  (? OR sh.b_scheduler_managed = true)                 AS managed_ok "
            + "FROM layer l "
            + "JOIN job j            ON j.pk_job = l.pk_job "
            + "JOIN job_resource jr  ON jr.pk_job = j.pk_job "
            + "JOIN show sh          ON sh.pk_show = j.pk_show "
            + "LEFT JOIN subscription sub ON sub.pk_show = j.pk_show AND sub.pk_alloc = ? "
            + "LEFT JOIN layer_stat ls    ON ls.pk_layer = l.pk_layer "
            + "LEFT JOIN folder_resource fr ON fr.pk_folder = j.pk_folder "
            + "WHERE j.str_state = 'PENDING' AND j.b_paused = false "
            + "ORDER BY jr.int_priority DESC "
            + "LIMIT "
            + EXPLAIN_LIMIT;
    // spotless:on

    /** Log the explain rows for a group that produced no candidates. DEBUG-gated by the caller. */
    private void explainGroupExclusions(HostSpecKey spec, int maxCoresTotalInGroup) {
        getJdbcTemplate().query(EXPLAIN_GROUP_EXCLUSIONS, rs -> {
            logger.debug("Maestro explain " + spec + ": job=" + rs.getString("job_name") + " layer="
                    + rs.getString("layer_name") + " prio=" + rs.getInt("int_priority") + " tags='"
                    + rs.getString("str_tags") + "' tagOk=" + rs.getBoolean("tag_ok") + " osOk="
                    + rs.getBoolean("os_ok") + " facOk=" + rs.getBoolean("fac_ok") + " threadOk="
                    + rs.getBoolean("thread_ok") + " hasSub=" + rs.getBoolean("has_sub")
                    + " underBurst=" + rs.getBoolean("under_burst") + " underJobCap="
                    + rs.getBoolean("under_job_cap") + " fitsCores=" + rs.getBoolean("fits_cores")
                    + " hasWaiting=" + rs.getBoolean("has_waiting") + " folderOk="
                    + rs.getBoolean("folder_ok") + " managedOk=" + rs.getBoolean("managed_ok"));
        }, spec.tagsNormalized, spec.os, spec.pkFacility, spec.allThreadMode ? 1 : 0,
                maxCoresTotalInGroup, MaestroMode.facility(env), spec.pkAlloc);
    }

    /**
     * What Maestro may book against one gating limit this tick.
     *
     * For a FRAME limit only {@link #usable} matters: frames still bookable right now. For a HOST
     * limit the cap counts distinct machines, so Maestro needs the holder set ({@link #seats}:
     * hosts already holding the limit, external holders included) and {@link #seatCap}, the most
     * machines it may let hold it.
     */
    static final class LimitBudget {
        final String id;
        final String name;
        final boolean hostBased;
        final int usable;
        final int seatCap;
        final Set<String> seats;

        LimitBudget(String id, String name, boolean hostBased, int usable, int seatCap,
                Set<String> seats) {
            this.id = id;
            this.name = name;
            this.hostBased = hostBased;
            this.usable = usable;
            this.seatCap = seatCap;
            this.seats = seats;
        }
    }

    // Per-limit budget rows for a tick: every limit the legacy dispatcher's gate would apply
    // (ENFORCED and, when externally reported, fresh), with its thresholds and merged usage.
    // Reuses the gate's own CTE so the two dispatchers count identically.
    private static final String SELECT_LIMIT_BUDGETS = DispatchQuery.LIMIT_USAGE_CTE
            + "SELECT lim.pk_limit_record, lr.str_name, lim.str_type, lim.int_soft_value, "
            + "lim.int_max_value, lim.usage_val "
            + "FROM lim JOIN limit_record lr ON lr.pk_limit_record = lim.pk_limit_record";

    // Hosts holding a HOST-type limit: the license server's reported holders union every host of
    // ours running a frame of a bound layer (the same generous test as DispatchQuery.hostHolds,
    // precomputed once per tick instead of per candidate row).
    private static final String SELECT_LIMIT_HOLDERS =
            "SELECT hld.pk_limit_record AS id, hld.str_host_name AS host " + "FROM limit_host hld "
                    + "JOIN limit_record lr ON lr.pk_limit_record = hld.pk_limit_record "
                    + "WHERE lr.str_type = 'HOST' " + "UNION "
                    + "SELECT ll.pk_limit_record, SPLIT_PART(LOWER(h.str_name), '.', 1) "
                    + "FROM proc p " + "JOIN host h ON h.pk_host = p.pk_host "
                    + "JOIN layer_limit ll ON ll.pk_layer = p.pk_layer "
                    + "JOIN limit_record lr2 ON lr2.pk_limit_record = ll.pk_limit_record "
                    + "WHERE lr2.str_type = 'HOST'";

    /**
     * SELECT_LIMIT_BUDGETS with the limit gate's placeholder tokens resolved. Lazy because the
     * MATERIALIZED keyword depends on the server version, which needs a live connection.
     */
    private volatile String limitBudgetsSql;

    private String limitBudgetsSql() {
        String sql = limitBudgetsSql;
        if (sql == null) {
            Integer version =
                    getJdbcTemplate().queryForObject("SHOW server_version_num", Integer.class);
            sql = SELECT_LIMIT_BUDGETS
                    .replace(DispatchQuery.SETTLE_WINDOW_TOKEN,
                            String.valueOf(env.getProperty("limit.settle_window_seconds",
                                    Integer.class, 120)))
                    .replace(DispatchQuery.CTE_MATERIALIZED_TOKEN,
                            (version != null && version >= 120000) ? "MATERIALIZED" : "");
            limitBudgetsSql = sql;
        }
        return sql;
    }

    /**
     * Record which of these candidates are bound to limits, and load this tick's budgets on first
     * need.
     *
     * The bound limit ids already arrived on the candidate rows, so recording them costs nothing
     * but a walk of the list. Budgets are the part that touches the database, so they are read once
     * per tick, the first time any candidate is bound: one query for every gating limit's merged
     * usage (the legacy gate's own counting rule) and, when HOST limits exist, one for their holder
     * sets. Later groups reuse them, which also keeps the numbers consistent across groups within a
     * tick. All the maps are tick-scoped and Maestro-thread only.
     *
     * Mirroring {@code DispatchQuery.limitFilter}, a limit that is ADVISORY or DISABLED, or whose
     * external report has gone stale past its TTL, gets no budget entry at all: candidates book
     * through it exactly as they would under the legacy dispatcher.
     */
    /* package for tests */ void resolveLimitBudgets(List<LayerCandidate> candidates,
            Map<String, List<String>> layerLimits, Map<String, LimitBudget> limitBudgets) {
        boolean bound = false;
        for (LayerCandidate c : candidates) {
            if (c.limitIds == null)
                continue;
            layerLimits.put(c.layerId, c.limitIds);
            bound = true;
        }
        if (!bound || limitBudgetsResolved)
            return;
        limitBudgetsResolved = true;

        List<Object[]> rows = getJdbcTemplate().query(limitBudgetsSql(),
                (rs, i) -> new Object[] {rs.getString("pk_limit_record"), rs.getString("str_name"),
                        rs.getString("str_type"), rs.getInt("int_soft_value"),
                        rs.getInt("int_max_value"), rs.getInt("usage_val")});
        Map<String, Set<String>> holders = null;
        for (Object[] row : rows) {
            String id = (String) row[0];
            String name = (String) row[1];
            boolean hostBased = "HOST".equals(row[2]);
            int soft = (Integer) row[3];
            int max = (Integer) row[4];
            int usage = (Integer) row[5];
            if (hostBased) {
                if (holders == null)
                    holders = readLimitHolders();
                Set<String> seats = holders.getOrDefault(id, new HashSet<>());
                // Above the threshold (soft when set, max otherwise) only holding
                // machines may book; below it, threshold - usage new machines may
                // light up. Expressed as a seat cap over the live seat set so the
                // spend during the tick is what closes the gap.
                int threshold = soft >= 0 ? soft : max;
                int seatCap = seats.size() + Math.max(0, threshold - usage);
                limitBudgets.put(id, new LimitBudget(id, name, true, 0, seatCap, seats));
            } else {
                limitBudgets.put(id, new LimitBudget(id, name, false, Math.max(0, max - usage), 0,
                        Collections.emptySet()));
            }
        }
    }

    /** Holder host sets per HOST-type limit, keyed by limit id. Sets are tick-mutable. */
    private Map<String, Set<String>> readLimitHolders() {
        Map<String, Set<String>> holders = new HashMap<>();
        getJdbcTemplate().query(SELECT_LIMIT_HOLDERS, rs -> {
            holders.computeIfAbsent(rs.getString("id"), k -> new HashSet<>())
                    .add(rs.getString("host"));
        });
        return holders;
    }

    /**
     * May this host take a frame of a layer bound to HOST-type limits?
     *
     * Yes when, for every such limit, the host either already holds it (extra frames there are
     * free, they share the one checkout) or the limit still has a seat to give out. The seat set
     * includes holders the license server reports outside the cue, so an artist's workstation
     * occupies a seat here just as a render node does.
     */
    /* package for tests */ static boolean limitSeatsAllow(List<LimitBudget> pools,
            Map<String, Set<String>> limitSeats, BookableHost h) {
        String hostName = shortHostName(h.hostName);
        for (LimitBudget b : pools) {
            Set<String> seats = limitSeats.get(b.id);
            if (seats.contains(hostName))
                continue;
            if (seats.size() >= b.seatCap)
                return false;
        }
        return true;
    }

    /** The normalized seat key: short hostname, lowercased, as limit_host stores it. */
    static String shortHostName(String hostName) {
        if (hostName == null)
            return "";
        String lower = hostName.toLowerCase();
        int dot = lower.indexOf('.');
        return dot < 0 ? lower : lower.substring(0, dot);
    }

    /** {@code "a,b"} to {@code [a, b]}, blanks dropped. */
    static List<String> splitIds(String csv) {
        List<String> out = new ArrayList<>(2);
        if (csv == null)
            return out;
        for (String part : csv.split(",")) {
            String s = part.trim();
            if (!s.isEmpty() && !out.contains(s))
                out.add(s);
        }
        return out;
    }

    /* package for tests */ List<LayerCandidate> readLayerCandidatesForGroup(HostSpecKey spec,
            int maxIdleInGroup) {
        int limit = env.getProperty("maestro.layer_candidates_per_group_max", Integer.class, 2000);
        List<LayerCandidate> rows =
                getJdbcTemplate().query(SELECT_CANDIDATES_FOR_GROUP, CANDIDATE_MAPPER, spec.pkAlloc,
                        spec.os, spec.pkFacility, spec.allThreadMode ? 1 : 0, spec.tagsNormalized,
                        maxIdleInGroup, MaestroMode.facility(env), limit);
        // Defensive dedupe: a duplicated row would clone its candidate (double
        // placement per tick). First row per layer wins.
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

    /**
     * Fold the farm-health ledger into this tick's per-spec-group and per-hardware-shape
     * aggregates. The group label is the human half of the spec key (normalized tags plus os); the
     * shape label is cores and memory, e.g. 128c/112g. Hosts absent from the ledger (no report yet)
     * contribute nothing.
     */
    private static void aggregateFarmHealth(Map<HostSpecKey, List<BookableHost>> groups,
            Map<String, FarmHealth.HostHealth> health, MaestroMetrics.TickStats stats) {
        for (Map.Entry<HostSpecKey, List<BookableHost>> e : groups.entrySet()) {
            HostSpecKey k = e.getKey();
            String groupLabel = k.tagsNormalized + (k.hasGpu ? " gpu" : "") + "|" + k.os;
            for (BookableHost h : e.getValue()) {
                FarmHealth.HostHealth hh = health.get(h.hostName.toLowerCase());
                if (hh == null)
                    continue;
                String shape = (h.coresTotal / 100) + "c/"
                        + Math.round(h.memTotal / (1024.0 * 1024.0)) + "g";
                stats.healthByGroup.computeIfAbsent(groupLabel, x -> new MaestroMetrics.HealthAgg())
                        .add(hh.swapTotalKb, hh.swapFreeKb, hh.sysTimePct);
                stats.healthByHwtype.computeIfAbsent(shape, x -> new MaestroMetrics.HealthAgg())
                        .add(hh.swapTotalKb, hh.swapFreeKb, hh.sysTimePct);
            }
        }
    }

    static Map<HostSpecKey, List<BookableHost>> groupByHostSpec(List<BookableHost> hosts) {
        Map<HostSpecKey, List<BookableHost>> groups = new LinkedHashMap<>();
        for (BookableHost h : hosts)
            groups.computeIfAbsent(hostSpecKey(h), x -> new ArrayList<>()).add(h);
        return groups;
    }

    /**
     * A host's spec: what kind of machine it is, never which one. Cuebot auto-adds each host's own
     * name as a tag; the key drops it, otherwise every host falls into a group of one and the
     * per-group candidate query runs once per host instead of once per real spec. A name in a
     * layer's tags is a pin instead (see {@link #readPinnedCandidates}). GPU presence is a static
     * hardware property, so it uses totals, not idle: a fully-booked GPU host must still group as a
     * GPU host so its candidate query filters for GPU layers and the GPU-weighted score protects
     * it.
     */
    static HostSpecKey hostSpecKey(BookableHost h) {
        return new HostSpecKey(h.pkAlloc, h.pkFacility, normalizeTags(h.tagsRaw, h.hostName), h.os,
                h.gpusTotal > 0 || h.gpuMemTotal > 0, h.threadMode == ThreadMode.ALL_VALUE);
    }

    /**
     * Pins: a tag that names a host is a pin, not a spec. A layer pinned to hosts is a candidate
     * only on the hosts it names and obeys every other rule there (its show's subscription in that
     * host's allocation, facility, OS, thread mode, fit, caps, reservations, seats and the soft
     * per-host cap), and it never widens to the host's group. The legacy match is an OR over the
     * layer's tags, so a layer tagged with a spec and a name runs anywhere the spec allows plus on
     * the named host; that layer is a group candidate as well and the group's copy wins there.
     *
     * One read per tick returns a row per (layer, named host) for the waiting layers whose tags are
     * not all spec tags, with the host resolved and checked in SQL exactly as the group query
     * checks a group (see SELECT_PINNED_CANDIDATES). The rows become one candidate per (layer,
     * host-spec group), each carrying its pinned hosts, filed under the groups those hosts belong
     * to; planGroup adds them to the group's candidates. A layer none of whose names resolves, and
     * that has no spec tag either, waits with the reason "no host" so a stale machine list is
     * visible in the waitlist instead of silent.
     *
     * Bound: one query over the waiting layers with a non-spec tag, then O(rows).
     */
    private void readPinnedCandidates(Map<HostSpecKey, List<BookableHost>> groups,
            Map<String, BookableHost> hostById) {
        Set<String> specTags = new HashSet<>();
        for (HostSpecKey k : groups.keySet())
            for (String t : k.tagsNormalized.split("\\s+"))
                if (!t.isEmpty())
                    specTags.add(t.toLowerCase());
        if (specTags.isEmpty())
            return;
        int limit = env.getProperty("maestro.layer_candidates_per_group_max", Integer.class, 2000);
        List<PinRow> rows;
        try {
            rows = getJdbcTemplate().query(SELECT_PINNED_CANDIDATES, PINNED_MAPPER,
                    ThreadMode.ALL_VALUE, String.join(",", specTags), MaestroMode.facility(env),
                    limit);
        } catch (RuntimeException e) {
            logger.warn("Maestro: pinned candidate query failed; no pinned layer is planned this"
                    + " tick: " + e.getMessage());
            return;
        }
        pinnedByGroup
                .putAll(attachPins(rows, hostById, specTags, waitReasonByLayer, waitFramesByLayer));
    }

    /**
     * Turn the pinned rows into one candidate per (layer, host-spec group), each holding the pinned
     * hosts of that group. A row whose host is not in this tick's snapshot resolves nothing; a
     * layer with no resolved host and no spec tag is filed under the waitlist reason "no host" with
     * its waiting frames. Bound: O(rows).
     */
    static Map<HostSpecKey, List<LayerCandidate>> attachPins(List<PinRow> rows,
            Map<String, BookableHost> hostById, Set<String> specTags,
            Map<String, String> waitReason, Map<String, Integer> waitFrames) {
        Map<HostSpecKey, List<LayerCandidate>> out = new HashMap<>();
        Map<HostSpecKey, Map<String, LayerCandidate>> byLayer = new HashMap<>();
        Set<String> resolved = new HashSet<>();
        List<PinRow> unresolved = new ArrayList<>();
        for (PinRow r : rows) {
            BookableHost h = r.hostId == null ? null : hostById.get(r.hostId);
            if (h == null) {
                unresolved.add(r);
                continue;
            }
            HostSpecKey k = hostSpecKey(h);
            Map<String, LayerCandidate> inGroup = byLayer.computeIfAbsent(k, x -> new HashMap<>());
            LayerCandidate c = inGroup.get(r.row.layerId);
            if (c == null) {
                c = r.row;
                c.pinnedHosts = new ArrayList<>();
                c.pinnedIds = new HashSet<>();
                inGroup.put(c.layerId, c);
                out.computeIfAbsent(k, x -> new ArrayList<>()).add(c);
            }
            c.pinnedHosts.add(h);
            c.pinnedIds.add(h.hostId);
            resolved.add(c.layerId);
        }
        for (PinRow r : unresolved) {
            if (resolved.contains(r.row.layerId) || namesSpecTag(r.tags, specTags))
                continue;
            waitReason.put(r.row.layerId, "no host");
            waitFrames.put(r.row.layerId, r.row.waitingFrameCount);
        }
        return out;
    }

    /** Whether any token of a layer's tag regex is a host-spec tag (case-insensitive). */
    static boolean namesSpecTag(String layerTags, Set<String> specTags) {
        if (layerTags == null)
            return false;
        for (String t : layerTags.replace(" ", "").split("\\|"))
            if (specTags.contains(t.toLowerCase()))
                return true;
        return false;
    }

    /**
     * Add a group's pinned candidates to its candidate list, skipping a layer the group query
     * already returned (a layer tagged with a spec and a name), and cut each one's visit list to
     * its pinned hosts that are in the group's idle subset: those are the hosts the class index
     * holds, so a pinned placement moves a host the index knows. Bound: O(candidates + pins).
     */
    static void addPinned(List<LayerCandidate> candidates, List<LayerCandidate> pinned,
            List<BookableHost> idleGroup) {
        if (pinned == null || pinned.isEmpty())
            return;
        Set<String> present = new HashSet<>();
        for (LayerCandidate c : candidates)
            present.add(c.layerId);
        Set<BookableHost> idle = new HashSet<>(idleGroup);
        for (LayerCandidate c : pinned) {
            if (!present.add(c.layerId))
                continue;
            c.pinnedIdle = new ArrayList<>();
            for (BookableHost h : c.pinnedHosts)
                if (idle.contains(h))
                    c.pinnedIdle.add(h);
            candidates.add(c);
        }
    }

    /** A pinned candidate wants only its own hosts; an unpinned one wants any. */
    static boolean pinsAllow(LayerCandidate o, BookableHost h) {
        return o.pinnedIds == null || o.pinnedIds.contains(h.hostId);
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
     * Layer-driven placement with persistent reservations, one placement slot at a time. Every slot
     * goes to a candidate drawn by priority-weighted lottery among the candidates that can still
     * place (placeOnce: the host with the lowest {@link #placementScore} among those that fit and
     * pass the reservation, seat, per-host-plan and soft-cap gates), until none can. So a lone
     * layer takes every fitting host in one tick, contending layers share the tick's capacity in
     * proportion to their priority however much capacity there is, and priority stays a rate, never
     * a strict order. Every plan gets a disjoint frame slice from submitCommit, so parallel
     * per-host plan reads cannot collide, and a layer's waiting count is tick-wide (frames planned
     * for it in an earlier group are subtracted on entry), so the groups share one backlog. A tick
     * therefore costs what the idle capacity it can fill costs, and commitInChunks lands that in
     * bounded transactions.
     *
     * After the slots, once per candidate: the why-not trace, the waitlist tally, and the
     * reservation reconcile (c's reservation count should equal c.waitingFrameCount, decremented as
     * we dispatched; drop excess, claim more if short), all read against the end-of-tick gate.
     *
     * Layer ids are recorded in {@code seenLayerIds} so the end-of-tick sweep can drop reservations
     * for layers that left the dispatchable set.
     *
     * Bound: O(C x D + I log I) to bind; per slot O(shows + log C) to draw and O(classes + special
     * hosts) to place; the epilogue O(I log I + U log I).
     */
    private int dispatchGroupWithScoring(List<BookableHost> hosts, List<BookableHost> fullHosts,
            List<LayerCandidate> candidates, Set<String> seenLayerIds, String groupAllocId,
            List<ReservationRequest> reservationReqs, Map<String, Set<String>> limitSeats) {
        int dispatched = 0;
        // Largest host in this group, for the reservation width gate below: a
        // layer may reserve only if its per-frame cores are a big enough fraction
        // of this. Uses fullHosts (idle + busy) so the bar reflects the class's
        // real top-end capacity, not just what happens to be idle this tick.
        int maxGroupHostCores = 0;
        for (BookableHost h : fullHosts) {
            if (h.coresTotal > maxGroupHostCores)
                maxGroupHostCores = h.coresTotal;
        }
        // Prologue, once per candidate: register with the sweep and take the
        // tick-wide remainder. A layer planned in an earlier host-spec group
        // this tick keeps only its remaining frames here, so the groups share
        // one backlog and every plan's slice stays disjoint.
        for (LayerCandidate c : candidates) {
            seenLayerIds.add(c.layerId);
            c.waitingFrameCount -= plannedFramesByLayer.getOrDefault(c.layerId, 0);
            c.placedThisTick = false;
            c.showKey = subKey(c.showId, groupAllocId);
            bindCells(c);
        }
        reachNeeds = reachNeedsOf(candidates);
        bindWaiting(candidates);
        bindWarmClaims(hosts, candidates);
        classes = new HostClasses(hosts);

        // Placement slots: every slot goes first to the show with the lowest
        // tier on this allocation (cores in use over subscription size, read
        // tick-wide so this tick's placements count), which is the legacy
        // dispatcher's show walk applied per placement: a show under its size
        // beats a show over it, shows under size share in proportion to size,
        // and burst stays the ceiling. Inside that show the slot goes to a
        // candidate drawn with probability proportional to its job priority
        // among the candidates that can still place, until none can: the
        // candidate query's own draw (power(random(), 1/priority)) applied per
        // placement instead of once per tick, so a tick's capacity splits by
        // priority however much of it there is. A candidate leaves the draw
        // when it places nothing (capped, out of probe headroom, no host left)
        // or runs out of frames, and one no idle host fits never enters it
        // (see fitting); a show whose candidates all left yields the slot to
        // the next tier in the same tick.
        SlotDraw draw = new SlotDraw(fitting(candidates, new GroupViews.IdleView(hosts)));
        while (!draw.isEmpty()) {
            LayerCandidate c = draw.next(ThreadLocalRandom.current().nextDouble());
            int got = placeOnce(c, hosts, candidates, limitSeats);
            if (got > 0)
                dispatched += got;
            if (got <= 0 || c.waitingFrameCount <= 0)
                draw.remove(c);
        }

        // Epilogue, once per candidate, against the end-of-tick gate and one sorted view of the
        // idle hosts, built once here: the state is frozen from this point on.
        GroupViews.IdleView idle = new GroupViews.IdleView(hosts);
        for (LayerCandidate c : candidates) {
            if (c.waitingFrameCount <= 0 && !c.placedThisTick)
                continue;
            CandidateGate g = gate(c, limitSeats);
            if (c.limitIds != null && g.limitUsable <= 0)
                tickLicenseHeld++;
            boolean placed = c.placedThisTick;
            boolean capped = g.capped;
            int folderInUse = g.folderInUse;
            int limitUsable = g.limitUsable;
            List<LimitBudget> limitSeatPools = g.limitSeatPools;

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
                else if (c.folderMax >= 0 && folderInUse + c.layerCoresMin > c.folderMax)
                    why = "folderCap(" + folderInUse + "/" + c.folderMax + ")";
                else if (limitUsable <= 0)
                    why = "limitFull(" + c.limitIds + ")";
                else if (limitSeatPools != null)
                    why = "noFittingIdleHost(seat-gated limits present)";
                else
                    why = "noFittingIdleHost";
                logger.debug("Maestro unplaced: layer=" + c.layerId + " prio=" + c.priority
                        + " cores=" + c.layerCoresMin + " memKb=" + c.layerMemMin + " waiting="
                        + c.waitingFrameCount + " why=" + why);
            }

            // Waitlist tally: every candidate that leaves the loop with waiting frames lands in
            // exactly one bucket. A placed layer's remaining backlog is flowing; an unplaced one
            // is bucketed by the same precedence the why-not trace uses. Last outcome wins when a
            // layer appears in several groups; a layer that books its whole backlog away drops
            // off the waitlist.
            if (c.waitingFrameCount > 0) {
                waitReasonByLayer.put(c.layerId, placed ? "flowing"
                        : waitlistReason(c,
                                c.pinnedIdle != null ? new GroupViews.IdleView(c.pinnedIdle) : idle,
                                folderInUse, limitUsable, limitSeatPools, limitSeats));
                waitFramesByLayer.put(c.layerId, c.waitingFrameCount);
            } else if (placed) {
                waitReasonByLayer.remove(c.layerId);
                waitFramesByLayer.remove(c.layerId);
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
                    reservationReqs.add(new ReservationRequest(c,
                            c.pinnedHosts != null ? c.pinnedHosts : fullHosts));
                }
                // Trace reservation decisions for every candidate so we can
                // see why wide-job layers never accumulate enough debt.
                if (logger.isDebugEnabled()) {
                    logger.debug("Maestro resv-candidate: layer=" + c.layerId + " coresMin="
                            + c.layerCoresMin + " waiting=" + c.waitingFrameCount + " capped="
                            + capped + " placed=" + placed + " blocked=" + blocked + " debt=" + debt
                            + "ms threshold=" + reservationBlockMs + "ms" + " wide=" + wideEnough
                            + " (coresMin=" + c.layerCoresMin + " gate="
                            + (RESERVATION_MIN_HOST_FRACTION * maxGroupHostCores) + ")" + " holds="
                            + holdsResv + " qualifies=" + (holdsResv || qualified));
                }
            }
        }

        return dispatched;
    }

    /** The draw weight of a candidate: its job priority, floored at 1 like the query's GREATEST. */
    static long lotteryWeight(LayerCandidate c) {
        return Math.max(1, c.priority);
    }

    /**
     * The tier of a candidate's show on this allocation: the legacy dispatcher's subscription tier
     * (the database's tier() function) read tick-wide, once per show per slot by SlotDraw. Cores in
     * use over subscription size; a show running nothing sorts below every other, at minus its
     * size; a show with no size has no guarantee and sorts by its cores above every show that has
     * one. Lower runs first.
     */
    static double showTier(LayerCandidate c) {
        int cores = c.showCell.used;
        if (c.showSizeCores == 0)
            return cores / 100.0 + 1;
        if (cores == 0)
            return -c.showSizeCores;
        return (double) cores / c.showSizeCores;
    }

    /**
     * Bind a candidate to its tick-wide cap counters: one cell per job, subscription (show and
     * allocation), folder and bound limit, plus the budget of each bound limit (null where the
     * limit does not gate, see resolveLimitBudgets). A cell is seeded from the candidate's row the
     * first time its key is seen in the tick and shared by every later candidate of that key, in
     * this group or a later one, so every cap read is a field read and a spend on one candidate is
     * seen by all of them without a lookup. Null where the candidate has no folder cap or no limit.
     */
    void bindCells(LayerCandidate c) {
        c.jobCell = cell(jobCells, c.jobId, c.jobCoresInUse);
        c.showCell = cell(showCells, c.showKey, c.showCoresInUse);
        c.folderCell = c.folderMax < 0 ? null : cell(folderCells, c.folderId, c.folderRunning);
        if (c.limitIds != null) {
            c.limitCells = new Cell[c.limitIds.size()];
            c.limitBound = new LimitBudget[c.limitIds.size()];
            for (int i = 0; i < c.limitCells.length; i++) {
                String limId = c.limitIds.get(i);
                c.limitCells[i] = cell(limitCells, limId, 0);
                c.limitBound[i] = limitBudgets.get(limId);
            }
        }
    }

    private static Cell cell(Map<String, Cell> cells, String key, int seed) {
        Cell x = cells.get(key);
        if (x == null) {
            x = new Cell();
            x.used = seed;
            cells.put(key, x);
        }
        return x;
    }

    /** A tick-wide cap counter shared by every candidate of one key. */
    static final class Cell {
        int used;
    }

    /** Tick-wide cap state of one candidate, read fresh at every slot and once in the epilogue. */
    static final class CandidateGate {
        int folderInUse;
        int limitUsable = Integer.MAX_VALUE;
        List<LimitBudget> limitSeatPools;
        boolean capped;
    }

    /**
     * Sync one candidate's job and show usage with the tick-wide totals and evaluate every cap that
     * can hold it: job max cores, show burst (keyed on the subscription, not the show: a show with
     * two allocations has two bursts), the folder core ceiling, and the limits the layer is bound
     * to (FRAME limits allow the minimum of their remaining budgets, HOST limits are gated per host
     * in pickHost; a limit with no budget entry does not gate). Every counter is the candidate's
     * cell, bound in the group prologue (bindCells), so placements made earlier this tick, here or
     * in another group, count against this candidate. Idempotent: placeOnce calls it before every
     * attempt, the epilogue once more.
     *
     * Bound: O(1), plus one step per limit of the layer.
     */
    private CandidateGate gate(LayerCandidate c, Map<String, Set<String>> limitSeats) {
        CandidateGate g = new CandidateGate();
        c.jobCoresInUse = c.jobCell.used;
        c.showCoresInUse = c.showCell.used;
        if (c.limitBound != null) {
            for (int i = 0; i < c.limitBound.length; i++) {
                LimitBudget b = c.limitBound[i];
                if (b == null)
                    continue;
                if (b.hostBased) {
                    if (g.limitSeatPools == null)
                        g.limitSeatPools = new ArrayList<>(2);
                    g.limitSeatPools.add(b);
                    limitSeats.putIfAbsent(b.id, b.seats);
                } else {
                    int remaining = b.usable - c.limitCells[i].used;
                    if (remaining < g.limitUsable)
                        g.limitUsable = remaining;
                }
            }
        }
        g.folderInUse = c.folderCell == null ? 0 : c.folderCell.used;
        // A capped layer (job/show cap, folder ceiling, spent limit budget) must
        // not dispatch but must still reconcile, dropping reservations it can no
        // longer use so other work can take those hosts.
        g.capped = c.jobCoresInUse + c.layerCoresMin > c.jobMaxCores
                || c.showCoresInUse + c.layerCoresMin > c.showBurstCores
                || (c.folderMax >= 0 && g.folderInUse + c.layerCoresMin > c.folderMax)
                || g.limitUsable <= 0;
        return g;
    }

    /**
     * One placement attempt for candidate c: the gate, the probe headroom, the host scan (see
     * pickHost, over one host per class of equal state and c's special hosts), the frame estimate,
     * then the bookkeeping that makes the tick's later candidates see the spend, and submitCommit.
     * Returns the frames planned, 0 when the candidate is capped, out of probe headroom, or has no
     * host left this tick.
     *
     * Bound: O(classes + special hosts of c) for the scan, O(log I) to move the placed host, O(1)
     * for the rest.
     */
    private int placeOnce(LayerCandidate c, List<BookableHost> hosts,
            List<LayerCandidate> candidates, Map<String, Set<String>> limitSeats) {
        CandidateGate g = gate(c, limitSeats);
        if (g.capped)
            return 0;
        int limitUsable = g.limitUsable;
        List<LimitBudget> limitSeatPools = g.limitSeatPools;
        // Probe gate: a 1-core threadable layer with no rss evidence ("let the
        // system decide") may hold only PROBE_FRAMES frames farm-wide, so a
        // brand-new mis-sized layer cannot blast the farm before the reports
        // have seen what it really uses.
        int probeHeadroom = Integer.MAX_VALUE;
        if (!c.rssProven) {
            probeHeadroom = PROBE_FRAMES - layerRunningFrames.getOrDefault(c.layerId, 0)
                    - layerProbeUsed.getOrDefault(c.layerId, 0);
            if (probeHeadroom <= 0)
                return 0;
        }
        List<BookableHost> visit = c.pinnedIdle != null ? c.pinnedIdle
                : classes.candidates(c, limitSeatPools, limitSeats);
        Pick p = pickHost(c, visit, limitSeatPools, limitSeats);
        BookableHost best = p.best;
        int bestStrandFree = p.bestStrandFree;
        boolean overCap = false;
        if (best == null && p.fallback != null) {
            // Soft cap: the only thing between this layer and an idle
            // machine was the cap. Give it the machine.
            best = p.fallback;
            bestStrandFree = p.fallbackStrandFree;
            overCap = true;
        }
        if (best == null)
            return 0; // no host can fit this layer

        // Estimate how many frames this commit will book. The
        // dispatcher books up to job_frame_dispatch_max per call,
        // bounded by the same fit checks placementScore uses.
        int estFrames =
                headroomFrames(c, best, overCap, probeHeadroom, limitUsable, bestStrandFree);
        if (estFrames <= 0)
            return 0;

        // The locality dial: classify the chosen host here, before this
        // commit moves any of the maps the bonus scored.
        lastTickStats.bookedFramesByLocality.merge(localityKind(best, c), (long) estFrames,
                Long::sum);

        int estCores = estFrames * c.layerCoresMin;
        long estMem = (long) estFrames * c.layerMemMin;
        int estGpus = estFrames * c.layerGpusMin;
        long estGpuMem = (long) estFrames * c.layerGpuMemMin;

        for (Dim d : DIMS)
            d.take(best, (long) estFrames * d.need(c));
        c.jobCell.used += estCores;
        c.showCell.used += estCores;
        c.jobCoresInUse = c.jobCell.used;
        c.showCoresInUse = c.showCell.used;
        c.waitingFrameCount -= estFrames;
        if (layerHostMaxFrac > 0)
            best.layerFrames.merge(c.layerId, estFrames, Integer::sum);
        if (!c.rssProven)
            layerProbeUsed.merge(c.layerId, estFrames, Integer::sum);
        if (c.folderCell != null)
            c.folderCell.used += estCores;
        // Spend the limits: a frame is a token in each FRAME limit, and
        // this host now holds a seat in each HOST one. Both are tick-wide
        // so every later candidate of the same limit, in any group, sees
        // the spend.
        if (c.limitBound != null) {
            boolean gated = false;
            for (int i = 0; i < c.limitBound.length; i++) {
                LimitBudget b = c.limitBound[i];
                if (b == null)
                    continue;
                gated = true;
                if (b.hostBased) {
                    Set<String> seats = limitSeats.get(b.id);
                    if (seats.add(shortHostName(best.hostName))) {
                        logger.info("Maestro limit: new seat " + seats.size() + "/" + b.seatCap
                                + " on host " + best.hostName + " for limit " + b.name);
                    }
                } else {
                    c.limitCells[i].used += estFrames;
                }
            }
            if (gated)
                tickLicenseBooked += estFrames;
        }

        // Count an EASY-backfill borrow for the stat line: this host
        // is reserved for someone else and only backfillAllows let us
        // in.
        if (!reservationAllows(best, c)) {
            tickBackfilled++;
            tickBackfilledCores += estCores;
        }

        // No seize-on-dispatch: reservations are firm (see reservationAllows), so a host
        // reached here is either its owner booking after the drain or an EASY-backfill
        // borrow. A borrow never takes ownership, so the reservation is left intact.
        submitCommit(best, c.layerId, estFrames);
        classes.move(best);
        c.placedThisTick = true;
        return estFrames;
    }

    /**
     * One slot's scan outcome: the best host, the soft cap's fallback, their strand-free frames.
     */
    static final class Pick {
        BookableHost best; // consumed by placeOnce()
        BookableHost fallback; // consumed by placeOnce()
        int bestStrandFree = Integer.MAX_VALUE; // consumed by placeOnce()
        int fallbackStrandFree = Integer.MAX_VALUE; // consumed by placeOnce()
        double bestScore = Double.POSITIVE_INFINITY; // consumed by pickHost()
    }

    /**
     * The host scan of one slot over the hosts to visit: every fitting host scored with
     * placementScore under the reservation, seat, per-host-plan and soft-cap gates. The best host
     * is the lowest score, the lowest index among equals; the fallback is the lowest-index host
     * held by the cap alone. Both read the host's index, not the visit order, so the pick is the
     * same whichever host stands for its class (see HostClasses).
     *
     * Bound: one gate and one score per host visited.
     */
    Pick pickHost(LayerCandidate c, List<BookableHost> visit, List<LimitBudget> limitSeatPools,
            Map<String, Set<String>> limitSeats) {
        Pick p = new Pick();
        for (BookableHost h : visit) {
            if (!fitsOnHost(c, h))
                continue;
            // A host is not given away while work that needs one of its idle
            // resources is waiting: the bundle that resource needs stays,
            // and the slice is cut to what lies beyond it.
            int strandFree = strandFreeFrames(h, c);
            if (strandFree <= 0)
                continue;
            // Per-host gate for HOST-type limits, keyed by host name (what
            // a license server reports): this host is eligible only if it
            // already holds every such limit, or the limit still has a
            // seat to give out.
            if (limitSeatPools != null && !limitSeatsAllow(limitSeatPools, limitSeats, h))
                continue;
            // A reserved host is off-limits unless EASY backfill can
            // borrow it without delaying the reservation's owner.
            if (!reservationAllows(h, c)) {
                if (!backfillAllows(h, c))
                    continue;
            }
            // Per-host layer cap: a host already holding its share of
            // this layer takes no more of it; the flood spills to the
            // next host instead of blanketing this one.
            // One plan per (host, layer) per tick; a pair already
            // planned takes its next slice next tick.
            if (plannedOn(h, c))
                continue;
            // SOFT per-host layer cap: prefer hosts under the cap, so
            // a flood spreads instead of blanketing one machine. But a
            // fitting host blocked ONLY by the cap is remembered: if
            // no host is under the cap, the cap yields rather than
            // stranding an idle machine, and only on a host no other
            // candidate could still use (othersWant). Unproven layers
            // never get the fallback (the probe gate is their brake).
            if (layerHostMaxFrac > 0 && layerFramesOn(h, c) >= layerHostCap(h, c)) {
                if (c.rssProven && (p.fallback == null || h.ix < p.fallback.ix)
                        && !othersWant(h, c)) {
                    p.fallback = h;
                    p.fallbackStrandFree = strandFree;
                }
                continue;
            }
            double score = placementScore(h, c, reachNeeds);
            // Locality: the credit for the host's own warmth for this layer, and the price of
            // the strongest warmth another waiting layer holds there, which this placement
            // would wipe. Symmetric, so a cold host of equal state beats a host warm for
            // someone else by exactly their credit, and the only fitting host is still taken.
            score += otherClaim(h, c) - warmCredit(h, c);
            // Seat bonus for HOST-type limits: packing onto an
            // already-seated machine consumes no new seat, which is the
            // whole point when seats are the scarce resource. Applied per
            // limit, so a host seated in all of the layer's limits outranks
            // one seated in only some. Stacks with the locality bonus.
            if (limitSeatPools != null) {
                String hName = shortHostName(h.hostName);
                for (LimitBudget b : limitSeatPools) {
                    if (limitSeats.get(b.id).contains(hName))
                        score -= limitSeatBonus;
                }
            }
            if (score < p.bestScore
                    || (score == p.bestScore && p.best != null && h.ix < p.best.ix)) {
                p.bestScore = score;
                p.best = h;
                p.bestStrandFree = strandFree;
            }
        }
        return p;
    }

    /** True if any host is currently reserved for this layer. O(1): one probe of the index. */
    boolean layerHoldsReservation(String layerId) {
        return hostsByLayer.containsKey(layerId);
    }

    /**
     * Reserve a host for a layer, or release it, keeping the index by layer in step with the map: a
     * layer holds a reservation exactly when its set in the index is non-empty. O(1) each.
     */
    void reserve(String hostId, Reservation r) {
        reservations.put(hostId, r);
        hostsByLayer.computeIfAbsent(r.layerId, k -> new LinkedHashSet<>()).add(hostId);
    }

    void release(String hostId) {
        Reservation r = reservations.remove(hostId);
        if (r == null)
            return;
        Set<String> mine = hostsByLayer.get(r.layerId);
        mine.remove(hostId);
        if (mine.isEmpty())
            hostsByLayer.remove(r.layerId);
    }

    /** The hosts reserved for a layer, in the order they were reserved. */
    List<String> hostsReservedFor(String layerId) {
        Set<String> mine = hostsByLayer.get(layerId);
        return mine == null ? new ArrayList<>() : new ArrayList<>(mine);
    }

    /** Whether host h has enough total capacity to run a frame of c when idle. */
    static boolean hostCanEverFit(LayerCandidate c, BookableHost h) {
        for (Dim d : DIMS) {
            if (d.total(h) < d.need(c))
                return false;
        }
        return true;
    }

    /** How many frames of c fit on a fully-idle host h (min over dimensions). */
    private static int framesThatFit(LayerCandidate c, BookableHost h) {
        long f = Long.MAX_VALUE;
        for (Dim d : DIMS) {
            if (d.need(c) > 0)
                f = Math.min(f, d.total(h) / d.need(c));
        }
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
     * Whether host h's reservation lets c book and own it. Only its owner may: a reservation is
     * firm, the host is held for the reserving layer until it drains and that layer runs there, so
     * no other layer seizes it, not even a higher-priority one. Higher-priority work is not
     * blocked, it reaches the reserved host's spare cores through EASY backfill (see
     * {@link #backfillAllows}), which borrows without taking ownership so the owner is never
     * delayed. Firm reservations are what let a low-priority but long-starved wide job actually run
     * once granted; the priority-first grant order and the max-fraction cap keep the reserved set
     * bounded and fair.
     */
    private boolean reservationAllows(BookableHost h, LayerCandidate c) {
        if (!reservationsEnabled)
            return true;
        Reservation r = h.reservation;
        return r == null || r.layerId.equals(c.layerId);
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
    private boolean backfillAllows(BookableHost h, LayerCandidate c) {
        if (!backfillEnabled)
            return false;
        Integer tReady = h.tReady;
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
     * frames-per-host, not one host per frame.
     *
     * The per-class cap (reservationMaxFraction of the hosts that can fit c) throttles fresh grants
     * only, never a host c already holds. A held host is mid-drain: new bookings are frozen on it
     * and its cores are trickling toward c, so releasing it the moment another layer reserves a
     * different fitting host resets that progress and the wide job never assembles its block (the
     * reservation thrash this avoids). Retaining it cannot deadlock the class, because a draining
     * host runs its owner and then frees up. So c sheds hosts only when its own demand falls
     * (frames dispatched or the layer capped), least-drained first via
     * {@link #releaseSurplusReservations}, and claims more, up to its remaining cap headroom, via
     * {@link #reservationTargets}.
     *
     * Bound: O(H log H) per request; the layer's own hosts come from the index.
     */
    private void reconcileReservationsForLayer(LayerCandidate c, List<BookableHost> hosts) {
        List<String> mine = hostsReservedFor(c.layerId);

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

        // Fitting hosts in this group and how many are already held by other layers, for the
        // per-class cap. The cap bounds fresh grants only (see the header); held hosts are kept.
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

        if (have > need) {
            releaseSurplusReservations(mine, hosts, need);
        } else if (have < need) {
            int headroom = Math.max(0, capTotal - reservedByOthers - have);
            int want = Math.min(need - have, headroom);
            for (BookableHost t : reservationTargets(c, hosts, want))
                reserve(t.hostId, new Reservation(c.layerId, c.priority, c.layerCoresMin));
        }
    }

    /**
     * Release this layer's reservations down to {@code keep} hosts, dropping the least-drained
     * first: a host with more idle cores is nearer to launching the owner, so it survives while the
     * barely-drained ones are shed. Called only when the layer's own demand has fallen below what
     * it holds, never to satisfy the per-class cap, so a mid-drain host is never yanked for the
     * cap.
     */
    private void releaseSurplusReservations(List<String> mine, List<BookableHost> hosts, int keep) {
        Map<String, Integer> idleByHost = new HashMap<>();
        for (BookableHost h : hosts)
            idleByHost.put(h.hostId, h.coresIdle);
        // Idle cores descending, host id ascending among equals: a total order, so the
        // choice does not depend on the order the hosts were reserved in.
        mine.sort((a, b) -> {
            int byIdle =
                    Integer.compare(idleByHost.getOrDefault(b, 0), idleByHost.getOrDefault(a, 0));
            return byIdle != 0 ? byIdle : a.compareTo(b);
        });
        for (String hostId : mine.subList(Math.min(keep, mine.size()), mine.size()))
            release(hostId);
    }

    /**
     * The {@code want} free hosts most likely to become available for c soonest: fewest running
     * procs first, among the hosts whose totals fit c. Firm reservations: the claim only ever
     * expands into a free host and never takes a held one, so a low-priority grant is not clawed
     * back; own hosts are already counted in 'have'.
     *
     * Bound: O(H log H), one pass and one stable sort, which picks what a repeated argmin picks.
     */
    List<BookableHost> reservationTargets(LayerCandidate c, List<BookableHost> hosts, int want) {
        List<BookableHost> free = new ArrayList<>();
        for (BookableHost h : hosts) {
            if (hostCanEverFit(c, h) && reservations.get(h.hostId) == null)
                free.add(h);
        }
        free.sort((a, b) -> Integer.compare(a.runningProcs, b.runningProcs));
        return free.subList(0, Math.min(want, free.size()));
    }

    /**
     * Placement score for a (host, layer) pair; lower is better. Callers must fitsOnHost first,
     * this assumes the layer fits.
     *
     * The score is E-PVM marginal cost (Amir et al. 2000): the weighted sum over the resource
     * dimensions of each dimension's convex cost rise from adding one frame (see deltaCost).
     * Because the terms are e^(used/total), an already-full dimension (idle cores behind saturated
     * memory) costs far more, and the utilization-fraction exponent keeps the score size-unbiased
     * so big hosts are not starved. We pick the host with the smallest score. See maestro.md for
     * the derivation and the farm-balancing properties.
     *
     * One-step lookahead: the cost adds just this frame, not an end-of-tick projection. The
     * dispatch loop decrements h.*Idle after each commit, so the next frame sees a steeper delta on
     * its own, with no computeMaxMore pile-up estimate needed here.
     */
    static double placementScore(BookableHost h, LayerCandidate c) {
        return placementScore(h, c, null);
    }

    /**
     * The same score with reach in place of raw idle: each dimension's cost rises by the units of
     * it this frame consumes or puts out of reach, so a CPU frame that eats the cores an idle GPU
     * needs pays on the GPU term. With no coupling ({@code needs} null or all zero) every term
     * equals plain E-PVM.
     */
    static double placementScore(BookableHost h, LayerCandidate c, double[][] needs) {
        double score = 0;
        for (Dim d : DIMS) {
            double rb = reach(d, h, c, needs, false);
            double ra = reach(d, h, c, needs, true);
            score += d.weight() * deltaCost(d.total(h), rb, rb - ra);
        }
        return score;
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
     * Frames one commit may book for candidate c on host best: the minimum of every sizing rule,
     * each term named. Zero or less means stop booking this candidate this tick. A soft-cap grant
     * (overCap) skips the per-host layer-cap term; the cap already yielded for this booking.
     *
     * Bound: O(D).
     */
    private int headroomFrames(LayerCandidate c, BookableHost best, boolean overCap,
            int probeHeadroom, int limitUsable, int strandFree) {
        long maxMore = computeMaxMore(best, c);
        // Commit size: one plan slice.
        int est = (int) Math.min(frameQueryMax, maxMore + 1);
        // Backlog: never book frames the layer does not have.
        est = Math.min(est, c.waitingFrameCount);
        // Strand bundle: what lies beyond the reach waiting work keeps on this host.
        est = Math.min(est, strandFree);
        // Probe: an unproven layer's remaining farm-wide allowance.
        est = Math.min(est, probeHeadroom);
        // FRAME limits: one frame is one token, budgets shared tick-wide.
        if (limitUsable != Integer.MAX_VALUE)
            est = Math.min(est, limitUsable);
        // Folder ceiling (cores, not frames).
        if (c.folderCell != null && c.layerCoresMin > 0)
            est = Math.min(est, (c.folderMax - c.folderCell.used) / c.layerCoresMin);
        // Per-host layer cap: skipped when the cap already yielded.
        if (!overCap && layerHostMaxFrac > 0) {
            int hlCap = layerHostCap(best, c);
            if (hlCap != Integer.MAX_VALUE)
                est = Math.min(est, hlCap - layerFramesOn(best, c));
        }
        return est;
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
     *
     * Bound: O(D).
     */
    static long computeMaxMore(BookableHost h, LayerCandidate c) {
        long maxMore = Long.MAX_VALUE;
        for (Dim d : DIMS) {
            if (d.need(c) > 0)
                maxMore = Math.min(maxMore, (d.idle(h) - d.need(c)) / d.need(c));
        }

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

    /**
     * Classify the chosen host for the locality dial, reading the very signals the locality bonus
     * scored: live_warm when the host runs the layer right now, cache_warm when the layer left it
     * and fewer than a window of foreign frames displaced its caches since, cold otherwise. Counted
     * in planned frames at the decision, where the classification is exact; a plan can book fewer
     * frames than planned, never more. With the bonus off the warmth map is not fed, so cache_warm
     * reads cold and the dial shows the accidental locality rate, which is the A/B story.
     */
    /**
     * Whole cores idle after this group's plan that no still-waiting candidate can buy: on every
     * such host each candidate is stopped by cores, memory or gpu. The physical counterpart of the
     * waitlist's 'no fit' bucket, counted after planning so cores that just sold are not blamed. A
     * group with nothing waiting strands nothing; idle without demand is just idle.
     *
     * Bound: O(W log W + H log W).
     */
    static long strandedWholeCores(List<BookableHost> hosts, List<LayerCandidate> candidates) {
        GroupViews.NeedView need = new GroupViews.NeedView(candidates);
        if (need.isEmpty())
            return 0;
        long strandedCp = 0;
        for (BookableHost h : hosts) {
            if (h.coresIdle < Dispatcher.CORE_POINTS_RESERVED_MIN)
                continue;
            if (!need.sellable(h))
                strandedCp += h.coresIdle;
        }
        return strandedCp / CORE_POINTS_PER_CORE;
    }

    private String localityKind(BookableHost h, LayerCandidate c) {
        Set<String> layersHere = h.layersRunning;
        if (layersHere != null && layersHere.contains(c.layerId))
            return "live_warm";
        if (localityWindowFrames > 0) {
            Long seen = warmthOn(h, c);
            if (seen != null) {
                long foreign = h.odometer - seen;
                if (foreign >= 0 && foreign < localityWindowFrames)
                    return "cache_warm";
            }
        }
        return "cold";
    }

    // ---- plan / batch-commit: submission ----------------------------------

    /**
     * Record a (host, layer) placement to commit at the end of this tick. Maestro-thread only;
     * doTick drains plannedByHost via planBookings + startFramesAndProcsBatch.
     */
    void submitCommit(BookableHost best, String layerId, int estFrames) {
        plannedByHost.computeIfAbsent(best.hostId, k -> new ArrayList<>()).add(layerId);
        // Slice bookkeeping: this plan starts where the layer's earlier plans
        // this tick end, so parallel plan reads pull disjoint frames.
        best.planned.put(layerId,
                new int[] {plannedFramesByLayer.getOrDefault(layerId, 0), estFrames});
        plannedFramesByLayer.merge(layerId, estFrames, Integer::sum);
    }

    // ---- batched resource accounting: accumulate + flush ------------------

    /**
     * Record the resource deltas for the procs the batch commit just booked. Called on Maestro
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
            addDelta(subDeltas, subKey(p.getShowId(), p.getAllocationId()), cores, gpus);
            addDelta(layerDeltas, p.getLayerId(), cores, gpus);
            addDelta(jobDeltas, p.getJobId(), cores, gpus);
        }
    }

    /**
     * The identity a show's cores are counted against: the subscription, which is per show AND
     * allocation and carries its own burst. Used by both the in-tick cap accounting and the
     * subscription mirror, so the two can never key on different things again.
     */
    static String subKey(String showId, String allocId) {
        return showId + "\t" + allocId;
    }

    private static void addDelta(Map<String, long[]> buf, String key, long cores, long gpus) {
        buf.merge(key, new long[] {cores, gpus}, (a, b) -> {
            a[0] += b[0];
            a[1] += b[1];
            return a;
        });
    }

    /**
     * Apply this tick's accumulated resource deltas as one UPDATE per row. Runs on Maestro thread
     * right after the batch commit, so no accumulation races it. On a SQL error the deltas are
     * merged back so the next tick retries them rather than silently dropping accounting.
     * Subscription/layer rows missing (deleted mid-tick) simply update zero rows; folder/point use
     * the job subquery and likewise no-op if the job is gone.
     */
    private void flushResourceDeltas() {
        flushSubDeltas();
        flushLayerDeltas();
        flushJobDeltas();
    }

    private void flushSubDeltas() {
        if (subDeltas.isEmpty()) {
            return;
        }
        Map<String, long[]> snap = drain(subDeltas);
        List<Object[]> burstBatch = new ArrayList<>(snap.size());
        List<Object[]> pairBatch = new ArrayList<>(snap.size());
        for (Map.Entry<String, long[]> e : snap.entrySet()) {
            String[] k = e.getKey().split("\t", 2);
            long[] d = e.getValue();
            burstBatch.add(new Object[] {(int) d[0], k[0], k[1]});
            pairBatch.add(new Object[] {(int) d[0], (int) d[0], (int) d[1], k[0], k[1]});
        }
        // Same cap-neutral pair trick as flushJobDeltas: verify_subscription
        // rejects a plus that lands over the burst while the burst column is
        // unchanged, so an admin shrinking a busy subscription would wedge
        // this flush forever. Each statement below touches int_burst, the
        // trigger's WHEN clause skips both, and burst is net unchanged at
        // commit. Burst enforcement stays in Maestro at plan time.
        getJdbcTemplate().batchUpdate("UPDATE subscription SET int_burst = int_burst + ? "
                + "WHERE pk_show = ? AND pk_alloc = ?", burstBatch);
        getJdbcTemplate().batchUpdate("UPDATE subscription SET int_cores = int_cores + ?, "
                + "int_burst = int_burst - ?, int_gpus = int_gpus + ? "
                + "WHERE pk_show = ? AND pk_alloc = ?", pairBatch);
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
        getJdbcTemplate().batchUpdate("UPDATE layer_resource SET int_cores = int_cores + ?, "
                + "int_gpus = int_gpus + ? WHERE pk_layer = ?", batch);
    }

    private void flushJobDeltas() {
        if (jobDeltas.isEmpty()) {
            return;
        }
        Map<String, long[]> snap = drain(jobDeltas);
        List<Object[]> jobBatch = new ArrayList<>(snap.size());
        List<Object[]> pairBatch = new ArrayList<>(snap.size());
        List<Object[]> pointBatch = new ArrayList<>(snap.size());
        for (Map.Entry<String, long[]> e : snap.entrySet()) {
            long[] d = e.getValue();
            int cores = (int) d[0];
            int gpus = (int) d[1];
            String jobId = e.getKey();
            jobBatch.add(new Object[] {cores, gpus, jobId});
            pairBatch.add(new Object[] {cores, cores, gpus, gpus, jobId});
            pointBatch.add(new Object[] {cores, gpus, jobId, jobId});
        }
        // The job_resource write is a max-neutral PAIR, not a plain add. The
        // legacy trigger verify_job_resources rejects any statement that raises
        // int_cores while int_max_cores stays unchanged; when a user lowers a
        // running job's max under load, that rejection aborts the whole batch
        // and the mirror drifts (the CAPDROP verify scenario reproduces this).
        // Cap ENFORCEMENT is Maestro's job at plan time; this mirror must
        // always record reality. Each statement below also touches
        // int_max_cores, so the trigger's WHEN clause skips both, and max is
        // net unchanged at commit. Leans on that WHEN clause (V11: fires only
        // on cores-up with max unchanged) by design.
        getJdbcTemplate().batchUpdate("UPDATE job_resource SET int_max_cores = int_max_cores + ?, "
                + "int_max_gpus = int_max_gpus + ? WHERE pk_job = ?", jobBatch);
        getJdbcTemplate().batchUpdate("UPDATE job_resource SET int_cores = int_cores + ?, "
                + "int_max_cores = int_max_cores - ?, int_gpus = int_gpus + ?, "
                + "int_max_gpus = int_max_gpus - ? WHERE pk_job = ?", pairBatch);
        getJdbcTemplate().batchUpdate(
                "UPDATE folder_resource SET int_cores = int_cores + ?, "
                        + "int_gpus = int_gpus + ? "
                        + "WHERE pk_folder = (SELECT pk_folder FROM job WHERE pk_job = ?)",
                jobBatch);
        getJdbcTemplate()
                .batchUpdate(
                        "UPDATE point SET int_cores = int_cores + ?, int_gpus = int_gpus + ? "
                                + "WHERE pk_dept = (SELECT pk_dept FROM job WHERE pk_job = ?) "
                                + "AND pk_show = (SELECT pk_show FROM job WHERE pk_job = ?)",
                        pointBatch);
    }

    /** Copy out the current deltas and clear the buffer for the next tick. Bound: O(entries). */
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
        for (Dim d : DIMS) {
            if (d.idle(h) < d.need(c))
                return false;
        }
        return true;
    }

    /**
     * The resource dimensions of a host and of a frame, in one table, so the fit test, the
     * placement score, the frame estimate, the snapshot decrement and the reach logic all iterate
     * the same list. A new resource is one more constant here once the host report and the schema
     * carry it.
     */
    private static final Dim[] DIMS = Dim.values(); // consumed by the Dim loops

    enum Dim {
        CORES, MEM, GPUS, GPU_MEM;

        long total(BookableHost h) {
            switch (this) {
                case CORES:
                    return h.coresTotal;
                case MEM:
                    return h.memTotal;
                case GPUS:
                    return h.gpusTotal;
                default:
                    return h.gpuMemTotal;
            }
        }

        long idle(BookableHost h) {
            switch (this) {
                case CORES:
                    return h.coresIdle;
                case MEM:
                    return h.memIdle;
                case GPUS:
                    return h.gpusIdle;
                default:
                    return h.gpuMemIdle;
            }
        }

        long need(LayerCandidate c) {
            switch (this) {
                case CORES:
                    return c.layerCoresMin;
                case MEM:
                    return c.layerMemMin;
                case GPUS:
                    return c.layerGpusMin;
                default:
                    return c.layerGpuMemMin;
            }
        }

        double weight() {
            switch (this) {
                case CORES:
                    return wCores;
                case MEM:
                    return wMem;
                case GPUS:
                    return wGpus;
                default:
                    return wGpuMem;
            }
        }

        void take(BookableHost h, long amount) {
            switch (this) {
                case CORES:
                    h.coresIdle -= (int) amount;
                    break;
                case MEM:
                    h.memIdle -= amount;
                    break;
                case GPUS:
                    h.gpusIdle -= (int) amount;
                    break;
                default:
                    h.gpuMemIdle -= amount;
                    break;
            }
        }
    }

    /**
     * Per-unit needs that couple the dimensions, read from the group's waiting work: needs[d][e] is
     * how much of dimension e one unit of dimension d needs to be usable, taken as the smallest
     * ratio among the candidates that ask for d, so a unit counts as reachable while the lightest
     * waiting consumer could still use it. Only a dimension that some waiting candidate does not
     * ask for is coupled: a resource can be stranded only by work that does not use it, so cores
     * and memory, which every frame asks for, keep their plain E-PVM terms. Zero where nothing
     * waiting asks for d: an idle resource with nothing to run is not a loss.
     */
    static double[][] reachNeedsOf(List<LayerCandidate> candidates) {
        int n = DIMS.length;
        double[][] needs = new double[n][n];
        boolean[] strandable = new boolean[n];
        for (LayerCandidate c : candidates) {
            if (c.waitingFrameCount <= 0)
                continue;
            for (Dim d : DIMS)
                if (d.need(c) <= 0)
                    strandable[d.ordinal()] = true;
        }
        for (LayerCandidate c : candidates) {
            if (c.waitingFrameCount <= 0)
                continue;
            for (Dim d : DIMS) {
                long nd = d.need(c);
                if (nd <= 0 || !strandable[d.ordinal()])
                    continue;
                for (Dim e : DIMS) {
                    if (e == d || e.need(c) <= 0)
                        continue;
                    double r = (double) e.need(c) / nd;
                    double cur = needs[d.ordinal()][e.ordinal()];
                    if (cur == 0 || r < cur)
                        needs[d.ordinal()][e.ordinal()] = r;
                }
            }
        }
        return needs;
    }

    /**
     * Units of dimension d still reachable on host h, as it stands ({@code after} false) or once
     * one frame of c has taken its needs ({@code after} true): idle units of d, bounded by what the
     * other dimensions can still support at the group's per-unit needs. Fractional on purpose, so
     * the last core an idle GPU needs still counts toward it. Plain idle when nothing couples d.
     * Reads the host in place: this runs for every host of every slot.
     */
    static double reach(Dim d, BookableHost h, LayerCandidate c, double[][] needs, boolean after) {
        double r = Math.max(0, d.idle(h) - (after ? d.need(c) : 0));
        if (needs == null)
            return r;
        for (Dim e : DIMS) {
            double per = needs[d.ordinal()][e.ordinal()];
            if (per > 0)
                r = Math.min(r, Math.max(0, e.idle(h) - (after ? e.need(c) : 0)) / per);
        }
        return r;
    }

    /**
     * Why an unplaced layer could not fit on any of {@code hosts}, by the first gate no host clears
     * (gates mirror {@link #fitsOnHost}): {@code cores} (no host had enough idle cores for one
     * frame), {@code memory} (cores fit somewhere but not the RAM), {@code gpu} (cores and RAM fit
     * but not the GPU), or {@code fit} (some host fit fully, so the layer was gated by a
     * reservation or a HOST-limit seat -- the caller resolves that into held/license). Feeds the
     * waitlist buckets via {@link #waitlistReason}.
     *
     * Bound: O(log I) for a CPU need; a GPU need walks its fitting prefix.
     */
    static String classifyFragmentation(LayerCandidate c, GroupViews.IdleView idle) {
        int k = idle.fitPrefix(c.layerCoresMin);
        if (k == 0)
            return "cores";
        if (!idle.anyMem(k, c.layerMemMin))
            return "memory";
        if (c.layerGpusMin <= 0 && c.layerGpuMemMin <= 0)
            return "fit";
        for (int i = 0; i < k; i++) {
            BookableHost h = idle.byCores[i];
            if (h.memIdle >= c.layerMemMin && h.gpusIdle >= c.layerGpusMin
                    && h.gpuMemIdle >= c.layerGpuMemMin)
                return "fit";
        }
        return "gpu";
    }

    /**
     * The candidates some idle host of the group fits, the only ones a slot can go to: idle
     * capacity only falls during the slot loop and a need does not change, so a candidate no host
     * fits at the prologue places nothing in any slot, and a draw without it keeps its law.
     *
     * Bound: O(C log I) after the view's O(I log I) build.
     */
    static List<LayerCandidate> fitting(List<LayerCandidate> candidates, GroupViews.IdleView idle) {
        List<LayerCandidate> kept = new ArrayList<>(candidates.size());
        for (LayerCandidate c : candidates) {
            if ("fit".equals(classifyFragmentation(c, idle)))
                kept.add(c);
        }
        return kept;
    }

    /**
     * Resolve a {@code fit} fragmentation (some host fit the layer fully, yet it did not book) into
     * the gate that held it: {@code license} when a fitting host's HOST-limit seat is taken;
     * {@code held} when a fitting host is reserved for someone else (a reservation is draining it
     * for a wide job); {@code strand} when a fitting host keeps an idle resource's bundle for
     * waiting work that needs it (see strandFreeFrames); else {@code share}: every fitting host
     * already holds this layer's per-host share while other work waits (the soft cap yielding to
     * nobody, see othersWant), or was planned for it this tick and takes its next slice next tick.
     *
     * Bound: the fitting prefix at most; the held walk covers the reserved hosts, the strand walk
     * runs only when a dimension couples.
     */
    private String fitGateReason(LayerCandidate c, GroupViews.IdleView idle,
            List<LimitBudget> limitSeatPools, Map<String, Set<String>> limitSeats) {
        int k = idle.fitPrefix(c.layerCoresMin);
        if (limitSeatPools != null) {
            for (int i = 0; i < k; i++) {
                BookableHost h = idle.byCores[i];
                if (fitsOnHost(c, h) && !limitSeatsAllow(limitSeatPools, limitSeats, h))
                    return "license";
            }
        }
        for (BookableHost h : idle.reserved) {
            if (fitsOnHost(c, h) && !reservationAllows(h, c))
                return "held";
        }
        if (reachNeeds != null) {
            for (int i = 0; i < k; i++) {
                BookableHost h = idle.byCores[i];
                if (fitsOnHost(c, h) && strandFreeFrames(h, c) <= 0)
                    return "strand";
            }
        }
        return "share";
    }

    /**
     * The waitlist bucket for an unplaced candidate that still has waiting frames, by the same
     * precedence as the why-not trace: a job / show / folder cap is {@code limit}; an exhausted
     * FRAME-limit budget is {@code no license}; a fitting host reserved for someone else is
     * {@code held}; a layer at its per-host share on every fitting host while other work waits is
     * {@code share}. The remaining fit failures split in two: {@code capacity} when the group's
     * idle cores together cannot cover even one frame (the farm is simply full, nothing is wrong),
     * and {@code no fit} when idle cores exist but none fits (slivers too small for a wide frame,
     * or memory / gpu short): the shape mismatch worth investigating.
     */
    private String waitlistReason(LayerCandidate c, GroupViews.IdleView idle, int folderInUse,
            int limitUsable, List<LimitBudget> limitSeatPools,
            Map<String, Set<String>> limitSeats) {
        if (c.jobCoresInUse + c.layerCoresMin > c.jobMaxCores
                || c.showCoresInUse + c.layerCoresMin > c.showBurstCores
                || (c.folderMax >= 0 && folderInUse + c.layerCoresMin > c.folderMax))
            return "limit";
        if (limitUsable <= 0)
            return "no license";
        String fit = classifyFragmentation(c, idle);
        if ("fit".equals(fit))
            fit = fitGateReason(c, idle, limitSeatPools, limitSeats);
        if ("held".equals(fit) || "share".equals(fit) || "strand".equals(fit))
            return fit;
        if ("license".equals(fit))
            return "no license";
        if ("cores".equals(fit))
            return idle.idleCoresSum < c.layerCoresMin ? "capacity" : "no fit";
        return "no fit";
    }

    /**
     * Fold the per-layer waitlist tallies into the tick stats and preformat the stat-line fragment.
     * The waitlist is every candidate layer that still had waiting frames when the planning loop
     * left it; every such frame is in exactly one bucket, so the panel and the stat line sum to the
     * waitlist the tick actually weighed. Loop-only by design (no extra query): a job the candidate
     * query already filters out at its cap surfaces here only on the ticks churn re-admits it.
     */
    private void tallyWaitlist(MaestroMetrics.TickStats stats) {
        Map<String, Long> w = stats.waitingFramesByReason;
        for (Map.Entry<String, String> e : waitReasonByLayer.entrySet()) {
            Integer frames = waitFramesByLayer.get(e.getKey());
            if (frames != null && frames > 0)
                w.merge(e.getValue(), frames.longValue(), Long::sum);
        }
        long total = 0;
        for (Map.Entry<String, Long> e : w.entrySet()) {
            total += e.getValue();
            winWaitMax.merge(e.getKey(), e.getValue(), Math::max);
        }
        if (total > winWaitTotalMax)
            winWaitTotalMax = total;
    }

    // ---- config -----------------------------------------------------------

    private boolean isEnabled() {
        return MaestroMode.enabled(env);
    }

    // ---- POJOs ------------------------------------------------------------

    static final class BookableHost {
        String hostId;
        String hostName;
        String pkAlloc;
        String pkFacility;
        int threadMode;
        // consumed by hostCanEverFit()
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
        Set<String> layersRunning; // consumed by placeOnce() and localityKind()
        Map<String, Integer> layerFrames; // consumed by layerFramesOn()
        Map<String, int[]> planned; // consumed by plannedOn() and planBookings()
        Map<String, Long> warmth; // consumed by warmthOn()
        long odometer; // consumed by placeOnce() and localityKind()
        Reservation reservation; // consumed by reservationAllows()
        Integer tReady; // consumed by backfillAllows()
        int coresIdleAtBind; // consumed by dispatchHostOf()
        long memIdleAtBind; // consumed by dispatchHostOf()
        int gpusIdleAtBind; // consumed by dispatchHostOf()
        long gpuMemIdleAtBind; // consumed by dispatchHostOf()
        int ix; // consumed by pickHost()
        int stamp; // consumed by HostClasses.candidates()
        HostClasses.Bucket bucket; // consumed by HostClasses.move()
        String claimLayer; // consumed by otherClaim()
        double claim; // consumed by otherClaim()
        double claimNext; // consumed by otherClaim()
    }

    static final class LayerCandidate {
        String layerId;
        String jobId;
        String showId;
        int layerCoresMin;
        long layerMemMin;
        boolean threadable;
        int layerCoresMax;
        int layerGpusMin;
        long layerGpuMemMin;
        int priority;
        // True when rss sizing does not gate this layer: not threadable, feature off,
        // or the ledger has evidence (and the layer was resized from it).
        boolean rssProven;
        boolean placedThisTick; // consumed by dispatchGroupWithScoring()
        // Mutable in-tick accounting.
        int jobCoresInUse;
        int jobMaxCores;
        int showCoresInUse;
        int showBurstCores;
        int showSizeCores; // consumed by showTier()
        String showKey; // consumed by bindCells()
        Cell jobCell; // consumed by gate()
        Cell showCell; // consumed by showTier()
        Cell folderCell; // consumed by headroomFrames()
        Cell[] limitCells; // consumed by gate()
        LimitBudget[] limitBound; // consumed by gate()
        int drawShow; // consumed by SlotDraw.remove()
        int drawIx; // consumed by SlotDraw.remove()
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
        // Limits bound to the layer (layer_limit rows), or null when none (the
        // common case). Which of them actually gate, and with what budget, is
        // resolved once per tick in resolveLimitBudgets.
        List<String> limitIds;
        // Folder (group/dept) core cap. folderId is the job's folder; folderMax is
        // folder_resource.int_max_cores (-1 = unlimited, core-points); folderRunning
        // is the folder's current running cores (core-points), the seed of the
        // folder cell, see bindCells.
        String folderId;
        int folderMax;
        int folderRunning;
        List<BookableHost> pinnedHosts; // consumed by addPinned() and the epilogue's reservation
        Set<String> pinnedIds; // consumed by pinsAllow()
        List<BookableHost> pinnedIdle; // consumed by placeOnce()

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
    static final class PinRow {
        final LayerCandidate row;
        final String hostId;
        final String tags;

        PinRow(LayerCandidate row, String hostId, String tags) {
            this.row = row;
            this.hostId = hostId;
            this.tags = tags;
        }
    }

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
        // Per-tick priority-weighted lottery key (sortByPriorityLottery); higher grants first.
        double grantKey;

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

    public void setMaestroMetrics(MaestroMetrics m) {
        this.maestroMetrics = m;
    }
}
