

ALTER TABLE frame ADD ts_started_new TIMESTAMP WITH TIME ZONE;
ALTER TABLE frame ADD ts_stopped_new TIMESTAMP WITH TIME ZONE;
ALTER TABLE frame ADD ts_last_run_new TIMESTAMP WITH TIME ZONE;
ALTER TABLE frame ADD ts_updated_new TIMESTAMP WITH TIME ZONE;

ALTER TABLE frame rename column ts_started to ts_started_old;
ALTER TABLE frame rename column ts_stopped to ts_stopped_old;
ALTER TABLE frame rename column ts_last_run to ts_last_run_old;
ALTER TABLE frame rename column ts_updated to ts_updated_old;

ALTER TABLE frame rename column ts_started_new to ts_started;
ALTER TABLE frame rename column ts_stopped_new to ts_stopped;
ALTER TABLE frame rename column ts_last_run_new to ts_last_run;
ALTER TABLE frame rename column ts_updated_new to ts_updated;

/**
* Update timestamps with old values. Timezone automatically applied.
**/
UPDATE frame SET ts_started=ts_started_old, ts_stopped=ts_stopped_old;

/**
* Create a table to handle local core assignments from users.
**/
CREATE TABLE job_local (
    pk_job_local        VARCHAR2(36) NOT NULL,
    pk_job              VARCHAR2(36) NOT NULL,
    pk_host             VARCHAR2(36) NOT NULL,
    str_source          VARCHAR2(255) NOT NULL,
    ts_created          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL ,
    int_cores           NUMBER(16,0) DEFAULT 0 NOT NULL,
    int_max_cores       NUMBER(16,0) NOT NULL
);

ALTER TABLE job_local
    ADD CONSTRAINT c_pk_job_local PRIMARY KEY (pk_job_local);
CREATE UNIQUE INDEX i_job_local_pk_job ON job_local (pk_job);
CREATE UNIQUE INDEX i_job_local_pk_host ON job_local (pk_host);

ALTER TABLE job_local ADD CONSTRAINT c_job_local_pk_job 
FOREIGN KEY (pk_job) REFERENCES job (pk_job);

ALTER TABLE job_local ADD CONSTRAINT c_job_local_pk_host
FOREIGN KEY (pk_host) REFERENCES host (pk_host);

/**
* Verifies that we don't book more procs than job_local allows.
**/

create or replace TRIGGER verify_job_local BEFORE UPDATE ON job_local
FOR EACH ROW
WHEN ( NEW.int_max_cores = OLD.int_max_cores AND NEW.int_cores > OLD.int_cores)
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * when people lower the max.
    **/
    IF :NEW.int_cores > :NEW.int_max_cores THEN
        Raise_application_error(-20021, 'job local has exceeded max cores');
    END IF;
END;


/**
* Add column to proc so we know which procs are locally booked by the user.
**/
ALTER TABLE proc ADD b_local NUMBER(1,0) DEFAULT 0 NOT NULL;


/**
* Added DELETE so when a job finish any local proc assignements are deleted.
**/
create or replace TRIGGER "CUE3".after_job_finished AFTER UPDATE ON job
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
  
  /**
  * Delete any local core assignements from this job.
  **/
  DELETE FROM job_local WHERE pk_job=:new.pk_job;

END;
