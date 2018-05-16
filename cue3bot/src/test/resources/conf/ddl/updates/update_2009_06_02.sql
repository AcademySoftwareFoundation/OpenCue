
/**
* Added check for the return status of this frame.  If the return status is 
* 299, which is a constant defined in the cuebot as frame that didn't run but was
* cleared by a maintainence process, then this trigger should not execute.
*/
create or replace TRIGGER "CUE3".update_layer_usage AFTER UPDATE ON frame
FOR EACH ROW
WHEN (OLD.str_state = 'Running' AND NEW.str_state != 'Running' AND NEW.int_exit_status != 299)
DECLARE
    l_core_seconds NUMERIC(16) := 0;
    l_clock_seconds NUMERIC(16) := 0;
    l_cores NUMERIC(16);
BEGIN

      l_cores := :old.int_cores / 100.0;
      l_clock_seconds :=  interval_to_seconds(localtimestamp - :new.ts_started);
      IF l_clock_seconds < 0 THEN
        l_clock_seconds := l_clock_seconds + 3600;
      END IF;
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
              
      ELSIF :old.str_state = 'Running' AND :new.str_state != 'Running' THEN

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
