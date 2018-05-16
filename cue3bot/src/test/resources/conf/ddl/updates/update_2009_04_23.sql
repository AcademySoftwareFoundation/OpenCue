
/**
* Add column to store who locked a proc.
**/
ALTER TABLE host ADD str_lock_source VARCHAR2(128);

/* Tasks are no longer specifically assigned to jobs */
ALTER TABLE job DROP column pk_task;

/*
* We no longer have to keep track of task cores/tier because proc points
* updates the job's min cores directly.  There is also no longer a default
* task.
*/
ALTER TABLE task DROP COLUMN int_cores;
ALTER TABLE task DROP COLUMN float_tier;
DELETE FROM task WHERE b_default = 1;
ALTER TABLE task DROP column b_default;

/*
* Instead of using a view (vs_sub), if we keep track of a subscriptions
* cores directly we save a lot of CPU
**/
ALTER TABLE subscription ADD int_cores NUMERIC(16,0) DEFAULT 0 NOT NULL;
ALTER TABLE subscription ADD float_tier NUMERIC(16,2) DEFAULT 0 NOT NULL;

/**
* point.int_min_cores is now the min cores for the deparartment.
* int_cores keeps track of how many cores the department is running.
*/
ALTER TABLE point ADD int_min_cores NUMERIC(16,0) DEFAULT 0 NOT NULL;
ALTER TABLE point ADD float_tier NUMERIC(16,2) DEFAULT 0 NOT NULL;
ALTER TABLE point ADD ts_updated TIMESTAMP WITH TIME ZONE DEFAULT systimestamp NOT NULL;
UPDATE point SET int_cores = 0;

/**
* Create a new task for updating trackit tasks
**/
INSERT INTO task_lock VALUES (genkey(), 'LOCK_TASK_UPDATE', 0, 3600, systimestamp);

/*
* Drop old stuff
*/
DROP INDEX I_TASK_STR_SHOT;
DROP INDEX I_JOB_RESOURCE_PRI;
DROP TRIGGER AFTER_JOB_DEPT_UPDATE;
DROP TRIGGER AFTER_JOB_TASK_UPDATE;
DROP TRIGGER BEFORE_INSERT_JOB;
DROP TRIGGER insert_proc_update_layer;
DROP TRIGGER delete_proc_update_layer;
DROP TRIGGER "CUE3".insert_proc_update_host;
DROP TRIGGER "CUE3".delete_proc_update_host;
DROP TRIGGER "CUE3".before_update_job_resource;
DROP TRIGGER  "CUE3".before_update_folder_resource;

DROP PROCEDURE tmp_populate_dept;

/**
* Create new indexes
**/

CREATE INDEX I_JOB_TIER ON job_resource (float_tier);
CREATE INDEX I_FOLDER_TIER ON folder_resource (float_tier);
CREATE INDEX I_POINT_TIER ON point (float_tier);
CREATE INDEX I_SUB_TIER ON subscription (float_tier);

/**
* Merged ins/del_update_layer, and ins/del_update_host into
* these triggers cue3.proc_delete, cue3.proc_insert 
**/
create or replace TRIGGER "CUE3".proc_delete AFTER DELETE ON proc
FOR EACH ROW
BEGIN
    /**
    * Handles all the accounting when a proc is deleteed
    */
    UPDATE host SET 
        int_cores_idle = int_cores_idle + :old.int_cores_reserved,
        int_mem_idle = int_mem_idle + :old.int_mem_reserved
    WHERE
        pk_host = :old.pk_host;

    UPDATE subscription SET int_cores = int_cores - :old.int_cores_reserved
        WHERE pk_show = :old.pk_show AND pk_alloc = (SELECT pk_alloc FROM host WHERE pk_host = :old.pk_host);

    UPDATE layer_resource SET  int_cores=int_cores - :old.int_cores_reserved
        WHERE pk_layer = :old.pk_layer;

    UPDATE job_resource SET  int_cores=int_cores - :old.int_cores_reserved
        WHERE pk_job = :old.pk_job;

    UPDATE folder_resource SET int_cores = int_cores - :old.int_cores_reserved
        WHERE pk_folder = (SELECT pk_folder FROM job WHERE pk_job = :old.pk_job);
        
    UPDATE point SET int_cores = int_cores - :old.int_cores_reserved
        WHERE pk_dept = (SELECT pk_dept FROM job WHERE pk_job = :old.pk_job)
            AND pk_show = (SELECT pk_show FROM job WHERE pk_job = :old.pk_job);
