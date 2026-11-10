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
