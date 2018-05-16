/*
* Add a seperate version column for the frame table.
*/
ALTER TABLE frame ADD int_version NUMERIC(16,0) DEFAULT 0 NOT NULL;

/**
* Fix timestamp for job updated time.
**/
ALTER TABLE job ADD ts_updated_new TIMESTAMP WITH TIME ZONE DEFAULT systimestamp NOT NULL;
UPDATE job SET ts_updated_new = ts_updated;
ALTER TABLE job RENAME COLUMN ts_updated TO ts_updated_old;
ALTER TABLE job RENAME COLUMN ts_updated_new TO ts_updated;
ALTER TABLE job DROP COLUMN ts_updated_old;


/**
* Fix all timestamps on Proc table. 
**/
ALTER TABLE proc ADD ts_ping_new TIMESTAMP WITH TIME ZONE DEFAULT systimestamp NOT NULL;
ALTER TABLE proc ADD ts_booked_new TIMESTAMP WITH TIME ZONE DEFAULT systimestamp NOT NULL;
ALTER TABLE proc ADD ts_dispatched_new TIMESTAMP WITH TIME ZONE DEFAULT systimestamp NOT NULL;

UPDATE proc set ts_ping_new=ts_ping, ts_booked_new=ts_booked, ts_dispatched_new=ts_dispatched;

ALTER TABLE proc RENAME COLUMN ts_ping TO ts_ping_old;
ALTER TABLE proc RENAME COLUMN ts_booked TO ts_booked_old;
ALTER TABLE proc RENAME COLUMN ts_dispatched TO ts_dispatched_old;

ALTER TABLE proc RENAME COLUMN ts_ping_new TO ts_ping;
ALTER TABLE proc RENAME COLUMN ts_booked_new TO ts_booked;
ALTER TABLE proc RENAME COLUMN ts_dispatched_new TO ts_dispatched;

ALTER TABLE proc DROP COLUMN ts_ping_old;
ALTER TABLE proc DROP COLUMN ts_booked_old;
ALTER TABLE proc DROP COLUMN ts_dispatched_old;


/**
* Update the version of the frame.
**/
create or replace
TRIGGER "CUE3".update_frame_dep_to_wait BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (OLD.int_depend_count > 0 AND NEW.int_depend_count < 1 AND OLD.str_state='Depend')
BEGIN
    :NEW.str_state := 'Waiting';
    :NEW.ts_updated := systimestamp;
    :NEW.int_version := :NEW.int_version + 1;
END;

/**
* Update the version of the frame.
**/
create or replace
TRIGGER "CUE3".update_frame_wait_to_dep BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (NEW.int_depend_count > 0 AND NEW.str_state IN ('Dead','Succeeded','Waiting'))
BEGIN
    :NEW.str_state := 'Depend';
    :NEW.ts_updated := systimestamp;
    :NEW.int_version := :NEW.int_version + 1;
END;

