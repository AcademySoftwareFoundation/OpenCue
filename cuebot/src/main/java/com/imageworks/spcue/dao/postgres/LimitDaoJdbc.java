
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

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.support.JdbcDaoSupport;

import com.imageworks.spcue.LimitEntity;
import com.imageworks.spcue.LimitInterface;
import com.imageworks.spcue.LimitRule;
import com.imageworks.spcue.dao.LimitDao;
import com.imageworks.spcue.grpc.limit.LimitBindSource;
import com.imageworks.spcue.grpc.limit.LimitBinding;
import com.imageworks.spcue.grpc.limit.LimitEnforcement;
import com.imageworks.spcue.grpc.limit.LimitHold;
import com.imageworks.spcue.grpc.limit.LimitHoldSource;
import com.imageworks.spcue.grpc.limit.LimitHostUsage;
import com.imageworks.spcue.grpc.limit.LimitType;
import com.imageworks.spcue.util.SqlUtil;

public class LimitDaoJdbc extends JdbcDaoSupport implements LimitDao {

    /**
     * Normalizes a hostname column to the key limit_host rows are stored under: short hostname,
     * lowercased. License servers report anything from a bare name to an FQDN, and so may hosts.
     */
    private static String normHost(String column) {
        return "SPLIT_PART(LOWER(" + column + "), '.', 1)";
    }

    /**
     * Lower bound of the pending scan for one limit: bookings after this instant have not yet had a
     * chance to be observed by the license server.
     *
     * A limit that has never been reported has no ground truth, so every running proc of a bound
     * layer is pending -- exactly the pre-settlement counting. A reported limit reaches back a
     * settle window before its watermark, because a checkout takes time to appear on the license
     * server: a frame dispatched just before the snapshot may be in neither. Hosts the snapshot
     * already covers are de-duped against limit_host, so reaching back cannot double count.
     *
     * A reporter that stops therefore grows pending toward every running proc rather than opening a
     * blind spot between the watermark and the window. That is the fail-closed direction and it is
     * already bounded: past int_report_ttl the limit stops blocking altogether.
     *
     * Mirrored in DispatchQuery.PENDING_BOUND/USAGE_EXPR, which gates booking. The CueGUI "In Use"
     * column and the dispatch gate must count identically, so any change to the counting rule has
     * to be made in both places.
     */
    private static String pendingBound(int settleWindowSeconds) {
        return "CASE WHEN limit_record.ts_reported IS NULL THEN TO_TIMESTAMP(0) "
                + "ELSE limit_record.ts_reported - (" + settleWindowSeconds
                + " * INTERVAL '1 second') END";
    }

    /** Running frames of bound layers booked after the watermark. */
    private static String pendingFrames(int settleWindowSeconds) {
        return "(SELECT COUNT(*) FROM proc "
                + "JOIN layer_limit ON layer_limit.pk_layer = proc.pk_layer "
                + "WHERE layer_limit.pk_limit_record = limit_record.pk_limit_record "
                + "AND proc.ts_dispatched > " + pendingBound(settleWindowSeconds) + ")";
    }

    /**
     * Distinct hosts with pending bookings that the license server has not already reported holding
     * -- a host in both sets is settled, not pending.
     */
    private static String pendingHosts(int settleWindowSeconds) {
        return "(SELECT COUNT(DISTINCT proc.pk_host) FROM proc "
                + "JOIN layer_limit ON layer_limit.pk_layer = proc.pk_layer "
                + "WHERE layer_limit.pk_limit_record = limit_record.pk_limit_record "
                + "AND proc.ts_dispatched > " + pendingBound(settleWindowSeconds) + " "
                + "AND NOT EXISTS (" + "SELECT 1 FROM limit_host, host "
                + "WHERE limit_host.pk_limit_record = limit_record.pk_limit_record "
                + "AND host.pk_host = proc.pk_host " + "AND limit_host.str_host_name = "
                + normHost("host.str_name") + "))";
    }

