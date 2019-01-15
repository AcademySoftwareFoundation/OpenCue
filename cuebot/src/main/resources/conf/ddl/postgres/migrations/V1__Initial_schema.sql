
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE history_period_bak (
    pk VARCHAR(32),
    dt_begin DATE NOT NULL,
    dt_end DATE NOT NULL
);

CREATE TABLE frame_history (
    pk_frame_history VARCHAR(36) DEFAULT uuid_generate_v1() NOT NULL,
    pk_frame VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    str_name VARCHAR(256) NOT NULL,
    str_state VARCHAR(24) NOT NULL,
    int_mem_reserved BIGINT DEFAULT 0 NOT NULL,
    int_mem_max_used BIGINT DEFAULT 0 NOT NULL,
    int_cores INT DEFAULT 100 NOT NULL,
    str_host VARCHAR(64) DEFAULT NULL,
    int_exit_status SMALLINT DEFAULT -1 NOT NULL,
    pk_alloc VARCHAR(36),
    int_ts_started INT NOT NULL,
    int_ts_stopped INT DEFAULT 0 NOT NULL,
    int_checkpoint_count INT DEFAULT 0 NOT NULL,
    dt_last_modified DATE NOT NULL
);

CREATE TABLE history_period (
    pk VARCHAR(36) DEFAULT uuid_generate_v1(),
    dt_begin DATE DEFAULT to_date('01-JAN-2000','DD-MON-YYYY') NOT NULL,
    dt_end DATE DEFAULT current_timestamp NOT NULL
);

CREATE TABLE duplicate_cursors (
    dt_recorded DATE,
    inst_id NUMERIC,
    lng_count NUMERIC
);

CREATE TABLE uncommitted_transactions_bak (
    inst_id NUMERIC,
    sid NUMERIC,
    serial NUMERIC,
    username VARCHAR(30),
    machine VARCHAR(64),
    module VARCHAR(48),
    service_name VARCHAR(64),
    duration NUMERIC,
    dt_recorded DATE
);

CREATE TABLE uncommitted_transactions (
    inst_id NUMERIC,
    sid NUMERIC,
    serial NUMERIC,
    username VARCHAR(30),
    machine VARCHAR(64),
    module VARCHAR(48),
    service_name VARCHAR(64),
    duration NUMERIC,
    dt_recorded DATE DEFAULT current_timestamp
);

CREATE TABLE layer_output (
    pk_layer_output VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    str_filespec VARCHAR(2048) NOT NULL
);

CREATE TABLE show_service (
    pk_show_service VARCHAR(36) NOT NULL,
    pk_show VARCHAR(36) NOT NULL,
    str_name VARCHAR(36) NOT NULL,
    b_threadable BOOLEAN NOT NULL,
    int_cores_min INT NOT NULL,
    int_mem_min INT NOT NULL,
    str_tags VARCHAR(128) NOT NULL,
    int_cores_max INT DEFAULT 0 NOT NULL,
    int_gpu_min INT DEFAULT 0 NOT NULL
);

CREATE TABLE deed (
    pk_deed VARCHAR(36) NOT NULL,
    pk_owner VARCHAR(36) NOT NULL,
    pk_host VARCHAR(36) NOT NULL,
    b_blackout BOOLEAN DEFAULT false NOT NULL,
    int_blackout_start INT,
    int_blackout_stop INT
);

CREATE TABLE owner (
    pk_owner VARCHAR(36) NOT NULL,
    pk_show VARCHAR(36) NOT NULL,
    str_username VARCHAR(64) NOT NULL,
    ts_created TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    ts_updated TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL
);

CREATE TABLE host_local (
    pk_host_local VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36),
    pk_frame VARCHAR(36),
    pk_host VARCHAR(36) NOT NULL,
    ts_created TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    ts_updated TIMESTAMP (6) WITH TIME ZONE,
    int_mem_max INT DEFAULT 0 NOT NULL,
    int_mem_idle INT DEFAULT 0 NOT NULL,
    int_cores_max INT DEFAULT 100 NOT NULL,
    int_cores_idle INT DEFAULT 100 NOT NULL,
    int_threads INT DEFAULT 1 NOT NULL,
    float_tier NUMERIC(16,2) DEFAULT 0 NOT NULL,
    b_active BOOLEAN DEFAULT true NOT NULL,
    str_type VARCHAR(36) NOT NULL,
    int_gpu_idle INT DEFAULT 0 NOT NULL,
    int_gpu_max INT DEFAULT 0 NOT NULL
);

CREATE TABLE service (
    pk_service VARCHAR(36) NOT NULL,
    str_name VARCHAR(36) NOT NULL,
    b_threadable BOOLEAN NOT NULL,
    int_cores_min INT NOT NULL,
    int_mem_min INT NOT NULL,
    str_tags VARCHAR(128) NOT NULL,
    int_cores_max INT DEFAULT 0 NOT NULL,
    int_gpu_min INT DEFAULT 0 NOT NULL
);

CREATE TABLE job_local (
    pk_job_local VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    pk_host VARCHAR(36) NOT NULL,
    str_source VARCHAR(255) NOT NULL,
    ts_created TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    int_cores INT DEFAULT 0 NOT NULL,
    int_max_cores INT NOT NULL
);

CREATE TABLE task (
    pk_task VARCHAR(36) NOT NULL,
    pk_point VARCHAR(36) NOT NULL,
    str_shot VARCHAR(36) NOT NULL,
    int_min_cores INT DEFAULT 100 NOT NULL,
    int_adjust_cores INT DEFAULT 0 NOT NULL
);

CREATE TABLE point (
    pk_point VARCHAR(36) NOT NULL,
    pk_dept VARCHAR(36) NOT NULL,
    pk_show VARCHAR(36) NOT NULL,
    str_ti_task VARCHAR(36),
    int_cores INT DEFAULT 0 NOT NULL,
    b_managed BOOLEAN DEFAULT false NOT NULL,
    int_min_cores INT DEFAULT 0 NOT NULL,
    float_tier NUMERIC(16,2) DEFAULT 0 NOT NULL,
    ts_updated TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL
);

CREATE TABLE layer_mem (
    pk_layer_mem VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    int_max_rss INT DEFAULT 0 NOT NULL,
    int_max_vss INT DEFAULT 0 NOT NULL
);

CREATE TABLE job_mem (
    pk_job_mem VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    int_max_rss INT DEFAULT 0 NOT NULL,
    int_max_vss INT DEFAULT 0 NOT NULL
);

CREATE TABLE folder_resource (
    pk_folder_resource VARCHAR(36) NOT NULL,
    pk_folder VARCHAR(36) NOT NULL,
    int_cores INT DEFAULT 0 NOT NULL,
    int_max_cores INT DEFAULT -1 NOT NULL,
    int_min_cores INT DEFAULT 0 NOT NULL,
    float_tier NUMERIC(16,2) DEFAULT 0 NOT NULL
);

CREATE TABLE show_alias (
    pk_show_alias VARCHAR(36) NOT NULL,
    pk_show VARCHAR(36) NOT NULL,
    str_name VARCHAR(16) NOT NULL
);

CREATE TABLE dept (
    pk_dept VARCHAR(36) NOT NULL,
    str_name VARCHAR(36) NOT NULL,
    b_default BOOLEAN DEFAULT false NOT NULL
);

CREATE TABLE facility (
    pk_facility VARCHAR(36) NOT NULL,
    str_name VARCHAR(36) NOT NULL,
    b_default BOOLEAN DEFAULT false NOT NULL
);

CREATE TABLE job_post (
    pk_job_post VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    pk_post_job VARCHAR(36) NOT NULL
);

CREATE TABLE layer_history (
    pk_layer VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    str_name VARCHAR(512) NOT NULL,
    str_type VARCHAR(16) NOT NULL,
    int_cores_min BIGINT DEFAULT 100 NOT NULL,
    int_mem_min BIGINT DEFAULT 4194304 NOT NULL,
    int_core_time_success BIGINT DEFAULT 0 NOT NULL,
    int_core_time_fail BIGINT DEFAULT 0 NOT NULL,
    int_frame_count BIGINT DEFAULT 0 NOT NULL,
    int_layer_count BIGINT DEFAULT 0 NOT NULL,
    int_waiting_count BIGINT DEFAULT 0 NOT NULL,
    int_dead_count BIGINT DEFAULT 0 NOT NULL,
    int_depend_count BIGINT DEFAULT 0 NOT NULL,
    int_eaten_count BIGINT DEFAULT 0 NOT NULL,
    int_succeeded_count BIGINT DEFAULT 0 NOT NULL,
    int_running_count BIGINT DEFAULT 0 NOT NULL,
    int_max_rss BIGINT DEFAULT 0 NOT NULL,
    b_archived BOOLEAN DEFAULT false NOT NULL,
    dt_last_modified DATE NOT NULL,
    str_services VARCHAR(128)
);

CREATE TABLE job_history (
    pk_job VARCHAR(36) NOT NULL,
    pk_show VARCHAR(36) NOT NULL,
    str_name VARCHAR(512) NOT NULL,
    str_shot VARCHAR(64) NOT NULL,
    str_user VARCHAR(36) NOT NULL,
    int_core_time_success BIGINT DEFAULT 0 NOT NULL,
    int_core_time_fail BIGINT DEFAULT 0 NOT NULL,
    int_frame_count BIGINT DEFAULT 0 NOT NULL,
    int_layer_count BIGINT DEFAULT 0 NOT NULL,
    int_waiting_count BIGINT DEFAULT 0 NOT NULL,
    int_dead_count BIGINT DEFAULT 0 NOT NULL,
    int_depend_count BIGINT DEFAULT 0 NOT NULL,
    int_eaten_count BIGINT DEFAULT 0 NOT NULL,
    int_succeeded_count BIGINT DEFAULT 0 NOT NULL,
    int_running_count BIGINT DEFAULT 0 NOT NULL,
    int_max_rss BIGINT DEFAULT 0 NOT NULL,
    b_archived BOOLEAN DEFAULT false NOT NULL,
    pk_facility VARCHAR(36) NOT NULL,
    pk_dept VARCHAR(36) NOT NULL,
    int_ts_started INT NOT NULL,
    int_ts_stopped INT DEFAULT 0 NOT NULL,
    dt_last_modified DATE NOT NULL
);

CREATE TABLE task_lock (
    pk_task_lock VARCHAR(36) NOT NULL,
    str_name VARCHAR(36) NOT NULL,
    int_lock BIGINT DEFAULT 0 NOT NULL,
    int_timeout BIGINT DEFAULT 30 NOT NULL,
    ts_lastrun TIMESTAMP (6) DEFAULT current_timestamp NOT NULL
);

CREATE TABLE host_tag (
    pk_host_tag VARCHAR(36) NOT NULL,
    pk_host VARCHAR(36) NOT NULL,
    str_tag VARCHAR(36) NOT NULL,
    str_tag_type VARCHAR(24) DEFAULT 'Hardware' NOT NULL,
    b_constant BOOLEAN DEFAULT false NOT NULL
);

CREATE TABLE job_usage (
    pk_job_usage VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    int_core_time_success BIGINT DEFAULT 0 NOT NULL,
    int_core_time_fail BIGINT DEFAULT 0 NOT NULL,
    int_frame_success_count INT DEFAULT 0 NOT NULL,
    int_frame_fail_count INT DEFAULT 0 NOT NULL,
    int_clock_time_fail INT DEFAULT 0 NOT NULL,
    int_clock_time_high INT DEFAULT 0 NOT NULL,
    int_clock_time_success INT DEFAULT 0 NOT NULL
);

CREATE TABLE job_resource (
    pk_job_resource VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    int_cores BIGINT DEFAULT 0 NOT NULL,
    int_max_rss INT DEFAULT 0 NOT NULL,
    int_max_vss INT DEFAULT 0 NOT NULL,
    int_min_cores INT DEFAULT 100 NOT NULL,
    int_max_cores INT DEFAULT 10000 NOT NULL,
    float_tier NUMERIC(16,2) DEFAULT 0 NOT NULL,
    int_priority INT DEFAULT 1 NOT NULL,
    int_local_cores INT DEFAULT 0 NOT NULL
);

