
-- Functions

CREATE OR REPLACE FUNCTION recalculate_subs()
RETURNS VOID AS $body$
DECLARE
    r RECORD;
BEGIN
  --
  -- concatenates all tags in host_tag and sets host.str_tags
  --
  UPDATE subscription SET int_cores = 0;
  UPDATE subscription SET int_gpus = 0;
  FOR r IN
    SELECT
      proc.pk_show,
      alloc.pk_alloc,
      SUM(CAST(proc.int_cores_reserved AS numeric)) as c,
      SUM(CAST(proc.int_gpus_reserved AS numeric)) as d
    FROM proc, host, alloc
    WHERE proc.pk_host = host.pk_host AND host.pk_alloc = alloc.pk_alloc
    GROUP BY proc.pk_show, alloc.pk_alloc
  LOOP
    UPDATE subscription SET int_cores = r.c, int_gpus = r.d WHERE pk_alloc=r.pk_alloc AND pk_show=r.pk_show;

  END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION tmp_populate_folder()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT
          pk_folder,
          pk_show,
          SUM(CAST(int_cores AS numeric)) AS c,
          SUM(CAST(int_gpus AS numeric)) AS d
        FROM job, job_resource
        WHERE job.pk_job = job_resource.pk_job
        GROUP by pk_folder, pk_show
    LOOP
        UPDATE folder_resource SET int_cores = t.c, int_gpus = t.d WHERE pk_folder = t.pk_folder;
        COMMIT;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION tmp_populate_point()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT
          pk_dept,
          pk_show,
          SUM(CAST(int_cores AS numeric)) AS c,
          SUM(CAST(int_gpus AS numeric)) AS d
        FROM job, job_resource
        WHERE job.pk_job = job_resource.pk_job
        GROUP BY pk_dept, pk_show
    LOOP
        UPDATE point SET int_cores = t.c , int_gpus = t.d WHERE pk_show = t.pk_show AND pk_dept = t.pk_dept;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


CREATE OR REPLACE FUNCTION tmp_populate_sub()
RETURNS VOID AS $body$
DECLARE
    t RECORD;
BEGIN
    FOR t IN
        SELECT
          proc.pk_show,
          host.pk_alloc,
          SUM(CAST(int_cores_reserved AS numeric)) AS c,
          SUM(CAST(int_gpus_reserved AS numeric)) AS d
        FROM proc, host
        WHERE proc.pk_host = host.pk_host
        GROUP BY proc.pk_show, host.pk_alloc
    LOOP
        UPDATE subscription SET int_cores = t.c, int_gpus = t.d WHERE pk_show = t.pk_show AND pk_alloc = t.pk_alloc;
    END LOOP;
END;
$body$
LANGUAGE PLPGSQL;


-- Views

DROP VIEW vs_show_resource;
CREATE VIEW vs_show_resource (pk_show, int_cores, int_gpus) AS
  SELECT
        job.pk_show,
        SUM(CAST(int_cores as numeric)) AS int_cores,
        SUM(CAST(int_gpus as numeric)) AS int_gpus
    FROM
       job,
       job_resource
    WHERE
       job.pk_job = job_resource.pk_job
    AND
       job.str_state='PENDING'
    GROUP BY
       job.pk_show;


DROP VIEW vs_show_stat;
CREATE VIEW vs_show_stat (pk_show, int_pending_count, int_running_count, int_dead_count, int_job_count) AS
  SELECT
        job.pk_show,
        SUM(CAST(int_waiting_count+int_depend_count AS numeric)) AS int_pending_count,
        SUM(CAST(int_running_count AS numeric)) AS int_running_count,
        SUM(CAST(int_dead_count AS numeric)) AS int_dead_count,
        COUNT(1) AS int_job_count
    FROM
        job_stat,
        job
    WHERE
        job_stat.pk_job = job.pk_job
    AND
        job.str_state = 'PENDING'
    GROUP BY job.pk_show;


