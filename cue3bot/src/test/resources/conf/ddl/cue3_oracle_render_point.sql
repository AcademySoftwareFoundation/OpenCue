
/*
* These go away.
*/ 
DELETE FROM task;
DELETE FROM dept_config;
drop table task;
drop table dept_conf;

/*
* The point table
*/ 
CREATE TABLE point (
    pk_point            VARCHAR2(36) NOT NULL,
    pk_dept             VARCHAR2(36) NOT NULL,
    pk_show             VARCHAR2(36) NOT NULL,
    str_ti_task         VARCHAR2(36),
    int_cores           NUMERIC(16,0) DEFAULT 0 NOT NULL,
    b_managed           NUMERIC(1,0) DEFAULT 0 NOT NULL
);

ALTER TABLE  cue3.point
    ADD CONSTRAINT c_point_pk PRIMARY KEY (pk_point);

CREATE INDEX i_point_pk_dept ON cue3.point (pk_dept);
CREATE INDEX i_point_pk_show ON cue3.point (pk_show);

ALTER TABLE cue3.point ADD CONSTRAINT c_point_pk_dept
    FOREIGN KEY (pk_dept) REFERENCES dept (pk_dept);

ALTER TABLE cue3.point ADD CONSTRAINT c_point_pk_show
    FOREIGN KEY (pk_show) REFERENCES show (pk_show);

ALTER TABLE cue3.point ADD CONSTRAINT c_point_pk_show_dept
    UNIQUE (pk_show, pk_dept);

/*
* The task table
*/ 
CREATE TABLE cue3.task (
    pk_task                 VARCHAR2(36) NOT NULL,
    pk_point                VARCHAR2(36) NOT NULL,
    str_shot                VARCHAR2(36) NOT NULL,
    int_min_cores           NUMERIC(16,0) DEFAULT 1 NOT NULL,
    int_adjust_cores        NUMERIC(16,0) DEFAULT 0 NOT NULL,
    int_cores               NUMERIC(16,0) DEFAULT 0 NOT NULL,
    float_tier              NUMERIC(16,2) DEFAULT 0 NOT NULL,
    b_default               NUMERIC(1,0) DEFAULT 0 NOT NULL    
);

ALTER TABLE  cue3.task
    ADD CONSTRAINT c_task_pk PRIMARY KEY (pk_task);

CREATE INDEX i_task_pk_point ON cue3.task (pk_point);
CREATE INDEX i_task_str_shot ON cue3.task (str_shot);
CREATE INDEX i_task_float_tier ON cue3.task (float_tier);

ALTER TABLE cue3.task ADD CONSTRAINT c_task_pk_point
  FOREIGN KEY (pk_point) REFERENCES dept (pk_point);

ALTER TABLE  cue3.task
  ADD CONSTRAINT c_task_uniq UNIQUE (str_shot, pk_point);

create or replace
TRIGGER "CUE3".before_update_task BEFORE UPDATE ON task
FOR EACH ROW
BEGIN
    /** calculates new tier **/
    :new.float_tier := soft_tier(:new.int_cores,:new.int_min_cores);
END;

/*
* Move priority over to job_resource so we can index it.
*/
ALTER TABLE job_resource ADD int_priority NUMERIC(16,0) DEFAULT 1 NOT NULL;
UPDATE job_resource SET job_resource.int_priority = (SELECT int_priority FROM job WHERE job_resource.pk_job = job.pk_job);
ALTER TABLE job drop column int_priority;

CREATE INDEX i_job_resource_pri ON job_resource (float_tier, int_priority);

/**
* For generating keys locally in standard UUID format.
**/
create or replace
FUNCTION genkey RETURN VARCHAR2 IS
    str_result VARCHAR2(36);
    guid VARCHAR2(36) := sys_guid();
BEGIN
    str_result := SUBSTR(guid, 0,8) || '-' || SUBSTR(guid,8,4) 
      || '-' || SUBSTR(guid,12,4) || '-' || SUBSTR(guid,16,4) || '-' || SUBSTR(guid,20,12);
    RETURN str_result;
END;

/**
* Add the task into the job table
*/
ALTER TABLE job ADD pk_task VARCHAR2(36);
CREATE INDEX i_job_pk_task ON cue3.job (pk_task);

ALTER TABLE cue3.job
    ADD CONSTRAINT c_job_pk_task FOREIGN KEY (pk_task) REFERENCES task (pk_task);
ALTER TABLE job MODIFY (pk_task VARCHAR2(36) NOT NULL);

/**
* creates the default departments for all shows
**/
create or replace
PROCEDURE tmp_populate_dept IS
    str_pk_dept_config VARCHAR2(36);
BEGIN
    /**
    * A temporary function
    **/
    DELETE FROM task;
    DELETE FROM dept_config;
    FOR folder IN (SELECT DISTINCT pk_dept, pk_show FROM folder) LOOP
        str_pk_dept_config:=genkey();
        INSERT INTO point (pk_point,pk_dept, pk_show) VALUES (str_pk_dept_config, folder.pk_dept, folder.pk_show);
        INSERT INTO task (pk_task,pk_point,str_shot,b_default) VALUES (genkey(), str_pk_dept_config,'(default)',1);
    END LOOP;
    UPDATE job SET pk_task=(SELECT pk_task FROM task t, dept_config d WHERE t.pk_dept_config = d.pk_dept_config AND d.pk_dept_config.pk_dept = job.pk_dept AND d.pk_dept_config.show = job.pk_show AND t.b_default = 1);
END;

/* execute */
execute tmp_populate_dept();

/**
* task switch if department changes
**/
create or replace TRIGGER 
"CUE3"."AFTER_JOB_DEPT_UPDATE" BEFORE UPDATE ON job
FOR EACH ROW
WHEN(NEW.pk_dept != OLD.pk_dept)
DECLARE
    str_pk_task VARCHAR2(36) := null;
BEGIN
    /**
    * When a job is moved to a new department then the task
    * must also be updated.  If a task for the shot exists
    * the job should use that task, otherwise it will use the
    * default task.
    **/
    SELECT pk_task INTO str_pk_task FROM (
      SELECT 
        pk_task,
        b_default
      FROM
        task, point
      WHERE
        task.pk_point = point.pk_point
      AND 
        point.pk_show=:new.pk_show 
      AND 
        point.pk_dept=:new.pk_dept
      AND
        (task.str_shot=:new.str_shot OR task.b_default=1)
      ORDER BY
        b_default ASC
    ) WHERE ROWNUM = 1;

    :new.pk_task := str_pk_task;
END;

/**
* After job task update
*/
create or replace
TRIGGER 
"CUE3"."AFTER_JOB_TASK_UPDATE" AFTER UPDATE ON job
FOR EACH ROW
WHEN(NEW.pk_task != OLD.pk_task)
DECLARE
    int_running_cores NUMERIC(16,0);
BEGIN
    /**
    * When a task changes for a job, the cores must be removed from the
    * old task total and added to the new task total. During this time
    * job_resource must be locked with a FOR UPDATE or else you
    * could end up with the wrong core count.
    **/
    SELECT int_cores INTO int_running_cores FROM job_resource WHERE pk_job=:new.pk_job FOR UPDATE;
    IF int_running_cores > 0 THEN
      UPDATE task SET int_cores = int_cores + int_running_cores WHERE pk_task = :new.pk_task;
      UPDATE task SET int_cores = int_cores - int_running_cores WHERE pk_task = :old.pk_task;
    END IF;
END;