CREATE TABLE job_stat (
    pk_job_stat VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    int_waiting_count BIGINT DEFAULT 0 NOT NULL,
    int_running_count BIGINT DEFAULT 0 NOT NULL,
    int_dead_count BIGINT DEFAULT 0 NOT NULL,
    int_depend_count BIGINT DEFAULT 0 NOT NULL,
    int_eaten_count BIGINT DEFAULT 0 NOT NULL,
    int_succeeded_count BIGINT DEFAULT 0 NOT NULL,
    int_checkpoint_count BIGINT DEFAULT 0 NOT NULL
);

CREATE TABLE subscription (
    pk_subscription VARCHAR(36) NOT NULL,
    pk_alloc VARCHAR(36) NOT NULL,
    pk_show VARCHAR(36) NOT NULL,
    int_size BIGINT DEFAULT 0 NOT NULL,
    int_burst BIGINT DEFAULT 0 NOT NULL,
    int_cores INT DEFAULT 0 NOT NULL,
    float_tier NUMERIC(16,2) DEFAULT 0 NOT NULL
);

CREATE TABLE show (
    pk_show VARCHAR(36) NOT NULL,
    str_name VARCHAR(36) NOT NULL,
    b_paused BOOLEAN DEFAULT false NOT NULL,
    int_default_min_cores INT DEFAULT 100 NOT NULL,
    int_default_max_cores INT DEFAULT 10000 NOT NULL,
    int_frame_insert_count BIGINT DEFAULT 0 NOT NULL,
    int_job_insert_count BIGINT DEFAULT 0 NOT NULL,
    int_frame_success_count BIGINT DEFAULT 0 NOT NULL,
    int_frame_fail_count BIGINT DEFAULT 0 NOT NULL,
    b_booking_enabled BOOLEAN DEFAULT true NOT NULL,
    b_dispatch_enabled BOOLEAN DEFAULT true NOT NULL,
    b_active BOOLEAN DEFAULT true NOT NULL,
    str_comment_email VARCHAR(1024)
);

CREATE TABLE proc (
    pk_proc VARCHAR(36) NOT NULL,
    pk_host VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36),
    pk_show VARCHAR(36),
    pk_layer VARCHAR(36),
    pk_frame VARCHAR(36),
    int_cores_reserved BIGINT NOT NULL,
    int_mem_reserved BIGINT NOT NULL,
    int_mem_used BIGINT DEFAULT 0 NOT NULL,
    int_mem_max_used BIGINT DEFAULT 0 NOT NULL,
    b_unbooked BOOLEAN DEFAULT false NOT NULL,
    int_mem_pre_reserved BIGINT DEFAULT 0 NOT NULL,
    int_virt_used INT DEFAULT 0 NOT NULL,
    int_virt_max_used INT DEFAULT 0 NOT NULL,
    str_redirect VARCHAR(265),
    b_local BOOLEAN DEFAULT false NOT NULL,
    ts_ping TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    ts_booked TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    ts_dispatched TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    int_gpu_reserved INT DEFAULT 0 NOT NULL
);

CREATE TABLE matcher (
    pk_matcher VARCHAR(36) NOT NULL,
    pk_filter VARCHAR(36) NOT NULL,
    str_subject VARCHAR(64) NOT NULL,
    str_match VARCHAR(64) NOT NULL,
    str_value VARCHAR(4000) NOT NULL,
    ts_created TIMESTAMP (6) DEFAULT current_timestamp NOT NULL
);

CREATE TABLE layer_usage (
    pk_layer_usage VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    int_core_time_success BIGINT DEFAULT 0 NOT NULL,
    int_core_time_fail BIGINT DEFAULT 0 NOT NULL,
    int_frame_success_count INT DEFAULT 0 NOT NULL,
    int_frame_fail_count INT DEFAULT 0 NOT NULL,
    int_clock_time_fail INT DEFAULT 0 NOT NULL,
    int_clock_time_high INT DEFAULT 0 NOT NULL,
    int_clock_time_low INT DEFAULT 0 NOT NULL,
    int_clock_time_success INT DEFAULT 0 NOT NULL
);

CREATE TABLE layer_stat (
    pk_layer_stat VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    int_total_count BIGINT DEFAULT 0 NOT NULL,
    int_waiting_count BIGINT DEFAULT 0 NOT NULL,
    int_running_count BIGINT DEFAULT 0 NOT NULL,
    int_dead_count BIGINT DEFAULT 0 NOT NULL,
    int_depend_count BIGINT DEFAULT 0 NOT NULL,
    int_eaten_count BIGINT DEFAULT 0 NOT NULL,
    int_succeeded_count BIGINT DEFAULT 0 NOT NULL,
    int_checkpoint_count BIGINT DEFAULT 0 NOT NULL
);

CREATE TABLE layer_resource (
    pk_layer_resource VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    int_cores BIGINT DEFAULT 0 NOT NULL,
    int_max_rss INT DEFAULT 0 NOT NULL,
    int_max_vss INT DEFAULT 0 NOT NULL
);

CREATE TABLE layer_env (
    pk_layer_env VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36),
    pk_job VARCHAR(36),
    str_key VARCHAR(36),
    str_value VARCHAR(2048)
);

CREATE TABLE layer (
    pk_layer VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    str_name VARCHAR(256) NOT NULL,
    str_cmd VARCHAR(4000) NOT NULL,
    str_range VARCHAR(4000) NOT NULL,
    int_chunk_size BIGINT DEFAULT 1 NOT NULL,
    int_dispatch_order BIGINT DEFAULT 1 NOT NULL,
    int_cores_min BIGINT DEFAULT 100 NOT NULL,
    int_mem_min BIGINT DEFAULT 4194304 NOT NULL,
    str_tags VARCHAR(4000) DEFAULT '' NOT NULL,
    str_type VARCHAR(16) NOT NULL,
    b_threadable BOOLEAN DEFAULT true NOT NULL,
    str_services VARCHAR(128) DEFAULT 'default' NOT NULL,
    b_optimize BOOLEAN DEFAULT true NOT NULL,
    int_cores_max INT DEFAULT 0 NOT NULL,
    int_gpu_min INT DEFAULT 0 NOT NULL
);

CREATE TABLE job_env (
    pk_job_env VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36),
    str_key VARCHAR(36),
    str_value VARCHAR(2048)
);

CREATE TABLE job (
    pk_job VARCHAR(36) NOT NULL,
    pk_folder VARCHAR(36) NOT NULL,
    pk_show VARCHAR(36) NOT NULL,
    str_name VARCHAR(255) NOT NULL,
    str_visible_name VARCHAR(255),
    str_shot VARCHAR(64) NOT NULL,
    str_user VARCHAR(32) NOT NULL,
    str_state VARCHAR(16) NOT NULL,
    str_log_dir VARCHAR(4000) DEFAULT '' NOT NULL,
    int_uid BIGINT DEFAULT 0 NOT NULL,
    b_paused BOOLEAN DEFAULT false NOT NULL,
    b_autoeat BOOLEAN DEFAULT false NOT NULL,
    int_frame_count INT DEFAULT 0 NOT NULL,
    int_layer_count INT DEFAULT 0 NOT NULL,
    int_max_retries SMALLINT DEFAULT 3 NOT NULL,
    b_auto_book BOOLEAN DEFAULT true NOT NULL,
    b_auto_unbook BOOLEAN DEFAULT true NOT NULL,
    b_comment BOOLEAN DEFAULT false NOT NULL,
    str_email VARCHAR(256),
    pk_facility VARCHAR(36) NOT NULL,
    pk_dept VARCHAR(36) NOT NULL,
    ts_started TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    ts_stopped TIMESTAMP (6) WITH TIME ZONE,
    int_min_cores INT DEFAULT 100 NOT NULL,
    int_max_cores INT DEFAULT 20000 NOT NULL,
    str_show VARCHAR(32) DEFAULT 'none' NOT NULL,
    ts_updated TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    str_os VARCHAR(12) DEFAULT 'rhel40' NOT NULL
);

CREATE TABLE host_stat (
    pk_host_stat VARCHAR(36) NOT NULL,
    pk_host VARCHAR(36) NOT NULL,
    int_mem_total BIGINT DEFAULT 0 NOT NULL,
    int_mem_free BIGINT DEFAULT 0 NOT NULL,
    int_swap_total BIGINT DEFAULT 0 NOT NULL,
    int_swap_free BIGINT DEFAULT 0 NOT NULL,
    int_mcp_total BIGINT DEFAULT 0 NOT NULL,
    int_mcp_free BIGINT DEFAULT 0 NOT NULL,
    int_load BIGINT DEFAULT 0 NOT NULL,
    ts_ping TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    ts_booted TIMESTAMP (6) WITH TIME ZONE DEFAULT current_timestamp NOT NULL,
    str_state VARCHAR(32) DEFAULT 'UP' NOT NULL,
    str_os VARCHAR(12) DEFAULT 'rhel40' NOT NULL,
    int_gpu_total INT DEFAULT 0 NOT NULL,
    int_gpu_free INT DEFAULT 0 NOT NULL
);

CREATE TABLE host (
    pk_host VARCHAR(36) NOT NULL,
    pk_alloc VARCHAR(36) NOT NULL,
    str_name VARCHAR(30) NOT NULL,
    str_lock_state VARCHAR(36) NOT NULL,
    b_nimby BOOLEAN DEFAULT false NOT NULL,
    ts_created TIMESTAMP (6) DEFAULT current_timestamp NOT NULL,
    int_cores BIGINT DEFAULT 0 NOT NULL,
    int_procs BIGINT DEFAULT 0 NOT NULL,
    int_cores_idle BIGINT DEFAULT 0 NOT NULL,
    int_mem BIGINT DEFAULT 0 NOT NULL,
    int_mem_idle BIGINT DEFAULT 0 NOT NULL,
    b_unlock_boot BOOLEAN DEFAULT false NOT NULL,
    b_unlock_idle BOOLEAN DEFAULT false NOT NULL,
    b_reboot_idle BOOLEAN DEFAULT false NOT NULL,
    str_tags VARCHAR(128),
    str_fqdn VARCHAR(128),
    b_comment BOOLEAN DEFAULT false NOT NULL,
    int_thread_mode INT DEFAULT 0 NOT NULL,
    str_lock_source VARCHAR(128),
    int_gpu INT DEFAULT 0 NOT NULL,
    int_gpu_idle INT DEFAULT 0 NOT NULL
);

CREATE TABLE frame (
    pk_frame VARCHAR(36) NOT NULL,
    pk_layer VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36) NOT NULL,
    str_name VARCHAR(256) NOT NULL,
    str_state VARCHAR(24) NOT NULL,
    int_number BIGINT NOT NULL,
    int_depend_count BIGINT DEFAULT 0 NOT NULL,
    int_exit_status BIGINT DEFAULT -1 NOT NULL,
    int_retries BIGINT DEFAULT 0 NOT NULL,
    int_mem_reserved BIGINT DEFAULT 0 NOT NULL,
    int_mem_max_used BIGINT DEFAULT 0 NOT NULL,
    int_mem_used BIGINT DEFAULT 0 NOT NULL,
    int_dispatch_order BIGINT DEFAULT 0 NOT NULL,
    str_host VARCHAR(256),
    int_cores INT DEFAULT 0 NOT NULL,
    int_layer_order INT NOT NULL,
    ts_started TIMESTAMP (6) WITH TIME ZONE,
    ts_stopped TIMESTAMP (6) WITH TIME ZONE,
    ts_last_run TIMESTAMP (6) WITH TIME ZONE,
    ts_updated TIMESTAMP (6) WITH TIME ZONE,
    int_version INT DEFAULT 0,
    str_checkpoint_state VARCHAR(12) DEFAULT 'DISABLED' NOT NULL,
    int_checkpoint_count SMALLINT DEFAULT 0 NOT NULL,
    int_gpu_reserved INT DEFAULT 0 NOT NULL,
    int_total_past_core_time INT DEFAULT 0 NOT NULL
);

CREATE TABLE folder_level (
    pk_folder_level VARCHAR(36) NOT NULL,
    pk_folder VARCHAR(36) NOT NULL,
    int_level BIGINT DEFAULT 0 NOT NULL
);

