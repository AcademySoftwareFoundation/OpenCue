/**
* Procedures, functions, and triggers for Oracle.
*
**/

/**
* epoch_to_ts
*
* Converts epoch time into an oracle timestamp
**/
CREATE OR REPLACE FUNCTION epoch_to_ts (seconds IN NUMBER)
RETURN TIMESTAMP AS
BEGIN
    RETURN TO_TIMESTAMP('19700101000000','YYYYMMDDHH24MISS TZH:TZM')
        + NUMTODSINTERVAL(seconds, 'SECOND');
END;
/

/**
* interval_to_seconds
*
* Converts the differene between two timestamps to seconds
**/
 create or replace FUNCTION "INTERVAL_TO_SECONDS"
( intrvl IN DSINTERVAL_UNCONSTRAINED) 
RETURN NUMBER AS
BEGIN
   RETURN EXTRACT(DAY FROM intrvl) * 86400
         + EXTRACT(HOUR FROM intrvl) * 3600
         + EXTRACT(MINUTE FROM intrvl) * 60
         + EXTRACT(SECOND FROM intrvl);
END INTERVAL_TO_SECONDS;

/**
* Finds a tier value
**/
create or replace FUNCTION tier(int_cores IN NUMERIC, int_min_cores IN NUMERIC)
RETURN NUMBER AS
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

/**
* Creates a "soft" tier where all items are considered equal once they
* have met their minimum.
**/
create or replace FUNCTION soft_tier(int_cores IN NUMERIC, int_min_cores IN NUMERIC)
RETURN NUMBER AS
BEGIN
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

/**
* recurse_folder_parent_change
*
* Recurse_folder_parent_change recursively updates the int_level 
* field in the folders table when a folder is updated to a new parent.
* int_level is important because to build a nested data structure
* that represents folders, it has to be build from the trunk out
* to the branches.
**/

CREATE OR REPLACE PROCEDURE recurse_folder_parent_change(str_folder_id IN VARCHAR2, str_parent_folder_id IN VARCHAR2)
IS
BEGIN
    SELECT i_level + 1 INTO 
        int_parent_level
    FROM 
        folder_level
    WHERE 
        pk_folder = str_parent_folder_id;

    UPDATE
        folder
    SET
        int_level = int_parent_level
    WHERE
        pk_folder = str_folder_id;

    FOR child IN (SELECT pk_group FROM groups WHERE pk_parent_group = str_folder_id) LOOP
        recurse_group_parent_change(child.pk_group, str_folder_id);
    END LOOP; 
END;
/

/**
* recalculate_tags
*
* concatenates tags from the host_tag table and updates the
* full text indexed column in the host_table.  Run this
* on each host if tags are added/removed/or updated.
**/
create or replace PROCEDURE recalculate_tags(str_host_id IN VARCHAR2) 
IS
  str_tag VARCHAR2(256) := '';
BEGIN
  /**
  * concatenates all tags in host_tag and sets host.str_tags
  **/
  FOR tag IN (SELECT str_tag FROM host_tag WHERE pk_host=str_host_id ORDER BY str_tag_type ASC, str_tag ASC) LOOP
    str_tag := str_tag || ' ' || tag.str_tag;
  END LOOP;
  
  EXECUTE IMMEDIATE 'UPDATE host SET str_tags=trim(:1) WHERE pk_host=:2'
    USING str_tag, str_host_id;
END;

/**
* Triggers
**/

/**
* Before deleting group, deletes rows in supporting folder.
**/
create or replace TRIGGER 
"CUE3"."BEFORE_DELETE_FOLDER" BEFORE DELETE ON folder
FOR EACH ROW
BEGIN
    DELETE FROM folder_level WHERE pk_folder = :old.pk_folder;
    DELETE FROM folder_resource WHERE pk_folder = :old.pk_folder;
END;

/**
* Before inserting folder, determine if this is the default group.
* The default group has no parent.
**/
create or replace TRIGGER 
"CUE3"."BEFORE_INSERT_FOLDER" BEFORE INSERT ON folder
FOR EACH ROW
BEGIN
    IF :new.pk_parent_folder IS NULL THEN
        :new.b_default := 1;
    END IF;
END;

/**
* Inserts supporting tables after a folder is created.
**/
create or replace TRIGGER 
"CUE3"."AFTER_INSERT_FOLDER" AFTER INSERT ON folder
FOR EACH ROW
DECLARE
    int_level NUMERIC(16,0) :=0;
