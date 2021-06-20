-- Support multiple GPU

-- frame_history

ALTER TABLE frame_history ADD COLUMN int_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE frame_history ADD COLUMN int_gpu_mem_reserved BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE frame_history ADD COLUMN int_gpu_mem_max_used BIGINT DEFAULT 0 NOT NULL;


-- show_service

ALTER TABLE show_service RENAME COLUMN int_gpu_min TO int_gpu_mem_min;
ALTER TABLE show_service ALTER COLUMN int_gpu_mem_min TYPE BIGINT;
ALTER TABLE show_service ADD COLUMN int_gpus_min INT DEFAULT 0 NOT NULL;
ALTER TABLE show_service ADD COLUMN int_gpus_max INT DEFAULT 0 NOT NULL;

ALTER INDEX i_show_service_int_gpu_min RENAME TO i_show_service_int_gpu_mem_min;;
CREATE INDEX i_show_service_int_gpus_min ON show_service (int_gpus_min);


-- host_local

DROP TRIGGER verify_host_local ON host_local;
ALTER TABLE host_local ALTER COLUMN int_mem_max TYPE BIGINT;
ALTER TABLE host_local ALTER COLUMN int_mem_idle TYPE BIGINT;
ALTER TABLE host_local RENAME COLUMN int_gpu_idle TO int_gpu_mem_idle;
ALTER TABLE host_local ALTER COLUMN int_gpu_mem_idle TYPE BIGINT;
ALTER TABLE host_local RENAME COLUMN int_gpu_max TO int_gpu_mem_max;
ALTER TABLE host_local ALTER COLUMN int_gpu_mem_max TYPE BIGINT;
ALTER TABLE host_local ADD COLUMN int_gpus_idle INT DEFAULT 0 NOT NULL;
ALTER TABLE host_local ADD COLUMN int_gpus_max INT DEFAULT 0 NOT NULL;

CREATE INDEX i_host_local_int_gpus_idle ON host_local (int_gpus_idle);
CREATE INDEX i_host_local_int_gpus_max ON host_local (int_gpus_max);


-- service

ALTER TABLE service RENAME COLUMN int_gpu_min TO int_gpu_mem_min;
ALTER TABLE service ALTER COLUMN int_gpu_mem_min TYPE BIGINT;
ALTER TABLE service ADD COLUMN int_gpus_min INT DEFAULT 0 NOT NULL;
ALTER TABLE service ADD COLUMN int_gpus_max INT DEFAULT 0 NOT NULL;

ALTER INDEX i_service_int_gpu_min RENAME TO i_service_int_gpu_mem_min;
CREATE INDEX i_service_int_gpus_min ON service (int_gpus_min);


-- job_local

ALTER TABLE job_local ADD COLUMN int_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE job_local ADD COLUMN int_max_gpus INT DEFAULT 0 NOT NULL;


-- task

ALTER TABLE task ADD COLUMN int_min_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE task ADD COLUMN int_adjust_gpus INT DEFAULT 0 NOT NULL;


-- point

ALTER TABLE point ADD COLUMN int_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE point ADD COLUMN int_min_gpus INT DEFAULT 0 NOT NULL;


-- folder_resource

ALTER TABLE folder_resource ADD COLUMN int_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE folder_resource ADD COLUMN int_max_gpus INT DEFAULT -1 NOT NULL;
ALTER TABLE folder_resource ADD COLUMN int_min_gpus INT DEFAULT 0 NOT NULL;

CREATE INDEX i_folder_res_int_max_gpus ON folder_resource (int_max_gpus);


-- layer_history

ALTER TABLE layer_history ADD COLUMN int_gpus_min INT DEFAULT 0 NOT NULL;
ALTER TABLE layer_history ADD COLUMN int_gpu_time_success BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE layer_history ADD COLUMN int_gpu_time_fail BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE layer_history ADD COLUMN int_gpu_mem_min BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE layer_history ADD COLUMN int_gpu_mem_max BIGINT DEFAULT 0 NOT NULL;


-- job_history

ALTER TABLE job_history ADD COLUMN int_gpu_time_success BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE job_history ADD COLUMN int_gpu_time_fail BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE job_history ADD COLUMN int_gpu_mem_max BIGINT DEFAULT 0 NOT NULL;


-- job_usage

ALTER TABLE job_usage ADD COLUMN int_gpu_time_success BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE job_usage ADD COLUMN int_gpu_time_fail BIGINT DEFAULT 0 NOT NULL;


-- job_resource

ALTER TABLE job_resource ALTER COLUMN int_max_rss TYPE BIGINT;
ALTER TABLE job_resource ALTER COLUMN int_max_vss TYPE BIGINT;
ALTER TABLE job_resource ADD COLUMN int_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE job_resource ADD COLUMN int_min_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE job_resource ADD COLUMN int_max_gpus INT DEFAULT 100 NOT NULL;
ALTER TABLE job_resource ADD COLUMN int_local_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE job_resource ADD COLUMN int_gpu_mem_max BIGINT DEFAULT 0 NOT NULL;

