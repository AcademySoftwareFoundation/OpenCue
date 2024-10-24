-- Increase size of os column on host_stat
ALTER TABLE host_stat
MODIFY COLUMN str_os VARCHAR(32);