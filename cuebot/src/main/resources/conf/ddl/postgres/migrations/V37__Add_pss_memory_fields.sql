-- Add PSS (Proportional Set Size) memory tracking fields
-- PSS provides a more accurate view of memory usage by proportionally
-- accounting for shared memory pages

-- Add PSS fields to layer_mem table
ALTER TABLE layer_mem
    ADD int_max_pss BIGINT DEFAULT 0;

CREATE INDEX i_max_pss_layer ON layer_mem (int_max_pss);

-- Add PSS fields to job_mem table
ALTER TABLE job_mem
    ADD int_max_pss BIGINT DEFAULT 0;

CREATE INDEX i_max_pss_job ON job_mem (int_max_pss);

-- Add PSS fields to job_resource table
ALTER TABLE job_resource
    ADD int_max_pss BIGINT DEFAULT 0;

-- Add PSS fields to layer_resource table
ALTER TABLE layer_resource
    ADD int_max_pss BIGINT DEFAULT 0;

-- Add PSS fields to proc table
ALTER TABLE proc
    ADD int_pss_max_used BIGINT DEFAULT 0,
    ADD int_pss_used BIGINT DEFAULT 0;

-- Add PSS fields to frame table
ALTER TABLE frame
    ADD int_pss_max_used BIGINT DEFAULT 0,
    ADD int_pss_used BIGINT DEFAULT 0;
