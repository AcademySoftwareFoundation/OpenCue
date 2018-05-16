
/**
* Cue Job history
*
**/
CREATE TABLE job_history (
    pk_job                  VARCHAR(36) NOT NULL,
    pk_show                 VARCHAR(36) NOT NULL,
    pk_facility             VARCHAR2(36) NOT NULL,
    pk_dept                 VARCHAR2(36) NOT NULL,
    str_name                VARCHAR2(512) NOT NULL,
    str_shot                VARCHAR2(36) NOT NULL,
    str_user                VARCHAR2(36) NOT NULL,
    str_folder              VARCHAR2(256) NOT NULL,
    int_ts_started          NUMERIC(12,0) NOT NULL,
    int_ts_started          NUMERIC(12,0) DEFAULT 0 NOT NULL,
    int_proc_seconds        NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_proc_seconds_lost   NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_frame_count         NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_layer_count         NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_waiting_count       NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_dead_count          NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_depend_count        NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_eaten_count         NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_succeeded_count     NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_running_count       NUMERIC(38,0) DEFAULT 0 NOT NULL,
    int_max_rss             NUMERIC(38,0) DEFAULT 0 NOT NULL,
    b_archived              NUMERIC(1) DEFAULT 0 NOT NULL,
);

ALTER TABLE cue3.job_history
    ADD CONSTRAINT c_job_history_pk PRIMARY KEY (pk_job);

CREATE INDEX i_job_history_pk_show ON cue3.job_history (pk_show);
ALTER TABLE cue3.job_history ADD CONSTRAINT c_job_history_pk_show
    FOREIGN KEY (pk_show) REFERENCES show (pk_show);

CREATE INDEX i_job_history_pk_facility ON cue3.job_history (pk_facility);
ALTER TABLE cue3.job_history ADD CONSTRAINT c_job_history_pk_facility
    FOREIGN KEY (pk_facility) REFERENCES show (pk_facility);

CREATE INDEX i_job_history_pk_dept ON cue3.job_history (pk_dept);
ALTER TABLE cue3.job_history ADD CONSTRAINT c_job_history_pk_dept
    FOREIGN KEY (pk_dept) REFERENCES show (pk_dept);

CREATE INDEX i_job_history_str_name ON cue3.job_history (str_name);
CREATE INDEX i_job_history_str_shot ON cue3.job_history (str_shot); 
CREATE INDEX i_job_history_str_user ON cue3.job_history (str_user);
CREATE INDEX i_job_history_str_folder ON cue3.job_history (str_folder);
CREATE INDEX i_job_history_b_archived ON job_history(b_archived);

CREATE INDEX i_job_history_start_stop ON cue3.job_history (int_ts_started, int_ts_stopped);

/**
* Layer History
*
**/
CREATE TABLE layer_history (
    pk_layer                VARCHAR(36) NOT NULL,
    pk_job                  VARCHAR(36) NOT NULL,
    str_name                VARCHAR2(512) NOT NULL,
    str_type                VARCHAR2(16) NOT NULL,
    str_range               VARCHAR2(4000) NOT NULL,
    int_cores_min           NUMBER(38) DEFAULT 100 NOT NULL,
    int_mem_min             NUMBER(38) DEFAULT 4194304 NOT NULL,
    int_proc_seconds        NUMERIC(38,0) NOT NULL,
    int_proc_seconds_lost   NUMERIC(38,0) NOT NULL,
    int_frame_count         NUMERIC(38,0) NOT NULL,
    int_layer_count         NUMERIC(38,0) NOT NULL,
    int_waiting_count       NUMERIC(38,0) NOT NULL,
    int_dead_count          NUMERIC(38,0) NOT NULL,
    int_depend_count        NUMERIC(38,0) NOT NULL,
    int_eaten_count         NUMERIC(38,0) NOT NULL,
    int_succeeded_count     NUMERIC(38,0) NOT NULL,
    int_running_count       NUMERIC(38,0) NOT NULL,
    int_max_rss             NUMERIC(38,0) NOT NULL,
    b_archived              NUMERIC(1) DEFAULT 0 NOT NULL
);

ALTER TABLE cue3.layer_history
    ADD CONSTRAINT c_layer_history_pk PRIMARY KEY (pk_layer);

ALTER TABLE cue3.layer_history ADD CONSTRAINT c_layer_history_pk_job
    FOREIGN KEY (pk_job) REFERENCES job_history (pk_job) ON DELETE CASCADE;

CREATE INDEX i_layer_history_str_name ON cue3.layer_history (str_name);
CREATE INDEX i_layer_history_str_type ON cue3.layer_history (str_type);
CREATE INDEX i_layer_history_pk_job ON cue3.layer_history (pk_job);

CREATE INDEX i_layer_history_b_archived ON layer_history(b_archived);

/**
* Frame History
*
**/
CREATE TABLE frame_history (
    pk_frame_history        RAW(16) DEFAULT sys_guid() NOT NULL,
    pk_frame                VARCHAR(36) NOT NULL,
    pk_layer                VARCHAR(36) NOT NULL,
    pk_job                  VARCHAR(36) NOT NULL,
    pk_alloc                VARCHAR(36),
    str_name                VARCHAR2(256) NOT NULL,
    str_state               VARCHAR2(24) NOT NULL,
    str_host                VARCHAR2(64) NOT NULL,
    int_ts_started          NUMERIC(12) NOT NULL,
    int_ts_stopped          NUMERIC(12) DEFAULT NOT NULL,
    int_mem_reserved        NUMERIC(38) DEFAULT 0 NOT NULL,
    int_mem_max_used        NUMERIC(38) DEFAULT 0 NOT NULL,
    int_exit_status         NUMERIC(9) DEFAULT -1 NOT NULL,
    int_cores               NUMERIC(9) DEFAULT 100 NOT NULL
);

ALTER TABLE cue3.frame_history
    ADD CONSTRAINT c_frame_history_pk PRIMARY KEY (pk_frame_history);

CREATE INDEX i_frame_history_pk_frame ON cue3.frame_history (pk_frame);

CREATE INDEX i_frame_history_pk_job ON cue3.frame_history (pk_job);
ALTER TABLE cue3.frame_history ADD CONSTRAINT c_frame_history_pk_job
    FOREIGN KEY (pk_job) REFERENCES job_history (pk_job) ON DELETE CASCADE;

CREATE INDEX i_frame_history_pk_layer ON cue3.frame_history (pk_layer);
ALTER TABLE cue3.frame_history ADD CONSTRAINT c_frame_history_pk_layer
    FOREIGN KEY (pk_layer) REFERENCES layer_history (pk_layer) ON DELETE CASCADE;

CREATE INDEX i_frame_history_str_state ON cue3.frame_history (str_state);
CREATE INDEX i_frame_history_start_stop ON cue3.frame_history (int_ts_started, int_ts_stopped);
CREATE INDEX i_frame_history_exit_stat ON cue3.frame_history (int_exit_status);