CREATE TABLE folder (
    pk_folder VARCHAR(36) NOT NULL,
    pk_parent_folder VARCHAR(36),
    pk_show VARCHAR(36) NOT NULL,
    str_name VARCHAR(36) NOT NULL,
    int_priority BIGINT DEFAULT 1 NOT NULL,
    b_default BOOLEAN DEFAULT false NOT NULL,
    pk_dept VARCHAR(36) NOT NULL,
    int_job_min_cores INT DEFAULT -1 NOT NULL,
    int_job_max_cores INT DEFAULT -1 NOT NULL,
    int_job_priority INT DEFAULT -1 NOT NULL,
    int_min_cores INT DEFAULT 0 NOT NULL,
    int_max_cores INT DEFAULT -1 NOT NULL,
    b_exclude_managed BOOLEAN DEFAULT false NOT NULL,
    f_order INT DEFAULT 0 NOT NULL
);

CREATE TABLE filter (
    pk_filter VARCHAR(36) NOT NULL,
    pk_show VARCHAR(36) NOT NULL,
    str_name VARCHAR(128) NOT NULL,
    str_type VARCHAR(16) NOT NULL,
    f_order NUMERIC(6,2) DEFAULT 0.0 NOT NULL,
    b_enabled BOOLEAN DEFAULT true NOT NULL
);

CREATE TABLE depend (
    pk_depend VARCHAR(36) NOT NULL,
    pk_parent VARCHAR(36),
    pk_job_depend_on VARCHAR(36) NOT NULL,
    pk_job_depend_er VARCHAR(36) NOT NULL,
    pk_frame_depend_on VARCHAR(36),
    pk_frame_depend_er VARCHAR(36),
    pk_layer_depend_on VARCHAR(36),
    pk_layer_depend_er VARCHAR(36),
    str_type VARCHAR(36) NOT NULL,
    b_active BOOLEAN DEFAULT true NOT NULL,
    b_any BOOLEAN DEFAULT false NOT NULL,
    ts_created TIMESTAMP (6) DEFAULT current_timestamp NOT NULL,
    ts_satisfied TIMESTAMP (6),
    str_target VARCHAR(20) DEFAULT 'Internal' NOT NULL,
    str_signature VARCHAR(36) NOT NULL,
    b_composite BOOLEAN DEFAULT false NOT NULL
);

CREATE TABLE config (
    pk_config VARCHAR(36) NOT NULL,
    str_key VARCHAR(36) NOT NULL,
    int_value BIGINT DEFAULT 0,
    long_value BIGINT DEFAULT 0,
    str_value VARCHAR(255) DEFAULT '',
    b_value BOOLEAN DEFAULT false
);

CREATE TABLE comments (
    pk_comment VARCHAR(36) NOT NULL,
    pk_job VARCHAR(36),
    pk_host VARCHAR(36),
    ts_created TIMESTAMP (6) DEFAULT current_timestamp NOT NULL,
    str_user VARCHAR(36) NOT NULL,
    str_subject VARCHAR(128) NOT NULL,
    str_message VARCHAR(4000) NOT NULL
);

CREATE TABLE alloc (
    pk_alloc VARCHAR(36) NOT NULL,
    str_name VARCHAR(36) NOT NULL,
    b_allow_edit BOOLEAN DEFAULT true NOT NULL,
    b_default BOOLEAN DEFAULT false NOT NULL,
    str_tag VARCHAR(24),
    b_billable BOOLEAN DEFAULT true NOT NULL,
    pk_facility VARCHAR(36) NOT NULL,
    b_enabled BOOLEAN DEFAULT true
);

CREATE TABLE action (
    pk_action VARCHAR(36) NOT NULL,
    pk_filter VARCHAR(36) NOT NULL,
    pk_folder VARCHAR(36),
    str_action VARCHAR(24) NOT NULL,
    str_value_type VARCHAR(24) NOT NULL,
    str_value VARCHAR(4000),
    int_value BIGINT,
    b_value BOOLEAN,
    ts_created TIMESTAMP (6) DEFAULT current_timestamp NOT NULL,
    float_value NUMERIC(6,2),
    b_stop BOOLEAN DEFAULT false NOT NULL
);


CREATE TABLE redirect (
    pk_proc VARCHAR(36) NOT NULL,
    str_group_id VARCHAR(36) NOT NULL,
    int_type BIGINT NOT NULL,
    str_destination_id VARCHAR(512) NOT NULL,
    str_name VARCHAR(512) NOT NULL,
    lng_creation_time BIGINT NOT NULL
);


COMMENT ON COLUMN job_history.int_core_time_success IS 'seconds per core succeeded';

COMMENT ON COLUMN job_history.int_core_time_fail IS 'seconds per core failed';

COMMENT ON COLUMN job_history.int_max_rss IS 'maximum kilobytes of rss memory used by a single frame';

COMMENT ON COLUMN layer_history.int_core_time_success IS 'seconds per core succeeded';

COMMENT ON COLUMN layer_history.int_core_time_fail IS 'seconds per core failed';

COMMENT ON COLUMN layer_history.int_max_rss IS 'maximum kilobytes of rss memory used by a single frame';

COMMENT ON COLUMN frame_history.int_mem_reserved IS 'kilobytes of memory reserved';

COMMENT ON COLUMN frame_history.int_mem_max_used IS 'maximum kilobytes of rss memory used';

COMMENT ON COLUMN frame_history.int_cores IS '100 cores per physical core';


CREATE FUNCTION CALCULATE_CORE_HOURS (NUMERIC, NUMERIC, NUMERIC, NUMERIC, NUMERIC, NUMERIC)
RETURNS NUMERIC AS '
DECLARE
    int_ts_started ALIAS FOR $1;
    int_ts_stopped ALIAS FOR $2;
    int_start_report ALIAS FOR $3;
    int_stop_report ALIAS FOR $4;
    int_job_stopped ALIAS FOR $5;
    int_cores ALIAS FOR $6;

    int_started NUMERIC(12,0);
    int_stopped NUMERIC(12,0);
BEGIN
    IF int_cores = 0 THEN
        RETURN 0;
    END IF;

    int_started := int_ts_started;
    int_stopped := int_ts_stopped;

    IF int_stopped = 0 THEN
        int_stopped := int_job_stopped;
    END IF;

    IF int_stopped = 0 OR int_stopped > int_stop_report THEN
        int_stopped := int_stop_report;
    END IF;

    IF int_started < int_start_report THEN
        int_started := int_start_report;
    END IF;
    RETURN ((int_stopped - int_started) * (int_cores / 100) / 3600);
END;
' LANGUAGE 'plpgsql';

CREATE FUNCTION INTERVAL_TO_SECONDS(IN INTERVAL)
RETURNS NUMERIC AS '
DECLARE
    intrvl ALIAS FOR $1;
BEGIN
   RETURN EXTRACT(DAY FROM intrvl) * 86400
         + EXTRACT(HOUR FROM intrvl) * 3600
         + EXTRACT(MINUTE FROM intrvl) * 60
         + EXTRACT(SECOND FROM intrvl);
END;
' LANGUAGE 'plpgsql';

CREATE FUNCTION EPOCH(IN TIMESTAMP WITH TIME ZONE)
RETURNS NUMERIC AS '
DECLARE
    t ALIAS FOR $1;

    epoch_date TIMESTAMP(0) WITH TIME ZONE := TIMESTAMP ''1970-01-01 00:00:00.00 +00:00'';
    epoch_sec NUMERIC(12, 0);
    delta INTERVAL;
BEGIN
    delta := t - epoch_date;
    RETURN INTERVAL_TO_SECONDS(delta);
END;
' LANGUAGE 'plpgsql';

CREATE FUNCTION epoch_to_ts(IN NUMERIC)
RETURNS TIMESTAMP AS '
BEGIN
    RETURN TO_TIMESTAMP(''19700101000000'', ''YYYYMMDDHH24MISS TZH:TZM'')
        + NUMTODSINTERVAL(seconds, ''SECOND'');
END;
' LANGUAGE 'plpgsql';

CREATE FUNCTION FIND_DURATION(TIMESTAMP WITH TIME ZONE, TIMESTAMP WITH TIME ZONE)
RETURNS NUMERIC AS '
DECLARE
    ts_started ALIAS FOR $1;
    ts_stopped ALIAS FOR $2;

    t_interval INTERVAL DAY TO SECOND;
    t_stopped TIMESTAMP(0);
BEGIN

    IF ts_started IS NULL THEN
        RETURN 0;
    END IF;

    IF ts_stopped IS NULL THEN
      t_stopped := current_timestamp;
    ELSE
      t_stopped := ts_stopped;
    END IF;

    t_interval := t_stopped - ts_started;

    RETURN ROUND((EXTRACT(DAY FROM t_interval) * 86400
        + EXTRACT(HOUR FROM t_interval) * 3600
        + EXTRACT(MINUTE FROM t_interval) * 60
        + EXTRACT(SECOND FROM t_interval)));
END;
' LANGUAGE 'plpgsql';

CREATE FUNCTION genkey()
RETURNS VARCHAR AS $body$
DECLARE
    str_result VARCHAR(36);
    guid VARCHAR(36) := uuid_generate_v1();
BEGIN
    str_result := SUBSTR(guid, 0,8) || '-' || SUBSTR(guid,8,4)
      || '-' || SUBSTR(guid,12,4) || '-' || SUBSTR(guid,16,4) || '-' || SUBSTR(guid,20,12);
    RETURN str_result;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION render_weeks(DATE)
RETURNS NUMERIC AS '
DECLARE
    dt_end ALIAS FOR $1;

    int_weeks NUMERIC;
BEGIN
    int_weeks := (dt_end - (next_day(current_timestamp,''sunday'')+7)) / 7.0;
    IF int_weeks < 1 THEN
      RETURN 1;
    ELSE
      RETURN int_weeks;
    END IF;
END;
' LANGUAGE 'plpgsql';

CREATE FUNCTION soft_tier(IN NUMERIC, IN NUMERIC)
RETURNS NUMERIC AS '
DECLARE
    int_cores ALIAS FOR $1;
    int_min_cores ALIAS FOR $2;
BEGIN
  IF int_cores IS NULL THEN
      RETURN 0;
  END IF;
  IF int_min_cores = 0 OR int_cores >= int_min_cores THEN
      RETURN 1;
  ELSE
    IF int_cores = 0 THEN
        return int_min_cores * -1;
    ELSE
        RETURN int_cores / int_min_cores;
    END IF;
  END IF;
END;
' LANGUAGE 'plpgsql';

CREATE FUNCTION tier(IN NUMERIC, IN NUMERIC)
RETURNS NUMERIC AS '
DECLARE
    int_cores ALIAS FOR $1;
    int_min_cores ALIAS FOR $2;
BEGIN
  IF int_min_cores = 0 THEN
       RETURN (int_cores / 100) + 1;
  ELSE
    IF int_cores = 0 THEN
        return int_min_cores * -1;
    ELSE
        RETURN int_cores / int_min_cores;
    END IF;
  END IF;
END;
' LANGUAGE 'plpgsql';

CREATE FUNCTION recalculate_subs()
RETURNS VOID AS $body$
DECLARE
    r RECORD;
BEGIN
  --
  -- concatenates all tags in host_tag and sets host.str_tags
  --
  UPDATE subscription SET int_cores = 0;
  FOR r IN
    SELECT proc.pk_show, alloc.pk_alloc, sum(proc.int_cores_reserved) as c
    FROM proc, host, alloc
    WHERE proc.pk_host = host.pk_host AND host.pk_alloc = alloc.pk_alloc
    GROUP BY proc.pk_show, alloc.pk_alloc
  LOOP
    UPDATE subscription SET int_cores = r.c WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;

  END LOOP;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION recalculate_tags(IN VARCHAR)
RETURNS VOID AS $body$
DECLARE
    str_host_id ALIAS FOR $1;

    tag RECORD;
    full_str_tag VARCHAR(256) := '';
BEGIN
  --
  -- concatenates all tags in host_tag and sets host.str_tags
  --
  FOR tag IN (SELECT str_tag FROM host_tag WHERE pk_host=str_host_id ORDER BY str_tag_type ASC, str_tag ASC) LOOP
    full_str_tag := full_str_tag || ' ' || tag.str_tag;
  END LOOP;

  EXECUTE 'UPDATE host SET str_tags=trim($1) WHERE pk_host=$2'
    USING full_str_tag, str_host_id;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION recurse_folder_parent_change(IN VARCHAR, IN VARCHAR)
