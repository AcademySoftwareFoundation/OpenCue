-- Increase the length of show names
-- We drop and recreate the views as we are modifying fields that are used in these view.
-- postgres will raise a error otherwise on the alter.

DROP VIEW v_history_frame;
DROP VIEW v_history_job;
DROP VIEW v_history_layer;

ALTER TABLE "show" ALTER COLUMN "str_name" TYPE VARCHAR(512);
ALTER TABLE "job" ALTER COLUMN "str_show" TYPE VARCHAR(512);

CREATE VIEW v_history_frame (pk_frame_history, pk_frame, pk_layer, pk_job, str_name, str_state,
    int_mem_reserved, int_mem_max_used, int_cores, str_host, int_exit_status, str_alloc_name,
    b_alloc_billable, str_facility_name, int_ts_started, int_ts_stopped, int_checkpoint_count,
    str_show_name, dt_last_modified) AS
  SELECT
    fh.PK_FRAME_HISTORY,
    fh.PK_FRAME,
    fh.PK_LAYER,
    fh.PK_JOB,
    fh.STR_NAME,
    fh.STR_STATE,
    fh.INT_MEM_RESERVED,
    fh.INT_MEM_MAX_USED,
    fh.INT_CORES,
    fh.STR_HOST,
    fh.INT_EXIT_STATUS,
    a.STR_NAME STR_ALLOC_NAME,
    a.B_BILLABLE B_ALLOC_BILLABLE,
    f.STR_NAME STR_FACILITY_NAME,
    fh.INT_TS_STARTED,
    fh.INT_TS_STOPPED,
    fh.INT_CHECKPOINT_COUNT,
    null str_show_name,
    fh.dt_last_modified
  FROM frame_history fh
  JOIN job_history jh
    ON fh.pk_job = jh.pk_job
  LEFT OUTER JOIN alloc a
    ON fh.pk_alloc = a.pk_alloc
  LEFT OUTER JOIN facility f
    ON a.pk_facility = f.pk_facility
  WHERE fh.dt_last_modified >= (SELECT dt_begin FROM history_period)
    AND fh.dt_last_modified < (SELECT dt_end FROM history_period);


CREATE VIEW v_history_job (pk_job, str_name, str_shot, str_user, int_core_time_success, int_core_time_fail, int_frame_count, int_layer_count, int_waiting_count, int_dead_count, int_depend_count, int_eaten_count, int_succeeded_count, int_running_count, int_max_rss, b_archived, str_facility_name, str_dept_name, int_ts_started, int_ts_stopped, str_show_name, dt_last_modified) AS
  select
jh.PK_JOB,
jh.STR_NAME,
jh.STR_SHOT,
jh.STR_USER,
jh.INT_CORE_TIME_SUCCESS,
jh.INT_CORE_TIME_FAIL,
jh.INT_FRAME_COUNT,
jh.INT_LAYER_COUNT,
jh.INT_WAITING_COUNT,
jh.INT_DEAD_COUNT,
jh.INT_DEPEND_COUNT,
jh.INT_EATEN_COUNT,
jh.INT_SUCCEEDED_COUNT,
jh.INT_RUNNING_COUNT,
jh.INT_MAX_RSS,
jh.B_ARCHIVED,
f.str_name STR_FACILITY_NAME,
d.str_name str_dept_name,
jh.INT_TS_STARTED,
jh.INT_TS_STOPPED,
s.str_name str_show_name,
jh.dt_last_modified
from job_history jh, show s, facility f, dept d
where jh.pk_show   = s.pk_show
and jh.pk_facility = f.pk_facility
and jh.pk_dept     = d.pk_dept
and (
    jh.dt_last_modified >= (
        select dt_begin
        from history_period
    )
    or
    jh.int_ts_stopped = 0
);


CREATE VIEW v_history_layer (pk_layer, pk_job, str_name, str_type, int_cores_min,
    int_mem_min, int_core_time_success, int_core_time_fail, int_frame_count, int_layer_count,
    int_waiting_count, int_dead_count, int_depend_count, int_eaten_count, int_succeeded_count,
    int_running_count, int_max_rss, b_archived, str_services, str_show_name, dt_last_modified) AS
  SELECT
lh.PK_LAYER,
lh.PK_JOB,
lh.STR_NAME,
lh.STR_TYPE,
lh.INT_CORES_MIN,
lh.INT_MEM_MIN,
lh.INT_CORE_TIME_SUCCESS,
lh.INT_CORE_TIME_FAIL,
lh.INT_FRAME_COUNT,
lh.INT_LAYER_COUNT,
lh.INT_WAITING_COUNT,
lh.INT_DEAD_COUNT,
lh.INT_DEPEND_COUNT,
lh.INT_EATEN_COUNT,
lh.INT_SUCCEEDED_COUNT,
lh.INT_RUNNING_COUNT,
lh.INT_MAX_RSS,
lh.B_ARCHIVED,
lh.STR_SERVICES,
s.str_name str_show_name,
lh.dt_last_modified
from layer_history lh, job_history jh, show s
where lh.pk_job = jh.pk_job
and jh.pk_show  = s.pk_show
and jh.dt_last_modified >= (
    select dt_begin
    from history_period
)
and jh.dt_last_modified < (
    select dt_end
    from history_period
);