    /**
     * The full per-limit query: configuration columns plus the settlement-model usage numbers.
     * Settled comes from the precomputed limit_usage row; pending is scanned live so a fresh
     * booking counts immediately. All usage values are in the limit's own unit -- tokens for FRAME
     * limits, distinct machines for HOST limits.
     */
    public static String limitQuery(int settleWindowSeconds) {
        String pendingFrames = pendingFrames(settleWindowSeconds);
        String pendingHosts = pendingHosts(settleWindowSeconds);
        // spotless:off
        return "SELECT "
                + "limit_record.pk_limit_record, "
                + "limit_record.str_name, "
                + "limit_record.int_max_value, "
                + "limit_record.str_type, "
                + "limit_record.str_enforcement, "
                + "limit_record.int_soft_value, "
                + "limit_record.ts_reported, "
                + "limit_record.str_report_source, "
                + "limit_record.int_report_ttl, "
                + "limit_record.int_exit_status, "
                + "limit_record.int_delay_minutes, "
                + "limit_record.b_auto_tag, "
                + "CASE WHEN limit_record.str_type = 'HOST' "
                    + "THEN COALESCE(limit_usage.int_settled_hosts, 0) "
                    + "ELSE COALESCE(limit_usage.int_settled_usage, 0) END AS int_settled_usage, "
                + "CASE WHEN limit_record.str_type = 'HOST' "
                    + "THEN " + pendingHosts + " "
                    + "ELSE " + pendingFrames + " END AS int_pending_usage, "
                + "COALESCE(limit_usage.int_settled_hosts, 0) + " + pendingHosts
                    + " AS int_host_count, "
                + "(SELECT COUNT(*) FROM layer_limit "
                    + "WHERE layer_limit.pk_limit_record = limit_record.pk_limit_record "
                    + "AND layer_limit.str_source = 'SPEC') AS int_spec_layer_count, "
                + "(SELECT COUNT(*) FROM layer_limit "
                    + "WHERE layer_limit.pk_limit_record = limit_record.pk_limit_record "
                    + "AND layer_limit.str_source = 'AUTO') AS int_auto_layer_count "
            + "FROM "
                + "limit_record "
            + "LEFT JOIN "
                + "limit_usage ON limit_usage.pk_limit_record = limit_record.pk_limit_record ";
        // spotless:on
    }

    /**
     * Populates a LimitEntity from a limitQuery() row. Public so the whiteboard maps the same
     * columns and the two surfaces cannot disagree.
     */
    public static LimitEntity mapLimitRow(ResultSet rs) throws SQLException {
        LimitEntity limit = new LimitEntity();
        limit.id = rs.getString("pk_limit_record");
        limit.name = rs.getString("str_name");
        limit.maxValue = rs.getInt("int_max_value");
        limit.type = LimitType.valueOf(rs.getString("str_type"));
        limit.enforcement = LimitEnforcement.valueOf(rs.getString("str_enforcement"));
        limit.softValue = rs.getInt("int_soft_value");
        Timestamp reported = rs.getTimestamp("ts_reported");
        limit.reportedTime = reported == null ? 0 : reported.getTime();
        limit.reportSource = SqlUtil.getString(rs, "str_report_source");
        limit.reportTtl = rs.getInt("int_report_ttl");
        int exitStatus = rs.getInt("int_exit_status");
        limit.exitStatus = rs.wasNull() ? null : exitStatus;
        limit.delayMinutes = rs.getInt("int_delay_minutes");
        limit.autoTag = rs.getBoolean("b_auto_tag");
        limit.settledUsage = rs.getInt("int_settled_usage");
        limit.pendingUsage = rs.getInt("int_pending_usage");
        limit.hostCount = rs.getInt("int_host_count");
        limit.specLayerCount = rs.getInt("int_spec_layer_count");
        limit.autoLayerCount = rs.getInt("int_auto_layer_count");
        limit.currentRunning = limit.getCurrentUsage();
        return limit;
    }

    public static final RowMapper<LimitEntity> LIMIT_MAPPER = new RowMapper<LimitEntity>() {
        public LimitEntity mapRow(ResultSet rs, int rowNum) throws SQLException {
            return mapLimitRow(rs);
        }
    };