RETURNS VOID AS $body$
DECLARE
    str_folder_id ALIAS FOR $1;
    str_parent_folder_id ALIAS FOR $2;

    int_parent_level BIGINT;
    subfolder RECORD;
BEGIN
    SELECT int_level+1 INTO
        int_parent_level
    FROM
        folder_level
    WHERE
        pk_folder = str_parent_folder_id;

    UPDATE
        folder_level
    SET
        int_level = int_parent_level
    WHERE
        pk_folder = str_folder_id;

    FOR subfolder IN
        SELECT pk_folder FROM folder
        WHERE pk_parent_folder = str_folder_id
    LOOP
        PERFORM recurse_folder_parent_change(subfolder.pk_folder, str_folder_id);
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION rename_allocs()
RETURNS VOID AS $body$
DECLARE
    alloc RECORD;
BEGIN
    FOR alloc IN
        SELECT alloc.pk_alloc, alloc.str_name AS aname,facility.str_name AS fname
        FROM alloc,facility
        WHERE alloc.pk_facility = facility.pk_facility
    LOOP
        EXECUTE 'UPDATE alloc SET str_name=$1 WHERE pk_alloc=$2' USING
            alloc.fname || '.' || alloc.aname, alloc.pk_alloc;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION reorder_filters(IN VARCHAR)
RETURNS VOID AS $body$
DECLARE
    p_str_show_id ALIAS FOR $1;

    f_new_order INT := 1;
    r_filter RECORD;
BEGIN
    FOR r_filter IN
        SELECT pk_filter
        FROM filter
        WHERE pk_show=p_str_show_id
        ORDER BY f_order ASC
    LOOP
        UPDATE filter SET f_order=f_new_order WHERE pk_filter = r_filter.pk_filter;
        f_new_order := f_new_order + 1;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION tmp_populate_folder()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT pk_folder, pk_show, sum(int_cores) AS c
        FROM job, job_resource
        WHERE job.pk_job = job_resource.pk_job
        GROUP by pk_folder, pk_show
    LOOP
        UPDATE folder_resource SET int_cores = t.c WHERE pk_folder = t.pk_folder;
        COMMIT;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION tmp_populate_point()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT pk_dept, pk_show, sum(int_cores) AS c
        FROM job, job_resource
        WHERE job.pk_job = job_resource.pk_job
        GROUP BY pk_dept, pk_show
    LOOP
        UPDATE point SET int_cores = t.c WHERE pk_show = t.pk_show AND pk_dept = t.pk_dept;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION tmp_populate_sub()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT proc.pk_show, host.pk_alloc, sum(int_cores_reserved) AS c
        FROM proc, host
        WHERE proc.pk_host = host.pk_host
        GROUP BY proc.pk_show, host.pk_alloc
    LOOP
        UPDATE subscription SET int_cores = t.c WHERE pk_show = t.pk_show AND pk_alloc = t.pk_alloc;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


CREATE UNIQUE INDEX c_action_pk ON action (pk_action);

CREATE INDEX i_action_pk_filter ON action (pk_filter);

CREATE INDEX i_action_pk_group ON action (pk_folder);

CREATE UNIQUE INDEX c_alloc_pk ON alloc (pk_alloc);

CREATE INDEX i_alloc_pk_facility ON alloc (pk_facility);

CREATE UNIQUE INDEX c_alloc_name_uniq ON alloc (str_name);

CREATE UNIQUE INDEX c_comment_pk ON comments (pk_comment);

CREATE INDEX i_comment_pk_job ON comments (pk_job);

CREATE INDEX i_comment_pk_host ON comments (pk_host);

CREATE UNIQUE INDEX c_pk_pkconfig ON config (pk_config);

CREATE UNIQUE INDEX c_show_uk ON config (str_key);

CREATE UNIQUE INDEX i_depend_signature ON depend (str_signature);

CREATE INDEX i_depend_on_layer ON depend (pk_layer_depend_on);

CREATE INDEX i_depend_er_layer ON depend (pk_layer_depend_er);

CREATE INDEX i_depend_str_target ON depend (str_target);

CREATE INDEX i_depend_on_frame ON depend (pk_frame_depend_on);

CREATE INDEX i_depend_str_type ON depend (str_type);

CREATE INDEX i_depend_er_frame ON depend (pk_frame_depend_er);

CREATE INDEX i_depend_b_composite ON depend (b_composite);

CREATE UNIQUE INDEX c_depend_pk ON depend (pk_depend);

CREATE INDEX i_depend_pkparent ON depend (pk_parent);

CREATE INDEX i_depend_pk_on_job ON depend (pk_job_depend_on);

CREATE INDEX i_depend_pk_er_job ON depend (pk_job_depend_er);

CREATE UNIQUE INDEX c_filter_pk ON filter (pk_filter);

CREATE INDEX i_filters_pk_show ON filter (pk_show);

CREATE UNIQUE INDEX c_folder_uk ON folder (pk_parent_folder, str_name);

CREATE INDEX i_folder_pkparentfolder ON folder (pk_parent_folder);

CREATE INDEX i_folder_pkshow ON folder (pk_show);

CREATE INDEX i_folder_strname ON folder (str_name);

CREATE UNIQUE INDEX c_folder_pk ON folder (pk_folder);

CREATE UNIQUE INDEX c_folder_level_pk ON folder_level (pk_folder_level);

CREATE UNIQUE INDEX c_folder_level_uk ON folder_level (pk_folder);

CREATE INDEX i_frame_state_job ON frame (str_state, pk_job);

CREATE INDEX i_frame_dispatch_idx ON frame (int_dispatch_order, int_layer_order);

CREATE INDEX i_frame_pk_job ON frame (pk_job);

CREATE UNIQUE INDEX c_frame_pk ON frame (pk_frame);

CREATE INDEX i_frame_pkjoblayer ON frame (pk_layer);

CREATE UNIQUE INDEX c_frame_str_name_unq ON frame (str_name, pk_job);

CREATE INDEX i_frame_int_gpu_reserved ON frame (int_gpu_reserved);

CREATE UNIQUE INDEX c_str_host_fqdn_uk ON host (str_fqdn);

CREATE UNIQUE INDEX c_host_pk ON host (pk_host);

CREATE UNIQUE INDEX c_host_uk ON host (str_name);

CREATE INDEX i_host_pkalloc ON host (pk_alloc);

CREATE INDEX i_host_strlockstate ON host (str_lock_state);

CREATE INDEX i_host_int_gpu ON host (int_gpu);

CREATE INDEX i_host_int_gpu_idle ON host (int_gpu_idle);

CREATE INDEX i_host_str_tags ON host (str_tags);

CREATE INDEX i_host_stat_int_gpu_total ON host_stat (int_gpu_total);

CREATE INDEX i_host_stat_int_gpu_free ON host_stat (int_gpu_free);

CREATE INDEX i_host_stat_str_os ON host_stat (str_os);

CREATE UNIQUE INDEX c_hoststat_pk ON host_stat (pk_host_stat);

CREATE UNIQUE INDEX c_host_stat_pk_host_uk ON host_stat (pk_host);

CREATE INDEX i_booking_3 ON job (str_state, b_paused, pk_show, pk_facility);

CREATE INDEX i_job_str_os ON job (str_os);

CREATE INDEX i_job_pk_dept ON job (pk_dept);

CREATE INDEX i_job_pk_facility ON job (pk_facility);

CREATE INDEX i_job_str_shot ON job (str_shot);

CREATE UNIQUE INDEX c_job_pk ON job (pk_job);

CREATE UNIQUE INDEX c_job_uk ON job (str_visible_name);

CREATE INDEX i_job_pkgroup ON job (pk_folder);

CREATE INDEX i_job_pkshow ON job (pk_show);

CREATE INDEX i_job_str_name ON job (str_name);

CREATE INDEX i_job_str_state ON job (str_state);

CREATE UNIQUE INDEX c_job_env_pk ON job_env (pk_job_env);

CREATE INDEX i_job_env_pk_job ON job_env (pk_job);

CREATE INDEX i_layer_b_threadable ON layer (b_threadable);

CREATE INDEX i_layer_cores_mem ON layer (int_cores_min, int_mem_min);

CREATE INDEX i_layer_cores_mem_thread ON layer (int_cores_min, int_mem_min, b_threadable);

CREATE INDEX i_layer_mem_min ON layer (int_mem_min);

CREATE INDEX i_layer_int_dispatch_order ON layer (int_dispatch_order);

CREATE UNIQUE INDEX c_layer_pk ON layer (pk_layer);

CREATE INDEX i_layer_pkjob ON layer (pk_job);

CREATE INDEX i_layer_strname ON layer (str_name);

CREATE UNIQUE INDEX c_layer_str_name_unq ON layer (str_name, pk_job);

CREATE INDEX i_layer_int_gpu_min ON layer (int_gpu_min);

CREATE UNIQUE INDEX c_layer_env_pk ON layer_env (pk_layer_env);

CREATE INDEX i_layer_env_pk_job ON layer_env (pk_job);

CREATE INDEX i_layer_env_pk_layer ON layer_env (pk_layer);

CREATE UNIQUE INDEX c_layerresource_pk ON layer_resource (pk_layer_resource);

CREATE UNIQUE INDEX c_layerresource_uk ON layer_resource (pk_layer);

CREATE INDEX i_layer_resource_pk_job ON layer_resource (pk_job);

CREATE UNIQUE INDEX i_layer_stat_pk_layer ON layer_stat (pk_layer);

CREATE UNIQUE INDEX c_layerstat_pk ON layer_stat (pk_layer_stat);

CREATE INDEX i_layerstat_pkjob ON layer_stat (pk_job);

CREATE INDEX i_layerstat_int_waiting_count ON layer_stat ((CASE WHEN int_waiting_count > 0 THEN 1 ELSE NULL END), (CASE WHEN int_waiting_count > 0 THEN pk_layer ELSE NULL END));

CREATE INDEX i_layer_usage_pk_job ON layer_usage (pk_job);

CREATE UNIQUE INDEX c_layer_usage_pk ON layer_usage (pk_layer_usage);

CREATE UNIQUE INDEX c_layer_usage_pk_layer_uk ON layer_usage (pk_layer);

CREATE UNIQUE INDEX c_matcher_pk ON matcher (pk_matcher);

CREATE INDEX i_matcher_pk_filter ON matcher (pk_filter);

CREATE UNIQUE INDEX c_proc_pk ON proc (pk_proc);

CREATE UNIQUE INDEX c_proc_uk ON proc (pk_frame);

CREATE INDEX i_proc_pkhost ON proc (pk_host);

CREATE INDEX i_proc_pkjob ON proc (pk_job);

CREATE INDEX i_proc_pklayer ON proc (pk_layer);

CREATE INDEX i_proc_pkshow ON proc (pk_show);

CREATE INDEX i_proc_int_gpu_reserved ON proc (int_gpu_reserved);

CREATE UNIQUE INDEX c_show_pk ON show (pk_show);

CREATE INDEX i_sub_tier ON subscription (float_tier);

CREATE UNIQUE INDEX c_subscription_pk ON subscription (pk_subscription);

CREATE UNIQUE INDEX c_subscription_uk ON subscription (pk_show, pk_alloc);

CREATE INDEX i_subscription_pkalloc ON subscription (pk_alloc);

CREATE INDEX i_job_stat_int_waiting_count ON job_stat (int_waiting_count);

CREATE UNIQUE INDEX i_job_stat_pk_job ON job_stat (pk_job);

CREATE UNIQUE INDEX c_job_stat_pk ON job_stat (pk_job_stat);

CREATE INDEX i_job_resource_min_max ON job_resource (int_min_cores, int_max_cores);

CREATE INDEX i_job_tier ON job_resource (float_tier);

CREATE UNIQUE INDEX c_job_resource_pk ON job_resource (pk_job_resource);

CREATE UNIQUE INDEX c_job_resource_uk ON job_resource (pk_job);

CREATE INDEX i_job_resource_cores ON job_resource (int_cores);

