-- Increase size of os column on host_stat

ALTER TABLE host_stat ALTER COLUMN str_os TYPE VARCHAR(32);
