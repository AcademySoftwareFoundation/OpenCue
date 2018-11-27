  
/**
* Instead of a pending frames property, I've broken that
* out into waiting and depend so CueCommander can
* display group roll up data accurately.
**/
CREATE OR REPLACE FORCE VIEW "CUE3"."VS_FOLDER_COUNTS" AS 
SELECT
    folder.pk_folder,
    NVL(SUM(int_depend_count),0) AS int_depend_count,
    NVL(SUM(int_waiting_count),0) AS int_waiting_count,
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
 GROUP BY 
      folder.pk_folder;