CREATE INDEX i_job_resource_max_c ON job_resource (int_max_cores);

CREATE UNIQUE INDEX c_job_usage_pk ON job_usage (pk_job_usage);

CREATE UNIQUE INDEX c_job_usage_pk_job_uniq ON job_usage (pk_job);

CREATE UNIQUE INDEX c_host_tag_pk ON host_tag (pk_host_tag);

CREATE INDEX i_host_tag_pk_host ON host_tag (pk_host);

CREATE INDEX i_host_str_tag_type ON host_tag (str_tag_type);

CREATE UNIQUE INDEX c_task_lock_pk ON task_lock (pk_task_lock);

CREATE UNIQUE INDEX c_job_history_pk ON job_history (pk_job);

CREATE INDEX i_job_history_pk_show ON job_history (pk_show);

CREATE INDEX i_job_history_b_archived ON job_history (b_archived);

CREATE INDEX i_job_history_ts_start_stop ON job_history (int_ts_started, int_ts_stopped);

CREATE INDEX i_job_history_str_name ON job_history (str_name);

CREATE INDEX i_job_history_str_shot ON job_history (str_shot);

CREATE INDEX i_job_history_str_user ON job_history (str_user);

CREATE INDEX i_job_history_pk_dept ON job_history (pk_dept);

CREATE INDEX i_job_history_pk_facility ON job_history (pk_facility);

CREATE UNIQUE INDEX c_layer_history_pk ON layer_history (pk_layer);

CREATE INDEX i_layer_history_str_name ON layer_history (str_name);

CREATE INDEX i_layer_history_str_type ON layer_history (str_type);

CREATE INDEX i_layer_history_pk_job ON layer_history (pk_job);

CREATE INDEX i_layer_history_b_archived ON layer_history (b_archived);

CREATE INDEX i_job_post_pk_post_job ON job_post (pk_post_job);

CREATE UNIQUE INDEX c_job_post_pk ON job_post (pk_job_post);

CREATE INDEX i_job_post_pk_job ON job_post (pk_job);

CREATE UNIQUE INDEX c_facility_pk ON facility (pk_facility);

CREATE UNIQUE INDEX c_dept_pk ON dept (pk_dept);

CREATE INDEX i_show_alias_pk_show ON show_alias (pk_show);

CREATE UNIQUE INDEX c_show_alias_pk ON show_alias (pk_show_alias);

CREATE UNIQUE INDEX c_folder_resource_pk ON folder_resource (pk_folder_resource);

CREATE INDEX i_folder_res_int_max_cores ON folder_resource (int_max_cores);

CREATE INDEX i_folder_resource_fl_tier ON folder_resource (float_tier);

CREATE INDEX i_folderresource_pkfolder ON folder_resource (pk_folder);

CREATE UNIQUE INDEX c_job_mem_pk ON job_mem (pk_job_mem);

CREATE UNIQUE INDEX i_job_mem_pk_job ON job_mem (pk_job);

CREATE INDEX i_job_mem_int_max_rss ON job_mem (int_max_rss);

CREATE UNIQUE INDEX c_layer_mem_pk ON layer_mem (pk_layer_mem);

CREATE UNIQUE INDEX i_layer_mem_pk_layer ON layer_mem (pk_layer);

CREATE INDEX i_layer_mem_pk_job ON layer_mem (pk_job);

CREATE INDEX i_layer_mem_int_max_rss ON layer_mem (int_max_rss);

CREATE UNIQUE INDEX c_point_pk ON point (pk_point);

CREATE INDEX i_point_pk_dept ON point (pk_dept);

CREATE INDEX i_point_pk_show ON point (pk_show);

CREATE UNIQUE INDEX c_point_pk_show_dept ON point (pk_show, pk_dept);

CREATE INDEX i_point_tier ON point (float_tier);

CREATE UNIQUE INDEX c_task_pk ON task (pk_task);

CREATE INDEX i_task_pk_point ON task (pk_point);

CREATE UNIQUE INDEX c_task_uniq ON task (str_shot, pk_point);

CREATE UNIQUE INDEX c_pk_job_local ON job_local (pk_job_local);

CREATE UNIQUE INDEX i_job_local_pk_job ON job_local (pk_job);

CREATE UNIQUE INDEX i_job_local_pk_host ON job_local (pk_host);

CREATE UNIQUE INDEX c_pk_service ON service (pk_service);

CREATE UNIQUE INDEX i_service_str_name ON service (str_name);

CREATE INDEX i_service_int_gpu_min ON service (int_gpu_min);

CREATE INDEX i_host_local ON host_local (pk_host);

CREATE UNIQUE INDEX c_pk_host_local ON host_local (pk_host_local);

CREATE INDEX i_host_local_pk_job ON host_local (pk_job);

CREATE UNIQUE INDEX i_host_local_unique ON host_local (pk_host, pk_job);

CREATE INDEX i_host_local_int_gpu_idle ON host_local (int_gpu_idle);

CREATE INDEX i_host_local_int_gpu_max ON host_local (int_gpu_max);

CREATE UNIQUE INDEX c_pk_owner ON owner (pk_owner);

CREATE INDEX i_owner_pk_show ON owner (pk_show);

CREATE UNIQUE INDEX i_owner_str_username ON owner (str_username);

CREATE UNIQUE INDEX c_pk_deed ON deed (pk_deed);

CREATE UNIQUE INDEX i_deed_pk_host ON deed (pk_host);

CREATE INDEX i_deed_pk_owner ON deed (pk_owner);

CREATE UNIQUE INDEX c_pk_show_service ON show_service (pk_show_service);

CREATE UNIQUE INDEX i_show_service_str_name ON show_service (str_name, pk_show);

CREATE INDEX i_show_service_int_gpu_min ON show_service (int_gpu_min);

CREATE UNIQUE INDEX c_pk_layer_output ON layer_output (pk_layer_output);

CREATE INDEX i_layer_output_pk_layer ON layer_output (pk_layer);

CREATE INDEX i_layer_output_pk_job ON layer_output (pk_job);

CREATE UNIQUE INDEX i_layer_output_unique ON layer_output (pk_layer, str_filespec);

CREATE INDEX i_frame_history_ts_start_stop ON frame_history (int_ts_started, int_ts_stopped);

CREATE INDEX i_frame_history_int_exit_stat ON frame_history (int_exit_status);

CREATE INDEX i_frame_history_int_ts_stopped ON frame_history (int_ts_stopped);

CREATE INDEX i_frame_history_pk_alloc ON frame_history (pk_alloc);

CREATE INDEX i_frame_history_pk_frame ON frame_history (pk_frame);

CREATE INDEX i_frame_history_pk_job ON frame_history (pk_job);

CREATE INDEX i_frame_history_pk_layer ON frame_history (pk_layer);

CREATE INDEX i_frame_history_str_state ON frame_history (str_state);

CREATE UNIQUE INDEX c_history_period_pk ON history_period (pk);

CREATE UNIQUE INDEX c_frame_history_pk ON frame_history (pk_frame_history);

CREATE UNIQUE INDEX c_redirect_pk ON redirect (pk_proc);

CREATE INDEX i_redirect_group ON redirect (str_group_id);

CREATE INDEX i_redirect_create ON redirect (lng_creation_time);


ALTER TABLE action ADD CONSTRAINT c_action_pk PRIMARY KEY
  USING INDEX c_action_pk;

ALTER TABLE alloc ADD CONSTRAINT c_alloc_name_uniq UNIQUE
  USING INDEX c_alloc_name_uniq;

ALTER TABLE alloc ADD CONSTRAINT c_alloc_pk PRIMARY KEY
  USING INDEX c_alloc_pk;

ALTER TABLE comments ADD CONSTRAINT c_comment_pk PRIMARY KEY
  USING INDEX c_comment_pk;

ALTER TABLE config ADD CONSTRAINT c_pk_pkconfig PRIMARY KEY
  USING INDEX c_pk_pkconfig;

ALTER TABLE config ADD CONSTRAINT c_show_uk UNIQUE
  USING INDEX c_show_uk;

ALTER TABLE depend ADD CONSTRAINT c_depend_pk PRIMARY KEY
  USING INDEX c_depend_pk;

ALTER TABLE filter ADD CONSTRAINT c_filter_pk PRIMARY KEY
  USING INDEX c_filter_pk;

ALTER TABLE folder ADD CONSTRAINT c_folder_uk UNIQUE
  USING INDEX c_folder_uk;

ALTER TABLE folder ADD CONSTRAINT c_folder_pk PRIMARY KEY
  USING INDEX c_folder_pk;

ALTER TABLE folder_level ADD CONSTRAINT c_folder_level_pk PRIMARY KEY
  USING INDEX c_folder_level_pk;

ALTER TABLE folder_level ADD CONSTRAINT c_folder_level_uk UNIQUE
  USING INDEX c_folder_level_uk;

ALTER TABLE frame ADD CONSTRAINT c_frame_pk PRIMARY KEY
  USING INDEX c_frame_pk;

ALTER TABLE frame ADD CONSTRAINT c_frame_str_name_unq UNIQUE
  USING INDEX c_frame_str_name_unq;

ALTER TABLE host ADD CONSTRAINT c_str_host_fqdn_uk UNIQUE
  USING INDEX c_str_host_fqdn_uk;

ALTER TABLE host ADD CONSTRAINT c_host_pk PRIMARY KEY
  USING INDEX c_host_pk;

ALTER TABLE host ADD CONSTRAINT c_host_uk UNIQUE
  USING INDEX c_host_uk;

ALTER TABLE host_stat ADD CONSTRAINT c_hoststat_pk PRIMARY KEY
  USING INDEX c_hoststat_pk;

ALTER TABLE host_stat ADD CONSTRAINT c_host_stat_pk_host_uk UNIQUE
  USING INDEX c_host_stat_pk_host_uk;

ALTER TABLE job ADD CONSTRAINT c_job_pk PRIMARY KEY
  USING INDEX c_job_pk;

ALTER TABLE job ADD CONSTRAINT c_job_uk UNIQUE
  USING INDEX c_job_uk;

ALTER TABLE job_env ADD CONSTRAINT c_job_env_pk PRIMARY KEY
  USING INDEX c_job_env_pk;

ALTER TABLE job_local ADD CONSTRAINT c_pk_job_local PRIMARY KEY
  USING INDEX c_pk_job_local;

ALTER TABLE service ADD CONSTRAINT c_pk_service PRIMARY KEY
  USING INDEX c_pk_service;

ALTER TABLE host_local ADD CONSTRAINT c_pk_host_local PRIMARY KEY
  USING INDEX c_pk_host_local;

ALTER TABLE owner ADD CONSTRAINT c_pk_owner PRIMARY KEY
  USING INDEX c_pk_owner;

ALTER TABLE deed ADD CONSTRAINT c_pk_deed PRIMARY KEY
  USING INDEX c_pk_deed;

ALTER TABLE show_service ADD CONSTRAINT c_pk_show_service PRIMARY KEY
  USING INDEX c_pk_show_service;

ALTER TABLE layer_output ADD CONSTRAINT c_pk_layer_output PRIMARY KEY
  USING INDEX c_pk_layer_output;

ALTER TABLE layer ADD CONSTRAINT c_layer_pk PRIMARY KEY
  USING INDEX c_layer_pk;

ALTER TABLE layer ADD CONSTRAINT c_layer_str_name_unq UNIQUE
  USING INDEX c_layer_str_name_unq;

ALTER TABLE layer_env ADD CONSTRAINT c_layer_env_pk PRIMARY KEY
  USING INDEX c_layer_env_pk;

ALTER TABLE layer_resource ADD CONSTRAINT c_layerresource_pk PRIMARY KEY
  USING INDEX c_layerresource_pk;

ALTER TABLE layer_resource ADD CONSTRAINT c_layerresource_uk UNIQUE
  USING INDEX c_layerresource_uk;

ALTER TABLE layer_stat ADD CONSTRAINT c_layerstat_pk PRIMARY KEY
  USING INDEX c_layerstat_pk;

ALTER TABLE layer_usage ADD CONSTRAINT c_layer_usage_pk PRIMARY KEY
  USING INDEX c_layer_usage_pk;

