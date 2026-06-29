-- Adds the per-show partition flag that determines which scheduler owns
-- accounting writes for a show:
--   false (default) -> Cuebot's existing transactional accounting path.
--   true            -> Rust scheduler is authoritative; Cuebot must not
--                      mutate the show's accounting rows.
--
-- The flag is wired through ShowDao/ShowInterface in PR-A but has no live
-- consumer until PR-B (Cuebot Redis publisher + show-aware unbookProc) and
-- PR-C (Rust scheduler accounting module). In PR-A all rows stay false in
-- practice, so behavior is unchanged.
--
-- recalculate_subs() is rewritten here (CREATE OR REPLACE) so that the
-- 2-hour maintenance task skips scheduler-managed shows, per the
-- "recalculate_subs() show-awareness" section of
-- docs/_docs/developer-guide/redis-accounting.md. The body is otherwise identical to
-- V20__recalculate_subs_gpu.sql with two narrow changes:
--   1) the initial UPDATE-to-zero of subscription is restricted to shows
--      with b_scheduler_managed = false, so Rust-owned rows are never
--      transiently zeroed;
--   2) the cursor's WHERE clause also filters on b_scheduler_managed = false.
-- The EXCEPTION-clause reference to r.show has also been fixed to r.show_name
-- (it would never compile if hit; the cursor aliases the column show_name).

ALTER TABLE show
    ADD COLUMN b_scheduler_managed BOOLEAN DEFAULT false NOT NULL;

CREATE OR REPLACE FUNCTION public.recalculate_subs(
    )
    RETURNS void
    LANGUAGE 'plpgsql'

    COST 100
    VOLATILE
AS $BODY$
DECLARE
    r RECORD;
    cur_burst bigint;
BEGIN
  UPDATE subscription SET int_cores = 0
    WHERE pk_show IN (SELECT pk_show FROM show WHERE b_scheduler_managed = false);
  UPDATE subscription SET int_gpus = 0
    WHERE pk_show IN (SELECT pk_show FROM show WHERE b_scheduler_managed = false);
  FOR r IN (select show.str_name as show_name,
                   proc.pk_show,
                   alloc.pk_alloc,
                   alloc.str_name as alloc_name,
                   sum(proc.int_cores_reserved) as c,
                   sum(proc.int_gpus_reserved) as d
            from show, proc, host, alloc
            where show.pk_show = proc.pk_show
              and proc.pk_host = host.pk_host
              AND host.pk_alloc = alloc.pk_alloc
              AND proc.b_local = false
              AND show.b_scheduler_managed = false
            group by show.str_name, proc.pk_show, alloc.pk_alloc, alloc.str_name)
  LOOP
     BEGIN
       SELECT int_burst INTO cur_burst FROM subscription WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;
       -- Also changing int_burst here to bypass VERIFY_SUBSCRIPTION trigger
       UPDATE subscription SET int_cores = r.c, int_burst = r.c, int_gpus = r.d WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;
       -- Put original int_burst back.
       UPDATE subscription SET int_burst = cur_burst WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;
     EXCEPTION
       WHEN NO_DATA_FOUND THEN
         -- ignore
         NULL;
       WHEN DATA_EXCEPTION THEN
         RAISE DATA_EXCEPTION USING MESSAGE = r.show_name||' '||r.alloc_name|| ' could not be fixed (over burst)';
     END;
  END LOOP;
END;
$BODY$;
