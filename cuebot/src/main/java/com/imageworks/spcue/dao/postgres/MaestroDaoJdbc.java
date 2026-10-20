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

package com.imageworks.spcue.dao.postgres;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.dao.MaestroDao;
import com.imageworks.spcue.dispatcher.Maestro;
import com.imageworks.spcue.dispatcher.Maestro.BookableHost;
import com.imageworks.spcue.dispatcher.Maestro.CandidateRow;
import com.imageworks.spcue.dispatcher.Maestro.LayerCandidate;

public class MaestroDaoJdbc extends JdbcDaoSupport implements MaestroDao {

    // Postgres advisory-lock key, shared by every Cuebot on the database. ASCII "OpenCue".
    private static final long SCHEDULER_LOCK_KEY = 0x4F70656E437565L;

    // Max pending layers the "why nothing books" explain returns per group, highest priority first.
    private static final int EXPLAIN_LIMIT = 20;

    private final Environment env;

    @Autowired
    public MaestroDaoJdbc(Environment env) {
        this.env = env;
    }

    // ---- snapshot queries -------------------------------------------------

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

    // The bound flag is facility mode: every show, else only the b_scheduler_managed ones.
    // spotless:off
    private static final String SELECT_LIVE_SHOW_USAGE =
            "SELECT "
            + "  sh.str_name AS show_name, "
            + "  SUM(p.int_cores_reserved) AS cores, "
            + "  COUNT(*) AS frames "
            + "FROM proc p "
            + "JOIN show sh ON sh.pk_show = p.pk_show "
            + "WHERE (? OR sh.b_scheduler_managed = true) "
            + "GROUP BY sh.str_name";
    // spotless:on

    // spotless:off
    // The tick's one candidate read: every dispatchable layer of the shows Maestro plans,
    // with the columns the groups cut on (tags, os, facility). The predicates that depend
    // on the group (allocation subscription, os, facility, thread mode, tag regex, largest
    // host) are applied in Maestro.groupCandidates, in memory, once per group; the per-row
    // tag regex in particular is matched once per distinct tag string there instead of being
    // compiled by Postgres for every layer on every group's query. No ORDER BY or LIMIT: the
    // priority lottery and the per-group cap are drawn per group.
    private static final String SELECT_CANDIDATE_ROWS =
            "SELECT "
            + "  l.pk_layer, "
            + "  l.pk_job, "
            + "  j.pk_show, "
            + "  j.pk_facility, "
            + "  j.str_os, "
            + "  l.str_tags, "
            + "  l.int_cores_min, "
            + "  l.int_mem_min, "
            + "  l.b_threadable, "
            + "  l.int_cores_max, "
            + "  l.int_gpus_min, "
            + "  l.int_gpu_mem_min, "
            + "  jr.int_priority, "
            + "  jr.int_cores       AS job_cores_in_use, "
            + "  jr.int_max_cores   AS job_max_cores, "
            + "  0 AS show_cores_in_use, "
            + "  0 AS show_burst, "
            + "  0 AS show_size, "
            + "  COALESCE(ls.int_waiting_count, 0) AS waiting_frame_count, "
            + "  COALESCE(lu.int_clock_time_high, 0)     AS clock_time_high, "
            + "  COALESCE(lu.int_frame_success_count, 0) AS frame_success_count, "
            + "  COALESCE(lm.int_max_rss, 0) AS layer_max_rss, "
            + "  position('manual' in lower(l.str_tags)) > 0 AS b_manual, "
            // Limits bound to the layer, comma separated, NULL when none. The
            // per-limit budgets (usage, thresholds, holder hosts) are resolved
            // once per tick in Maestro.resolveLimitBudgets, not per candidate row.
            + "  (SELECT string_agg(ll.pk_limit_record, ',') "
            + "     FROM layer_limit ll WHERE ll.pk_layer = l.pk_layer) AS limit_ids, "
            // Folder (group/dept) core cap: the job's folder, its ceiling, and the
            // folder's running cores as the database counts them (see the fr join).
            + "  j.pk_folder AS folder_id, "
            + "  COALESCE(fr.int_max_cores, -1) AS folder_max, "
            + "  COALESCE(fr.int_cores, 0)      AS folder_running "
            + "FROM   layer l "
            + "JOIN   job j           ON j.pk_job  = l.pk_job "
            + "JOIN   job_resource jr ON jr.pk_job = j.pk_job "
            + "JOIN   show sh         ON sh.pk_show = j.pk_show "
            + "LEFT JOIN layer_usage lu ON lu.pk_layer = l.pk_layer "
            + "LEFT JOIN layer_mem   lm ON lm.pk_layer = l.pk_layer "
            + "LEFT JOIN layer_stat  ls ON ls.pk_layer = l.pk_layer "
            // Folder core ceiling + the folder's running cores, both from
            // folder_resource. int_cores is the cores the folder's procs reserve: the
            // commit adds each booking's real reservation to it (addJobUsage) and
            // every proc release subtracts it, and it is the figure the folder cap is
            // enforced against in the database. A layer's int_cores_min is only a
            // floor on what a frame reserves (memory sizing books threadable layers
            // wider), so a count built from running frames x int_cores_min undercounts
            // a folder and lets the plan carry it past a cap the commit then rejects.
            + "LEFT JOIN folder_resource fr ON fr.pk_folder = j.pk_folder "
            + "WHERE  j.str_state = 'PENDING' "
            + "  AND  j.b_paused  = false "
            + "  AND  jr.int_cores  < jr.int_max_cores "
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
            // ceiling is enforced by the post-plan folder trim in Maestro.doTick, which,
            // unlike this filter, also binds the frames planHost books in the tick
            // that crosses the cap.
            + "  AND (COALESCE(fr.int_max_cores, -1) = -1 "
            + "       OR COALESCE(fr.int_cores, 0) + l.int_cores_min <= fr.int_max_cores) "
            + "  AND (? OR sh.b_scheduler_managed = true) ";