BEGIN
    IF :new.pk_parent_folder IS NOT NULL THEN
        SELECT folder_level.int_level + 1 INTO int_level FROM folder_level WHERE pk_folder = :new.pk_parent_folder;
    END IF;
    INSERT INTO folder_level (pk_folder_level,pk_folder,int_level) VALUES (:new.pk_folder, :new.pk_folder, int_level);
    INSERT INTO folder_resource (pk_folder_resource,pk_folder) VALUES (:new.pk_folder, :new.pk_folder);
END;


/**
* after_insert_job
*
* Runs after a job is inserted.
**/
create or replace TRIGGER "CUE3".after_insert_job AFTER INSERT ON job
FOR EACH ROW
BEGIN
    INSERT INTO job_stat (pk_job_stat,pk_job) VALUES(:new.pk_job,:new.pk_job);
    INSERT INTO job_resource (pk_job_resource,pk_job) VALUES(:new.pk_job,:new.pk_job);
    INSERT INTO job_usage (pk_job_usage,pk_job) VALUES(:new.pk_job,:new.pk_job);
    INSERT INTO job_mem (pk_job_mem,pk_job) VALUES (:new.pk_job,:new.pk_job);
    
    INSERT INTO job_history 
        (pk_job, pk_show, pk_facility, pk_dept, str_name, str_shot, str_user, int_ts_started)
    VALUES
        (:new.pk_job, :new.pk_show, :new.pk_facility, :new.pk_dept, 
         :new.str_name, :new.str_shot, :new.str_user, epoch(systimestamp));
END;

/**
* Updates folder counts when ajob is moved between folders.
**/
create or replace TRIGGER 
"CUE3"."AFTER_JOB_MOVED" AFTER UPDATE ON job
FOR EACH ROW
WHEN(NEW.pk_folder != OLD.pk_folder)
DECLARE
    int_core_count NUMERIC(16,0);
BEGIN
  SELECT int_cores INTO int_core_count
  FROM job_resource WHERE pk_job = :new.pk_job FOR UPDATE;

  IF int_core_count > 0 THEN
    UPDATE folder_resource  SET int_cores = int_cores + int_core_count
    WHERE pk_folder = :new.pk_folder;
    
    UPDATE folder_resource  SET int_cores = int_cores - int_core_count
    WHERE pk_folder = :old.pk_folder;
  END IF;
END;

/**
* Pre-caclulates the tier value for the folder.  The tier
* represents what percentage the folder is booked up past min procs.
**/
create or replace TRIGGER "CUE3".before_update_folder_resource BEFORE UPDATE ON folder_resource
FOR EACH ROW
BEGIN
    /** calculates new tier **/
    :new.float_tier := soft_tier(:new.int_cores,:new.int_min_cores);
END;

/**
* Pre-calculates the tier value for the job.  The tier repesents
* what percentage the job is booked up past min procs.
**/
create or replace TRIGGER "CUE3".before_update_job_resource BEFORE UPDATE ON job_resource
FOR EACH ROW
BEGIN
    /** calculates new tier **/
    :new.float_tier := tier(:new.int_cores,:new.int_min_cores);
END;

/**
* Runs after a job is set to the Finished state.  It sets the job's stop time and
* updates the stop time of all the waiting frames.
*/
create or replace TRIGGER "CUE3".after_job_finished AFTER UPDATE ON job
FOR EACH ROW
WHEN (old.str_state = 'Pending' AND new.str_state = 'Finished')
DECLARE
    ts NUMERIC(12,0) := epoch(systimestamp);
BEGIN
    /* Sets the job history stop time */
    UPDATE job_history SET int_ts_stopped = ts WHERE pk_job=:new.pk_job;
    UPDATE frame_history SET int_ts_stopped = ts WHERE pk_job=:new.pk_job AND str_state='Waiting' AND int_ts_stopped=0;
END;

