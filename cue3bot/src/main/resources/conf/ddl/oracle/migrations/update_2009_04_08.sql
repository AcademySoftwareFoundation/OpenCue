/**
* Moved all columns that are updated during a host ping
* into host_stat so host pings do not interfere with dispatching
**/
ALTER TABLE host_stat ADD ts_ping TIMESTAMP WITH TIME ZONE DEFAULT systimestamp NOT NULL;
ALTER TABLE host_stat ADD ts_booted TIMESTAMP WITH TIME ZONE DEFAULT systimestamp NOT NULL; 
ALTER TABLE host_stat ADD str_state VARCHAR2(32) DEFAULT 'Up' NOT NULL ;

update host_stat SET ts_ping = (SELECT ts_ping FROM host WHERE host_stat.pk_host = host.pk_host);
update host_stat SET ts_booted = (SELECT ts_booted FROM host WHERE host_stat.pk_host = host.pk_host);
update host_stat SET str_state = (SELECT str_state FROM host WHERE host_stat.pk_host = host.pk_host);

ALTER TABLE host DROP COLUMN str_state;
ALTER TABLE host DROP COLUMN ts_booted;
ALTER TABLE host DROP COLUMN ts_ping;

CREATE OR REPLACE VIEW cue3.vs_alloc_usage AS
    SELECT
        alloc.pk_alloc,
        NVL(SUM(host.int_cores),0) AS int_cores,
        NVL(SUM(host.int_cores_idle),0) AS int_idle_cores,
        NVL(SUM(host.int_cores - host.int_cores_idle),0) as int_running_cores,
        NVL((SELECT SUM(int_cores) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND (str_lock_state='NimbyLocked' OR str_lock_state='Locked')),0) AS int_locked_cores,
        NVL((SELECT SUM(int_cores_idle) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND h.str_lock_state='Open' AND hs.str_state !='Down'),0) AS int_available_cores,
        COUNT(host.pk_host) AS int_hosts,
        (SELECT COUNT(*) FROM host WHERE host.pk_alloc=alloc.pk_alloc AND str_lock_state='Locked') AS int_locked_hosts,
        (SELECT COUNT(*) FROM host h,host_stat hs WHERE h.pk_host = hs.pk_host AND h.pk_alloc=alloc.pk_alloc AND hs.str_state='Down') AS int_down_hosts         
    FROM
        alloc LEFT JOIN host ON (alloc.pk_alloc = host.pk_alloc)
    GROUP BY
        alloc.pk_alloc;   

/**
* This column is unsused
**/
ALTER TABLE host_stat DROP COLUMN b_over_loaded;

