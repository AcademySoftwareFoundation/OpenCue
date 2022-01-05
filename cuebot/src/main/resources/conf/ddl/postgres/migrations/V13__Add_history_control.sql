-- Add history control

CREATE OR REPLACE FUNCTION trigger__after_insert_job()
RETURNS TRIGGER AS $body$
BEGIN
    INSERT INTO job_stat (pk_job_stat,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_resource (pk_job_resource,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_usage (pk_job_usage,pk_job) VALUES(NEW.pk_job,NEW.pk_job);
    INSERT INTO job_mem (pk_job_mem,pk_job) VALUES (NEW.pk_job,NEW.pk_job);

    IF NOT EXISTS (SELECT FROM config WHERE str_key='DISABLE_HISTORY') THEN

        INSERT INTO job_history
            (pk_job, pk_show, pk_facility, pk_dept, str_name, str_shot, str_user, int_ts_started)
        VALUES
            (NEW.pk_job, NEW.pk_show, NEW.pk_facility, NEW.pk_dept,
             NEW.str_name, NEW.str_shot, NEW.str_user, epoch(current_timestamp));

    END IF;

    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__before_delete_job()
RETURNS TRIGGER AS $body$
DECLARE
    js JobStatType;
BEGIN
    IF NOT EXISTS (SELECT FROM config WHERE str_key='DISABLE_HISTORY') THEN

        SELECT
            job_usage.int_core_time_success,
            job_usage.int_core_time_fail,
            job_usage.int_gpu_time_success,
            job_usage.int_gpu_time_fail,
            job_stat.int_waiting_count,
            job_stat.int_dead_count,
            job_stat.int_depend_count,
            job_stat.int_eaten_count,
            job_stat.int_succeeded_count,
            job_stat.int_running_count,
            job_mem.int_max_rss,
            job_mem.int_gpu_mem_max
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
            job_mem.pk_job = OLD.pk_job;

        UPDATE
            job_history
        SET
            pk_dept = OLD.pk_dept,
            int_core_time_success = js.int_core_time_success,
            int_core_time_fail = js.int_core_time_fail,
            int_gpu_time_success = js.int_gpu_time_success,
            int_gpu_time_fail = js.int_gpu_time_fail,
            int_frame_count = OLD.int_frame_count,
            int_layer_count = OLD.int_layer_count,
            int_waiting_count = js.int_waiting_count,
            int_dead_count = js.int_dead_count,
            int_depend_count = js.int_depend_count,
            int_eaten_count = js.int_eaten_count,
            int_succeeded_count = js.int_succeeded_count,
            int_running_count = js.int_running_count,
            int_max_rss = js.int_max_rss,
            int_gpu_mem_max = js.int_gpu_mem_max,
            b_archived = true,
            int_ts_stopped = COALESCE(epoch(OLD.ts_stopped), epoch(current_timestamp))
        WHERE
            pk_job = OLD.pk_job;

    END IF;

    DELETE FROM depend WHERE pk_job_depend_on=OLD.pk_job OR pk_job_depend_er=OLD.pk_job;
    DELETE FROM frame WHERE pk_job=OLD.pk_job;
    DELETE FROM layer WHERE pk_job=OLD.pk_job;
    DELETE FROM job_env WHERE pk_job=OLD.pk_job;
    DELETE FROM job_stat WHERE pk_job=OLD.pk_job;
    DELETE FROM job_resource WHERE pk_job=OLD.pk_job;
    DELETE FROM job_usage WHERE pk_job=OLD.pk_job;
    DELETE FROM job_mem WHERE pk_job=OLD.pk_job;
    DELETE FROM comments WHERE pk_job=OLD.pk_job;

    RETURN OLD;
END
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__after_job_finished()
RETURNS TRIGGER AS $body$
DECLARE
    ts INT := cast(epoch(current_timestamp) as integer);
    js JobStatType;
    ls LayerStatType;
    one_layer RECORD;
BEGIN
    IF NOT EXISTS (SELECT FROM config WHERE str_key='DISABLE_HISTORY') THEN

        SELECT
            job_usage.int_core_time_success,
            job_usage.int_core_time_fail,
            job_usage.int_gpu_time_success,
            job_usage.int_gpu_time_fail,
            job_stat.int_waiting_count,
            job_stat.int_dead_count,
            job_stat.int_depend_count,
            job_stat.int_eaten_count,
            job_stat.int_succeeded_count,
            job_stat.int_running_count,
            job_mem.int_max_rss,
            job_mem.int_gpu_mem_max
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
            job_mem.pk_job = NEW.pk_job;

        UPDATE
            job_history
        SET
            pk_dept = NEW.pk_dept,
            int_core_time_success = js.int_core_time_success,
            int_core_time_fail = js.int_core_time_fail,
            int_gpu_time_success = js.int_gpu_time_success,
            int_gpu_time_fail = js.int_gpu_time_fail,
            int_frame_count = NEW.int_frame_count,
            int_layer_count = NEW.int_layer_count,
            int_waiting_count = js.int_waiting_count,
            int_dead_count = js.int_dead_count,
            int_depend_count = js.int_depend_count,
            int_eaten_count = js.int_eaten_count,
            int_succeeded_count = js.int_succeeded_count,
            int_running_count = js.int_running_count,
            int_max_rss = js.int_max_rss,
            int_gpu_mem_max = js.int_gpu_mem_max,
            int_ts_stopped = ts
        WHERE
            pk_job = NEW.pk_job;

        FOR one_layer IN (SELECT pk_layer from layer where pk_job = NEW.pk_job)
        LOOP
            SELECT
                layer_usage.int_core_time_success,
                layer_usage.int_core_time_fail,
                layer_usage.int_gpu_time_success,
                layer_usage.int_gpu_time_fail,
                layer_stat.int_total_count,
                layer_stat.int_waiting_count,
                layer_stat.int_dead_count,
                layer_stat.int_depend_count,
                layer_stat.int_eaten_count,
                layer_stat.int_succeeded_count,
                layer_stat.int_running_count,
                layer_mem.int_max_rss,
                layer_mem.int_gpu_mem_max
            INTO
                ls
            FROM
                layer_mem,
                layer_usage,
                layer_stat
            WHERE
                layer_usage.pk_layer = layer_mem.pk_layer
            AND
                layer_stat.pk_layer = layer_mem.pk_layer
            AND
                layer_mem.pk_layer = one_layer.pk_layer;

            UPDATE
                layer_history
            SET
                int_core_time_success = ls.int_core_time_success,
                int_core_time_fail = ls.int_core_time_fail,
                int_gpu_time_success = ls.int_gpu_time_success,
                int_gpu_time_fail = ls.int_gpu_time_fail,
                int_frame_count = ls.int_total_count,
                int_waiting_count = ls.int_waiting_count,
                int_dead_count = ls.int_dead_count,
                int_depend_count = ls.int_depend_count,
                int_eaten_count = ls.int_eaten_count,
                int_succeeded_count = ls.int_succeeded_count,
                int_running_count = ls.int_running_count,
                int_max_rss = ls.int_max_rss,
                int_gpu_mem_max = ls.int_gpu_mem_max
            WHERE
                pk_layer = one_layer.pk_layer;
        END LOOP;

    END IF;

    /**
     * Delete any local core assignments from this job.
     **/
    DELETE FROM job_local WHERE pk_job=NEW.pk_job;

    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__after_insert_layer()
RETURNS TRIGGER AS $body$
BEGIN
    INSERT INTO layer_stat (pk_layer_stat, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_resource (pk_layer_resource, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_usage (pk_layer_usage, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);
    INSERT INTO layer_mem (pk_layer_mem, pk_layer, pk_job) VALUES (NEW.pk_layer, NEW.pk_layer, NEW.pk_job);

    IF NOT EXISTS (SELECT FROM config WHERE str_key='DISABLE_HISTORY') THEN

        INSERT INTO layer_history
            (pk_layer, pk_job, str_name, str_type, int_cores_min, int_mem_min, int_gpus_min, int_gpu_mem_min, b_archived,str_services)
        VALUES
            (NEW.pk_layer, NEW.pk_job, NEW.str_name, NEW.str_type, NEW.int_cores_min, NEW.int_mem_min, NEW.int_gpus_min, NEW.int_gpu_mem_min, false, NEW.str_services);

    END IF;

    RETURN NEW;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__before_delete_layer()
RETURNS TRIGGER AS $body$
DECLARE
    js LayerStatType;
BEGIN
    IF NOT EXISTS (SELECT FROM config WHERE str_key='DISABLE_HISTORY') THEN

        SELECT
            layer_usage.int_core_time_success,
            layer_usage.int_core_time_fail,
            layer_usage.int_gpu_time_success,
            layer_usage.int_gpu_time_fail,
            layer_stat.int_total_count,
            layer_stat.int_waiting_count,
            layer_stat.int_dead_count,
            layer_stat.int_depend_count,
            layer_stat.int_eaten_count,
            layer_stat.int_succeeded_count,
            layer_stat.int_running_count,
            layer_mem.int_max_rss,
            layer_mem.int_gpu_mem_max
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
            layer_mem.pk_layer = OLD.pk_layer;

        UPDATE
            layer_history
        SET
            int_core_time_success = js.int_core_time_success,
            int_core_time_fail = js.int_core_time_fail,
            int_gpu_time_success = js.int_gpu_time_success,
            int_gpu_time_fail = js.int_gpu_time_fail,
            int_frame_count = js.int_total_count,
            int_waiting_count = js.int_waiting_count,
            int_dead_count = js.int_dead_count,
            int_depend_count = js.int_depend_count,
            int_eaten_count = js.int_eaten_count,
            int_succeeded_count = js.int_succeeded_count,
            int_running_count = js.int_running_count,
            int_max_rss = js.int_max_rss,
            int_gpu_mem_max = js.int_gpu_mem_max,
            b_archived = true
        WHERE
            pk_layer = OLD.pk_layer;

    END IF;

    DELETE FROM layer_resource where pk_layer=OLD.pk_layer;
    DELETE FROM layer_stat where pk_layer=OLD.pk_layer;
    DELETE FROM layer_usage where pk_layer=OLD.pk_layer;
    DELETE FROM layer_env where pk_layer=OLD.pk_layer;
    DELETE FROM layer_mem where pk_layer=OLD.pk_layer;
    DELETE FROM layer_output where pk_layer=OLD.pk_layer;

    RETURN OLD;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION trigger__frame_history_open()
RETURNS TRIGGER AS $body$
DECLARE
  str_pk_alloc VARCHAR(36) := null;
  int_checkpoint INT := 0;
BEGIN

    IF NOT EXISTS (SELECT FROM config WHERE str_key='DISABLE_HISTORY') THEN

        IF OLD.str_state = 'RUNNING' THEN

            IF NEW.int_exit_status = 299 THEN

              EXECUTE 'DELETE FROM frame_history WHERE int_ts_stopped = 0 AND pk_frame=$1' USING
                NEW.pk_frame;

            ELSE
              If NEW.str_state = 'CHECKPOINT' THEN
                  int_checkpoint := 1;
              END IF;

              EXECUTE
              'UPDATE
                  frame_history
              SET
                  int_mem_max_used=$1,
                  int_gpu_mem_max_used=$2,
                  int_ts_stopped=$3,
                  int_exit_status=$4,
                  int_checkpoint_count=$5
              WHERE
                  int_ts_stopped = 0 AND pk_frame=$6'
              USING
                  NEW.int_mem_max_used,
                  NEW.int_gpu_mem_max_used,
                  epoch(current_timestamp),
                  NEW.int_exit_status,
                  int_checkpoint,
                  NEW.pk_frame;
            END IF;
        END IF;

        IF NEW.str_state = 'RUNNING' THEN

          SELECT pk_alloc INTO str_pk_alloc FROM host WHERE str_name=NEW.str_host;

          EXECUTE
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
                int_gpus,
                int_gpu_mem_reserved,
                str_host,
                int_ts_started,
                pk_alloc
             )
             VALUES
                ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)'
             USING NEW.pk_frame,
                NEW.pk_layer,
                NEW.pk_job,
                NEW.str_name,
                'RUNNING',
                NEW.int_cores,
                NEW.int_mem_reserved,
                NEW.int_gpus,
                NEW.int_gpu_mem_reserved,
                NEW.str_host,
                epoch(current_timestamp),
                str_pk_alloc;
        END IF;

    END IF;
    RETURN NULL;

END;
$body$
LANGUAGE PLPGSQL;
