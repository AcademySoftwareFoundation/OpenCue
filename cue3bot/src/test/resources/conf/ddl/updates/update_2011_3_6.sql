/*
* Additional data for frame history
**/
ALTER TABLE frame_history ADD int_checkpoint_count NUMBER(6) DEFAULT 0 NOT NULL;

/*
* GPU booking support.
**/
ALTER TABLE host ADD int_gpu NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE host ADD int_gpu_idle NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE service ADD int_gpu_min NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE show_service ADD int_gpu_min NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE layer ADD int_gpu_min NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE proc ADD int_gpu_reserved NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE frame ADD int_gpu_reserved NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE host_stat ADD int_gpu_total NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE host_stat ADD int_gpu_free NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE host_local ADD int_gpu_idle NUMBER(10) DEFAULT 0 NOT NULL;
ALTER TABLE host_local ADD int_gpu_max NUMBER(10) DEFAULT 0 NOT NULL;

CREATE INDEX i_host_int_gpu ON host (int_gpu);
CREATE INDEX i_host_int_gpu_idle ON host (int_gpu_idle);
CREATE INDEX i_service_int_gpu_min ON service (int_gpu_min);
CREATE INDEX i_show_service_int_gpu_min ON show_service (int_gpu_min);
CREATE INDEX i_layer_int_gpu_min ON layer (int_gpu_min);
CREATE INDEX i_proc_int_gpu_reserved ON proc (int_gpu_reserved);
CREATE INDEX i_frame_int_gpu_reserved ON frame (int_gpu_reserved);
CREATE INDEX i_host_stat_int_gpu_total ON host_stat (int_gpu_total);
CREATE INDEX i_host_stat_int_gpu_free ON host_stat (int_gpu_free);
CREATE INDEX i_host_local_int_gpu_idle ON host_local (int_gpu_idle);
CREATE INDEX i_host_local_int_gpu_max ON host_local (int_gpu_max);

// ----------------------------------------------------------------------------

create or replace
TRIGGER "CUE3"."VERIFY_HOST_LOCAL" BEFORE UPDATE ON host_local
FOR EACH ROW
  WHEN ((NEW.int_cores_max = OLD.int_cores_max AND NEW.int_mem_max = OLD.int_mem_max) AND 
(NEW.int_cores_idle != OLD.int_cores_idle OR NEW.int_mem_idle != OLD.int_mem_idle)) BEGIN
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

    IF :NEW.int_gpu_idle < 0 THEN
        Raise_application_error(-20021, 'host local doesnt have enough idle gpu memory');
    END IF;
END;

// ----------------------------------------------------------------------------

create or replace
TRIGGER "CUE3"."VERIFY_HOST_RESOURCES" BEFORE UPDATE ON host
FOR EACH ROW
  WHEN (new.int_cores_idle != old.int_cores_idle OR new.int_mem_idle != old.int_mem_idle) BEGIN
    IF :new.int_cores_idle < 0 THEN
        Raise_application_error(-20011, 'unable to allocate additional core units');
    END IF;

    If :new.int_mem_idle < 0 THEN
        Raise_application_error(-20012, 'unable to allocate additional memory');
    END IF;

    If :new.int_gpu_idle < 0 THEN
        Raise_application_error(-20013, 'unable to allocate additional gpu memory');
    END IF;

END;

// ----------------------------------------------------------------------------
