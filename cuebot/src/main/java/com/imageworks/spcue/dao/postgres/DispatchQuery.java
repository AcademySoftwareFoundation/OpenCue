
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

public class DispatchQuery {

    /**
     * Placeholder for limit.settle_window_seconds, resolved by DispatcherDaoJdbc at startup. Query
     * constants cannot read properties, and binding the window as a parameter would touch every
     * call site's argument array.
     */
    public static final String SETTLE_WINDOW_TOKEN = "__LIMIT_SETTLE_SEC__";

    /**
     * Placeholder in the frame queries' ORDER BY for the license-affinity sort key. Resolved by
     * DispatcherDaoJdbc to {@link #AFFINITY_ORDER_SQL} (which binds the host name twice, ahead of
     * every other parameter) when dispatcher.limit.affinity_ordering_enabled is true, or to nothing
     * when it is off.
     */
    public static final String AFFINITY_ORDER_TOKEN = "__LIMIT_AFFINITY_ORDER__";

    /**
     * Sorts layers that would need this host to acquire a NEW license last, within the job. A layer
     * with no license limits and a layer whose licenses this host already holds are
     * indistinguishable at position 0, so unlicensed work is never penalized. Applies to ADVISORY
     * limits too: it never blocks anything, it only chooses among work already eligible.
     */
    // spotless:off
    public static final String AFFINITY_ORDER_SQL =
            "CASE WHEN EXISTS ("
                + "SELECT 1 FROM layer_limit aff_ll "
                + "JOIN limit_record aff_lr ON aff_lr.pk_limit_record = aff_ll.pk_limit_record "
                + "WHERE aff_ll.pk_layer = frame.pk_layer "
                + "AND aff_lr.str_type = 'HOST' "
                + "AND aff_lr.str_enforcement != 'DISABLED' "
                + "AND NOT ("
                    + "EXISTS ("
                        + "SELECT 1 FROM limit_host aff_lh "
                        + "WHERE aff_lh.pk_limit_record = aff_lr.pk_limit_record "
                        + "AND aff_lh.str_host_name = SPLIT_PART(LOWER(:hostName), '.', 1)) "
                    + "OR EXISTS ("
                        + "SELECT 1 FROM proc aff_p "
                        + "JOIN host aff_h ON aff_h.pk_host = aff_p.pk_host "
                        + "JOIN layer_limit aff_pll ON aff_pll.pk_layer = aff_p.pk_layer "
                        + "WHERE aff_pll.pk_limit_record = aff_lr.pk_limit_record "
                        + "AND aff_h.str_name = :hostName)"
                + ")"
            + ") THEN 1 ELSE 0 END ASC, ";
    // spotless:on

    /**
     * Lower bound of the pending scan: bookings after this instant have not yet had a chance to be
     * observed by the license server.
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
     * Mirrored in LimitDaoJdbc.pendingBound/pendingFrames/pendingHosts, which feed the whiteboard's
     * usage columns. The dispatch gate and the CueGUI "In Use" column must count identically, so
     * any change to the counting rule has to be made in both places.
     */
    // spotless:off
    private static final String PENDING_BOUND =
            "CASE WHEN limit_record.ts_reported IS NULL THEN TO_TIMESTAMP(0) "
            + "ELSE limit_record.ts_reported - ("
                + SETTLE_WINDOW_TOKEN + " * INTERVAL '1 second') END";

    /**
     * Merged usage for the limit in scope: the precomputed settled row plus the live pending
     * scan, in the limit's own unit (tokens for FRAME, distinct machines for HOST). Pending hosts
     * the server already reports holding are settled, not pending, and are not counted twice.
     * Evaluated only inside {@link #LIMIT_USAGE_CTE}, once per limit per query.
     */
    private static final String USAGE_EXPR =
            "(CASE WHEN limit_record.str_type = 'HOST' THEN "
                + "COALESCE(limit_usage.int_settled_hosts, 0) + ("
                    + "SELECT COUNT(DISTINCT pnd.pk_host) FROM proc pnd "
                    + "JOIN layer_limit pnd_ll ON pnd_ll.pk_layer = pnd.pk_layer "
                    + "WHERE pnd_ll.pk_limit_record = limit_record.pk_limit_record "
                    + "AND pnd.ts_dispatched > " + PENDING_BOUND + " "
                    + "AND NOT EXISTS ("
                        + "SELECT 1 FROM limit_host stl, host sth "
                        + "WHERE stl.pk_limit_record = limit_record.pk_limit_record "
                        + "AND sth.pk_host = pnd.pk_host "
                        + "AND stl.str_host_name = SPLIT_PART(LOWER(sth.str_name), '.', 1))"
                + ") "
            + "ELSE "
                + "COALESCE(limit_usage.int_settled_usage, 0) + ("
                    + "SELECT COUNT(*) FROM proc pnd2 "
                    + "JOIN layer_limit pnd2_ll ON pnd2_ll.pk_layer = pnd2.pk_layer "
                    + "WHERE pnd2_ll.pk_limit_record = limit_record.pk_limit_record "
                    + "AND pnd2.ts_dispatched > " + PENDING_BOUND + ") "
            + "END)";
    // spotless:on

    /**
     * Placeholder for the CTE's MATERIALIZED keyword, resolved by DispatcherDaoJdbc against the
     * server version: "MATERIALIZED" on PostgreSQL 12+, empty on 11 where the keyword does not
     * parse and every CTE is an optimization fence anyway.
     */
    public static final String CTE_MATERIALIZED_TOKEN = "__LIMIT_CTE_MATERIALIZED__";