ALTER TABLE layer_usage ADD CONSTRAINT c_layer_usage_pk_layer_uk UNIQUE
  USING INDEX c_layer_usage_pk_layer_uk;

ALTER TABLE matcher ADD CONSTRAINT c_matcher_pk PRIMARY KEY
  USING INDEX c_matcher_pk;

ALTER TABLE proc ADD CONSTRAINT c_proc_pk PRIMARY KEY
  USING INDEX c_proc_pk;

ALTER TABLE proc ADD CONSTRAINT c_proc_uk UNIQUE
  USING INDEX c_proc_uk;

ALTER TABLE show ADD CONSTRAINT c_show_pk PRIMARY KEY
  USING INDEX c_show_pk;

ALTER TABLE subscription ADD CONSTRAINT c_subscription_pk PRIMARY KEY
  USING INDEX c_subscription_pk;

ALTER TABLE subscription ADD CONSTRAINT c_subscription_uk UNIQUE
  USING INDEX c_subscription_uk;

ALTER TABLE job_stat ADD CONSTRAINT c_job_stat_pk PRIMARY KEY
  USING INDEX c_job_stat_pk;

ALTER TABLE job_resource ADD CONSTRAINT c_job_resource_pk PRIMARY KEY
  USING INDEX c_job_resource_pk;

ALTER TABLE job_resource ADD CONSTRAINT c_job_resource_uk UNIQUE
  USING INDEX c_job_resource_uk;

ALTER TABLE job_usage ADD CONSTRAINT c_job_usage_pk PRIMARY KEY
  USING INDEX c_job_usage_pk;

ALTER TABLE job_usage ADD CONSTRAINT c_job_usage_pk_job_uniq UNIQUE
  USING INDEX c_job_usage_pk_job_uniq;

ALTER TABLE host_tag ADD CONSTRAINT c_host_tag_pk PRIMARY KEY
  USING INDEX c_host_tag_pk;

ALTER TABLE task_lock ADD CONSTRAINT c_task_lock_pk PRIMARY KEY
  USING INDEX c_task_lock_pk;

ALTER TABLE job_history ADD CONSTRAINT c_job_history_pk PRIMARY KEY
  USING INDEX c_job_history_pk;

ALTER TABLE layer_history ADD CONSTRAINT c_layer_history_pk PRIMARY KEY
  USING INDEX c_layer_history_pk;

ALTER TABLE job_post ADD CONSTRAINT c_job_post_pk PRIMARY KEY
  USING INDEX c_job_post_pk;

ALTER TABLE facility ADD CONSTRAINT c_facility_pk PRIMARY KEY
  USING INDEX c_facility_pk;

ALTER TABLE dept ADD CONSTRAINT c_dept_pk PRIMARY KEY
  USING INDEX c_dept_pk;

ALTER TABLE show_alias ADD CONSTRAINT c_show_alias_pk PRIMARY KEY
  USING INDEX c_show_alias_pk;

ALTER TABLE folder_resource ADD CONSTRAINT c_folder_resource_pk PRIMARY KEY
  USING INDEX c_folder_resource_pk;

ALTER TABLE job_mem ADD CONSTRAINT c_job_mem_pk PRIMARY KEY
  USING INDEX c_job_mem_pk;

ALTER TABLE layer_mem ADD CONSTRAINT c_layer_mem_pk PRIMARY KEY
  USING INDEX c_layer_mem_pk;

ALTER TABLE point ADD CONSTRAINT c_point_pk PRIMARY KEY
  USING INDEX c_point_pk;

ALTER TABLE point ADD CONSTRAINT c_point_pk_show_dept UNIQUE
  USING INDEX c_point_pk_show_dept;

ALTER TABLE task ADD CONSTRAINT c_task_pk PRIMARY KEY
  USING INDEX c_task_pk;

ALTER TABLE task ADD CONSTRAINT c_task_uniq UNIQUE
  USING INDEX c_task_uniq;

ALTER TABLE history_period ADD CONSTRAINT c_history_period_pk PRIMARY KEY
  USING INDEX c_history_period_pk;

ALTER TABLE frame_history ADD CONSTRAINT c_frame_history_pk PRIMARY KEY
  USING INDEX c_frame_history_pk;

ALTER TABLE redirect ADD CONSTRAINT c_redirect_pk PRIMARY KEY
  USING INDEX c_redirect_pk;


CREATE VIEW vs_show_resource (pk_show, int_cores) AS
  SELECT
        job.pk_show,
        SUM(int_cores) AS int_cores
    FROM
       job,
       job_resource
    WHERE
       job.pk_job = job_resource.pk_job
    AND
       job.str_state='PENDING'
    GROUP BY
       job.pk_show;


CREATE VIEW vs_show_stat (pk_show, int_pending_count, int_running_count, int_dead_count, int_job_count) AS
  SELECT
        job.pk_show,
        SUM(int_waiting_count+int_depend_count) AS int_pending_count,
        SUM(int_running_count) AS int_running_count,
        SUM(int_dead_count) AS int_dead_count,
        COUNT(1) AS int_job_count
    FROM
        job_stat,
        job
    WHERE
        job_stat.pk_job = job.pk_job
    AND
        job.str_state = 'PENDING'
    GROUP BY job.pk_show;


CREATE VIEW vs_job_resource (pk_job, int_procs, int_cores, int_mem_reserved) AS
  SELECT
       job.pk_job,
       COUNT(proc.pk_proc) AS int_procs,
       COALESCE(SUM(int_cores_reserved),0) AS int_cores,
       COALESCE(SUM(int_mem_reserved),0) AS int_mem_reserved
    FROM
       job LEFT JOIN proc ON (proc.pk_job = job.pk_job)
    GROUP BY
       job.pk_job;


CREATE VIEW vs_alloc_usage (pk_alloc, int_cores, int_idle_cores, int_running_cores, int_locked_cores, int_available_cores, int_hosts, int_locked_hosts, int_down_hosts) AS
  SELECT
        alloc.pk_alloc,
        COALESCE(SUM(host.int_cores),0) AS int_cores,
        COALESCE(SUM(host.int_cores_idle),0) AS int_idle_cores,
        COALESCE(SUM(host.int_cores - host.int_cores_idle),0) as int_running_cores,
        COALESCE((SELECT SUM(int_cores) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND (str_lock_state='NIMBY_LOCKED' OR str_lock_state='LOCKED')),0) AS int_locked_cores,
        COALESCE((SELECT SUM(int_cores_idle) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND h.str_lock_state='OPEN' AND hs.str_state ='UP'),0) AS int_available_cores,
        COUNT(host.pk_host) AS int_hosts,
        (SELECT COUNT(*) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND str_lock_state='LOCKED') AS int_locked_hosts,
        (SELECT COUNT(*) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND hs.str_state='DOWN') AS int_down_hosts
    FROM
        alloc LEFT JOIN host ON (alloc.pk_alloc = host.pk_alloc)
    GROUP BY
        alloc.pk_alloc;


CREATE VIEW vs_folder_counts (pk_folder, int_depend_count, int_waiting_count, int_running_count, int_dead_count, int_cores, int_job_count) AS
  SELECT
    folder.pk_folder,
    COALESCE(SUM(int_depend_count),0) AS int_depend_count,
    COALESCE(SUM(int_waiting_count),0) AS int_waiting_count,
    COALESCE(SUM(int_running_count),0) AS int_running_count,
    COALESCE(SUM(int_dead_count),0) AS int_dead_count,
    COALESCE(SUM(int_cores),0) AS int_cores,
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


CREATE VIEW vs_waiting (pk_show) AS
  SELECT
        job.pk_show
    FROM
        job_resource jr,
        job_stat,
        job
    WHERE
        job_stat.pk_job = job.pk_job
    AND
        jr.pk_job = job.pk_job
    AND
        job.str_state = 'PENDING'
    AND
        job.b_paused = false
    AND
        jr.int_max_cores - jr.int_cores >= 100
    AND
        job_stat.int_waiting_count != 0

    GROUP BY job.pk_show;


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

CREATE FUNCTION history__period_shift()
RETURNS VOID AS $body$
DECLARE
    vTemp DATE;
BEGIN
    SELECT dt_end
    INTO vTemp
    FROM history_period;

    UPDATE history_period
    SET dt_begin = vTemp,
        dt_end = (SELECT current_timestamp FROM dual);

EXCEPTION
    WHEN no_data_found THEN
        INSERT INTO history_period (pk) VALUES (uuid_generate_v1());
        SELECT dt_end
        INTO vTemp
        FROM history_period;
    WHEN OTHERS THEN
        RAISE;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION history__period_shift(IN DATE)
RETURNS VOID AS $body$
DECLARE
    piEndDate ALIAS FOR $1;
    vTemp DATE;
BEGIN
    SELECT dt_end
    INTO vTemp
    FROM history_period;

    UPDATE history_period
    SET dt_begin = vTemp,
    dt_end = (SELECT nvl(piEndDate, current_timestamp) FROM dual);

EXCEPTION
    WHEN no_data_found THEN
        INSERT INTO history_period (pk) VALUES (uuid_generate_v1());
        SELECT dt_end
        INTO vTemp
        FROM history_period;
    WHEN OTHERS THEN
        RAISE;
END;
$body$
LANGUAGE PLPGSQL;

CREATE FUNCTION history__period_clear()
RETURNS VOID AS $body$
BEGIN

    DELETE FROM history_period;
    INSERT INTO history_period (pk) VALUES (uuid_generate_v1());

END;
$body$
LANGUAGE PLPGSQL;



ALTER TABLE action ADD CONSTRAINT c_action_pk_filter FOREIGN KEY (pk_filter)
      REFERENCES filter (pk_filter);

ALTER TABLE action ADD CONSTRAINT c_action_pk_folder FOREIGN KEY (pk_folder)
      REFERENCES folder (pk_folder);

ALTER TABLE alloc ADD CONSTRAINT c_alloc_pk_facility FOREIGN KEY (pk_facility)
      REFERENCES facility (pk_facility);

ALTER TABLE comments ADD CONSTRAINT c_comment_pk_host FOREIGN KEY (pk_host)
      REFERENCES host (pk_host);

ALTER TABLE comments ADD CONSTRAINT c_comment_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE filter ADD CONSTRAINT c_filter_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE folder ADD CONSTRAINT c_folder_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE folder ADD CONSTRAINT c_folder_pk_dept FOREIGN KEY (pk_dept)
      REFERENCES dept (pk_dept);

ALTER TABLE folder_level ADD CONSTRAINT c_folder_level_pk_folder FOREIGN KEY (pk_folder)
      REFERENCES folder (pk_folder);

ALTER TABLE frame ADD CONSTRAINT c_frame_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE frame ADD CONSTRAINT c_frame_pk_layer FOREIGN KEY (pk_layer)
      REFERENCES layer (pk_layer);

ALTER TABLE host ADD CONSTRAINT c_host_pk_alloc FOREIGN KEY (pk_alloc)
      REFERENCES alloc (pk_alloc);

ALTER TABLE host_stat ADD CONSTRAINT c_host_stat_pk_host FOREIGN KEY (pk_host)
      REFERENCES host (pk_host);

ALTER TABLE job ADD CONSTRAINT c_job_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE job ADD CONSTRAINT c_job_pk_folder FOREIGN KEY (pk_folder)
      REFERENCES folder (pk_folder);

ALTER TABLE job ADD CONSTRAINT c_job_pk_facility FOREIGN KEY (pk_facility)
      REFERENCES facility (pk_facility);

ALTER TABLE job ADD CONSTRAINT c_job_pk_dept FOREIGN KEY (pk_dept)
      REFERENCES dept (pk_dept);

ALTER TABLE job_env ADD CONSTRAINT c_job_env_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE layer ADD CONSTRAINT c_layer_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE layer_env ADD CONSTRAINT c_layer_env_pk_layer FOREIGN KEY (pk_layer)
      REFERENCES layer (pk_layer);

ALTER TABLE layer_env ADD CONSTRAINT c_layer_env_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE layer_resource ADD CONSTRAINT c_layer_resource_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE layer_resource ADD CONSTRAINT c_layer_resource_pk_layer FOREIGN KEY (pk_layer)
      REFERENCES layer (pk_layer);

