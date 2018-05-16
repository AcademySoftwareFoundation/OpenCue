
/*
* Max cores support.
**/
ALTER TABLE layer ADD int_cores_max NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE service ADD int_cores_max NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE show_service ADD int_cores_max NUMBER(10) DEFAULT 0 NOT NULL;

/**
* Output registration support.
**/
CREATE TABLE layer_output (
  pk_layer_output VARCHAR2(36) NOT NULL,
  pk_layer  VARCHAR2(36) NOT NULL,
  pk_job  VARCHAR2(36) NOT NULL,
  str_filespec VARCHAR(2048) NOT NULL
);
ALTER TABLE cue3.layer_output
    ADD CONSTRAINT c_pk_layer_output PRIMARY KEY (pk_layer_output);

ALTER TABLE cue3.layer_output ADD CONSTRAINT c_layer_output_pk_layer
  FOREIGN KEY (pk_layer) REFERENCES layer (pk_layer);
ALTER TABLE cue3.layer_output ADD CONSTRAINT c_layer_output_pk_job
  FOREIGN KEY (pk_job) REFERENCES job (pk_job);

CREATE INDEX i_layer_output_pk_layer ON cue3.layer_output (pk_layer);
CREATE INDEX i_layer_output_pk_job ON cue3.layer_output (pk_job);
CREATE UNIQUE INDEX i_layer_output_unique ON cue3.layer_output (pk_layer, str_filespec);

/**
* Update trigger to delete outputs
**/
create or replace
TRIGGER "CUE3".before_delete_layer BEFORE DELETE ON layer
FOR EACH ROW
DECLARE
    TYPE StatType IS RECORD (
        int_core_time_success NUMERIC(38),
        int_core_time_fail NUMERIC(38),
        int_total_count NUMERIC(38),
        int_waiting_count NUMERIC(38),
        int_dead_count NUMERIC(38),
        int_depend_count NUMERIC(38),
        int_eaten_count NUMERIC(38),
        int_succeeded_count NUMERIC(38),
        int_running_count NUMERIC(38),
        int_max_rss NUMERIC(38)
    );
    js StatType;

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
        layer_mem.pk_layer = :old.pk_layer;   
    
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
        b_archived = 1
    WHERE
        pk_layer = :old.pk_layer;

    delete from layer_resource where pk_layer=:old.pk_layer;
    delete from layer_stat where pk_layer=:old.pk_layer;
    delete from layer_usage where pk_layer=:old.pk_layer;
    delete from layer_env where pk_layer=:old.pk_layer;
    delete from layer_mem where pk_layer=:old.pk_layer;
    delete from layer_output where pk_layer=:old.pk_layer;
END;

/**
* Email comment support
**/
ALTER TABLE show ADD str_comment_email VARCHAR2(1024);


/**
* A add column to support the checkpoint state value
**/
ALTER TABLE frame ADD str_checkpoint_state VARCHAR2(12) DEFAULT 'Disabled' NOT NULL;
ALTER TABLE frame ADD int_checkpoint_count NUMERIC(6) DEFAULT 0 NOT NULL;

/**
* A couple cols to store the nunmber of frames in the Checkpoint state.
**/
ALTER TABLE job_stat ADD int_checkpoint_count NUMBER(38) DEFAULT 0 NOT NULL;
ALTER TABLE layer_stat ADD int_checkpoint_count NUMBER(38) DEFAULT 0 NOT NULL;

/**
* Intercepts setting a frame to Waiting if checkpoint is enabled and rewrites
* the state to checkpoint.
**/
create or replace
TRIGGER "CUE3".update_frame_checkpoint_state BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (NEW.str_state='Waiting' AND OLD.str_state='Running' AND NEW.str_checkpoint_state IN ('Enabled', 'Copying'))
BEGIN
    :NEW.str_state :='Checkpoint';
END;

/**
* Make sure frames doing to depend don't go to checkpoint state instead.
**/
create or replace
TRIGGER "CUE3".update_frame_wait_to_dep BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (NEW.int_depend_count > 0 AND NEW.str_state IN ('Dead','Succeeded','Waiting','Checkpoint'))
BEGIN
    :NEW.str_state := 'Depend';
    :NEW.ts_updated := systimestamp;
    :NEW.int_version := :NEW.int_version + 1;
END;

/**
* add a new maintenance task.
**/
Insert into TASK_LOCK (PK_TASK_LOCK,STR_NAME,INT_LOCK,INT_TIMEOUT) values ('00000000-0000-0000-0000-000000000010','LOCK_STALE_CHECKPOINT',0,300);

