/*
* Views are mainly used by the whiteboard as a quick
* way to roll up data and include it as a simple join
* rather than lots of subselects.
*/

/*
* A view which dispays the subscriptions plus the
* number of cores used.
*/   
CREATE OR REPLACE VIEW vs_sub AS
select 
  subscription.pk_subscription,
  subscription.pk_alloc,
  subscription.pk_show,
  subscription.str_name,
  subscription.int_size,
  subscription.int_burst,
  (
  SELECT 
    NVL(SUM(proc.int_cores_reserved),0) 
  FROM 
    host,proc 
  WHERE 
    host.pk_host = proc.pk_host 
  AND 
    host.pk_alloc = subscription.pk_alloc 
  AND 
    proc.pk_show = subscription.pk_show
  )  AS int_cores
  FROM 
    subscription;


/**
* Frame counts by show
**/
CREATE OR REPLACE VIEW cue3.vs_show_stat AS
    SELECT
        job.pk_show,
        SUM(int_waiting_count+int_depend_count) AS int_pending_count,
        SUM(int_running_count) AS int_running_count,
        SUM(int_dead_count) AS int_dead_count,
        COUNT(1) AS int_job_count
    FROM
        job_stat,
        job
    WHERE
        job_stat.pk_job = job.pk_job
    AND
        job.str_state = 'Pending'
    GROUP BY job.pk_show;

/** 
* Frame counts by folder
**/
CREATE OR REPLACE VIEW cue3.vs_folder_counts AS
    SELECT
        folder.pk_folder,
        NVL(SUM(int_waiting_count+int_depend_count),0) AS int_pending_count,
        NVL(SUM(int_running_count),0) AS int_running_count,
        NVL(SUM(int_dead_count),0) AS int_dead_count,
        NVL(SUM(int_cores),0) AS int_cores,
        NVL(COUNT(job.pk_job),0) AS int_job_count
    FROM
        folder 
          LEFT JOIN 
            job ON (folder.pk_folder = job.pk_folder AND job.str_state='Pending')
          LEFT JOIN
            job_stat ON (job.pk_job = job_stat.pk_job)
          LEFT JOIN
            job_resource ON (job.pk_job = job_resource.pk_job)
    GROUP BY folder.pk_folder;  


/**
* Resources by show.
**/
CREATE OR REPLACE VIEW cue3.vs_show_resource AS
    SELECT
        job.pk_show,
        SUM(int_cores) AS int_cores
    FROM
       job,
       job_resource
    WHERE
       job.pk_job = job_resource.pk_job
    AND
       job.str_state='Pending'
    GROUP BY
       job.pk_show;

/**
* Allocation usage by host state.  Used in the whiteboard.
**/       
CREATE OR REPLACE VIEW cue3.vs_alloc_usage AS
    SELECT
        alloc.pk_alloc,
        NVL(SUM(host.int_cores),0) AS int_cores,
        NVL(SUM(host.int_cores_idle),0) AS int_idle_cores,
        NVL(SUM(host.int_cores - host.int_cores_idle),0) as int_running_cores,
        NVL((SELECT SUM(int_cores) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND (str_lock_state='NimbyLocked' OR str_lock_state='Locked')),0) AS int_locked_cores,
        NVL((SELECT SUM(int_cores_idle) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND h.str_lock_state='Open' AND hs.str_state ='Up'),0) AS int_available_cores,
        COUNT(host.pk_host) AS int_hosts,
        (SELECT COUNT(*) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND str_lock_state='Locked') AS int_locked_hosts,
        (SELECT COUNT(*) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND hs.str_state='Down') AS int_down_hosts         
    FROM
        alloc LEFT JOIN host ON (alloc.pk_alloc = host.pk_alloc)
    GROUP BY
        alloc.pk_alloc;      
        
        
        
        
        

  
