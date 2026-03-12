-- Create an index on pk_job for jobs that are not finished
CREATE INDEX idx_job_active_pkjob ON job(pk_job) WHERE str_state <> 'FINISHED';