CREATE INDEX i_job_resource_gpus_min_max ON job_resource (int_min_gpus, int_max_gpus);
CREATE INDEX i_job_resource_gpus ON job_resource (int_gpus);
CREATE INDEX i_job_resource_max_gpus ON job_resource (int_max_gpus);


-- subscription

ALTER TABLE subscription ADD COLUMN int_gpus INT DEFAULT 0 NOT NULL;


-- show

ALTER TABLE show ADD COLUMN int_default_min_gpus INT DEFAULT 100 NOT NULL;
ALTER TABLE show ADD COLUMN int_default_max_gpus INT DEFAULT 100000 NOT NULL;


-- proc

ALTER TABLE proc RENAME COLUMN int_gpu_reserved TO int_gpu_mem_reserved;
ALTER TABLE proc ALTER COLUMN int_gpu_mem_reserved TYPE BIGINT;
ALTER TABLE proc ADD COLUMN int_gpus_reserved INT DEFAULT 0 NOT NULL;
ALTER TABLE proc ADD COLUMN int_gpu_mem_used BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE proc ADD COLUMN int_gpu_mem_max_used BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE proc ADD COLUMN int_gpu_mem_pre_reserved BIGINT DEFAULT 0 NOT NULL;

ALTER INDEX i_proc_int_gpu_reserved RENAME TO i_proc_int_gpu_mem_reserved;


-- layer_usage

ALTER TABLE layer_usage ADD COLUMN int_gpu_time_success BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE layer_usage ADD COLUMN int_gpu_time_fail BIGINT DEFAULT 0 NOT NULL;


-- layer_mem

ALTER TABLE layer_mem ALTER COLUMN int_max_rss TYPE BIGINT;
ALTER TABLE layer_mem ALTER COLUMN int_max_vss TYPE BIGINT;
ALTER TABLE layer_mem ADD COLUMN int_gpu_mem_max BIGINT DEFAULT 0 NOT NULL;


-- layer_resource

ALTER TABLE layer_resource ALTER COLUMN int_max_rss TYPE BIGINT;
ALTER TABLE layer_resource ALTER COLUMN int_max_vss TYPE BIGINT;
ALTER TABLE layer_resource ADD COLUMN int_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE layer_resource ADD COLUMN int_gpu_mem_max BIGINT DEFAULT 0 NOT NULL;


-- layer

ALTER TABLE layer RENAME COLUMN int_gpu_min TO int_gpu_mem_min;
ALTER TABLE layer ALTER COLUMN int_gpu_mem_min TYPE BIGINT;
ALTER TABLE layer ADD COLUMN int_gpus_min BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE layer ADD COLUMN int_gpus_max BIGINT DEFAULT 0 NOT NULL;

ALTER INDEX i_layer_int_gpu_min RENAME TO i_layer_int_gpu_mem_min;
CREATE INDEX i_layer_cores_gpus_mem ON layer (int_cores_min, int_gpus_min, int_mem_min, int_gpu_mem_min);
CREATE INDEX i_layer_cores_gpus_mem_thread ON layer (int_cores_min, int_gpus_min, int_mem_min, int_gpu_mem_min, b_threadable);


-- job_mem

ALTER TABLE job_mem ALTER COLUMN int_max_rss TYPE BIGINT;
ALTER TABLE job_mem ALTER COLUMN int_max_vss TYPE BIGINT;
ALTER TABLE job_mem ADD COLUMN int_gpu_mem_max BIGINT DEFAULT 0 NOT NULL;


-- job

ALTER TABLE job ADD COLUMN int_min_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE job ADD COLUMN int_max_gpus INT DEFAULT 100000 NOT NULL;


-- host_stat

ALTER TABLE host_stat RENAME COLUMN int_gpu_total TO int_gpu_mem_total;
ALTER TABLE host_stat ALTER COLUMN int_gpu_mem_total TYPE BIGINT;
ALTER TABLE host_stat RENAME COLUMN int_gpu_free TO int_gpu_mem_free;
ALTER TABLE host_stat ALTER COLUMN int_gpu_mem_free TYPE BIGINT;

ALTER INDEX i_host_stat_int_gpu_total RENAME TO i_host_stat_int_gpu_mem_total;
ALTER INDEX i_host_stat_int_gpu_free RENAME TO i_host_stat_int_gpu_mem_free;


-- host

ALTER TABLE host RENAME COLUMN int_gpu TO int_gpu_mem;
ALTER TABLE host ALTER COLUMN int_gpu_mem TYPE BIGINT;
ALTER TABLE host RENAME COLUMN int_gpu_idle TO int_gpu_mem_idle;
ALTER TABLE host ALTER COLUMN int_gpu_mem_idle TYPE BIGINT;
ALTER TABLE host ADD COLUMN int_gpus BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE host ADD COLUMN int_gpus_idle BIGINT DEFAULT 0 NOT NULL;

