-- Adds ts_started / ts_stopped timestamp columns to layer_stat so the layer
-- activity window can be served as a direct column read instead of two
-- correlated aggregates against the frame table. Mirrors how
-- job.ts_started / job.ts_stopped are denormalized on the job row.
--
-- ts_started records when the layer's first frame entered RUNNING.
-- ts_stopped records when the layer's most recent frame left RUNNING.
-- The "stay at 0 until everything is done" semantic exposed by
-- Layer.stopTime() is applied at read time in WhiteboardDaoJdbc.LAYER_MAPPER
-- using the existing waiting / running / depend counters on layer_stat, so the
-- write path here can stay branch-free (always overwrite ts_stopped on exit
-- from RUNNING).

ALTER TABLE layer_stat
    ADD COLUMN ts_started TIMESTAMP (6) WITH TIME ZONE,
    ADD COLUMN ts_stopped TIMESTAMP (6) WITH TIME ZONE;

-- One-time backfill so existing layers expose their activity window
-- immediately after the migration runs. Layers whose frames never ran keep
-- both columns NULL (the proto default of 0 is what callers expect).
UPDATE layer_stat ls
SET ts_started = f.min_started,
    ts_stopped = f.max_stopped
FROM (
    SELECT pk_layer,
           MIN(ts_started) AS min_started,
           MAX(ts_stopped)  AS max_stopped
    FROM frame
    GROUP BY pk_layer
) f
WHERE ls.pk_layer = f.pk_layer;

-- Extend the existing frame-state-change trigger so it also maintains the
-- new timestamps. The trigger already fires AFTER UPDATE ON frame whenever
-- str_state changes (excluding the initial transition out of SETUP), so we
-- get the right write coverage for free:
--   * any transition INTO RUNNING stamps ts_started (first-writer-wins via
--     COALESCE, so re-runs and retries don't bump it).
--   * any transition OUT OF RUNNING stamps ts_stopped (latest-writer-wins).
--
-- The trigger copies NEW.ts_started / NEW.ts_stopped from the just-updated
-- frame row instead of sampling current_timestamp, so the layer-level value
-- agrees exactly with the underlying frame.ts_started / frame.ts_stopped.
-- That matters because FrameDaoJdbc.UPDATE_FRAME_STOPPED writes
-- "ts_stopped = current_timestamp + interval '1' second" on the frame row to
-- guarantee a non-zero duration on instant frames -- sampling
-- current_timestamp here would land the layer one second earlier than the
-- frame and break client-side cross-checks. COALESCE provides a defensive
-- fallback in case some future caller updates the state row without
-- restamping the timestamp columns.
CREATE OR REPLACE FUNCTION trigger__update_frame_status_counts()
RETURNS TRIGGER AS $body$
DECLARE
    s_old_status_col VARCHAR(32);
    s_new_status_col VARCHAR(32);
BEGIN
    s_old_status_col := 'int_' || OLD.str_state || '_count';
    s_new_status_col := 'int_' || NEW.str_state || '_count';

    EXECUTE 'UPDATE layer_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_layer=$1' USING NEW.pk_layer;

    EXECUTE 'UPDATE job_stat SET ' || s_old_status_col || '=' || s_old_status_col || ' -1, '
        || s_new_status_col || ' = ' || s_new_status_col || '+1 WHERE pk_job=$1' USING NEW.pk_job;

    -- Stamp the layer activity window from NEW so layer_stat.ts_started /
    -- ts_stopped agree exactly with the underlying frame row (matters because
    -- FrameDaoJdbc.UPDATE_FRAME_STOPPED writes
    -- ts_stopped = current_timestamp + interval '1' second on the frame).
    -- COALESCE provides a defensive fallback if a future caller updates the
    -- state without restamping the timestamp columns.
    IF NEW.str_state = 'RUNNING' THEN
        UPDATE layer_stat
        SET ts_started = COALESCE(ts_started, NEW.ts_started, current_timestamp)
        WHERE pk_layer = NEW.pk_layer;
    END IF;
    IF OLD.str_state = 'RUNNING' THEN
        UPDATE layer_stat
        SET ts_stopped = COALESCE(NEW.ts_stopped, current_timestamp)
        WHERE pk_layer = NEW.pk_layer;
    END IF;

    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;