    private final String getLimitQueryBase;

    @Autowired
    public LimitDaoJdbc(Environment env) {
        // Default mirrored in DispatcherDaoJdbc and WhiteboardDaoJdbc; keep the three in step.
        this.getLimitQueryBase =
                limitQuery(env.getProperty("limit.settle_window_seconds", Integer.class, 120));
    }

    @Override
    public String createLimit(String name, int maxValue, LimitType type,
            LimitEnforcement enforcement, int softValue) {
        String limitId = SqlUtil.genKeyRandom();
        getJdbcTemplate().update(
                "INSERT INTO limit_record "
                        + "(pk_limit_record, str_name, int_max_value, str_type, str_enforcement, "
                        + "int_soft_value) VALUES (?,?,?,?,?,?)",
                limitId, name, maxValue, type.toString(), enforcement.toString(),
                softValue < 0 ? -1 : softValue);
        refreshUsageById(limitId);
        return limitId;
    }

    @Override
    @Deprecated
    public String createLimit(String name, int maxValue) {
        return createLimit(name, maxValue, LimitType.FRAME, LimitEnforcement.ENFORCED, -1);
    }

    @Override
    public void deleteLimit(LimitInterface limit) {
        getJdbcTemplate().update("DELETE FROM " + "limit_record " + "WHERE " + "pk_limit_record=?",
                limit.getId());
    }

    @Override
    public LimitEntity findLimit(String name) {
        return getJdbcTemplate().queryForObject(getLimitQueryBase + "WHERE limit_record.str_name=?",
                LIMIT_MAPPER, name);
    }

    @Override
    public List<String> findMissingLimitNames(Collection<String> names) {
        Set<String> uniqueNames = new LinkedHashSet<String>(names);
        if (uniqueNames.isEmpty()) {
            return Collections.emptyList();
        }

        String placeholders =
                uniqueNames.stream().map(name -> "?").collect(Collectors.joining(","));
        Set<String> existing = new HashSet<String>(getJdbcTemplate().queryForList(
                "SELECT str_name FROM limit_record WHERE str_name IN (" + placeholders + ")",
                String.class, uniqueNames.toArray()));

        return uniqueNames.stream().filter(name -> !existing.contains(name))
                .collect(Collectors.toList());
    }

    @Override
    public LimitEntity getLimit(String id) {
        return getJdbcTemplate().queryForObject(
                getLimitQueryBase + "WHERE limit_record.pk_limit_record=?", LIMIT_MAPPER, id);
    }

    @Override
    public List<LimitEntity> getLimits() {
        return getJdbcTemplate().query(getLimitQueryBase + "ORDER BY limit_record.str_name",
                LIMIT_MAPPER);
    }

    @Override
    public void setLimitName(LimitInterface limit, String name) {
        getJdbcTemplate().update("UPDATE " + "limit_record " + "SET " + "str_name = ? " + "WHERE "
                + "pk_limit_record = ?", name, limit.getId());
    }

    @Override
    public void setMaxValue(LimitInterface limit, int maxValue) {
        getJdbcTemplate().update("UPDATE " + "limit_record " + "SET " + "int_max_value = ? "
                + "WHERE " + "pk_limit_record = ?", maxValue, limit.getId());
    }

    @Override
    public void setSoftValue(LimitInterface limit, int value) {
        // -1 is the only "same as max_value" sentinel the dispatch gate understands: it tests
        // int_soft_value >= 0, so a stored 0 would mean "no host that isn't already holding may
        // ever book". Fold 0 into -1 here so every write path agrees with create.
        getJdbcTemplate().update(
                "UPDATE limit_record SET int_soft_value = ? " + "WHERE pk_limit_record = ?",
                value <= 0 ? -1 : value, limit.getId());
    }

    @Override
    public void setLimitType(LimitInterface limit, LimitType type) {
        getJdbcTemplate().update("UPDATE limit_record SET str_type = ? WHERE pk_limit_record = ?",
                type.toString(), limit.getId());
    }