CREATE INDEX i_host_int_gpu_mem ON host (int_gpu_mem);
CREATE INDEX i_host_int_gpu_mem_idle ON host (int_gpu_mem_idle);
CREATE INDEX i_host_int_gpus ON host (int_gpus);
CREATE INDEX i_host_int_gpus_idle ON host (int_gpus_idle);


-- frame

ALTER TABLE frame RENAME COLUMN int_gpu_reserved TO int_gpu_mem_reserved;
ALTER TABLE frame ALTER COLUMN int_gpu_mem_reserved TYPE BIGINT;
ALTER TABLE frame ADD COLUMN int_gpu_mem_used BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE frame ADD COLUMN int_gpu_mem_max_used BIGINT DEFAULT 0 NOT NULL;
ALTER TABLE frame ADD COLUMN int_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE frame ADD COLUMN int_total_past_gpu_time INT DEFAULT 0 NOT NULL;

ALTER INDEX i_frame_int_gpu_reserved RENAME TO i_frame_int_gpu_mem_reserved;


-- folder

ALTER TABLE folder ADD COLUMN int_job_min_gpus INT DEFAULT -1 NOT NULL;
ALTER TABLE folder ADD COLUMN int_job_max_gpus INT DEFAULT -1 NOT NULL;
ALTER TABLE folder ADD COLUMN int_min_gpus INT DEFAULT 0 NOT NULL;
ALTER TABLE folder ADD COLUMN int_max_gpus INT DEFAULT -1 NOT NULL;


-- Views

DROP VIEW vs_show_resource;
CREATE VIEW vs_show_resource (pk_show, int_cores, int_gpus) AS
  SELECT
        job.pk_show,
        SUM(int_cores) AS int_cores, SUM(int_gpus) AS int_gpus
    FROM
       job,
       job_resource
    WHERE
       job.pk_job = job_resource.pk_job
    AND
       job.str_state='PENDING'
    GROUP BY
       job.pk_show;


DROP VIEW vs_job_resource;
CREATE VIEW vs_job_resource (pk_job, int_procs, int_cores, int_gpus, int_mem_reserved) AS
  SELECT
       job.pk_job,
       COUNT(proc.pk_proc) AS int_procs,
       COALESCE(SUM(int_cores_reserved),0) AS int_cores,
       COALESCE(SUM(int_gpus_reserved),0) AS int_gpus,
       COALESCE(SUM(int_mem_reserved),0) AS int_mem_reserved
    FROM
       job LEFT JOIN proc ON (proc.pk_job = job.pk_job)
    GROUP BY
       job.pk_job;


DROP VIEW vs_alloc_usage;
CREATE VIEW vs_alloc_usage (pk_alloc, int_cores, int_idle_cores, int_running_cores, int_locked_cores, int_available_cores, int_gpus, int_idle_gpus, int_running_gpus, int_locked_gpus, int_available_gpus, int_hosts, int_locked_hosts, int_down_hosts) AS
  SELECT
        alloc.pk_alloc,
        COALESCE(SUM(host.int_cores),0) AS int_cores,
        COALESCE(SUM(host.int_cores_idle),0) AS int_idle_cores,
        COALESCE(SUM(host.int_cores - host.int_cores_idle),0) as int_running_cores,
        COALESCE((SELECT SUM(int_cores) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND (str_lock_state='NIMBY_LOCKED' OR str_lock_state='LOCKED')),0) AS int_locked_cores,
        COALESCE((SELECT SUM(int_cores_idle) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND h.str_lock_state='OPEN' AND hs.str_state ='UP'),0) AS int_available_cores,
        COALESCE(SUM(host.int_gpus),0) AS int_gpus,
        COALESCE(SUM(host.int_gpus_idle),0) AS int_idle_gpus,
        COALESCE(SUM(host.int_gpus - host.int_gpus_idle),0) as int_running_gpus,
        COALESCE((SELECT SUM(int_gpus) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND (str_lock_state='NIMBY_LOCKED' OR str_lock_state='LOCKED')),0) AS int_locked_gpus,
        COALESCE((SELECT SUM(int_gpus_idle) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND h.str_lock_state='OPEN' AND hs.str_state ='UP'),0) AS int_available_gpus,
        COUNT(host.pk_host) AS int_hosts,
        (SELECT COUNT(*) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND str_lock_state='LOCKED') AS int_locked_hosts,
        (SELECT COUNT(*) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND hs.str_state='DOWN') AS int_down_hosts
    FROM
        alloc LEFT JOIN host ON (alloc.pk_alloc = host.pk_alloc)
    GROUP BY
        alloc.pk_alloc;