DROP VIEW vs_job_resource;
CREATE VIEW vs_job_resource (pk_job, int_procs, int_cores, int_gpus, int_mem_reserved) AS
  SELECT
       job.pk_job,
       COUNT(proc.pk_proc) AS int_procs,
       COALESCE(SUM(CAST(int_cores_reserved AS numeric)),0) AS int_cores,
       COALESCE(SUM(CAST(int_gpus_reserved AS numeric)),0) AS int_gpus,
       COALESCE(SUM(CAST(int_mem_reserved AS numeric)),0) AS int_mem_reserved
    FROM
       job LEFT JOIN proc ON (proc.pk_job = job.pk_job)
    GROUP BY
       job.pk_job;


DROP VIEW vs_alloc_usage;
CREATE VIEW vs_alloc_usage (pk_alloc, int_cores, int_idle_cores, int_running_cores, int_locked_cores, int_available_cores, int_gpus, int_idle_gpus, int_running_gpus, int_locked_gpus, int_available_gpus, int_hosts, int_locked_hosts, int_down_hosts) AS
  SELECT
        alloc.pk_alloc,
        COALESCE(SUM(CAST(host.int_cores AS numeric)),0) AS int_cores,
        COALESCE(SUM(CAST(host.int_cores_idle AS numeric)),0) AS int_idle_cores,
        COALESCE(SUM(CAST(host.int_cores - host.int_cores_idle AS numeric)),0) as int_running_cores,
        COALESCE((SELECT SUM(CAST(int_cores AS numeric)) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND (str_lock_state='NIMBY_LOCKED' OR str_lock_state='LOCKED')),0) AS int_locked_cores,
        COALESCE((SELECT SUM(CAST(int_cores_idle AS numeric)) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND h.str_lock_state='OPEN' AND hs.str_state ='UP'),0) AS int_available_cores,
        COALESCE(SUM(CAST(host.int_gpus AS numeric)),0) AS int_gpus,
        COALESCE(SUM(CAST(host.int_gpus_idle AS numeric)),0) AS int_idle_gpus,
        COALESCE(SUM(CAST(host.int_gpus - host.int_gpus_idle AS numeric)),0) as int_running_gpus,
        COALESCE((SELECT SUM(CAST(int_gpus AS numeric)) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND (str_lock_state='NIMBY_LOCKED' OR str_lock_state='LOCKED')),0) AS int_locked_gpus,
        COALESCE((SELECT SUM(CAST(int_gpus_idle AS numeric)) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND h.str_lock_state='OPEN' AND hs.str_state ='UP'),0) AS int_available_gpus,
        COUNT(host.pk_host) AS int_hosts,
        (SELECT COUNT(*) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND str_lock_state='LOCKED') AS int_locked_hosts,
        (SELECT COUNT(*) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND hs.str_state='DOWN') AS int_down_hosts
    FROM
        alloc LEFT JOIN host ON (alloc.pk_alloc = host.pk_alloc)
    GROUP BY
        alloc.pk_alloc;


DROP VIEW vs_folder_counts;
CREATE VIEW vs_folder_counts (pk_folder, int_depend_count, int_waiting_count, int_running_count, int_dead_count, int_cores, int_gpus, int_job_count) AS
  SELECT
    folder.pk_folder,
    COALESCE(SUM(CAST(int_depend_count AS numeric)),0) AS int_depend_count,
    COALESCE(SUM(CAST(int_waiting_count AS numeric)),0) AS int_waiting_count,
    COALESCE(SUM(CAST(int_running_count AS numeric)),0) AS int_running_count,
    COALESCE(SUM(CAST(int_dead_count AS numeric)),0) AS int_dead_count,
    COALESCE(SUM(CAST(int_cores AS numeric)),0) AS int_cores,
    COALESCE(SUM(CAST(int_gpus AS numeric)),0) AS int_gpus,
    COALESCE(COUNT(job.pk_job),0) AS int_job_count
FROM
    folder
      LEFT JOIN
        job ON (folder.pk_folder = job.pk_folder AND job.str_state='PENDING')
      LEFT JOIN
        job_stat ON (job.pk_job = job_stat.pk_job)
      LEFT JOIN
        job_resource ON (job.pk_job = job_resource.pk_job)
 GROUP BY
      folder.pk_folder;
