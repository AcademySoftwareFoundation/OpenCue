-- Indexes supporting the rewritten QUERY_PENDING_BY_SHOW_FACILITY_TAG used
-- by the Rust scheduler's per-cluster pending-job query. Together they
-- eliminate the cardinality blowup from the previous DISTINCT pk_job join
-- and bring per-call cost from multi-second on big shows down to <500ms.
--
-- OPERATIONAL NOTE
-- Flyway 5.2.0 (used by cuebot's test setup) wraps each migration in a
-- single transaction, and PostgreSQL rejects CREATE INDEX CONCURRENTLY
-- inside a transaction. The plain form below is safe for the embedded
-- test DB and for any environment where index-build downtime is acceptable.
--
-- For production deployments against populated tables (where AccessExclusive
-- locks during the GIN index build could be measurable), apply this
-- migration manually via `psql` with CONCURRENTLY *before* running Flyway,
-- then mark the row in flyway_schema_history yourself, e.g.:
--
--   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_layer_tags_array ...
--   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_pending_lookup ...
--   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_layer_stat_waiting ...
--   INSERT INTO flyway_schema_history(...) VALUES (44, ...);

-- GIN index on layer.str_tags for the && array-overlap test in the rewritten
-- QUERY_PENDING_BY_SHOW_FACILITY_TAG. Without this, tag matching is a sequential
-- scan over every layer row.
CREATE INDEX IF NOT EXISTS idx_layer_tags_array
    ON layer USING gin (string_to_array(REPLACE(str_tags, ' ', ''), '|'));

-- Composite filter index on job for the bookable-job WHERE clause.
-- Plain (non-functional) pk_facility column is intentional: the scheduler
-- now compares pk_facility as a case-sensitive string (Cuebot writes
-- canonical casing on insert), so the previous LOWER() expression index
-- is no longer needed.
CREATE INDEX IF NOT EXISTS idx_job_pending_lookup
    ON job (pk_show, pk_facility, str_state, b_paused)
    WHERE str_state = 'PENDING' AND b_paused = false;

-- Layer_stat lookup for the EXISTS subquery in the rewritten query. Restricts
-- the index to rows that actually have waiting frames, keeping it small.
CREATE INDEX IF NOT EXISTS idx_layer_stat_waiting
    ON layer_stat (pk_layer)
    WHERE int_waiting_count > 0;