ALTER TABLE layer_stat ADD CONSTRAINT c_layer_stat_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE layer_stat ADD CONSTRAINT c_layer_stat_pk_layer FOREIGN KEY (pk_layer)
      REFERENCES layer (pk_layer);

ALTER TABLE layer_usage ADD CONSTRAINT c_layer_usage_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE layer_usage ADD CONSTRAINT c_layer_usage_pk_layer FOREIGN KEY (pk_layer)
      REFERENCES layer (pk_layer);

ALTER TABLE matcher ADD CONSTRAINT c_matcher_pk_filter FOREIGN KEY (pk_filter)
      REFERENCES filter (pk_filter);

ALTER TABLE proc ADD CONSTRAINT c_proc_pk_frame FOREIGN KEY (pk_frame)
      REFERENCES frame (pk_frame);

ALTER TABLE proc ADD CONSTRAINT c_proc_pk_host FOREIGN KEY (pk_host)
      REFERENCES host (pk_host);

ALTER TABLE subscription ADD CONSTRAINT c_subscription_pk_alloc FOREIGN KEY (pk_alloc)
      REFERENCES alloc (pk_alloc);

ALTER TABLE subscription ADD CONSTRAINT c_subscription_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE job_stat ADD CONSTRAINT c_job_stat_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE job_resource ADD CONSTRAINT c_job_resource_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE job_usage ADD CONSTRAINT c_job_usage_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE job_history ADD CONSTRAINT c_job_history_pk_facility FOREIGN KEY (pk_facility)
      REFERENCES facility (pk_facility);

ALTER TABLE job_history ADD CONSTRAINT c_job_history_pk_dept FOREIGN KEY (pk_dept)
      REFERENCES dept (pk_dept);

ALTER TABLE job_history ADD CONSTRAINT c_job_history_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE layer_history ADD CONSTRAINT c_layer_history_pk_job FOREIGN KEY (pk_job)
      REFERENCES job_history (pk_job) ON DELETE CASCADE;

ALTER TABLE job_post ADD CONSTRAINT c_job_post_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE job_post ADD CONSTRAINT c_job_post_pk_post_job FOREIGN KEY (pk_post_job)
      REFERENCES job (pk_job);

ALTER TABLE show_alias ADD CONSTRAINT c_show_alias_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE folder_resource ADD CONSTRAINT c_folder_resource_pk_folder FOREIGN KEY (pk_folder)
      REFERENCES folder (pk_folder);

ALTER TABLE job_mem ADD CONSTRAINT c_job_mem_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE layer_mem ADD CONSTRAINT c_layer_mem_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE layer_mem ADD CONSTRAINT c_layer_mem_pk_layer FOREIGN KEY (pk_layer)
      REFERENCES layer (pk_layer);

ALTER TABLE point ADD CONSTRAINT c_point_pk_dept FOREIGN KEY (pk_dept)
      REFERENCES dept (pk_dept);

ALTER TABLE point ADD CONSTRAINT c_point_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE task ADD CONSTRAINT c_task_pk_point FOREIGN KEY (pk_point)
      REFERENCES point (pk_point);

ALTER TABLE job_local ADD CONSTRAINT c_job_local_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE job_local ADD CONSTRAINT c_job_local_pk_host FOREIGN KEY (pk_host)
      REFERENCES host (pk_host);

ALTER TABLE host_local ADD CONSTRAINT c_host_local_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE host_local ADD CONSTRAINT c_host_local_pk_host FOREIGN KEY (pk_host)
      REFERENCES host (pk_host);

ALTER TABLE owner ADD CONSTRAINT c_owner_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE deed ADD CONSTRAINT c_deed_pk_host FOREIGN KEY (pk_host)
      REFERENCES host (pk_host);

ALTER TABLE show_service ADD CONSTRAINT c_show_service_pk_show FOREIGN KEY (pk_show)
      REFERENCES show (pk_show);

ALTER TABLE layer_output ADD CONSTRAINT c_layer_output_pk_layer FOREIGN KEY (pk_layer)
      REFERENCES layer (pk_layer);

ALTER TABLE layer_output ADD CONSTRAINT c_layer_output_pk_job FOREIGN KEY (pk_job)
      REFERENCES job (pk_job);

ALTER TABLE frame_history ADD CONSTRAINT c_frame_history_pk_job FOREIGN KEY (pk_job)
      REFERENCES job_history (pk_job) ON DELETE CASCADE;

ALTER TABLE frame_history ADD CONSTRAINT c_frame_history_pk_layer FOREIGN KEY (pk_layer)
      REFERENCES layer_history (pk_layer) ON DELETE CASCADE;

ALTER TABLE frame_history ADD CONSTRAINT c_frame_history_pk_alloc FOREIGN KEY (pk_alloc)
      REFERENCES alloc (pk_alloc);


CREATE TYPE JobStatType AS (
    int_core_time_success BIGINT,
    int_core_time_fail BIGINT,
    int_waiting_count BIGINT,
    int_dead_count BIGINT,
    int_depend_count BIGINT,
    int_eaten_count BIGINT,
    int_succeeded_count BIGINT,
    int_running_count BIGINT,
    int_max_rss BIGINT
);

CREATE TYPE LayerStatType AS (
    int_core_time_success BIGINT,
    int_core_time_fail BIGINT,
    int_total_count BIGINT,
    int_waiting_count BIGINT,
    int_dead_count BIGINT,
    int_depend_count BIGINT,
    int_eaten_count BIGINT,
    int_succeeded_count BIGINT,
    int_running_count BIGINT,
    int_max_rss BIGINT
);


CREATE FUNCTION trigger__tbiu_layer_history()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.dt_last_modified := current_timestamp;
    RETURN NEW;
END
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER tbiu_layer_history
BEFORE INSERT OR UPDATE ON layer_history
FOR EACH ROW
EXECUTE PROCEDURE trigger__tbiu_layer_history();


CREATE FUNCTION trigger__after_job_moved()
RETURNS TRIGGER AS $body$
DECLARE
    int_core_count INT;
BEGIN
    SELECT int_cores INTO int_core_count
    FROM job_resource WHERE pk_job = NEW.pk_job;

    IF int_core_count > 0 THEN
        UPDATE folder_resource SET int_cores = int_cores + int_core_count
        WHERE pk_folder = NEW.pk_folder;

        UPDATE folder_resource  SET int_cores = int_cores - int_core_count
        WHERE pk_folder = OLD.pk_folder;
    END IF;
    RETURN NULL;
END
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER after_job_moved AFTER UPDATE ON job
FOR EACH ROW
WHEN (NEW.pk_folder != OLD.pk_folder)
EXECUTE PROCEDURE trigger__after_job_moved();


CREATE FUNCTION trigger__before_delete_job()
RETURNS TRIGGER AS $body$
DECLARE
    js JobStatType;
BEGIN
    SELECT
        job_usage.int_core_time_success,
        job_usage.int_core_time_fail,
        job_stat.int_waiting_count,
        job_stat.int_dead_count,
        job_stat.int_depend_count,
        job_stat.int_eaten_count,
        job_stat.int_succeeded_count,
        job_stat.int_running_count,
        job_mem.int_max_rss
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
        int_frame_count = OLD.int_frame_count,
        int_layer_count = OLD.int_layer_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
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

CREATE TRIGGER before_delete_job BEFORE DELETE ON job
FOR EACH ROW
EXECUTE PROCEDURE trigger__before_delete_job();


CREATE FUNCTION trigger__after_job_finished()
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
        job_stat.int_waiting_count,
        job_stat.int_dead_count,
        job_stat.int_depend_count,
        job_stat.int_eaten_count,
        job_stat.int_succeeded_count,
        job_stat.int_running_count,
        job_mem.int_max_rss
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
        int_frame_count = NEW.int_frame_count,
        int_layer_count = NEW.int_layer_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        int_ts_stopped = ts
    WHERE
        pk_job = NEW.pk_job;

    FOR one_layer IN (SELECT pk_layer from layer where pk_job = NEW.pk_job)
    LOOP
        SELECT
            layer_usage.int_core_time_success,
            layer_usage.int_core_time_fail,
            layer_stat.int_total_count,
            layer_stat.int_waiting_count,
            layer_stat.int_dead_count,
            layer_stat.int_depend_count,
            layer_stat.int_eaten_count,
            layer_stat.int_succeeded_count,
            layer_stat.int_running_count,
            layer_mem.int_max_rss
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
            int_frame_count = ls.int_total_count,
            int_waiting_count = ls.int_waiting_count,
            int_dead_count = ls.int_dead_count,
            int_depend_count = ls.int_depend_count,
            int_eaten_count = ls.int_eaten_count,
            int_succeeded_count = ls.int_succeeded_count,
            int_running_count = ls.int_running_count,
            int_max_rss = ls.int_max_rss
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

CREATE TRIGGER after_job_finished AFTER UPDATE ON job
FOR EACH ROW
WHEN (OLD.str_state = 'PENDING' AND NEW.str_state = 'FINISHED')
EXECUTE PROCEDURE trigger__after_job_finished();