    @Override
    public void setEnforcement(LimitInterface limit, LimitEnforcement enforcement) {
        getJdbcTemplate().update(
                "UPDATE limit_record SET str_enforcement = ? WHERE pk_limit_record = ?",
                enforcement.toString(), limit.getId());
    }

    @Override
    public void setReportTtl(LimitInterface limit, int seconds) {
        getJdbcTemplate().update(
                "UPDATE limit_record SET int_report_ttl = ? WHERE pk_limit_record = ?",
                Math.max(0, seconds), limit.getId());
    }

    @Override
    public void setFailureRule(LimitInterface limit, Integer exitStatus, int delayMinutes,
            boolean autoTag) {
        getJdbcTemplate().update(
                "UPDATE limit_record SET int_exit_status = ?, int_delay_minutes = ?, "
                        + "b_auto_tag = ? WHERE pk_limit_record = ?",
                exitStatus, delayMinutes, autoTag, limit.getId());
    }

    @Override
    public Map<Integer, LimitRule> getFailureRules() {
        Map<Integer, LimitRule> rules = new HashMap<Integer, LimitRule>();
        getJdbcTemplate().query(
                "SELECT pk_limit_record, str_name, int_exit_status, int_delay_minutes, b_auto_tag "
                        + "FROM limit_record WHERE int_exit_status IS NOT NULL",
                rs -> {
                    LimitRule rule = new LimitRule(rs.getString("pk_limit_record"),
                            rs.getString("str_name"), rs.getInt("int_exit_status"),
                            rs.getInt("int_delay_minutes"), rs.getBoolean("b_auto_tag"));
                    rules.put(rule.exitStatus, rule);
                });
        return rules;
    }

    private static final RowMapper<LimitBinding> BINDING_MAPPER = new RowMapper<LimitBinding>() {
        public LimitBinding mapRow(ResultSet rs, int rowNum) throws SQLException {
            LimitBinding.Builder builder =
                    LimitBinding.newBuilder().setLimitId(SqlUtil.getString(rs, "pk_limit_record"))
                            .setLayerId(SqlUtil.getString(rs, "pk_layer"))
                            .setLayerName(SqlUtil.getString(rs, "str_layer_name"))
                            .setJobName(SqlUtil.getString(rs, "str_job_name"))
                            .setSource(LimitBindSource.valueOf(rs.getString("str_source")))
                            .setCreateTime(rs.getTimestamp("ts_created").getTime() / 1000);
            String services = SqlUtil.getString(rs, "str_services");
            if (!services.isEmpty()) {
                for (String service : services.split(",")) {
                    builder.addServices(service);
                }
            }
            return builder.build();
        }
    };

    // spotless:off
    private static final String GET_BINDINGS =
            "SELECT "
                + "layer_limit.pk_limit_record, "
                + "layer_limit.pk_layer, "
                + "layer_limit.str_source, "
                + "layer_limit.ts_created, "
                + "layer.str_name AS str_layer_name, "
                + "layer.str_services, "
                + "job.str_name AS str_job_name "
            + "FROM "
                + "layer_limit "
            + "JOIN layer ON layer.pk_layer = layer_limit.pk_layer "
            + "JOIN job ON job.pk_job = layer.pk_job "
            + "WHERE "
                + "layer_limit.pk_limit_record = ? ";
    // spotless:on

    @Override
    public List<LimitBinding> getBindings(LimitInterface limit, Set<LimitBindSource> sources,
            Collection<String> layerIds) {
        StringBuilder query = new StringBuilder(GET_BINDINGS);
        List<Object> args = new ArrayList<Object>();
        args.add(limit.getId());
        appendSourceFilter(query, args, sources);
        appendLayerFilter(query, args, layerIds);
        query.append("ORDER BY layer_limit.ts_created DESC");
        return getJdbcTemplate().query(query.toString(), BINDING_MAPPER, args.toArray());
    }

    private static void appendLayerFilter(StringBuilder query, List<Object> args,
            Collection<String> layerIds) {
        if (layerIds == null || layerIds.isEmpty()) {
            return;
        }
        query.append("AND layer_limit.pk_layer IN (");
        boolean first = true;
        for (String layerId : layerIds) {
            query.append(first ? "?" : ",?");
            args.add(layerId);
            first = false;
        }
        query.append(") ");
    }

