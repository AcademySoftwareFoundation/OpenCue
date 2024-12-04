-- Clear frame_state_display_overrides when a job gets deleted

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

    -- This is the only real change on the trigger
    DELETE FROM frame_state_display_overrides WHERE pk_frame in (
        select pk_frame from frame f where f.pk_job = OLD.pk_job
    );

    DELETE FROM frame WHERE pk_job=OLD.pk_job;
    DELETE FROM layer WHERE pk_job=OLD.pk_job;
    DELETE FROM job_env WHERE pk_job=OLD.pk_job;
    DELETE FROM job_stat WHERE pk_job=OLD.pk_job;
    DELETE FROM job_resource WHERE pk_job=OLD.pk_job;
    DELETE FROM job_usage WHERE pk_job=OLD.pk_job;
    DELETE FROM job_mem WHERE pk_job=OLD.pk_job;
    DELETE FROM job_post where pk_job = OLD.pk_job;
    DELETE FROM comments WHERE pk_job=OLD.pk_job;

    RETURN OLD;
END
$body$
LANGUAGE PLPGSQL;