    /**
     * Per-limit merged usage, computed once per query. Every ENFORCED, non-stale limit gets one
     * row: id, thresholds and its {@link #USAGE_EXPR} value. Materialization is load-bearing: an
     * inlined CTE lands inside {@link #limitFilter}'s NOT EXISTS and re-runs the pending scan for
     * every candidate layer row, which benchmarked 17-45x slower on the job-finding query with
     * never-reported limits (the steady state for FRAME limits, which have no external reporter).
     * The CTE is only materialized if a bound layer actually probes it, so queries over unlimited
     * work pay nothing.
     *
     * Public because FrameDaoJdbc prefixes its UPDATE_FRAME_STARTED with it: the frame-start
     * last-chance check reuses the same counting rule rather than mirroring it.
     */
    // spotless:off
    public static final String LIMIT_USAGE_CTE =
            "WITH lim AS " + CTE_MATERIALIZED_TOKEN + " ("
                + "SELECT "
                    + "limit_record.pk_limit_record, "
                    + "limit_record.str_type, "
                    + "limit_record.int_soft_value, "
                    + "limit_record.int_max_value, "
                    + USAGE_EXPR + " AS usage_val "
                + "FROM limit_record "
                + "LEFT JOIN limit_usage "
                    + "ON limit_usage.pk_limit_record = limit_record.pk_limit_record "
                + "WHERE limit_record.str_enforcement = 'ENFORCED' "
                + "AND (limit_record.int_report_ttl = 0 "
                    + "OR limit_record.ts_reported IS NULL "
                    + "OR limit_record.ts_reported > current_timestamp "
                        + "- (limit_record.int_report_ttl * INTERVAL '1 second'))"
            + ") ";
    // spotless:on

    /**
     * The generous holding test: any external hold, or any running frame of a bound layer, counts
     * as holding. A host that might still have the license is treated as though it does, so work
     * packs onto it rather than lighting up a new machine.
     *
     * The proc probe nests its EXISTS so the planner drives from the host's procs (a handful)
     * rather than the limit's bound layers (thousands under auto-tagging); as a flat join it
     * sometimes picked the layer side, which multiplies across the filter's per-row evaluations.
     */
    private static String hostHolds(String hostAlias) {
        // spotless:off
        return "(EXISTS ("
                    + "SELECT 1 FROM limit_host hld "
                    + "WHERE hld.pk_limit_record = lim.pk_limit_record "
                    + "AND hld.str_host_name = SPLIT_PART(LOWER("
                        + hostAlias + ".str_name), '.', 1)) "
                + "OR EXISTS ("
                    + "SELECT 1 FROM proc hp "
                    + "WHERE hp.pk_host = " + hostAlias + ".pk_host "
                    + "AND EXISTS ("
                        + "SELECT 1 FROM layer_limit hp_ll "
                        + "WHERE hp_ll.pk_layer = hp.pk_layer "
                        + "AND hp_ll.pk_limit_record = lim.pk_limit_record)))";
        // spotless:on
    }

    /**
     * Excludes layers bound to a limit with no headroom for this host. Joins the per-limit usage
     * rows of {@link #LIMIT_USAGE_CTE} -- every query embedding this filter must be prefixed with
     * that CTE -- and correlates only to the layer alias (and host alias, when the query has one),
     * so no call site's argument array changes shape.
     *
     * A limit blocks only when ENFORCED and not stale (both enforced by the CTE's WHERE). Below
     * soft_value (max_value when no soft threshold is set) any host may book. Above it, a host
     * already holding one of the limit's tokens may still book -- all frames on a holding machine
     * share the token, so the booking consumes nothing new -- while a host that would light up a
     * new machine may not. Stated as NOT EXISTS(blocking limit) so a layer with no limits passes
     * naturally.
     *
     * The local dispatch queries pass a null host alias and gate on max_value alone, so a
     * workstation already holding a token is refused work the farm dispatcher would give it. That
     * is a deliberate simplification, not a structural limit: those queries have no host table in
     * scope, but their call sites do have the host name, and the holder test can be written against
     * a bound name the way AFFINITY_ORDER_SQL does. Local bookings are a small share of the farm,
     * so the extra binds were judged not worth it -- revisit if artists hit it on saturated HOST
     * limits.
     *
     * Public because FrameDaoJdbc embeds it in the frame-start last-chance check; callers outside
     * this class must resolve {@link #SETTLE_WINDOW_TOKEN} and {@link #CTE_MATERIALIZED_TOKEN}
     * themselves.
     */
    public static String limitFilter(String layerAlias, String hostAlias) {
        // spotless:off
        String threshold = hostAlias == null
                ? "AND lim.usage_val >= lim.int_max_value "
                : "AND lim.usage_val >= "
                    + "CASE WHEN lim.str_type = 'HOST' "
                            + "AND lim.int_soft_value >= 0 "
                        + "THEN lim.int_soft_value "
                        + "ELSE lim.int_max_value END "
                + "AND NOT ("
                    + "lim.str_type = 'HOST' "
                    + "AND " + hostHolds(hostAlias)
                + ") ";
        return "NOT EXISTS ("
                + "SELECT 1 FROM layer_limit "
                + "JOIN lim ON lim.pk_limit_record = layer_limit.pk_limit_record "
                + "WHERE layer_limit.pk_layer = " + layerAlias + ".pk_layer "
                + threshold
            + ")";
        // spotless:on
    }

    // spotless:off
    public static final String FIND_JOBS_BY_SHOW =
            "/* FIND_JOBS_BY_SHOW */ "
            + LIMIT_USAGE_CTE
            + "SELECT pk_job, int_priority, rank FROM ( "
                + "SELECT "
                    + "ROW_NUMBER() OVER (ORDER BY int_priority DESC) AS rank, "
                    + "pk_job, "
                    + "int_priority "
                + "FROM ( "
                    + "SELECT DISTINCT "
                        + "job.pk_job as pk_job, "
                        + "/* sort = priority + (100 * (1 - (job.cores/job.int_min_cores))) + (age in days) */ "
                        + "CAST( "
                            + "job_resource.int_priority + ( "
                                + "100 * (CASE WHEN job_resource.int_min_cores <= 0 THEN 0 "
                                + "ELSE "
                                    + "CASE WHEN job_resource.int_cores > job_resource.int_min_cores THEN 0 "
                                    + "ELSE 1 - job_resource.int_cores/job_resource.int_min_cores "
                                    + "END "
                                + "END) "
                            + ") + ( "
                                + "(DATE_PART('days', NOW()) - DATE_PART('days', job.ts_updated)) "
                            + ") as INT) as int_priority "
                    + "FROM "
                        + "job            , "
                        + "job_resource   , "
                        + "folder         , "
                        + "folder_resource, "
                        + "point          , "
                        + "layer          , "
                        + "layer_stat     , "
                        + "host             "
                    + "WHERE "
                        + "job.pk_job                 = job_resource.pk_job "
                        + "AND job.pk_folder          = folder.pk_folder "
                        + "AND folder.pk_folder       = folder_resource.pk_folder "
                        + "AND folder.pk_dept         = point.pk_dept "
                        + "AND folder.pk_show         = point.pk_show "
                        + "AND job.pk_job             = layer.pk_job "
                        + "AND job_resource.pk_job    = job.pk_job "
                        + "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN layer_stat.pk_layer ELSE NULL END) = layer.pk_layer "
                        + "AND "
                            + "("
                                + "folder_resource.int_max_cores = -1 "
                            + "OR "
                                + "folder_resource.int_cores + layer.int_cores_min < folder_resource.int_max_cores "
                            + ") "
                        + "AND job.str_state                  = 'PENDING' "
                        + "AND job.b_paused                   = false "
                        + "AND job.pk_show                    = ? "
                        + "AND job.pk_facility                = ? "
                        + "AND "
                            + "("
                                + "job.str_os IS NULL OR job.str_os = '' "
                            + "OR "
                                + "job.str_os IN ? "
                            + ") "
                        + "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 "
                        + "AND (layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                        + "AND layer.int_cores_min            <= ? "
                        + "AND layer.int_mem_min              <= ? "
                        + "AND (CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= ? "
                        + "AND layer.int_gpus_min              BETWEEN 1 AND ? "
                        + "AND layer.int_gpu_mem_min          BETWEEN ? AND ? "
                        + "AND job_resource.int_cores + layer.int_cores_min <= job_resource.int_max_cores "
                        + "AND host.str_tags ~* ('(?x)' || layer.str_tags) "
                        + "AND host.str_name = ? "
                        + "AND " + limitFilter("layer", "host") + " "
            + ") AS t1 ) AS t2 WHERE rank < ?";
    // spotless:on