    @Override
    public int clearBindings(LimitInterface limit, Set<LimitBindSource> sources) {
        StringBuilder query = new StringBuilder(
                "DELETE FROM layer_limit WHERE pk_limit_record = ? AND str_source != 'SPEC' ");
        List<Object> args = new ArrayList<Object>();
        args.add(limit.getId());
        appendSourceFilter(query, args, sources);
        return getJdbcTemplate().update(query.toString(), args.toArray());
    }

    private static void appendSourceFilter(StringBuilder query, List<Object> args,
            Set<LimitBindSource> sources) {
        if (sources == null || sources.isEmpty()) {
            return;
        }
        query.append("AND str_source IN (");
        boolean first = true;
        for (LimitBindSource source : sources) {
            query.append(first ? "?" : ",?");
            args.add(source.toString());
            first = false;
        }
        query.append(") ");
    }

    // An unchanged holder produces no new row version at all, which is the common case; that is
    // what keeps a 5-second reporter from bloating the table. fillfactor 70 keeps the updates
    // that do happen HOT.
    // spotless:off
    private static final String UPSERT_HOLD =
            "INSERT INTO limit_host "
                + "(pk_limit_host, pk_limit_record, str_host_name, str_reported_name, int_tokens, "
                + "str_user, ts_reported) "
            + "VALUES (?, ?, ?, ?, ?, ?, ?) "
            + "ON CONFLICT (pk_limit_record, str_host_name) DO UPDATE SET "
                + "int_tokens = EXCLUDED.int_tokens, "
                + "str_user = EXCLUDED.str_user, "
                + "str_reported_name = EXCLUDED.str_reported_name, "
                + "ts_reported = EXCLUDED.ts_reported "
            + "WHERE "
                + "limit_host.int_tokens IS DISTINCT FROM EXCLUDED.int_tokens "
                + "OR limit_host.str_user IS DISTINCT FROM EXCLUDED.str_user";
    // spotless:on

    @Override
    public boolean claimReportWatermark(LimitInterface limit, Timestamp captureTime, String source,
            long minIntervalMs) {
        // A losing concurrent reporter blocks on the row lock here, then re-evaluates the WHERE
        // against the winner's committed watermark and updates zero rows. That also serializes
        // the hold rewrites that follow a successful claim.
        return getJdbcTemplate().update(
                "UPDATE limit_record SET ts_reported = ?, str_report_source = ? "
                        + "WHERE pk_limit_record = ? AND (ts_reported IS NULL "
                        + "OR (ts_reported <= ? AND ts_reported <= ?))",
                captureTime, source, limit.getId(), captureTime,
                new Timestamp(System.currentTimeMillis() - minIntervalMs)) == 1;
    }

