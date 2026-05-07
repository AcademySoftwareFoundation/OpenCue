CREATE INDEX IF NOT EXISTS i_depend_active_er_job_frame
ON depend (pk_job_depend_er, pk_frame_depend_er)
WHERE b_active = true
AND pk_frame_depend_er IS NOT NULL;

CREATE INDEX IF NOT EXISTS i_depend_active_er_job_layer
ON depend (pk_job_depend_er, pk_layer_depend_er)
WHERE b_active = true
 AND pk_frame_depend_er IS NULL
 AND pk_layer_depend_er IS NOT NULL;

CREATE INDEX IF NOT EXISTS i_depend_active_er_job_only
ON depend (pk_job_depend_er)
WHERE b_active = true
AND pk_frame_depend_er IS NULL
AND pk_layer_depend_er IS NULL;

CREATE INDEX IF NOT EXISTS i_frame_depend_candidates
ON frame (pk_job, pk_layer, pk_frame)
WHERE str_state = 'DEPEND'
AND int_depend_count > 0;