    public static final String FIND_JOBS_BY_SHOW_NO_GPU =
            FIND_JOBS_BY_SHOW.replace("AND layer.int_gpus_min              BETWEEN 1 AND ? ", "")
                    .replace("AND layer.int_gpu_mem_min          BETWEEN ? AND ? ", "");

    // spotless:off
    public static final String FIND_JOBS_BY_SHOW_PRIORITY_MODE =
            "/* FIND_JOBS_BY_SHOW_PRIORITY_MODE */ "
            + LIMIT_USAGE_CTE
            + "SELECT pk_job, int_priority, rank FROM ( "
                + "SELECT "
                    + "ROW_NUMBER() OVER (ORDER BY job_resource.int_priority DESC) AS rank, "
                    + "job.pk_job, "
                    + "job_resource.int_priority "
                + "FROM "
                    + "job            , "
                    + "job_resource   , "
                    + "folder         , "
                    + "folder_resource, "
                    + "point          , "
                    + "layer          , "
                    + "layer_stat     , "
                    + "host             "
                + "WHERE "
                    + "job.pk_job                 = job_resource.pk_job "
                    + "AND job.pk_folder          = folder.pk_folder "
                    + "AND folder.pk_folder       = folder_resource.pk_folder "
                    + "AND folder.pk_dept         = point.pk_dept "
                    + "AND folder.pk_show         = point.pk_show "
                    + "AND job.pk_job             = layer.pk_job "
                    + "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN layer_stat.pk_layer ELSE NULL END) = layer.pk_layer "
                    + "AND "
                        + "("
                            + "folder_resource.int_max_cores = -1 "
                        + "OR "
                            + "folder_resource.int_cores < folder_resource.int_max_cores "
                        + ") "
                    + "AND "
                        + "("
                            + "folder_resource.int_max_gpus = -1 "
                            + "OR "
                            + "folder_resource.int_gpus < folder_resource.int_max_gpus "
                        + ") "
                    + "AND job.str_state                  = 'PENDING' "
                    + "AND job.b_paused                   = false "
                    + "AND job.pk_show                    = ? "
                    + "AND job.pk_facility                = ? "
                    + "AND "
                        + "("
                            + "job.str_os IS NULL OR job.str_os = '' "
                        + "OR "
                            + "job.str_os IN ? "
                        + ") "
                    + "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 "
                    + "AND (layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                    + "AND layer.int_cores_min            <= ? "
                    + "AND layer.int_mem_min              <= ? "
                    + "AND (CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= ? "
                    + "AND layer.int_gpus_min             <= ? "
                    + "AND layer.int_gpu_mem_min          BETWEEN ? AND ? "
                    + "AND job_resource.int_cores + layer.int_cores_min < job_resource.int_max_cores "
                    + "AND job_resource.int_gpus + layer.int_gpus_min < job_resource.int_max_gpus "
                    + "AND host.str_tags ~* ('(?x)' || layer.str_tags || '\\y') "
                    + "AND host.str_name = ? "
                    + "AND " + limitFilter("layer", "host") + " "
            + ") AS t1 WHERE rank < ?";
    // spotless:on


    public static final String FIND_JOBS_BY_GROUP_PRIORITY_MODE =
            FIND_JOBS_BY_SHOW_PRIORITY_MODE.replace("FIND_JOBS_BY_SHOW", "FIND_JOBS_BY_GROUP")
                    .replace("AND job.pk_show                    = ? ",
                            "AND job.pk_folder                  = ? ");

    public static final String FIND_JOBS_BY_GROUP_BALANCED_MODE =
            FIND_JOBS_BY_SHOW.replace("FIND_JOBS_BY_SHOW", "FIND_JOBS_BY_GROUP").replace(
                    "AND job.pk_show                    = ? ",
                    "AND job.pk_folder                  = ? ");

    public static final String FIND_JOBS_BY_GROUP =
            FIND_JOBS_BY_SHOW.replace("FIND_JOBS_BY_SHOW", "FIND_JOBS_BY_GROUP").replace(
                    "AND job.pk_show                    = ? ",
                    "AND job.pk_folder                  = ? ");

    public static final String FIND_JOBS_BY_GROUP_NO_GPU =
            FIND_JOBS_BY_SHOW_NO_GPU.replace("FIND_JOBS_BY_SHOW", "FIND_JOBS_BY_GROUP").replace(
                    "AND job.pk_show                    = ? ",
                    "AND job.pk_folder                  = ? ");

    private static final String replaceQueryForFifo(String query) {
        return query.replace("JOBS_BY", "JOBS_FIFO_BY")
                .replace("ORDER BY job_resource.int_priority DESC",
                        "ORDER BY job_resource.int_priority DESC, job.ts_started ASC")
                .replace("WHERE rank < ?", "WHERE rank < ? ORDER BY rank");
    }