END;

create or replace TRIGGER "CUE3".proc_insert AFTER INSERT ON proc
FOR EACH ROW
BEGIN
    /**
    * Handles all the accounting when a proc is created
    */
   UPDATE host SET 
        int_cores_idle = int_cores_idle - :new.int_cores_reserved,
        int_mem_idle = int_mem_idle - :new.int_mem_reserved
    WHERE
        pk_host=:new.pk_host; 

    UPDATE subscription SET int_cores = int_cores + :new.int_cores_reserved
        WHERE pk_show = :new.pk_show AND pk_alloc = (SELECT pk_alloc FROM host WHERE pk_host = :new.pk_host);

    UPDATE layer_resource SET  int_cores=int_cores + :new.int_cores_reserved
        WHERE pk_layer = :new.pk_layer;
        
    UPDATE job_resource SET int_cores=int_cores + :new.int_cores_reserved
        WHERE pk_job = :new.pk_job;

    UPDATE folder_resource SET int_cores = int_cores + :new.int_cores_reserved
        WHERE pk_folder = (SELECT pk_folder FROM job WHERE pk_job = :new.pk_job);
        
    UPDATE point SET int_cores = int_cores + :new.int_cores_reserved
        WHERE pk_dept = (SELECT pk_dept FROM job WHERE pk_job = :new.pk_job)
            AND pk_show = (SELECT pk_show FROM job WHERE pk_job = :new.pk_job);
END;


create or replace TRIGGER 
"CUE3"."AFTER_JOB_DEPT_UPDATE" AFTER UPDATE ON job
FOR EACH ROW
WHEN(NEW.pk_dept != OLD.pk_dept AND new.str_state='Pending')
DECLARE
    int_running_cores NUMERIC(16,0);
BEGIN
  /**
  * Handles the accounting for moving a job between departments.
  **/
  SELECT int_cores INTO int_running_cores
    FROM job_resource WHERE pk_job = :new.pk_job;

  IF int_running_cores > 0 THEN
    UPDATE point SET int_cores = int_cores + int_running_cores
        WHERE pk_dept = :new.pk_dept AND pk_show = :new.pk_show;
    
    UPDATE point  SET int_cores = int_cores - int_running_cores
        WHERE pk_dept = :old.pk_dept AND pk_show = :old.pk_show;
  END IF;    
    
END;

create or replace
TRIGGER "CUE3".point_tier BEFORE UPDATE ON point
FOR EACH ROW
BEGIN
    /* calcultes a soft tier */
    :new.float_tier := soft_tier(:new.int_cores, :new.int_min_cores);
END;

create or replace
TRIGGER "CUE3".tier_subscription BEFORE UPDATE ON subscription
FOR EACH ROW
BEGIN
    /* calcultes a soft tier */
    :new.float_tier := tier(:new.int_cores, :new.int_size);
END;

create or replace TRIGGER tier_job BEFORE UPDATE ON job_resource
FOR EACH ROW
BEGIN
    /** calculates new tier **/
    :new.float_tier := tier(:new.int_cores,:new.int_min_cores);
END;

create or replace TRIGGER tier_folder BEFORE UPDATE ON folder_resource
FOR EACH ROW
BEGIN
    /** calculates new tier **/
    :new.float_tier := soft_tier(:new.int_cores,:new.int_min_cores);
END;

/**
* Formatting change
**/
create or replace
TRIGGER "CUE3".after_job_finished AFTER UPDATE ON job
FOR EACH ROW
WHEN (old.str_state = 'Pending' AND new.str_state = 'Finished')
DECLARE
    ts NUMERIC(12,0) := epoch(systimestamp);
BEGIN
    /* Sets the job history stop time */
    UPDATE job_history SET int_ts_stopped = ts WHERE pk_job=:new.pk_job;
    UPDATE frame_history SET int_ts_stopped = ts 
      WHERE pk_job=:new.pk_job AND str_state='Waiting' AND int_ts_stopped=0;
END;

