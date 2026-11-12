-- Maestro auto memory (docs/_docs/developer-guide/maestro.md section 3.9).
--
-- layer_mem.int_mem_booked: the per-frame memory (KB) Maestro last booked the
-- layer at, published for the GUI. 0 means Maestro has not sized it yet.
-- Written only by the Maestro leader, and only when the value changes.
--
-- frame.int_mem_retry: the memory floor (KB) for this frame's next attempt
-- after it was killed for running out of memory. 0 means no floor. Cleared
-- when the frame succeeds.
--
-- Additive: both columns are NOT NULL with a constant default, which on
-- PostgreSQL 11+ is a metadata-only change, so frame is not rewritten. An
-- older Cuebot keeps working against a migrated database.
ALTER TABLE layer_mem ADD COLUMN IF NOT EXISTS int_mem_booked BIGINT NOT NULL DEFAULT 0;
ALTER TABLE frame ADD COLUMN IF NOT EXISTS int_mem_retry BIGINT NOT NULL DEFAULT 0;

-- The Maestro leader reads each auto memory layer's rss percentile over its
-- succeeded frames (MaestroDao.getSucceededRssPercentile). This index serves
-- that read as an index-only scan already in rss order, instead of fetching
-- and sorting every frame of the layer.
--
-- On a large production frame table, build it out-of-band first with
-- CREATE INDEX CONCURRENTLY (not allowed inside Flyway's transaction) under
-- the same name, so writes to frame are not blocked meanwhile. The IF NOT
-- EXISTS below then makes this statement a no-op when Flyway runs it.
CREATE INDEX IF NOT EXISTS i_frame_layer_succeeded_rss
    ON frame (pk_layer, int_mem_max_used)
    WHERE str_state = 'SUCCEEDED';