    public static final String FIND_JOBS_BY_SHOW_FIFO_MODE =
            replaceQueryForFifo(FIND_JOBS_BY_SHOW_PRIORITY_MODE);
    public static final String FIND_JOBS_BY_GROUP_FIFO_MODE =
            replaceQueryForFifo(FIND_JOBS_BY_GROUP_PRIORITY_MODE);

    /**
     * Dispatch a host in local booking mode.
     */
    // spotless:off
    public static final String FIND_JOBS_BY_LOCAL =
            "/* FIND_JOBS_BY_LOCAL */ "
            + LIMIT_USAGE_CTE
            + "SELECT pk_job, float_tier, rank "
            + "FROM ( "
                + "SELECT "
                    + "ROW_NUMBER() OVER (ORDER BY "
                        + "host_local.float_tier ASC "
                    + ") AS rank, "
                    + "job.pk_job, "
                    + "host_local.float_tier "
                + "FROM "
                    + "job, "
                    + "host_local "
                + "WHERE "
                    + "job.pk_job = host_local.pk_job "
                + "AND "
                    + "host_local.pk_host = ? "
                + "AND "
                    + "job.str_state = 'PENDING' "
                + "AND "
                    + "job.b_paused = false "
                + "AND "
                    + "job.pk_facility =  ? "
                + "AND "
                    + "(job.str_os IN ? OR job.str_os IS NULL) "
                + "AND "
                    + "job.pk_job IN ( "
                        + "SELECT "
                            + "l.pk_job "
                        + "FROM "
                            + "job j, "
                            + "layer l, "
                            + "layer_stat lst, "
                            + "host h, "
                            + "host_local "
                        + "WHERE "
                            + "j.pk_job = l.pk_job "
                        + "AND "
                            + "j.pk_job = host_local.pk_job "
                        + "AND "
                            + "h.pk_host = host_local.pk_host "
                        + "AND "
                            + "h.pk_host = ? "
                        + "AND "
                            + "j.str_state = 'PENDING' "
                        + "AND "
                            + "j.b_paused = false "
                        + "AND "
                            + "j.pk_facility = ? "
                        + "AND "
                            + "(j.str_os IN ? OR j.str_os IS NULL) "
                        + "AND "
                            + "(CASE WHEN lst.int_waiting_count > 0 THEN lst.pk_layer ELSE NULL END) = l.pk_layer "
                        + "AND "
                            + "(CASE WHEN lst.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 "
                        + "AND "
                            + "(l.ts_start_after IS NULL OR l.ts_start_after <= current_timestamp) "
                        + "AND "
                            + "l.int_mem_min <= host_local.int_mem_idle "
                        + "AND "
                            + "l.int_gpu_mem_min <= host_local.int_gpu_mem_idle "
                        + "AND "
                            + limitFilter("l", "h") + " "
                    + ") "
            + ") AS t1 "
            + "WHERE rank < 5";
    // spotless:on

    /**
     * This query is run before a proc is dispatched to the next frame. It checks to see if there is
     * another job someplace that is under its minimum and can take the proc.
     *
     * The current job the proc is on is excluded. This should only be run if the excluded job is
     * actually over its min proc.
     *
     * Does not unbook for Utility frames
     *
     */
    // spotless:off
    public static final String FIND_UNDER_PROCED_JOB_BY_FACILITY =
            LIMIT_USAGE_CTE
            + "SELECT "
                + "1 "
            + "FROM "
                + "job, "
                + "job_resource, "
                + "folder, "
                + "folder_resource "
            + "WHERE "
                + "job.pk_job = job_resource.pk_job "
            + "AND "
                + "job.pk_folder = folder.pk_folder "
            + "AND "
                + "folder.pk_folder = folder_resource.pk_folder "
            + "AND "
                + "(folder_resource.int_max_cores = -1 OR folder_resource.int_cores < folder_resource.int_max_cores) "
            + "AND "
                + "(folder_resource.int_max_gpus = -1 OR folder_resource.int_gpus < folder_resource.int_max_gpus) "
            + "AND "
                + "job_resource.float_tier < 1.00 "
            + "AND "
                + "job_resource.int_cores < job_resource.int_min_cores "
            + "AND "
                + "job.str_state = 'PENDING' "
            + "AND "
                + "job.b_paused = false "
            + "AND "
                + "job.pk_show = ? "
            + "AND "
                + "job.pk_facility = ? "
            + "AND "
                + "(job.str_os = ? OR job.str_os IS NULL) "
            + "AND "
                + "job.pk_job IN ( "
                    + "SELECT /* index (h i_str_host_tag) */ "
                        + "l.pk_job "
                    + "FROM "
                        + "job j, "
                        + "layer l, "
                        + "layer_stat lst, "
                        + "host h "
                    + "WHERE "
                        + "j.pk_job = l.pk_job "
                    + "AND "
                        + "j.str_state = 'PENDING' "
                    + "AND "
                        + "j.b_paused = false "
                    + "AND "
                        + "j.pk_show = ? "
                    + "AND "
                        + "j.pk_facility = ? "
                    + "AND "
                        + "(j.str_os = ? OR j.str_os IS NULL) "
                    + "AND "
                        + "(CASE WHEN lst.int_waiting_count > 0 THEN lst.pk_layer ELSE NULL END) = l.pk_layer "
                    + "AND "
                        + "(CASE WHEN lst.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 "
                    + "AND "
                        + "(l.ts_start_after IS NULL OR l.ts_start_after <= current_timestamp) "
                    + "AND "
                        + "l.int_cores_min <= ? "
                    + "AND "
                        + "l.int_mem_min <= ? "
                    + "AND "
                        + "l.int_gpus_min <= ? "
                    + "AND "
                        + "l.int_gpu_mem_min = ? "
                    + "AND "
                        + "h.str_tags ~* ('(?x)' || l.str_tags || '\\y') "
                    + "AND "
                        + "h.str_name = ? "
                    + "AND "
                        + limitFilter("l", "h") + " "
                + ") "
            + "LIMIT 1";
    // spotless:on