    // Every subscription, read once per tick beside the candidate rows: a show is a
    // candidate on a group only through its subscription to the group's allocation,
    // and only while under its burst (Maestro.groupCandidates).
    private static final String SELECT_SUBSCRIPTIONS =
            "SELECT pk_show, pk_alloc, int_cores, int_burst, int_size FROM subscription";
    // spotless:on

    // A proc carries pk_layer directly, so no join is needed. A just-completed proc has been
    // unbooked (row deleted), so only live placements appear.
    private static final String SELECT_RUNNING_FRAMES_BY_HOST_LAYER =
            "SELECT pk_host, pk_layer, COUNT(*) AS n FROM proc "
                    + "WHERE pk_layer IS NOT NULL GROUP BY pk_host, pk_layer";

    // ---- row mappers ------------------------------------------------------

    private static final RowMapper<BookableHost> HOST_MAPPER = new RowMapper<BookableHost>() {
        public BookableHost mapRow(ResultSet rs, int rowNum) throws SQLException {
            BookableHost host = new BookableHost();
            host.hostId = rs.getString("pk_host");
            host.hostName = rs.getString("str_name");
            host.pkAlloc = rs.getString("pk_alloc");
            host.pkFacility = rs.getString("pk_facility");
            host.threadMode = rs.getInt("int_thread_mode");
            host.coresTotal = rs.getInt("int_cores");
            host.coresIdle = rs.getInt("int_cores_idle");
            host.memTotal = rs.getLong("int_mem");
            host.memIdle = rs.getLong("int_mem_idle");
            host.gpusTotal = rs.getInt("int_gpus");
            host.gpusIdle = rs.getInt("int_gpus_idle");
            host.gpuMemTotal = rs.getLong("int_gpu_mem");
            host.gpuMemIdle = rs.getLong("int_gpu_mem_idle");
            host.runningProcs = rs.getInt("int_procs");
            host.tagsRaw = rs.getString("str_tags");
            host.os = rs.getString("str_os");
            return host;
        }
    };

    private static final RowMapper<LayerCandidate> CANDIDATE_MAPPER =
            new RowMapper<LayerCandidate>() {
                public LayerCandidate mapRow(ResultSet rs, int rowNum) throws SQLException {
                    LayerCandidate candidate = new LayerCandidate();
                    candidate.layerId = rs.getString("pk_layer");
                    candidate.jobId = rs.getString("pk_job");
                    candidate.showId = rs.getString("pk_show");
                    candidate.layerCoresMin = rs.getInt("int_cores_min");
                    candidate.layerMemMin = rs.getLong("int_mem_min");
                    candidate.threadable = rs.getBoolean("b_threadable");
                    candidate.layerCoresMax = rs.getInt("int_cores_max");
                    candidate.layerGpusMin = rs.getInt("int_gpus_min");
                    candidate.layerGpuMemMin = rs.getLong("int_gpu_mem_min");
                    candidate.priority = rs.getInt("int_priority");
                    candidate.jobCoresInUse = rs.getInt("job_cores_in_use");
                    candidate.jobMaxCores = rs.getInt("job_max_cores");
                    candidate.showCoresInUse = rs.getInt("show_cores_in_use");
                    candidate.showBurstCores = rs.getInt("show_burst");
                    candidate.showSizeCores = rs.getInt("show_size");
                    candidate.waitingFrameCount = rs.getInt("waiting_frame_count");
                    candidate.clockTimeHighSec = rs.getInt("clock_time_high");
                    candidate.frameSuccessCount = rs.getInt("frame_success_count");
                    candidate.layerMaxRssKb = rs.getLong("layer_max_rss");
                    candidate.manual = rs.getBoolean("b_manual");
                    candidate.folderId = rs.getString("folder_id");
                    candidate.folderMax = rs.getInt("folder_max"); // -1 = unlimited
                    candidate.folderRunning = rs.getInt("folder_running"); // core-points
                    // Limits bound to the layer, or null when none. Kept null
                    // rather than an empty list so the placement loop skips all
                    // limit work with one reference check.
                    List<String> limitIds = Maestro.splitIds(rs.getString("limit_ids"));
                    candidate.limitIds = limitIds.isEmpty() ? null : limitIds;
                    return candidate;
                }
            };

