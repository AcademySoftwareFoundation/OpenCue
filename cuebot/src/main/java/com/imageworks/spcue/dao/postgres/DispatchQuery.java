
/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */



package com.imageworks.spcue.dao.postgres;

public class DispatchQuery {

    public static final String FIND_JOBS_BY_SHOW =
        "/* FIND_JOBS_BY_SHOW */ " +
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
                "AND job_resource.pk_job    = job.pk_job " +
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
                        "job.str_os = ? " +
                    ") " +
                "AND (CASE WHEN layer_stat.int_waiting_count > 0 THEN 1 ELSE NULL END) = 1 " +
                "AND layer.int_cores_min            <= ? " +
                "AND layer.int_mem_min              <= ? " +
                "AND (CASE WHEN layer.b_threadable = true THEN 1 ELSE 0 END) >= ? " +
                "AND layer.int_gpus_min             <= ? " +
                "AND layer.int_gpu_mem_min          BETWEEN ? AND ? " +
                "AND job_resource.int_cores + layer.int_cores_min < job_resource.int_max_cores " +
                "AND job_resource.int_gpus + layer.int_gpus_min < job_resource.int_max_gpus " +
                "AND host.str_tags ~* ('(?x)' || layer.str_tags) " +
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


    public static final String FIND_JOBS_BY_GROUP =
        FIND_JOBS_BY_SHOW
            .replace(
                "FIND_JOBS_BY_SHOW",
                "FIND_JOBS_BY_GROUP")
            .replace(
                "AND job.pk_show                    = ? ",
                "AND job.pk_folder                  = ? ");


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
                "(job.str_os = ? OR job.str_os IS NULL)" +
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
                        "(j.str_os = ? OR j.str_os IS NULL)" +
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
            "(job.str_os = ? OR job.str_os IS NULL)" +
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
                    "(j.str_os = ? OR j.str_os IS NULL)" +
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
                    "h.str_tags ~* ('(?x)' || l.str_tags) " +
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
                "job_resource.int_priority > ?" +
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
                "(job.str_os = ? OR job.str_os IS NULL)" +
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
                        "(j.str_os = ? OR j.str_os IS NULL)" +
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
                        "h.str_tags ~* ('(?x)' || l.str_tags) " +
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
     * Schedule the next frame in a job for a proc.
     */
    private static final String SCHEDULE_TIMEOUT = "interval '60' second";
    public static final String SCHEDULE_DISPATCH_FRAME_BY_JOB_AND_PROC =
        "WITH rows AS ( " +
            "SELECT " +
                "frame.pk_frame " +
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
                "(frame.str_scheduled_by IS NULL OR " +
                    "current_timestamp - frame.ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
            "AND " +
                "job.pk_job=? " +
            "AND layer.pk_layer IN ( " +
                "SELECT /*+ index (h i_str_host_tag) */ " +
                    "l.pk_layer " +
                "FROM " +
                    "layer l " +
                "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags) AND h.str_name = ?) " +
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
            "ORDER BY " +
                "frame.int_dispatch_order ASC, " +
                "frame.int_layer_order ASC " +
            "LIMIT " +
                "? " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    /**
     * Schedule the next frame in a job for a host.
     */
    public static final String SCHEDULE_DISPATCH_FRAME_BY_JOB_AND_HOST =
        "WITH rows AS ( " +
            "SELECT " +
                "frame.pk_frame " +
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
                "(frame.str_scheduled_by IS NULL OR " +
                    "current_timestamp - frame.ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
            "AND " +
                "job.pk_job=? " +
            "AND " +
                "layer.pk_layer IN ( " +
                    "SELECT /*+ index (h i_str_host_tag) */ " +
                        "l.pk_layer " +
                    "FROM " +
                        "layer l " +
                    "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags) AND h.str_name = ?) " +
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
            "ORDER BY " +
                "frame.int_dispatch_order ASC, " +
                "frame.int_layer_order ASC " +
            "LIMIT " +
                "? " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    public static final String SCHEDULE_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC =
        "WITH rows AS ( " +
            "SELECT " +
                "frame.pk_frame " +
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
                "(frame.str_scheduled_by IS NULL OR " +
                    "current_timestamp - frame.ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
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
            "ORDER BY " +
                "frame.int_dispatch_order ASC, " +
                "frame.int_layer_order ASC " +
            "LIMIT " +
                "? " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    /**
     * Schedule the next frame in a job for a host.
     */
    public static final String SCHEDULE_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST =
        "WITH rows AS ( " +
            "SELECT " +
                "frame.pk_frame " +
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
                "(frame.str_scheduled_by IS NULL OR " +
                    "current_timestamp - frame.ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
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
            "ORDER BY " +
                "frame.int_dispatch_order ASC, " +
                "frame.int_layer_order ASC " +
            "LIMIT " +
                "? " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    /**** LAYER DISPATCHING **/

