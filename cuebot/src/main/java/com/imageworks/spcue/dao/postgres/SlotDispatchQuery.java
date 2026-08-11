
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

/**
 * SQL for slot-based dispatching.
 *
 * Slot-based booking is an alternative dispatch mode for hosts marked with a concurrent slots limit
 * ({@code host.int_concurrent_slots_limit >= 0}). Slot hosts run only slot-based layers
 * ({@code layer.int_slots_required > 0}); slot layers run only on slot hosts. A slot booking
 * reserves 0 cores and 0 memory - the only constraints are the per-host slot cap and the
 * {@code int_max_slots} limits at the subscription, folder and job levels (-1 = unlimited, 0 =
 * reject-all, N = cap at N concurrent slots). {@code proc.int_slots_reserved} is the single source
 * of truth for slot usage at every level.
 *
 * These queries are intentionally kept separate from {@link DispatchQuery}: the generic
 * cores/memory dispatch pipeline is performance sensitive and must not be affected by the slot
 * axis. The only interaction with the generic path is the {@code *_EXCLUDE_SLOT} variants below,
 * which append a single equality predicate so regular hosts and procs never pick up slot-based
 * frames (strict pairing).
 */
public class SlotDispatchQuery {

    /**
     * Marker present in every generic frame-dispatch query; used to append the slot-layer exclusion
     * predicate without touching {@link DispatchQuery} itself.
     */
    private static final String WAITING_MARKER = "frame.str_state='WAITING' ";

    private static String excludeSlotLayers(String query) {
        if (!query.contains(WAITING_MARKER)) {
            throw new IllegalStateException(
                    "Generic dispatch query no longer contains the WAITING marker; "
                            + "the slot-layer exclusion cannot be applied.");
        }
        return query.replace(WAITING_MARKER,
                "frame.str_state='WAITING' AND layer.int_slots_required = 0 ");
    }

    /**
     * Generic frame-dispatch queries with slot-based layers excluded. Used by the regular dispatch
     * path so a slot layer can never book onto a regular (cores/memory) host or proc.
     */
    public static final String FIND_DISPATCH_FRAME_BY_JOB_AND_PROC_EXCLUDE_SLOT =
            excludeSlotLayers(DispatchQuery.FIND_DISPATCH_FRAME_BY_JOB_AND_PROC);

    public static final String FIND_DISPATCH_FRAME_BY_JOB_AND_HOST_EXCLUDE_SLOT =
            excludeSlotLayers(DispatchQuery.FIND_DISPATCH_FRAME_BY_JOB_AND_HOST);

    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC_EXCLUDE_SLOT =
            excludeSlotLayers(DispatchQuery.FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_PROC);

    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST_EXCLUDE_SLOT =
            excludeSlotLayers(DispatchQuery.FIND_LOCAL_DISPATCH_FRAME_BY_JOB_AND_HOST);

    public static final String FIND_DISPATCH_FRAME_BY_LAYER_AND_PROC_EXCLUDE_SLOT =
            excludeSlotLayers(DispatchQuery.FIND_DISPATCH_FRAME_BY_LAYER_AND_PROC);

    public static final String FIND_DISPATCH_FRAME_BY_LAYER_AND_HOST_EXCLUDE_SLOT =
            excludeSlotLayers(DispatchQuery.FIND_DISPATCH_FRAME_BY_LAYER_AND_HOST);

    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC_EXCLUDE_SLOT =
            excludeSlotLayers(DispatchQuery.FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_PROC);

    public static final String FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST_EXCLUDE_SLOT =
            excludeSlotLayers(DispatchQuery.FIND_LOCAL_DISPATCH_FRAME_BY_LAYER_AND_HOST);

