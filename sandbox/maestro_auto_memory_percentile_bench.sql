-- Times the Maestro auto memory percentile read (MaestroDao.getSucceededRssPercentile)
-- on a real database, before and after i_frame_layer_succeeded_rss exists.
-- Plain SQL: paste it into a pgAdmin query tool (or psql) and execute the whole
-- script. It works on a database without V52 and creates nothing permanent: the
-- sample table and the function live in this session only.
--
-- Before and after, in the same query tool tab (one session, so the second run
-- measures the same layers):
--   1. Execute this script: the "before" numbers.
--   2. Execute on its own, with auto-commit on (CONCURRENTLY can't run in a
--      transaction, nor in a batch with other statements):
--        CREATE INDEX CONCURRENTLY i_frame_layer_succeeded_rss
--            ON frame (pk_layer, int_mem_max_used) WHERE str_state = 'SUCCEEDED';
--   3. Execute this script again: the "after" numbers.
--
-- The sample is the 500 largest layers Maestro would read (pending jobs, at least
-- maestro.probe_frames = 8 succeeded frames): the cold-cache worst case, one read
-- of maestro.auto_mem_refresh_max_layers layers. Change the LIMIT for another size
-- (50 is a busy steady-state tick) and drop bench_layers to draw a new sample.

CREATE TEMP TABLE IF NOT EXISTS bench_layers (pk_layer VARCHAR(36) PRIMARY KEY);

INSERT INTO bench_layers
SELECT ls.pk_layer
FROM layer_stat ls
JOIN job j ON j.pk_job = ls.pk_job
WHERE j.str_state = 'PENDING' AND ls.int_succeeded_count >= 8
  AND NOT EXISTS (SELECT 1 FROM bench_layers)
ORDER BY ls.int_succeeded_count DESC
LIMIT 500;

-- Runs the read three times with EXPLAIN ANALYZE, with the same literal IN list
-- Cuebot sends. Run 1 shows a cold cache (Buffers: read=), run 3 the warm steady
-- state (Buffers: hit=).
CREATE OR REPLACE FUNCTION pg_temp.bench_auto_memory_percentile()
RETURNS TABLE (run INT, line TEXT) AS $$
DECLARE
    ids TEXT;
BEGIN
    SELECT string_agg(quote_literal(b.pk_layer), ',') INTO ids FROM bench_layers b;

    run := 0;
    line := 'index present: ' || (to_regclass('i_frame_layer_succeeded_rss') IS NOT NULL)
        || ', size: ' || coalesce(
            pg_size_pretty(pg_relation_size(to_regclass('i_frame_layer_succeeded_rss'))), '-');
    RETURN NEXT;
    SELECT 'sample: ' || count(*) || ' layers, ' || coalesce(sum(ls.int_succeeded_count), 0)
        || ' succeeded frames' INTO line
    FROM bench_layers b JOIN layer_stat ls ON ls.pk_layer = b.pk_layer;
    RETURN NEXT;
    IF ids IS NULL THEN
        line := 'no layer matches the sample; nothing to measure';
        RETURN NEXT;
        RETURN;
    END IF;

    FOR i IN 1..3 LOOP
        run := i;
        FOR line IN EXECUTE
            'EXPLAIN (ANALYZE, BUFFERS) SELECT pk_layer, percentile_cont(0.9) WITHIN GROUP '
            || '(ORDER BY int_mem_max_used) AS rss_pct FROM frame WHERE pk_layer IN (' || ids
            || ') AND str_state = ''SUCCEEDED'' AND int_mem_max_used > 0 GROUP BY pk_layer'
        LOOP
            -- The Index Cond repeats the whole IN list; it says nothing worth reading.
            CONTINUE WHEN line LIKE '%Index Cond:%' OR line LIKE '%Recheck Cond:%'
                OR line LIKE '%Filter:%';
            RETURN NEXT;
        END LOOP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

SELECT run, line FROM pg_temp.bench_auto_memory_percentile();