    /**
     * This query is run before a proc is dispatched to the next frame. It checks to see if there is
     * another job someplace that is at a higher priority and can take the proc.
     *
     * The current job the proc is on is excluded. This should only be run if the excluded job is
     * actually over its min proc.
     *
     * Does not unbook for Utility frames
     *
     */
    // spotless:off
    public static final String HIGHER_PRIORITY_JOB_BY_FACILITY_EXISTS =
            LIMIT_USAGE_CTE
            + "SELECT "
                + "1 "
            + "FROM "
                + "job, "
                + "job_resource, "
                + "folder, "
                + "folder_resource "
            + "WHERE "
                + "job.pk_job = job_resource.pk_job "
            + "AND "
                + "job.pk_folder = folder.pk_folder "
            + "AND "
                + "folder.pk_folder = folder_resource.pk_folder "
            + "AND "
                + "(folder_resource.int_max_cores = -1 OR folder_resource.int_cores < folder_resource.int_max_cores) "
            + "AND "
                + "(folder_resource.int_max_gpus = -1 OR folder_resource.int_gpus < folder_resource.int_max_gpus) "
            + "AND "
                + "job_resource.int_priority > ? "
            + "AND "
                + "job_resource.int_cores < job_resource.int_max_cores "
            + "AND "
                + "job_resource.int_gpus < job_resource.int_max_gpus "
            + "AND "
                + "job.str_state = 'PENDING' "
            + "AND "
                + "job.b_paused = false "
            + "AND "
                + "job.pk_facility = ? "
            + "AND "
                + "(job.str_os = ? OR job.str_os IS NULL) "
            + "AND "
                + "job.pk_job IN ( "
                    + "SELECT /* index (h i_str_host_tag) */ "
                        + "l.pk_job "
                    + "FROM "
                        + "job j, "
                        + "layer l, "
                        + "layer_stat lst, "
                        + "host h "
                    + "WHERE "
                        + "j.pk_job = l.pk_job "
                    + "AND "
                        + "j.str_state = 'PENDING' "
                    + "AND "
                        + "j.b_paused = false "
                    + "AND "
                        + "j.pk_facility = ? "
                    + "AND "
                        + "(j.str_os = ? OR j.str_os IS NULL) "
                    + "AND "
                        + "(CASE WHEN lst.int_waiting_count > 0 THEN lst.pk_layer ELSE NULL END) = l.pk_layer "
                    + "AND "
                        + "(CASE WHEN lst.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 "
                    + "AND "
                        + "(l.ts_start_after IS NULL OR l.ts_start_after <= current_timestamp) "
                    + "AND "
                        + "l.int_cores_min <= ? "
                    + "AND "
                        + "l.int_mem_min <= ? "
                    + "AND "
                        + "l.int_gpus_min <= ? "
                    + "AND "
                        + "l.int_gpu_mem_min = ? "
                    + "AND "
                        + "h.str_tags ~* ('(?x)' || l.str_tags || '\\y') "
                    + "AND "
                        + "h.str_name = ? "
                    + "AND "
                        + limitFilter("l", "h") + " "
                + ") "
            + "LIMIT 1";
    // spotless:on

    // spotless:off
    private static final String FIND_DISPATCH_FRAME_COLUMNS =
            "show_name, "
            + "job_name, "
            + "pk_job, "
            + "pk_show, "
            + "pk_facility, "
            + "str_name, "
            + "str_shot, "
            + "str_user, "
            + "int_uid, "
            + "str_log_dir, "
            + "COALESCE(str_os, '') AS str_os, "
            + "COALESCE(str_loki_url, '') AS str_loki_url, "
            + "frame_name, "
            + "frame_state, "
            + "pk_frame, "
            + "pk_layer, "
            + "int_retries, "
            + "int_version, "
            + "layer_name, "
            + "layer_type, "
            + "b_threadable, "
            + "int_cores_min, "
            + "int_cores_max, "
            + "int_mem_min, "
            + "int_gpus_min, "
            + "int_gpus_max, "
            + "int_gpu_mem_min, "
            + "str_cmd, "
            + "str_range, "
            + "int_chunk_size, "
            + "str_services ";
    // spotless:on

    /**
     * Finds the next frame in a job for a proc.
     */
    // spotless:off
    public static final String FIND_DISPATCH_FRAME_BY_JOB_AND_PROC =
            LIMIT_USAGE_CTE + "SELECT " + FIND_DISPATCH_FRAME_COLUMNS
            + "FROM ( "
                + "SELECT "
                    + "ROW_NUMBER() OVER ( ORDER BY "
                        + AFFINITY_ORDER_TOKEN
                        + "frame.int_dispatch_order ASC, "
                        + "frame.int_layer_order ASC "
                    + ") AS LINENUM, "
                    + "job.str_show AS show_name, "
                    + "job.str_name AS job_name, "
                    + "job.pk_job, "
                    + "job.pk_show, "
                    + "job.pk_facility, "
                    + "job.str_name, "
                    + "job.str_shot, "
                    + "job.str_user, "
                    + "job.int_uid, "
                    + "job.str_log_dir, "
                    + "job.str_os, "
                    + "job.str_loki_url, "
                    + "frame.str_name AS frame_name, "
                    + "frame.str_state AS frame_state, "
                    + "frame.pk_frame, "
                    + "frame.pk_layer, "
                    + "frame.int_retries, "
                    + "frame.int_version, "
                    + "layer.str_name AS layer_name, "
                    + "layer.str_type AS layer_type, "
                    + "layer.b_threadable, "
                    + "layer.int_cores_min, "
                    + "layer.int_cores_max, "
                    + "layer.int_mem_min, "
                    + "layer.int_gpus_min, "
                    + "layer.int_gpus_max, "
                    + "layer.int_gpu_mem_min, "
                    + "layer.str_cmd, "
                    + "layer.str_range, "
                    + "layer.int_chunk_size, "
                    + "layer.str_services "
                + "FROM "
                    + "job, "
                    + "frame, "
                    + "layer "
                + "WHERE "
                    + "frame.pk_layer = layer.pk_layer "
                + "AND "
                    + "layer.pk_job = job.pk_job "
                + "AND "
                    + "layer.int_cores_min <= :coresAvailable "
                + "AND "
                    + "layer.int_mem_min <= :memoryAvailable "
                + "AND "
                    + "layer.int_gpus_min <= :gpusAvailable "
                + "AND "
                    + "layer.int_gpu_mem_min BETWEEN :gpuMemoryMin AND :gpuMemoryAvailable "
                + "AND "
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "(layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                + "AND "
                    + "job.pk_job=:jobId "
                + "AND layer.pk_layer IN ( "
                    + "SELECT /*+ index (h i_str_host_tag) */ "
                        + "l.pk_layer "
                    + "FROM "
                        + "layer l "
                    + "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags || '\\y') AND h.str_name = :hostName) "
                    + "WHERE "
                        + "l.pk_job= :jobId "
                    + "AND "
                        + limitFilter("l", "h") + " "
                + ") "
            + ") AS t1 WHERE LINENUM <= :frameLimit";
    // spotless:on