    /**
     * Find jobs with pending slot-based work bookable on a slot host.
     *
     * A job qualifies when it is PENDING, matches the host's facility/OS, has at least one
     * slot-based layer with waiting frames whose tags match the host and whose slot requirement
     * fits the host's idle slots, and is under the job/folder max_slots caps. The show must also
     * subscribe to the host's allocation and be under the subscription max_slots cap. Slot usage at
     * every level derives from SUM(proc.int_slots_reserved).
     *
     * Binds: facility, os..., idle_slots, host_name, alloc, limit
     */
    // spotless:off
    public static final String FIND_SLOT_DISPATCH_JOBS =
            "/* FIND_SLOT_DISPATCH_JOBS */ "
            + "SELECT pk_job, int_priority, rank FROM ( "
                + "SELECT "
                    + "ROW_NUMBER() OVER (ORDER BY job_resource.int_priority DESC) AS rank, "
                    + "job.pk_job, "
                    + "job_resource.int_priority "
                + "FROM "
                    + "job "
                + "JOIN job_resource ON job_resource.pk_job = job.pk_job "
                + "JOIN folder_resource ON folder_resource.pk_folder = job.pk_folder "
                + "JOIN show ON show.pk_show = job.pk_show "
                + "WHERE "
                    /* Scheduler-managed shows are dispatched by the standalone Rust
                     * scheduler, including their slot-based work. */
                    + "show.b_scheduler_managed = false "
                + "AND "
                    + "job.str_state = 'PENDING' "
                + "AND "
                    + "job.b_paused = false "
                + "AND "
                    + "job.pk_facility = ? "
                + "AND "
                    + "(job.str_os IS NULL OR job.str_os = '' OR job.str_os IN ?) "
                + "AND EXISTS ( "
                    + "SELECT 1 "
                    + "FROM "
                        + "layer "
                    + "JOIN layer_stat ON layer_stat.pk_layer = layer.pk_layer "
                    + "JOIN host ON host.str_tags ~* ('(?x)' || layer.str_tags || '\\y') "
                    + "WHERE "
                        + "layer.pk_job = job.pk_job "
                    + "AND "
                        + "layer.int_slots_required > 0 "
                    + "AND "
                        + "layer.int_slots_required <= ? "
                    + "AND "
                        + "layer_stat.int_waiting_count > 0 "
                    + "AND "
                        + "host.str_name = ? "
                + ") "
                + "AND "
                    + "(job_resource.int_max_slots = -1 OR "
                        + "(SELECT COALESCE(SUM(proc.int_slots_reserved), 0) FROM proc "
                            + "WHERE proc.pk_job = job.pk_job) "
                        + "< job_resource.int_max_slots) "
                + "AND "
                    + "(folder_resource.int_max_slots = -1 OR "
                        + "(SELECT COALESCE(SUM(proc.int_slots_reserved), 0) "
                            + "FROM proc JOIN job j ON j.pk_job = proc.pk_job "
                            + "WHERE j.pk_folder = job.pk_folder) "
                        + "< folder_resource.int_max_slots) "
                + "AND EXISTS ( "
                    + "SELECT 1 FROM subscription s "
                    + "WHERE "
                        + "s.pk_show = job.pk_show "
                    + "AND "
                        + "s.pk_alloc = ? "
                    + "AND "
                        + "(s.int_max_slots = -1 OR "
                            + "(SELECT COALESCE(SUM(p.int_slots_reserved), 0) "
                                + "FROM proc p JOIN host h ON h.pk_host = p.pk_host "
                                + "WHERE p.pk_show = s.pk_show AND h.pk_alloc = s.pk_alloc) "
                            + "< s.int_max_slots) "
                + ") "
            /* rank < ? returns numJobs - 1 rows; kept as-is for parity with the generic
             * FIND_JOBS queries, which use the same bound. */
            + ") AS t1 WHERE rank < ?";
    // spotless:on

    /**
     * Compute how many more slots the given job may book, taking the smallest remaining allowance
     * across the job, folder and subscription max_slots caps. NULL means unlimited (all three caps
     * are -1). Usage at every level derives from SUM(proc.int_slots_reserved).
     *
     * Binds: alloc, job
     */
    // spotless:off
    public static final String GET_SLOT_CAPACITY_REMAINING =
            "/* GET_SLOT_CAPACITY_REMAINING */ "
            + "SELECT LEAST( "
                + "CASE WHEN job_resource.int_max_slots = -1 THEN NULL "
                    + "ELSE job_resource.int_max_slots - "
                        + "(SELECT COALESCE(SUM(p.int_slots_reserved), 0) FROM proc p "
                            + "WHERE p.pk_job = job.pk_job) "
                + "END, "
                + "CASE WHEN folder_resource.int_max_slots = -1 THEN NULL "
                    + "ELSE folder_resource.int_max_slots - "
                        + "(SELECT COALESCE(SUM(p.int_slots_reserved), 0) "
                            + "FROM proc p JOIN job j2 ON j2.pk_job = p.pk_job "
                            + "WHERE j2.pk_folder = job.pk_folder) "
                + "END, "
                + "CASE WHEN s.int_max_slots = -1 THEN NULL "
                    + "ELSE s.int_max_slots - "
                        + "(SELECT COALESCE(SUM(p.int_slots_reserved), 0) "
                            + "FROM proc p JOIN host h ON h.pk_host = p.pk_host "
                            + "WHERE p.pk_show = job.pk_show AND h.pk_alloc = s.pk_alloc) "
                + "END "
            + ") AS int_slot_capacity "
            + "FROM job "
            + "JOIN job_resource ON job_resource.pk_job = job.pk_job "
            + "JOIN folder_resource ON folder_resource.pk_folder = job.pk_folder "
            + "JOIN subscription s ON s.pk_show = job.pk_show AND s.pk_alloc = ? "
            + "WHERE job.pk_job = ?";
    // spotless:on

