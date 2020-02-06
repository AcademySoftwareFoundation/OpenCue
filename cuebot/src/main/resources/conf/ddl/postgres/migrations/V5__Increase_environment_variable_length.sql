-- Increase the length of environment variable names:

ALTER TABLE "job_env" ALTER COLUMN "str_key" TYPE VARCHAR(2048);
ALTER TABLE "layer_env" ALTER COLUMN "str_key" TYPE VARCHAR(2048);