    /**
     * Find the next frame in a job for a host.
     */
    // spotless:off
    public static final String FIND_DISPATCH_FRAME_BY_JOB_AND_HOST =
            LIMIT_USAGE_CTE + "SELECT " + FIND_DISPATCH_FRAME_COLUMNS
            + "FROM ( "
                + "SELECT "
                    + "ROW_NUMBER() OVER ( ORDER BY "
                        + AFFINITY_ORDER_TOKEN
                        + "frame.int_dispatch_order ASC, "
                        + "frame.int_layer_order ASC "
                    + ") AS LINENUM, "
                    + "job.str_show AS show_name, "
                    + "job.str_name AS job_name, "
                    + "job.pk_job, "
                    + "job.pk_show, "
                    + "job.pk_facility, "
                    + "job.str_name, "
                    + "job.str_shot, "
                    + "job.str_user, "
                    + "job.int_uid, "
                    + "job.str_log_dir, "
                    + "job.str_os, "
                    + "job.str_loki_url, "
                    + "frame.str_name AS frame_name, "
                    + "frame.str_state AS frame_state, "
                    + "frame.pk_frame, "
                    + "frame.pk_layer, "
                    + "frame.int_retries, "
                    + "frame.int_version, "
                    + "layer.str_name AS layer_name, "
                    + "layer.str_type AS layer_type, "
                    + "layer.int_cores_min, "
                    + "layer.int_cores_max, "
                    + "layer.int_gpus_min, "
                    + "layer.int_gpus_max, "
                    + "layer.b_threadable, "
                    + "layer.int_mem_min, "
                    + "layer.int_gpu_mem_min, "
                    + "layer.str_cmd, "
                    + "layer.str_range, "
                    + "layer.int_chunk_size, "
                    + "layer.str_services "
                + "FROM "
                    + "job, "
                    + "frame, "
                    + "layer "
                + "WHERE "
                    + "frame.pk_layer = layer.pk_layer "
                + "AND "
                    + "layer.pk_job = job.pk_job "
                + "AND "
                    + "layer.int_cores_min <= :coresAvailable "
                + "AND "
                    + "layer.int_mem_min <= :memoryAvailable "
                + "AND "
                    + "(CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= :threadMode "
                + "AND "
                    + "layer.int_gpus_min <= :gpusAvailable "
                + "AND "
                    + "layer.int_gpu_mem_min BETWEEN :gpuMemoryMin AND :gpuMemoryAvailable "
                + "AND "
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "(layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                + "AND "
                    + "job.pk_job=:jobId "
                + "AND "
                    + "layer.pk_layer IN ( "
                        + "SELECT /*+ index (h i_str_host_tag) */ "
                            + "l.pk_layer "
                        + "FROM "
                            + "layer l "
                        + "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags || '\\y') AND h.str_name = :hostName) "
                        + "WHERE "
                            + "l.pk_job = :jobId "
                        + "AND "
                            + limitFilter("l", "h") + " "
                    + ") "
            + ") AS t1 WHERE LINENUM <= :frameLimit";
    // spotless:on


    // spotless:off
    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC =
            LIMIT_USAGE_CTE + "SELECT " + FIND_DISPATCH_FRAME_COLUMNS
            + "FROM ( "
                + "SELECT "
                    + "ROW_NUMBER() OVER ( ORDER BY "
                        + "frame.int_dispatch_order ASC, "
                        + "frame.int_layer_order ASC "
                    + ") AS LINENUM, "
                    + "job.str_show AS show_name, "
                    + "job.str_name AS job_name, "
                    + "job.pk_job, "
                    + "job.pk_show, "
                    + "job.pk_facility, "
                    + "job.str_name, "
                    + "job.str_shot, "
                    + "job.str_user, "
                    + "job.int_uid, "
                    + "job.str_log_dir, "
                    + "job.str_os, "
                    + "job.str_loki_url, "
                    + "frame.str_name AS frame_name, "
                    + "frame.str_state AS frame_state, "
                    + "frame.pk_frame, "
                    + "frame.pk_layer, "
                    + "frame.int_retries, "
                    + "frame.int_version, "
                    + "layer.str_name AS layer_name, "
                    + "layer.str_type AS layer_type, "
                    + "layer.b_threadable, "
                    + "layer.int_cores_min, "
                    + "layer.int_cores_max, "
                    + "layer.int_mem_min, "
                    + "layer.int_gpus_min, "
                    + "layer.int_gpus_max, "
                    + "layer.int_gpu_mem_min, "
                    + "layer.str_cmd, "
                    + "layer.str_range, "
                    + "layer.int_chunk_size, "
                    + "layer.str_services "
                + "FROM "
                    + "job, "
                    + "frame, "
                    + "layer "
                + "WHERE "
                    + "frame.pk_layer = layer.pk_layer "
                + "AND "
                    + "layer.pk_job = job.pk_job "
                + "AND "
                    + "layer.int_mem_min <= ? "
                + "AND "
                    + "layer.int_gpu_mem_min <= ? "
                + "AND "
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "(layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                + "AND "
                    + "job.pk_job=? "
                + "AND "
                    + limitFilter("layer", null) + " "
            + ") AS t1 WHERE LINENUM <= ?";
    // spotless:on