    /**
     * Find the next slot-based frames in a job for a slot host.
     *
     * Selects WAITING frames of slot-based layers whose slot requirement fits the host's idle
     * slots, whose tags match the host, that are under the layer limits (limit_record) and under
     * the job/folder/subscription max_slots caps counting this layer's requirement.
     *
     * Binds: idle_slots, job, host_name, job, alloc, limit
     */
    // spotless:off
    public static final String FIND_SLOT_DISPATCH_FRAMES_BY_JOB_AND_HOST =
            "/* FIND_SLOT_DISPATCH_FRAMES_BY_JOB_AND_HOST */ "
            + "SELECT "
                + "show_name, "
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
                + "int_slots_required, "
                + "str_cmd, "
                + "str_range, "
                + "int_chunk_size, "
                + "str_services "
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
                    + "layer.int_slots_required, "
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
                    + "frame.str_state='WAITING' "
                + "AND "
                    + "layer.int_slots_required > 0 "
                + "AND "
                    + "layer.int_slots_required <= ? "
                + "AND "
                    + "job.pk_job = ? "
                + "AND "
                    + "layer.pk_layer IN ( "
                        + "SELECT "
                            + "l.pk_layer "
                        + "FROM "
                            + "layer l "
                        + "JOIN job j ON j.pk_job = l.pk_job "
                        + "JOIN job_resource ON job_resource.pk_job = j.pk_job "
                        + "JOIN folder_resource ON folder_resource.pk_folder = j.pk_folder "
                        + "JOIN host h ON (h.str_tags ~* ('(?x)' || l.str_tags || '\\y') AND h.str_name = ?) "
                        + "LEFT JOIN layer_limit ON layer_limit.pk_layer = l.pk_layer "
                        + "LEFT JOIN limit_record ON limit_record.pk_limit_record = layer_limit.pk_limit_record "
                        + "LEFT JOIN ("
                            + "SELECT "
                                + "limit_record.pk_limit_record, "
                                + "SUM(layer_stat.int_running_count) AS int_sum_running "
                            + "FROM "
                                + "layer_limit "
                            + "LEFT JOIN limit_record ON layer_limit.pk_limit_record = limit_record.pk_limit_record "
                            + "LEFT JOIN layer_stat ON layer_stat.pk_layer = layer_limit.pk_layer "
                            + "GROUP BY limit_record.pk_limit_record) AS sum_running "
                        + "ON limit_record.pk_limit_record = sum_running.pk_limit_record "
                        + "WHERE "
                            + "l.pk_job = ? "
                        + "AND "
                            + "(sum_running.int_sum_running < limit_record.int_max_value "
                                + "OR sum_running.int_sum_running IS NULL) "
                        + "AND "
                            + "(job_resource.int_max_slots = -1 OR "
                                + "(SELECT COALESCE(SUM(proc.int_slots_reserved), 0) FROM proc "
                                    + "WHERE proc.pk_job = j.pk_job) "
                                + "+ l.int_slots_required <= job_resource.int_max_slots) "
                        + "AND "
                            + "(folder_resource.int_max_slots = -1 OR "
                                + "(SELECT COALESCE(SUM(proc.int_slots_reserved), 0) "
                                    + "FROM proc JOIN job j2 ON j2.pk_job = proc.pk_job "
                                    + "WHERE j2.pk_folder = j.pk_folder) "
                                + "+ l.int_slots_required <= folder_resource.int_max_slots) "
                        + "AND EXISTS ( "
                            + "SELECT 1 FROM subscription s "
                            + "WHERE "
                                + "s.pk_show = j.pk_show "
                            + "AND "
                                + "s.pk_alloc = ? "
                            + "AND "
                                + "(s.int_max_slots = -1 OR "
                                    + "(SELECT COALESCE(SUM(p.int_slots_reserved), 0) "
                                        + "FROM proc p JOIN host h2 ON h2.pk_host = p.pk_host "
                                        + "WHERE p.pk_show = s.pk_show AND h2.pk_alloc = s.pk_alloc) "
                                    + "+ l.int_slots_required <= s.int_max_slots) "
                        + ") "
                + ") "
            + ") AS t1 WHERE LINENUM <= ?";
    // spotless:on
}
