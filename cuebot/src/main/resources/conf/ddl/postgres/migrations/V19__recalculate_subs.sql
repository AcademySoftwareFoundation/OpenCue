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
  --
  -- concatenates all tags in host_tag and sets host.str_tags
  --
  UPDATE subscription SET int_cores = 0;
  FOR r IN (select show.str_name as show_name, proc.pk_show, alloc.pk_alloc, alloc.str_name as alloc_name, sum(proc.int_cores_reserved) as c
            from show, proc, host, alloc
            where show.pk_show = proc.pk_show and proc.pk_host = host.pk_host AND host.pk_alloc = alloc.pk_alloc AND proc.b_local = false
            group by show.str_name, proc.pk_show, alloc.pk_alloc, alloc.str_name)
  LOOP
     BEGIN
       SELECT int_burst INTO cur_burst FROM subscription WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;
       -- Also changing int_burst here to bypass VERIFY_SUBSCRIPTION trigger
       UPDATE subscription SET int_cores = r.c, int_burst = r.c WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;
       -- Put original int_burst back.
       UPDATE subscription SET int_burst = cur_burst WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;
     EXCEPTION
       WHEN NO_DATA_FOUND THEN
         -- ignore
         NULL;
       WHEN DATA_EXCEPTION THEN
	 RAISE DATA_EXCEPTION USING MESSAGE = r.show||' '||r.alloc_name|| ' could not be fixed (over burst)';
     END;
  END LOOP;
END;
$BODY$;