    private static final RowMapper<CandidateRow> CANDIDATE_ROW_MAPPER =
            (rs, rowNum) -> new CandidateRow(CANDIDATE_MAPPER.mapRow(rs, rowNum),
                    rs.getString("pk_facility"), rs.getString("str_os"), rs.getString("str_tags"));

    // ---- diagnostics ------------------------------------------------------

    // The candidate read's WHERE clauses recast as per-layer boolean columns, so the first false
    // column names the gate that excluded a pending layer. The subscription join is LEFT here
    // (unlike the real read) precisely so a missing subscription shows up as has_sub=false instead
    // of an invisible row; each column mirrors its production clause (os = ANY of the host's
    // comma-separated list, facility bind).
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
            + "   OR COALESCE(fr.int_cores, 0) + l.int_cores_min <= fr.int_max_cores) AS folder_ok, "
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

    // ---- limits -----------------------------------------------------------

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

    // ---- reads ------------------------------------------------------------

    @Override
    public List<BookableHost> getSchedulableHosts() {
        return getJdbcTemplate().query(SELECT_ALL_HOSTS, HOST_MAPPER);
    }

    @Override
    public List<ShowUsage> getLiveShowUsage(boolean facilityMode) {
        return getJdbcTemplate().query(SELECT_LIVE_SHOW_USAGE,
                (rs, rowNum) -> new ShowUsage(rs.getString("show_name"), rs.getLong("cores"),
                        rs.getLong("frames")),
                facilityMode);
    }

    @Override
    public List<CandidateRow> getCandidateRows(boolean facilityMode) {
        return getJdbcTemplate().query(SELECT_CANDIDATE_ROWS, CANDIDATE_ROW_MAPPER, facilityMode);
    }

    @Override
    public List<SubscriptionUsage> getSubscriptions() {
        return getJdbcTemplate().query(SELECT_SUBSCRIPTIONS,
                (rs, rowNum) -> new SubscriptionUsage(rs.getString("pk_show"),
                        rs.getString("pk_alloc"), rs.getLong("int_cores"), rs.getLong("int_burst"),
                        rs.getLong("int_size")));
    }

    @Override
    public List<HostLayerFrames> getRunningFramesByHostLayer() {
        return getJdbcTemplate().query(SELECT_RUNNING_FRAMES_BY_HOST_LAYER,
                (rs, rowNum) -> new HostLayerFrames(rs.getString("pk_host"),
                        rs.getString("pk_layer"), rs.getInt("n")));
    }

    @Override
    public List<GroupExclusion> explainGroupExclusions(String groupTags, String groupOs,
            String facilityId, boolean allThreadMode, int maxCoresTotal, boolean facilityMode,
            String allocId) {
        return getJdbcTemplate().query(EXPLAIN_GROUP_EXCLUSIONS, (rs, rowNum) -> {
            GroupExclusion exclusion = new GroupExclusion();
            exclusion.jobName = rs.getString("job_name");
            exclusion.layerName = rs.getString("layer_name");
            exclusion.layerTags = rs.getString("str_tags");
            exclusion.priority = rs.getInt("int_priority");
            exclusion.tagOk = rs.getBoolean("tag_ok");
            exclusion.osOk = rs.getBoolean("os_ok");
            exclusion.facilityOk = rs.getBoolean("fac_ok");
            exclusion.threadOk = rs.getBoolean("thread_ok");
            exclusion.hasSubscription = rs.getBoolean("has_sub");
            exclusion.underBurst = rs.getBoolean("under_burst");
            exclusion.underJobCap = rs.getBoolean("under_job_cap");
            exclusion.fitsCores = rs.getBoolean("fits_cores");
            exclusion.hasWaiting = rs.getBoolean("has_waiting");
            exclusion.folderOk = rs.getBoolean("folder_ok");
            exclusion.managedOk = rs.getBoolean("managed_ok");
            return exclusion;
        }, groupTags, groupOs, facilityId, allThreadMode ? 1 : 0, maxCoresTotal, facilityMode,
                allocId);
    }

