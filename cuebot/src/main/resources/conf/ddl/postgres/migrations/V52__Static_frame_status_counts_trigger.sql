-- The frame state-change trigger as two static statements instead of four
-- dynamic ones. EXECUTE re-plans its SQL on every call and the layer's
-- ts_started/ts_stopped stamps were two more UPDATEs of the same layer_stat
-- row; each frame start or stop paid four plans and three row versions on a
-- hot row. The counts are now a delta per column, the stamps ride in the same
-- UPDATE, and the plans are cached per session. Counting is unchanged from V43.
--
-- A transaction that sets cue.batch_counts applies the counts itself, once per
-- batch (FrameDaoJdbc.applyBatchCounts), and the trigger stands aside.
CREATE OR REPLACE FUNCTION trigger__update_frame_status_counts()
RETURNS TRIGGER AS $body$
BEGIN
    IF current_setting('cue.batch_counts', true) = 'on' THEN
        RETURN NULL;
    END IF;
    UPDATE layer_stat SET
        int_waiting_count = int_waiting_count
            + (NEW.str_state = 'WAITING')::int - (OLD.str_state = 'WAITING')::int,
        int_running_count = int_running_count
            + (NEW.str_state = 'RUNNING')::int - (OLD.str_state = 'RUNNING')::int,
        int_dead_count = int_dead_count
            + (NEW.str_state = 'DEAD')::int - (OLD.str_state = 'DEAD')::int,
        int_depend_count = int_depend_count
            + (NEW.str_state = 'DEPEND')::int - (OLD.str_state = 'DEPEND')::int,
        int_eaten_count = int_eaten_count
            + (NEW.str_state = 'EATEN')::int - (OLD.str_state = 'EATEN')::int,
        int_succeeded_count = int_succeeded_count
            + (NEW.str_state = 'SUCCEEDED')::int - (OLD.str_state = 'SUCCEEDED')::int,
        int_checkpoint_count = int_checkpoint_count
            + (NEW.str_state = 'CHECKPOINT')::int - (OLD.str_state = 'CHECKPOINT')::int,
        ts_started = CASE WHEN NEW.str_state = 'RUNNING'
            THEN COALESCE(ts_started, NEW.ts_started, current_timestamp) ELSE ts_started END,
        ts_stopped = CASE WHEN OLD.str_state = 'RUNNING'
            THEN COALESCE(NEW.ts_stopped, current_timestamp) ELSE ts_stopped END
    WHERE pk_layer = NEW.pk_layer;

    UPDATE job_stat SET
        int_waiting_count = int_waiting_count
            + (NEW.str_state = 'WAITING')::int - (OLD.str_state = 'WAITING')::int,
        int_running_count = int_running_count
            + (NEW.str_state = 'RUNNING')::int - (OLD.str_state = 'RUNNING')::int,
        int_dead_count = int_dead_count
            + (NEW.str_state = 'DEAD')::int - (OLD.str_state = 'DEAD')::int,
        int_depend_count = int_depend_count
            + (NEW.str_state = 'DEPEND')::int - (OLD.str_state = 'DEPEND')::int,
        int_eaten_count = int_eaten_count
            + (NEW.str_state = 'EATEN')::int - (OLD.str_state = 'EATEN')::int,
        int_succeeded_count = int_succeeded_count
            + (NEW.str_state = 'SUCCEEDED')::int - (OLD.str_state = 'SUCCEEDED')::int,
        int_checkpoint_count = int_checkpoint_count
            + (NEW.str_state = 'CHECKPOINT')::int - (OLD.str_state = 'CHECKPOINT')::int
    WHERE pk_job = NEW.pk_job;

    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;
