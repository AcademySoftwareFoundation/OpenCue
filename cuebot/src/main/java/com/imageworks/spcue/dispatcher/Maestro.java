
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
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Random;
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
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;
import java.util.stream.Collectors;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import com.imageworks.spcue.DispatchFrame;
import com.imageworks.spcue.DispatchHost;
import com.imageworks.spcue.VirtualProc;
import com.imageworks.spcue.dao.MaestroDao;
import com.imageworks.spcue.dao.MaestroDao.ResourceDelta;
import com.imageworks.spcue.dao.MaestroDao.SubscriptionDelta;
import com.imageworks.spcue.dao.ProcDao;
import com.imageworks.spcue.grpc.host.ThreadMode;
import com.imageworks.spcue.service.HostManager;
import com.imageworks.spcue.rqd.RqdClient;
import com.imageworks.spcue.rqd.RqdLaunchUnknownOutcomeException;

/**
 * Whole-farm scheduler. Each tick, one Cuebot, the leader holding a Postgres advisory lock, plans
 * placements for every idle host at once; the other Cuebots are warm standbys that only drain frame
 * completions.
 *
 * Planning state (reservations, cache warmth, tick scratch) belongs to the tick thread, so
 * placement decisions never race; only the plan reads and the RQD launches run on pools. Reads and
 * resource mirrors go through MaestroDao, bookings through DispatchSupport. A tick's bookings
 * commit in host-aligned chunks, each its own transaction, and launch as they land. A leader that
 * loses the lock stops committing, and the next leader plans from the database, never from another
 * Cuebot's memory. Persistent reservations hold hosts for blocked wide layers until enough cores
 * free up.
 *
 * Gated by maestro.enabled (default false) and tuned by the maestro.* properties. See
 * docs/_docs/developer-guide/maestro.md for the full model.
 */
public class Maestro {

    private static final Logger logger = LogManager.getLogger(Maestro.class);

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
    private final Map<String, Long> warmthByHostLayer = new HashMap<String, Long>();
    // host -> booking odometer, incremented per frame booked on the host.
    private final Map<String, Long> bookingsByHost = new HashMap<String, Long>();

    // Per-host same-layer cap: one layer may hold at most this fraction of a host's cores,
    // never below layerHostCapMinFrames frames so small hosts still anchor a cache-warm batch.
    // 0 disables; default 0.25. Bounds the blast radius and the phase-locked IO of a hundred
    // identical frames blanketing one machine, at the price of nibbling more hosts per flood.
    private volatile double layerHostMaxFrac = 0.25;
    // Floor of the per-host same-layer cap, in frames (maestro.layer_host_cap_min_frames).
    private volatile int layerHostCapMinFrames = 8;

    // Memory-driven sizing (see maestro.md 3.9). A threadable layer books
    // round(memory / memory-per-core) cores, where memory is the larger of its ask and the
    // largest rss any of its frames has reported (layer_mem.int_max_rss, raised by every
    // host report). cores=1 means "let the system decide": a layer that still sizes to 1
    // core with no rss seen yet probes at probeFrames running frames, then every later
    // launch books at its real shape. The ratio is maestro.mem_per_core (KB); 0, the
    // default, derives it from each group's own hosts.
    // Static, like the score weights, because the pure helpers that read them are static.
    static volatile int probeFrames = 8; // maestro.probe_frames
    static volatile int commitChunkFrames = 500; // maestro.commit_chunk_frames
    static volatile double priorityExponent = 1.5; // maestro.priority_exponent
    // Shutdown bounds (maestro.shutdown_launch_drain_seconds, maestro.shutdown_tick_wait_seconds).
    private volatile int launchDrainMaxSeconds = 30;
    private volatile int tickEndWaitMaxSeconds = 30;
    // Launch-queue age past which a committed booking is rolled back unsent; see
    // launchMaxAgeMs(Environment). Re-read from the environment at pool start.
    volatile long launchMaxAgeMs = launchMaxAgeMs(null);
    // Consecutive failed liveness probes before leaderAlive() gives the lock up
    // (maestro.leader_probe_strikes). A single isValid(1) timeout on a loaded server must not
    // demote a leader that still holds the lock.
    private volatile int leaderProbeStrikes = 2;
    private volatile long memPerCoreKb = 0;

    // Seat bonus for HOST-type limits (one license checkout per machine): subtracted per seated
    // pool so placement packs limited work onto the fewest hosts. Sized above the E-PVM spread.
    private volatile double limitSeatBonus = 16.0;

    // Retry transactions a tick may spend splitting failed commit chunks
    // (maestro.commit_split_max_tx); see commitContained.
    private volatile int commitSplitMaxTx = 64;

    // Spring config; scheduler.* properties read once in startSchedulerPoolsIfNeeded().
    @Autowired
    private Environment env;

    // Backs txTemplate (atomic resource-delta flushes).
    @Autowired
    private PlatformTransactionManager transactionManager;

    // Wraps each resource-delta flush so its several UPDATEs commit atomically. Built lazily.
    private volatile TransactionTemplate txTemplate;

    private TransactionTemplate txTemplate() {
        TransactionTemplate template = txTemplate;
        if (template == null) {
            template = new TransactionTemplate(transactionManager);
            txTemplate = template;
        }
        return template;
    }

    // Every database read and resource-mirror write the scheduler makes, and the planning lock.
    private MaestroDao maestroDao;

    // Plans one host's next bookable frames via planHost() (legacy per-host dispatch path).
    private Dispatcher dispatcher;

    // Applies frame completions; drives the stage-0 drain (drainResolvedCompletions).
    private FrameCompleteHandler frameCompleteHandler;

    // Records each tick's stats to Prometheus via recordTick (runTick).
    private MaestroMetrics maestroMetrics;

    // Live farm-health ledger (swap, kernel time) fed by host reports; optional so the
    // scheduler runs unchanged where the ledger bean is absent (unit tests).
    @Autowired(required = false)
    private FarmHealth farmHealth;

    // The in-progress tick's stats, handed to maestroMetrics at tick end.
    private MaestroMetrics.TickStats lastTickStats;

    // Wall time of the latest drain, for the tick's phase split (doTick).
    private long lastDrainMs = 0;

    // A tick longer than this is logged at WARN with its phase breakdown
    // (maestro.slow_tick_warn_ms).
    private volatile long slowTickWarnMs = 10_000;

    // Completions per drain transaction (maestro.drain_chunk_completions). Each holds its procs'
    // host rows, and every stop costs a frame_history close on the production table: 130 rows
    // at 200 ms held every host of a tick for 27 s. Small, so no one waits long on a host.
    private volatile int drainChunkCompletions = 20;

    // Batched commit, frame stop/unbook, and RQD launch of committed frames.
    private DispatchSupport dispatchSupport;

    // Resolves a host id to a DispatchHost for the plan reads (planBookings).
    private HostManager hostManager;

    // Kills the frame whose post-commit launch failed (by frame id); see launchCommitted.
    private RqdClient rqdClient;

    // Reentrancy latch: a slow tick makes the next firing skip instead of overlapping (runTick).
    private final AtomicBoolean tickInFlight = new AtomicBoolean(false);

    // This Cuebot's planning-leadership lock connection, or null when standby. Sticky and raw (not
    // pooled, so Hikari cannot reap it and drop the lock). See maestro.md for the failover model.
    private volatile Connection leaderConn = null;
    // Set once by onShutdown; from then on no tick takes or keeps leadership.
    private volatile boolean shuttingDown = false;
    // Consecutive leaderAlive() probe misses; tick thread only. See leaderProbeStrikes.
    private int leaderProbeMisses = 0;

    // Live host reservations, persistent across ticks: host id -> claiming (layer, priority).
    // Maestro-thread only (single-writer); empty after failover. See maestro.md for the model.
    private final Map<String, Reservation> reservations = new HashMap<>();

    // ---- plan / batch-commit / launch -------------------------------------
    // Placement only records (host, layer) pairings; after it, planHost reads each pairing's frames
    // and one batched transaction commits them all, then RQD launches fire on a small pool.

    // Per-tick placements to commit, host id -> layer ids. Maestro-thread only; cleared each tick.
    private final Map<String, List<String>> plannedByHost = new LinkedHashMap<>();


    // Tick-scoped planning scratch (Maestro-thread only, reset each tick by clearTickScratch). Held
    // as fields so the phase methods share them without threading a dozen parameters.
    private final Map<String, Integer> jobCoresUsed = new HashMap<>();
    private final Map<String, Integer> showCoresUsed = new HashMap<>();
    private final Map<String, Integer> folderUsed = new HashMap<>();
    private final Map<String, Integer> folderMaxCp = new HashMap<>();
    private final Map<String, Integer> folderRunSeed = new HashMap<>();
    private final Map<String, String> jobFolderCap = new HashMap<>();
    private final Map<String, List<String>> layerLimits = new HashMap<>();
    private final Map<String, LimitBudget> limitBudgets = new HashMap<>();
    private final Map<String, Integer> limitUsed = new HashMap<>();
    private final Map<String, Set<String>> limitSeats = new HashMap<>();
    // True once this tick's limit budgets are loaded; reset by clearTickScratch.
    /* package for tests */ boolean limitBudgetsResolved = false;
    private final Set<String> seenLayerIds = new HashSet<>();
    // This tick's pinned candidates per host-spec group (resolveTickPins), merged by planGroup.
    private final Map<HostSpecKey, List<LayerCandidate>> pinnedByGroup = new HashMap<>();
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
    private Map<String, Integer> hostLayerFrames = new HashMap<>();
    // Frames each layer runs farm-wide right now, read with the same snapshot. Backs the
    // probe gate for layers with no rss evidence yet.
    private Map<String, Integer> layerRunningFrames = new HashMap<>();
    // Probe frames planned this tick per unproven layer.
    private final Map<String, Integer> layerProbeUsed = new HashMap<>();

    // Tick-scoped frame slices, so a layer planned on several hosts has its parallel plan reads
    // pull disjoint frames and deliver exactly what the scoring accounted.
    // layerId -> frames planned for the layer so far this tick (where its next slice starts).
    private final Map<String, Integer> plannedFramesByLayer = new HashMap<>();
    // "hostId|layerId" -> the pair's slices of the layer's waiting list, each {offset, frame
    // count}. A pair holds one slice per slot the draw gave it this tick.
    private final Map<String, List<int[]>> planSliceByHostLayer = new HashMap<>();
    // Layers sized this tick: layerId -> {core points, memory KB}, read by planBookings so
    // the commit books the same shape the Maestro scored.
    private final Map<String, long[]> layerResize = new HashMap<>();

    // Layer-placements planned this tick, for the tick-breakdown log line.
    private int lastPlacements;

    // Consecutive ticks a layer was planned but planHost's commit-time read found zero frames: the
    // signature of a Maestro-vs-dispatch eligibility mismatch. Warns at plan_zero_warn_ticks.
    private final Map<String, Integer> planZeroStreak = new ConcurrentHashMap<>();

    // Fixed pool over an unbounded queue for the post-commit RQD launches (one gRPC per frame);
    // see startSchedulerPoolsIfNeeded and launchOne.
    private volatile ThreadPoolExecutor launchPool;

    // Pool for the plan phase (planBookings), two rounds: one frame read per planned layer, then
    // one in-memory plan task per host (serial within a host so the capacity decrement is
    // correct). Commit is still single/batched.
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
    // full snapshot for bug reports, emitted on every tick attempt (leader or standby) as a
    // heartbeat.

    // Core points per whole core: OpenCue stores host/proc cores as cores * 100.
    private static final int CORE_POINTS_PER_CORE = 100;

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
    private int summaryPlanFailures = 0; // plan reads that threw (planFail)
    private int summaryGranted = 0; // new reservations granted
    private int summaryBackfilled = 0; // frames placed onto a reserved host
    private long summaryBackfilledCores = 0; // core-points placed via EASY backfill
    private long summaryDrained = 0; // completion reports drained at tick start
    private long summaryLicenseBooked = 0; // frames booked against a license pool
    private long summaryLicenseHeld = 0; // candidates held back by a license pool
    private long summaryLicenseTrimmed = 0; // planned frames a pool could not cover
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
    // The last commitInChunks: chunk splits made and bookings dropped (commitContained).
    int lastCommitSplits = 0;
    int lastCommitDropped = 0;
    // Wall time of this tick's candidate read (loadTickCandidates), the SQL half of the place
    // phase, and of the pin resolution over it (resolveTickPins).
    private long tickCandidatesMs = 0;
    private long tickPinsMs = 0;

    // This tick's candidate read, cut per group by readLayerCandidatesForGroup; null between
    // ticks (clearTickScratch), and read on demand by a caller outside a tick (tests).
    private TickCandidates tickCandidates = null;

    // Layer tag regexes compiled once per distinct tag string, kept across ticks: most layers
    // share a handful of patterns, and compiling is the cost the per-group SQL paid per row.
    // A pattern Java cannot compile maps to null and its layers are excluded (warned once).
    // Tag strings that name a host (pins) make the set grow with the farm's history, so the
    // cache is dropped whole past TAG_PATTERN_CACHE_MAX and rebuilt from the next tick's rows.
    private final Map<String, Optional<Pattern>> tagPatterns = new ConcurrentHashMap<>();
    static final int TAG_PATTERN_CACHE_MAX = 10_000;
    // group tags + NUL + layer tags -> matched, for this tick (clearTickScratch).
    private final Map<String, Boolean> tagMatches = new HashMap<>();
    private final Set<String> warnedTagPatterns = ConcurrentHashMap.newKeySet();
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
    // Warn threshold: a group count near the host count means near-per-host fragmentation
    // (maestro.group_count_warn_threshold). See warnIfGroupsFragmented.
    private volatile int groupCountWarnThreshold = 100;
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
     * Read the maestro.* tunables and start the launch and read pools, once, on the first tick.
     * Idempotent. Lazy rather than a Spring init-method: Cuebot is long past startup by the time
     * maestro.enabled is turned on, and a tunable changed before then is still picked up.
     */
    private synchronized void startSchedulerPoolsIfNeeded() {
        if (launchPool != null)
            return;
        int launchSize = env.getProperty("maestro.launch_pool_size", Integer.class, 8);
        launchMaxAgeMs = launchMaxAgeMs(env);
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
        layerHostCapMinFrames =
                env.getProperty("maestro.layer_host_cap_min_frames", Integer.class, 8);
        memPerCoreKb = env.getProperty("maestro.mem_per_core", Long.class, 0L);
        // Property name kept from the per-host-limit feature this supersedes, so
        // any site already setting it keeps its value.
        limitSeatBonus = env.getProperty("maestro.host_limit_seat_bonus", Double.class, 16.0);
        commitSplitMaxTx = env.getProperty("maestro.commit_split_max_tx", Integer.class, 64);
        wCores = env.getProperty("maestro.score_weight_cores", Double.class, 1.0);
        wMem = env.getProperty("maestro.score_weight_mem", Double.class, 1.0);
        wGpus = env.getProperty("maestro.score_weight_gpus", Double.class, 4.0);
        wGpuMem = env.getProperty("maestro.score_weight_gpu_mem", Double.class, 1.0);
        // Cadence of the consolidated INFO stat line (see maybeLogStat). Default
        // 5 minutes; lower it for a live incident, raise it to quiet the log.
        statIntervalMs =
                1000L * env.getProperty("maestro.stat_interval_seconds", Integer.class, 300);
        probeFrames = env.getProperty("maestro.probe_frames", Integer.class, 8);
        commitChunkFrames = env.getProperty("maestro.commit_chunk_frames", Integer.class, 500);
        priorityExponent = env.getProperty("maestro.priority_exponent", Double.class, 1.5);
        drainChunkCompletions =
                env.getProperty("maestro.drain_chunk_completions", Integer.class, 20);
        leaderProbeStrikes = env.getProperty("maestro.leader_probe_strikes", Integer.class, 2);
        slowTickWarnMs = env.getProperty("maestro.slow_tick_warn_ms", Long.class, 10_000L);
        groupCountWarnThreshold =
                env.getProperty("maestro.group_count_warn_threshold", Integer.class, 100);
        launchDrainMaxSeconds =
                env.getProperty("maestro.shutdown_launch_drain_seconds", Integer.class, 30);
        tickEndWaitMaxSeconds =
                env.getProperty("maestro.shutdown_tick_wait_seconds", Integer.class, 30);
        // A fixed pool so launches never run on the tick thread (a slow RQD sink would stall the
        // tick), over an UNBOUNDED queue: a committed booking is always launched. A tick may
        // commit a whole cold farm at once, and a dropped launch leaves a frame RUNNING in the
        // DB with no process behind it until the orphan sweep finds it minutes later; a slow
        // sink now shows as launch latency, never as lost work. The handler below can only fire
        // when the pool is shutting down.
        ThreadPoolExecutor pool = new ThreadPoolExecutor(launchSize, launchSize, 0L,
                TimeUnit.MILLISECONDS, new LinkedBlockingQueue<>(), runnable -> {
                    Thread thread = new Thread(runnable);
                    thread.setName("Maestro-launch-" + thread.getId());
                    thread.setDaemon(true);
                    return thread;
                }, (runnable, ex) -> {
                    logger.warn("Maestro: launch rejected, pool shutting down;"
                            + " RQD reconciliation will recover");
                });
        launchPool = pool;
        // Read pool for the parallel plan phase. Reads are DB-bound (they block
        // on Postgres, not the CPU), so sizing above the core count is fine.
        int readSize = env.getProperty("maestro.read_pool_size", Integer.class, launchSize);
        readPool = Executors.newFixedThreadPool(readSize, runnable -> {
            Thread thread = new Thread(runnable);
            thread.setName("Maestro-read-" + thread.getId());
            thread.setDaemon(true);
            return thread;
        });
        logger.info("Maestro: launch pool started with " + launchSize + " workers, read pool with "
                + readSize + " workers");
    }

    // ---- tick -------------------------------------------------------------

