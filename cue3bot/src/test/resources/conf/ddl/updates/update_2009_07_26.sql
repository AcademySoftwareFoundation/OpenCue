/*
* This trigger is replaced by jobDao.updateUsage and layerDao.updateUsage
*/
DROP TRIGGER CUE3.UPDATE_LAYER_USAGE;

/**
* These triggers are now handled in the ProcDao
**/
DROP TRIGGER CUE3.PROC_DELETE;
DROP TRIGGER CUE3.PROC_INSERT;

/**
* The dispatcher attempts to set this column to true when
* marking the frame to be dispatched.
**/
ALTER TABLE frame ADD b_reserved NUMBER(1,0) DEFAULT 0 NOT NULL;
CREATE INDEX i_frame_reserved ON FRAME (str_state, b_reserved);

/**
* A boolean that determines of the depend is a regular or composite
* depend. A composite depend is made up of many depends.
**/
ALTER TABLE depend ADD b_composite NUMBER(1,0) DEFAULT 0 NOT NULL;
update depend SET b_composite = 1 WHERE str_type='FrameByFrame';

/**
* The order of updates must be guaranteed.
**/
create or replace
TRIGGER "CUE3".update_proc_update_layer AFTER UPDATE ON proc
FOR EACH ROW
WHEN (new.pk_layer != old.pk_layer)
BEGIN
     FOR lr IN (
        SELECT
          pk_layer
        FROM
          layer_stat
        WHERE
          pk_layer IN (:old.pk_layer,:new.pk_layer)
        ORDER BY layer_stat.pk_layer DESC
        ) LOOP

      IF lr.pk_layer = :old.pk_layer THEN

        UPDATE layer_resource SET
          int_cores = int_cores - :old.int_cores_reserved
        WHERE
          pk_layer = :old.pk_layer;

      ELSE

        UPDATE layer_resource SET
          int_cores = int_cores + :new.int_cores_reserved
       WHERE
          pk_layer = :new.pk_layer;
       END IF;

    END LOOP;
END;

/**
* Update to copy the memory value over right after the job is completed.
**/
create or replace
TRIGGER "CUE3".after_job_finished AFTER UPDATE ON job
FOR EACH ROW
WHEN (old.str_state = 'Pending' AND new.str_state = 'Finished')
DECLARE
    ts NUMERIC(12,0) := epoch(systimestamp);
BEGIN
    /* Sets the job history stop time */
    UPDATE
      job_history
    SET
      int_ts_stopped = ts,
      int_max_rss = (SELECT int_max_rss FROM job_mem WHERE pk_job = :new.pk_job)
    WHERE
      pk_job=:new.pk_job;
    UPDATE frame_history SET int_ts_stopped = ts
      WHERE pk_job=:new.pk_job AND str_state='Waiting' AND int_ts_stopped=0;
END;
