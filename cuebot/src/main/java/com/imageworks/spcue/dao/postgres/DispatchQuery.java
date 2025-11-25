
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

// spotless:off
public class DispatchQuery {
    public static final String FIND_JOBS_BY_SHOW =
        "/* FIND_JOBS_BY_SHOW */ " +
            "SELECT pk_job, int_priority, rank FROM ( " +
            "SELECT " +
                "ROW_NUMBER() OVER (ORDER BY int_priority DESC) AS rank, " +
                "pk_job, " +
                "int_priority " +
            "FROM ( " +
            "SELECT DISTINCT " +
                "job.pk_job as pk_job, " +
                "/* sort = priority + (100 * (1 - (job.cores/job.int_min_cores))) + (age in days) */ " +
                "CAST( " +
                        "job_resource.int_priority + ( " +
                            "100 * (CASE WHEN job_resource.int_min_cores <= 0 THEN 0 " +
                        "ELSE " +
                            "CASE WHEN job_resource.int_cores > job_resource.int_min_cores THEN 0 " +
                            "ELSE 1 - job_resource.int_cores/job_resource.int_min_cores " +
                            "END " +
                        "END) " +
				") + ( " +
                "(DATE_PART('days', NOW()) - DATE_PART('days', job.ts_updated)) " +
            ") as INT) as int_priority " +
            "FROM " +
                "job            , " +
                "job_resource   , " +
                "folder         , " +
                "folder_resource, " +
                "point          , " +
                "layer          , " +
                "layer_stat     , " +
                "host             " +
            "WHERE " +
                "job.pk_job                 = job_resource.pk_job " +
                "AND job.pk_folder          = folder.pk_folder " +
                "AND folder.pk_folder       = folder_resource.pk_folder " +
                "AND folder.pk_dept         = point.pk_dept " +
                "AND folder.pk_show         = point.pk_show " +
                "AND job.pk_job             = layer.pk_job " +
                "AND job_resource.pk_job    = job.pk_job " +
                "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN layer_stat.pk_layer ELSE NULL END) = layer.pk_layer " +
                "AND " +
                    "(" +
                        "folder_resource.int_max_cores = -1 " +
                    "OR " +
                        "folder_resource.int_cores + layer.int_cores_min < folder_resource.int_max_cores " +
                    ") " +
                "AND job.str_state                  = 'PENDING' " +
                "AND job.b_paused                   = false " +
                "AND job.pk_show                    = ? " +
                "AND job.pk_facility                = ? " +
                "AND " +
                    "(" +
                        "job.str_os IS NULL OR job.str_os = '' " +
                    "OR " +
                        "job.str_os IN ? " +
                    ") " +
                "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 " +
                "AND layer.int_cores_min            <= ? " +
                "AND layer.int_mem_min              <= ? " +
                "AND (CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= ? " +
                "AND layer.int_gpus_min              BETWEEN 1 AND ? " +
                "AND layer.int_gpu_mem_min          BETWEEN ? AND ? " +
                "AND job_resource.int_cores + layer.int_cores_min <= job_resource.int_max_cores " +
                "AND host.str_tags ~* ('(?x)' || layer.str_tags) " +
                "AND host.str_name = ? " +
        ") AS t1 ) AS t2 WHERE rank < ?";

    public static final String FIND_JOBS_BY_SHOW_NO_GPU =
        FIND_JOBS_BY_SHOW.replace("AND layer.int_gpus_min              BETWEEN 1 AND ? ", "")
                .replace("AND layer.int_gpu_mem_min          BETWEEN ? AND ? ", "");

