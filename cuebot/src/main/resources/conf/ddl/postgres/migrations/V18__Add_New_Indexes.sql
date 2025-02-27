--Performance issue, Created new index on column int_gpus_min and int_gpus_mem_min

CREATE INDEX IF NOT EXISTS i_layer_int_gpus_min
    ON layer USING btree
    (int_gpus_min ASC NULLS LAST);
    

CREATE INDEX IF NOT EXISTS i_layer_int_gpus_mem_min_1
    ON layer USING btree
    (int_gpu_mem_min ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS i_layer_int_cores_max ON layer(int_cores_max);

CREATE INDEX IF NOT EXISTS i_job_resource_int_priority ON job_resource(int_priority);

CREATE INDEX IF NOT EXISTS i_job_int_min_cores ON job(int_min_cores);

CREATE INDEX IF NOT EXISTS i_layer_limit_pk_layer ON layer_limit(pk_layer);

CREATE INDEX IF NOT EXISTS i_folder_resource_int_cores ON folder_resource(int_cores);

CREATE INDEX IF NOT EXISTS i_job_ts_updated ON job(ts_updated);

CREATE INDEX IF NOT EXISTS i_layer_str_tags ON layer(str_tags);
