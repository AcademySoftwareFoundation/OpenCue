-- Move frame_history writes off the frame UPDATE hot path.
--
-- trigger__frame_history_open used to INSERT/UPDATE frame_history inline on every frame state
-- change into or out of RUNNING. frame_history is large and carries 9 random-key indexes, so
-- those writes get slower as the table grows, and every frame completion paid for them.
--
-- The trigger now appends one narrow row to frame_history_queue in the same transaction, so an
-- event commits or rolls back together with the frame change. Cuebot drains the queue in
-- batches with frame_history_drain(), which applies the events to frame_history with the
-- same semantics the trigger used to have. frame_history therefore lags by up to one drain
-- interval (history.frame_drain_interval_ms).
--
-- Ordering: events for one frame are produced by transactions that serialize on the frame's
-- row lock, so a later event always gets a larger id and is never visible before an earlier
-- one. A single drainer (advisory lock) applying events in id order preserves that order.
--
-- A run whose start and end land in the same batch is written as one finished frame_history
-- row, which skips the UPDATE (and its 9 index entries and dead tuple) for short frames. A
-- start followed by a discard (exit 299) in the same batch writes nothing.

CREATE TABLE frame_history_queue (
    id BIGSERIAL PRIMARY KEY,
    -- S = frame started RUNNING, E = frame left RUNNING, X = discard the open run (exit 299)
    str_event CHAR(1) NOT NULL,
    pk_frame VARCHAR(36) NOT NULL,
    int_ts INT NOT NULL,
    -- S payload
    pk_layer VARCHAR(36),
    pk_job VARCHAR(36),
    str_name VARCHAR(256),
    str_host VARCHAR(256),
    pk_alloc VARCHAR(36),
    int_cores INT,
    int_mem_reserved BIGINT,
    int_gpus INT,
    int_gpu_mem_reserved BIGINT,
    -- E payload
    int_mem_max_used BIGINT,
    int_gpu_mem_max_used BIGINT,
    int_exit_status BIGINT,
    int_checkpoint_count INT
);

COMMENT ON TABLE frame_history_queue IS
    'Pending frame_history events, written by trigger__frame_history_open and applied by frame_history_drain()';


CREATE OR REPLACE FUNCTION trigger__frame_history_open()
RETURNS TRIGGER AS $body$
DECLARE
    ts INT;
BEGIN
    IF EXISTS (SELECT FROM config WHERE str_key='DISABLE_HISTORY') THEN
        RETURN NULL;
    END IF;

    ts := epoch(current_timestamp);

    IF OLD.str_state = 'RUNNING' THEN
        INSERT INTO frame_history_queue
            (str_event, pk_frame, int_ts, int_mem_max_used, int_gpu_mem_max_used,
             int_exit_status, int_checkpoint_count)
        VALUES
            (CASE WHEN NEW.int_exit_status = 299 THEN 'X' ELSE 'E' END,
             NEW.pk_frame, ts, NEW.int_mem_max_used, NEW.int_gpu_mem_max_used,
             NEW.int_exit_status, CASE WHEN NEW.str_state = 'CHECKPOINT' THEN 1 ELSE 0 END);
    END IF;

    IF NEW.str_state = 'RUNNING' THEN
        INSERT INTO frame_history_queue
            (str_event, pk_frame, int_ts, pk_layer, pk_job, str_name, str_host, pk_alloc,
             int_cores, int_mem_reserved, int_gpus, int_gpu_mem_reserved)
        VALUES
            ('S', NEW.pk_frame, ts, NEW.pk_layer, NEW.pk_job, NEW.str_name, NEW.str_host,
             (SELECT pk_alloc FROM host WHERE str_name = NEW.str_host),
             NEW.int_cores, NEW.int_mem_reserved, NEW.int_gpus, NEW.int_gpu_mem_reserved);
    END IF;

    RETURN NULL;
END;
$body$
LANGUAGE PLPGSQL;