/**
* after_insert_layer
*
* Runs after a layer is inserted
**/
create or replace TRIGGER "CUE3".after_insert_layer AFTER INSERT ON layer
FOR EACH ROW
BEGIN
    
    INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job) VALUES (:new.pk_layer, :new.pk_layer, :new.pk_job);
    INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES (:new.pk_layer, :new.pk_layer, :new.pk_job);
    INSERT INTO layer_usage (pk_layer_usage, pk_layer, pk_job) VALUES (:new.pk_layer, :new.pk_layer, :new.pk_job);
    INSERT INTO layer_mem (pk_layer_mem, pk_layer, pk_job) VALUES (:new.pk_layer, :new.pk_layer, :new.pk_job);

    INSERT INTO layer_history
        (pk_layer, pk_job, str_name, str_type, int_cores_min, int_mem_min, b_archived)
    VALUES
        (:new.pk_layer, :new.pk_job, :new.str_name, :new.str_type, :new.int_cores_min, :new.int_mem_min, 0);
END;

/**
* before_delete_host
*
* Runs before a host is deleted.
**/
create or replace TRIGGER "CUE3".before_delete_host BEFORE DELETE ON host
FOR EACH ROW
BEGIN
    delete from host_stat WHERE pk_host = :old.pk_host;
    delete from host_tag WHERE pk_host = :old.pk_host;
END;

