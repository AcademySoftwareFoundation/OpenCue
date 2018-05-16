
/**
* Changes for moving alloc under facility.
**/
ALTER TABLE alloc ADD pk_facility VARCHAR2(36);

ALTER TABLE alloc ADD CONSTRAINT c_alloc_pk_facility
FOREIGN KEY (pk_facility) REFERENCES facility (pk_facility);

UPDATE alloc SET pk_facility = 'AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA1';
UPDATE alloc SET pk_facility = 'AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAA2' WHERE str_name LIKE '%ABQ%';

/**
* The allocation name was unique, that is no longer possible.
**/
DROP INDEX c_alloc_name_uniq;
CREATE UNIQUE INDEX i_alloc_facility_name ON alloc (str_name, pk_facility);
CREATE INDEX i_alloc_pk_facility ON alloc (pk_facility);

/** Now change the facility to not null. **/
ALTER TABLE alloc MODIFY (pk_facility VARCHAR2(36) NOT NULL);

DROP INDEX i_host_pk_facility;
ALTER TABLE host DROP COLUMN pk_facility;

/** Name is now being automatically generated **/
ALTER TABLE subscription DROP COLUMN str_name;

/**
* This field will stop allocations from appearing in the allocation list
* returned to the user.  People have created a bunch of useless allocations
* that cannot be deleted.
**/

ALTER TABLE alloc ADD b_enabled NUMERIC(1,0) DEFAULT 1;

/**
* This field will stop shows from showing up in the show list.
**/
ALTER TABLE show ADD b_active NUMERIC(1,0) DEFAULT 1 NOT NULL;

/**
* Keeps a count of local cores.
**/
ALTER TABLE job_resource ADD int_local_cores NUMERIC(16,0) DEFAULT 0 NOT NULL;

/**
* Delete any deeds on the host.
**/
create or replace
TRIGGER "CUE3".before_delete_host BEFORE DELETE ON host
FOR EACH ROW
BEGIN
    delete from host_stat WHERE pk_host = :old.pk_host;
    delete from host_tag WHERE pk_host = :old.pk_host;
    delete from deed WHERE pk_host = :old.pk_host;
END;

/**
* Temp utility method to rename all allocs.
**/
create or replace
PROCEDURE rename_allocs
IS
BEGIN
    FOR alloc IN (SELECT alloc.pk_alloc, alloc.str_name AS aname,facility.str_name AS fname FROM alloc,facility
        WHERE alloc.pk_facility = facility.pk_facility) LOOP
        EXECUTE IMMEDIATE 'UPDATE alloc SET str_name=:1 WHERE pk_alloc=:2' USING
            alloc.fname || '.' || alloc.aname, alloc.pk_alloc;
    END LOOP;
END;

/**
* Much simplified historical frame.
**/
create or replace
TRIGGER "FRAME_HISTORY_OPEN" AFTER UPDATE ON frame
FOR EACH ROW
 WHEN (NEW.str_state != OLD.str_state) DECLARE
  str_pk_alloc VARCHAR2(36) := null;
BEGIN

    IF :old.str_state = 'Running' THEN

        IF :new.int_exit_status = 299 THEN

          EXECUTE IMMEDIATE
          'DELETE FROM
              frame_history
          WHERE
              int_ts_stopped = 0 AND pk_frame=:1'
          USING
            :new.pk_frame;

        ELSE

          EXECUTE IMMEDIATE
          'UPDATE
              frame_history
          SET
              int_mem_max_used=:1,
              int_ts_stopped=:2,
              int_exit_status=:3
          WHERE
              int_ts_stopped = 0 AND pk_frame=:4'
          USING
              :new.int_mem_max_used,
              epoch(systimestamp),
              :new.int_exit_status,
              :new.pk_frame;
        END IF;
    END IF;

    IF :new.str_state = 'Running' THEN

      SELECT pk_alloc INTO str_pk_alloc FROM host WHERE str_name=:new.str_host;

      EXECUTE IMMEDIATE
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
            (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10)'
         USING :new.pk_frame,
            :new.pk_layer,
            :new.pk_job,
            :new.str_name,
            'Running',
            :new.int_cores,
            :new.int_mem_reserved,
            :new.str_host,
            epoch(systimestamp),
            str_pk_alloc;
    END IF;


EXCEPTION
    /**
    * When we first roll this out then job won't be in the historical
    * table, so frames on existing jobs will fail unless we catch
    * and eat the exceptions.
    **/
    WHEN OTHERS THEN
        NULL;
END;

