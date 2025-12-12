-- Add a field to limit the max amount of concurrent procs a host can run
-- -1 means no limit
alter table host
    add int_concurrent_procs_limit INT NOT NULL DEFAULT -1;

alter table host_stat
    add int_running_procs INT NOT NULL DEFAULT 0;