CREATE FUNCTION trigger__after_insert_job()
RETURNS TRIGGER AS $body$
BEGIN
    INSERT INTO job_stat (pk_job_stat,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_resource (pk_job_resource,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_usage (pk_job_usage,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_mem (pk_job_mem,pk_job) VALUES (NEW.pk_job,NEW.pk_job);

    INSERT INTO job_history
        (pk_job, pk_show, pk_facility, pk_dept, str_name, str_shot, str_user, int_ts_started)
    VALUES
        (NEW.pk_job, NEW.pk_show, NEW.pk_facility, NEW.pk_dept,
         NEW.str_name, NEW.str_shot, NEW.str_user, epoch(current_timestamp));

    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER after_insert_job AFTER INSERT ON job
FOR EACH ROW
EXECUTE PROCEDURE trigger__after_insert_job();


CREATE FUNCTION trigger__after_job_dept_update()
RETURNS TRIGGER AS $body$
DECLARE
    int_running_cores INT;
BEGIN
  /**
  * Handles the accounting for moving a job between departments.
  **/
  SELECT int_cores INTO int_running_cores
    FROM job_resource WHERE pk_job = NEW.pk_job;

  IF int_running_cores > 0 THEN
    UPDATE point SET int_cores = int_cores + int_running_cores
        WHERE pk_dept = NEW.pk_dept AND pk_show = NEW.pk_show;

    UPDATE point SET int_cores = int_cores - int_running_cores
        WHERE pk_dept = OLD.pk_dept AND pk_show = OLD.pk_show;
  END IF;

  RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER after_job_dept_update AFTER UPDATE ON job
FOR EACH ROW
  WHEN (NEW.pk_dept != OLD.pk_dept AND new.str_state='PENDING')
  EXECUTE PROCEDURE trigger__after_job_dept_update();


CREATE FUNCTION trigger__verify_host_local()
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

    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER verify_host_local BEFORE UPDATE ON host_local
FOR EACH ROW
   WHEN ((NEW.int_cores_max = OLD.int_cores_max AND NEW.int_mem_max = OLD.int_mem_max) AND
    (NEW.int_cores_idle != OLD.int_cores_idle OR NEW.int_mem_idle != OLD.int_mem_idle))
   EXECUTE PROCEDURE trigger__verify_host_local();


CREATE FUNCTION trigger__tier_host_local()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.float_tier := tier(NEW.int_cores_max - NEW.int_cores_idle,NEW.int_cores_max);
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER tier_host_local BEFORE UPDATE ON host_local
FOR EACH ROW
    EXECUTE PROCEDURE trigger__tier_host_local();


CREATE OR REPLACE FUNCTION trigger__after_insert_layer()
RETURNS TRIGGER AS $body$
BEGIN
    INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_usage (pk_layer_usage, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_mem (pk_layer_mem, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);

    INSERT INTO layer_history
        (pk_layer, pk_job, str_name, str_type, int_cores_min, int_mem_min, b_archived,str_services)
    VALUES
        (NEW.pk_layer, NEW.pk_job, NEW.str_name, NEW.str_type, NEW.int_cores_min, NEW.int_mem_min, false, NEW.str_services);

    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER after_insert_layer AFTER INSERT ON layer
FOR EACH ROW
    EXECUTE PROCEDURE trigger__after_insert_layer();


CREATE FUNCTION trigger__before_delete_layer()
RETURNS TRIGGER AS $body$
DECLARE
    js LayerStatType;
BEGIN
    SELECT
        layer_usage.int_core_time_success,
        layer_usage.int_core_time_fail,
        layer_stat.int_total_count,
        layer_stat.int_waiting_count,
        layer_stat.int_dead_count,
        layer_stat.int_depend_count,
        layer_stat.int_eaten_count,
        layer_stat.int_succeeded_count,
        layer_stat.int_running_count,
        layer_mem.int_max_rss
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
        int_frame_count = js.int_total_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
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

CREATE TRIGGER before_delete_layer BEFORE DELETE ON layer
FOR EACH ROW
    EXECUTE PROCEDURE trigger__before_delete_layer();


CREATE FUNCTION trigger__tbiu_job_history()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.dt_last_modified := current_timestamp;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER tbiu_job_history BEFORE INSERT OR UPDATE ON job_history
FOR EACH ROW
    EXECUTE PROCEDURE trigger__tbiu_job_history();


CREATE FUNCTION trigger__verify_host_resources()
RETURNS TRIGGER AS $body$
BEGIN
    IF NEW.int_cores_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional core units';
    END IF;

    If NEW.int_mem_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional memory';
    END IF;

    If NEW.int_gpu_idle < 0 THEN
        RAISE EXCEPTION 'unable to allocate additional gpu memory';
    END IF;

    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER verify_host_resources BEFORE UPDATE ON host
FOR EACH ROW
   WHEN (NEW.int_cores_idle != OLD.int_cores_idle OR NEW.int_mem_idle != OLD.int_mem_idle)
   EXECUTE PROCEDURE trigger__verify_host_resources();


CREATE FUNCTION trigger__before_delete_host()
RETURNS TRIGGER AS $body$
BEGIN
    DELETE FROM host_stat WHERE pk_host = OLD.pk_host;
    DELETE FROM host_tag WHERE pk_host = OLD.pk_host;
    DELETE FROM deed WHERE pk_host = OLD.pk_host;
    RETURN OLD;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER before_delete_host BEFORE DELETE ON host
FOR EACH ROW
    EXECUTE PROCEDURE trigger__before_delete_host();


CREATE FUNCTION trigger__verify_job_resources()
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
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER verify_job_resources BEFORE UPDATE ON job_resource
FOR EACH ROW
  WHEN (NEW.int_max_cores = OLD.int_max_cores AND NEW.int_cores > OLD.int_cores)
  EXECUTE PROCEDURE trigger__verify_job_resources();


CREATE FUNCTION trigger__tier_job()
RETURNS TRIGGER AS $body$
BEGIN
    /** calculates new tier **/
    NEW.float_tier := tier(NEW.int_cores, NEW.int_min_cores);
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER tier_job BEFORE UPDATE ON job_resource
FOR EACH ROW
    EXECUTE PROCEDURE trigger__tier_job();


CREATE FUNCTION trigger__verify_job_local()
RETURNS TRIGGER AS $body$
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * when people lower the max.
    **/
    IF NEW.int_cores > NEW.int_max_cores THEN
        RAISE EXCEPTION 'job local has exceeded max cores';
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER verify_job_local BEFORE UPDATE ON job_local
FOR EACH ROW
  WHEN (NEW.int_max_cores = OLD.int_max_cores AND NEW.int_cores > OLD.int_cores)
  EXECUTE PROCEDURE trigger__verify_job_local();


CREATE FUNCTION trigger__tier_folder()
RETURNS TRIGGER AS $body$
BEGIN
    /** calculates new tier **/
    NEW.float_tier := soft_tier(NEW.int_cores, NEW.int_min_cores);
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER tier_folder BEFORE UPDATE ON folder_resource
FOR EACH ROW
EXECUTE PROCEDURE trigger__tier_folder();


CREATE FUNCTION trigger__before_delete_folder()
RETURNS TRIGGER AS $body$
BEGIN
    DELETE FROM folder_level WHERE pk_folder = OLD.pk_folder;
    DELETE FROM folder_resource WHERE pk_folder = OLD.pk_folder;
    RETURN OLD;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER before_delete_folder BEFORE DELETE ON folder
FOR EACH ROW
EXECUTE PROCEDURE trigger__before_delete_folder();


CREATE FUNCTION trigger__after_insert_folder()
RETURNS TRIGGER AS $body$
DECLARE
    int_level INT := 0;
BEGIN
    IF NEW.pk_parent_folder IS NOT NULL THEN
        SELECT folder_level.int_level + 1 INTO int_level FROM folder_level WHERE pk_folder = NEW.pk_parent_folder;
    END IF;
    INSERT INTO folder_level (pk_folder_level, pk_folder, int_level) VALUES (NEW.pk_folder, NEW.pk_folder, int_level);
    INSERT INTO folder_resource (pk_folder_resource, pk_folder) VALUES (NEW.pk_folder, NEW.pk_folder);
    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER after_insert_folder AFTER INSERT ON folder
FOR EACH ROW
EXECUTE PROCEDURE trigger__after_insert_folder();


CREATE FUNCTION trigger__before_insert_folder()
RETURNS TRIGGER AS $body$
BEGIN
    IF NEW.pk_parent_folder IS NULL THEN
        NEW.b_default := 1;
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER before_insert_folder BEFORE INSERT ON folder
FOR EACH ROW
EXECUTE PROCEDURE trigger__before_insert_folder();


CREATE FUNCTION trigger__before_insert_proc()
RETURNS TRIGGER AS $body$
BEGIN
    IF NEW.int_cores_reserved <= 0 THEN
        RAISE EXCEPTION 'failed to allocate proc, tried to allocate 0 cores';
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER before_insert_proc BEFORE INSERT ON proc
FOR EACH ROW
EXECUTE PROCEDURE trigger__before_insert_proc();


CREATE FUNCTION trigger__update_proc_update_layer()
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
          int_cores = int_cores - OLD.int_cores_reserved
        WHERE
          pk_layer = OLD.pk_layer;

      ELSE

        UPDATE layer_resource SET
          int_cores = int_cores + NEW.int_cores_reserved
       WHERE
          pk_layer = NEW.pk_layer;
       END IF;

    END LOOP;
    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER update_proc_update_layer AFTER UPDATE ON proc
FOR EACH ROW
  WHEN (NEW.pk_layer != OLD.pk_layer)
  EXECUTE PROCEDURE trigger__update_proc_update_layer();


CREATE FUNCTION trigger__upgrade_proc_memory_usage()
RETURNS TRIGGER AS $body$
BEGIN
    UPDATE host SET
        int_mem_idle = int_mem_idle - (NEW.int_mem_reserved - OLD.int_mem_reserved)
    WHERE
        pk_host = NEW.pk_host;
    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER upgrade_proc_memory_usage AFTER UPDATE ON proc
FOR EACH ROW
  WHEN (NEW.int_mem_reserved != OLD.int_mem_reserved)
  EXECUTE PROCEDURE trigger__upgrade_proc_memory_usage();


CREATE FUNCTION trigger__update_frame_wait_to_dep()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.str_state := 'DEPEND';
    NEW.ts_updated := current_timestamp;
    NEW.int_version := NEW.int_version + 1;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER update_frame_wait_to_dep BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (NEW.int_depend_count > 0 AND NEW.str_state IN ('DEAD','SUCCEEDED','WAITING','CHECKPOINT'))
  EXECUTE PROCEDURE trigger__update_frame_wait_to_dep();


CREATE FUNCTION trigger__update_frame_eaten()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.str_state := 'SUCCEEDED';
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER update_frame_eaten BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (NEW.str_state = 'EATEN' AND OLD.str_state = 'SUCCEEDED')
  EXECUTE PROCEDURE trigger__update_frame_eaten();


CREATE FUNCTION trigger__update_frame_dep_to_wait()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.str_state := 'WAITING';
    NEW.ts_updated := current_timestamp;
    NEW.int_version := NEW.int_version + 1;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER update_frame_dep_to_wait BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (OLD.int_depend_count > 0 AND NEW.int_depend_count < 1 AND OLD.str_state='DEPEND')
  EXECUTE PROCEDURE trigger__update_frame_dep_to_wait();


CREATE FUNCTION trigger__frame_history_open()
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
              int_ts_stopped=$2,
              int_exit_status=$3,
              int_checkpoint_count=$4
          WHERE
              int_ts_stopped = 0 AND pk_frame=$5'
          USING
              NEW.int_mem_max_used,
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
            str_host,
            int_ts_started,
            pk_alloc
         )
         VALUES
            ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)'
         USING NEW.pk_frame,
            NEW.pk_layer,
            NEW.pk_job,
            NEW.str_name,
            'RUNNING',
            NEW.int_cores,
            NEW.int_mem_reserved,
            NEW.str_host,
            epoch(current_timestamp),
            str_pk_alloc;
    END IF;
    RETURN NULL;

END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER frame_history_open AFTER UPDATE ON frame
FOR EACH ROW
   WHEN (NEW.str_state != OLD.str_state)
   EXECUTE PROCEDURE trigger__frame_history_open();


CREATE FUNCTION trigger__update_frame_checkpoint_state()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.str_state := 'CHECKPOINT';
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER update_frame_checkpoint_state BEFORE UPDATE ON frame
FOR EACH ROW
  WHEN (NEW.str_state = 'WAITING' AND OLD.str_state = 'RUNNING' AND NEW.str_checkpoint_state IN ('ENABLED', 'COPYING'))
  EXECUTE PROCEDURE trigger__update_frame_checkpoint_state();


CREATE FUNCTION trigger__update_frame_status_counts()
RETURNS TRIGGER AS $body$
DECLARE
    s_old_status_col VARCHAR(32);
    s_new_status_col VARCHAR(32);
BEGIN
    s_old_status_col := 'int_' || OLD.str_state || '_count';
    s_new_status_col := 'int_' || NEW.str_state || '_count';
    EXECUTE 'UPDATE layer_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_layer=$1' USING NEW.pk_layer;

    EXECUTE 'UPDATE job_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_job=$1' USING NEW.pk_job;
    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER update_frame_status_counts AFTER UPDATE ON frame
FOR EACH ROW
  WHEN (old.str_state != 'SETUP' AND old.str_state != new.str_state)
  EXECUTE PROCEDURE trigger__update_frame_status_counts();


CREATE FUNCTION trigger__verify_subscription()
RETURNS TRIGGER AS $body$
BEGIN
    /**
    * Check to see if adding more procs will push the show over
    * its subscription size.  This check is only done when
    * new.int_burst = old.int_burst and new.int_cores > old.int cores,
    * otherwise this error would be thrown at the wrong time.
    **/
    IF NEW.int_cores > NEW.int_burst THEN
        RAISE EXCEPTION 'subscription has exceeded burst size';
    END IF;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER verify_subscription BEFORE UPDATE ON subscription
FOR EACH ROW
  WHEN (NEW.int_burst = OLD.int_burst AND NEW.int_cores > OLD.int_cores)
  EXECUTE PROCEDURE trigger__verify_subscription();


CREATE FUNCTION trigger__tier_subscription()
RETURNS TRIGGER AS $body$
BEGIN
    /* calcultes a soft tier */
    NEW.float_tier := tier(NEW.int_cores, NEW.int_size);
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER tier_subscription BEFORE UPDATE ON subscription
FOR EACH ROW
EXECUTE PROCEDURE trigger__tier_subscription();


CREATE FUNCTION trigger__point_tier()
RETURNS TRIGGER AS $body$
BEGIN
    /* calcultes a soft tier */
    NEW.float_tier := soft_tier(NEW.int_cores, NEW.int_min_cores);
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER point_tier BEFORE UPDATE ON point
FOR EACH ROW
EXECUTE PROCEDURE trigger__point_tier();


CREATE FUNCTION trigger__tbiu_frame_history()
RETURNS TRIGGER AS $body$
BEGIN
    NEW.dt_last_modified := current_timestamp;
    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;

CREATE TRIGGER tbiu_frame_history BEFORE INSERT OR UPDATE ON frame_history
FOR EACH ROW
EXECUTE PROCEDURE trigger__tbiu_frame_history();