    public static final String FIND_JOBS_BY_SHOW_PRIORITY_MODE =
        "/* FIND_JOBS_BY_SHOW_PRIORITY_MODE */ " +
        "SELECT pk_job, int_priority, rank FROM ( " +
            "SELECT " +
                "ROW_NUMBER() OVER (ORDER BY job_resource.int_priority DESC) AS rank, " +
                "job.pk_job, " +
                "job_resource.int_priority " +
            "FROM " +
                "job            , " +
                "job_resource   , " +
                "folder         , " +
                "folder_resource, " +
                "point          , " +
                "layer          , " +
                "layer_stat     , " +
                "host             " +
            "WHERE " +
                "job.pk_job                 = job_resource.pk_job " +
                "AND job.pk_folder          = folder.pk_folder " +
                "AND folder.pk_folder       = folder_resource.pk_folder " +
                "AND folder.pk_dept         = point.pk_dept " +
                "AND folder.pk_show         = point.pk_show " +
                "AND job.pk_job             = layer.pk_job " +
                "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN layer_stat.pk_layer ELSE NULL END) = layer.pk_layer " +
                "AND " +
                    "(" +
                        "folder_resource.int_max_cores = -1 " +
                    "OR " +
                        "folder_resource.int_cores < folder_resource.int_max_cores " +
                    ") " +
                "AND " +
                    "(" +
                        "folder_resource.int_max_gpus = -1 " +
                        "OR " +
                        "folder_resource.int_gpus < folder_resource.int_max_gpus " +
                    ") " +
                "AND job.str_state                  = 'PENDING' " +
                "AND job.b_paused                   = false " +
                "AND job.pk_show                    = ? " +
                "AND job.pk_facility                = ? " +
                "AND " +
                    "(" +
                        "job.str_os IS NULL OR job.str_os = '' " +
                    "OR " +
                        "job.str_os IN ? " +
                    ") " +
                "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 " +
                "AND layer.int_cores_min            <= ? " +
                "AND layer.int_mem_min              <= ? " +
                "AND (CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= ? " +
                "AND layer.int_gpus_min             <= ? " +
                "AND layer.int_gpu_mem_min          BETWEEN ? AND ? " +
                "AND job_resource.int_cores + layer.int_cores_min < job_resource.int_max_cores " +
                "AND job_resource.int_gpus + layer.int_gpus_min < job_resource.int_max_gpus " +
                "AND host.str_tags ~* ('(?x)' || layer.str_tags || '\\y') " +
                "AND host.str_name = ? " +
                "AND layer.pk_layer IN (" +
                    "SELECT " +
                        "l.pk_layer " +
                    "FROM " +
                        "layer l " +
                    "LEFT JOIN layer_limit ON layer_limit.pk_layer = l.pk_layer " +
                    "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                    "LEFT JOIN (" +
                        "SELECT " +
                            "limit_record.pk_limit_record, " +
                            "SUM(layer_stat.int_running_count) AS int_sum_running " +
                        "FROM " +
                            "layer_limit " +
                        "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                        "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                        "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                    "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                    "WHERE " +
                        "sum_running.int_sum_running < limit_record.int_max_value " +
                        "OR sum_running.int_sum_running IS NULL " +
                ") " +
        ") AS t1 WHERE rank < ?";


    public static final String FIND_JOBS_BY_GROUP_PRIORITY_MODE =
        FIND_JOBS_BY_SHOW_PRIORITY_MODE
            .replace(
                "FIND_JOBS_BY_SHOW",
                "FIND_JOBS_BY_GROUP")
            .replace(
                "AND job.pk_show                    = ? ",
                "AND job.pk_folder                  = ? ");

    public static final String FIND_JOBS_BY_GROUP_BALANCED_MODE =
        FIND_JOBS_BY_SHOW
            .replace(
                "FIND_JOBS_BY_SHOW",
                "FIND_JOBS_BY_GROUP")
            .replace(
                "AND job.pk_show                    = ? ",
                "AND job.pk_folder                  = ? ");

    public static final String FIND_JOBS_BY_GROUP =
            FIND_JOBS_BY_SHOW
                    .replace(
                            "FIND_JOBS_BY_SHOW",
                            "FIND_JOBS_BY_GROUP")
                    .replace(
                            "AND job.pk_show                    = ? ",
                            "AND job.pk_folder                  = ? ");

    public static final String FIND_JOBS_BY_GROUP_NO_GPU =
            FIND_JOBS_BY_SHOW_NO_GPU
                    .replace(
                            "FIND_JOBS_BY_SHOW",
                            "FIND_JOBS_BY_GROUP")
                    .replace(
                            "AND job.pk_show                    = ? ",
                            "AND job.pk_folder                  = ? ");

    private static final String replaceQueryForFifo(String query) {
        return query
            .replace(
                "JOBS_BY",
                "JOBS_FIFO_BY")
            .replace(
                "ORDER BY job_resource.int_priority DESC",
                "ORDER BY job_resource.int_priority DESC, job.ts_started ASC")
            .replace(
                "WHERE rank < ?",
                "WHERE rank < ? ORDER BY rank");
    }

    public static final String FIND_JOBS_BY_SHOW_FIFO_MODE = replaceQueryForFifo(FIND_JOBS_BY_SHOW_PRIORITY_MODE);
    public static final String FIND_JOBS_BY_GROUP_FIFO_MODE = replaceQueryForFifo(FIND_JOBS_BY_GROUP_PRIORITY_MODE);

    /**
     * Dispatch a host in local booking mode.
     */
    public static final String FIND_JOBS_BY_LOCAL =
        "/* FIND_JOBS_BY_LOCAL */ " +
        "SELECT pk_job, float_tier, rank " +
        "FROM ( " +
            "SELECT " +
                "ROW_NUMBER() OVER (ORDER BY " +
                    "host_local.float_tier ASC " +
                ") AS rank, " +
                "job.pk_job, " +
                "host_local.float_tier " +
            "FROM " +
                "job, " +
                "host_local " +
            "WHERE " +
                "job.pk_job = host_local.pk_job " +
            "AND " +
                "host_local.pk_host = ? " +
            "AND " +
                "job.str_state = 'PENDING' " +
            "AND " +
                "job.b_paused = false " +
            "AND " +
                "job.pk_facility =  ? " +
            "AND " +
                "(job.str_os IN ? OR job.str_os IS NULL) " +
            "AND " +
                "job.pk_job IN ( " +
                    "SELECT " +
                        "l.pk_job " +
                    "FROM " +
                        "job j, " +
                        "layer l, " +
                        "layer_stat lst, " +
                        "host h, " +
                        "host_local " +
                    "WHERE " +
                        "j.pk_job = l.pk_job " +
                    "AND " +
                        "j.pk_job = host_local.pk_job " +
                    "AND " +
                        "h.pk_host = host_local.pk_host " +
                    "AND " +
                        "h.pk_host = ? " +
                    "AND " +
                        "j.str_state = 'PENDING' " +
                    "AND " +
                        "j.b_paused = false " +
                    "AND " +
                        "j.pk_facility = ? " +
                    "AND " +
                        "(j.str_os IN ? OR j.str_os IS NULL) " +
                    "AND " +
                        "(CASE WHEN lst.int_waiting_count > 0 THEN lst.pk_layer ELSE NULL END) = l.pk_layer " +
                    "AND " +
                        "(CASE WHEN lst.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 " +
                    "AND " +
                        "l.int_mem_min <= host_local.int_mem_idle " +
                    "AND " +
                        "l.int_gpu_mem_min <= host_local.int_gpu_mem_idle " +
                    "AND " +
                        "l.pk_layer IN (" +
                            "SELECT " +
                                "la.pk_layer " +
                            "FROM " +
                                "layer la " +
                            "LEFT JOIN layer_limit ON layer_limit.pk_layer = la.pk_layer " +
                            "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                            "LEFT JOIN (" +
                                "SELECT " +
                                    "limit_record.pk_limit_record, " +
                                    "SUM(layer_stat.int_running_count) AS int_sum_running " +
                                "FROM " +
                                    "layer_limit " +
                                "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                                "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                                "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                            "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                            "WHERE " +
                                "sum_running.int_sum_running < limit_record.int_max_value " +
                                "OR sum_running.int_sum_running IS NULL " +
                        ") " +
                ") " +
        ") AS t1 " +
        "WHERE rank < 5";

    /**
     * This query is run before a proc is dispatched to the next frame.
     * It checks to see if there is another job someplace that is
     * under its minimum and can take the proc.
     *
     * The current job the proc is on is excluded.  This should only be run
     * if the excluded job is actually over its min proc.
     *
     * Does not unbook for Utility frames
     *
     */
    public static final String FIND_UNDER_PROCED_JOB_BY_FACILITY =
        "SELECT " +
            "1 " +
        "FROM " +
            "job, " +
            "job_resource, " +
            "folder, " +
            "folder_resource " +
        "WHERE " +
            "job.pk_job = job_resource.pk_job " +
        "AND " +
            "job.pk_folder = folder.pk_folder " +
        "AND " +
            "folder.pk_folder = folder_resource.pk_folder " +
        "AND " +
            "(folder_resource.int_max_cores = -1 OR folder_resource.int_cores < folder_resource.int_max_cores) " +
        "AND " +
            "(folder_resource.int_max_gpus = -1 OR folder_resource.int_gpus < folder_resource.int_max_gpus) " +
        "AND " +
            "job_resource.float_tier < 1.00 " +
        "AND " +
            "job_resource.int_cores < job_resource.int_min_cores " +
        "AND " +
            "job.str_state = 'PENDING' " +
        "AND " +
            "job.b_paused = false " +
        "AND " +
            "job.pk_show = ? " +
        "AND " +
            "job.pk_facility = ? " +
        "AND " +
            "(job.str_os = ? OR job.str_os IS NULL) " +
        "AND " +
            "job.pk_job IN ( " +
                "SELECT /* index (h i_str_host_tag) */ " +
                    "l.pk_job " +
                "FROM " +
                    "job j, " +
                    "layer l, " +
                    "layer_stat lst, " +
                    "host h " +
                "WHERE " +
                    "j.pk_job = l.pk_job " +
                "AND " +
                    "j.str_state = 'PENDING' " +
                "AND " +
                    "j.b_paused = false " +
                "AND " +
                    "j.pk_show = ? " +
                "AND " +
                    "j.pk_facility = ? " +
                "AND " +
                    "(j.str_os = ? OR j.str_os IS NULL) " +
                "AND " +
                    "(CASE WHEN lst.int_waiting_count > 0 THEN lst.pk_layer ELSE NULL END) = l.pk_layer " +
                "AND " +
                    "(CASE WHEN lst.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 " +
                "AND " +
                    "l.int_cores_min <= ? " +
                "AND " +
                    "l.int_mem_min <= ? " +
                "AND " +
                    "l.int_gpus_min <= ? " +
                "AND " +
                    "l.int_gpu_mem_min = ? " +
                "AND " +
                    "h.str_tags ~* ('(?x)' || l.str_tags || '\\y') " +
                "AND " +
                    "h.str_name = ? " +
                "AND " +
                    "l.pk_layer IN (" +
                        "SELECT " +
                            "la.pk_layer " +
                        "FROM " +
                            "layer la " +
                        "LEFT JOIN layer_limit ON layer_limit.pk_layer = la.pk_layer " +
                        "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                        "LEFT JOIN (" +
                            "SELECT " +
                                "limit_record.pk_limit_record, " +
                                "SUM(layer_stat.int_running_count) AS int_sum_running " +
                            "FROM " +
                                "layer_limit " +
                            "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                            "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                            "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                        "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                        "WHERE " +
                            "sum_running.int_sum_running < limit_record.int_max_value " +
                            "OR sum_running.int_sum_running IS NULL " +
                    ") " +
            ") " +
        "LIMIT 1";

    /**
     * This query is run before a proc is dispatched to the next frame.
     * It checks to see if there is another job someplace that is
     * at a higher priority and can take the proc.
     *
     * The current job the proc is on is excluded.  This should only be run
     * if the excluded job is actually over its min proc.
     *
     * Does not unbook for Utility frames
     *
     */
    public static final String HIGHER_PRIORITY_JOB_BY_FACILITY_EXISTS =
            "SELECT " +
                "1 " +
            "FROM " +
                "job, " +
                "job_resource, " +
                "folder, " +
                "folder_resource " +
            "WHERE " +
                "job.pk_job = job_resource.pk_job " +
            "AND " +
                "job.pk_folder = folder.pk_folder " +
            "AND " +
                "folder.pk_folder = folder_resource.pk_folder " +
            "AND " +
                "(folder_resource.int_max_cores = -1 OR folder_resource.int_cores < folder_resource.int_max_cores) " +
            "AND " +
                "(folder_resource.int_max_gpus = -1 OR folder_resource.int_gpus < folder_resource.int_max_gpus) " +
            "AND " +
                "job_resource.int_priority > ? " +
            "AND " +
                "job_resource.int_cores < job_resource.int_max_cores " +
            "AND " +
                "job_resource.int_gpus < job_resource.int_max_gpus " +
            "AND " +
                "job.str_state = 'PENDING' " +
            "AND " +
                "job.b_paused = false " +
            "AND " +
                "job.pk_facility = ? " +
            "AND " +
                "(job.str_os = ? OR job.str_os IS NULL) " +
            "AND " +
                "job.pk_job IN ( " +
                    "SELECT /* index (h i_str_host_tag) */ " +
                        "l.pk_job " +
                    "FROM " +
                        "job j, " +
                        "layer l, " +
                        "layer_stat lst, " +
                        "host h " +
                    "WHERE " +
                        "j.pk_job = l.pk_job " +
                    "AND " +
                        "j.str_state = 'PENDING' " +
                    "AND " +
                        "j.b_paused = false " +
                    "AND " +
                        "j.pk_facility = ? " +
                    "AND " +
                        "(j.str_os = ? OR j.str_os IS NULL) " +
                    "AND " +
                        "(CASE WHEN lst.int_waiting_count > 0 THEN lst.pk_layer ELSE NULL END) = l.pk_layer " +
                    "AND " +
                        "(CASE WHEN lst.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 " +
                    "AND " +
                        "l.int_cores_min <= ? " +
                    "AND " +
                        "l.int_mem_min <= ? " +
                    "AND " +
                        "l.int_gpus_min <= ? " +
                    "AND " +
                        "l.int_gpu_mem_min = ? " +
                    "AND " +
                        "h.str_tags ~* ('(?x)' || l.str_tags || '\\y') " +
                    "AND " +
                        "h.str_name = ? " +
                    "AND " +
                        "l.pk_layer IN (" +
                            "SELECT " +
                                "la.pk_layer " +
                            "FROM " +
                                "layer la " +
                            "LEFT JOIN layer_limit ON layer_limit.pk_layer = la.pk_layer " +
                            "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                            "LEFT JOIN (" +
                                "SELECT " +
                                    "limit_record.pk_limit_record, " +
                                    "SUM(layer_stat.int_running_count) AS int_sum_running " +
                                "FROM " +
                                    "layer_limit " +
                                "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                                "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                                "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                            "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                            "WHERE " +
                                "sum_running.int_sum_running < limit_record.int_max_value " +
                                "OR sum_running.int_sum_running IS NULL " +
                        ") " +
                ") " +
            "LIMIT 1";

    private static final String FIND_DISPATCH_FRAME_COLUMNS =
        "show_name, " +
        "job_name, " +
        "pk_job, " +
        "pk_show, " +
        "pk_facility, " +
        "str_name, " +
        "str_shot, " +
        "str_user, " +
        "int_uid, " +
        "str_log_dir, " +
        "COALESCE(str_os, '') AS str_os, " +
        "COALESCE(str_loki_url, '') AS str_loki_url, " +
        "frame_name, " +
        "frame_state, " +
        "pk_frame, " +
        "pk_layer, " +
        "int_retries, " +
        "int_version, " +
        "layer_name, " +
        "layer_type, " +
        "b_threadable, " +
        "int_cores_min, " +
        "int_cores_max, " +
        "int_mem_min, " +
        "int_gpus_min, " +
        "int_gpus_max, " +
        "int_gpu_mem_min, " +
        "str_cmd, " +
        "str_range, " +
        "int_chunk_size, " +
        "str_services ";
    /**
     * Finds the next frame in a job for a proc.
     */
    public static final String FIND_DISPATCH_FRAME_BY_JOB_AND_PROC =
        "SELECT " + FIND_DISPATCH_FRAME_COLUMNS +
        "FROM ( " +
            "SELECT " +
                "ROW_NUMBER() OVER ( ORDER BY " +
                    "frame.int_dispatch_order ASC, " +
                    "frame.int_layer_order ASC " +
                ") AS LINENUM, " +
                "job.str_show AS show_name, " +
                "job.str_name AS job_name, " +
                "job.pk_job, " +
                "job.pk_show, " +
                "job.pk_facility, " +
                "job.str_name, " +
                "job.str_shot, " +
                "job.str_user, " +
                "job.int_uid, " +
                "job.str_log_dir, " +
                "job.str_os, " +
                "job.str_loki_url, " +
                "frame.str_name AS frame_name, " +
                "frame.str_state AS frame_state, " +
                "frame.pk_frame, " +
                "frame.pk_layer, " +
                "frame.int_retries, " +
                "frame.int_version, " +
                "layer.str_name AS layer_name, " +
                "layer.str_type AS layer_type, " +
                "layer.b_threadable, " +
                "layer.int_cores_min, " +
                "layer.int_cores_max, " +
                "layer.int_mem_min, " +
                "layer.int_gpus_min, " +
                "layer.int_gpus_max, " +
                "layer.int_gpu_mem_min, " +
                "layer.str_cmd, " +
                "layer.str_range, " +
                "layer.int_chunk_size, " +
                "layer.str_services " +
            "FROM " +
                "job, " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.pk_job = job.pk_job " +
            "AND " +
                "layer.int_cores_min <= ? " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "layer.int_gpus_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min BETWEEN ? AND ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "job.pk_job=? " +
            "AND layer.pk_layer IN ( " +
                "SELECT /*+ index (h i_str_host_tag) */ " +
                    "l.pk_layer " +
                "FROM " +
                    "layer l " +
                "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags || '\\y') AND h.str_name = ?) " +
                "LEFT JOIN layer_limit ON layer_limit.pk_layer = l.pk_layer " +
                "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                "LEFT JOIN (" +
                    "SELECT " +
                        "limit_record.pk_limit_record, " +
                        "SUM(layer_stat.int_running_count) AS int_sum_running " +
                    "FROM " +
                        "layer_limit " +
                    "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                    "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                    "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                "WHERE " +
                    "l.pk_job= ? " +
                "AND " +
                    "sum_running.int_sum_running < limit_record.int_max_value " +
                    "OR sum_running.int_sum_running IS NULL " +
            ") " +
        ") AS t1 WHERE LINENUM <= ?";

    /**
     * Find the next frame in a job for a host.
     */
    public static final String FIND_DISPATCH_FRAME_BY_JOB_AND_HOST =
        "SELECT " + FIND_DISPATCH_FRAME_COLUMNS +
        "FROM ( " +
            "SELECT " +
                "ROW_NUMBER() OVER ( ORDER BY " +
                    "frame.int_dispatch_order ASC, " +
                    "frame.int_layer_order ASC " +
                ") AS LINENUM, " +
                "job.str_show AS show_name, " +
                "job.str_name AS job_name, " +
                "job.pk_job, " +
                "job.pk_show, " +
                "job.pk_facility, " +
                "job.str_name, " +
                "job.str_shot, " +
                "job.str_user, " +
                "job.int_uid, " +
                "job.str_log_dir, " +
                "job.str_os, " +
                "job.str_loki_url, " +
                "frame.str_name AS frame_name, " +
                "frame.str_state AS frame_state, " +
                "frame.pk_frame, " +
                "frame.pk_layer, " +
                "frame.int_retries, " +
                "frame.int_version, " +
                "layer.str_name AS layer_name, " +
                "layer.str_type AS layer_type, " +
                "layer.int_cores_min, " +
                "layer.int_cores_max, " +
                "layer.int_gpus_min, " +
                "layer.int_gpus_max, " +
                "layer.b_threadable, " +
                "layer.int_mem_min, " +
                "layer.int_gpu_mem_min, " +
                "layer.str_cmd, " +
                "layer.str_range, " +
                "layer.int_chunk_size, " +
                "layer.str_services " +
            "FROM " +
                "job, " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.pk_job = job.pk_job " +
            "AND " +
                "layer.int_cores_min <= ? " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "(CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= ? " +
            "AND " +
                "layer.int_gpus_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min BETWEEN ? AND ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "job.pk_job=? " +
            "AND " +
                "layer.pk_layer IN ( " +
                    "SELECT /*+ index (h i_str_host_tag) */ " +
                        "l.pk_layer " +
                    "FROM " +
                        "layer l " +
                    "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags || '\\y') AND h.str_name = ?) " +
                    "LEFT JOIN layer_limit ON layer_limit.pk_layer = l.pk_layer " +
                    "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                    "LEFT JOIN (" +
                        "SELECT " +
                            "limit_record.pk_limit_record, " +
                            "SUM(layer_stat.int_running_count) AS int_sum_running " +
                        "FROM " +
                            "layer_limit " +
                        "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                        "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                        "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                    "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                    "WHERE " +
                        "l.pk_job = ? " +
                    "AND " +
                        "sum_running.int_sum_running < limit_record.int_max_value " +
                        "OR sum_running.int_sum_running IS NULL " +
                ") " +
        ") AS t1 WHERE LINENUM <= ?";


    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC =
        "SELECT " + FIND_DISPATCH_FRAME_COLUMNS +
        "FROM ( " +
            "SELECT " +
                "ROW_NUMBER() OVER ( ORDER BY " +
                    "frame.int_dispatch_order ASC, " +
                    "frame.int_layer_order ASC " +
                ") AS LINENUM, " +
                "job.str_show AS show_name, " +
                "job.str_name AS job_name, " +
                "job.pk_job, " +
                "job.pk_show, " +
                "job.pk_facility, " +
                "job.str_name, " +
                "job.str_shot, " +
                "job.str_user, " +
                "job.int_uid, " +
                "job.str_log_dir, " +
                "job.str_os, " +
                "job.str_loki_url, " +
                "frame.str_name AS frame_name, " +
                "frame.str_state AS frame_state, " +
                "frame.pk_frame, " +
                "frame.pk_layer, " +
                "frame.int_retries, " +
                "frame.int_version, " +
                "layer.str_name AS layer_name, " +
                "layer.str_type AS layer_type, " +
                "layer.b_threadable, " +
                "layer.int_cores_min, " +
                "layer.int_cores_max, " +
                "layer.int_mem_min, " +
                "layer.int_gpus_min, " +
                "layer.int_gpus_max, " +
                "layer.int_gpu_mem_min, " +
                "layer.str_cmd, " +
                "layer.str_range, " +
                "layer.int_chunk_size, " +
                "layer.str_services " +
            "FROM " +
                "job, " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.pk_job = job.pk_job " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min <= ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "job.pk_job=? " +
            "AND " +
                "layer.pk_layer IN (" +
                    "SELECT " +
                        "la.pk_layer " +
                    "FROM " +
                        "layer la " +
                    "LEFT JOIN layer_limit ON layer_limit.pk_layer = la.pk_layer " +
                    "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                    "LEFT JOIN (" +
                        "SELECT " +
                            "limit_record.pk_limit_record, " +
                            "SUM(layer_stat.int_running_count) AS int_sum_running " +
                        "FROM " +
                            "layer_limit " +
                        "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                        "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                        "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                    "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                    "WHERE " +
                        "sum_running.int_sum_running < limit_record.int_max_value " +
                        "OR sum_running.int_sum_running IS NULL " +
                ") " +
        ") AS t1 WHERE LINENUM <= ?";

    /**
     * Find the next frame in a job for a host.
     */
    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST =
        "SELECT " + FIND_DISPATCH_FRAME_COLUMNS +
        "FROM (" +
            "SELECT " +
                "ROW_NUMBER() OVER ( ORDER BY " +
                    "frame.int_dispatch_order ASC, " +
                    "frame.int_layer_order ASC " +
                ") LINENUM, " +
                "job.str_show AS show_name, " +
                "job.str_name AS job_name, " +
                "job.pk_job, " +
                "job.pk_show, " +
                "job.pk_facility, " +
                "job.str_name, " +
                "job.str_shot, " +
                "job.str_user, " +
                "job.int_uid, " +
                "job.str_log_dir, " +
                "job.str_os, " +
                "job.str_loki_url, " +
                "frame.str_name AS frame_name, " +
                "frame.str_state AS frame_state, " +
                "frame.pk_frame, " +
                "frame.pk_layer, " +
                "frame.int_retries, " +
                "frame.int_version, " +
                "layer.str_name AS layer_name, " +
                "layer.str_type AS layer_type, " +
                "layer.int_cores_min, " +
                "layer.int_cores_max, " +
                "layer.b_threadable, " +
                "layer.int_mem_min, " +
                "layer.int_gpus_min, " +
                "layer.int_gpus_max, " +
                "layer.int_gpu_mem_min, " +
                "layer.str_cmd, " +
                "layer.str_range, " +
                "layer.int_chunk_size, " +
                "layer.str_services " +
            "FROM " +
                "job, " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.pk_job = job.pk_job " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min <= ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "job.pk_job=? " +
            "AND " +
                "layer.pk_layer IN (" +
                    "SELECT " +
                        "la.pk_layer " +
                    "FROM " +
                        "layer la " +
                    "LEFT JOIN layer_limit ON layer_limit.pk_layer = la.pk_layer " +
                    "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                    "LEFT JOIN (" +
                        "SELECT " +
                            "limit_record.pk_limit_record, " +
                            "SUM(layer_stat.int_running_count) AS int_sum_running " +
                        "FROM " +
                            "layer_limit " +
                        "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                        "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                        "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                    "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                    "WHERE " +
                        "sum_running.int_sum_running < limit_record.int_max_value " +
                        "OR sum_running.int_sum_running IS NULL " +
                ") " +
        ") AS t1 WHERE LINENUM <= ?";


    /**** LAYER DISPATCHING **/

    /**
     * Finds the next frame in a job for a proc.
     */
    public static final String FIND_DISPATCH_FRAME_BY_LAYER_AND_PROC =
        "SELECT " + FIND_DISPATCH_FRAME_COLUMNS +
        "FROM (" +
            "SELECT " +
                "ROW_NUMBER() OVER ( ORDER BY " +
                    "frame.int_dispatch_order ASC, " +
                    "frame.int_layer_order ASC " +
                ") LINENUM, " +
                "job.str_show AS show_name, " +
                "job.str_name AS job_name, " +
                "job.pk_job, " +
                "job.pk_show, " +
                "job.pk_facility, " +
                "job.str_name, " +
                "job.str_shot, " +
                "job.str_user, " +
                "job.int_uid, " +
                "job.str_log_dir, " +
                "job.str_os, " +
                "job.str_loki_url, " +
                "frame.str_name AS frame_name, " +
                "frame.str_state AS frame_state, " +
                "frame.pk_frame, " +
                "frame.pk_layer, " +
                "frame.int_retries, " +
                "frame.int_version, " +
                "layer.str_name AS layer_name, " +
                "layer.str_type AS layer_type, " +
                "layer.b_threadable, " +
                "layer.int_cores_min, " +
                "layer.int_cores_max, " +
                "layer.int_mem_min, " +
                "layer.int_gpus_min, " +
                "layer.int_gpus_max, " +
                "layer.int_gpu_mem_min, " +
                "layer.str_cmd, " +
                "layer.str_range, " +
                "layer.int_chunk_size, " +
                "layer.str_services " +
            "FROM " +
                "job, " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.pk_job = job.pk_job " +
            "AND " +
                "layer.int_cores_min <= ? " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "layer.int_gpus_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min <= ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "job.pk_layer=? " +
            "AND layer.pk_layer IN ( " +
                "SELECT /*+ index (h i_str_host_tag) */ " +
                    "l.pk_layer " +
                "FROM " +
                    "layer l " +
                "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags || '\\y') AND h.str_name = ?) " +
                "LEFT JOIN layer_limit ON layer_limit.pk_layer = l.pk_layer " +
                "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                "LEFT JOIN (" +
                    "SELECT " +
                        "limit_record.pk_limit_record, " +
                        "SUM(layer_stat.int_running_count) AS int_sum_running " +
                    "FROM " +
                        "layer_limit " +
                    "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                    "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                    "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                "WHERE " +
                    "l.pk_layer= ? " +
                "AND " +
                    "sum_running.int_sum_running < limit_record.int_max_value " +
                    "OR sum_running.int_sum_running IS NULL " +
            ")" +
        ") WHERE LINENUM <= ?";

    /**
     * Find the next frame in a job for a host.
     */
    public static final String FIND_DISPATCH_FRAME_BY_LAYER_AND_HOST =
        "SELECT " + FIND_DISPATCH_FRAME_COLUMNS +
        "FROM (" +
            "SELECT " +
                "ROW_NUMBER() OVER ( ORDER BY " +
                    "frame.int_dispatch_order ASC, " +
                    "frame.int_layer_order ASC " +
                ") AS LINENUM, " +
                "job.str_show AS show_name, " +
                "job.str_name AS job_name, " +
                "job.pk_job, " +
                "job.pk_show, " +
                "job.pk_facility, " +
                "job.str_name, " +
                "job.str_shot, " +
                "job.str_user, " +
                "job.int_uid, " +
                "job.str_log_dir, " +
                "job.str_os, " +
                "job.str_loki_url, " +
                "frame.str_name AS frame_name, " +
                "frame.str_state AS frame_state, " +
                "frame.pk_frame, " +
                "frame.pk_layer, " +
                "frame.int_retries, " +
                "frame.int_version, " +
                "layer.str_name AS layer_name, " +
                "layer.str_type AS layer_type, " +
                "layer.int_cores_min, " +
                "layer.int_cores_max, " +
                "layer.b_threadable, " +
                "layer.int_mem_min, " +
                "layer.int_gpus_min, " +
                "layer.int_gpus_max, " +
                "layer.int_gpu_mem_min, " +
                "layer.str_cmd, " +
                "layer.str_range, " +
                "layer.int_chunk_size, " +
                "layer.str_services " +
            "FROM " +
                "job, " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.pk_job = job.pk_job " +
            "AND " +
                "layer.int_cores_min <= ? " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "(CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= ? " +
            "AND " +
                "layer.int_gpus_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min <= ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "layer.pk_layer=? " +
            "AND " +
                "layer.pk_layer IN ( " +
                    "SELECT /*+ index (h i_str_host_tag) */ " +
                        "l.pk_layer " +
                    "FROM " +
                        "layer l " +
                    "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags  || '\\y') AND h.str_name = ?) " +
                    "LEFT JOIN layer_limit ON layer_limit.pk_layer = l.pk_layer " +
                    "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                    "LEFT JOIN (" +
                        "SELECT " +
                            "limit_record.pk_limit_record, " +
                            "SUM(layer_stat.int_running_count) AS int_sum_running " +
                        "FROM " +
                            "layer_limit " +
                        "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                        "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                        "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                    "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                    "WHERE " +
                        "l.pk_layer= ? " +
                    "AND " +
                        "sum_running.int_sum_running < limit_record.int_max_value " +
                        "OR sum_running.int_sum_running IS NULL " +
                ") " +
        ") WHERE LINENUM <= ?";


    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC =
        "SELECT " + FIND_DISPATCH_FRAME_COLUMNS +
        "FROM (" +
            "SELECT " +
                "ROW_NUMBER() OVER ( ORDER BY " +
                    "frame.int_dispatch_order ASC, " +
                    "frame.int_layer_order ASC " +
                ") AS LINENUM, " +
                "job.str_show AS show_name, " +
                "job.str_name AS job_name, " +
                "job.pk_job, " +
                "job.pk_show, " +
                "job.pk_facility, " +
                "job.str_name, " +
                "job.str_shot, " +
                "job.str_user, " +
                "job.int_uid, " +
                "job.str_log_dir, " +
                "job.str_os, " +
                "job.str_loki_url, " +
                "frame.str_name AS frame_name, " +
                "frame.str_state AS frame_state, " +
                "frame.pk_frame, " +
                "frame.pk_layer, " +
                "frame.int_retries, " +
                "frame.int_version, " +
                "layer.str_name AS layer_name, " +
                "layer.str_type AS layer_type, " +
                "layer.b_threadable, " +
                "layer.int_cores_min, " +
                "layer.int_mem_min, " +
                "layer.int_gpus_min, " +
                "layer.int_gpus_max, " +
                "layer.int_gpu_mem_min, " +
                "layer.int_cores_max, " +
                "layer.str_cmd, " +
                "layer.str_range, " +
                "layer.int_chunk_size, " +
                "layer.str_services " +
            "FROM " +
                "job, " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.pk_job = job.pk_job " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min <= ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "layer.pk_layer = ? " +
            "AND " +
                "layer.pk_layer IN (" +
                    "SELECT " +
                        "la.pk_layer " +
                    "FROM " +
                        "layer la " +
                    "LEFT JOIN layer_limit ON layer_limit.pk_layer = la.pk_layer " +
                    "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                    "LEFT JOIN (" +
                        "SELECT " +
                            "limit_record.pk_limit_record, " +
                            "SUM(layer_stat.int_running_count) AS int_sum_running " +
                        "FROM " +
                            "layer_limit " +
                        "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                        "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                        "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                    "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                    "WHERE " +
                        "sum_running.int_sum_running < limit_record.int_max_value " +
                        "OR sum_running.int_sum_running IS NULL " +
                ") " +
        ") AS t1 WHERE LINENUM <= ?";

    /**
     * Find the next frame in a job for a host.
     */
    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST =
        "SELECT " + FIND_DISPATCH_FRAME_COLUMNS +
        "FROM (" +
            "SELECT " +
                "ROW_NUMBER() OVER (ORDER BY " +
                    "frame.int_dispatch_order ASC, " +
                    "frame.int_layer_order ASC " +
                ") AS LINENUM, " +
                "job.str_show AS show_name, " +
                "job.str_name AS job_name, " +
                "job.pk_job, " +
                "job.pk_show, " +
                "job.pk_facility, " +
                "job.str_name, " +
                "job.str_shot, " +
                "job.str_user, " +
                "job.int_uid, " +
                "job.str_log_dir, " +
                "job.str_os, " +
                "job.str_loki_url, " +
                "frame.str_name AS frame_name, " +
                "frame.str_state AS frame_state, " +
                "frame.pk_frame, " +
                "frame.pk_layer, " +
                "frame.int_retries, " +
                "frame.int_version, " +
                "layer.str_name AS layer_name, " +
                "layer.str_type AS layer_type, " +
                "layer.int_cores_min, " +
                "layer.int_cores_max, " +
                "layer.b_threadable, " +
                "layer.int_mem_min, " +
                "layer.int_gpus_min, " +
                "layer.int_gpus_max, " +
                "layer.int_gpu_mem_min, " +
                "layer.str_cmd, " +
                "layer.str_range, " +
                "layer.int_chunk_size, " +
                "layer.str_services " +
            "FROM " +
                "job, " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.pk_job = job.pk_job " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min <= ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "layer.pk_layer= ? " +
            "AND " +
                "layer.pk_layer IN (" +
                    "SELECT " +
                        "la.pk_layer " +
                    "FROM " +
                        "layer la " +
                    "LEFT JOIN layer_limit ON layer_limit.pk_layer = la.pk_layer " +
                    "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record " +
                    "LEFT JOIN (" +
                        "SELECT " +
                            "limit_record.pk_limit_record, " +
                            "SUM(layer_stat.int_running_count) AS int_sum_running " +
                        "FROM " +
                            "layer_limit " +
                        "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record " +
                        "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer " +
                        "GROUP BY limit_record.pk_limit_record) AS sum_running " +
                    "ON limit_record.pk_limit_record = sum_running.pk_limit_record " +
                    "WHERE " +
                        "sum_running.int_sum_running < limit_record.int_max_value " +
                        "OR sum_running.int_sum_running IS NULL " +
                ") " +
        ") AS t1 WHERE LINENUM <= ?";

    /**
     * Looks for shows that are under their burst for a particular
     * type of proc.  The show has to be at least one whole proc
     * under their burst to be considered for booking.
     */
    public static final String FIND_SHOWS =
        "SELECT " +
            "vs_waiting.pk_show, " +
            "s.float_tier, " +
            "s.int_burst " +
        "FROM " +
            "subscription s, " +
            "vs_waiting " +
        "WHERE " +
            "vs_waiting.pk_show = s.pk_show " +
        "AND " +
            "s.pk_alloc = ? " +
        "AND " +
            "s.int_burst > 0 " +
        "AND " +
             "s.int_burst - s.int_cores >= 100 " +
        "AND " +
            "s.int_cores < s.int_burst ";

}


// spotless:on