    /**
     * Quartz entry point, fired every few seconds on every Cuebot. Runs at most one tick at a time
     * per Cuebot: a firing that overlaps a tick in flight is skipped and counted, never queued.
     * Does nothing while maestro.enabled is false.
     *
     * Every tick, leader or standby, feeds the per-window stat line (maybeLogStat), which doubles
     * as a heartbeat; a standby contributes only its drain count.
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
        } catch (RuntimeException exception) {
            logger.error("Maestro tick failed", exception);
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
     * Apply the frame completions queued since the last tick, before any planning, so a plan never
     * races an in-flight completion. Runs on every Cuebot, leader or standby, as the single writer
     * of completions in arrival order. Returns the number drained.
     *
     * Completions are applied in transactions of at most {@link #drainChunkCompletions}, bounding
     * how long host rows stay locked. A completion that fails never blocks the rest of the queue.
     * When locality is on, every applied completion leaves a cache-warmth entry for its (host,
     * layer).
     */
    int drainResolvedCompletions() {
        lastDrainMs = 0;
        if (frameCompleteHandler == null)
            return 0;
        List<QueuedFrameCompletion> resolved = MaestroCompletionQueue.drain();
        int drained = resolved.size();
        long tDrain0 = System.currentTimeMillis();
        for (int from = 0; from < resolved.size(); from += drainChunkCompletions) {
            List<QueuedFrameCompletion> chunk =
                    resolved.subList(from, Math.min(from + drainChunkCompletions, resolved.size()));
            long tChunk0 = System.currentTimeMillis();
            try {
                boolean[] won = dispatchSupport.stopFramesBatch(chunk);
                long tChunk = System.currentTimeMillis() - tChunk0;
                if (tChunk > 500) {
                    logger.info("Maestro drain: stopFramesBatch(" + chunk.size() + ") took "
                            + tChunk + "ms");
                }
                for (int index = 0; index < won.length; index++) {
                    QueuedFrameCompletion completion = chunk.get(index);
                    if (won[index]) {
                        // Warmth is the leader's ledger: a standby never advances
                        // the odometers, so its stamps would neither expire nor mean
                        // anything.
                        if (leaderConn != null && localityEnabled && localityWindowFrames > 0
                                && completion.proc.getLayerId() != null) {
                            warmthByHostLayer.put(
                                    completion.proc.getHostId() + "|"
                                            + completion.proc.getLayerId(),
                                    bookingsByHost.getOrDefault(completion.proc.getHostId(), 0L));
                        }
                        frameCompleteHandler.queuePostOps(completion);
                    } else {
                        frameCompleteHandler.handleStaleCompletion(completion.proc,
                                completion.report,
                                completion.proc.getName() + "/" + completion.frame.getName());
                    }
                }
            } catch (RuntimeException exception) {
                logger.warn("Maestro drain: batch of " + chunk.size()
                        + " completions failed, retrying per-report: " + exception);
                for (QueuedFrameCompletion completion : chunk) {
                    try {
                        frameCompleteHandler.processReportNow(completion.report);
                    } catch (RuntimeException e2) {
                        logger.warn("Maestro drain: completion for frame "
                                + completion.frame.getName() + " failed: " + e2);
                    }
                }
            }
        }
        long tDrain = System.currentTimeMillis() - tDrain0;
        lastDrainMs = tDrain;
        if (tDrain > 1000) {
            logger.info("Maestro drain: " + drained + " completions in " + tDrain + "ms");
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
                .removeIf(entry -> bookingsByHost
                        .getOrDefault(entry.getKey().substring(0, entry.getKey().indexOf('|')), 0L)
                        - entry.getValue() >= localityWindowFrames);
    }

    /**
     * Emit the consolidated INFO stat line at most once per {@link #statIntervalMs}, then reset the
     * window accumulators. The line is meant to be a complete snapshot for a bug report:
     *
     * health/HA: window seconds, ticks won, ticks skipped because the previous one still ran,
     * lockLost (ticks spent as a standby), average and slowest tick. farm: the last planned tick's
     * host and core fill and its host-spec group count (near the host count means tags are
     * fragmenting the groups). flow: committed procs, planned frames, the gap lost to the
     * frame-version race, and RQD launches dropped. resv: reservations held and the cores they
     * hold, new grants, last tick's requests, and frames EASY-backfilled onto reserved hosts. lic,
     * only while gating limits are in play: frames booked against a limit, candidates a limit held
     * back, and planned frames trimmed at commit.
     *
     * Tick thread only (runTick's finally, under tickInFlight), so the window fields are
     * single-writer; the exception is summarySkipped, bumped atomically by the firing that lost the
     * latch.
     */
    private void maybeLogStat() {
        long nowMs = System.currentTimeMillis();
        if (lastSummaryMs == 0) { // first call: start the window, do not emit
            lastSummaryMs = nowMs;
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
        int skipped = summarySkipped.getAndSet(0);

        // Cores currently held by the wide-job reservation feature: the sum of the
        // reserved layers' per-frame core requirement across all live reservations.
        // A point-in-time level (like held), not a window flow, so it is summed
        // here from the reservations map rather than accumulated per tick.
        long reservedCp = 0;
        for (Reservation reservation : reservations.values()) {
            reservedCp += reservation.layerCoresMin;
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
                        + " share=%d nohost=%d",
                winWaitTotalMax, winWaitMax.getOrDefault("flowing", 0L),
                winWaitMax.getOrDefault("capacity", 0L), winWaitMax.getOrDefault("no fit", 0L),
                winWaitMax.getOrDefault("limit", 0L), winWaitMax.getOrDefault("no license", 0L),
                winWaitMax.getOrDefault("held", 0L), winWaitMax.getOrDefault("share", 0L),
                winWaitMax.getOrDefault("no host", 0L));

        logger.info(String.format(
                "Maestro stat: win=%ds ticks=%d skipped=%d lockLost=%d avgTick=%dms maxTick=%dms"
                        + " | farm hosts=%d idleHosts=%d cores=%d idleCores=%d util=%.1f%% groups=%d"
                        + " | flow committed=%d planned=%d raceLost=%d drained=%d"
                        + " completionQ=%d postQ=%d planFail=%d"
                        + " | resv held=%d reservedCores=%d granted=%d reqs=%d backfilled=%d backfilledCores=%d%s%s",
                win, summaryTicks, skipped, summaryLockLost, avgTick, summaryMaxTickMs, lastHosts,
                lastIdleHosts, coresTotal, idleCores, util, lastGroups, summaryDispatched,
                summaryPlanned, raceLost, summaryDrained, MaestroCompletionQueue.size(),
                frameCompleteHandler == null ? 0 : frameCompleteHandler.getPostCompleteQueueDepth(),
                summaryPlanFailures, reservations.size(), reservedCp / CORE_POINTS_PER_CORE,
                summaryGranted, lastReservationReqs, summaryBackfilled,
                summaryBackfilledCores / CORE_POINTS_PER_CORE, lic, waitlist));

        lastSummaryMs = nowMs;
        summaryTicks = 0;
        summaryDispatched = 0;
        summaryTickMs = 0;
        summaryMaxTickMs = 0;
        summaryLockLost = 0;
        summaryPlanned = 0;
        summaryPlanFailures = 0;
        summaryGranted = 0;
        summaryBackfilled = 0;
        summaryBackfilledCores = 0;
        summaryDrained = 0;
        summaryLicenseBooked = 0;
        summaryLicenseHeld = 0;
        summaryLicenseTrimmed = 0;
        winWaitMax.clear();
        winWaitTotalMax = 0;
    }

    /**
     * Zero the per-tick stat outputs before any early return, so a host-less tick contributes zero
     * to the window rather than carrying last tick's values.
     */
    private void resetTickOutputs() {
        tickPlanned = 0;
        tickCandidatesMs = 0;
        tickPinsMs = 0;
        tickGranted = 0;
        tickBackfilled = 0;
        tickBackfilledCores = 0;
        tickLicenseBooked = 0;
        tickLicenseHeld = 0;
        tickLicenseTrimmed = 0;
    }

    /**
     * Record the farm's host and core fill for the stat line. Must run before placement, which
     * decrements the snapshot's idle counts. Core points; maybeLogStat converts to whole cores.
     */
    private void snapshotFarmFill(List<BookableHost> allHosts) {
        lastHosts = allHosts.size();
        lastIdleHosts = 0;
        lastCoresTotalCp = 0;
        lastCoresIdleCp = 0;
        for (BookableHost host : allHosts) {
            lastCoresTotalCp += host.coresTotal;
            lastCoresIdleCp += host.coresIdle;
            if (host.coresIdle >= Dispatcher.CORE_POINTS_RESERVED_MIN)
                lastIdleHosts++;
        }
    }

    /**
     * Warn, at most every five minutes, when the host-spec group count reaches
     * {@link #groupCountWarnThreshold}. A handful of groups is expected; a count near the host
     * count means the spec key is fragmenting per host, usually because a host name leaked into the
     * tag set, and planning degenerates to one group per host, the cost grouping exists to avoid.
     */
    private void warnIfGroupsFragmented(int groupCount, int hostCount) {
        if (groupCount < groupCountWarnThreshold)
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
     * Drop the planned bookings that would take a capped folder past its int_max_cores, in plan
     * order, counting from the folder's running cores at tick start. The plan read does not see
     * folder caps, so this trim is what enforces them. Folders without a cap are untouched; dropped
     * frames stay WAITING for the next tick. Returns the bookings to keep.
     */
    List<FrameBooking> trimOverFolderCeiling(List<FrameBooking> planned,
            Map<String, Integer> folderMaxCp, Map<String, Integer> folderRunSeed,
            Map<String, String> jobFolderCap) {
        if (folderMaxCp.isEmpty() || planned.isEmpty())
            return planned;
        Map<String, Integer> folderCommit = new HashMap<>(folderRunSeed);
        List<FrameBooking> keep = new ArrayList<>(planned.size());
        int folderTrimmed = 0;
        for (FrameBooking booking : planned) {
            String fid = jobFolderCap.get(booking.proc.getJobId());
            if (fid == null) {
                keep.add(booking);
                continue;
            }
            int cap = folderMaxCp.get(fid);
            int used = folderCommit.getOrDefault(fid, 0);
            int cp = booking.proc.coresReserved;
            if (used + cp <= cap) {
                folderCommit.put(fid, used + cp);
                keep.add(booking);
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
     * Drop the planned bookings that would exceed a gating limit's budget this tick. The plan read
     * is limit-blind, so this trim is what enforces limits. Returns the bookings to keep; dropped
     * frames stay WAITING for the next tick.
     *
     * FRAME limits count frames; HOST limits count only hosts not already seated. A frame consumes
     * its limits only once every one of them admits it, so a frame rejected by one limit never
     * takes a seat in another. A limit with no budget entry (ADVISORY, DISABLED or stale report)
     * does not gate.
     */
    private List<FrameBooking> trimOverLimitBudgets(List<FrameBooking> planned,
            Map<String, LimitBudget> limitBudgets, Map<String, List<String>> layerLimits) {
        if (limitBudgets.isEmpty() || layerLimits.isEmpty() || planned.isEmpty())
            return planned;
        Map<String, Integer> committedByLimit = new HashMap<>();
        Map<String, Set<String>> seatsByLimit = new HashMap<>();
        List<FrameBooking> keep = new ArrayList<>(planned.size());
        int limTrimmed = 0;
        for (FrameBooking booking : planned) {
            List<String> limIds = layerLimits.get(booking.proc.getLayerId());
            if (limIds == null) {
                keep.add(booking);
                continue;
            }
            String hostName = shortHostName(booking.proc.hostName);
            boolean fits = true;
            for (String limId : limIds) {
                LimitBudget bd = limitBudgets.get(limId);
                if (bd == null)
                    continue;
                if (bd.hostBased) {
                    Set<String> seats =
                            seatsByLimit.computeIfAbsent(limId, key -> new HashSet<>(bd.seats));
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
            keep.add(booking);
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
    private void sweepStaleReservationState(Set<String> seenLayerIds) {
        reservations.entrySet().removeIf(entry -> !seenLayerIds.contains(entry.getValue().layerId));
        blockedDebtMs.keySet().removeIf(id -> !seenLayerIds.contains(id));
        lastSeenMs.keySet().removeIf(id -> !seenLayerIds.contains(id));
    }

    /**
     * Settle this tick's reservation requests. Every layer already holding reservations is
     * reconciled (refreshed, or released promptly), while at most maestro.reservation_max_grantees
     * new layers are granted this tick, in priority-lottery order (sortByPriorityLottery) so a
     * low-priority wide job is not starved by a higher-priority stream. Requests not granted draw
     * again next tick.
     */
    private void grantReservations(List<ReservationRequest> reservationReqs) {
        int reservationMaxGrantees =
                env.getProperty("maestro.reservation_max_grantees", Integer.class, 8);
        sortByPriorityLottery(reservationReqs);
        logReservationTick(reservationReqs, reservationMaxGrantees);
        int newGrantees = 0;
        for (ReservationRequest request : reservationReqs) {
            if (layerHoldsReservation(request.candidate.layerId)) {
                reconcileReservationsForLayer(request.candidate, request.fullHosts);
            } else if (newGrantees < reservationMaxGrantees) {
                reconcileReservationsForLayer(request.candidate, request.fullHosts);
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
     * Order reservation requests by a priority-weighted lottery (Efraimidis-Spirakis, weight =
     * priority), highest key first. Higher priority is favored, yet every request has a nonzero
     * chance of leading, which keeps a low-priority wide job from being starved of grants with no
     * separate anti-starvation deadline.
     */
    private void sortByPriorityLottery(List<ReservationRequest> reqs) {
        for (ReservationRequest request : reqs) {
            int pri = Math.max(1, request.candidate.priority);
            request.grantKey = Math.pow(ThreadLocalRandom.current().nextDouble(), 1.0 / pri);
        }
        reqs.sort((left, right) -> Double.compare(right.grantKey, left.grantKey));
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
            for (int index = 0; index < show; index++) {
                ReservationRequest rr = reservationReqs.get(index);
                long debt = blockedDebtMs.getOrDefault(rr.candidate.layerId, 0L);
                sb.append("layer=").append(rr.candidate.layerId).append("(cores=")
                        .append(rr.candidate.layerCoresMin).append(",waiting=")
                        .append(rr.candidate.waitingFrameCount).append(",debt=").append(debt)
                        .append("ms)");
                if (index < show - 1)
                    sb.append(", ");
            }
            sb.append("]");
        }
        logger.debug(sb.toString());
    }

    /**
     * Reset all tick-scoped planning scratch. Runs at the start of every tick so a tick that threw
     * mid-placement never leaks (host, layer) pairings or half-filled cap maps into the next. The
     * read-fresh maps (tReadyByHost, hostLayerAffinity) are reassigned by doTick instead.
     */
    private void clearTickScratch() {
        plannedByHost.clear();
        jobCoresUsed.clear();
        showCoresUsed.clear();
        folderUsed.clear();
        folderMaxCp.clear();
        folderRunSeed.clear();
        jobFolderCap.clear();
        layerLimits.clear();
        limitBudgets.clear();
        limitUsed.clear();
        limitSeats.clear();
        limitBudgetsResolved = false;
        seenLayerIds.clear();
        pinnedByGroup.clear();
        reservationReqs.clear();
        waitReasonByLayer.clear();
        waitFramesByLayer.clear();
        tickCandidates = null;
        tagMatches.clear();
        if (tagPatterns.size() > TAG_PATTERN_CACHE_MAX) {
            tagPatterns.clear();
            warnedTagPatterns.clear();
        }
    }

    /**
     * Plan one host-spec group against this tick's candidates and return the frames booked for it.
     * Bumps exactly one outcome counter in stats: queryError, noWork, booked or noFit.
     *
     * Placement uses only the group's idle hosts (those with the minimum reservable cores free),
     * while reservations consider the whole group so a blocked layer can hold a busy host.
     * Candidates are admitted against the group's largest host, not its idle capacity, so a layer
     * waiting on a partially loaded reserved host stays a candidate and keeps its reservation. A
     * failed tick candidate read counts as this group's query error.
     */
    private int planGroup(HostSpecKey spec, List<BookableHost> fullGroup,
            MaestroMetrics.TickStats stats) {
        List<BookableHost> idleGroup = new ArrayList<>();
        for (BookableHost host : fullGroup) {
            if (host.coresIdle >= Dispatcher.CORE_POINTS_RESERVED_MIN)
                idleGroup.add(host);
        }
        int maxCoresTotalInGroup =
                fullGroup.stream().mapToInt(host -> host.coresTotal).max().orElse(0);

        List<LayerCandidate> candidates;
        try {
            candidates = readLayerCandidatesForGroup(spec, maxCoresTotalInGroup);
            addPinned(candidates, pinnedByGroup.get(spec), idleGroup);
            // Size threadable layers from their memory before anything scores or fits
            // them, against the memory-per-core ratio (or this group's own derived one).
            sizeFromMemory(candidates,
                    memPerCoreKb > 0 ? memPerCoreKb : memPerWholeCoreKb(fullGroup),
                    maxCoresTotalInGroup, layerResize);
        } catch (RuntimeException exception) {
            long nowMs = System.currentTimeMillis();
            if (nowMs - lastCandidateErrWarnMs >= GROUP_WARN_INTERVAL_MS) {
                lastCandidateErrWarnMs = nowMs;
                logger.warn("Maestro: the candidate read failed; skipping " + spec
                        + " and every other group this tick: " + exception.getMessage());
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
                spec.pkAlloc, jobCoresUsed, showCoresUsed, folderUsed, reservationReqs,
                tReadyByHost, hostLayerAffinity, limitBudgets, limitUsed, limitSeats);
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
     * One scheduling pass. Every Cuebot drains completions first; only the leader goes on to plan.
     * Returns the frames committed, or -1 for a standby that drained but did not plan.
     *
     * The leader plans from one snapshot of the farm taken at tick start: hosts are grouped by
     * spec, each group is planned in memory against the tick's single candidate read, reservations
     * are granted, and the resulting bookings are trimmed to the folder and limit caps, committed
     * and launched. See maestro.md for the full model.
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
        stats.phaseMs.put("drain", lastDrainMs);
        resetTickOutputs();
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
        Map<String, List<BookableHost>> hostByName = new HashMap<>();
        for (BookableHost host : allHosts) {
            hostById.put(host.hostId, host);
            hostByName.computeIfAbsent(host.hostName.toLowerCase(Locale.ROOT),
                    key -> new ArrayList<>()).add(host);
        }
        tReadyByHost = computeHostReadySeconds(hostById);
        hostLayerAffinity = readHostLayerAffinity();
        long tSnapshot = System.currentTimeMillis();
        stats.phaseMs.put("snapshot", tSnapshot - tStart);

        // 3. READ the tick's candidates once, resolve the pins among them, then PLAN each
        // host-spec group in priority order.
        loadTickCandidates();
        resolveTickPins(groups, hostByName);
        int dispatched = 0;
        for (Map.Entry<HostSpecKey, List<BookableHost>> entry : groups.entrySet())
            dispatched += planGroup(entry.getKey(), entry.getValue(), stats);
        tallyWaitlist(stats);

        grantReservations(reservationReqs);

        // 4. PLAN bookings in parallel, then trim to the exact folder + limit budgets.
        long tPlan = System.currentTimeMillis();
        stats.phaseMs.put("place", tPlan - tSnapshot);
        // The place phase split: the candidate read (SQL), the pin resolution over it, and
        // everything else (the group cuts, scoring, the epilogue, the waitlist tally and the
        // grants, all in memory).
        stats.phaseMs.put("candidates", tickCandidatesMs);
        stats.phaseMs.put("pins", tickPinsMs);
        stats.phaseMs.put("score", tPlan - tSnapshot - tickCandidatesMs - tickPinsMs);
        List<FrameBooking> planned = planBookings();
        if (planned == null)
            return dispatched; // interrupted mid-plan; abort before committing
        planned = trimOverFolderCeiling(planned, folderMaxCp, folderRunSeed, jobFolderCap);
        planned = trimOverLimitBudgets(planned, limitBudgets, layerLimits);
        long tRead = System.currentTimeMillis();
        stats.phaseMs.put("read", tRead - tPlan);
        tickPlanned = planned.size();

        // 4b. COMMIT the survivors and their resource accounting in host-aligned chunks, each
        // chunk one transaction, launched as it lands (commitInChunks). DispatchSupportService
        // is REQUIRED, so the batch joins the chunk's transaction rather than opening its own:
        // procs and the counters that mirror them commit together or not at all. Splitting them
        // let a crash in between leave procs whose cores were never added, while the release
        // path subtracts them regardless, and four of the five mirrors have no repair job to
        // undo that.
        List<FrameBooking> committed = commitInChunks(planned);
        long tCommit = System.currentTimeMillis();
        stats.phaseMs.put("commit", tCommit - tRead);
        stats.commitRetryTx = 2L * lastCommitSplits;
        stats.commitDroppedBookings = lastCommitDropped;
        recordCommitted(committed, stats);
        // Read live usage AFTER this tick's bookings landed. Reading at tick start
        // would sample the post-drain trough, where a fast-completing farm reads as
        // empty every time.
        if (maestroMetrics != null && maestroMetrics.isEnabled()) {
            try {
                readLiveShowUsage(stats);
            } catch (DataAccessException exception) {
                logger.warn("Maestro: live show usage read failed: " + exception.getMessage());
            }
            if (farmHealth != null)
                aggregateFarmHealth(groups, farmHealth.snapshot(), stats);
        }
        int dispatchedNow = committed.size();
        long tFlush = System.currentTimeMillis();
        stats.phaseMs.put("usage", tFlush - tCommit);
        long tTick = tFlush - tStart;
        if (tTick > 1000) {
            String breakdown = "drain=" + lastDrainMs + "ms, snapshot=" + (tSnapshot - tStart)
                    + "ms, place=" + (tPlan - tSnapshot) + "ms (candidates=" + tickCandidatesMs
                    + "ms, pins=" + tickPinsMs + "ms, score="
                    + (tPlan - tSnapshot - tickCandidatesMs - tickPinsMs) + "ms), read="
                    + (tRead - tPlan) + "ms, batchCommit=" + (tCommit - tRead) + "ms, usage="
                    + (tFlush - tCommit) + "ms | placements=" + lastPlacements + " planned="
                    + planned.size() + " committed=" + dispatchedNow + " splits=" + lastCommitSplits
                    + " dropped=" + lastCommitDropped;
            logger.info("Maestro tick breakdown: " + breakdown);
            // Production runs at WARN, so a slow tick carries its own breakdown there.
            if (tTick > slowTickWarnMs)
                logger.warn("Maestro slow tick: " + tTick + "ms | " + breakdown);
        }
        dispatched = dispatchedNow;

        sweepStaleReservationState(seenLayerIds);
        return dispatched;
    }

    /**
     * Commit the tick's planned bookings and return the ones that landed. Expects each host's
     * bookings to be contiguous in planned, as planBookings emits them.
     *
     * Transactions hold at most {@link #commitChunkFrames} frames, cut on host boundaries so a
     * host's bookings always share one transaction (the capacity gate is per host). This bounds how
     * long host and stat rows stay locked, and lets procs launch while later chunks are still
     * committing. Each chunk carries its own resource deltas, so procs and their mirrors land
     * together or not at all. A failing chunk costs only the bookings of the host that causes it
     * (commitContained), never the tick. A leader that loses the planning lock stops before its
     * next chunk; the remaining frames stay WAITING for the next leader.
     */
    List<FrameBooking> commitInChunks(List<FrameBooking> planned) {
        List<FrameBooking> committed = new ArrayList<>();
        SplitBudget budget = new SplitBudget(commitSplitMaxTx);
        int start = 0;
        while (start < planned.size()) {
            if (!leaderAlive()) {
                logger.warn("Maestro: leadership lost mid-commit, " + (planned.size() - start)
                        + " planned frames left for the next leader");
                demote();
                break;
            }
            int end = chunkEnd(planned, start);
            committed.addAll(commitContained(planned.subList(start, end), budget));
            start = end;
        }
        lastCommitSplits = budget.splits;
        lastCommitDropped = budget.dropped;
        return committed;
    }

    /**
     * End (exclusive) of the chunk that starts at start: {@link #commitChunkFrames} bookings,
     * extended to the last booking of the host that straddles the cut, so a host's bookings never
     * span two transactions.
     */
    static int chunkEnd(List<FrameBooking> planned, int start) {
        int end = Math.min(start + commitChunkFrames, planned.size());
        while (end < planned.size()
                && planned.get(end).proc.getHostId().equals(planned.get(end - 1).proc.getHostId()))
            end++;
        return end;
    }

    /**
     * The host boundary nearest the middle of piece, or -1 when every booking is on one host. Never
     * splits a host's bookings, for the same reason as chunkEnd.
     */
    static int hostAlignedMid(List<FrameBooking> piece) {
        int pieceSize = piece.size();
        int target = pieceSize / 2;
        int best = -1;
        for (int index = 1; index < pieceSize; index++) {
            if (!piece.get(index).proc.getHostId().equals(piece.get(index - 1).proc.getHostId())
                    && (best < 0 || Math.abs(index - target) < Math.abs(best - target)))
                best = index;
        }
        return best;
    }

    /**
     * The retry transactions one commitInChunks may spend, shared by all its chunks, and the tally
     * of what splitting did. A healthy tick spends nothing. A split costs two transactions, so
     * isolating a bad booking in a chunk of H hosts costs about 2 * log2(H); once the budget is
     * spent a failing piece is dropped whole. This bounds a tick in which every booking fails (a
     * trigger rejecting everything, a database gone away).
     */
    static final class SplitBudget {
        private int left;
        int splits;
        int dropped;

        SplitBudget(int retryTx) {
            this.left = retryTx;
        }

        /** Take the two transactions of one split; false, and nothing taken, when short. */
        boolean takeSplit() {
            if (left < 2)
                return false;
            left -= 2;
            splits++;
            return true;
        }
    }

    /**
     * Commit one piece of the plan, containing any failure to the bookings that cause it, and
     * return the bookings that landed.
     *
     * A piece whose transaction fails is split at the host boundary nearest its middle and each
     * half committed the same way, until the failure is isolated to one host's bookings, which are
     * dropped (dropPiece) and stay WAITING; every other booking lands this tick. Retrying is safe
     * because a failed transaction rolled back whole and the retry passes the same frame-version
     * guard. Deltas a failed attempt left buffered are discarded, so a retry credits only its own
     * procs. Once the split budget is spent or leadership is lost, a failing piece is dropped
     * whole. The in-memory host snapshot stays decremented either way; the next tick's snapshot
     * corrects it.
     */
    List<FrameBooking> commitContained(List<FrameBooking> piece, SplitBudget budget) {
        List<FrameBooking> won;
        try {
            won = commitPiece(piece);
        } catch (RuntimeException exception) {
            // Only the transaction is retried: the publish and launch of a committed
            // piece run outside it, below, so their failures never re-commit anything.
            discardResourceDeltas();
            int mid = hostAlignedMid(piece);
            String why = mid < 0 ? "one host, nothing to split"
                    : !leaderAlive() ? "leadership lost, not retrying without the lock"
                            : !budget.takeSplit() ? "the tick's split budget is spent" : null;
            if (why != null) {
                dropPiece(piece, exception, why, budget);
                return Collections.emptyList();
            }
            won = new ArrayList<>(commitContained(piece.subList(0, mid), budget));
            won.addAll(commitContained(piece.subList(mid, piece.size()), budget));
            return won;
        }
        launchPiece(won);
        return won;
    }

    /**
     * Commit one piece in its own transaction: the frame starts, the procs and the resource deltas
     * that mirror them, together or not at all. A failed transaction propagates to the caller,
     * which splits or drops the piece.
     */
    List<FrameBooking> commitPiece(List<FrameBooking> piece) {
        final List<FrameBooking> chunk = new ArrayList<>(piece);
        return txTemplate().execute(status -> {
            List<FrameBooking> won = dispatchSupport.startFramesAndProcsBatch(chunk);
            applyResourceDeltas(won);
            return won;
        });
    }

    /**
     * Publish and launch a committed piece, outside its transaction: a slow publish never extends
     * the lock window, and the frames start while the later pieces are still committing instead of
     * after the last. A failed event publish is logged and never keeps a committed piece from its
     * launch.
     */
    void launchPiece(List<FrameBooking> won) {
        try {
            dispatchSupport.publishFrameStartedEvents(won);
        } catch (RuntimeException exception) {
            logger.warn("Maestro: frame-started events of a chunk of " + won.size()
                    + " bookings failed: " + exception.getMessage());
        }
        launchCommitted(won);
    }

    /**
     * Give up on a piece whose commit failed and is not split further: its frames stay WAITING for
     * the next tick. One WARN names the hosts, the jobs, why there was no split and the root cause
     * (the SQL error behind the wrappers), so a commit-time gate Maestro does not model is visible
     * by name.
     */
    private void dropPiece(List<FrameBooking> piece, RuntimeException failure, String why,
            SplitBudget budget) {
        budget.dropped += piece.size();
        Set<String> hosts = new LinkedHashSet<>();
        Set<String> jobs = new LinkedHashSet<>();
        for (FrameBooking booking : piece) {
            hosts.add(booking.proc.hostName != null ? booking.proc.hostName
                    : booking.proc.getHostId());
            jobs.add(booking.proc.getJobId() != null ? booking.proc.getJobId()
                    : booking.frame.getJobId());
        }
        logger.warn("Maestro: commit of " + piece.size() + " booking(s) on host(s) " + hosts
                + " for job(s) " + jobs + " failed and rolled back (" + why + "); its frames"
                + " wait for the next tick: " + rootCauseMessage(failure));
    }

    /**
     * The message of the deepest cause of a commit failure, past the DAO and Spring wrappers and
     * following a JDBC batch failure's chained SQLException, so the log names the statement that
     * failed.
     */
    static String rootCauseMessage(Throwable cause) {
        Throwable cur = cause;
        Set<Throwable> seen = new HashSet<>();
        while (cur != null && seen.add(cur)) {
            Throwable next = null;
            if (cur instanceof SQLException && ((SQLException) cur).getNextException() != null)
                next = ((SQLException) cur).getNextException();
            else if (cur.getCause() != null && cur.getCause() != cur)
                next = cur.getCause();
            if (next == null)
                break;
            cur = next;
        }
        if (cur == null)
            return String.valueOf(cause);
        String msg = cur.getMessage();
        return cur.getClass().getSimpleName() + ": " + (msg != null ? msg.trim() : "");
    }

    /**
     * Plan one (host, layer) pairing: each of its slices of the layer's tick-wide frame read,
     * booked at the size Maestro scored it with (layerResize; absent means the layer's own ask).
     * Tracks layers that keep planning zero bookable frames and warns after
     * maestro.plan_zero_warn_ticks ticks in a row.
     */
    private List<FrameBooking> planLayerOnHost(DispatchHost host, String hostId,
            PlannedLayer planned, int planZeroWarnTicks) {
        String layerId = planned.layerId;
        long[] resize = layerResize.get(layerId);
        long effMemKb = resize != null ? resize[1] : 0;
        // No recorded slice: the whole read, at the layer's own cores.
        List<int[]> slices = planSliceByHostLayer.getOrDefault(hostId + "|" + layerId,
                List.of(new int[] {0, planned.frames.size(), 0}));
        List<FrameBooking> got = new ArrayList<>();
        for (int[] slice : slices) {
            // {offset, count, cores}: the cores are the slice's own (see submitCommit).
            got.addAll(dispatcher.planHost(host, slice[2], effMemKb,
                    planned.slice(slice[0], slice[1])));
        }
        if (got.isEmpty()) {
            int streak = planZeroStreak.merge(layerId, 1, Integer::sum);
            if (streak % planZeroWarnTicks == 0) {
                logger.warn("Maestro: layer " + layerId + " planned " + streak
                        + " consecutive ticks (last host " + host.getName()
                        + ") but planHost found 0 bookable frames each time."
                        + " A dispatch-query gate Maestro does not model is"
                        + " rejecting it (thread mode, limit, local booking, ...):"
                        + " enable DEBUG on this class and read the 'Maestro"
                        + " unplaced'/'explain' lines for the candidate-side view.");
            }
        } else {
            planZeroStreak.remove(layerId);
        }
        return got;
    }

    /**
     * One line per tick for the plan reads that threw, host tasks and layer slices together, with
     * the first cause: a database that fails under every host would otherwise write one warning per
     * host and layer every tick. The window count goes on the stat line (planFail).
     */
    private void reportPlanFailures(int failedTasks, int tasks, int failedLayers, String cause) {
        int failed = failedTasks + failedLayers;
        if (failed == 0)
            return;
        summaryPlanFailures += failed;
        logger.warn("Maestro: " + failedTasks + " of " + tasks + " host plans and " + failedLayers
                + " layer plans failed this tick, the rest stand; first cause: " + cause);
    }

    /**
     * Turn this tick's placements into bookings: read each planned layer's frames and build procs
     * in memory, with no database writes. Returns the bookings with each host's contiguous, or null
     * if interrupted, in which case the caller abandons the tick before committing.
     *
     * Runs on the read pool. A layer costs one frame read per tick however many hosts it was placed
     * on, and each (host, layer) slice takes a disjoint part of it, so parallel host tasks never
     * share a frame. A host is planned serially within one task because planning decrements its
     * idle capacity; different hosts plan concurrently. A failure costs only its own layer's or
     * host's bookings and is reported once per tick (reportPlanFailures). A layer that keeps
     * planning zero bookable frames is warned: a commit-time gate Maestro does not model would
     * otherwise starve it silently.
     */
    List<FrameBooking> planBookings() {
        int planZeroWarnTicks = env.getProperty("maestro.plan_zero_warn_ticks", Integer.class, 40);
        lastPlacements = 0;
        Set<String> plannedLayerIds = new HashSet<>();
        for (List<String> ls : plannedByHost.values()) {
            lastPlacements += ls.size();
            plannedLayerIds.addAll(ls);
        }
        AtomicInteger failedLayers = new AtomicInteger();
        AtomicReference<String> firstCause = new AtomicReference<>();

        Map<String, PlannedLayer> layers =
                readPlannedLayers(plannedLayerIds, failedLayers, firstCause);
        if (layers == null) {
            plannedByHost.clear();
            return null;
        }

        List<Callable<List<FrameBooking>>> tasks = new ArrayList<>(plannedByHost.size());
        for (Map.Entry<String, List<String>> entry : plannedByHost.entrySet()) {
            final String hostId = entry.getKey();
            final List<String> layerIds = entry.getValue();
            tasks.add(() -> {
                List<FrameBooking> out = new ArrayList<>();
                DispatchHost host = hostManager.getDispatchHost(hostId);
                // A host whose launches keep ending with unknown outcomes is not
                // booked: the launch would cost a deadline and a confirmation.
                if (rqdClient != null && rqdClient.isLaunchBreakerOpen(host.getName())) {
                    logger.info(
                            "Maestro: skipping " + host.getName() + ", its launch breaker is open");
                    return out;
                }
                for (String layerId : layerIds) {
                    // One layer is one unit: a layer whose read failed (deleted
                    // mid-tick) costs its own slices on every host, never the
                    // host's other layers; the failure was counted once, above.
                    PlannedLayer planned = layers.get(layerId);
                    if (planned == null)
                        continue;
                    try {
                        out.addAll(planLayerOnHost(host, hostId, planned, planZeroWarnTicks));
                    } catch (RuntimeException ex) {
                        failedLayers.incrementAndGet();
                        firstCause.compareAndSet(null, "layer " + layerId + " on host "
                                + host.getName() + ": " + ex.getMessage());
                    }
                }
                return out;
            });
        }
        plannedByHost.clear();

        List<FrameBooking> planned = new ArrayList<>();
        int failedTasks = 0;
        try {
            for (Future<List<FrameBooking>> future : readPool.invokeAll(tasks)) {
                try {
                    planned.addAll(future.get());
                } catch (ExecutionException ee) {
                    failedTasks++;
                    firstCause.compareAndSet(null, "host task: "
                            + (ee.getCause() != null ? ee.getCause().toString() : ee.toString()));
                }
            }
            reportPlanFailures(failedTasks, tasks.size(), failedLayers.get(), firstCause.get());
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            return null;
        }
        // Streaks matter only while Maestro keeps choosing the layer; drop entries for
        // layers not planned this tick so the map tracks live pathologies, not vanished work.
        planZeroStreak.keySet().retainAll(plannedLayerIds);
        return planned;
    }

    /**
     * A planned layer's once-per-tick read: its next waiting frames in dispatch order, as many as
     * every placement of it this tick accounted for. Each (host, layer) slice takes a disjoint
     * sub-list by its offset (submitCommit), so parallel host tasks never share a frame.
     */
    static final class PlannedLayer {
        final String layerId;
        final List<DispatchFrame> frames;

        PlannedLayer(String layerId, List<DispatchFrame> frames) {
            this.layerId = layerId;
            this.frames = frames;
        }

        /** The slice [offset, offset + count), clipped to the frames the read returned. */
        List<DispatchFrame> slice(int offset, int count) {
            int from = Math.min(Math.max(offset, 0), frames.size());
            int to = Math.min(from + Math.max(count, 0), frames.size());
            return frames.subList(from, to);
        }
    }

    /**
     * Round one of planBookings: each planned layer's next waiting frames, as many as this tick's
     * placements accounted for, read once per layer on the read pool. A layer whose read fails is
     * left out, so its slices plan nothing, and is counted in failedLayers. Returns null if
     * interrupted.
     */
    private Map<String, PlannedLayer> readPlannedLayers(Set<String> layerIds,
            AtomicInteger failedLayers, AtomicReference<String> firstCause) {
        List<Callable<PlannedLayer>> reads = new ArrayList<>(layerIds.size());
        for (String layerId : layerIds) {
            reads.add(() -> {
                int wanted = plannedFramesByLayer.getOrDefault(layerId, 0);
                List<DispatchFrame> frames =
                        wanted > 0 ? dispatchSupport.findNextDispatchFrames(layerId, wanted)
                                : Collections.emptyList();
                return new PlannedLayer(layerId, frames);
            });
        }
        Map<String, PlannedLayer> out = new HashMap<>();
        try {
            for (Future<PlannedLayer> future : readPool.invokeAll(reads)) {
                try {
                    PlannedLayer planned = future.get();
                    out.put(planned.layerId, planned);
                } catch (ExecutionException ee) {
                    failedLayers.incrementAndGet();
                    firstCause.compareAndSet(null, "layer read: "
                            + (ee.getCause() != null ? ee.getCause().toString() : ee.toString()));
                }
            }
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
            return null;
        }
        return out;
    }

    /**
     * Size each candidate's cores and memory to what its frames actually need, before placement, so
     * scoring, fit, caps and booking all use one shape.
     *
     * Memory is the larger of the layer's ask and the largest rss any of its frames has reported.
     * Threadable layers book {@code round(memory / memPerCoreKb)} cores, never below the ask and
     * never above the layer's max or {@code maxHostCores}. A layer tagged {@code manual} keeps its
     * ask, as under cue-layer-man.
     *
     * A layer that still sizes to 1 core with no rss seen yet is unproven ({@code rssProven =
     * false}): at most {@link #probeFrames} of its frames run until its rss is known. A layer that
     * already finished that many frames without reporting rss ends too fast to sample and is
     * treated as proven.
     */
    static void sizeFromMemory(List<LayerCandidate> candidates, long memPerCoreKb, int maxHostCores,
            Map<String, long[]> resizeOut) {
        for (LayerCandidate layer : candidates) {
            if (layer.layerCoresMin <= 0) {
                layer.rssProven = true;
                continue;
            }
            boolean coresFollowMemory = layer.threadable && memPerCoreKb > 0 && !layer.manual;
            long memKb = Math.max(layer.layerMemMin, layer.layerMaxRssKb);
            int cores = coresFollowMemory ? coresForMemory(layer, memKb, memPerCoreKb, maxHostCores)
                    : layer.layerCoresMin;
            layer.rssProven = layer.layerMaxRssKb > 0 || !coresFollowMemory
                    || cores != CORE_POINTS_PER_CORE || layer.frameSuccessCount >= probeFrames;
            if (cores != layer.layerCoresMin || memKb != layer.layerMemMin) {
                resizeOut.put(layer.layerId, new long[] {cores, memKb});
                layer.layerCoresMin = cores;
                layer.layerMemMin = memKb;
            }
        }
    }

    /**
     * round(memKb / memPerCoreKb) cores, never below the ask, capped by the layer's and host's max.
     */
    private static int coresForMemory(LayerCandidate layer, long memKb, long memPerCoreKb,
            int maxHostCores) {
        int cores = (int) Math.round(memKb / (double) memPerCoreKb) * CORE_POINTS_PER_CORE;
        if (layer.layerCoresMax > 0 && cores > layer.layerCoresMax)
            cores = layer.layerCoresMax;
        if (cores > maxHostCores)
            cores = maxHostCores;
        return Math.max(layer.layerCoresMin, cores);
    }

    /**
     * The group's own memory-per-core in KB (whole cores), the self-derived sizing metric: total
     * bookable memory over total cores of the group's hosts. On a 3.5G-per-core farm an 18G layer
     * sizes to 5 cores; buy different machines and the figure follows, with no configuration.
     */
    static long memPerWholeCoreKb(List<BookableHost> hosts) {
        long mem = 0;
        long cores = 0;
        for (BookableHost host : hosts) {
            mem += host.memTotal;
            cores += host.coresTotal;
        }
        long wholeCores = cores / 100;
        return wholeCores > 0 ? mem / wholeCores : 0;
    }

    /** Fold the committed bookings into the per-show throughput tally. */
    private void recordCommitted(List<FrameBooking> committed, MaestroMetrics.TickStats stats) {
        for (FrameBooking booking : committed)
            stats.framesByShow.merge(booking.frame.show, 1, Integer::sum);
    }

    /**
     * Mirror the committed procs' cores and gpus into the subscription, layer, job, folder and
     * point counters. Must run inside the booking transaction: a failure rolls the bookings back
     * with it, so a mirror is never applied without its procs and nothing is left over to retry.
     */
    private void applyResourceDeltas(List<FrameBooking> committed) {
        if (committed.isEmpty()) {
            return;
        }
        List<VirtualProc> procs = new ArrayList<>(committed.size());
        for (FrameBooking booking : committed)
            procs.add(booking.proc);
        accumulateResourceDeltas(procs);
        flushResourceDeltas();
    }

    /**
     * Hand each committed booking to the launch pool (launchOne), stamped with its commit time, so
     * the tick never waits on RQD. Also advances cache warmth: every commit moves its host's
     * booking odometer forward, displacing older cache, while a layer returning to its own warm
     * host refreshes its entry instead.
     */
    private void launchCommitted(List<FrameBooking> committed) {
        if (localityEnabled && localityWindowFrames > 0) {
            for (FrameBooking booking : committed) {
                long odo = bookingsByHost.merge(booking.proc.getHostId(), 1L, Long::sum);
                if (booking.proc.getLayerId() != null) {
                    String key = booking.proc.getHostId() + "|" + booking.proc.getLayerId();
                    if (warmthByHostLayer.containsKey(key)) {
                        warmthByHostLayer.put(key, odo);
                    }
                }
            }
        }
        long now = System.currentTimeMillis();
        for (FrameBooking booking : committed) {
            final FrameBooking fb = booking;
            fb.committedMs = now;
            launchPool.execute(() -> launchOne(fb));
        }
    }

    /**
     * How long a committed booking may wait in the launch queue before it is rolled back unsent:
     * half the orphan age (ProcDao.ORPHAN_AGE_PROPERTY). At the orphan age the maintenance pass
     * releases a proc that never pinged and the next tick rebooks its frame, so a later launch
     * would run the frame twice; the other half leaves the pass cadence, the RPC and the first host
     * report their time. A null environment (bare unit tests) uses the default orphan age.
     */
    static long launchMaxAgeMs(Environment env) {
        long ageS =
                env == null ? ProcDao.DEFAULT_ORPHAN_AGE_SECONDS : ProcDao.orphanAgeSeconds(env);
        return ageS * 1000L / 2;
    }

    /**
     * Launch one committed booking on its host, on a launch-pool thread. A failure is this launch's
     * alone; the pool goes on with the next.
     *
     * A booking is never released while its frame may be running: an RPC that failed without proof
     * the frame never started (RqdLaunchUnknownOutcomeException) is confirmed not running twice
     * through DispatchSupport before any rollback, the legacy dispatcher's double-run guard. A
     * definite failure rolls back (rollbackLaunch). A booking that waited longer than
     * {@link #launchMaxAgeMs}, or whose host's launch breaker opened since the plan, is rolled back
     * unsent and without a kill, since the maintenance pass may already be releasing its proc.
     */
    void launchOne(FrameBooking fb) {
        long waitedMs = fb.committedMs > 0 ? System.currentTimeMillis() - fb.committedMs : 0;
        if (waitedMs > launchMaxAgeMs) {
            logger.warn("Maestro: launch of " + fb.proc.getName() + " on frame "
                    + fb.frame.getFrameId() + " waited " + waitedMs / 1000
                    + "s in the queue; rolling the booking back unsent");
            rollbackLaunch(fb, false);
            return;
        }
        if (rqdClient != null && rqdClient.isLaunchBreakerOpen(fb.proc.hostName)) {
            logger.info("Maestro: launch breaker open for " + fb.proc.hostName
                    + "; rolling the booking of frame " + fb.frame.getFrameId() + " back unsent");
            rollbackLaunch(fb, false);
            return;
        }
        try {
            dispatchSupport.runFrame(fb.proc, fb.frame);
        } catch (RqdLaunchUnknownOutcomeException exception) {
            logger.warn("Maestro: launch outcome unknown for " + fb.proc.getName() + " on frame "
                    + fb.frame.getFrameId() + ", keeping the booking until resolved: "
                    + exception.getMessage());
            try {
                dispatchSupport.resolveUnknownLaunchOutcomeAsync(fb.proc, fb.frame);
            } catch (RuntimeException re) {
                logger.warn("Maestro: launch outcome resolution failed for " + fb.frame.getFrameId()
                        + ", booking kept: " + re.getMessage());
            }
        } catch (RuntimeException exception) {
            logger.warn("Maestro: RQD launch failed for " + fb.proc.getName() + " on frame "
                    + fb.frame.getFrameId() + ": " + exception.getMessage()
                    + ", unbooking and clearing frame");
            rollbackLaunch(fb, true);
        }
    }

    /**
     * Undo a booking whose launch failed: unbook the proc and clear the frame on the version this
     * tick committed. The frame is killed on the host only when the launch was sent and the clear
     * matched; a clear that matched nothing means the frame was released and rebooked since, and a
     * kill by host and frame would hit its new run. A partial cleanup is logged and left to the
     * proc sweep.
     */
    private void rollbackLaunch(FrameBooking fb, boolean sent) {
        try {
            dispatchSupport.unbookProc(fb.proc);
            boolean cleared = dispatchSupport.clearFrame(fb.frame);
            if (sent && cleared)
                rqdClient.killFrame(fb.proc, "launch failed during scheduler dispatch");
        } catch (RuntimeException ce) {
            logger.warn("Maestro: launch-failure cleanup partial for " + fb.frame.getFrameId()
                    + ": " + ce.getMessage());
        }
    }

    // ---- leader lock ------------------------------------------------------

    /**
     * Whether this Cuebot is the planning leader for this tick, taking leadership if it is free.
     *
     * Leadership is sticky: once won, the session-scoped advisory lock is held on a dedicated
     * connection across ticks and never re-acquired (it is re-entrant and would need matching
     * unlocks). A leader demotes itself when that connection is lost (see leaderAlive); a standby
     * retries every tick. The per-tick liveness probe doubles as a keepalive, so a firewall or NAT
     * idle timeout never drops the lock connection. No leadership is taken while onShutdown runs,
     * so a tick that raced the shutdown cannot retake the lock it just released.
     */
    boolean ensureLeadership() {
        if (shuttingDown)
            return false;
        Connection held = leaderConn;
        if (held != null) {
            try {
                if (held.isValid(1)) {
                    return true;
                }
            } catch (SQLException exception) {
                // treated as dead below
            }
            logger.warn("Maestro: planning-lock connection lost; demoting to standby");
            demote();
            return false;
        }
        Connection conn = null;
        try {
            conn = openLeaderConnection();
            if (maestroDao.tryAcquireSchedulerLock(conn)) {
                leaderConn = conn;
                logger.info("Maestro: acquired planning leadership (sticky)");
                return true;
            }
            conn.close();
            return false;
        } catch (SQLException exception) {
            logger.warn("Maestro: leadership probe failed: " + exception.getMessage());
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
     * Open a dedicated connection for the leadership lock, outside the connection pool, built from
     * the configured JDBC url and credentials. A pooled connection held across ticks would be
     * reaped on idle timeout or flagged as a leak, silently releasing the advisory lock.
     */
    private Connection openLeaderConnection() throws SQLException {
        String url = env.getProperty("datasource.cue-data-source.jdbc-url");
        String user = env.getProperty("datasource.cue-data-source.username");
        String pass = env.getProperty("datasource.cue-data-source.password");
        Connection connection = java.sql.DriverManager.getConnection(url, user, pass);
        connection.setAutoCommit(true);
        return connection;
    }

    /**
     * Whether this Cuebot still holds the planning lock: the lock connection is alive and no
     * shutdown is under way. A closed connection is a definite loss and demotes at once. A failed
     * liveness probe is ambiguous (a dead server or merely a loaded one), so only
     * {@link #leaderProbeStrikes} consecutive misses demote: one blip must not cost every live
     * reservation and all cache warmth, while a truly dead session at worst commits one more chunk,
     * which the frame-version guards fence off from the next leader.
     */
    private boolean leaderAlive() {
        if (shuttingDown) {
            return false;
        }
        Connection held = leaderConn;
        if (held == null) {
            return false;
        }
        boolean ok;
        try {
            if (held.isClosed()) {
                leaderProbeMisses = 0;
                return false;
            }
            ok = held.isValid(1);
        } catch (SQLException exception) {
            ok = false;
        }
        if (ok) {
            leaderProbeMisses = 0;
            return true;
        }
        if (++leaderProbeMisses < leaderProbeStrikes) {
            logger.warn("Maestro: leadership probe miss " + leaderProbeMisses + " of "
                    + leaderProbeStrikes + "; keeping the lock");
            return true;
        }
        leaderProbeMisses = 0;
        return false;
    }

    /**
     * Demote, on the tick thread: release the lock and forget what only a leader may hold. The next
     * leader plans from the database, not from this Maestro's memory: reservations, blocked debt,
     * warmth and odometers go with the lock (forgetLeaderMemory).
     */
    void demote() {
        closeLeaderConn();
        forgetLeaderMemory();
    }

    /** The planner's memory, cleared on demotion. Tick thread only: these are plain maps. */
    void forgetLeaderMemory() {
        reservations.clear();
        blockedDebtMs.clear();
        lastSeenMs.clear();
        warmthByHostLayer.clear();
        bookingsByHost.clear();
    }

    /**
     * Release (if the connection is still alive) and close the leadership connection. Only the
     * lock: the memory goes on the tick thread (demote), never from the shutdown thread.
     */
    void closeLeaderConn() {
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
     * Bean lifecycle hook: hand leadership over and launch what was already committed.
     *
     * Marks the shutdown first, so a tick that raced it takes no leadership and commits no further
     * chunk. Releases the lock, so a standby takes over without waiting for the socket teardown.
     * Waits up to maestro.shutdown_tick_wait_seconds for a tick in flight, then up to
     * maestro.shutdown_launch_drain_seconds for the launch pool to drain: every committed booking
     * is RUNNING in the database, and its queued launch is the only thing that will start it. A
     * launch that misses the drain is an orphan the proc sweep resets, as after a crash. The
     * planner's memory belongs to the tick thread and is never touched here.
     */
    public void onShutdown() {
        shuttingDown = true;
        closeLeaderConn();
        awaitTickEnd();
        drainLaunchPool();
    }

    /**
     * Wait, at most {@link #tickEndWaitMaxSeconds}, for a tick in flight to finish, so its
     * committed chunks reach the launch pool before the pool closes. Shutdown only.
     */
    private void awaitTickEnd() {
        long deadline = System.currentTimeMillis() + 1000L * tickEndWaitMaxSeconds;
        while (tickInFlight.get() && System.currentTimeMillis() < deadline) {
            try {
                Thread.sleep(100);
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
                return;
            }
        }
        if (tickInFlight.get()) {
            logger.warn("Maestro: a tick is still in flight at shutdown; the launches it has not"
                    + " handed to the pool are left to the proc sweep");
        }
    }

    /**
     * Stop accepting launches and wait, at most {@link #launchDrainMaxSeconds}, for the queued ones
     * to run. Shutdown only; a launch left behind is an orphan the proc sweep resets.
     */
    private void drainLaunchPool() {
        ExecutorService pool = launchPool;
        if (pool == null)
            return;
        pool.shutdown();
        try {
            if (!pool.awaitTermination(launchDrainMaxSeconds, TimeUnit.SECONDS)) {
                logger.warn("Maestro: launch pool did not drain within " + launchDrainMaxSeconds
                        + "s; the launches still queued are left to the proc sweep");
            }
        } catch (InterruptedException exception) {
            Thread.currentThread().interrupt();
        }
    }

    /**
     * Release the planning lock on conn. A failure is harmless: a dropped connection already took
     * the lock with it.
     */
    private void releaseLeaderLock(Connection conn) {
        try {
            maestroDao.releaseSchedulerLock(conn);
        } catch (SQLException exception) {
            // If the connection dropped, the backend session ended and the
            // lock was released automatically.
            logger.debug("Maestro: pg_advisory_unlock failed (probably connection drop): "
                    + exception.getMessage());
        }
    }

    // ---- snapshot reads ---------------------------------------------------

    /**
     * Every schedulable host (UP and OPEN), busy or idle: the tick's host snapshot. Each group's
     * idle subset for placement is derived from it in doTick.
     */
    /* package for tests */ List<BookableHost> readAllHosts() {
        return maestroDao.getSchedulableHosts();
    }

    /**
     * Fill the stats' cores-per-show and running-frame count from the procs alive right now, for
     * the shows this scheduler plans. Read from the proc table each tick rather than tallied from
     * bookings and completions: a tally starts empty on a new leader and never subtracts procs
     * released outside the drain (kills, retries, lost hosts, failed launches), so it drifts.
     */
    /* package for tests */ void readLiveShowUsage(MaestroMetrics.TickStats stats) {
        for (MaestroDao.ShowUsage usage : maestroDao.getLiveShowUsage(MaestroMode.facility(env))) {
            stats.coresByShow.put(usage.showName, usage.corePoints / (double) CORE_POINTS_PER_CORE);
            stats.runningFrames += usage.frames;
        }
    }

    /**
     * Which layers have at least one live proc on each host: the locality signal behind the
     * locality bonus. Refreshes hostLayerFrames and layerRunningFrames from the same snapshot, so
     * the per-host layer cap and the probe gate agree with it, and resets the tick's per-layer plan
     * scratch. Empty when neither locality nor the per-host layer cap is on.
     */
    private Map<String, Set<String>> readHostLayerAffinity() {
        Map<String, Set<String>> affinity = new HashMap<>();
        Map<String, Integer> counts = new HashMap<>();
        hostLayerFrames = counts;
        layerRunningFrames = new HashMap<>();
        layerProbeUsed.clear();
        layerResize.clear();
        plannedFramesByLayer.clear();
        planSliceByHostLayer.clear();
        if (!localityEnabled && layerHostMaxFrac <= 0)
            return affinity;
        for (MaestroDao.HostLayerFrames running : maestroDao.getRunningFramesByHostLayer()) {
            String host = running.hostId;
            String layer = running.layerId;
            affinity.computeIfAbsent(host, key -> new HashSet<>()).add(layer);
            counts.put(host + "|" + layer, running.frames);
            layerRunningFrames.merge(layer, running.frames, Integer::sum);
        }
        return affinity;
    }

    /**
     * The soft cap's yield test: whether another candidate of this group could still use host now.
     *
     * The per-host layer cap is a contention rule among peers: while work of equal or higher
     * priority waits for a machine, no layer takes more than its share of it. It holds only while
     * some other layer has waiting frames, fits the host as it stands, is under its own per-host
     * cap there and is not held by its job cap, show burst or a full limit. With nobody else able
     * to use the host, holding the cap would only strand it. Candidates later in the draw count as
     * waiting, so the yield never runs ahead of their turn.
     */
    private boolean othersWant(BookableHost host, LayerCandidate candidate,
            List<LayerCandidate> candidates, String groupAllocId, Map<String, Integer> jobCoresUsed,
            Map<String, Integer> showCoresUsed, Map<String, LimitBudget> limitBudgets,
            Map<String, Integer> limitUsed, Map<String, Set<String>> limitSeats) {
        for (LayerCandidate other : candidates) {
            if (other == candidate || other.waitingFrameCount <= 0 || !pinsAllow(other, host)
                    || !fitsOnHost(other, host))
                continue;
            if (lotteryWeight(other) < lotteryWeight(candidate))
                continue;
            if (hostLayerFrames.getOrDefault(host.hostId + "|" + other.layerId,
                    0) >= layerHostCap(host, other))
                continue;
            if (jobCoresUsed.getOrDefault(other.jobId, other.jobCoresInUse)
                    + other.layerCoresMin > other.jobMaxCores)
                continue;
            if (showCoresUsed.getOrDefault(subKey(other.showId, groupAllocId), other.showCoresInUse)
                    + other.layerCoresMin > other.showBurstCores)
                continue;
            if (limitBlocks(host, other, limitBudgets, limitUsed, limitSeats))
                continue;
            return true;
        }
        return false;
    }

    /**
     * Whether a gating limit keeps candidate other off host right now: a FRAME limit whose
     * tick-wide budget is spent, or a HOST limit with no seat left that the host does not already
     * hold. A limit with no budget entry does not gate (see resolveLimitBudgets).
     */
    private static boolean limitBlocks(BookableHost host, LayerCandidate other,
            Map<String, LimitBudget> limitBudgets, Map<String, Integer> limitUsed,
            Map<String, Set<String>> limitSeats) {
        if (other.limitIds == null)
            return false;
        for (String limId : other.limitIds) {
            LimitBudget budget = limitBudgets.get(limId);
            if (budget == null)
                continue;
            if (budget.hostBased) {
                Set<String> seats = limitSeats.getOrDefault(limId, budget.seats);
                if (!seats.contains(shortHostName(host.hostName)) && seats.size() >= budget.seatCap)
                    return true;
            } else if (limitUsed.getOrDefault(limId, 0) >= budget.usable) {
                return true;
            }
        }
        return false;
    }

    /**
     * Most frames of candidate one host may hold under the per-host layer cap:
     * maestro.layer_host_max_frac of the host's cores, never below {@link #layerHostCapMinFrames}
     * so small hosts still anchor a cache-warm batch. Uncapped when the fraction is 0 or the layer
     * reserves no cores.
     */
    private int layerHostCap(BookableHost host, LayerCandidate candidate) {
        if (layerHostMaxFrac <= 0 || candidate.layerCoresMin <= 0)
            return Integer.MAX_VALUE;
        int byFrac = (int) ((layerHostMaxFrac * host.coresTotal) / candidate.layerCoresMin);
        return Math.max(layerHostCapMinFrames, byFrac);
    }

    /** Log the explain rows for a group that produced no candidates. DEBUG-gated by the caller. */
    private void explainGroupExclusions(HostSpecKey spec, int maxCoresTotalInGroup) {
        List<MaestroDao.GroupExclusion> exclusions = maestroDao.explainGroupExclusions(
                spec.tagsNormalized, spec.os, spec.pkFacility, spec.allThreadMode,
                maxCoresTotalInGroup, MaestroMode.facility(env), spec.pkAlloc);
        for (MaestroDao.GroupExclusion exclusion : exclusions) {
            logger.debug("Maestro explain " + spec + ": job=" + exclusion.jobName + " layer="
                    + exclusion.layerName + " prio=" + exclusion.priority + " tags='"
                    + exclusion.layerTags + "' tagOk=" + exclusion.tagOk + " osOk=" + exclusion.osOk
                    + " facOk=" + exclusion.facilityOk + " threadOk=" + exclusion.threadOk
                    + " hasSub=" + exclusion.hasSubscription + " underBurst=" + exclusion.underBurst
                    + " underJobCap=" + exclusion.underJobCap + " fitsCores=" + exclusion.fitsCores
                    + " hasWaiting=" + exclusion.hasWaiting + " folderOk=" + exclusion.folderOk
                    + " managedOk=" + exclusion.managedOk);
        }
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

    /**
     * Record which of these candidates are bound to gating limits, and load this tick's limit
     * budgets the first time any is.
     *
     * Budgets are read at most once per tick and shared by every group, so all groups judge a limit
     * by the same numbers. Mirroring {@code DispatchQuery.limitFilter}, a limit that is ADVISORY or
     * DISABLED, or whose external report is stale past its TTL, gets no budget entry: candidates
     * book through it exactly as under the legacy dispatcher. Tick-scoped and tick thread only.
     */
    /* package for tests */ void resolveLimitBudgets(List<LayerCandidate> candidates,
            Map<String, List<String>> layerLimits, Map<String, LimitBudget> limitBudgets) {
        boolean bound = false;
        for (LayerCandidate candidate : candidates) {
            if (candidate.limitIds == null)
                continue;
            layerLimits.put(candidate.layerId, candidate.limitIds);
            bound = true;
        }
        if (!bound || limitBudgetsResolved)
            return;
        limitBudgetsResolved = true;

        Map<String, Set<String>> holders = null;
        for (MaestroDao.LimitUsage row : maestroDao.getGatingLimitUsage()) {
            String id = row.limitId;
            String name = row.name;
            boolean hostBased = "HOST".equals(row.type);
            int soft = row.softValue;
            int max = row.maxValue;
            int usage = row.usage;
            if (hostBased) {
                if (holders == null)
                    holders = maestroDao.getHostLimitHolders();
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

    /**
     * May this host take a frame of a layer bound to HOST-type limits?
     *
     * Yes when, for every such limit, the host either already holds it (extra frames there are
     * free, they share the one checkout) or the limit still has a seat to give out. The seat set
     * includes holders the license server reports outside the cue, so an artist's workstation
     * occupies a seat here just as a render node does.
     */
    /* package for tests */ static boolean limitSeatsAllow(List<LimitBudget> pools,
            Map<String, Set<String>> limitSeats, BookableHost host) {
        String hostName = shortHostName(host.hostName);
        for (LimitBudget budget : pools) {
            Set<String> seats = limitSeats.get(budget.id);
            if (seats.contains(hostName))
                continue;
            if (seats.size() >= budget.seatCap)
                return false;
        }
        return true;
    }

    /** The normalized seat key: short hostname, lowercased, as limit_host stores it. */
    private static String shortHostName(String hostName) {
        if (hostName == null)
            return "";
        String lower = hostName.toLowerCase();
        int dot = lower.indexOf('.');
        return dot < 0 ? lower : lower.substring(0, dot);
    }

    /** {@code "a,b"} to {@code [a, b]}, blanks dropped. */
    public static List<String> splitIds(String csv) {
        List<String> out = new ArrayList<>(2);
        if (csv == null)
            return out;
        for (String part : csv.split(",")) {
            String id = part.trim();
            if (!id.isEmpty() && !out.contains(id))
                out.add(id);
        }
        return out;
    }

    /**
     * This group's candidates, cut from the tick's candidate read (see groupCandidates), at most
     * maestro.layer_candidates_per_group_max of them. Outside a tick (tests), reads the candidates
     * on demand.
     */
    /* package for tests */ List<LayerCandidate> readLayerCandidatesForGroup(HostSpecKey spec,
            int maxIdleInGroup) {
        int limit = env.getProperty("maestro.layer_candidates_per_group_max", Integer.class, 2000);
        TickCandidates tick = tickCandidates != null ? tickCandidates : readTickCandidates();
        if (tick.failure != null)
            throw tick.failure;
        return groupCandidates(spec, maxIdleInGroup, tick, limit, this::tagsMatch,
                ThreadLocalRandom.current());
    }

    /**
     * Read this tick's candidates once, before any group plans. A failed read is kept, so every
     * group counts it as a query error instead of retrying it.
     */
    private void loadTickCandidates() {
        long t0 = System.currentTimeMillis();
        try {
            tickCandidates = readTickCandidates();
        } catch (RuntimeException exception) {
            tickCandidates = new TickCandidates(exception);
        }
        tickCandidatesMs = System.currentTimeMillis() - t0;
    }

    /**
     * The tick's candidate read: every dispatchable layer of the shows this scheduler plans and
     * every subscription's usage, in the form groupCandidates and resolvePins cut.
     */
    /* package for tests */ TickCandidates readTickCandidates() {
        List<CandidateRow> rows = maestroDao.getCandidateRows(MaestroMode.facility(env));
        Map<String, long[]> subs = new HashMap<>();
        for (MaestroDao.SubscriptionUsage sub : maestroDao.getSubscriptions()) {
            subs.put(subKey(sub.showId, sub.allocId), new long[] {sub.cores, sub.burst, sub.size});
        }
        return new TickCandidates(rows, subs);
    }

    /** Whether a layer's tag regex admits a group's tags; see {@link #tagsMatch}. */
    interface TagMatcher {
        boolean matches(String groupTags, String layerTags);
    }

    /**
     * One host-spec group's candidates, cut in memory from the tick's candidate read with the
     * legacy per-group query's rules: the job's facility and OS match the group, the layer passes
     * the group's thread mode and fits its largest host, the show subscribes to the group's
     * allocation and is under its burst there, and the layer's tag regex matches the group's tags.
     * Pure. Yields one candidate per layer, carrying that subscription's figures; at most limit are
     * kept, drawn by the priority lottery (drawByPriority).
     */
    static List<LayerCandidate> groupCandidates(HostSpecKey spec, int maxIdleInGroup,
            TickCandidates tick, int limit, TagMatcher tags, Random random) {
        List<LayerCandidate> admitted = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (CandidateRow row : tick.rows) {
            LayerCandidate candidate = row.row;
            if (!Objects.equals(row.facilityId, spec.pkFacility))
                continue;
            if (!jobOsAllowed(row.jobOs, spec.os))
                continue;
            if (spec.allThreadMode && !candidate.threadable)
                continue;
            if (candidate.layerCoresMin > maxIdleInGroup)
                continue;
            long[] sub = tick.subscriptions.get(subKey(candidate.showId, spec.pkAlloc));
            if (sub == null || sub[0] >= sub[1])
                continue;
            if (!tags.matches(spec.tagsNormalized, row.tags))
                continue;
            if (!seen.add(candidate.layerId))
                continue;
            LayerCandidate out = candidate.copyForGroup();
            out.showCoresInUse = (int) sub[0];
            out.showBurstCores = (int) sub[1];
            out.showSizeCores = (int) sub[2];
            admitted.add(out);
        }
        return drawByPriority(admitted, limit, random);
    }

    /**
     * At most limit of admitted, drawn by priority lottery: each candidate draws {@code random^(1 /
     * priority^priorityExponent)} and the highest draws win, so a higher priority wins more of the
     * slots without shutting lower ones out. Shared by the group cut and the pins.
     */
    static List<LayerCandidate> drawByPriority(List<LayerCandidate> admitted, int limit,
            Random random) {
        double[] draws = new double[admitted.size()];
        for (int index = 0; index < draws.length; index++)
            draws[index] = Math.pow(random.nextDouble(),
                    1.0 / Math.pow(Math.max(admitted.get(index).priority, 1), priorityExponent));
        Integer[] order = new Integer[admitted.size()];
        for (int index = 0; index < order.length; index++)
            order[index] = index;
        Arrays.sort(order, (left, right) -> Double.compare(draws[right], draws[left]));
        List<LayerCandidate> out = new ArrayList<>(Math.min(limit, order.length));
        for (int index = 0; index < order.length && out.size() < limit; index++)
            out.add(admitted.get(order[index]));
        return out;
    }

    /**
     * The legacy os rule: a job with no os runs anywhere; otherwise it must appear exactly in the
     * host's comma-separated os list (host_stat.str_os, e.g. "rhel7,rhel9" mid-migration).
     */
    static boolean jobOsAllowed(String jobOs, String hostOs) {
        if (jobOs == null || jobOs.isEmpty())
            return true;
        if (hostOs == null)
            return false;
        for (String os : hostOs.split(","))
            if (os.equals(jobOs))
                return true;
        return false;
    }

    /**
     * Whether a layer's tag regex admits a group's tags, with the legacy query's semantics: {@code
     * groupTags ~* ('(?x)' || layerTags || '\\y')}, an expanded-mode, case-insensitive match
     * anywhere in the group's tags that ends on a word boundary. Results are remembered per tick
     * and patterns across ticks. A pattern Java cannot compile excludes its layers and is warned
     * once; the legacy query failed the whole group on it.
     */
    boolean tagsMatch(String groupTags, String layerTags) {
        if (layerTags == null)
            return false;
        String key = groupTags + '\0' + layerTags;
        Boolean hit = tagMatches.get(key);
        if (hit != null)
            return hit;
        Optional<Pattern> pattern = tagPatterns.computeIfAbsent(layerTags,
                tags -> Optional.ofNullable(compileTagPattern(tags)));
        boolean matched = pattern.isPresent() && pattern.get().matcher(groupTags).find();
        if (!pattern.isPresent() && warnedTagPatterns.add(layerTags))
            logger.warn("Maestro: layer tag regex " + layerTags + " does not compile; its layers"
                    + " are not candidates until the tags are fixed");
        tagMatches.put(key, matched);
        return matched;
    }

    /**
     * {@link #tagsMatch}'s pattern for one layer tag string, or null when it does not compile.
     * Postgres' word escapes map to Java's: \y, \m and \M to \b, \Y to \B.
     */
    static Pattern compileTagPattern(String layerTags) {
        String regex = layerTags.replace("\\y", "\\b").replace("\\m", "\\b").replace("\\M", "\\b")
                .replace("\\Y", "\\B");
        try {
            return Pattern.compile(regex + "\\b",
                    Pattern.COMMENTS | Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE);
        } catch (PatternSyntaxException exception) {
            return null;
        }
    }

    /**
     * EASY backfill deadline per reserved host: seconds from now until it is projected to free
     * enough cores for its reserving layer. A frame may borrow the host only if it finishes by then
     * (see {@link #backfillAllows}). Empty when backfill is off or nothing is reserved.
     *
     * Each running proc is projected to finish at its layer's average successful runtime minus its
     * elapsed time; the deadline is when, taking procs soonest-first, enough cores have freed to
     * cover the owner's deficit.
     *
     * Conservative by construction: a host whose needed procs lack a runtime estimate maps to
     * {@link Integer#MAX_VALUE} (never backfill), and the deadline uses the procs' average finish
     * while a borrowed frame is bounded by its worst case. Cores only; memory and GPU readiness are
     * not modelled. Must run before placement mutates the snapshot's idle counts.
     */
    private Map<String, Integer> computeHostReadySeconds(Map<String, BookableHost> hostById) {
        Map<String, Integer> ready = new HashMap<>();
        if (!backfillEnabled || reservations.isEmpty())
            return ready;

        List<String> hostIds = new ArrayList<>(reservations.keySet());

        // Per host: list of {coresFreed, secondsUntilFree} for each running proc.
        Map<String, List<int[]>> procsByHost = new HashMap<>();
        for (MaestroDao.RunningProcEstimate proc : maestroDao.getRunningProcEstimates(hostIds)) {
            String hid = proc.hostId;
            int cores = proc.coresReserved;
            int elapsed = proc.elapsedSeconds;
            int avg = proc.averageSeconds;
            int remaining = (avg < 0) ? Integer.MAX_VALUE : Math.max(0, avg - elapsed);
            procsByHost.computeIfAbsent(hid, key -> new ArrayList<>())
                    .add(new int[] {cores, remaining});
        }

        for (Map.Entry<String, Reservation> entry : reservations.entrySet()) {
            String hid = entry.getKey();
            BookableHost host = hostById.get(hid);
            if (host == null)
                continue; // reserved host not in this tick's snapshot
            int need = entry.getValue().layerCoresMin - host.coresIdle;
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
        for (Map.Entry<HostSpecKey, List<BookableHost>> entry : groups.entrySet()) {
            HostSpecKey spec = entry.getKey();
            String groupLabel = spec.tagsNormalized + (spec.hasGpu ? " gpu" : "") + "|" + spec.os;
            for (BookableHost host : entry.getValue()) {
                FarmHealth.HostHealth hh = health.get(host.hostName.toLowerCase());
                if (hh == null)
                    continue;
                stats.busyCorePoints += hh.busyCorePoints;
                String shape = (host.coresTotal / 100) + "c/"
                        + Math.round(host.memTotal / (1024.0 * 1024.0)) + "g";
                stats.healthByGroup
                        .computeIfAbsent(groupLabel, key -> new MaestroMetrics.HealthAgg())
                        .add(hh.swapTotalKb, hh.swapFreeKb, hh.sysTimePct);
                stats.healthByHwtype.computeIfAbsent(shape, key -> new MaestroMetrics.HealthAgg())
                        .add(hh.swapTotalKb, hh.swapFreeKb, hh.sysTimePct);
            }
        }
    }

    /**
     * The hosts grouped by spec (hostSpecKey), in snapshot order. Each group is planned as a unit.
     */
    static Map<HostSpecKey, List<BookableHost>> groupByHostSpec(List<BookableHost> hosts) {
        Map<HostSpecKey, List<BookableHost>> groups = new LinkedHashMap<>();
        for (BookableHost host : hosts)
            groups.computeIfAbsent(hostSpecKey(host), key -> new ArrayList<>()).add(host);
        return groups;
    }

    /**
     * A host's spec: what kind of machine it is, never which one. Hosts with equal keys are planned
     * as one group. The host's auto-added name tag is dropped, otherwise every host would form a
     * group of its own; a host name in a layer's tags is a pin instead (see {@link #resolvePins}).
     * GPU presence uses totals, not idle, so a fully booked GPU host still groups as a GPU host and
     * only GPU layers and the GPU-weighted score reach it.
     */
    static HostSpecKey hostSpecKey(BookableHost host) {
        return new HostSpecKey(host.pkAlloc, host.pkFacility,
                normalizeTags(host.tagsRaw, host.hostName), host.os,
                host.gpusTotal > 0 || host.gpuMemTotal > 0,
                host.threadMode == ThreadMode.ALL_VALUE);
    }

    /**
     * Resolve this tick's pins into pinnedByGroup. A tag that names a host is a pin: the layer is a
     * candidate only on the hosts it names, obeys every other rule there (subscription in that
     * host's allocation, facility, OS, thread mode, fit, caps, reservations, seats and the soft
     * per-host cap), and never widens to the host's group. A layer tagged with both a spec and a
     * name runs wherever the spec allows plus on the named host; the group's own copy of it wins
     * there.
     *
     * Resolves nothing when there are no groups (so no spec tags) or the candidate read failed,
     * which every group already counts. Cost is O(candidate rows x tag tokens) hash lookups,
     * independent of the host count.
     */
    private void resolveTickPins(Map<HostSpecKey, List<BookableHost>> groups,
            Map<String, List<BookableHost>> hostByName) {
        long t0 = System.currentTimeMillis();
        Set<String> specTags = new HashSet<>();
        for (HostSpecKey spec : groups.keySet())
            for (String tag : spec.tagsNormalized.split("\\s+"))
                if (!tag.isEmpty())
                    specTags.add(tag.toLowerCase(Locale.ROOT));
        if (!specTags.isEmpty() && tickCandidates.failure == null) {
            int limit =
                    env.getProperty("maestro.layer_candidates_per_group_max", Integer.class, 2000);
            pinnedByGroup.putAll(resolvePins(tickCandidates, hostByName, specTags, limit,
                    ThreadLocalRandom.current(), waitReasonByLayer, waitFramesByLayer));
        }
        tickPinsMs = System.currentTimeMillis() - t0;
    }

    /**
     * The pins of the tick's candidate read, pure: for each pinned layer, one candidate per
     * host-spec group holding its pinned hosts there, filed under the group's key.
     *
     * A row is pinned when its tag tokens (spaces removed, lower-cased, split on '|') are not all
     * spec tags. Each token is looked up as a host name, case-insensitively. A named host is pinned
     * when it passes the same rules as the group cut (facility, OS, thread mode, fits one frame)
     * and the show is under its burst in the host's allocation. A layer none of whose names fits,
     * and that names no spec tag either, is tallied in the waitlist as "no host". A repeated name
     * pins its host once; an empty tag string pins nothing. Each group keeps at most limit pinned
     * candidates, drawn by the priority lottery.
     */
    static Map<HostSpecKey, List<LayerCandidate>> resolvePins(TickCandidates tick,
            Map<String, List<BookableHost>> hostByName, Set<String> specTags, int limit,
            Random random, Map<String, String> waitReason, Map<String, Integer> waitFrames) {
        Map<HostSpecKey, Map<String, LayerCandidate>> byGroup = new LinkedHashMap<>();
        for (CandidateRow row : tick.rows) {
            if (row.tags == null || row.tags.replace(" ", "").isEmpty())
                continue; // the SQL's empty token array is a subset of any spec tags
            String[] tokens = row.tags.replace(" ", "").toLowerCase(Locale.ROOT).split("\\|", -1);
            if (specTags.containsAll(Arrays.asList(tokens)))
                continue;
            boolean fits = false;
            for (String token : tokens) {
                List<BookableHost> named = hostByName.get(token);
                if (named != null)
                    for (BookableHost host : named)
                        fits |= pinHost(row, host, tick, byGroup);
            }
            if (!fits && !namesSpecTag(row.tags, specTags)) {
                waitReason.put(row.row.layerId, "no host");
                waitFrames.put(row.row.layerId, row.row.waitingFrameCount);
            }
        }
        Map<HostSpecKey, List<LayerCandidate>> out = new HashMap<>();
        for (Map.Entry<HostSpecKey, Map<String, LayerCandidate>> entry : byGroup.entrySet())
            out.put(entry.getKey(),
                    drawByPriority(new ArrayList<>(entry.getValue().values()), limit, random));
        return out;
    }

    /**
     * Try one named host for a candidate row: returns whether the host fits the row, and when it
     * does and the show is under its burst in the host's allocation, adds the host to the row's pin
     * in the host's group.
     */
    private static boolean pinHost(CandidateRow row, BookableHost host, TickCandidates tick,
            Map<HostSpecKey, Map<String, LayerCandidate>> byGroup) {
        LayerCandidate candidate = row.row;
        if (!Objects.equals(row.facilityId, host.pkFacility) || !jobOsAllowed(row.jobOs, host.os)
                || (host.threadMode == ThreadMode.ALL_VALUE && !candidate.threadable)
                || candidate.layerCoresMin > host.coresTotal)
            return false;
        long[] sub = tick.subscriptions.get(subKey(candidate.showId, host.pkAlloc));
        if (sub == null || sub[0] >= sub[1])
            return true;
        Map<String, LayerCandidate> inGroup =
                byGroup.computeIfAbsent(hostSpecKey(host), key -> new LinkedHashMap<>());
        LayerCandidate pin = inGroup.get(candidate.layerId);
        if (pin == null) {
            pin = candidate.copyForGroup();
            pin.showCoresInUse = (int) sub[0];
            pin.showBurstCores = (int) sub[1];
            pin.showSizeCores = (int) sub[2];
            pin.pinnedHosts = new ArrayList<>();
            pin.pinnedIds = new HashSet<>();
            inGroup.put(candidate.layerId, pin);
        }
        if (pin.pinnedIds.add(host.hostId))
            pin.pinnedHosts.add(host);
        return true;
    }

    /** Whether any token of a layer's tag regex is a host-spec tag (case-insensitive). */
    static boolean namesSpecTag(String layerTags, Set<String> specTags) {
        if (layerTags == null)
            return false;
        for (String tag : layerTags.replace(" ", "").split("\\|"))
            if (specTags.contains(tag.toLowerCase()))
                return true;
        return false;
    }

    /**
     * Merge a group's pinned candidates into its candidate list, skipping layers the group cut
     * already admitted, and restrict each pin to its hosts in the group's idle subset: placement
     * scans that subset, while reservations use the full group, for a pin as for any other
     * candidate. Cost is O(candidates + pins).
     */
    static void addPinned(List<LayerCandidate> candidates, List<LayerCandidate> pinned,
            List<BookableHost> idleGroup) {
        if (pinned == null || pinned.isEmpty())
            return;
        Set<String> present = new HashSet<>();
        for (LayerCandidate candidate : candidates)
            present.add(candidate.layerId);
        Set<BookableHost> idle = new HashSet<>(idleGroup);
        for (LayerCandidate candidate : pinned) {
            if (!present.add(candidate.layerId))
                continue;
            candidate.pinnedIdle = new ArrayList<>();
            for (BookableHost host : candidate.pinnedHosts)
                if (idle.contains(host))
                    candidate.pinnedIdle.add(host);
            candidates.add(candidate);
        }
    }

    /** A pinned candidate wants only its own hosts; an unpinned one wants any. */
    static boolean pinsAllow(LayerCandidate other, BookableHost host) {
        return other.pinnedIds == null || other.pinnedIds.contains(host.hostId);
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
        return Arrays.stream(raw.trim().split("\\s+"))
                .filter(tag -> !tag.equalsIgnoreCase(excludeName)).distinct().sorted()
                .collect(Collectors.joining(" "));
    }

    // ---- placement: layer-driven, best-fit -------------------------------

    /**
     * Place one group's candidates on its idle hosts, one slot at a time, and return the frames
     * planned.
     *
     * Each slot goes to the show with the lowest subscription tier (showTier) and, within it, to a
     * candidate drawn by priority lottery among those that can still place (placeOnce); the loop
     * ends when none can. So a lone layer can take every fitting host in one tick, shows converge
     * to their subscription sizes, and contending layers share capacity in proportion to priority:
     * a rate, never a strict order. A layer's backlog is tick-wide, so groups never plan the same
     * frames twice.
     *
     * Afterwards every candidate gets its why-not trace, waitlist tally and reservation reconcile,
     * judged against the end-of-tick caps. Each candidate's layer is added to seenLayerIds so the
     * end-of-tick sweep keeps its reservation state.
     */
    private int dispatchGroupWithScoring(List<BookableHost> hosts, List<BookableHost> fullHosts,
            List<LayerCandidate> candidates, Set<String> seenLayerIds, String groupAllocId,
            Map<String, Integer> jobCoresUsed, Map<String, Integer> showCoresUsed,
            Map<String, Integer> folderUsed, List<ReservationRequest> reservationReqs,
            Map<String, Integer> tReadyByHost, Map<String, Set<String>> hostLayerAffinity,
            Map<String, LimitBudget> limitBudgets, Map<String, Integer> limitUsed,
            Map<String, Set<String>> limitSeats) {
        int dispatched = 0;
        // Largest host in this group, for the reservation width gate below: a
        // layer may reserve only if its per-frame cores are a big enough fraction
        // of this. Uses fullHosts (idle + busy) so the bar reflects the class's
        // real top-end capacity, not just what happens to be idle this tick.
        int maxGroupHostCores = 0;
        for (BookableHost host : fullHosts) {
            if (host.coresTotal > maxGroupHostCores)
                maxGroupHostCores = host.coresTotal;
        }
        takeTickWideRemainder(candidates, plannedFramesByLayer, seenLayerIds);
        stampDrawWeights(candidates);
        for (LayerCandidate candidate : candidates)
            candidate.showKey = subKey(candidate.showId, groupAllocId);

        // Hand out placements one at a time until no candidate can place. Each
        // placement goes to the show with the lowest tier (cores in use over
        // subscription size, updated after every placement), as the legacy
        // dispatcher does. Within that show, a candidate is drawn weighted by
        // job priority. A candidate that places nothing or runs out of frames
        // leaves the draw; once a show has none left, the next tier takes over.
        List<LayerCandidate> active = new ArrayList<>(candidates.size());
        for (LayerCandidate candidate : candidates) {
            if (candidate.waitingFrameCount > 0)
                active.add(candidate);
        }
        while (!active.isEmpty()) {
            LayerCandidate head = stampTiers(active, showCoresUsed);
            double weightSum = headWeight(active, head);
            int idx = drawSlot(active, head, ThreadLocalRandom.current().nextDouble() * weightSum);
            LayerCandidate drawn = active.get(idx);
            int got = placeOnce(drawn, hosts, candidates, groupAllocId, jobCoresUsed, showCoresUsed,
                    folderUsed, tReadyByHost, hostLayerAffinity, limitBudgets, limitUsed,
                    limitSeats);
            if (got > 0)
                dispatched += got;
            if (got <= 0 || drawn.waitingFrameCount <= 0) {
                active.set(idx, active.get(active.size() - 1));
                active.remove(active.size() - 1);
            }
        }

        // Epilogue, once per candidate, against the end-of-tick gate.
        for (LayerCandidate candidate : candidates) {
            if (candidate.waitingFrameCount <= 0 && !candidate.placedThisTick)
                continue;
            CandidateGate gate = gate(candidate, groupAllocId, jobCoresUsed, showCoresUsed,
                    folderUsed, limitBudgets, limitUsed, limitSeats);
            if (candidate.limitIds != null && gate.limitUsable <= 0)
                tickLicenseHeld++;
            boolean placed = candidate.placedThisTick;
            boolean capped = gate.capped;
            int folderInUse = gate.folderInUse;
            int limitUsable = gate.limitUsable;
            List<LimitBudget> limitSeatPools = gate.limitSeatPools;

            // Why-not trace: one DEBUG line per candidate that wanted work but
            // placed nothing this tick, naming the binding constraint in the
            // same precedence the cap check uses. With the group summary and
            // the zero-candidate explain, one DEBUG tick tells the whole story
            // of a layer that books under the legacy dispatcher but not here.
            if (logger.isDebugEnabled() && !placed && candidate.waitingFrameCount > 0) {
                String why;
                if (candidate.jobCoresInUse + candidate.layerCoresMin > candidate.jobMaxCores)
                    why = "jobMaxCores";
                else if (candidate.showCoresInUse
                        + candidate.layerCoresMin > candidate.showBurstCores)
                    why = "showBurst";
                else if (candidate.folderMax >= 0
                        && folderInUse + candidate.layerCoresMin > candidate.folderMax)
                    why = "folderCap(" + folderInUse + "/" + candidate.folderMax + ")";
                else if (limitUsable <= 0)
                    why = "limitFull(" + candidate.limitIds + ")";
                else if (limitSeatPools != null)
                    why = "noFittingIdleHost(seat-gated limits present)";
                else
                    why = "noFittingIdleHost";
                logger.debug("Maestro unplaced: layer=" + candidate.layerId + " prio="
                        + candidate.priority + " cores=" + candidate.layerCoresMin + " memKb="
                        + candidate.layerMemMin + " waiting=" + candidate.waitingFrameCount
                        + " why=" + why);
            }

            // Waitlist tally: every candidate that leaves the loop with waiting frames lands in
            // exactly one bucket. A placed layer's remaining backlog is flowing; an unplaced one
            // is bucketed by the same precedence the why-not trace uses. Last outcome wins when a
            // layer appears in several groups; a layer that books its whole backlog away drops
            // off the waitlist.
            if (candidate.waitingFrameCount > 0) {
                waitReasonByLayer.put(candidate.layerId,
                        placed ? "flowing"
                                : waitlistReason(candidate,
                                        candidate.pinnedIdle != null ? candidate.pinnedIdle : hosts,
                                        folderInUse, limitUsable, limitSeatPools, limitSeats));
                waitFramesByLayer.put(candidate.layerId, candidate.waitingFrameCount);
            } else if (placed) {
                waitReasonByLayer.remove(candidate.layerId);
                waitFramesByLayer.remove(candidate.layerId);
            }

            if (reservationsEnabled) {
                // Blocked = waiting frames, not capped, placed nothing. A layer
                // at its seat cap counts as capped, not blocked: reserving new
                // hosts could never help it, so it must not accrue debt.
                boolean blocked = !capped && !placed && candidate.waitingFrameCount > 0;
                long now = System.currentTimeMillis();
                long dt = now - lastSeenMs.getOrDefault(candidate.layerId, now);
                lastSeenMs.put(candidate.layerId, now);
                long debt = blockedDebtMs.getOrDefault(candidate.layerId, 0L);
                debt = blocked ? debt + dt : Math.max(0, debt - dt);
                blockedDebtMs.put(candidate.layerId, debt);

                // Request a reservation if the layer already holds some (keep
                // maintaining them until the job drains) or it newly qualifies:
                // blocked past the threshold and wide enough. The width gate
                // keeps the small-frame stream out of the wide-job budget.
                boolean wideEnough = maxGroupHostCores > 0
                        && candidate.layerCoresMin >= RESERVATION_MIN_HOST_FRACTION
                                * maxGroupHostCores;
                boolean qualified = blocked && debt >= reservationBlockMs && wideEnough;
                boolean holdsResv = layerHoldsReservation(candidate.layerId);
                if (holdsResv || qualified) {
                    reservationReqs.add(new ReservationRequest(candidate,
                            candidate.pinnedHosts != null ? candidate.pinnedHosts : fullHosts));
                }
                // Trace reservation decisions for every candidate so we can
                // see why wide-job layers never accumulate enough debt.
                if (logger.isDebugEnabled()) {
                    logger.debug("Maestro resv-candidate: layer=" + candidate.layerId + " coresMin="
                            + candidate.layerCoresMin + " waiting=" + candidate.waitingFrameCount
                            + " capped=" + capped + " placed=" + placed + " blocked=" + blocked
                            + " debt=" + debt + "ms threshold=" + reservationBlockMs + "ms"
                            + " wide=" + wideEnough + " (coresMin=" + candidate.layerCoresMin
                            + " gate=" + (RESERVATION_MIN_HOST_FRACTION * maxGroupHostCores) + ")"
                            + " holds=" + holdsResv + " qualifies=" + (holdsResv || qualified));
                }
            }
        }

        return dispatched;
    }

    /**
     * The weight of a job in the placement draw; the higher the weight, the larger the share of
     * this tick's slots the job wins. Each slot goes to a candidate picked at random with odds
     * proportional to its weight, so a higher priority wins more slots but a lower one still gets
     * some.
     *
     * The weight is priority^{@link #priorityExponent}, with priorities below 1 counted as 1. The
     * exponent decides how much a priority gap is worth: with priorities 80 and 30 competing for
     * the same slots, the higher job wins 73% of them with a linear weight and 81% with the default
     * 1.5, where legacy's job walk gives it all of them until it runs out of frames. The weight is
     * per job; stampDrawWeights splits it among the job's layers.
     */
    static double lotteryWeight(LayerCandidate candidate) {
        return Math.pow(Math.max(1, candidate.priority), priorityExponent);
    }

    /**
     * The winner of one slot among the candidates of {@code head}'s tier (see stampTiers): their
     * drawWeight bands (see headWeight) laid end to end in list order, ticket in [0, headWeight).
     * The last of them absorbs any rounding, so a draw never falls outside the tier.
     */
    static int drawSlot(List<LayerCandidate> active, LayerCandidate head, double ticket) {
        int lastInTier = 0;
        for (int index = 0; index < active.size(); index++) {
            LayerCandidate candidate = active.get(index);
            if (candidate.tier > head.tier)
                continue;
            lastInTier = index;
            ticket -= candidate.drawWeight;
            if (ticket < 0)
                return index;
        }
        return lastInTier;
    }

    /**
     * Stamp every active candidate with its show's tier, read against the tick-wide show cores map
     * so every placement of this tick moves its show before the next draw, and return a candidate
     * of the lowest tier.
     */
    static LayerCandidate stampTiers(List<LayerCandidate> active,
            Map<String, Integer> showCoresUsed) {
        LayerCandidate head = null;
        for (LayerCandidate candidate : active) {
            candidate.tier = showTier(candidate, showCoresUsed);
            if (head == null || candidate.tier < head.tier)
                head = candidate;
        }
        return head;
    }

    /** The draw weight of {@code head}'s tier: the range drawSlot draws from. */
    static double headWeight(List<LayerCandidate> active, LayerCandidate head) {
        double weightSum = 0;
        for (LayerCandidate candidate : active) {
            if (candidate.tier <= head.tier)
                weightSum += candidate.drawWeight;
        }
        return weightSum;
    }

    /**
     * Stamp each candidate's draw weight, once per group. Priority is a job's, so a job's weight is
     * split evenly among its layers in the group: an eight-layer job draws as one job, not as
     * eight.
     */
    static void stampDrawWeights(List<LayerCandidate> candidates) {
        Map<String, Integer> layersOfJob = new HashMap<>();
        for (LayerCandidate candidate : candidates)
            layersOfJob.merge(candidate.jobId, 1, Integer::sum);
        for (LayerCandidate candidate : candidates)
            candidate.drawWeight = lotteryWeight(candidate) / layersOfJob.get(candidate.jobId);
    }

    /**
     * Prologue of a group, once per candidate: register it with the sweep and take its tick-wide
     * remainder. A layer planned in an earlier host-spec group this tick keeps only its remaining
     * frames here, so the groups share one backlog and every plan's slice stays disjoint.
     */
    static void takeTickWideRemainder(List<LayerCandidate> candidates,
            Map<String, Integer> plannedByLayer, Set<String> seenLayerIds) {
        for (LayerCandidate candidate : candidates) {
            seenLayerIds.add(candidate.layerId);
            candidate.waitingFrameCount -= plannedByLayer.getOrDefault(candidate.layerId, 0);
            candidate.placedThisTick = false;
        }
    }

    /**
     * The tier of a candidate's show on this allocation: the legacy dispatcher's subscription tier
     * (the database's tier() function) read tick-wide. Cores in use over subscription size; a show
     * running nothing sorts below every other, at minus its size; a show with no size scores its
     * whole cores plus one, so it sorts above every show still under its size, though a sized show
     * far enough over its size can sort above it. Lower runs first.
     */
    static double showTier(LayerCandidate candidate, Map<String, Integer> showCoresUsed) {
        int cores = showCoresUsed.getOrDefault(candidate.showKey, candidate.showCoresInUse);
        if (candidate.showSizeCores == 0)
            return cores / 100.0 + 1;
        if (cores == 0)
            return -candidate.showSizeCores;
        return (double) cores / candidate.showSizeCores;
    }

    /** Tick-wide cap state of one candidate, read fresh at every slot and once in the epilogue. */
    static final class CandidateGate {
        int folderInUse;
        int limitUsable = Integer.MAX_VALUE;
        List<LimitBudget> limitSeatPools;
        boolean capped;
    }

    /**
     * Every cap that can hold candidate right now, judged against the tick-wide usage: job max
     * cores, show burst (per subscription, so a show with two allocations has two bursts), the
     * folder core ceiling, and the FRAME limits the layer is bound to (HOST limits are checked per
     * host in placeOnce; a limit with no budget entry does not gate). Placements made earlier this
     * tick, in any group, count against it. Idempotent: placeOnce calls it before every attempt and
     * the epilogue once more.
     */
    private CandidateGate gate(LayerCandidate candidate, String groupAllocId,
            Map<String, Integer> jobCoresUsed, Map<String, Integer> showCoresUsed,
            Map<String, Integer> folderUsed, Map<String, LimitBudget> limitBudgets,
            Map<String, Integer> limitUsed, Map<String, Set<String>> limitSeats) {
        CandidateGate gate = new CandidateGate();
        candidate.jobCoresInUse =
                jobCoresUsed.computeIfAbsent(candidate.jobId, key -> candidate.jobCoresInUse);
        candidate.showCoresInUse = showCoresUsed.computeIfAbsent(
                subKey(candidate.showId, groupAllocId), key -> candidate.showCoresInUse);
        if (candidate.limitIds != null) {
            for (String limId : candidate.limitIds) {
                LimitBudget budget = limitBudgets.get(limId);
                if (budget == null)
                    continue;
                if (budget.hostBased) {
                    if (gate.limitSeatPools == null)
                        gate.limitSeatPools = new ArrayList<>(2);
                    gate.limitSeatPools.add(budget);
                    limitSeats.putIfAbsent(limId, budget.seats);
                } else {
                    int remaining = budget.usable - limitUsed.computeIfAbsent(limId, key -> 0);
                    if (remaining < gate.limitUsable)
                        gate.limitUsable = remaining;
                }
            }
        }
        gate.folderInUse = (candidate.folderMax >= 0)
                ? folderUsed.computeIfAbsent(candidate.folderId, key -> candidate.folderRunning)
                : 0;
        // A capped layer (job/show cap, folder ceiling, spent limit budget) must
        // not dispatch but must still reconcile, dropping reservations it can no
        // longer use so other work can take those hosts.
        gate.capped = candidate.jobCoresInUse + candidate.layerCoresMin > candidate.jobMaxCores
                || candidate.showCoresInUse + candidate.layerCoresMin > candidate.showBurstCores
                || (candidate.folderMax >= 0
                        && gate.folderInUse + candidate.layerCoresMin > candidate.folderMax)
                || gate.limitUsable <= 0;
        return gate;
    }

    /**
     * One placement attempt for candidate: choose its best host, size the booking, record the spend
     * so later candidates see it, and submit it (submitCommit). Returns the frames planned, or 0
     * when the candidate is capped, out of probe headroom, or has no usable host left this tick.
     *
     * The best host has the lowest placementScore among those that fit and pass the reservation,
     * seat, per-host-plan and soft-cap gates. A pinned candidate considers only its pinned hosts
     * (addPinned); the soft cap yields only on a host nobody else wants (othersWant).
     */
    private int placeOnce(LayerCandidate candidate, List<BookableHost> hosts,
            List<LayerCandidate> candidates, String groupAllocId, Map<String, Integer> jobCoresUsed,
            Map<String, Integer> showCoresUsed, Map<String, Integer> folderUsed,
            Map<String, Integer> tReadyByHost, Map<String, Set<String>> hostLayerAffinity,
            Map<String, LimitBudget> limitBudgets, Map<String, Integer> limitUsed,
            Map<String, Set<String>> limitSeats) {
        CandidateGate gate = gate(candidate, groupAllocId, jobCoresUsed, showCoresUsed, folderUsed,
                limitBudgets, limitUsed, limitSeats);
        if (gate.capped)
            return 0;
        int limitUsable = gate.limitUsable;
        List<LimitBudget> limitSeatPools = gate.limitSeatPools;
        // Probe gate: a 1-core threadable layer with no rss evidence ("let the
        // system decide") may hold only probeFrames frames farm-wide, so a
        // brand-new mis-sized layer cannot blast the farm before the reports
        // have seen what it really uses.
        int probeHeadroom = Integer.MAX_VALUE;
        if (!candidate.rssProven) {
            probeHeadroom = probeFrames - layerRunningFrames.getOrDefault(candidate.layerId, 0)
                    - layerProbeUsed.getOrDefault(candidate.layerId, 0);
            if (probeHeadroom <= 0)
                return 0;
        }
        BookableHost best = null;
        BookableHost cappedFallback = null;
        double bestScore = Double.POSITIVE_INFINITY;
        for (BookableHost host : candidate.pinnedIdle != null ? candidate.pinnedIdle : hosts) {
            if (!fitsOnHost(candidate, host))
                continue;
            // Per-host gate for HOST-type limits, keyed by host name (what
            // a license server reports): this host is eligible only if it
            // already holds every such limit, or the limit still has a
            // seat to give out.
            if (limitSeatPools != null && !limitSeatsAllow(limitSeatPools, limitSeats, host))
                continue;
            // A reserved host is off-limits unless EASY backfill can
            // borrow it without delaying the reservation's owner.
            if (!reservationAllows(host, candidate)) {
                if (!backfillAllows(host, candidate, tReadyByHost))
                    continue;
            }
            // Per-host layer cap: a host already holding its share of
            // this layer takes no more of it; the flood spills to the
            // next host instead of blanketing this one.
            // SOFT per-host layer cap: prefer hosts under the cap, so
            // a flood spreads instead of blanketing one machine. But a
            // fitting host blocked ONLY by the cap is remembered: if
            // no host is under the cap, the cap yields rather than
            // stranding an idle machine, and only on a host no other
            // candidate could still use (othersWant). Unproven layers
            // never get the fallback (the probe gate is their brake).
            if (layerHostMaxFrac > 0
                    && hostLayerFrames.getOrDefault(host.hostId + "|" + candidate.layerId,
                            0) >= layerHostCap(host, candidate)) {
                if (cappedFallback == null && candidate.rssProven
                        && !othersWant(host, candidate, candidates, groupAllocId, jobCoresUsed,
                                showCoresUsed, limitBudgets, limitUsed, limitSeats))
                    cappedFallback = host;
                continue;
            }
            double score = placementScore(host, candidate);
            // Locality bonus: prefer a host already running this layer so
            // a freed core is refilled by the same layer (same-machine
            // locality, formerly the reactive DispatchNextFrame path).
            if (localityEnabled) {
                Set<String> layersHere = hostLayerAffinity.get(host.hostId);
                if (layersHere != null && layersHere.contains(candidate.layerId)) {
                    score -= localityBonus;
                } else if (localityWindowFrames > 0) {
                    // Cache warmth: the host ran this layer and few
                    // foreign frames displaced its cache since, so
                    // pull the layer back with a decayed bonus. Never
                    // larger than the live bonus; fit/reservations
                    // are filtered before scoring.
                    Long seen = warmthByHostLayer.get(host.hostId + "|" + candidate.layerId);
                    if (seen != null) {
                        long foreign = bookingsByHost.getOrDefault(host.hostId, 0L) - seen;
                        if (foreign >= 0 && foreign < localityWindowFrames) {
                            score -= localityBonus
                                    * (1.0 - (double) foreign / localityWindowFrames);
                        }
                    }
                }
            }
            // Seat bonus for HOST-type limits: packing onto an
            // already-seated machine consumes no new seat, which is the
            // whole point when seats are the scarce resource. Applied per
            // limit, so a host seated in all of the layer's limits outranks
            // one seated in only some. Stacks with the locality bonus.
            if (limitSeatPools != null) {
                String hName = shortHostName(host.hostName);
                for (LimitBudget budget : limitSeatPools) {
                    if (limitSeats.get(budget.id).contains(hName))
                        score -= limitSeatBonus;
                }
            }
            if (score < bestScore) {
                bestScore = score;
                best = host;
            }
        }
        boolean overCap = false;
        if (best == null && cappedFallback != null) {
            // Soft cap: the only thing between this layer and an idle
            // machine was the cap. Give it the machine.
            best = cappedFallback;
            overCap = true;
        }
        if (best == null)
            return 0; // no host can fit this layer

        // Estimate how many frames this commit will book. The
        // dispatcher books up to job_frame_dispatch_max per call,
        // bounded by the same fit checks placementScore uses.
        int estFrames =
                headroomFrames(candidate, best, overCap, probeHeadroom, limitUsable, folderUsed);
        if (estFrames <= 0)
            return 0;

        // The locality dial: classify the chosen host here, before this
        // commit moves any of the maps the bonus scored.
        lastTickStats.bookedFramesByLocality.merge(localityKind(best, candidate), (long) estFrames,
                Long::sum);

        int estCores = estFrames * candidate.layerCoresMin;
        long estMem = (long) estFrames * candidate.layerMemMin;
        int estGpus = estFrames * candidate.layerGpusMin;
        long estGpuMem = (long) estFrames * candidate.layerGpuMemMin;

        best.coresIdle -= estCores;
        best.memIdle -= estMem;
        best.gpusIdle -= estGpus;
        best.gpuMemIdle -= estGpuMem;
        candidate.jobCoresInUse += estCores;
        candidate.showCoresInUse += estCores;
        candidate.waitingFrameCount -= estFrames;
        // Publish back so other candidates of the same job/show this
        // tick see the updated usage.
        jobCoresUsed.put(candidate.jobId, candidate.jobCoresInUse);
        showCoresUsed.put(subKey(candidate.showId, groupAllocId), candidate.showCoresInUse);
        if (layerHostMaxFrac > 0)
            hostLayerFrames.merge(best.hostId + "|" + candidate.layerId, estFrames, Integer::sum);
        if (!candidate.rssProven)
            layerProbeUsed.merge(candidate.layerId, estFrames, Integer::sum);
        if (candidate.folderMax >= 0)
            folderUsed.merge(candidate.folderId, estCores, Integer::sum);
        // Spend the limits: a frame is a token in each FRAME limit, and
        // this host now holds a seat in each HOST one. Both are tick-wide
        // so every later candidate of the same limit, in any group, sees
        // the spend.
        if (candidate.limitIds != null) {
            boolean gated = false;
            for (String limId : candidate.limitIds) {
                LimitBudget budget = limitBudgets.get(limId);
                if (budget == null)
                    continue;
                gated = true;
                if (budget.hostBased) {
                    Set<String> seats = limitSeats.get(limId);
                    if (seats.add(shortHostName(best.hostName))) {
                        logger.info("Maestro limit: new seat " + seats.size() + "/" + budget.seatCap
                                + " on host " + best.hostName + " for limit " + budget.name);
                    }
                } else {
                    limitUsed.merge(limId, estFrames, Integer::sum);
                }
            }
            if (gated)
                tickLicenseBooked += estFrames;
        }

        // Count an EASY-backfill borrow for the stat line: this host
        // is reserved for someone else and only backfillAllows let us
        // in.
        if (!reservationAllows(best, candidate)) {
            tickBackfilled++;
            tickBackfilledCores += estCores;
        }

        // No seize-on-dispatch: reservations are firm (see reservationAllows), so a host
        // reached here is either its owner booking after the drain or an EASY-backfill
        // borrow. A borrow never takes ownership, so the reservation is left intact.
        submitCommit(best.hostId, candidate.layerId, estFrames, candidate.layerCoresMin);
        candidate.placedThisTick = true;
        return estFrames;

    }

    /** True if any host is currently reserved for this layer. */
    private boolean layerHoldsReservation(String layerId) {
        for (Reservation reservation : reservations.values()) {
            if (reservation.layerId.equals(layerId))
                return true;
        }
        return false;
    }

    /** Whether host has the total capacity to run one frame of candidate once idle. */
    private static boolean hostCanEverFit(LayerCandidate candidate, BookableHost host) {
        return host.coresTotal >= candidate.layerCoresMin && host.memTotal >= candidate.layerMemMin
                && host.gpusTotal >= candidate.layerGpusMin
                && host.gpuMemTotal >= candidate.layerGpuMemMin;
    }

    /** How many frames of candidate fit on host when fully idle (min over dimensions). */
    private static int framesThatFit(LayerCandidate candidate, BookableHost host) {
        long frames = Long.MAX_VALUE;
        if (candidate.layerCoresMin > 0)
            frames = Math.min(frames, host.coresTotal / candidate.layerCoresMin);
        if (candidate.layerMemMin > 0)
            frames = Math.min(frames, host.memTotal / candidate.layerMemMin);
        if (candidate.layerGpusMin > 0)
            frames = Math.min(frames, host.gpusTotal / candidate.layerGpusMin);
        if (candidate.layerGpuMemMin > 0)
            frames = Math.min(frames, host.gpuMemTotal / candidate.layerGpuMemMin);
        return (frames == Long.MAX_VALUE) ? 1 : (int) frames; // unconstrained -> 1
    }

    /**
     * Frames of candidate one reservation-eligible host can hold, the minimum over fitting hosts so
     * a layer never reserves too few hosts (the dangerous direction: it stays starved). 0 when no
     * host fits; the caller then counts one host per frame.
     */
    private static int framesPerFittingHost(LayerCandidate candidate, List<BookableHost> hosts) {
        int min = 0;
        for (BookableHost host : hosts) {
            if (!hostCanEverFit(candidate, host))
                continue;
            int frames = framesThatFit(candidate, host);
            if (frames > 0 && (min == 0 || frames < min))
                min = frames;
        }
        return min;
    }

    /**
     * Whether host's reservation, if any, lets candidate book and own it: only the reserving layer
     * may. A reservation is firm: the host is held for its owner until it drains and the owner runs
     * there, and no other layer seizes it, not even a higher-priority one. Other work reaches a
     * reserved host's spare cores only through EASY backfill ({@link #backfillAllows}), which
     * borrows without delaying the owner. Firmness is what lets a long-starved wide job finally
     * run; the grant lottery and maestro.reservation_max_fraction keep the reserved set bounded and
     * fair.
     */
    private boolean reservationAllows(BookableHost host, LayerCandidate candidate) {
        if (!reservationsEnabled)
            return true;
        Reservation reservation = reservations.get(host.hostId);
        return reservation == null || reservation.layerId.equals(candidate.layerId);
    }

    /**
     * EASY backfill (Lifka 1995): whether candidate may borrow reserved host without delaying its
     * owner. Yes only when candidate's worst-case runtime (layer_usage.int_clock_time_high)
     * finishes before host is projected to free enough cores for its owner
     * ({@link #computeHostReadySeconds}). Borrowing never takes ownership. Refuses when candidate
     * has no runtime history or host's ready time is unknown, keeping the no-delay guarantee
     * conservative under soft (non-killed) estimates.
     *
     * The time check is the whole guarantee; do not also require the host to already have enough
     * idle for the owner. Once it does, the owner books the host itself, so such a guard would
     * leave backfill nothing to place and strand the sub-owner-width idle on draining hosts.
     */
    private boolean backfillAllows(BookableHost host, LayerCandidate candidate,
            Map<String, Integer> tReadyByHost) {
        if (!backfillEnabled)
            return false;
        Integer tReady = tReadyByHost.get(host.hostId);
        if (tReady == null)
            return false;
        return backfillFits(candidate.hasRuntimeEstimate(), candidate.clockTimeHighSec, tReady);
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
        sorted.sort(Comparator.comparingInt(proc -> proc[1]));
        int freed = 0;
        for (int[] proc : sorted) {
            if (proc[1] == Integer.MAX_VALUE)
                break; // unknown proc needed
            freed += proc[0];
            if (freed >= needCores)
                return proc[1];
        }
        return Integer.MAX_VALUE;
    }

    /**
     * Bring candidate's reservations to the number of hosts it can still use: its waiting frames,
     * clamped by its job and show caps (a capped layer must not hold hosts it cannot legally use),
     * over the frames one fitting host runs.
     *
     * {@link #reservationMaxFraction} throttles fresh grants only, never a host already held. A
     * held host is mid-drain toward its owner; releasing it whenever another layer reserves would
     * reset that progress and the wide job would never assemble its block. Holding it cannot
     * deadlock the class, since a draining host runs its owner and then frees up. So a layer sheds
     * hosts only when its own demand falls ({@link #releaseSurplusReservations}) and claims more,
     * up to its cap headroom, via {@link #pickReservationTarget}.
     */
    private void reconcileReservationsForLayer(LayerCandidate candidate, List<BookableHost> hosts) {
        List<String> mine = new ArrayList<>();
        for (Map.Entry<String, Reservation> entry : reservations.entrySet()) {
            if (entry.getValue().layerId.equals(candidate.layerId))
                mine.add(entry.getKey());
        }

        int have = mine.size();
        int framesNeed = Math.max(0, candidate.waitingFrameCount);
        if (candidate.layerCoresMin > 0) {
            int jobFramesLeft = Math.max(0,
                    (candidate.jobMaxCores - candidate.jobCoresInUse) / candidate.layerCoresMin);
            int showFramesLeft = Math.max(0, (candidate.showBurstCores - candidate.showCoresInUse)
                    / candidate.layerCoresMin);
            framesNeed = Math.min(framesNeed, Math.min(jobFramesLeft, showFramesLeft));
        }

        // Capacity-aware: how many hosts does framesNeed actually require?
        // Use the smallest fitting host's capacity so we never under-reserve.
        int framesPerHost = framesPerFittingHost(candidate, hosts);
        int need = framesPerHost > 0 ? (framesNeed + framesPerHost - 1) / framesPerHost // ceil
                : framesNeed;

        // Fitting hosts in this group and how many are already held by other layers, for the
        // per-class cap. The cap bounds fresh grants only (see the header); held hosts are kept.
        int fittingTotal = 0, reservedByOthers = 0;
        for (BookableHost host : hosts) {
            if (!hostCanEverFit(candidate, host))
                continue;
            fittingTotal++;
            Reservation reservation = reservations.get(host.hostId);
            if (reservation != null && !reservation.layerId.equals(candidate.layerId))
                reservedByOthers++;
        }
        int capTotal = (int) Math.floor(reservationMaxFraction * fittingTotal);

        if (have > need) {
            releaseSurplusReservations(mine, hosts, need);
        } else if (have < need) {
            int headroom = Math.max(0, capTotal - reservedByOthers - have);
            int want = Math.min(need - have, headroom);
            for (int index = 0; index < want; index++) {
                BookableHost host = pickReservationTarget(candidate, hosts);
                if (host == null)
                    break; // no free eligible host
                reservations.put(host.hostId, new Reservation(candidate.layerId, candidate.priority,
                        candidate.layerCoresMin));
            }
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
        for (BookableHost host : hosts)
            idleByHost.put(host.hostId, host.coresIdle);
        mine.sort((left, right) -> Integer.compare(idleByHost.getOrDefault(right, 0),
                idleByHost.getOrDefault(left, 0)));
        for (String hostId : mine.subList(Math.min(keep, mine.size()), mine.size()))
            reservations.remove(hostId);
    }

    /**
     * The host likely to free up for candidate soonest, taken as the one with the fewest running
     * procs, among the hosts that could run it once idle and that nobody has reserved: a held host
     * is never taken from its owner. Null when no host qualifies.
     */
    private BookableHost pickReservationTarget(LayerCandidate candidate, List<BookableHost> hosts) {
        BookableHost best = null;
        int bestProcs = Integer.MAX_VALUE;
        for (BookableHost host : hosts) {
            if (!hostCanEverFit(candidate, host))
                continue;
            // Firm reservations: only ever expand into a free host. A held host is
            // never taken from its owner, not even by a higher-priority reserver, so a
            // low-priority job's lottery-won grant is not clawed back; it frees only
            // when its owner's demand drops (releaseSurplusReservations) or the layer
            // leaves. Own hosts are already counted in 'have', so skipping every
            // reserved host covers them too.
            if (reservations.get(host.hostId) != null)
                continue;
            if (host.runningProcs < bestProcs) {
                bestProcs = host.runningProcs;
                best = host;
            }
        }
        return best;
    }

    /**
     * Placement score of a (host, layer) pair; lower is better. Assumes the layer fits (check
     * fitsOnHost first).
     *
     * E-PVM marginal cost (Amir et al. 2000): the weighted sum, over resource dimensions, of each
     * dimension's convex cost rise from adding one frame (see deltaCost). An already full dimension
     * (idle cores behind saturated memory) costs far more, and costs are on the
     * utilization-fraction scale so big hosts are not starved. One frame at a time: placement
     * decrements the host's idle counts after each booking, so the next frame sees the steeper
     * cost. See maestro.md for the derivation.
     */
    static double placementScore(BookableHost host, LayerCandidate candidate) {
        return wCores * deltaCost(host.coresTotal, host.coresIdle, candidate.layerCoresMin)
                + wMem * deltaCost(host.memTotal, host.memIdle, candidate.layerMemMin)
                + wGpus * deltaCost(host.gpusTotal, host.gpusIdle, candidate.layerGpusMin)
                + wGpuMem * deltaCost(host.gpuMemTotal, host.gpuMemIdle, candidate.layerGpuMemMin);
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
     * Frames one commit may book for candidate on host best: the minimum of every sizing rule. Zero
     * or less means stop booking this candidate this tick. A soft-cap grant (overCap) ignores the
     * per-host layer cap, which already yielded for this booking.
     */
    private int headroomFrames(LayerCandidate candidate, BookableHost best, boolean overCap,
            int probeHeadroom, int limitUsable, Map<String, Integer> folderUsed) {
        long maxMore = computeMaxMore(best, candidate);
        // Commit size: one plan slice.
        int est = (int) Math.min(frameQueryMax, maxMore + 1);
        // Backlog: never book frames the layer does not have.
        est = Math.min(est, candidate.waitingFrameCount);
        // Probe: an unproven layer's remaining farm-wide allowance.
        est = Math.min(est, probeHeadroom);
        // FRAME limits: one frame is one token, budgets shared tick-wide.
        if (limitUsable != Integer.MAX_VALUE)
            est = Math.min(est, limitUsable);
        // Folder ceiling (cores, not frames).
        if (candidate.folderMax >= 0 && candidate.layerCoresMin > 0)
            est = Math.min(est, (candidate.folderMax - folderUsed.get(candidate.folderId))
                    / candidate.layerCoresMin);
        // Per-host layer cap: skipped when the cap already yielded.
        if (!overCap && layerHostMaxFrac > 0) {
            int hlCap = layerHostCap(best, candidate);
            if (hlCap != Integer.MAX_VALUE)
                est = Math.min(est, hlCap
                        - hostLayerFrames.getOrDefault(best.hostId + "|" + candidate.layerId, 0));
        }
        return est;
    }

    /**
     * Further frames of candidate host could take after this one, bounded by every physical
     * dimension and the job's and show's remaining core headroom. 0 when no further frame fits.
     */
    static long computeMaxMore(BookableHost host, LayerCandidate candidate) {
        long remCores = host.coresIdle - candidate.layerCoresMin;
        long remMem = host.memIdle - candidate.layerMemMin;
        long remGpus = host.gpusIdle - candidate.layerGpusMin;
        long remGpuMem = host.gpuMemIdle - candidate.layerGpuMemMin;

        long maxMore = Long.MAX_VALUE;
        if (candidate.layerCoresMin > 0)
            maxMore = Math.min(maxMore, remCores / candidate.layerCoresMin);
        if (candidate.layerMemMin > 0)
            maxMore = Math.min(maxMore, remMem / candidate.layerMemMin);
        if (candidate.layerGpusMin > 0)
            maxMore = Math.min(maxMore, remGpus / candidate.layerGpusMin);
        if (candidate.layerGpuMemMin > 0)
            maxMore = Math.min(maxMore, remGpuMem / candidate.layerGpuMemMin);

        if (candidate.layerCoresMin > 0) {
            long jobRem = (long) candidate.jobMaxCores - candidate.jobCoresInUse
                    - candidate.layerCoresMin;
            if (jobRem < 0)
                jobRem = 0;
            maxMore = Math.min(maxMore, jobRem / candidate.layerCoresMin);
        }
        if (candidate.layerCoresMin > 0) {
            long showRem = (long) candidate.showBurstCores - candidate.showCoresInUse
                    - candidate.layerCoresMin;
            if (showRem < 0)
                showRem = 0;
            maxMore = Math.min(maxMore, showRem / candidate.layerCoresMin);
        }
        if (maxMore == Long.MAX_VALUE)
            maxMore = 0;
        return maxMore;
    }

    /**
     * Whole cores idle after this group's plan that no still-waiting candidate can buy: on every
     * such host each candidate is stopped by cores, memory or gpu. The physical counterpart of the
     * waitlist's 'no fit' bucket, counted after planning so cores that just sold are not blamed. A
     * group with nothing waiting strands nothing; idle without demand is just idle.
     */
    static long strandedWholeCores(List<BookableHost> hosts, List<LayerCandidate> candidates) {
        List<LayerCandidate> waiting = new ArrayList<>();
        for (LayerCandidate candidate : candidates)
            if (candidate.waitingFrameCount > 0)
                waiting.add(candidate);
        if (waiting.isEmpty())
            return 0;
        long strandedCp = 0;
        for (BookableHost host : hosts) {
            if (host.coresIdle < Dispatcher.CORE_POINTS_RESERVED_MIN)
                continue;
            boolean sellable = false;
            for (LayerCandidate candidate : waiting) {
                if (candidate.layerCoresMin <= host.coresIdle
                        && candidate.layerMemMin <= host.memIdle
                        && candidate.layerGpusMin <= host.gpusIdle
                        && candidate.layerGpuMemMin <= host.gpuMemIdle) {
                    sellable = true;
                    break;
                }
            }
            if (!sellable)
                strandedCp += host.coresIdle;
        }
        return strandedCp / CORE_POINTS_PER_CORE;
    }

    /**
     * Classify a chosen host for the locality dial with the same signals the locality bonus scored:
     * live_warm when the host runs the layer right now, cache_warm when the layer left it and fewer
     * than a window of foreign frames displaced its caches since, cold otherwise. With locality off
     * the warmth map is not fed, so cache_warm reads cold and the dial shows the accidental
     * locality rate, the baseline for an A/B comparison.
     */
    private String localityKind(BookableHost host, LayerCandidate candidate) {
        Set<String> layersHere = hostLayerAffinity.get(host.hostId);
        if (layersHere != null && layersHere.contains(candidate.layerId))
            return "live_warm";
        if (localityWindowFrames > 0) {
            Long seen = warmthByHostLayer.get(host.hostId + "|" + candidate.layerId);
            if (seen != null) {
                long foreign = bookingsByHost.getOrDefault(host.hostId, 0L) - seen;
                if (foreign >= 0 && foreign < localityWindowFrames)
                    return "cache_warm";
            }
        }
        return "cold";
    }

    // ---- plan / batch-commit: submission ----------------------------------

    /**
     * Record a (host, layer) placement for this tick's plan phase. Each call takes the next
     * estFrames of the layer's tick-wide backlog as the pair's own slice, so no two placements plan
     * the same frames. Tick thread only.
     */
    private void submitCommit(String hostId, String layerId, int estFrames, int cores) {
        // Start this slice where the layer's previous one ended, so parallel plan reads never
        // pull the same frames. A (host, layer) pair gets one slice per slot the draw gives it.
        List<int[]> slices = planSliceByHostLayer.computeIfAbsent(hostId + "|" + layerId,
                key -> new ArrayList<>());
        if (slices.isEmpty())
            plannedByHost.computeIfAbsent(hostId, key -> new ArrayList<>()).add(layerId);
        // Cores are per slice: the grant is capped per group, and a layer may plan in several.
        slices.add(new int[] {plannedFramesByLayer.getOrDefault(layerId, 0), estFrames, cores});
        plannedFramesByLayer.merge(layerId, estFrames, Integer::sum);
    }

    // ---- batched resource accounting: accumulate + flush ------------------

    /**
     * Buffer the resource deltas of the procs a commit just booked, for flushResourceDeltas in the
     * same transaction. Only winners are passed, so rolled-back bookings are never counted. Local
     * dispatches keep their own accounting and are skipped. Tick thread only.
     */
    private void accumulateResourceDeltas(List<VirtualProc> procs) {
        if (procs == null || procs.isEmpty()) {
            return;
        }
        for (VirtualProc proc : procs) {
            if (proc.isLocalDispatch) {
                continue;
            }
            long cores = proc.coresReserved;
            long gpus = proc.gpusReserved;
            addDelta(subDeltas, subKey(proc.getShowId(), proc.getAllocationId()), cores, gpus);
            addDelta(layerDeltas, proc.getLayerId(), cores, gpus);
            addDelta(jobDeltas, proc.getJobId(), cores, gpus);
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
        buf.merge(key, new long[] {cores, gpus}, (accumulated, added) -> {
            accumulated[0] += added[0];
            accumulated[1] += added[1];
            return accumulated;
        });
    }

    /**
     * Write the buffered resource deltas, one UPDATE per row, inside the committing chunk's
     * transaction on the tick thread. A failure rolls back with the chunk, and commitContained
     * discards the rest (discardResourceDeltas), so a failed chunk never credits the next. Rows
     * deleted mid-tick (subscription, layer, or a vanished job's folder and point) simply update
     * nothing.
     */
    private void flushResourceDeltas() {
        flushSubDeltas();
        flushLayerDeltas();
        flushJobDeltas();
    }

    /** Drop the deltas a failed chunk left behind, so the next chunk credits only its own procs. */
    void discardResourceDeltas() {
        subDeltas.clear();
        layerDeltas.clear();
        jobDeltas.clear();
    }

    private void flushSubDeltas() {
        if (subDeltas.isEmpty()) {
            return;
        }
        Map<String, long[]> snap = drain(subDeltas);
        List<SubscriptionDelta> deltas = new ArrayList<>(snap.size());
        for (Map.Entry<String, long[]> entry : snap.entrySet()) {
            String[] showAndAlloc = entry.getKey().split("\t", 2);
            long[] delta = entry.getValue();
            deltas.add(new SubscriptionDelta(showAndAlloc[0], showAndAlloc[1], (int) delta[0],
                    (int) delta[1]));
        }
        maestroDao.addSubscriptionUsage(deltas);
    }

    private void flushLayerDeltas() {
        if (layerDeltas.isEmpty()) {
            return;
        }
        Map<String, long[]> snap = drain(layerDeltas);
        List<ResourceDelta> deltas = new ArrayList<>(snap.size());
        for (Map.Entry<String, long[]> entry : snap.entrySet()) {
            long[] delta = entry.getValue();
            deltas.add(new ResourceDelta(entry.getKey(), (int) delta[0], (int) delta[1]));
        }
        maestroDao.addLayerUsage(deltas);
    }

    private void flushJobDeltas() {
        if (jobDeltas.isEmpty()) {
            return;
        }
        Map<String, long[]> snap = drain(jobDeltas);
        List<ResourceDelta> deltas = new ArrayList<>(snap.size());
        for (Map.Entry<String, long[]> entry : snap.entrySet()) {
            long[] delta = entry.getValue();
            deltas.add(new ResourceDelta(entry.getKey(), (int) delta[0], (int) delta[1]));
        }
        maestroDao.addJobUsage(deltas);
    }

    /** Copy out a delta buffer and clear it. */
    private static Map<String, long[]> drain(Map<String, long[]> buf) {
        Map<String, long[]> snap = new HashMap<>();
        for (Iterator<Map.Entry<String, long[]>> it = buf.entrySet().iterator(); it.hasNext();) {
            Map.Entry<String, long[]> entry = it.next();
            snap.put(entry.getKey(), entry.getValue());
            it.remove();
        }
        return snap;
    }

    /** Whether one frame of candidate fits host's idle capacity right now, in every dimension. */
    static boolean fitsOnHost(LayerCandidate candidate, BookableHost host) {
        if (host.coresIdle < candidate.layerCoresMin)
            return false;
        if (host.memIdle < candidate.layerMemMin)
            return false;
        if (host.gpusIdle < candidate.layerGpusMin)
            return false;
        if (host.gpuMemIdle < candidate.layerGpuMemMin)
            return false;
        return true;
    }

    /**
     * Why an unplaced layer could not fit on any of {@code hosts}, by the first gate no host clears
     * (gates mirror {@link #fitsOnHost}): {@code cores} (no host had enough idle cores for one
     * frame), {@code memory} (cores fit somewhere but not the RAM), {@code gpu} (cores and RAM fit
     * but not the GPU), or {@code fit} (some host fit fully, so the layer was gated by a
     * reservation or a HOST-limit seat -- the caller resolves that into held/license). Feeds the
     * waitlist buckets via {@link #waitlistReason}.
     */
    static String classifyFragmentation(LayerCandidate candidate, List<BookableHost> hosts) {
        boolean anyCores = false;
        boolean anyMem = false;
        for (BookableHost host : hosts) {
            if (host.coresIdle < candidate.layerCoresMin)
                continue;
            anyCores = true;
            if (host.memIdle < candidate.layerMemMin)
                continue;
            anyMem = true;
            if (host.gpusIdle >= candidate.layerGpusMin
                    && host.gpuMemIdle >= candidate.layerGpuMemMin)
                return "fit";
        }
        if (!anyCores)
            return "cores";
        if (!anyMem)
            return "memory";
        return "gpu";
    }

    /**
     * Name the gate that held a candidate some host could fit: {@code license} when a fitting
     * host's HOST-limit seat is taken; {@code held} when a fitting host is reserved for someone
     * else (draining for a wide job); otherwise {@code share}, when every fitting host already
     * holds this layer's per-host share while other work waits (see othersWant), or was planned for
     * it this tick and takes its next slice next tick.
     */
    private String fitGateReason(LayerCandidate candidate, List<BookableHost> hosts,
            List<LimitBudget> limitSeatPools, Map<String, Set<String>> limitSeats) {
        if (limitSeatPools != null) {
            for (BookableHost host : hosts) {
                if (fitsOnHost(candidate, host)
                        && !limitSeatsAllow(limitSeatPools, limitSeats, host))
                    return "license";
            }
        }
        for (BookableHost host : hosts) {
            if (fitsOnHost(candidate, host) && !reservationAllows(host, candidate))
                return "held";
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
    String waitlistReason(LayerCandidate candidate, List<BookableHost> hosts, int folderInUse,
            int limitUsable, List<LimitBudget> limitSeatPools,
            Map<String, Set<String>> limitSeats) {
        if (candidate.jobCoresInUse + candidate.layerCoresMin > candidate.jobMaxCores
                || candidate.showCoresInUse + candidate.layerCoresMin > candidate.showBurstCores
                || (candidate.folderMax >= 0
                        && folderInUse + candidate.layerCoresMin > candidate.folderMax))
            return "limit";
        if (limitUsable <= 0)
            return "no license";
        String fit = classifyFragmentation(candidate, hosts);
        if ("fit".equals(fit))
            fit = fitGateReason(candidate, hosts, limitSeatPools, limitSeats);
        if ("held".equals(fit) || "share".equals(fit))
            return fit;
        if ("license".equals(fit))
            return "no license";
        if ("cores".equals(fit)) {
            long idleSum = 0;
            for (BookableHost host : hosts)
                idleSum += host.coresIdle;
            return idleSum < candidate.layerCoresMin ? "capacity" : "no fit";
        }
        return "no fit";
    }

    /**
     * Fold the per-layer waitlist into the tick stats and preformat its stat-line fragment. The
     * waitlist is every candidate layer that still had waiting frames when the planning loop left
     * it, each frame in exactly one bucket, so the buckets sum to the waitlist the tick weighed. A
     * job the candidate read already filters out at its cap shows here only on ticks that re-admit
     * it.
     */
    private void tallyWaitlist(MaestroMetrics.TickStats stats) {
        Map<String, Long> waitingByReason = stats.waitingFramesByReason;
        for (Map.Entry<String, String> entry : waitReasonByLayer.entrySet()) {
            Integer frames = waitFramesByLayer.get(entry.getKey());
            if (frames != null && frames > 0)
                waitingByReason.merge(entry.getValue(), frames.longValue(), Long::sum);
        }
        long total = 0;
        for (Map.Entry<String, Long> entry : waitingByReason.entrySet()) {
            total += entry.getValue();
            winWaitMax.merge(entry.getKey(), entry.getValue(), Math::max);
        }
        if (total > winWaitTotalMax)
            winWaitTotalMax = total;
    }

    // ---- config -----------------------------------------------------------

    private boolean isEnabled() {
        return MaestroMode.enabled(env);
    }

    // ---- POJOs ------------------------------------------------------------

    public static final class BookableHost {
        public String hostId;
        public String hostName;
        public String pkAlloc;
        public String pkFacility;
        public int threadMode;
        // Total capacity. Used by pickReservationTarget to check whether the
        // host could fit a layer when fully idle, independent of the host's
        // current load.
        public int coresTotal;
        public long memTotal;
        public int gpusTotal;
        public long gpuMemTotal;
        // Current idle resources. Decremented as we dispatch within a tick.
        public int coresIdle;
        public long memIdle;
        public int gpusIdle;
        public long gpuMemIdle;
        // Current running proc count. Used as the "soonest-to-free" heuristic
        // for reservation target selection.
        public int runningProcs;
        public String tagsRaw;
        public String os;
    }

    public static final class LayerCandidate {
        public String layerId;
        public String jobId;
        public String showId;
        public int layerCoresMin; // the ask, or the grant (resizeFromLiveMem)
        public long layerMemMin;
        public boolean threadable;
        public int layerCoresMax;
        public int layerGpusMin;
        public long layerGpuMemMin;
        public int priority;
        double drawWeight; // stamped by stampDrawWeights(), consumed by drawSlot()
        public long layerMaxRssKb; // largest rss any frame reported (layer_mem), 0 before the first
        public boolean manual; // tagged "manual": sized by hand, never by Maestro
        boolean rssProven; // false arms the probe gate (see sizeFromMemory)
        boolean placedThisTick; // consumed by dispatchGroupWithScoring()
        // Mutable in-tick accounting.
        public int jobCoresInUse;
        public int jobMaxCores;
        public int showCoresInUse;
        public int showBurstCores;
        public int showSizeCores; // consumed by showTier()
        String showKey; // consumed by showTier()
        double tier; // consumed by drawSlot()
        // Number of pending dispatchable (waiting) frames. Initialized from
        // waiting_frame_count in the candidate query; decremented as the
        // layer dispatches in this tick. Reconcile keeps the layer's
        // reservation count equal to this value.
        public int waitingFrameCount;
        // EASY-backfill runtime estimate (from layer_usage). clockTimeHighSec
        // is the worst single-frame wall-clock time ever recorded for the
        // layer; frameSuccessCount is how many successful frames produced it.
        // Both 0 when the layer has no history. Used only as the conservative
        // upper bound on how long a frame of this layer would occupy a host it
        // backfills onto (see backfillAllows).
        public int clockTimeHighSec;
        public int frameSuccessCount;
        // Limits bound to the layer (layer_limit rows), or null when none (the
        // common case). Which of them actually gate, and with what budget, is
        // resolved once per tick in resolveLimitBudgets.
        public List<String> limitIds;
        // Folder (group/dept) core cap. folderId is the job's folder; folderMax is
        // folder_resource.int_max_cores (-1 = unlimited, core-points); folderRunning
        // is folder_resource.int_cores, the cores the folder's procs reserve
        // (core-points), seed for the tick-wide folderUsed cap in dispatchGroupWithScoring.
        public String folderId;
        public int folderMax;
        public int folderRunning;
        List<BookableHost> pinnedHosts; // consumed by addPinned() and the epilogue's reservation
        Set<String> pinnedIds; // consumed by pinsAllow()
        List<BookableHost> pinnedIdle; // consumed by placeOnce()

        /** Whether the layer has enough history to bound a frame's runtime. */
        boolean hasRuntimeEstimate() {
            return frameSuccessCount > 0 && clockTimeHighSec > 0;
        }

        /**
         * A fresh candidate from this row for one group: the per-tick row fields, none of the
         * per-group scratch (sizing, draw, tier, pins, placement), which each group sets itself.
         */
        LayerCandidate copyForGroup() {
            LayerCandidate candidate = new LayerCandidate();
            candidate.layerId = layerId;
            candidate.jobId = jobId;
            candidate.showId = showId;
            candidate.layerCoresMin = layerCoresMin;
            candidate.layerMemMin = layerMemMin;
            candidate.threadable = threadable;
            candidate.layerCoresMax = layerCoresMax;
            candidate.layerGpusMin = layerGpusMin;
            candidate.layerGpuMemMin = layerGpuMemMin;
            candidate.priority = priority;
            candidate.layerMaxRssKb = layerMaxRssKb;
            candidate.manual = manual;
            candidate.jobCoresInUse = jobCoresInUse;
            candidate.jobMaxCores = jobMaxCores;
            candidate.waitingFrameCount = waitingFrameCount;
            candidate.clockTimeHighSec = clockTimeHighSec;
            candidate.frameSuccessCount = frameSuccessCount;
            candidate.limitIds = limitIds;
            candidate.folderId = folderId;
            candidate.folderMax = folderMax;
            candidate.folderRunning = folderRunning;
            return candidate;
        }
    }

    /**
     * One row of the tick's candidate read: a dispatchable layer with the job fields the groups cut
     * on. The candidate is a template; each group that admits the row gets its own copy with the
     * group's subscription figures filled in.
     */
    public static final class CandidateRow {
        final LayerCandidate row;
        final String facilityId;
        final String jobOs; // null or empty = any os
        final String tags; // the layer's tag regex, matched against a group's tags

        public CandidateRow(LayerCandidate row, String facilityId, String jobOs, String tags) {
            this.row = row;
            this.facilityId = facilityId;
            this.jobOs = jobOs;
            this.tags = tags;
        }
    }

    /**
     * The tick's candidate read: every dispatchable layer of the planned shows and every
     * subscription (show|alloc to {cores, burst, size}), read once and cut per group by
     * groupCandidates. A failed read is kept too, so every group of the tick counts its query error
     * without retrying the read.
     */
    static final class TickCandidates {
        final List<CandidateRow> rows;
        final Map<String, long[]> subscriptions;
        final RuntimeException failure;

        TickCandidates(List<CandidateRow> rows, Map<String, long[]> subscriptions) {
            this.rows = rows;
            this.subscriptions = subscriptions;
            this.failure = null;
        }

        TickCandidates(RuntimeException failure) {
            this.rows = Collections.emptyList();
            this.subscriptions = Collections.emptyMap();
            this.failure = failure;
        }
    }

    /**
     * A firm claim on a host by one layer, keyed by host id and persistent across ticks: only the
     * owner may book the host (see reservationAllows). Carries what the backfill deadline needs, so
     * the owner need not be among the current group's candidates.
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
     * A layer that wants reservations this tick, with the full host set of its group. Collected
     * during placement and settled after all groups by grantReservations.
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
        public boolean equals(Object other) {
            if (this == other)
                return true;
            if (!(other instanceof HostSpecKey))
                return false;
            HostSpecKey spec = (HostSpecKey) other;
            return hasGpu == spec.hasGpu && allThreadMode == spec.allThreadMode
                    && Objects.equals(pkAlloc, spec.pkAlloc)
                    && Objects.equals(pkFacility, spec.pkFacility)
                    && Objects.equals(tagsNormalized, spec.tagsNormalized)
                    && Objects.equals(os, spec.os);
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

    public void setMaestroDao(MaestroDao maestroDao) {
        this.maestroDao = maestroDao;
    }

    public void setDispatcher(Dispatcher dispatcher) {
        this.dispatcher = dispatcher;
    }

    public void setDispatchSupport(DispatchSupport dispatchSupport) {
        this.dispatchSupport = dispatchSupport;
    }

    public void setHostManager(HostManager hostManager) {
        this.hostManager = hostManager;
    }

    public void setRqdClient(RqdClient rqdClient) {
        this.rqdClient = rqdClient;
    }

    public void setFrameCompleteHandler(FrameCompleteHandler frameCompleteHandler) {
        this.frameCompleteHandler = frameCompleteHandler;
    }

    public void setMaestroMetrics(MaestroMetrics maestroMetrics) {
        this.maestroMetrics = maestroMetrics;
    }
}