    /**
     * Find the next frame in a job for a host.
     */
    // spotless:off
    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST =
            LIMIT_USAGE_CTE + "SELECT " + FIND_DISPATCH_FRAME_COLUMNS
            + "FROM ("
                + "SELECT "
                    + "ROW_NUMBER() OVER ( ORDER BY "
                        + "frame.int_dispatch_order ASC, "
                        + "frame.int_layer_order ASC "
                    + ") LINENUM, "
                    + "job.str_show AS show_name, "
                    + "job.str_name AS job_name, "
                    + "job.pk_job, "
                    + "job.pk_show, "
                    + "job.pk_facility, "
                    + "job.str_name, "
                    + "job.str_shot, "
                    + "job.str_user, "
                    + "job.int_uid, "
                    + "job.str_log_dir, "
                    + "job.str_os, "
                    + "job.str_loki_url, "
                    + "frame.str_name AS frame_name, "
                    + "frame.str_state AS frame_state, "
                    + "frame.pk_frame, "
                    + "frame.pk_layer, "
                    + "frame.int_retries, "
                    + "frame.int_version, "
                    + "layer.str_name AS layer_name, "
                    + "layer.str_type AS layer_type, "
                    + "layer.int_cores_min, "
                    + "layer.int_cores_max, "
                    + "layer.b_threadable, "
                    + "layer.int_mem_min, "
                    + "layer.int_gpus_min, "
                    + "layer.int_gpus_max, "
                    + "layer.int_gpu_mem_min, "
                    + "layer.str_cmd, "
                    + "layer.str_range, "
                    + "layer.int_chunk_size, "
                    + "layer.str_services "
                + "FROM "
                    + "job, "
                    + "frame, "
                    + "layer "
                + "WHERE "
                    + "frame.pk_layer = layer.pk_layer "
                + "AND "
                    + "layer.pk_job = job.pk_job "
                + "AND "
                    + "layer.int_mem_min <= ? "
                + "AND "
                    + "layer.int_gpu_mem_min <= ? "
                + "AND "
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "(layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                + "AND "
                    + "job.pk_job=? "
                + "AND "
                    + limitFilter("layer", null) + " "
            + ") AS t1 WHERE LINENUM <= ?";
    // spotless:on


    /**** LAYER DISPATCHING **/

    /**
     * Finds the next frame in a job for a proc.
     */
    // spotless:off
    public static final String FIND_DISPATCH_FRAME_BY_LAYER_AND_PROC =
            LIMIT_USAGE_CTE + "SELECT " + FIND_DISPATCH_FRAME_COLUMNS
            + "FROM ("
                + "SELECT "
                    + "ROW_NUMBER() OVER ( ORDER BY "
                        + AFFINITY_ORDER_TOKEN
                        + "frame.int_dispatch_order ASC, "
                        + "frame.int_layer_order ASC "
                    + ") LINENUM, "
                    + "job.str_show AS show_name, "
                    + "job.str_name AS job_name, "
                    + "job.pk_job, "
                    + "job.pk_show, "
                    + "job.pk_facility, "
                    + "job.str_name, "
                    + "job.str_shot, "
                    + "job.str_user, "
                    + "job.int_uid, "
                    + "job.str_log_dir, "
                    + "job.str_os, "
                    + "job.str_loki_url, "
                    + "frame.str_name AS frame_name, "
                    + "frame.str_state AS frame_state, "
                    + "frame.pk_frame, "
                    + "frame.pk_layer, "
                    + "frame.int_retries, "
                    + "frame.int_version, "
                    + "layer.str_name AS layer_name, "
                    + "layer.str_type AS layer_type, "
                    + "layer.b_threadable, "
                    + "layer.int_cores_min, "
                    + "layer.int_cores_max, "
                    + "layer.int_mem_min, "
                    + "layer.int_gpus_min, "
                    + "layer.int_gpus_max, "
                    + "layer.int_gpu_mem_min, "
                    + "layer.str_cmd, "
                    + "layer.str_range, "
                    + "layer.int_chunk_size, "
                    + "layer.str_services "
                + "FROM "
                    + "job, "
                    + "frame, "
                    + "layer "
                + "WHERE "
                    + "frame.pk_layer = layer.pk_layer "
                + "AND "
                    + "layer.pk_job = job.pk_job "
                + "AND "
                    + "layer.int_cores_min <= :coresAvailable "
                + "AND "
                    + "layer.int_mem_min <= :memoryAvailable "
                + "AND "
                    + "layer.int_gpus_min <= :gpusAvailable "
                + "AND "
                    + "layer.int_gpu_mem_min <= :gpuMemoryAvailable "
                + "AND "
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "(layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                + "AND "
                    + "layer.pk_layer=:layerId "
                + "AND layer.pk_layer IN ( "
                    + "SELECT /*+ index (h i_str_host_tag) */ "
                        + "l.pk_layer "
                    + "FROM "
                        + "layer l "
                    + "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags || '\\y') AND h.str_name = :hostName) "
                    + "WHERE "
                        + "l.pk_layer= :layerId "
                    + "AND "
                        + limitFilter("l", "h") + " "
                + ")"
            + ") AS t1 WHERE LINENUM <= :frameLimit";
    // spotless:on

    /**
     * Find the next frame in a job for a host.
     */
    // spotless:off
    public static final String FIND_DISPATCH_FRAME_BY_LAYER_AND_HOST =
            LIMIT_USAGE_CTE + "SELECT " + FIND_DISPATCH_FRAME_COLUMNS
            + "FROM ("
                + "SELECT "
                    + "ROW_NUMBER() OVER ( ORDER BY "
                        + AFFINITY_ORDER_TOKEN
                        + "frame.int_dispatch_order ASC, "
                        + "frame.int_layer_order ASC "
                    + ") AS LINENUM, "
                    + "job.str_show AS show_name, "
                    + "job.str_name AS job_name, "
                    + "job.pk_job, "
                    + "job.pk_show, "
                    + "job.pk_facility, "
                    + "job.str_name, "
                    + "job.str_shot, "
                    + "job.str_user, "
                    + "job.int_uid, "
                    + "job.str_log_dir, "
                    + "job.str_os, "
                    + "job.str_loki_url, "
                    + "frame.str_name AS frame_name, "
                    + "frame.str_state AS frame_state, "
                    + "frame.pk_frame, "
                    + "frame.pk_layer, "
                    + "frame.int_retries, "
                    + "frame.int_version, "
                    + "layer.str_name AS layer_name, "
                    + "layer.str_type AS layer_type, "
                    + "layer.int_cores_min, "
                    + "layer.int_cores_max, "
                    + "layer.b_threadable, "
                    + "layer.int_mem_min, "
                    + "layer.int_gpus_min, "
                    + "layer.int_gpus_max, "
                    + "layer.int_gpu_mem_min, "
                    + "layer.str_cmd, "
                    + "layer.str_range, "
                    + "layer.int_chunk_size, "
                    + "layer.str_services "
                + "FROM "
                    + "job, "
                    + "frame, "
                    + "layer "
                + "WHERE "
                    + "frame.pk_layer = layer.pk_layer "
                + "AND "
                    + "layer.pk_job = job.pk_job "
                + "AND "
                    + "layer.int_cores_min <= :coresAvailable "
                + "AND "
                    + "layer.int_mem_min <= :memoryAvailable "
                + "AND "
                    + "(CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= :threadMode "
                + "AND "
                    + "layer.int_gpus_min <= :gpusAvailable "
                + "AND "
                    + "layer.int_gpu_mem_min <= :gpuMemoryAvailable "
                + "AND "
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "(layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                + "AND "
                    + "layer.pk_layer=:layerId "
                + "AND "
                    + "layer.pk_layer IN ( "
                        + "SELECT /*+ index (h i_str_host_tag) */ "
                            + "l.pk_layer "
                        + "FROM "
                            + "layer l "
                        + "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags  || '\\y') AND h.str_name = :hostName) "
                        + "WHERE "
                            + "l.pk_layer= :layerId "
                        + "AND "
                            + limitFilter("l", "h") + " "
                    + ") "
            + ") AS t1 WHERE LINENUM <= :frameLimit";
    // spotless:on