-- Applies one queued event to frame_history. When ev is a start and stop is the end event of
-- the same run, writes the finished run as a single row. Returns false when the event was
-- dropped because its job or layer has no history row (history purged, or DISABLE_HISTORY was
-- set when the job was launched); inserting it would violate frame_history's foreign keys.
CREATE FUNCTION frame_history_apply(ev frame_history_queue, stop frame_history_queue DEFAULT NULL)
RETURNS BOOLEAN AS $body$
BEGIN
    IF ev.str_event = 'S' THEN
        INSERT INTO frame_history
            (pk_frame, pk_layer, pk_job, str_name, str_state, int_cores, int_mem_reserved,
             int_gpus, int_gpu_mem_reserved, str_host, int_ts_started, pk_alloc,
             int_ts_stopped, int_mem_max_used, int_gpu_mem_max_used, int_exit_status,
             int_checkpoint_count)
        SELECT
            ev.pk_frame, ev.pk_layer, ev.pk_job, ev.str_name, 'RUNNING', ev.int_cores,
            ev.int_mem_reserved, ev.int_gpus, ev.int_gpu_mem_reserved,
            -- frame.str_host is wider than frame_history.str_host.
            left(ev.str_host, 64), ev.int_ts, ev.pk_alloc,
            -- Open run unless stop is given; these are the frame_history column defaults.
            COALESCE(stop.int_ts, 0), COALESCE(stop.int_mem_max_used, 0),
            COALESCE(stop.int_gpu_mem_max_used, 0), COALESCE(stop.int_exit_status, -1),
            COALESCE(stop.int_checkpoint_count, 0)
        WHERE EXISTS (SELECT FROM job_history WHERE pk_job = ev.pk_job)
          AND EXISTS (SELECT FROM layer_history WHERE pk_layer = ev.pk_layer);
        RETURN FOUND;
    ELSIF ev.str_event = 'E' THEN
        UPDATE frame_history SET
            int_mem_max_used = ev.int_mem_max_used,
            int_gpu_mem_max_used = ev.int_gpu_mem_max_used,
            int_ts_stopped = ev.int_ts,
            int_exit_status = ev.int_exit_status,
            int_checkpoint_count = ev.int_checkpoint_count
        WHERE int_ts_stopped = 0 AND pk_frame = ev.pk_frame;
    ELSIF ev.str_event = 'X' THEN
        DELETE FROM frame_history WHERE int_ts_stopped = 0 AND pk_frame = ev.pk_frame;
    END IF;
    RETURN true;
END;
$body$
LANGUAGE PLPGSQL;


-- Drains up to p_limit queued events, oldest first, and removes them from the queue in the
-- same transaction.
--
-- p_wait: block until the drain lock is free instead of returning immediately when another
--         session is draining.
-- p_safe: apply each event in its own subtransaction and drop (with a WARNING in the server
--         log) any event that fails, so a single bad event cannot block the queue. Slower;
--         meant as the fallback after a normal drain fails.
--
-- drained counts events removed from the queue; skipped counts the subset that was dropped
-- instead of applied; merged counts runs whose start and end were written as one row.
CREATE FUNCTION frame_history_drain(p_limit INT, p_wait BOOLEAN DEFAULT false,
        p_safe BOOLEAN DEFAULT false, OUT drained INT, OUT skipped INT, OUT merged INT)
AS $body$
DECLARE
    -- ASCII "FrmHist", shared by every Cuebot on the database.
    lock_key CONSTANT BIGINT := 19829062061618036;
    r RECORD;
    ev frame_history_queue;
    stop frame_history_queue;
    is_merge BOOLEAN;
    applied BOOLEAN;
BEGIN
    drained := 0;
    skipped := 0;
    merged := 0;

    IF p_wait THEN
        PERFORM pg_advisory_xact_lock(lock_key);
    ELSIF NOT pg_try_advisory_xact_lock(lock_key) THEN
        RETURN;
    END IF;

    -- A frame leaves RUNNING before it can start again, so a start's next event in the batch
    -- is always the end (E) or discard (X) of that same run.
    FOR r IN
        SELECT b.q AS ev,
               lead(b.q) OVER w AS next_ev,
               lag((b.q).str_event) OVER w AS prev_event
        FROM (SELECT q FROM frame_history_queue q ORDER BY q.id LIMIT p_limit) b
        WINDOW w AS (PARTITION BY (b.q).pk_frame ORDER BY (b.q).id)
        ORDER BY (b.q).id
    LOOP
        ev := r.ev;
        is_merge := ev.str_event = 'S' AND (r.next_ev).str_event IS NOT DISTINCT FROM 'E';
        stop := CASE WHEN is_merge THEN r.next_ev END;
        applied := true;

        IF ev.str_event = 'S' AND (r.next_ev).str_event = 'X' THEN
            -- Started and discarded within the batch: nothing to write.
            NULL;
        ELSIF ev.str_event IN ('E', 'X') AND r.prev_event = 'S' THEN
            -- Already handled together with its start.
            NULL;
        ELSIF p_safe THEN
            BEGIN
                applied := frame_history_apply(ev, stop);
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'frame_history_drain: dropped event % (%) for frame %: %',
                    ev.id, ev.str_event, ev.pk_frame, SQLERRM;
                applied := false;
            END;
        ELSE
            applied := frame_history_apply(ev, stop);
        END IF;

        IF NOT applied THEN
            skipped := skipped + 1;
        ELSIF is_merge THEN
            merged := merged + 1;
        END IF;
        DELETE FROM frame_history_queue WHERE id = ev.id;
        drained := drained + 1;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;