DROP VIEW vs_folder_counts;
CREATE VIEW vs_folder_counts (pk_folder, int_depend_count, int_waiting_count, int_running_count, int_dead_count, int_cores, int_gpus, int_job_count) AS
  SELECT
    folder.pk_folder,
    COALESCE(SUM(int_depend_count),0) AS int_depend_count,
    COALESCE(SUM(int_waiting_count),0) AS int_waiting_count,
    COALESCE(SUM(int_running_count),0) AS int_running_count,
    COALESCE(SUM(int_dead_count),0) AS int_dead_count,
    COALESCE(SUM(int_cores),0) AS int_cores,
    COALESCE(SUM(int_gpus),0) AS int_gpus,
    COALESCE(COUNT(job.pk_job),0) AS int_job_count
FROM
    folder
      LEFT JOIN
        job ON (folder.pk_folder = job.pk_folder AND job.str_state='PENDING')
      LEFT JOIN
        job_stat ON (job.pk_job = job_stat.pk_job)
      LEFT JOIN
        job_resource ON (job.pk_job = job_resource.pk_job)
 GROUP BY
      folder.pk_folder;


DROP VIEW v_history_frame;
CREATE VIEW v_history_frame (pk_frame_history, pk_frame, pk_layer, pk_job, str_name, str_state,
    int_mem_reserved, int_mem_max_used, int_cores, int_gpu_mem_reserved, int_gpu_mem_max_used, int_gpus,
    str_host, int_exit_status, str_alloc_name,
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
    fh.INT_GPU_MEM_RESERVED,
    fh.INT_GPU_MEM_MAX_USED,
    fh.INT_GPUS,
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


DROP VIEW v_history_job;
CREATE VIEW v_history_job (pk_job, str_name, str_shot, str_user, int_core_time_success, int_core_time_fail, int_gpu_time_success, int_gpu_time_fail, int_frame_count, int_layer_count, int_waiting_count, int_dead_count, int_depend_count, int_eaten_count, int_succeeded_count, int_running_count, int_max_rss, int_gpu_mem_max, b_archived, str_facility_name, str_dept_name, int_ts_started, int_ts_stopped, str_show_name, dt_last_modified) AS
  select
jh.PK_JOB,
jh.STR_NAME,
jh.STR_SHOT,
jh.STR_USER,
jh.INT_CORE_TIME_SUCCESS,
jh.INT_CORE_TIME_FAIL,
jh.INT_GPU_TIME_SUCCESS,
jh.INT_GPU_TIME_FAIL,
jh.INT_FRAME_COUNT,
jh.INT_LAYER_COUNT,
jh.INT_WAITING_COUNT,
jh.INT_DEAD_COUNT,
jh.INT_DEPEND_COUNT,
jh.INT_EATEN_COUNT,
jh.INT_SUCCEEDED_COUNT,
jh.INT_RUNNING_COUNT,
jh.INT_MAX_RSS,
jh.INT_GPU_MEM_MAX,
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


DROP VIEW v_history_layer;
CREATE VIEW v_history_layer (pk_layer, pk_job, str_name, str_type, int_cores_min,
    int_mem_min, int_gpus_min, int_gpu_mem_min, int_core_time_success, int_core_time_fail,
    int_gpu_time_success, int_gpu_time_fail, int_frame_count, int_layer_count,
    int_waiting_count, int_dead_count, int_depend_count, int_eaten_count, int_succeeded_count,
    int_running_count, int_max_rss, int_gpu_mem_max, b_archived, str_services, str_show_name, dt_last_modified) AS
  SELECT
lh.PK_LAYER,
lh.PK_JOB,
lh.STR_NAME,
lh.STR_TYPE,
lh.INT_CORES_MIN,
lh.INT_MEM_MIN,
lh.INT_GPUS_MIN,
lh.INT_GPU_MEM_MIN,
lh.INT_CORE_TIME_SUCCESS,
lh.INT_CORE_TIME_FAIL,
lh.INT_GPU_TIME_SUCCESS,
lh.INT_GPU_TIME_FAIL,
lh.INT_FRAME_COUNT,
lh.INT_LAYER_COUNT,
lh.INT_WAITING_COUNT,
lh.INT_DEAD_COUNT,
lh.INT_DEPEND_COUNT,
lh.INT_EATEN_COUNT,
lh.INT_SUCCEEDED_COUNT,
lh.INT_RUNNING_COUNT,
lh.INT_MAX_RSS,
lh.INT_GPU_MEM_MAX,
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


-- Types

ALTER TYPE JobStatType ADD ATTRIBUTE int_gpu_time_success BIGINT;
ALTER TYPE JobStatType ADD ATTRIBUTE int_gpu_time_fail BIGINT;
ALTER TYPE JobStatType ADD ATTRIBUTE int_gpu_mem_max BIGINT;

ALTER TYPE LayerStatType ADD ATTRIBUTE int_gpu_time_success BIGINT;
ALTER TYPE LayerStatType ADD ATTRIBUTE int_gpu_time_fail BIGINT;
ALTER TYPE LayerStatType ADD ATTRIBUTE int_gpu_mem_max BIGINT;


-- Functions

CREATE OR REPLACE FUNCTION recalculate_subs()
RETURNS VOID AS $body$
DECLARE
    r RECORD;
BEGIN
  --
  -- concatenates all tags in host_tag and sets host.str_tags
  --
  UPDATE subscription SET int_cores = 0;
  UPDATE subscription SET int_gpus = 0;
  FOR r IN
    SELECT proc.pk_show, alloc.pk_alloc, sum(proc.int_cores_reserved) as c, sum(proc.int_gpus_reserved) as d
    FROM proc, host, alloc
    WHERE proc.pk_host = host.pk_host AND host.pk_alloc = alloc.pk_alloc
    GROUP BY proc.pk_show, alloc.pk_alloc
  LOOP
    UPDATE subscription SET int_cores = r.c, int_gpus = r.d WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;

  END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION tmp_populate_folder()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT pk_folder, pk_show, sum(int_cores) AS c, sum(int_gpus) AS d
        FROM job, job_resource
        WHERE job.pk_job = job_resource.pk_job
        GROUP by pk_folder, pk_show
    LOOP
        UPDATE folder_resource SET int_cores = t.c, int_gpus = t.d WHERE pk_folder = t.pk_folder;
        COMMIT;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION tmp_populate_point()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT pk_dept, pk_show, sum(int_cores) AS c, sum(int_gpus) AS d
        FROM job, job_resource
        WHERE job.pk_job = job_resource.pk_job
        GROUP BY pk_dept, pk_show
    LOOP
        UPDATE point SET int_cores = t.c , int_gpus = t.d WHERE pk_show = t.pk_show AND pk_dept = t.pk_dept;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION tmp_populate_sub()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT proc.pk_show, host.pk_alloc, sum(int_cores_reserved) AS c, sum(int_gpus_reserved) AS d
        FROM proc, host
        WHERE proc.pk_host = host.pk_host
        GROUP BY proc.pk_show, host.pk_alloc
    LOOP
        UPDATE subscription SET int_cores = t.c, int_gpus = t.d WHERE pk_show = t.pk_show AND pk_alloc = t.pk_alloc;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__after_job_moved()
RETURNS TRIGGER AS $body$
DECLARE
    int_core_count INT;
    int_gpu_count INT;
BEGIN
    SELECT int_cores, int_gpus INTO int_core_count, int_gpu_count
    FROM job_resource WHERE pk_job = NEW.pk_job;

    IF int_core_count > 0 THEN
        UPDATE folder_resource SET int_cores = int_cores + int_core_count
        WHERE pk_folder = NEW.pk_folder;

        UPDATE folder_resource  SET int_cores = int_cores - int_core_count
        WHERE pk_folder = OLD.pk_folder;
    END IF;

    IF int_gpu_count > 0 THEN
        UPDATE folder_resource SET int_gpus = int_gpus + int_gpu_count
        WHERE pk_folder = NEW.pk_folder;

        UPDATE folder_resource  SET int_gpus = int_gpus - int_gpu_count
        WHERE pk_folder = OLD.pk_folder;
    END IF;
    RETURN NULL;
END
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__before_delete_job()
RETURNS TRIGGER AS $body$
DECLARE
    js JobStatType;
BEGIN
    SELECT
        job_usage.int_core_time_success,
        job_usage.int_core_time_fail,
        job_usage.int_gpu_time_success,
        job_usage.int_gpu_time_fail,
        job_stat.int_waiting_count,
        job_stat.int_dead_count,
        job_stat.int_depend_count,
        job_stat.int_eaten_count,
        job_stat.int_succeeded_count,
        job_stat.int_running_count,
        job_mem.int_max_rss,
        job_mem.int_gpu_mem_max
    INTO
        js
    FROM
        job_mem,
        job_usage,
        job_stat
    WHERE
        job_usage.pk_job = job_mem.pk_job
    AND
        job_stat.pk_job = job_mem.pk_job
    AND
        job_mem.pk_job = OLD.pk_job;

    UPDATE
        job_history
    SET
        pk_dept = OLD.pk_dept,
        int_core_time_success = js.int_core_time_success,
        int_core_time_fail = js.int_core_time_fail,
        int_gpu_time_success = js.int_gpu_time_success,
        int_gpu_time_fail = js.int_gpu_time_fail,
        int_frame_count = OLD.int_frame_count,
        int_layer_count = OLD.int_layer_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        int_gpu_mem_max = js.int_gpu_mem_max,
        b_archived = true,
        int_ts_stopped = COALESCE(epoch(OLD.ts_stopped), epoch(current_timestamp))
    WHERE
        pk_job = OLD.pk_job;

    DELETE FROM depend WHERE pk_job_depend_on=OLD.pk_job OR pk_job_depend_er=OLD.pk_job;
    DELETE FROM frame WHERE pk_job=OLD.pk_job;
    DELETE FROM layer WHERE pk_job=OLD.pk_job;
    DELETE FROM job_env WHERE pk_job=OLD.pk_job;
    DELETE FROM job_stat WHERE pk_job=OLD.pk_job;
    DELETE FROM job_resource WHERE pk_job=OLD.pk_job;
    DELETE FROM job_usage WHERE pk_job=OLD.pk_job;
    DELETE FROM job_mem WHERE pk_job=OLD.pk_job;
    DELETE FROM comments WHERE pk_job=OLD.pk_job;

    RETURN OLD;
END
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__after_job_finished()
RETURNS TRIGGER AS $body$
DECLARE
    ts INT := cast(epoch(current_timestamp) as integer);
    js JobStatType;
    ls LayerStatType;
    one_layer RECORD;
BEGIN
    SELECT
        job_usage.int_core_time_success,
        job_usage.int_core_time_fail,
        job_usage.int_gpu_time_success,
        job_usage.int_gpu_time_fail,
        job_stat.int_waiting_count,
        job_stat.int_dead_count,
        job_stat.int_depend_count,
        job_stat.int_eaten_count,
        job_stat.int_succeeded_count,
        job_stat.int_running_count,
        job_mem.int_max_rss,
        job_mem.int_gpu_mem_max
    INTO
        js
    FROM
        job_mem,
        job_usage,
        job_stat
    WHERE
        job_usage.pk_job = job_mem.pk_job
    AND
        job_stat.pk_job = job_mem.pk_job
    AND
        job_mem.pk_job = NEW.pk_job;

    UPDATE
        job_history
    SET
        pk_dept = NEW.pk_dept,
        int_core_time_success = js.int_core_time_success,
        int_core_time_fail = js.int_core_time_fail,
        int_gpu_time_success = js.int_gpu_time_success,
        int_gpu_time_fail = js.int_gpu_time_fail,
        int_frame_count = NEW.int_frame_count,
        int_layer_count = NEW.int_layer_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        int_gpu_mem_max = js.int_gpu_mem_max,
        int_ts_stopped = ts
    WHERE
        pk_job = NEW.pk_job;

    FOR one_layer IN (SELECT pk_layer from layer where pk_job = NEW.pk_job)
    LOOP
        SELECT
            layer_usage.int_core_time_success,
            layer_usage.int_core_time_fail,
            layer_usage.int_gpu_time_success,
            layer_usage.int_gpu_time_fail,
            layer_stat.int_total_count,
            layer_stat.int_waiting_count,
            layer_stat.int_dead_count,
            layer_stat.int_depend_count,
            layer_stat.int_eaten_count,
            layer_stat.int_succeeded_count,
            layer_stat.int_running_count,
            layer_mem.int_max_rss,
            layer_mem.int_gpu_mem_max
        INTO
            ls
        FROM
            layer_mem,
            layer_usage,
            layer_stat
        WHERE
            layer_usage.pk_layer = layer_mem.pk_layer
        AND
            layer_stat.pk_layer = layer_mem.pk_layer
        AND
            layer_mem.pk_layer = one_layer.pk_layer;

        UPDATE
            layer_history
        SET
            int_core_time_success = ls.int_core_time_success,
            int_core_time_fail = ls.int_core_time_fail,
            int_gpu_time_success = ls.int_gpu_time_success,
            int_gpu_time_fail = ls.int_gpu_time_fail,
            int_frame_count = ls.int_total_count,
            int_waiting_count = ls.int_waiting_count,
            int_dead_count = ls.int_dead_count,
            int_depend_count = ls.int_depend_count,
            int_eaten_count = ls.int_eaten_count,
            int_succeeded_count = ls.int_succeeded_count,
            int_running_count = ls.int_running_count,
            int_max_rss = ls.int_max_rss,
            int_gpu_mem_max = ls.int_gpu_mem_max
        WHERE
            pk_layer = one_layer.pk_layer;
    END LOOP;

    /**
     * Delete any local core assignments from this job.
     **/
    DELETE FROM job_local WHERE pk_job=NEW.pk_job;

    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__after_job_dept_update()
RETURNS TRIGGER AS $body$
DECLARE
    int_running_cores INT;
    int_running_gpus INT;
BEGIN
  /**
  * Handles the accounting for moving a job between departments.
  **/
  SELECT int_cores, int_gpus INTO int_running_cores, int_running_gpus
    FROM job_resource WHERE pk_job = NEW.pk_job;

  IF int_running_cores > 0 THEN
    UPDATE point SET int_cores = int_cores + int_running_cores
        WHERE pk_dept = NEW.pk_dept AND pk_show = NEW.pk_show;

    UPDATE point SET int_cores = int_cores - int_running_cores
        WHERE pk_dept = OLD.pk_dept AND pk_show = OLD.pk_show;
  END IF;

  IF int_running_gpus > 0 THEN
    UPDATE point SET int_gpus = int_gpus + int_running_gpus
        WHERE pk_dept = NEW.pk_dept AND pk_show = NEW.pk_show;

    UPDATE point SET int_gpus = int_gpus - int_running_gpus
        WHERE pk_dept = OLD.pk_dept AND pk_show = OLD.pk_show;
  END IF;

  RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__verify_host_local()
RETURNS TRIGGER AS $body$
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * when people lower the max.
    **/
    IF NEW.int_cores_idle < 0 THEN
        RAISE EXCEPTION 'host local doesnt have enough idle cores.';
    END IF;

    IF NEW.int_mem_idle < 0 THEN
        RAISE EXCEPTION 'host local doesnt have enough idle memory';
    END IF;

    IF NEW.int_gpus_idle < 0 THEN
        RAISE EXCEPTION 'host local doesnt have enough GPU idle cores.';
    END IF;

    IF NEW.int_gpu_mem_idle < 0 THEN
        RAISE EXCEPTION 'host local doesnt have enough GPU idle memory.';
    END IF;

    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER verify_host_local BEFORE UPDATE ON host_local
FOR EACH ROW
   WHEN ((NEW.int_cores_max = OLD.int_cores_max AND NEW.int_mem_max = OLD.int_mem_max) AND
    (NEW.int_cores_idle != OLD.int_cores_idle OR NEW.int_mem_idle != OLD.int_mem_idle) AND
    (NEW.int_gpus_max = OLD.int_gpus_max AND NEW.int_gpu_mem_max = OLD.int_gpu_mem_max) AND
    (NEW.int_gpus_idle != OLD.int_gpus_idle OR NEW.int_gpu_mem_idle != OLD.int_gpu_mem_idle))
   EXECUTE PROCEDURE trigger__verify_host_local();


CREATE OR REPLACE FUNCTION trigger__after_insert_layer()
RETURNS TRIGGER AS $body$
BEGIN
    INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_usage (pk_layer_usage, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_mem (pk_layer_mem, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);

    INSERT INTO layer_history
        (pk_layer, pk_job, str_name, str_type, int_cores_min, int_mem_min, int_gpus_min, int_gpu_mem_min, b_archived,str_services)
    VALUES
        (NEW.pk_layer, NEW.pk_job, NEW.str_name, NEW.str_type, NEW.int_cores_min, NEW.int_mem_min, NEW.int_gpus_min, NEW.int_gpu_mem_min, false, NEW.str_services);

    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__before_delete_layer()
RETURNS TRIGGER AS $body$
DECLARE
    js LayerStatType;
BEGIN
    SELECT
        layer_usage.int_core_time_success,
        layer_usage.int_core_time_fail,
        layer_usage.int_gpu_time_success,
        layer_usage.int_gpu_time_fail,
        layer_stat.int_total_count,
        layer_stat.int_waiting_count,
        layer_stat.int_dead_count,
        layer_stat.int_depend_count,
        layer_stat.int_eaten_count,
        layer_stat.int_succeeded_count,
        layer_stat.int_running_count,
        layer_mem.int_max_rss,
        layer_mem.int_gpu_mem_max
    INTO
        js
    FROM
        layer_mem,
        layer_usage,
        layer_stat
    WHERE
        layer_usage.pk_layer = layer_mem.pk_layer
    AND
        layer_stat.pk_layer = layer_mem.pk_layer
    AND
        layer_mem.pk_layer = OLD.pk_layer;

    UPDATE
        layer_history
    SET
        int_core_time_success = js.int_core_time_success,
        int_core_time_fail = js.int_core_time_fail,
        int_gpu_time_success = js.int_gpu_time_success,
        int_gpu_time_fail = js.int_gpu_time_fail,
        int_frame_count = js.int_total_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        int_gpu_mem_max = js.int_gpu_mem_max,
        b_archived = true
    WHERE
        pk_layer = OLD.pk_layer;

    DELETE FROM layer_resource where pk_layer=OLD.pk_layer;
    DELETE FROM layer_stat where pk_layer=OLD.pk_layer;
    DELETE FROM layer_usage where pk_layer=OLD.pk_layer;
    DELETE FROM layer_env where pk_layer=OLD.pk_layer;
    DELETE FROM layer_mem where pk_layer=OLD.pk_layer;
    DELETE FROM layer_output where pk_layer=OLD.pk_layer;

    RETURN OLD;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__verify_host_resources()
RETURNS TRIGGER AS $body$
BEGIN
    IF NEW.int_cores_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional core units';
    END IF;

    If NEW.int_mem_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional memory';
    END IF;

    If NEW.int_gpus_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional GPU units';
    END IF;

    If NEW.int_gpu_mem_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional GPU memory';
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

DROP TRIGGER verify_host_resources ON host;
CREATE TRIGGER verify_host_resources BEFORE UPDATE ON host
FOR EACH ROW
   WHEN (NEW.int_cores_idle != OLD.int_cores_idle
        OR NEW.int_mem_idle != OLD.int_mem_idle
        OR NEW.int_gpus_idle != OLD.int_gpus_idle
        OR NEW.int_gpu_mem_idle != OLD.int_gpu_mem_idle)
   EXECUTE PROCEDURE trigger__verify_host_resources();


CREATE OR REPLACE FUNCTION trigger__verify_job_resources()
RETURNS TRIGGER AS $body$
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * at the wrong time.
    **/
    IF NEW.int_cores > NEW.int_max_cores THEN
        RAISE EXCEPTION 'job has exceeded max cores';
    END IF;
    IF NEW.int_gpus > NEW.int_max_gpus THEN
        RAISE EXCEPTION 'job has exceeded max GPU units';
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

DROP TRIGGER verify_job_resources ON job_resource;
CREATE TRIGGER verify_job_resources BEFORE UPDATE ON job_resource
FOR EACH ROW
  WHEN (NEW.int_max_cores = OLD.int_max_cores AND NEW.int_cores > OLD.int_cores OR
        NEW.int_max_gpus = OLD.int_max_gpus AND NEW.int_gpus > OLD.int_gpus)
  EXECUTE PROCEDURE trigger__verify_job_resources();


CREATE OR REPLACE FUNCTION trigger__update_proc_update_layer()
RETURNS TRIGGER AS $body$
DECLARE
    lr RECORD;
BEGIN
     FOR lr IN (
        SELECT
          pk_layer
        FROM
          layer_stat
        WHERE
          pk_layer IN (OLD.pk_layer, NEW.pk_layer)
        ORDER BY layer_stat.pk_layer DESC
        ) LOOP

      IF lr.pk_layer = OLD.pk_layer THEN

        UPDATE layer_resource SET
          int_cores = int_cores - OLD.int_cores_reserved,
          int_gpus = int_gpus - OLD.int_gpus_reserved
        WHERE
          pk_layer = OLD.pk_layer;

      ELSE

        UPDATE layer_resource SET
          int_cores = int_cores + NEW.int_cores_reserved,
          int_gpus = int_gpus + NEW.int_gpus_reserved
       WHERE
          pk_layer = NEW.pk_layer;
       END IF;

    END LOOP;
    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__frame_history_open()
RETURNS TRIGGER AS $body$
DECLARE
  str_pk_alloc VARCHAR(36) := null;
  int_checkpoint INT := 0;
BEGIN

    IF OLD.str_state = 'RUNNING' THEN

        IF NEW.int_exit_status = 299 THEN

          EXECUTE 'DELETE FROM frame_history WHERE int_ts_stopped = 0 AND pk_frame=$1' USING
            NEW.pk_frame;

        ELSE
          If NEW.str_state = 'CHECKPOINT' THEN
              int_checkpoint := 1;
          END IF;

          EXECUTE
          'UPDATE
              frame_history
          SET
              int_mem_max_used=$1,
              int_gpu_mem_max_used=$2,
              int_ts_stopped=$3,
              int_exit_status=$4,
              int_checkpoint_count=$5
          WHERE
              int_ts_stopped = 0 AND pk_frame=$6'
          USING
              NEW.int_mem_max_used,
              NEW.int_gpu_mem_max_used,
              epoch(current_timestamp),
              NEW.int_exit_status,
              int_checkpoint,
              NEW.pk_frame;
        END IF;
    END IF;

    IF NEW.str_state = 'RUNNING' THEN

      SELECT pk_alloc INTO str_pk_alloc FROM host WHERE str_name=NEW.str_host;

      EXECUTE
        'INSERT INTO
            frame_history
        (
            pk_frame,
            pk_layer,
            pk_job,
            str_name,
            str_state,
            int_cores,
            int_mem_reserved,
            int_gpus,
            int_gpu_mem_reserved,
            str_host,
            int_ts_started,
            pk_alloc
         )
         VALUES
            ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)'
         USING NEW.pk_frame,
            NEW.pk_layer,
            NEW.pk_job,
            NEW.str_name,
            'RUNNING',
            NEW.int_cores,
            NEW.int_mem_reserved,
            NEW.int_gpus,
            NEW.int_gpu_mem_reserved,
            NEW.str_host,
            epoch(current_timestamp),
            str_pk_alloc;
    END IF;
    RETURN NULL;

END;
$body$
LANGUAGE PLPGSQL;