    // spotless:off
    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC =
            LIMIT_USAGE_CTE + "SELECT " + FIND_DISPATCH_FRAME_COLUMNS
            + "FROM ("
                + "SELECT "
                    + "ROW_NUMBER() OVER ( ORDER BY "
                        + "frame.int_dispatch_order ASC, "
                        + "frame.int_layer_order ASC "
                    + ") AS LINENUM, "
                    + "job.str_show AS show_name, "
                    + "job.str_name AS job_name, "
                    + "job.pk_job, "
                    + "job.pk_show, "
                    + "job.pk_facility, "
                    + "job.str_name, "
                    + "job.str_shot, "
                    + "job.str_user, "
                    + "job.int_uid, "
                    + "job.str_log_dir, "
                    + "job.str_os, "
                    + "job.str_loki_url, "
                    + "frame.str_name AS frame_name, "
                    + "frame.str_state AS frame_state, "
                    + "frame.pk_frame, "
                    + "frame.pk_layer, "
                    + "frame.int_retries, "
                    + "frame.int_version, "
                    + "layer.str_name AS layer_name, "
                    + "layer.str_type AS layer_type, "
                    + "layer.b_threadable, "
                    + "layer.int_cores_min, "
                    + "layer.int_mem_min, "
                    + "layer.int_gpus_min, "
                    + "layer.int_gpus_max, "
                    + "layer.int_gpu_mem_min, "
                    + "layer.int_cores_max, "
                    + "layer.str_cmd, "
                    + "layer.str_range, "
                    + "layer.int_chunk_size, "
                    + "layer.str_services "
                + "FROM "
                    + "job, "
                    + "frame, "
                    + "layer "
                + "WHERE "
                    + "frame.pk_layer = layer.pk_layer "
                + "AND "
                    + "layer.pk_job = job.pk_job "
                + "AND "
                    + "layer.int_mem_min <= ? "
                + "AND "
                    + "layer.int_gpu_mem_min <= ? "
                + "AND "
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "(layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                + "AND "
                    + "layer.pk_layer = ? "
                + "AND "
                    + limitFilter("layer", null) + " "
            + ") AS t1 WHERE LINENUM <= ?";
    // spotless:on

    /**
     * Find the next frame in a job for a host.
     */
    // spotless:off
    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST =
            LIMIT_USAGE_CTE + "SELECT " + FIND_DISPATCH_FRAME_COLUMNS
            + "FROM ("
                + "SELECT "
                    + "ROW_NUMBER() OVER (ORDER BY "
                        + "frame.int_dispatch_order ASC, "
                        + "frame.int_layer_order ASC "
                    + ") AS LINENUM, "
                    + "job.str_show AS show_name, "
                    + "job.str_name AS job_name, "
                    + "job.pk_job, "
                    + "job.pk_show, "
                    + "job.pk_facility, "
                    + "job.str_name, "
                    + "job.str_shot, "
                    + "job.str_user, "
                    + "job.int_uid, "
                    + "job.str_log_dir, "
                    + "job.str_os, "
                    + "job.str_loki_url, "
                    + "frame.str_name AS frame_name, "
                    + "frame.str_state AS frame_state, "
                    + "frame.pk_frame, "
                    + "frame.pk_layer, "
                    + "frame.int_retries, "
                    + "frame.int_version, "
                    + "layer.str_name AS layer_name, "
                    + "layer.str_type AS layer_type, "
                    + "layer.int_cores_min, "
                    + "layer.int_cores_max, "
                    + "layer.b_threadable, "
                    + "layer.int_mem_min, "
                    + "layer.int_gpus_min, "
                    + "layer.int_gpus_max, "
                    + "layer.int_gpu_mem_min, "
                    + "layer.str_cmd, "
                    + "layer.str_range, "
                    + "layer.int_chunk_size, "
                    + "layer.str_services "
                + "FROM "
                    + "job, "
                    + "frame, "
                    + "layer "
                + "WHERE "
                    + "frame.pk_layer = layer.pk_layer "
                + "AND "
                    + "layer.pk_job = job.pk_job "
                + "AND "
                    + "layer.int_mem_min <= ? "
                + "AND "
                    + "layer.int_gpu_mem_min <= ? "
                + "AND "
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "(layer.ts_start_after IS NULL OR layer.ts_start_after <= current_timestamp) "
                + "AND "
                    + "layer.pk_layer= ? "
                + "AND "
                    + limitFilter("layer", null) + " "
            + ") AS t1 WHERE LINENUM <= ?";
    // spotless:on

    /**
     * Looks for shows that are under their burst for a particular type of proc. The show has to be
     * at least one whole proc under their burst to be considered for booking. Scheduler-managed
     * shows are excluded; their dispatch is owned by the standalone Rust scheduler.
     */
    // spotless:off
    public static final String FIND_SHOWS =
            "SELECT "
                + "vs_waiting.pk_show, "
                + "s.float_tier, "
                + "s.int_burst, "
                + "show.str_name as str_show_name "
            + "FROM "
                + "subscription s, "
                + "vs_waiting, "
                + "show "
            + "WHERE "
                + "vs_waiting.pk_show = s.pk_show "
            + "AND "
                + "s.pk_show = show.pk_show "
            + "AND "
                + "s.pk_alloc = ? "
            + "AND "
                + "s.int_burst > 0 "
            + "AND "
                + "s.int_burst - s.int_cores >= 100 "
            + "AND "
                + "s.int_cores < s.int_burst "
            + "AND "
                + "show.b_scheduler_managed = false ";
    // spotless:on

}