/**
* before_delete_job
* 
* Runs before a job is deleted.  Updates the place holder job
* history entry, then removes all data with a dependency on pk_job.
**/
create or replace TRIGGER "CUE3".before_delete_job BEFORE DELETE ON job
FOR EACH ROW
DECLARE
    TYPE StatType IS RECORD (
        int_core_time_success NUMERIC(38),
        int_core_time_fail NUMERIC(38),
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
        job_mem.pk_job = :old.pk_job;

    UPDATE 
        job_history
    SET
        pk_dept = :old.pk_dept,
        int_core_time_success = js.int_core_time_success,
        int_core_time_fail = js.int_core_time_fail,
        int_frame_count = :old.int_frame_count,
        int_layer_count = :old.int_layer_count,
        int_waiting_count = js.int_waiting_count,
        int_dead_count = js.int_dead_count,
        int_depend_count = js.int_depend_count,
        int_eaten_count = js.int_eaten_count,
        int_succeeded_count = js.int_succeeded_count,
        int_running_count = js.int_running_count,
        int_max_rss = js.int_max_rss,
        b_archived = 1,
        int_ts_stopped = nvl(epoch(:old.ts_stopped), epoch(systimestamp))
    WHERE
        pk_job = :old.pk_job;

    delete from depend where pk_job_depend_on=:old.pk_job or pk_job_depend_er=:old.pk_job;
    delete from frame where pk_job=:old.pk_job;
    delete from layer where pk_job=:old.pk_job;
    delete from job_env WHERE pk_job=:old.pk_job;
    delete from job_stat WHERE pk_job=:old.pk_job;
    delete from job_resource WHERE pk_job=:old.pk_job;
    delete from job_usage WHERE pk_job=:old.pk_job;
    delete from job_mem WHERE pk_job=:old.pk_job;
    delete from comments WHERE pk_job=:old.pk_job;
END;

/**
* before_delete_layer
*
* Rus before a layer is deleted.  Updates the layer_history table with
* layer stats, then removes all data that depends on pk_layer.
**/
create or replace TRIGGER "CUE3".before_delete_layer BEFORE DELETE ON layer
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
END;

/**
* delete_proc_update_host
*
* runs after a proc is deleted and updates the host entry with the
* free resources from the proc.
**/
create or replace TRIGGER "CUE3".delete_proc_update_host AFTER DELETE ON PROC 
FOR EACH ROW
BEGIN
   UPDATE host SET 
        int_cores_idle = int_cores_idle + :old.int_cores_reserved,
        int_mem_idle = int_mem_idle + :old.int_mem_reserved
    WHERE
        pk_host=:old.pk_host;
        
    UPDATE host SET int_mem_idle = int_mem WHERE pk_host=:old.pk_host AND int_mem_idle > int_mem;
        
END;

/**
* delete_proc_update_layer
*
* runs after a proc is deleted and removes the proc from 
* the layers resource count
**/
create or replace TRIGGER "CUE3".delete_proc_update_layer AFTER DELETE ON proc
FOR EACH ROW
DECLARE
  str_pk_folder CHAR(36);
BEGIN
    UPDATE layer_resource SET 
        int_cores=int_cores - :old.int_cores_reserved
    WHERE
        pk_layer = :old.pk_layer;

  UPDATE job_resource SET 
        int_cores=int_cores - :old.int_cores_reserved
    WHERE
        pk_job = :old.pk_job;
    
    SELECT pk_folder INTO str_pk_folder FROM job WHERE pk_job = :old.pk_job FOR UPDATE;
    UPDATE folder_resource SET
        int_cores = int_cores - :old.int_cores_reserved
    WHERE
        pk_folder = str_pk_folder;
END;

/**
* insert_proc_update_host
*
* removes the resources used by a proc from the host
**/
create or replace TRIGGER "CUE3".insert_proc_update_host AFTER INSERT ON proc
FOR EACH ROW
BEGIN
    UPDATE host SET 
        int_cores_idle = int_cores_idle - :new.int_cores_reserved,
        int_mem_idle = int_mem_idle - :new.int_mem_reserved
    WHERE
        pk_host = :new.pk_host;
END;


/**
* insert_proc_update_layer
*
* updates the layer and job resource counts when a proc is inserted.
**/
create or replace TRIGGER "CUE3".insert_proc_update_layer AFTER INSERT ON proc
FOR EACH ROW
DECLARE
    str_pk_folder CHAR(36);
BEGIN
    UPDATE layer_resource SET 
        int_cores=int_cores + :new.int_cores_reserved
    WHERE
        pk_layer = :new.pk_layer;
        
    UPDATE job_resource SET 
        int_cores=int_cores + :new.int_cores_reserved
    WHERE
        pk_job = :new.pk_job;
    
    SELECT pk_folder INTO str_pk_folder FROM job WHERE pk_job = :new.pk_job FOR UPDATE;    
    UPDATE folder_resource SET
        int_cores = int_cores + :new.int_cores_reserved
    WHERE
        pk_folder = str_pk_folder;
END;

/** FRAME TRIGGERS **/

/**
* update_frame_status_counts
*
* updates the frame state counts upon a frame state change.
**/
create or replace TRIGGER "CUE3".update_frame_status_counts AFTER UPDATE ON frame
FOR EACH ROW
WHEN (old.str_state != 'Setup' AND old.str_state != new.str_state)
DECLARE
    s_old_status_col VARCHAR2(32);
    s_new_status_col VARCHAR2(32);
BEGIN
    s_old_status_col := 'int_' || :old.str_state || '_count';
    s_new_status_col := 'int_' || :new.str_state || '_count';

    EXECUTE IMMEDIATE 'UPDATE layer_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_layer=:1' USING :new.pk_layer;
  
    EXECUTE IMMEDIATE 'UPDATE job_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_job=:1' USING :new.pk_job;    
END;

/**
* update_frame_waiting
*
* checks to see if a frame has any new dependencies before setting it to waiting
**/
create or replace TRIGGER "CUE3".update_frame_waiting BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (NEW.str_state='Waiting' AND NEW.int_depend_count > 0)
BEGIN
    :NEW.str_state :='Depend';
END;

/**
* update_frame_eaten
*
* checks to see if a frame is succeeded but is being set to eaten and
* sets it back to succeeded
**/
create or replace TRIGGER "CUE3".update_frame_eaten BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (NEW.str_state='Eaten' AND OLD.str_state='Succeeded')
BEGIN
    :NEW.str_state :='Succeeded';
END;


/**
* update_frame_eaten
*
* Updates frames from depend to waiting if their depend count is zero.
**/
create or replace TRIGGER "CUE3".update_frame_dep_to_wait BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (OLD.int_depend_count > 0 AND NEW.int_depend_count < 1 AND OLD.str_state='Depend')
BEGIN
    :NEW.str_state := 'Waiting';
    :NEW.ts_updated := systimestamp;
END;

/**
* update_layer_usage
*
* updates the layer/job usage table with the proc time a layer has used
* after a frame has completed.  The number of cores the frame used serves
* as a multiplier to the proc time.
**/
create or replace
TRIGGER "CUE3".update_layer_usage AFTER UPDATE ON frame
FOR EACH ROW
WHEN (OLD.str_state = 'Running' AND NEW.str_state != 'Running')
DECLARE
    l_core_seconds NUMERIC(16);
    l_clock_seconds NUMERIC(16);
    l_cores NUMERIC(16);
BEGIN
      l_cores := :old.int_cores / 100.0;
      l_clock_seconds :=  interval_to_seconds(:new.ts_stopped - :new.ts_started);
      l_core_seconds := CEIL(l_clock_seconds * l_cores);

      IF :old.str_state = 'Running' AND :new.str_state = 'Succeeded' THEN

          /** Layer Usage **/

          UPDATE layer_usage SET
              int_core_time_success = int_core_time_success + l_core_seconds,
              int_clock_time_success = int_clock_time_success + l_clock_seconds,
              int_frame_success_count = int_frame_success_count + 1
          WHERE
              pk_layer = :new.pk_layer;

          UPDATE layer_usage SET  
              int_clock_time_high = l_clock_seconds 
          WHERE 
              pk_layer = :new.pk_layer
          AND
              int_clock_time_high < l_clock_seconds;

          UPDATE layer_usage SET  
              int_clock_time_low = l_clock_seconds 
          WHERE 
              pk_layer = :new.pk_layer
          AND
              (l_clock_seconds < int_clock_time_low OR int_clock_time_low = 0);
          
          /** Job Usage **/

          UPDATE job_usage SET
              int_core_time_success = int_core_time_success + l_core_seconds,
              int_clock_time_success = int_clock_time_success + l_clock_seconds,
              int_frame_success_count = int_frame_success_count + 1
          WHERE
              pk_job = :new.pk_job;

          UPDATE job_usage SET  
              int_clock_time_high = l_clock_seconds 
          WHERE 
              pk_job = :new.pk_job
          AND
              int_clock_time_high < l_clock_seconds;      
      ELSE

          UPDATE layer_usage SET
              int_core_time_fail = int_core_time_fail + l_core_seconds,
              int_clock_time_fail = int_clock_time_fail + l_clock_seconds,
              int_frame_fail_count = int_frame_fail_count + 1
          WHERE
              pk_layer = :new.pk_layer;
              
          UPDATE job_usage SET
              int_core_time_fail = int_core_time_fail + l_core_seconds,
              int_clock_time_fail = int_clock_time_fail + l_clock_seconds,
              int_frame_fail_count = int_frame_fail_count + 1
          WHERE
              pk_job = :new.pk_job;
      END IF;
END;

/** PROC TRIGGERS **/

/**
* update_proc_update_layer
*
* Updates the layer/job resource table when a proc changes layers
**/
create or replace TRIGGER "CUE3".update_proc_update_layer AFTER UPDATE ON proc
FOR EACH ROW
WHEN (new.pk_layer != old.pk_layer) 
BEGIN
    UPDATE layer_resource SET
        int_cores = int_cores - :old.int_cores_reserved
    WHERE
        pk_layer = :old.pk_layer;

    UPDATE layer_resource SET
        int_cores = int_cores + :new.int_cores_reserved
    WHERE
        pk_layer = :new.pk_layer;
 
    UPDATE job_resource SET
        int_cores = int_cores - :old.int_cores_reserved
    WHERE
        pk_job = :old.pk_job;

    UPDATE job_resource SET
        int_cores = int_cores + :new.int_cores_reserved
    WHERE
        pk_job = :new.pk_job;
END;

/**
* upgrade_proc_memory_usage
*
* When proc memory usages changes, this fuction adds/removes the memory from the host.
**/
create or replace TRIGGER upgrade_proc_memory_usage AFTER UPDATE ON proc
FOR EACH ROW
WHEN (NEW.int_mem_reserved != OLD.int_mem_reserved) 
BEGIN
    UPDATE host SET 
        int_mem_idle = int_mem_idle - (:new.int_mem_reserved - :old.int_mem_reserved)
    WHERE
        pk_host = :new.pk_host;
END;


/**
* update_satisfy_frame_depend
* 
* Satisfies frame on frame dependencies.
**/
create or replace TRIGGER "CUE3".update_satisfy_frame_depend AFTER UPDATE ON depend
FOR EACH ROW
WHEN (OLD.str_type='FrameOnFrame' AND OLD.b_active = 1 AND NEW.b_active = 0)
BEGIN
    EXECUTE IMMEDIATE 'UPDATE frame SET int_depend_count = int_depend_count - 1 WHERE pk_job=:1 AND pk_frame=:2 AND int_depend_count > 0'
        USING :new.pk_job_depend_er, :new.pk_frame_depend_er;
END;


/**
* verify_host_resources
*
* verify that a host has the resources being allocated from it.
**/
create or replace TRIGGER "CUE3".verify_host_resources BEFORE UPDATE ON host
FOR EACH ROW
DECLARE
    l_idle_mem NUMERIC(38,0);
BEGIN
    IF :new.int_cores_idle < 0 THEN
        Raise_application_error(-20011, 'unable to allocate additional core units');
    END IF;

    If :new.int_mem_idle < 0 THEN
        Raise_application_error(-20012, 'unable to allocate additional memory');
    END IF;
    
END;

/**
* If the end timestamp is less than or equal to the start time
* then rewrite it to be a 1 second frame duration.  This only
* matters on the update.
**/
CREATE OR REPLACE TRIGGER
cue3.frame_history_fix_time BEFORE UPDATE ON frame_history
FOR EACH ROW
WHEN (NEW.int_ts_stopped <= NEW.int_ts_started)
BEGIN
    :new.int_ts_stopped := :new.int_ts_started + 1;
END;


/**
* frame_history_open
*
* upon a state change, this updates the last frame in frame_history with
* a stop time (if any), and inserts a new frame.
**/
create or replace
TRIGGER "CUE3".frame_history_open AFTER UPDATE ON frame
FOR EACH ROW
WHEN (NEW.str_state != OLD.str_state AND new.str_state != 'Setup')
DECLARE
  str_pk_alloc VARCHAR2(36) := null;
  str_host VARCHAR2(36) := null;
  str_state VARCHAR2(36);
  int_cores NUMBER(16) := 0;
  int_mem_reserved NUMBER(38) := 0;
  str_job_state VARCHAR2(36);
BEGIN
    /**
    * Waiting and depend are just considered waiting so don't
    * record when a frame switches from waiting to depend
    * or depend to waiting.
    **/
    IF :new.str_state = 'Waiting' AND :old.str_state='Depend' THEN
        RETURN;
    END IF;

    IF :new.str_state = 'Depend' AND :old.str_state='Waiting' THEN
        RETURN;
    END IF;

    /**
    * Catches instances where a depend might get in and 
    * rewrites it as waiting.  Frames can go from any state
    * to depend.
    **/
    str_state := :new.str_state;
    IF :new.str_state = 'Depend' THEN
        str_state := 'Waiting';
    END IF;

    /**
    * If the old frame was running then the running stats are updated,
    * otherwise, just the stop time is updated.
    **/
    IF :old.str_state = 'Running' THEN
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
    ELSE
        EXECUTE IMMEDIATE
        'UPDATE 
            frame_history
        SET
            int_ts_stopped=:1
        WHERE
            int_ts_stopped = 0 AND pk_frame=:2'
        USING
            epoch(systimestamp),
            :new.pk_frame; 
    END IF;

    /**
    * Once the last state was updated with its runtime stats,
    * return if the frame state is not waiting or running.  We
    * Don't care about succeeded, eaten, dead, any of that.
    **/
    IF str_state NOT IN ('Waiting','Running') THEN
        RETURN;
    END IF;

    /**
    * If the new frame state is running then setup the run time stats
    * we know about.  If the frame is waiting its inserted with all 0s.
    * Make sure not to put run time stats on waiting frames.
    */
    IF str_state = 'Running' THEN
      SELECT pk_alloc INTO str_pk_alloc FROM host WHERE str_name=:new.str_host;
      str_host := :new.str_host;
      int_cores := :new.int_cores;
      int_mem_reserved := :new.int_mem_reserved;
    END IF;

    /**
    * Check if the job state is finished.  This is so if the job is killed a whole
    * bunch of waiting frames don't get added to the historical data.
    */
    SELECT job.str_state INTO str_job_state FROM job WHERE pk_job=:new.pk_job;
    IF str_job_state = 'Finished' THEN
        RETURN;
    END IF;

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
        str_state,
        int_cores,
        int_mem_reserved,
        str_host,
        epoch(systimestamp),
        str_pk_alloc;
EXCEPTION
    /**
    * When we first roll this out then job won't be in the historical
    * table, so frames on existing jobs will fail unless we catch
    * and eat the exceptions.
    **/
    WHEN OTHERS THEN
        NULL;
END;

/**
* Methods for finding the amount of proc hours used with
* clamping capability.
*
**/
create or replace FUNCTION CALCULATE_CORE_HOURS
(int_ts_started NUMERIC, int_ts_stopped NUMERIC, 
int_start_report NUMERIC, int_stop_report NUMERIC, 
int_job_stopped NUMERIC, int_cores NUMBER)
RETURN NUMBER IS
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

