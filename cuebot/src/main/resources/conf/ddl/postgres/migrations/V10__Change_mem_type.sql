-- Change memory type from INT to BIGINT.

ALTER TABLE "job_mem" ALTER COLUMN "int_max_rss" TYPE BIGINT;
ALTER TABLE "job_mem" ALTER COLUMN "int_max_vss" TYPE BIGINT;
ALTER TABLE "job_resource" ALTER COLUMN "int_max_rss" TYPE BIGINT;
ALTER TABLE "job_resource" ALTER COLUMN "int_max_vss" TYPE BIGINT;
ALTER TABLE "layer_mem" ALTER COLUMN "int_max_rss" TYPE BIGINT;
ALTER TABLE "layer_mem" ALTER COLUMN "int_max_vss" TYPE BIGINT;
ALTER TABLE "layer_resource" ALTER COLUMN "int_max_rss" TYPE BIGINT;
ALTER TABLE "layer_resource" ALTER COLUMN "int_max_vss" TYPE BIGINT;
