
/** Down day SQL **/

/*
* Dropping these indexes on depend.
*/
DROP INDEX i_depend_pkjobdependon;
DROP INDEX i_depend_pkjobdepender;
DROP INDEX i_depend_pkframedependon;
DROP INDEX i_depend_pklayerdependon;
DROP INDEX i_depend_b_active;

/**
* Creating these index which give me faster lookups.
**/
CREATE INDEX i_depend_on_layer ON cue3.depend (pk_job_depend_on, pk_layer_depend_on);
CREATE INDEX i_depend_on_frame ON cue3.depend (pk_job_depend_on, pk_frame_depend_on);
CREATE INDEX i_depend_er_layer ON cue3.depend (pk_job_depend_er, pk_layer_depend_er);
CREATE INDEX i_depend_er_frame ON cue3.depend (pk_job_depend_er, pk_frame_depend_er);

/**
* Create a signature column for ensuring the depends are unique.  It can't
* be used as a PK because people re-create dependencies sometimes during
* development or troubleshooting.
**/
ALTER TABLE depend ADD str_signature VARCHAR2(36);
UPDATE depend SET str_signature = pk_depend;
ALTER TABLE depend MODIFY (str_signature VARCHAR2(36) NOT NULL);

CREATE UNIQUE INDEX i_depend_sig ON cue3.depend (b_active, str_signature);

/** Dropping old historical columns **/
DROP INDEX I_FRAME_HISTORY_TS_STARTED;
DROP INDEX I_FRAME_HISTORY_TS_STOPPED;

ALTER TABLE frame_history DROP COLUMN ts_started;
ALTER TABLE frame_history DROP COLUMN ts_stopped;

/**
* Trigger handles setting a frame state to depend if the
* depend count > 0.
**/
create or replace
TRIGGER "CUE3".update_frame_wait_to_dep BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (NEW.int_depend_count > 0  AND NEW.str_state = 'Waiting')
BEGIN
    :NEW.str_state := 'Depend';
    :NEW.ts_updated := systimestamp;
END;

/**
* This is now handled by the application.
**/
drop trigger update_satisfy_frame_depend;

/**
* Redundant
**/
DROP TRIGGER update_frame_waiting;