    @Override
    public void replaceExternalHolds(LimitInterface limit, List<LimitHostUsage> holds,
            String source, Timestamp captureTime) {
        Timestamp batchTime = new Timestamp(System.currentTimeMillis());

        // Coalesce duplicate hostnames after normalization (an FQDN and a short name for the same
        // machine) to the highest token count seen.
        Map<String, LimitHostUsage> byHost = new HashMap<String, LimitHostUsage>();
        for (LimitHostUsage hold : holds) {
            String key = normalizeHostName(hold.getHostName());
            if (key.isEmpty() || hold.getTokens() <= 0) {
                continue;
            }
            LimitHostUsage existing = byHost.get(key);
            if (existing == null || hold.getTokens() > existing.getTokens()) {
                byHost.put(key, hold);
            }
        }

        // One round-trip for the whole snapshot: a site reporting thousands of holders every
        // poll would otherwise spend the transaction on per-row latency while holding their locks.
        List<Object[]> upserts = new ArrayList<Object[]>(byHost.size());
        for (Map.Entry<String, LimitHostUsage> entry : byHost.entrySet()) {
            LimitHostUsage hold = entry.getValue();
            upserts.add(new Object[] {SqlUtil.genKeyRandom(), limit.getId(), entry.getKey(),
                    hold.getHostName(), hold.getTokens(), hold.getUser(), batchTime});
        }
        if (!upserts.isEmpty()) {
            getJdbcTemplate().batchUpdate(UPSERT_HOLD, upserts);
        }

        // Sweep holders absent from this snapshot. Matching on the batch's hostname set rather
        // than ts_reported keeps unchanged holders (whose rows were deliberately not rewritten)
        // alive.
        if (byHost.isEmpty()) {
            getJdbcTemplate().update("DELETE FROM limit_host WHERE pk_limit_record = ?",
                    limit.getId());
        } else {
            StringBuilder sweep = new StringBuilder(
                    "DELETE FROM limit_host WHERE pk_limit_record = ? AND str_host_name NOT IN (");
            List<Object> args = new ArrayList<Object>();
            args.add(limit.getId());
            boolean first = true;
            for (String hostName : byHost.keySet()) {
                sweep.append(first ? "?" : ",?");
                args.add(hostName);
                first = false;
            }
            sweep.append(")");
            getJdbcTemplate().update(sweep.toString(), args.toArray());
        }

        getJdbcTemplate().update("UPDATE limit_record SET ts_reported = ?, str_report_source = ? "
                + "WHERE pk_limit_record = ?", captureTime, source, limit.getId());
    }

    /** Reduces a reported hostname to the normalized join key: short hostname, lowercased. */
    public static String normalizeHostName(String name) {
        if (name == null) {
            return "";
        }
        String trimmed = name.trim().toLowerCase(java.util.Locale.ROOT);
        int dot = trimmed.indexOf('.');
        return dot < 0 ? trimmed : trimmed.substring(0, dot);
    }

    // spotless:off
    private static final String REFRESH_USAGE =
            "INSERT INTO limit_usage "
                + "(pk_limit_record, int_settled_usage, int_settled_hosts, ts_watermark, ts_updated) "
            + "SELECT "
                + "limit_record.pk_limit_record, "
                + "COALESCE(SUM(limit_host.int_tokens), 0), "
                + "COUNT(limit_host.pk_limit_host), "
                + "limit_record.ts_reported, "
                + "current_timestamp "
            + "FROM limit_record "
            + "LEFT JOIN limit_host ON limit_host.pk_limit_record = limit_record.pk_limit_record "
            + "%s"
            + "GROUP BY limit_record.pk_limit_record, limit_record.ts_reported "
            + "ON CONFLICT (pk_limit_record) DO UPDATE SET "
                + "int_settled_usage = EXCLUDED.int_settled_usage, "
                + "int_settled_hosts = EXCLUDED.int_settled_hosts, "
                + "ts_watermark = EXCLUDED.ts_watermark, "
                + "ts_updated = EXCLUDED.ts_updated "
            + "WHERE "
                + "limit_usage.int_settled_usage IS DISTINCT FROM EXCLUDED.int_settled_usage "
                + "OR limit_usage.int_settled_hosts IS DISTINCT FROM EXCLUDED.int_settled_hosts "
                + "OR limit_usage.ts_watermark IS DISTINCT FROM EXCLUDED.ts_watermark";
    // spotless:on

    @Override
    public void refreshUsage(LimitInterface limit) {
        refreshUsageById(limit.getId());
    }

    private void refreshUsageById(String limitId) {
        getJdbcTemplate().update(
                String.format(REFRESH_USAGE, "WHERE limit_record.pk_limit_record = ? "), limitId);
    }

    @Override
    public void refreshAllUsage() {
        getJdbcTemplate().update(String.format(REFRESH_USAGE, ""));
    }