    /**
     * Schedule the next frame in a job for a proc.
     */
    public static final String SCHEDULE_DISPATCH_FRAME_BY_LAYER_AND_PROC =
        "WITH rows AS ( " +
            "SELECT " +
                "frame.pk_frame " +
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
                "(frame.str_scheduled_by IS NULL OR " +
                    "current_timestamp - frame.ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
            "AND " +
                "job.pk_layer=? " +
            "AND layer.pk_layer IN ( " +
                "SELECT /*+ index (h i_str_host_tag) */ " +
                    "l.pk_layer " +
                "FROM " +
                    "layer l " +
                "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags) AND h.str_name = ?) " +
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
            "ORDER BY " +
                "frame.int_dispatch_order ASC, " +
                "frame.int_layer_order ASC " +
            "LIMIT " +
                "? " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    /**
     * Schedule the next frame in a job for a host.
     */
    public static final String SCHEDULE_DISPATCH_FRAME_BY_LAYER_AND_HOST =
        "WITH rows AS ( " +
            "SELECT " +
                "frame.pk_frame " +
            "FROM " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
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
                "(frame.str_scheduled_by IS NULL OR " +
                    "current_timestamp - frame.ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
            "AND " +
                "layer.pk_layer=? " +
            "AND " +
                "layer.pk_layer IN ( " +
                    "SELECT /*+ index (h i_str_host_tag) */ " +
                        "l.pk_layer " +
                    "FROM " +
                        "layer l " +
                    "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags) AND h.str_name = ?) " +
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
            "ORDER BY " +
                "frame.int_dispatch_order ASC, " +
                "frame.int_layer_order ASC " +
            "LIMIT " +
                "? " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    public static final String SCHEDULE_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC =
        "WITH rows AS ( " +
            "SELECT " +
                "frame.pk_frame " +
            "FROM " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min <= ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "(frame.str_scheduled_by IS NULL OR " +
                    "current_timestamp - frame.ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
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
            "ORDER BY " +
                "frame.int_dispatch_order ASC, " +
                "frame.int_layer_order ASC " +
            "LIMIT " +
                "? " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    /**
     * Schedule the next frame in a job for a host.
     */
    public static final String SCHEDULE_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST =
        "WITH rows AS ( " +
            "SELECT " +
                "frame.pk_frame " +
            "FROM " +
                "frame, " +
                "layer " +
            "WHERE " +
                "frame.pk_layer = layer.pk_layer " +
            "AND " +
                "layer.int_mem_min <= ? " +
            "AND " +
                "layer.int_gpu_mem_min <= ? " +
            "AND " +
                "frame.str_state='WAITING' " +
            "AND " +
                "(frame.str_scheduled_by IS NULL OR " +
                    "current_timestamp - frame.ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
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
            "ORDER BY " +
                "frame.int_dispatch_order ASC, " +
                "frame.int_layer_order ASC " +
            "LIMIT " +
                "? " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    public static final String SCHEDULE_DISPATCH_FRAME =
        "WITH rows AS ( " +
            "SELECT " +
                "pk_frame "+
            "FROM " +
                "frame " +
            "WHERE " +
                "pk_frame = ?" +
            "AND " +
                "str_state='WAITING' " +
            "AND " +
                "(str_scheduled_by IS NULL OR " +
                    "current_timestamp - ts_scheduled > " + SCHEDULE_TIMEOUT + ") " +
        ") " +
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = ?, " +
            "ts_scheduled = current_timestamp " +
        "FROM " +
            "rows " +
        "WHERE " +
            "frame.pk_frame = rows.pk_frame ";

    public static final String GET_SCHEDULED_DISPATCH_FRAMES =
        "SELECT " +
            "frame.pk_frame, "+
            "frame.str_name AS frame_name, "+
            "frame.pk_layer, "+
            "job.pk_job,"+
            "job.pk_show,"+
            "job.pk_facility,"+
            "frame.int_retries, "+
            "frame.str_state AS frame_state, "+
            "layer.str_cmd, "+
            "job.str_name AS job_name, " +
            "layer.str_name AS layer_name, " +
            "layer.int_chunk_size, " +
            "layer.str_range, "+
            "job.str_log_dir,"+
            "job.str_shot,"+
            "show.str_name AS show_name, "+
            "job.str_user,"+
            "job.int_uid,"+
            "layer.int_cores_min,"+
            "layer.int_cores_max,"+
            "layer.b_threadable,"+
            "layer.int_mem_min, "+
            "layer.int_gpus_min,"+
            "layer.int_gpus_max,"+
            "layer.int_gpu_mem_min, "+
            "frame.int_version, " +
            "layer.str_services " +
        "FROM " +
            "show, " +
            "job, "+
            "frame, " +
            "layer " +
        "WHERE " +
            "job.pk_show = show.pk_show "+
        "AND " +
            "frame.pk_job = job.pk_job " +
        "AND " +
            "frame.pk_layer = layer.pk_layer " +
        "AND " +
            "frame.str_scheduled_by = ? " +
        "ORDER BY " +
            "frame.int_dispatch_order ASC, " +
            "frame.int_layer_order ASC " +
        "LIMIT " +
            "? ";

    public static final String UNSCHEDULE_DISPATCH_FRAMES =
        "UPDATE " +
            "frame " +
        "SET " +
            "str_scheduled_by = NULL " +
        "WHERE " +
            "pk_frame IN (%s) ";

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

