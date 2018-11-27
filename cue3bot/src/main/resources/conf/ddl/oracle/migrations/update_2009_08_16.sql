
/**
* Chanaged to update all historical frames without a stop time,
* not just the waiting ones.
*
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

END;


CREATE OR REPLACE TRIGGER verify_job_resources BEFORE UPDATE ON job_resource
FOR EACH ROW
WHEN ( NEW.int_max_cores = OLD.int_max_cores AND NEW.int_cores > OLD.int_cores)
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * at the wrong time.
    **/
    IF :NEW.int_cores > :NEW.int_max_cores THEN
        Raise_application_error(-20021, 'job has exceeded max cores');
    END IF;
END;

CREATE OR REPLACE TRIGGER verify_subscription BEFORE UPDATE ON subscription
FOR EACH ROW
WHEN ( NEW.int_burst = OLD.int_burst AND NEW.int_cores > OLD.int_cores)
BEGIN
    /**
    * Check to see if adding more procs will push the show over
    * its subscription size.  This check is only done when
    * new.int_burst = old.int_burst and new.int_cores > old.int cores,
    * otherwise this error would be thrown at the wrong time.
    **/
    IF :NEW.int_cores > :NEW.int_burst THEN
        Raise_application_error(-20022, 'subscription has exceeded burst size');
    END IF;
END;

/**
* This trigger would ensure frames that failed immediatly would
* have at least 1 second of render time, but, we actually want
* them to have 0 seconds of render time.
**/
DROP TRIGGER frame_history_fix_time;

/**
* Drop b_reserved
**
DROP INDEX i_frame_reserved;
ALTER TABLE frame DROP COLUMN b_reserved;

/** Dependency table index fixes **/
DROP INDEX i_depend_sig;
DROP INDEX i_depend_er_frame;
DROP INDEX i_depend_on_frame;
DROP INDEX i_depend_on_layer;
DROP INDEX i_depend_er_layer;
DROP INDEX i_depend_pk_on_frame;
DROP INDEX i_depend_pk_on_layer;

CREATE UNIQUE INDEX i_depend_signature ON depend (str_signature);

CREATE INDEX i_depend_on_layer ON depend (pk_layer_depend_on);
CREATE INDEX i_depend_er_layer ON depend (pk_layer_depend_er);

CREATE INDEX i_depend_on_frame ON depend (pk_frame_depend_on);
CREATE INDEX i_depend_er_frame ON depend (pk_frame_depend_er);

CREATE INDEX i_depend_b_composite ON depend (b_composite);
