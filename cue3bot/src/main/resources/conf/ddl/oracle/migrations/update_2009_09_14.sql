
/**
* Updated this trigger to also change the status on Dead/Succeeded frames
* if their dependency count changed.  Previously we were only doing this
* with waiting frames.
**/
create or replace TRIGGER "CUE3".update_frame_wait_to_dep BEFORE UPDATE ON frame
FOR EACH ROW
WHEN (NEW.int_depend_count > 0 AND NEW.str_state IN ('Dead','Succeeded','Waiting'))
BEGIN
    :NEW.str_state := 'Depend';
    :NEW.ts_updated := systimestamp;
END;
