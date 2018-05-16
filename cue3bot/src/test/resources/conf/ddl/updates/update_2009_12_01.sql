/*
* Drop obsolete table.
*/ 
DROP TABLE job_local;

/**
* The host local table stores local booking instructions.
*/
CREATE TABLE host_local (
    pk_host_local       VARCHAR2(36) NOT NULL,
    pk_job              VARCHAR2(36) NOT NULL,
    pk_layer            VARCHAR2(36),
    pk_frame            VARCHAR2(36),
    pk_host             VARCHAR2(36) NOT NULL,
    ts_created          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    ts_updated          TIMESTAMP WITH TIME ZONE,
    str_type            VARCHAR2(36) NOT NULL,
    int_mem_max         NUMBER(16,0) DEFAULT 0 NOT NULL,
    int_mem_idle        NUMBER(16,0) DEFAULT 0 NOT NULL,     
    int_cores_max       NUMBER(16,0) DEFAULT 100 NOT NULL,
    int_cores_idle      NUMBER(16,0) DEFAULT 100 NOT NULL,    
    int_threads         NUMBER(4,0) DEFAULT 1 NOT NULL,
    float_tier          NUMBER(16,2) DEFAULT 0 NOT NULL,
    b_active            NUMBER(1,0) DEFAULT 1 NOT NULL
);

ALTER TABLE host_local
    ADD CONSTRAINT c_pk_host_local PRIMARY KEY (pk_host_local);
CREATE INDEX i_host_local_pk_job ON host_local (pk_job);
CREATE UNIQUE INDEX i_host_local_unique ON host_local (pk_host);

ALTER TABLE host_local ADD CONSTRAINT c_host_local_pk_job 
FOREIGN KEY (pk_job) REFERENCES job (pk_job);

ALTER TABLE host_local ADD CONSTRAINT c_host_local_pk_host
FOREIGN KEY (pk_host) REFERENCES host (pk_host);

/**
* Calculates tier based on how close the job is to its max.
**/
create or replace TRIGGER tier_host_local BEFORE UPDATE ON host_local
FOR EACH ROW
BEGIN
    :new.float_tier := tier(:new.int_cores_max - :new.int_cores_idle,:new.int_cores_max);
END;

/**
* Ensures that we don't automatically book more cores or memory than allowed.
**/
create or replace TRIGGER verify_host_local BEFORE UPDATE ON host_local
FOR EACH ROW
WHEN ((NEW.int_cores_max = OLD.int_cores_max AND NEW.int_mem_max = OLD.int_mem_max) AND 
(NEW.int_cores_idle != OLD.int_cores_idle OR NEW.int_mem_idle !=  OLD.int_mem_idle))
BEGIN
    /**
    * Check to see if the new cores exceeds max cores.  This check is only
    * done if NEW.int_max_cores is equal to OLD.int_max_cores and
    * NEW.int_cores > OLD.int_cores, otherwise this error will be thrown
    * when people lower the max.
    **/
    IF :NEW.int_cores_idle < 0 THEN
        Raise_application_error(-20021, 'host local doesnt have enough idle cores.');
    END IF;
    
    IF :NEW.int_mem_idle < 0 THEN
        Raise_application_error(-20021, 'host local doesnt have enough idle memory');
    END IF;
END;