    /**
     * Every host holding at least one token: external holds from the license server, hosts running
     * frames of bound layers, or both. The external side resolves pk_host by hostname at read time,
     * so a workstation that later joins the farm starts matching automatically.
     */
    // spotless:off
    private static final String GET_HOLDS =
            "SELECT "
                + "limit_record.pk_limit_record, "
                + "limit_record.str_name AS str_limit_name, "
                + "limit_record.str_type, "
                + "holders.str_host_name, "
                + "COALESCE(cue_host.pk_host, '') AS pk_host, "
                + "external_hold.int_tokens AS int_external_tokens, "
                + "external_hold.str_user, "
                + "external_hold.ts_reported, "
                + "COALESCE(cue.int_procs, 0) AS int_procs "
            + "FROM limit_record "
            + "JOIN ("
                + "SELECT pk_limit_record, str_host_name FROM limit_host "
                + "UNION "
                + "SELECT layer_limit.pk_limit_record, "
                    + "SPLIT_PART(LOWER(host.str_name), '.', 1) "
                + "FROM proc "
                + "JOIN layer_limit ON layer_limit.pk_layer = proc.pk_layer "
                + "JOIN host ON host.pk_host = proc.pk_host"
            + ") AS holders ON holders.pk_limit_record = limit_record.pk_limit_record "
            + "LEFT JOIN limit_host external_hold "
                + "ON external_hold.pk_limit_record = limit_record.pk_limit_record "
                + "AND external_hold.str_host_name = holders.str_host_name "
            + "LEFT JOIN host cue_host "
                + "ON SPLIT_PART(LOWER(cue_host.str_name), '.', 1) = holders.str_host_name "
            + "LEFT JOIN LATERAL ("
                + "SELECT COUNT(*) AS int_procs FROM proc "
                + "JOIN layer_limit ON layer_limit.pk_layer = proc.pk_layer "
                + "WHERE layer_limit.pk_limit_record = limit_record.pk_limit_record "
                + "AND proc.pk_host = cue_host.pk_host"
            + ") AS cue ON true ";
    // spotless:on

    private static final RowMapper<LimitHold> HOLD_MAPPER = new RowMapper<LimitHold>() {
        public LimitHold mapRow(ResultSet rs, int rowNum) throws SQLException {
            int externalTokens = rs.getInt("int_external_tokens");
            boolean external = !rs.wasNull();
            int procs = rs.getInt("int_procs");
            boolean cue = procs > 0;

            int tokens;
            if (external) {
                tokens = externalTokens;
            } else if ("HOST".equals(rs.getString("str_type"))) {
                tokens = 1;
            } else {
                tokens = procs;
            }

            Timestamp reported = rs.getTimestamp("ts_reported");
            return LimitHold.newBuilder().setLimitId(SqlUtil.getString(rs, "pk_limit_record"))
                    .setLimitName(SqlUtil.getString(rs, "str_limit_name"))
                    .setHostName(SqlUtil.getString(rs, "str_host_name"))
                    .setHostId(SqlUtil.getString(rs, "pk_host")).setTokens(tokens)
                    .setUser(SqlUtil.getString(rs, "str_user"))
                    .setSource(external && cue ? LimitHoldSource.BOTH
                            : external ? LimitHoldSource.EXTERNAL : LimitHoldSource.CUE)
                    .setReportTime(reported == null ? 0 : reported.getTime() / 1000).build();
        }
    };

    @Override
    public List<LimitHold> getHolds(LimitInterface limit, String hostName) {
        return queryHolds(limit.getId(), hostName);
    }

    @Override
    public List<LimitHold> getHolds(String hostName) {
        return queryHolds(null, hostName);
    }

    private List<LimitHold> queryHolds(String limitId, String hostName) {
        StringBuilder query = new StringBuilder(GET_HOLDS);
        List<Object> args = new ArrayList<Object>();
        query.append("WHERE 1=1 ");
        if (limitId != null) {
            query.append("AND limit_record.pk_limit_record = ? ");
            args.add(limitId);
        }
        // Both sides of the UNION already produce the normalized short name, so the caller may
        // pass either an FQDN or a short name.
        String normalized = normalizeHostName(hostName);
        if (!normalized.isEmpty()) {
            query.append("AND holders.str_host_name = ? ");
            args.add(normalized);
        }
        query.append("ORDER BY limit_record.str_name, holders.str_host_name");
        return getJdbcTemplate().query(query.toString(), HOLD_MAPPER, args.toArray());
    }
}