    @Override
    public List<LimitUsage> getGatingLimitUsage() {
        return getJdbcTemplate().query(limitBudgetsSql(),
                (rs, rowNum) -> new LimitUsage(rs.getString("pk_limit_record"),
                        rs.getString("str_name"), rs.getString("str_type"),
                        rs.getInt("int_soft_value"), rs.getInt("int_max_value"),
                        rs.getInt("usage_val")));
    }

    @Override
    public Map<String, Set<String>> getHostLimitHolders() {
        Map<String, Set<String>> holders = new HashMap<>();
        getJdbcTemplate().query(SELECT_LIMIT_HOLDERS, rs -> {
            holders.computeIfAbsent(rs.getString("id"), limitId -> new HashSet<>())
                    .add(rs.getString("host"));
        });
        return holders;
    }

    @Override
    public List<RunningProcEstimate> getRunningProcEstimates(List<String> hostIds) {
        String in = hostIds.stream().map(hostId -> "?").collect(Collectors.joining(","));
        String sql = "SELECT p.pk_host AS pk_host, p.int_cores_reserved AS cores, "
                + "EXTRACT(EPOCH FROM (now() - p.ts_dispatched))::int AS elapsed_sec, "
                + "CASE WHEN lu.int_frame_success_count > 0 "
                + "     THEN lu.int_clock_time_success / lu.int_frame_success_count "
                + "     ELSE -1 END AS avg_sec " + "FROM proc p "
                + "LEFT JOIN layer_usage lu ON lu.pk_layer = p.pk_layer " + "WHERE p.pk_host IN ("
                + in + ")";
        return getJdbcTemplate().query(
                sql, (rs, rowNum) -> new RunningProcEstimate(rs.getString("pk_host"),
                        rs.getInt("cores"), rs.getInt("elapsed_sec"), rs.getInt("avg_sec")),
                hostIds.toArray());
    }

    // ---- resource mirrors -------------------------------------------------

    @Override
    public void addSubscriptionUsage(List<SubscriptionDelta> deltas) {
        List<Object[]> burstBatch = new ArrayList<>(deltas.size());
        List<Object[]> pairBatch = new ArrayList<>(deltas.size());
        for (SubscriptionDelta delta : deltas) {
            burstBatch.add(new Object[] {delta.cores, delta.showId, delta.allocId});
            pairBatch.add(new Object[] {delta.cores, delta.cores, delta.gpus, delta.showId,
                    delta.allocId});
        }
        // Same cap-neutral pair trick as addJobUsage: verify_subscription
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

    @Override
    public void addLayerUsage(List<ResourceDelta> deltas) {
        List<Object[]> batch = new ArrayList<>(deltas.size());
        for (ResourceDelta delta : deltas) {
            batch.add(new Object[] {delta.cores, delta.gpus, delta.id});
        }
        getJdbcTemplate().batchUpdate("UPDATE layer_resource SET int_cores = int_cores + ?, "
                + "int_gpus = int_gpus + ? WHERE pk_layer = ?", batch);
    }

    @Override
    public void addJobUsage(List<ResourceDelta> deltas) {
        List<Object[]> jobBatch = new ArrayList<>(deltas.size());
        List<Object[]> pairBatch = new ArrayList<>(deltas.size());
        List<Object[]> pointBatch = new ArrayList<>(deltas.size());
        for (ResourceDelta delta : deltas) {
            jobBatch.add(new Object[] {delta.cores, delta.gpus, delta.id});
            pairBatch
                    .add(new Object[] {delta.cores, delta.cores, delta.gpus, delta.gpus, delta.id});
            pointBatch.add(new Object[] {delta.cores, delta.gpus, delta.id, delta.id});
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

    // ---- planning lock ----------------------------------------------------

    @Override
    public boolean tryAcquireSchedulerLock(Connection connection) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement("SELECT pg_try_advisory_lock(?)")) {
            ps.setLong(1, SCHEDULER_LOCK_KEY);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() && rs.getBoolean(1);
            }
        }
    }

    @Override
    public void releaseSchedulerLock(Connection connection) throws SQLException {
        try (PreparedStatement ps = connection.prepareStatement("SELECT pg_advisory_unlock(?)")) {
            ps.setLong(1, SCHEDULER_LOCK_KEY);
            ps.execute();
        }
    }
}
