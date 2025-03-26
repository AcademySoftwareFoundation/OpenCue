/* Update layestattype to include new columns and fix ordering of columns as its used in update statement in trigger*/

DROP TYPE public.layerstattype;

CREATE TYPE public.layerstattype AS
(
        int_cores_min bigint,
        int_mem_min bigint,
        int_core_time_success bigint,
        int_core_time_fail bigint,
        int_gpu_time_success bigint,
        int_gpu_time_fail bigint,
        int_total_count bigint,
        int_waiting_count bigint,
        int_dead_count bigint,
        int_depend_count bigint,
        int_eaten_count bigint,
        int_succeeded_count bigint,
        int_running_count bigint,
        int_max_rss bigint,
        int_gpu_mem_max bigint
);

/* update trigger to include new columns in update for layer_history */
-- FUNCTION: public.trigger__after_job_finished()

-- DROP FUNCTION IF EXISTS public.trigger__after_job_finished();

CREATE OR REPLACE FUNCTION public.trigger__after_job_finished()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
DECLARE
    ts INT := cast(epoch(current_timestamp) as integer);
    js JobStatType;
    ls LayerStatType;
    one_layer RECORD;
BEGIN
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
            layer.int_cores_min,
            layer.int_mem_min,
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
            layer,
            layer_mem,
            layer_usage,
            layer_stat
        WHERE
            layer_mem.pk_layer = layer.pk_layer
        AND
            layer_usage.pk_layer = layer.pk_layer
        AND
            layer_stat.pk_layer = layer.pk_layer
        AND
            layer.pk_layer = one_layer.pk_layer;
        UPDATE
            layer_history
        SET
            int_cores_min = ls.int_cores_min,
            int_mem_min = ls.int_mem_min,
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

    /**
     * Delete any local core assignments from this job.
     **/
    DELETE FROM job_local WHERE pk_job=NEW.pk_job;

    RETURN NEW;
END;
$BODY$;

-- FUNCTION: public.trigger__before_delete_layer()

-- DROP FUNCTION IF EXISTS public.trigger__before_delete_layer();

CREATE OR REPLACE FUNCTION public.trigger__before_delete_layer()
    RETURNS trigger
    LANGUAGE 'plpgsql'
    COST 100
    VOLATILE NOT LEAKPROOF
AS $BODY$
DECLARE
    ls LayerStatType;
BEGIN
    SELECT
        layer.int_cores_min,
        layer.int_mem_min,
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
        layer,
        layer_mem,
        layer_usage,
        layer_stat
    WHERE
        layer_mem.pk_layer = layer.pk_layer
    AND
        layer_usage.pk_layer = layer.pk_layer
    AND
        layer_stat.pk_layer = layer.pk_layer
    AND
        layer.pk_layer = OLD.pk_layer;
    UPDATE
        layer_history
    SET
        int_cores_min = ls.int_cores_min,
        int_mem_min = ls.int_mem_min,
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
        int_gpu_mem_max = ls.int_gpu_mem_max,
        b_archived = true
    WHERE
        pk_layer = OLD.pk_layer;

    DELETE FROM layer_resource where pk_layer=OLD.pk_layer;
    DELETE FROM layer_stat where pk_layer=OLD.pk_layer;
    DELETE FROM layer_usage where pk_layer=OLD.pk_layer;
    DELETE FROM layer_env where pk_layer=OLD.pk_layer;
    DELETE FROM layer_mem where pk_layer=OLD.pk_layer;
    DELETE FROM layer_output where pk_layer=OLD.pk_layer;

    RETURN OLD;
END;
$BODY$;
